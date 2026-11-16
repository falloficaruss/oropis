from __future__ import annotations

from agg.config import AccountCfg
from agg.db import connect
from agg.text import now_ts, simhash64
from agg.topics import compute_topics


def cfg() -> AccountCfg:
    return AccountCfg(account="test", watchlist={"hardware": ["Switch 2"], "tickers": ["META"]})


def add(
    conn,
    cid: int,
    title: str,
    source: str,
    age_s: int,
    entities: tuple[str, ...] = (),
) -> None:
    ts = now_ts() - age_s
    conn.execute(
        """INSERT INTO items(id, source, kind, guid, title, summary, published_ts,
                             fetched_ts, cluster_id)
           VALUES(?,?,?,?,?,'',?,?,?)""",
        (cid, source, "news", f"g{cid}", title, ts, ts, cid),
    )
    conn.execute(
        """INSERT INTO clusters(id, account, canonical_title, first_seen_ts, last_seen_ts,
                                item_count, source_count, simhash, score, archetype)
           VALUES(?,?,?,?,?,1,1,?,0,'news')""",
        (cid, "test", title, ts, ts, simhash64(title)),
    )
    for name in entities:
        conn.execute("INSERT OR IGNORE INTO entities(name, kind) VALUES(?, 'x')", (name,))
        row = conn.execute("SELECT id FROM entities WHERE name=?", (name,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO item_entities(item_id, entity_id) VALUES(?,?)",
            (cid, row["id"]),
        )
    conn.commit()


def test_topic_requires_multiple_sources():
    c = cfg()
    conn = connect(":memory:")
    add(conn, 1, "Nintendo Switch 2 price revealed", "a", 60, ("Nintendo", "Switch 2"))
    add(conn, 2, "Nintendo Switch 2 launch lineup grows", "b", 120, ("Nintendo", "Switch 2"))
    add(conn, 3, "Capcom teases a new Mega Man", "c", 180, ("Capcom",))
    topics = compute_topics(conn, c, since_h=24, min_df=2, min_sources=2, limit=10)
    labels = {t.label.lower() for t in topics}
    assert any("nintendo" in label or "switch" in label for label in labels)


def test_single_source_topic_is_excluded():
    c = cfg()
    conn = connect(":memory:")
    add(conn, 1, "Nintendo Switch 2 price revealed", "a", 60, ("Nintendo", "Switch 2"))
    add(conn, 2, "Nintendo Switch 2 launch lineup grows", "a", 120, ("Nintendo", "Switch 2"))
    assert compute_topics(conn, c, since_h=24, min_df=2, min_sources=2) == []


def test_case_variants_merge():
    c = cfg()
    conn = connect(":memory:")
    add(conn, 1, "META reports record quarterly revenue", "a", 60, ("META",))
    add(conn, 2, "Meta unveils a new VR headset", "b", 120, ("META",))
    add(conn, 3, "Meta hit with EU antitrust fine", "c", 180, ("META",))
    topics = compute_topics(conn, c, since_h=24, min_df=2, min_sources=2)
    meta = [t for t in topics if t.label.lower() == "meta"]
    assert len(meta) == 1
    assert meta[0].df == 3


def test_burst_prefers_recent():
    c = cfg()
    conn = connect(":memory:")
    for i in range(3):
        add(conn, 10 + i, f"Switch 2 retro story {i}", f"old{i}", 3600 * 20, ("Switch 2",))
    for i in range(3):
        add(conn, 20 + i, f"Switch 2 breaking story {i}", f"new{i}", 600, ("Switch 2",))
    topics = compute_topics(conn, c, since_h=24, min_df=2, min_sources=2)
    assert topics
    assert topics[0].label.lower() == "switch 2"
    assert topics[0].burst > 1.0


def test_sparkline_length():
    c = cfg()
    conn = connect(":memory:")
    add(conn, 1, "Switch 2 one", "a", 60, ("Switch 2",))
    add(conn, 2, "Switch 2 two", "b", 120, ("Switch 2",))
    topics = compute_topics(conn, c, since_h=24, min_df=2, min_sources=2, spark_hours=24)
    assert topics and len(topics[0].hourly) == 24
