from __future__ import annotations

import hashlib
import re

import feedparser

from ..config import SourceCfg
from ..models import FetchResult, RawItem
from ..text import strip_html
from .base import FetchCtx, request, struct_to_ts

_IMG = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


def _media(entry: dict, summary_html: str) -> list[dict]:
    media: list[dict] = []
    seen: set[str] = set()

    def add(url: str | None, kind: str = "image", **extra) -> None:
        if not url or url in seen or not url.startswith("http"):
            return
        seen.add(url)
        media.append({"url": url, "type": kind, **extra})

    for item in entry.get("media_content") or []:
        add(item.get("url"), item.get("medium") or "image")
    for item in entry.get("media_thumbnail") or []:
        add(item.get("url"), "image")
    for link in entry.get("links") or []:
        if link.get("rel") == "enclosure":
            add(link.get("href"), "video" if "video" in (link.get("type") or "") else "image")
    for match in _IMG.finditer(summary_html or ""):
        add(match.group(1), "image")
    return media[:6]


async def fetch(ctx: FetchCtx, source: SourceCfg) -> FetchResult:
    if not source.url:
        raise ValueError(f"rss source {source.name} has no url")
    headers: dict[str, str] = {}
    if source.options.get("etag"):
        headers["If-None-Match"] = str(source.options["etag"])
    retries = int(source.options.get("retries", ctx.cfg.network.retries))
    resp = await request(ctx.client, source.url, headers=headers, retries=retries)
    if resp.status_code == 304:
        return FetchResult([], not_modified=True)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"unparseable feed: {feed.get('bozo_exception')}")

    limit = int(source.options.get("limit", ctx.cfg.poll.max_items_per_source))
    require_any = [
        re.compile(r"(?<![a-z0-9])" + re.escape(k.lower()) + r"(?![a-z0-9])", re.IGNORECASE)
        for k in source.options.get("require_any", [])
    ]
    exclude_any = [
        re.compile(r"(?<![a-z0-9])" + re.escape(k.lower()) + r"(?![a-z0-9])", re.IGNORECASE)
        for k in source.options.get("exclude_any", [])
    ]
    items: list[RawItem] = []
    for entry in feed.entries[:limit]:
        title = strip_html(entry.get("title"))
        if not title:
            continue
        link = entry.get("link")
        summary_html = entry.get("summary") or ""
        content = ""
        if entry.get("content"):
            content = " ".join(strip_html(c.get("value")) for c in entry["content"])
        guid = entry.get("id") or link or hashlib.sha1(title.encode()).hexdigest()
        tags = [t.get("term") for t in entry.get("tags") or [] if t.get("term")]
        hay = f"{title} {strip_html(summary_html)}".lower()
        if exclude_any and any(p.search(hay) for p in exclude_any):
            continue
        if require_any and not any(p.search(hay) for p in require_any):
            continue
        items.append(
            RawItem(
                source=source.name,
                kind=str(source.options.get("item_kind", "news")),
                guid=str(guid),
                title=title,
                url=link,
                summary=strip_html(summary_html),
                body=content,
                author=entry.get("author"),
                published_ts=struct_to_ts(entry.get("published_parsed") or entry.get("updated_parsed")),
                media=_media(entry, summary_html),
                extra={"tags": tags, "feed_title": feed.feed.get("title")},
            )
        )
    return FetchResult(
        items,
        etag=resp.headers.get("etag"),
        last_modified=resp.headers.get("last-modified"),
    )
