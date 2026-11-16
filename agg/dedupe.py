from __future__ import annotations

import re
import sqlite3

from .config import AccountCfg
from .db import insert_item
from .entities import EntityMatcher, ensure_entities
from .models import RawItem
from .relevance import RelevanceMatcher
from .text import (
    GENERIC_PROPER,
    canonical_url,
    hamming,
    jaccard,
    now_ts,
    proper_tokens,
    simhash64,
    tokenize,
)

WINDOW_S = 72 * 3600
ARCHETYPE_BY_KIND = {
    "research": "research",
    "paper": "research",
    "product": "product",
    "release": "product",
    "launch": "product",
    "deployment": "deployment",
    "policy": "policy",
    "funding": "funding",
    "filing": "funding",
    "business": "business",
    "social": "news",
    "news": "news",
}

_ARCH_PATTERNS = [
    ("research", re.compile(
        r"\b(paper|preprint|study|benchmark|dataset|researchers?|scientists?|"
        r"labs?|experiment|evaluation|ablation|state.of.the.art|sota|"
        r"breakthrough|scaling law|training run|fine.tun|reasoning|"
        r"arxiv|neurips|icml|iclr|cvpr|acl|emnlp|corl|iros|icra)\b"
    )),
    ("funding", re.compile(
        r"\b(raises?|raised|funding round|series [a-e]|valuation|invests?|"
        r"investment|acquires?|acquisition|merger|ipo|earnings|revenue|"
        r"backed by|led by|capital|stake|buyout)\b"
    )),
    ("policy", re.compile(
        r"\b(regulat|legislation|bill|law|lawsuit|antitrust|copyright|"
        r"privacy|safety|standard|standards|ban|bans|govern|senate|congress|"
        r"parliament|european commission|ftc|eu ai act|executive order|"
        r"compliance|audit|liability)\w*\b"
    )),
    ("deployment", re.compile(
        r"\b(deploy|deployed|deployment|rollout|roll out|pilot|installed|"
        r"factory|warehouse|hospital|farm|field|fleet|production line|"
        r"commercial|in production|at scale|customers?|shipping now)\w*\b"
    )),
    ("product", re.compile(
        r"\b(launch(?:es|ed)?|unveil(?:s|ed)?|introduc\w*|releas(?:e|es|ed)|"
        r"ships?|shipping|available|new model|new version|update|upgrade|"
        r"api|app store|mobile app|platform|feature|tool|product|robot|"
        r"humanoid|chip|gpu)\b"
    )),
    ("business", re.compile(
        r"\b(layoffs?|partnership|sponsor|shuts? down|shutdown|bankruptcy|"
        r"restructur|hire|hiring|ceo|executive|joint venture|contract)\w*\b"
    )),
]
_SCORE_RE = re.compile(r"(?<![\d-])([0-5])\s*[-:]\s*([0-5])(?![\d-])")


def infer_archetype(item: RawItem) -> str:
    explicit = ARCHETYPE_BY_KIND.get(item.kind)
    if explicit and item.kind not in {"news", "social"}:
        return explicit
    hay = f"{item.title} {item.summary[:400]}".lower()
    for archetype, pattern in _ARCH_PATTERNS:
        if pattern.search(hay):
            return archetype
    return explicit or "news"


def _score_conflict(a: str, b: str) -> bool:
    scores_a = set(_SCORE_RE.findall(a or ""))
    scores_b = set(_SCORE_RE.findall(b or ""))
    return bool(scores_a and scores_b and scores_a.isdisjoint(scores_b))


def _title_tokens(title: str) -> set[str]:
    return set(tokenize(title))


def _cluster_entities(conn: sqlite3.Connection, cluster_id: int) -> set[int]:
    rows = conn.execute(
        """SELECT DISTINCT ie.entity_id FROM item_entities ie
           WHERE ie.item_id IN (SELECT id FROM items WHERE cluster_id=?)""",
        (cluster_id,),
    ).fetchall()
    return {int(r["entity_id"]) for r in rows}


