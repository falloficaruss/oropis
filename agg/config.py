from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

_ENV = re.compile(r"\$\{([A-Z0-9_]+)\}")


class NetworkCfg(BaseModel):
    user_agent: str = "agg/0.1 (+https://oropis.com; contact: editorial@oropis.com)"
    timeout_s: float = 20.0
    max_concurrent: int = 6
    retries: int = 2
    reddit_delay_s: float = 2.0


class PollCfg(BaseModel):
    default_interval_s: int = 300
    catchup_hours: int = 72
    digest_cap: int = 30
    jitter_s: int = 15
    max_items_per_source: int = 60


class ScoringCfg(BaseModel):
    recency_half_life_h: float = 6.0
    watchlist_boost: float = 0.20
    single_source_penalty: float = 0.15


class RelevanceCfg(BaseModel):
    require_any: list[str] = Field(default_factory=list)
    exclude_any: list[str] = Field(default_factory=list)
    # Optional second gate: an item must also contain one of these terms. Use it
    # when a broad feed mentions AI or robots in passing and you want only
    # substantive coverage.
    context_any: list[str] = Field(default_factory=list)


class TelegramCfg(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    min_score: float = 0.55
    official_min_score: float = 0.45
    max_per_hour: int = 12
    max_per_day: int = 80
    max_age_h: float = 6.0
    backfill_minutes: int = 15
    poll_interval_s: int = 20
    max_attempts: int = 3
    disable_preview: bool = True
    instant_sources: list[str] = Field(default_factory=list)
    # Sources that enrich the database and digest but must not, by themselves,
    # trigger a push. This is useful for search/news aggregators that can surface
    # a recap long after the primary announcement.
    discovery_only_sources: list[str] = Field(default_factory=list)


class SiteCfg(BaseModel):
    enabled: bool = False
    name: str = "Oropis"
    tagline: str = "Robotics & AI, reported."
    description: str = "Independent coverage of artificial intelligence and robotics."
    base_url: str = "https://oropis.com"
    email: str = ""
    x_handle: str = "@OropisHQ"
    db: str = "site.db"
    media_dir: str = "site-media"
    repo_path: str = "site-repo"
    repo_url: str = "git@github.com:falloficaruss/oropis.git"
    branch: str = "master"
    host: str = "127.0.0.1"
    port: int = 8091
    page_size: int = 20
    min_draft_score: float = 0.45
    default_author: str = "OropisHQ"
    auto_deploy: bool = True
    deploy_limit: int = 6
    cache_heroes: bool = True
    plan_days: int = 7
    plan_targets: dict[str, list[int]] = Field(
        default_factory=lambda: {
            "research": [3, 5],
            "product": [3, 5],
            "deployment": [2, 4],
            "funding": [2, 4],
            "policy": [1, 3],
            "business": [1, 3],
            "news": [2, 4],
        }
    )

    @field_validator("base_url")
    @classmethod
    def _strip_slash(cls, v: str) -> str:
        return v.rstrip("/")


class SourceCfg(BaseModel):
    name: str
    kind: str
    enabled: bool = True
    interval_s: int | None = None
    authority: float = 0.5
    tier: int = 1
    skip_relevance: bool = False
    url: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("authority")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class AccountCfg(BaseModel):
    account: str
    db: str = "data.db"
    network: NetworkCfg = Field(default_factory=NetworkCfg)
    poll: PollCfg = Field(default_factory=PollCfg)
    scoring: ScoringCfg = Field(default_factory=ScoringCfg)
    relevance: RelevanceCfg = Field(default_factory=RelevanceCfg)
    telegram: TelegramCfg = Field(default_factory=TelegramCfg)
    site: SiteCfg = Field(default_factory=SiteCfg)
    sources: list[SourceCfg] = Field(default_factory=list)
    watchlist: dict[str, list[str]] = Field(default_factory=dict)
    entities: dict[str, list[str]] = Field(default_factory=dict)
    # Canonical beat name -> alternate names. Aliases tag the canonical beat so
    # "artificial intelligence" and "AI" stay on one desk.
    beat_aliases: dict[str, list[str]] = Field(default_factory=dict)
    voice: dict[str, Any] = Field(default_factory=dict)

    @property
    def root(self) -> Path:
        return self._root

    def source(self, name: str) -> SourceCfg | None:
        return next((s for s in self.sources if s.name == name), None)


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return _ENV.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


def load_account(path: str | Path) -> AccountCfg:
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path / "config.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no config at {path}")
    data = _expand(yaml.safe_load(path.read_text()) or {})
    cfg = AccountCfg(**data)
    cfg._root = path.parent  # type: ignore[attr-defined]
    return cfg


def resolve_account(arg: str | None, cwd: Path | None = None) -> AccountCfg:
    cwd = cwd or Path.cwd()
    if arg:
        candidates = [
            Path(arg),
            cwd / arg,
            Path.home() / "twitter" / arg,
            Path(arg).expanduser(),
        ]
        for c in candidates:
            if (c / "config.yaml").exists() or (c.suffix in {".yaml", ".yml"} and c.exists()):
                return load_account(c)
        raise FileNotFoundError(f"cannot resolve account {arg!r}")
    if (cwd / "config.yaml").exists() and cwd.name in {"oropis", "twitter"}:
        return load_account(cwd)
    for name in ("oropis",):
        if (cwd / name / "config.yaml").exists():
            return load_account(cwd / name)
    raise FileNotFoundError("pass --account oropis")
