from __future__ import annotations

import asyncio
import calendar
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from ..config import AccountCfg, SourceCfg
from ..models import FetchResult


@dataclass
class FetchCtx:
    client: httpx.AsyncClient
    cfg: AccountCfg
    conn: sqlite3.Connection | None


def make_client(cfg: AccountCfg) -> httpx.AsyncClient:
    net = cfg.network
    return httpx.AsyncClient(
        headers={
            "User-Agent": net.user_agent,
            "Accept": "application/rss+xml, application/atom+xml, application/json, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=httpx.Timeout(net.timeout_s),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=net.max_concurrent, max_keepalive_connections=4),
    )


_HOST_MIN_INTERVAL = {
    "reddit.com": 45.0,
    "arxiv.org": 3.0,
}
_host_locks: dict[str, asyncio.Lock] = {}
_host_last: dict[str, float] = {}


async def _throttle(url: str) -> None:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    key = next((k for k in _HOST_MIN_INTERVAL if host.endswith(k)), None)
    if key is None:
        return
    lock = _host_locks.setdefault(key, asyncio.Lock())
    async with lock:
        wait = _HOST_MIN_INTERVAL[key] - (time.monotonic() - _host_last.get(key, 0.0))
        if wait > 0:
            await asyncio.sleep(wait)
        _host_last[key] = time.monotonic()


async def request(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    retries: int = 2,
) -> httpx.Response:
    delay = 1.0
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            await _throttle(url)
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                retry_after = resp.headers.get("retry-after", "")
                wait = float(retry_after) if retry_after.replace(".", "").isdigit() else delay
                await asyncio.sleep(min(wait, 30))
                delay *= 2
                continue
            return resp
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last = exc
            if attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
    raise last or RuntimeError(f"request failed: {url}")


def struct_to_ts(value: Any) -> int | None:
    if not value:
        return None
    try:
        return calendar.timegm(value)
    except (TypeError, ValueError):
        return None


def iso_to_ts(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


async def fetch_body(url: str | None, cfg: AccountCfg) -> str:
    if not url:
        return ""
    try:
        import trafilatura
    except ImportError:
        return ""
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": cfg.network.user_agent},
            timeout=httpx.Timeout(cfg.network.timeout_s),
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return ""
            return trafilatura.extract(resp.text) or ""
    except Exception:
        return ""


async def probe(
    client: httpx.AsyncClient,
    source: SourceCfg,
    cfg: AccountCfg,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    from . import fetch_source

    started = time.monotonic()
    try:
        result = await fetch_source(FetchCtx(client, cfg, conn), source)  # type: ignore[arg-type]
        elapsed = time.monotonic() - started
        latest = max((i.published_ts or 0 for i in result.items), default=0)
        return {
            "ok": True,
            "status": 304 if result.not_modified else 200,
            "items": len(result.items),
            "ms": int(elapsed * 1000),
            "latest_ts": latest or None,
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "items": 0,
            "ms": int((time.monotonic() - started) * 1000),
            "latest_ts": None,
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def _unused(_: FetchResult) -> None:
    return None
