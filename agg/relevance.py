from __future__ import annotations

import re

from .config import AccountCfg
from .models import RawItem


def _compile(terms: list[str]) -> list[re.Pattern[str]]:
    return [
        re.compile(r"(?<![\w])" + re.escape(term.lower()) + r"(?![\w])", re.IGNORECASE)
        for term in terms
        if term.strip()
    ]


class RelevanceMatcher:
    def __init__(self, cfg: AccountCfg):
        self.require_any = _compile(cfg.relevance.require_any)
        self.exclude_any = _compile(cfg.relevance.exclude_any)
        self.context_any = _compile(cfg.relevance.context_any)
        self.skip_sources = {
            source.name for source in cfg.sources
            if source.skip_relevance
        }

    def keep(self, item: RawItem) -> bool:
        hay = f"{item.title} {item.summary}"[:2000]
        if self.exclude_any and any(p.search(hay) for p in self.exclude_any):
            return False
        if item.source in self.skip_sources:
            return True
        if self.require_any and not any(p.search(hay) for p in self.require_any):
            return False
        if self.context_any and not any(p.search(hay) for p in self.context_any):
            return False
        return True
