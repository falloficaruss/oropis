from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from ..config import AccountCfg

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/avif": ".avif",
    "image/gif": ".gif",
}
MAX_BYTES = 5 * 1024 * 1024


class MediaError(RuntimeError):
    pass


def _public_host(host: str) -> None:
    if not host:
        raise MediaError("image URL has no host")
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise MediaError(f"cannot resolve image host: {host}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise MediaError("image host is not a public address")


def _validate_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise MediaError("image URL must be http(s)")
    _public_host(parts.hostname or "")


async def cache_hero(cfg: AccountCfg, story: dict | object, slug: str) -> str | None:
    if not cfg.site.cache_heroes:
        return None
    url = story["hero_url"] if not isinstance(story, dict) else story.get("hero_url")
    if not url:
        return None
    _validate_url(str(url))
    timeout = httpx.Timeout(20.0, connect=8.0)
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, max_redirects=3
    ) as client:
        async with client.stream("GET", str(url)) as response:
            response.raise_for_status()
            _public_host(response.url.host or "")
            content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
            ext = ALLOWED.get(content_type)
            if not ext:
                raise MediaError(f"unsupported image type: {content_type or 'unknown'}")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise MediaError("image is larger than 5 MB")
                chunks.append(chunk)
    target_dir = cfg.root / cfg.site.media_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}{ext}"
    path = target_dir / filename
    path.write_bytes(b"".join(chunks))
    return filename


def local_hero(cfg: AccountCfg, story: dict | object) -> Path | None:
    name = story["hero_local"] if not isinstance(story, dict) else story.get("hero_local")
    if not name:
        return None
    path = cfg.root / cfg.site.media_dir / str(name)
    return path if path.exists() else None
