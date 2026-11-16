from __future__ import annotations

from ..config import SourceCfg
from ..models import FetchResult
from . import google_news, rss, telegram, web, x

REGISTRY = {
    "rss": rss.fetch,
    "google_news": google_news.fetch,
    "web": web.fetch,
    "x": x.fetch,
    "telegram": telegram.fetch,
}


async def fetch_source(ctx, source: SourceCfg) -> FetchResult:
    handler = REGISTRY.get(source.kind)
    if handler is None:
        raise ValueError(f"unknown source kind: {source.kind}")
    return await handler(ctx, source)
