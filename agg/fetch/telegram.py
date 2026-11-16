from __future__ import annotations

import hashlib
from datetime import datetime
from urllib.parse import urljoin

from lxml import html as lxml_html

from ..config import SourceCfg
from ..models import FetchResult, RawItem
from ..text import strip_html
from .base import FetchCtx, request

BASE = "https://t.me"
_MEDIA_STYLE = "background-image"


def _message_text(node) -> str:
    parts = node.xpath('.//div[contains(@class,"tgme_widget_message_text")]//text()')
    return strip_html(" ".join(str(part) for part in parts))


def _published(node) -> int | None:
    values = node.xpath('.//time/@datetime')
    if not values:
        return None
    try:
        return int(datetime.fromisoformat(str(values[0]).replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _link(node, channel: str, post_id: str) -> str:
    values = node.xpath('.//a[contains(@class,"tgme_widget_message_date")]/@href')
    if values:
        return urljoin(BASE, str(values[0]))
    return f"{BASE}/{channel}/{post_id}" if post_id else f"{BASE}/s/{channel}"


def _media(node) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for anchor in node.xpath('.//a[contains(@class,"tgme_widget_message_photo_wrap")]'):
        style = anchor.get("style") or ""
        start = style.find("url(")
        if start == -1:
            continue
        end = style.find(")", start)
        url = style[start + 4:end].strip("'\" ")
        if url.startswith("http") and url not in seen:
            seen.add(url)
            out.append({"url": url, "type": "image"})
    for image in node.xpath('.//img[contains(@class,"tgme_widget_message")]/@src'):
        url = str(image)
        if url.startswith("http") and url not in seen:
            seen.add(url)
            out.append({"url": url, "type": "image"})
    return out[:6]


def parse_messages(markup: str, channel: str, source: SourceCfg) -> list[RawItem]:
    limit = int(source.options.get("limit", 30))
    root = lxml_html.fromstring(markup)
    items: list[RawItem] = []
    for node in root.xpath('//div[contains(@class,"tgme_widget_message") and @data-post]'):
        classes = (node.get("class") or "").split()
        if "service_message" in classes or "text_not_supported_wrap" in classes:
            continue
        text = _message_text(node)
        if not text:
            continue
        post_id = str(node.get("data-post") or "").rsplit("/", 1)[-1]
        title = " ".join(text.split())
        if len(title) > 140:
            title = title[:140].rsplit(" ", 1)[0] + "…"
        items.append(
            RawItem(
                source=source.name,
                kind="social",
                guid=f"telegram:{channel}:{post_id or hashlib.sha1(text.encode()).hexdigest()}",
                title=title,
                url=_link(node, channel, post_id),
                summary=text,
                published_ts=_published(node),
                media=_media(node),
                extra={"source_type": "telegram", "channel": channel, "post_id": post_id},
            )
        )
        if len(items) >= limit:
            break
    return items


async def fetch(ctx: FetchCtx, source: SourceCfg) -> FetchResult:
    channel = str(source.options.get("channel") or "").strip().lstrip("@")
    if not channel:
        raise ValueError(f"telegram source {source.name} needs options.channel")
    url = source.url or f"{BASE}/s/{channel}"
    headers = {"User-Agent": str(source.options.get("user_agent") or "Mozilla/5.0")}
    resp = await request(
        ctx.client, url, headers=headers, retries=int(source.options.get("retries", 1))
    )
    resp.raise_for_status()
    return FetchResult(parse_messages(resp.text, channel, source))
