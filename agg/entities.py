from __future__ import annotations

import re
import sqlite3

from .config import AccountCfg


class EntityMatcher:
    def __init__(self, cfg: AccountCfg):
        dict_sources: dict[str, list[str]] = {
            "publisher": cfg.watchlist.get("publishers", []),
            "team": cfg.watchlist.get("teams", []),
            "player": cfg.watchlist.get("players", []),
            "tournament": cfg.watchlist.get("tournaments", []),
            "studio": cfg.watchlist.get("studios", []),
            "ticker": cfg.watchlist.get("tickers", []),
            "company": cfg.watchlist.get("companies", []),
            "hardware": cfg.watchlist.get("hardware", []),
            "keyword": cfg.watchlist.get("keywords", []),
        }
        for kind, names in cfg.entities.items():
            dict_sources.setdefault(kind, []).extend(names)

        beats = [name.strip() for name in cfg.watchlist.get("beats", []) if name.strip()]
        alias_to_beat = {name.lower(): name for name in beats}
        for canonical, aliases in cfg.beat_aliases.items():
            canonical = canonical.strip()
            if not canonical:
                continue
            if canonical not in beats:
                beats.append(canonical)
            alias_to_beat.setdefault(canonical.lower(), canonical)
            for alias in aliases:
                key = alias.strip().lower()
                if key:
                    alias_to_beat[key] = canonical

        self.index: list[tuple[str, str, str]] = []
        seen: set[str] = set()
        for key, canonical in alias_to_beat.items():
            if key in seen:
                continue
            seen.add(key)
            self.index.append((key, canonical, "beat"))
        for kind, names in dict_sources.items():
            for name in names:
                key = name.strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                self.index.append((key, name.strip(), kind))
        self.index.sort(key=lambda row: len(row[0]), reverse=True)
        self._patterns = {
            key: re.compile(r"(?<![\w])" + re.escape(key) + r"(?![\w])", re.IGNORECASE)
            for key, _, _ in self.index
        }

    def match(self, text: str) -> list[tuple[str, str, str]]:
        if not text:
            return []
        found: list[tuple[str, str, str]] = []
        for key, name, kind in self.index:
            if self._patterns[key].search(text):
                found.append((key, name, kind))
        return found


def ensure_entities(
    conn: sqlite3.Connection, item_id: int, matches: list[tuple[str, str, str]]
) -> list[int]:
    ids: list[int] = []
    seen: set[tuple[str, str]] = set()
    for _, name, kind in matches:
        pair = (name, kind)
        if pair in seen:
            continue
        seen.add(pair)
        conn.execute(
            "INSERT OR IGNORE INTO entities(name, kind) VALUES(?, ?)", (name, kind)
        )
        row = conn.execute(
            "SELECT id FROM entities WHERE name=? AND kind=?", (name, kind)
        ).fetchone()
        if row:
            ids.append(int(row["id"]))
    if ids:
        conn.executemany(
            "INSERT OR IGNORE INTO item_entities(item_id, entity_id) VALUES(?, ?)",
            [(item_id, eid) for eid in ids],
        )
    return ids
