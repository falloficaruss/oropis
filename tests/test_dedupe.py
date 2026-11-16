from __future__ import annotations

from agg.config import AccountCfg
from agg.db import connect
from agg.dedupe import ingest_items
from agg.entities import EntityMatcher
from agg.models import RawItem
from agg.text import now_ts


def make_cfg() -> AccountCfg:
    return AccountCfg(
        account="test",
        watchlist={
            "beats": ["AI", "Robotics"],
            "hardware": ["GPU", "humanoid robot"],
            "publishers": ["OpenAI", "Figure", "Waymo", "Unitree"],
        },
    )


def item(source: str, guid: str, title: str, summary: str = "", ts: int | None = None) -> RawItem:
    return RawItem(
        source=source,
        kind="news",
        guid=guid,
        title=title,
        summary=summary,
        published_ts=ts or now_ts(),
    )


def test_syndicated_story_becomes_one_cluster():
    cfg = make_cfg()
    conn = connect(":memory:")
    matcher = EntityMatcher(cfg)
    ts = now_ts()
    items = [
        item("a", "1", "OpenAI releases GPT-5.5 with improved reasoning", ts=ts),
        item("b", "2", "OpenAI releases GPT-5.5 with improved reasoning", ts=ts),
        item("c", "3", "OpenAI releases GPT-5.5 with improved reasoning", ts=ts),
    ]
    new_items, new_clusters = ingest_items(conn, cfg, matcher, items)
    assert new_items == 3
    assert new_clusters == 1
    row = conn.execute("SELECT * FROM clusters").fetchone()
    assert row["item_count"] == 3
    assert row["source_count"] == 3


def test_different_stories_do_not_merge():
    cfg = make_cfg()
    conn = connect(":memory:")
    matcher = EntityMatcher(cfg)
    ts = now_ts()
    items = [
        item("a", "1", "OpenAI releases GPT-5.5", ts=ts),
        item("b", "2", "OpenAI delays GPT-5.5 to 2026", ts=ts),
        item("c", "3", "Figure unveils a new humanoid robot", ts=ts),
    ]
    _, new_clusters = ingest_items(conn, cfg, matcher, items)
    assert new_clusters == 3


def test_reingest_is_idempotent():
    cfg = make_cfg()
    conn = connect(":memory:")
    matcher = EntityMatcher(cfg)
    items = [item("a", "1", "Waymo expands robotaxi service to Austin")]
    first = ingest_items(conn, cfg, matcher, items)
    second = ingest_items(conn, cfg, matcher, items)
    assert first == (1, 1)
    assert second == (0, 0)


def test_rewritten_duplicate_merges_on_distinctive_noun():
    cfg = make_cfg()
    conn = connect(":memory:")
    matcher = EntityMatcher(cfg)
    ts = now_ts()
    items = [
        item("a", "1", "Unitree G1 humanoid robot goes on sale", ts=ts),
        item("b", "2", "Unitree G1 humanoid robot is now on sale", ts=ts),
    ]
    _, new_clusters = ingest_items(conn, cfg, matcher, items)
    assert new_clusters == 1
