from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass, field

from .config import AccountCfg
from .text import STOPWORDS, now_ts

_CAP = re.compile(r"\b([A-Z][A-Za-z0-9&'.\-]*(?:\s+[A-Z][A-Za-z0-9&'.\-]*){0,3})\b")
_ACRONYM = re.compile(r"\b([A-Z]{2,6})\b")
_NOISE = {"the", "this", "that", "new", "how", "why", "what", "when", "here", "now"}


@dataclass
class Topic:
    label: str
    df: int
    sources: int
    burst: float
    score: float
    members: list[str] = field(default_factory=list)
    hourly: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "df": self.df,
            "sources": self.sources,
            "burst": round(self.burst, 2),
            "score": round(self.score, 3),
            "members": self.members,
            "hourly": self.hourly,
        }


def _terms(title: str) -> set[str]:
    out: set[str] = set()
    for match in _CAP.finditer(title):
        phrase = match.group(1).strip(" .-")
        words = phrase.split()
        if not words or words[0].lower() in STOPWORDS:
            continue
        if all(w.lower() in _NOISE for w in words):
            continue
        if len(phrase) < 3:
            continue
        out.add(phrase)
    for match in _ACRONYM.finditer(title):
        if match.group(1).lower() not in STOPWORDS:
            out.add(match.group(1))
    return out


class _UnionFind:
    def __init__(self, keys: list[str]):
        self.parent = {k: k for k in keys}

    def find(self, key: str) -> str:
        while self.parent[key] != key:
            self.parent[key] = self.parent[self.parent[key]]
            key = self.parent[key]
        return key

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def compute_topics(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    since_h: float = 24.0,
    min_df: int = 2,
    min_sources: int = 2,
    limit: int = 20,
    spark_hours: int = 24,
) -> list[Topic]:
    now = now_ts()
    since = now - int(since_h * 3600)
    clusters = conn.execute(
        """SELECT id, canonical_title, first_seen_ts, last_seen_ts, source_count
           FROM clusters WHERE account=? AND last_seen_ts >= ?""",
        (cfg.account, since),
    ).fetchall()
    if not clusters:
        return []

    cluster_ids = [int(c["id"]) for c in clusters]
    placeholders = ",".join("?" * len(cluster_ids))

    entity_rows = conn.execute(
        f"""SELECT DISTINCT i.cluster_id AS cid, e.name AS name
            FROM items i
            JOIN item_entities ie ON ie.item_id = i.id
            JOIN entities e ON e.id = ie.entity_id
            WHERE i.cluster_id IN ({placeholders})""",
        cluster_ids,
    ).fetchall()
    source_rows = conn.execute(
        f"""SELECT DISTINCT cluster_id AS cid, source FROM items
            WHERE cluster_id IN ({placeholders})""",
        cluster_ids,
    ).fetchall()

    last_seen: dict[int, int] = {int(c["id"]): int(c["last_seen_ts"]) for c in clusters}
    cluster_terms: dict[int, set[str]] = {cid: set() for cid in cluster_ids}
    for row in clusters:
        cluster_terms[int(row["id"])].update(_terms(row["canonical_title"]))
    for row in entity_rows:
        cluster_terms[int(row["cid"])].add(row["name"])

    sources_by_cluster: dict[int, set[str]] = {cid: set() for cid in cluster_ids}
    for row in source_rows:
        sources_by_cluster[int(row["cid"])].add(row["source"])

    term_clusters: dict[str, set[int]] = {}
    display: dict[str, str] = {}
    for cid, terms in cluster_terms.items():
        for term in terms:
            key = term.lower()
            display.setdefault(key, term)
            if display[key].isupper() and term[0].isupper() and not term.isupper():
                display[key] = term
            term_clusters.setdefault(key, set()).add(cid)

    term_sources: dict[str, set[str]] = {}
    for term, cids in term_clusters.items():
        srcs: set[str] = set()
        for cid in cids:
            srcs |= sources_by_cluster.get(cid, set())
        term_sources[term] = srcs

    filtered = [
        term for term, cids in term_clusters.items()
        if len(cids) >= min_df and len(term_sources[term]) >= min_sources
    ]
    if not filtered:
        return []

    uf = _UnionFind(filtered)
    filtered.sort(key=lambda t: len(term_clusters[t]), reverse=True)
    for i, a in enumerate(filtered):
        set_a = term_clusters[a]
        for b in filtered[i + 1:]:
            set_b = term_clusters[b]
            inter = len(set_a & set_b)
            union = len(set_a | set_b)
            if not inter or not union:
                continue
            containment = inter / min(len(set_a), len(set_b))
            if inter / union > 0.5 or containment > 0.65:
                uf.union(a, b)

    groups: dict[str, list[str]] = {}
    for term in filtered:
        groups.setdefault(uf.find(term), []).append(term)

    topics: list[Topic] = []
    for members in groups.values():
        merged_clusters: set[int] = set()
        merged_sources: set[str] = set()
        for term in members:
            merged_clusters |= term_clusters[term]
            merged_sources |= term_sources[term]
        label_key = max(members, key=lambda t: (len(term_clusters[t]), len(t)))
        label = display.get(label_key, label_key)
        hourly = [0] * spark_hours
        for cid in merged_clusters:
            ts = last_seen.get(cid, now)
            bucket = spark_hours - 1 - (now - ts) // 3600
            if 0 <= bucket < spark_hours:
                hourly[bucket] += 1
        recent = sum(hourly[-6:])
        baseline = sum(hourly[:-6]) / max(1, (spark_hours - 6) / 6)
        burst = recent / (baseline + 1.0)
        df = len(merged_clusters)
        src = len(merged_sources)
        score = math.log1p(df) * math.log1p(src) * (1.0 + burst)
        topics.append(
            Topic(
                label=label,
                df=df,
                sources=src,
                burst=round(burst, 2),
                score=round(score, 3),
                members=[
                    display.get(t, t)
                    for t in sorted(members, key=lambda t: len(term_clusters[t]), reverse=True)[:6]
                ],
                hourly=hourly,
            )
        )

    topics.sort(key=lambda t: (t.score, t.df), reverse=True)
    return topics[:limit]
