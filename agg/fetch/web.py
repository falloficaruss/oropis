from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from lxml import html as lxml_html

from ..config import SourceCfg
from ..models import FetchResult, RawItem
from ..text import strip_html
from .base import FetchCtx, request


def _value(node, xpath: str | None) -> str:
    if not xpath:
        return ""
    values = node.xpath(xpath)
    if not values:
        return ""
    value = values[0]
    if hasattr(value, "text_content"):
        value = value.text_content()
    return " ".join(str(value).split())


def _timestamp(value: str, formats: list[str]) -> int | None:
    value = " ".join(value.split())
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    except (TypeError, ValueError):
        pass
    for fmt in formats:
        try:
            return int(datetime.strptime(value, fmt).replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            continue
    return None


def parse_items(markup: str, source: SourceCfg) -> list[RawItem]:
    """Extract a small, config-defined article listing from an official site."""
    opts = source.options
    item_xpath = str(opts.get("item_xpath") or "")
    if not item_xpath:
        raise ValueError(f"web source {source.name} needs options.item_xpath")
    root = lxml_html.fromstring(markup)
    limit = int(opts.get("limit", 30))
    base = str(opts.get("url_base") or source.url or "")
    formats = [str(v) for v in opts.get("date_formats", [])]
    items: list[RawItem] = []
    seen: set[str] = set()

    for node in root.xpath(item_xpath):
        if len(items) >= limit:
            break
        title = strip_html(_value(node, opts.get("title_xpath")))
        link = _value(node, opts.get("link_xpath"))
        if not title or not link:
            continue
        url = urljoin(base, link)
        guid = url or hashlib.sha1(title.encode()).hexdigest()
        if guid in seen:
            continue
        seen.add(guid)
        published = _timestamp(_value(node, opts.get("published_xpath")), formats)
        summary = strip_html(_value(node, opts.get("summary_xpath")))
        items.append(
            RawItem(
                source=source.name,
                kind=str(opts.get("item_kind", "news")),
                guid=guid,
                title=title,
                url=url,
                summary=summary,
                published_ts=published,
                extra={
                    "game": str(opts.get("game") or ""),
                    "source_type": "official_web",
                },
            )
        )
    return items


async def fetch(ctx: FetchCtx, source: SourceCfg) -> FetchResult:
    if not source.url:
        raise ValueError(f"web source {source.name} has no url")
    headers = {str(k): str(v) for k, v in (source.options.get("headers") or {}).items()}
    resp = await request(
        ctx.client,
        source.url,
        headers=headers or None,
        retries=int(source.options.get("retries", 1)),
    )
    resp.raise_for_status()
    return FetchResult(parse_items(resp.text, source))
