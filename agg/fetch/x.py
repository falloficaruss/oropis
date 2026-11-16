from __future__ import annotations

import asyncio
import hashlib
import re

from ..config import SourceCfg
from ..models import FetchResult, RawItem
from ..text import now_ts, strip_html
from .base import FetchCtx, request

PROFILE = "https://api.fxtwitter.com/2/profile/{handle}/statuses"
_TITLE = re.compile(r"\s+")


def _media(status: dict) -> list[dict]:
    media = status.get("media") or {}
    out: list[dict] = []
    for item in media.get("all") or []:
        kind = str(item.get("type") or "photo")
        if kind == "video":
            thumb = item.get("thumbnail_url")
            if thumb:
                out.append({"url": thumb, "type": "image", "source": item.get("url")})
        else:
            url = item.get("url") or item.get("thumbnail_url")
            if url:
                out.append({"url": url, "type": "image", "alt": item.get("alt", "")})
    return out[:6]


def _title(text: str) -> str:
    line = _TITLE.sub(" ", (text or "").strip()).strip()
    if len(line) <= 140:
        return line
    cut = line[:140].rsplit(" ", 1)[0]
    return cut + "…"


def parse_statuses(handle: str, payload: dict, source: SourceCfg) -> list[RawItem]:
    limit = int(source.options.get("limit", 30))
    max_age_h = float(source.options.get("max_age_h", 72))
    items: list[RawItem] = []
    cutoff = now_ts() - int(max_age_h * 3600) if max_age_h else 0
    for status in (payload.get("results") or [])[:limit]:
        if status.get("type") not in (None, "status"):
            continue
        text = str(status.get("text") or "").strip()
        if not text:
            continue
        url = status.get("url")
        sid = str(status.get("id") or "")
        author = status.get("author") or {}
        screen_name = str(author.get("screen_name") or handle)
        published = status.get("created_timestamp")
        if cutoff and published and int(published) < cutoff:
            continue
        items.append(
            RawItem(
                source=source.name,
                kind="social",
                guid=f"x:{screen_name}:{sid or hashlib.sha1(text.encode()).hexdigest()}",
                title=_title(text),
                url=url,
                summary=text,
                author=str(author.get("name") or screen_name),
                published_ts=int(published) if published else None,
                media=_media(status),
                extra={
                    "source_type": "x",
                    "handle": screen_name,
                    "display_name": author.get("name"),
                    "followers": author.get("followers"),
                    "likes": status.get("likes"),
                    "reposts": status.get("reposts"),
                    "replies": status.get("replies"),
                    "views": status.get("views"),
                    "lang": status.get("lang"),
                },
            )
        )
    return items


async def fetch(ctx: FetchCtx, source: SourceCfg) -> FetchResult:
    handles = source.options.get("handles") or []
    if isinstance(handles, str):
        handles = [handles]
    handles = [str(h).strip().lstrip("@") for h in handles if str(h).strip()]
    if not handles:
        raise ValueError(f"x source {source.name} needs options.handles")
    limit = max(1, min(100, int(source.options.get("limit", 30))))
    with_replies = str(bool(source.options.get("with_replies", False))).lower()
    headers = {"User-Agent": str(source.options.get("user_agent") or "Mozilla/5.0")}
    items: list[RawItem] = []
    errors: list[str] = []
    for handle in handles:
        try:
            resp = None
            for attempt in range(3):
                resp = await request(
                    ctx.client,
                    PROFILE.format(handle=handle),
                    params={"count": limit, "with_replies": with_replies},
                    headers=headers,
                    retries=int(source.options.get("retries", 2)),
                )
                if resp.status_code != 404:
                    break
                await asyncio.sleep(1.5 * (attempt + 1))
            assert resp is not None
            if resp.status_code == 404:
                errors.append(f"{handle}: no timeline")
                continue
            if resp.status_code != 200:
                errors.append(f"{handle}: HTTP {resp.status_code}")
                continue
            items.extend(parse_statuses(handle, resp.json(), source))
        except Exception as exc:  # noqa: BLE001 - one bad account should not kill the source
            errors.append(f"{handle}: {type(exc).__name__}: {exc}"[:160])
    if errors and not items:
        raise ValueError("; ".join(errors))
    return FetchResult(items)