def _candidates(conn: sqlite3.Connection, account: str, since_ts: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT id, simhash, canonical_title, item_count, source_count,
                  first_seen_ts, last_seen_ts, archetype
           FROM clusters WHERE account=? AND last_seen_ts >= ?
           ORDER BY last_seen_ts DESC LIMIT 4000""",
        (account, since_ts),
    ).fetchall()


def assign_cluster(
    conn: sqlite3.Connection,
    account: str,
    item_id: int,
    item: RawItem,
    entity_ids: list[int],
    common_keys: set[str] | None = None,
) -> tuple[int, bool]:
    text = f"{item.title} {item.summary}"
    sketch = simhash64(text)
    tokens = _title_tokens(item.title)
    published = item.published_ts or now_ts()
    entity_set = set(entity_ids)
    proper = proper_tokens(item.title)
    common = common_keys or set()
    best: tuple[int, float] | None = None
    token_cache: dict[str, tuple[set[str], set[str]]] = {}

    def cached(title: str) -> tuple[set[str], set[str]]:
        if title not in token_cache:
            token_cache[title] = (_title_tokens(title), proper_tokens(title))
        return token_cache[title]

    for row in _candidates(conn, account, published - WINDOW_S):
        if _score_conflict(item.title, row["canonical_title"]):
            continue
        distance = hamming(sketch, row["simhash"])
        if distance <= 4:
            best = (int(row["id"]), 1.0 - distance / 64)
            break
        other_tokens, other_proper = cached(row["canonical_title"])
        similarity = jaccard(tokens, other_tokens)
        overlap = len(entity_set & _cluster_entities(conn, int(row["id"])))
        shared_proper = proper & other_proper
        distinctive = {t for t in shared_proper - common - GENERIC_PROPER if len(t) >= 4}
        if (
            (overlap >= 2 and similarity >= 0.34)
            or similarity >= 0.62
            or (distinctive and similarity >= 0.48)
        ):
            score = similarity + overlap * 0.05 + (0.1 if shared_proper else 0)
            if best is None or score > best[1]:
                best = (int(row["id"]), score)

    if best is None:
        archetype = infer_archetype(item)
        cur = conn.execute(
            """INSERT INTO clusters
               (account, canonical_title, canonical_url, first_seen_ts, last_seen_ts,
                item_count, source_count, simhash, archetype)
               VALUES(?,?,?,?,?,1,1,?,?)""",
            (account, item.title, canonical_url(item.url), published, published, sketch, archetype),
        )
        cluster_id = int(cur.lastrowid or 0)
        conn.execute("UPDATE items SET cluster_id=? WHERE id=?", (cluster_id, item_id))
        return cluster_id, True

    cluster_id = best[0]
    conn.execute("UPDATE items SET cluster_id=? WHERE id=?", (cluster_id, item_id))
    new_archetype = infer_archetype(item)
    current = conn.execute(
        "SELECT archetype, canonical_title FROM clusters WHERE id=?", (cluster_id,)
    ).fetchone()
    if current:
        current_arch = str(current["archetype"] or "news")
        if current_arch in {"news", "tournament"} and new_archetype in {
            "match", "roster", "patch", "business"
        }:
            if new_archetype == "match" and _SCORE_RE.search(item.title) and not _SCORE_RE.search(
                str(current["canonical_title"] or "")
            ):
                conn.execute(
                    """UPDATE clusters SET archetype=?, canonical_title=?, canonical_url=?,
                       simhash=? WHERE id=?""",
                    (
                        new_archetype,
                        item.title,
                        canonical_url(item.url),
                        sketch,
                        cluster_id,
                    ),
                )
            else:
                conn.execute(
                    "UPDATE clusters SET archetype=? WHERE id=?", (new_archetype, cluster_id)
                )
    conn.execute(
        """UPDATE clusters SET
             last_seen_ts = MAX(last_seen_ts, ?),
             first_seen_ts = MIN(first_seen_ts, ?),
             item_count = (SELECT COUNT(*) FROM items WHERE cluster_id=?),
             source_count = (SELECT COUNT(DISTINCT source) FROM items WHERE cluster_id=?)
           WHERE id=?""",
        (published, published, cluster_id, cluster_id, cluster_id),
    )
    return cluster_id, False


def ingest_items(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    matcher: EntityMatcher,
    items: list[RawItem],
    relevance: RelevanceMatcher | None = None,
) -> tuple[int, int]:
    new_items = 0
    new_clusters = 0
    common_keys = {key for key, _, _ in matcher.index}
    relevance = relevance or RelevanceMatcher(cfg)
    source_games = {
        source.name: str(source.options.get("game") or "")
        for source in cfg.sources
    }
    cutoff = now_ts() - int(cfg.poll.catchup_hours * 3600) if cfg.poll.catchup_hours else 0
    for item in items:
        if cutoff and item.published_ts and item.published_ts < cutoff:
            continue
        if not relevance.keep(item):
            continue
        item_id = insert_item(conn, item)
        if item_id is None:
            continue
        new_items += 1
        matches = matcher.match(f"{item.title} {item.summary} {item.body}")
        default_game = str(item.extra.get("game") or source_games.get(item.source) or "").strip()
        if default_game and not any(kind == "game" for _, _, kind in matches):
            matches.append((default_game.lower(), default_game, "game"))
        entity_ids = ensure_entities(conn, item_id, matches)
        _, created = assign_cluster(conn, cfg.account, item_id, item, entity_ids, common_keys)
        if created:
            new_clusters += 1
    conn.commit()
    return new_items, new_clusters
