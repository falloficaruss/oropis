from __future__ import annotations

import hashlib
import re
from urllib.parse import urlencode

import feedparser

from ..config import SourceCfg
from ..models import FetchResult, RawItem
from ..text import strip_html
from .base import FetchCtx, request, struct_to_ts

SEARCH = "https://news.google.com/rss/search"


def _feed_url(source: SourceCfg) -> str:
    if source.url:
        return source.url
    query = source.options.get("query")
    if not query:
        raise ValueError(f"google_news source {source.name} needs url or options.query")
    params = {
        "q": str(query),
        "hl": str(source.options.get("hl", "en-US")),
        "gl": str(source.options.get("gl", "US")),
        "ceid": str(source.options.get("ceid", "US:en")),
    }
    return f"{SEARCH}?{urlencode(params)}"


def _publisher(entry: dict) -> tuple[str, str]:
    source = entry.get("source") or {}
    if isinstance(source, dict):
        return str(source.get("title") or ""), str(source.get("href") or "")
    return str(source or ""), ""


def _clean_title(title: str, publisher: str) -> str:
    suffix = f" - {publisher}"
    if publisher and title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title


async def fetch(ctx: FetchCtx, source: SourceCfg) -> FetchResult:
    url = _feed_url(source)
    retries = int(source.options.get("retries", ctx.cfg.network.retries))
    resp = await request(ctx.client, url, retries=retries)
    if resp.status_code == 304:
        return FetchResult([], not_modified=True)
    resp.raise_for_status()

    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"unparseable Google News feed: {feed.get('bozo_exception')}")

    limit = int(source.options.get("limit", ctx.cfg.poll.max_items_per_source))
    require_any = [
        re.compile(r"(?<![\w])" + re.escape(k.lower()) + r"(?![\w])", re.IGNORECASE)
        for k in source.options.get("require_any", [])
    ]
    exclude_any = [
        re.compile(r"(?<![\w])" + re.escape(k.lower()) + r"(?![\w])", re.IGNORECASE)
        for k in source.options.get("exclude_any", [])
    ]
    items: list[RawItem] = []
    for entry in feed.entries[:limit]:
        title = strip_html(entry.get("title"))
        if not title:
            continue
        publisher, publisher_url = _publisher(entry)
        title = _clean_title(title, publisher)
        summary = strip_html(entry.get("summary"))
        hay = f"{title} {summary}"
        if exclude_any and any(p.search(hay) for p in exclude_any):
            continue
        if require_any and not any(p.search(hay) for p in require_any):
            continue
        link = entry.get("link")
        guid = entry.get("id") or link or hashlib.sha1(title.encode()).hexdigest()
        tags = [t.get("term") for t in entry.get("tags") or [] if t.get("term")]
        items.append(
            RawItem(
                source=source.name,
                kind=str(source.options.get("item_kind", "news")),
                guid=str(guid),
                title=title,
                url=link,
                summary=summary,
                author=entry.get("author"),
                published_ts=struct_to_ts(entry.get("published_parsed") or entry.get("updated_parsed")),
                extra={
                    "publisher": publisher,
                    "publisher_url": publisher_url,
                    "handle": publisher,
                    "tags": tags,
                    "feed_title": feed.feed.get("title"),
                },
            )
        )
    return FetchResult(items, etag=resp.headers.get("etag"), last_modified=resp.headers.get("last-modified"))
