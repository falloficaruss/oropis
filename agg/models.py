from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RawItem:
    source: str
    kind: str
    guid: str
    title: str
    url: str | None = None
    summary: str = ""
    body: str = ""
    author: str | None = None
    published_ts: int | None = None
    media: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    items: list[RawItem]
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


@dataclass(slots=True)
class Cluster:
    id: int
    account: str
    canonical_title: str
    first_seen_ts: int
    last_seen_ts: int
    item_count: int
    source_count: int
    simhash: str
    score: float
    archetype: str
    canonical_url: str | None
