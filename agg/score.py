from __future__ import annotations

import sqlite3

from .config import AccountCfg
from .text import now_ts


def _cluster_entity_counts(conn: sqlite3.Connection, account: str, since_ts: int) -> dict[int, int]:
    rows = conn.execute(
        """SELECT ie.entity_id AS eid, COUNT(DISTINCT i.cluster_id) AS n
           FROM items i
           JOIN item_entities ie ON ie.item_id = i.id
           JOIN clusters c ON c.id = i.cluster_id
           WHERE c.account=? AND c.last_seen_ts >= ?
           GROUP BY ie.entity_id""",
        (account, since_ts),
    ).fetchall()
    return {int(r["eid"]): int(r["n"]) for r in rows}


def rescore(conn: sqlite3.Connection, cfg: AccountCfg, window_h: float = 72.0) -> int:
    now = now_ts()
    since = now - int(window_h * 3600)
    rows = conn.execute(
        """SELECT c.id, c.first_seen_ts, c.last_seen_ts, c.source_count, c.item_count,
                  COALESCE((SELECT MAX(s.authority)
                            FROM items i JOIN sources s ON s.name = i.source
                            WHERE i.cluster_id = c.id), 0.5) AS authority,
                  (SELECT GROUP_CONCAT(DISTINCT ie.entity_id)
                   FROM items i JOIN item_entities ie ON ie.item_id = i.id
                   WHERE i.cluster_id = c.id) AS entity_ids
           FROM clusters c
           WHERE c.account=? AND c.last_seen_ts >= ?""",
        (cfg.account, since),
    ).fetchall()

    entity_counts = _cluster_entity_counts(conn, cfg.account, since)
    half_life = max(0.5, cfg.scoring.recency_half_life_h)
    updates: list[tuple[float, int]] = []

    for row in rows:
        age_h = max(0.0, (now - int(row["first_seen_ts"])) / 3600)
        recency = 0.5 ** (age_h / half_life)
        authority = float(row["authority"] or 0.5)
        entity_ids = [int(x) for x in (row["entity_ids"] or "").split(",") if x]
        watch = 1.0 if entity_ids else 0.0
        if entity_ids:
            shared = max(entity_counts.get(eid, 1) for eid in entity_ids)
            novelty = 1.0 - min(1.0, (shared - 1) / 5.0)
        else:
            novelty = 1.0
        velocity = min(1.0, (int(row["source_count"]) - 1) / 4.0)
        watch_weight = max(0.0, cfg.scoring.watchlist_boost)
        total_weight = 0.30 + 0.25 + watch_weight + 0.15 + 0.10
        score = (
            0.30 * authority
            + 0.25 * recency
            + watch_weight * watch
            + 0.15 * novelty
            + 0.10 * velocity
        ) / total_weight
        if int(row["source_count"]) <= 1:
            score -= cfg.scoring.single_source_penalty
        updates.append((round(max(0.0, score), 4), int(row["id"])))

    conn.executemany("UPDATE clusters SET score=? WHERE id=?", updates)
    conn.commit()
    return len(updates)
