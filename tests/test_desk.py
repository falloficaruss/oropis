from __future__ import annotations

from pathlib import Path

from agg.config import AccountCfg, load_account
from agg.db import connect
from agg.dedupe import infer_archetype
from agg.entities import EntityMatcher
from agg.models import RawItem
from agg.relevance import RelevanceMatcher
from agg.telegram import format_cluster
from agg.text import now_ts


ROOT = Path(__file__).parents[1]


def test_oropis_config_has_the_new_desk():
    cfg = load_account(ROOT / "oropis" / "config.yaml")
    names = [source.name for source in cfg.sources]

    assert cfg.account == "oropis"
    assert cfg.watchlist["beats"] == ["AI", "Robotics"]
    assert set(cfg.beat_aliases) == {"AI", "Robotics"}
    assert sum(name.startswith("ai_") for name in names) == 25
    assert sum(name.startswith("robotics_") for name in names) == 25
    assert len([name for name in names if name.startswith("google_news_")]) == 4
    assert not any("pubg" in name or "codm" in name or "liquipedia" in name for name in names)


def test_relevance_keeps_ai_and_robotics_and_drops_esports():
    cfg = load_account(ROOT / "oropis" / "config.yaml")
    matcher = RelevanceMatcher(cfg)

    assert matcher.keep(RawItem(source="wire", kind="news", guid="1", title="OpenAI releases a new reasoning model"))
    assert matcher.keep(RawItem(source="wire", kind="news", guid="2", title="Waymo expands its robotaxi service"))
    assert not matcher.keep(RawItem(source="wire", kind="news", guid="3", title="BGMI finals recap"))


def test_beat_aliases_resolve_to_canonical_beats():
    cfg = AccountCfg(
        account="test",
        watchlist={"beats": ["AI", "Robotics"]},
        beat_aliases={
            "AI": ["LLM", "ChatGPT"],
            "Robotics": ["humanoid", "robotaxi"],
        },
    )
    matcher = EntityMatcher(cfg)

    matches = matcher.match("A new LLM is powering a humanoid robotaxi")

    assert ("AI", "beat") in {(name, kind) for _, name, kind in matches}
    assert ("Robotics", "beat") in {(name, kind) for _, name, kind in matches}


def test_archetypes_cover_the_new_desk():
    assert infer_archetype(RawItem("x", "news", "1", "Researchers publish a new reasoning benchmark")) == "research"
    assert infer_archetype(RawItem("x", "news", "2", "Figure launches a new humanoid robot")) == "product"
    assert infer_archetype(RawItem("x", "news", "3", "Waymo deploys robotaxis across Austin")) == "deployment"
    assert infer_archetype(RawItem("x", "news", "4", "Figure raises $1B at a $39B valuation")) == "funding"
    assert infer_archetype(RawItem("x", "news", "5", "EU opens antitrust probe into AI licensing")) == "policy"
    assert infer_archetype(RawItem("x", "news", "6", "Robotics firm cuts staff in restructuring")) == "business"
    assert infer_archetype(RawItem("x", "news", "7", "Weekly robotics roundup")) == "news"


def test_telegram_label_uses_beat_entity():
    conn = connect(":memory:")
    ts = now_ts()
    cluster_id = conn.execute(
        """INSERT INTO clusters
             (account, canonical_title, canonical_url, first_seen_ts, last_seen_ts,
              item_count, source_count, simhash, score, archetype)
           VALUES('oropis', 'A new reasoning model ships', 'https://example.com/a',
                  ?, ?, 1, 1, '0000000000000000', 0.9, 'research')""",
        (ts, ts),
    ).lastrowid
    item_id = conn.execute(
        """INSERT INTO items
             (source, kind, guid, url, url_canonical, title, summary, published_ts, fetched_ts, cluster_id)
           VALUES('ai_openai', 'news', 'g1', 'https://example.com/a', 'https://example.com/a',
                  'A new reasoning model ships', '', ?, ?, ?)""",
        (ts, ts, cluster_id),
    ).lastrowid
    entity_id = conn.execute("INSERT INTO entities(name, kind) VALUES('AI', 'beat')").lastrowid
    conn.execute("INSERT INTO item_entities(item_id, entity_id) VALUES(?, ?)", (item_id, entity_id))
    conn.commit()

    row = conn.execute("SELECT * FROM clusters WHERE id=?", (cluster_id,)).fetchone()
    text = format_cluster(conn, AccountCfg(account="oropis"), row)

    assert "[AI · RESEARCH]" in text
    conn.close()
