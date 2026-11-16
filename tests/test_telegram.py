from __future__ import annotations

import asyncio
import sqlite3

import httpx
import pytest

from agg.config import AccountCfg, TelegramCfg
from agg.db import connect
from agg.telegram import (
    TelegramClient,
    TelegramError,
    format_cluster,
    process_pending,
    qualifies,
)
from agg.text import now_ts


def _db(tmp_path) -> sqlite3.Connection:
    conn = connect(tmp_path / "data.db")
    conn.execute(
        """INSERT INTO sources(name, account, kind, authority)
           VALUES('ai_openai', 'oropis', 'rss', 0.9)"""
    )
    conn.execute(
        """INSERT INTO clusters
             (account, canonical_title, canonical_url, first_seen_ts, last_seen_ts,
              item_count, source_count, simhash, score, archetype)
           VALUES('oropis', '5 < 6 & counting', 'https://example.com/a?x=1&y=2',
                  ?, ?, 1, 1, '0000000000000000', 0.66, 'news')""",
        (now_ts(), now_ts()),
    )
    cluster_id = conn.execute("SELECT MAX(id) FROM clusters").fetchone()[0]
    conn.execute(
        """INSERT INTO items
             (source, kind, guid, url, url_canonical, title, summary, fetched_ts, cluster_id)
           VALUES('ai_openai', 'news', 'g1', 'https://example.com/a?x=1&y=2',
                  'https://example.com/a?x=1&y=2', '5 < 6 & counting', '', ?, ?)""",
        (now_ts(), cluster_id),
    )
    conn.commit()
    return conn


def _cfg(**telegram) -> AccountCfg:
    return AccountCfg(account="oropis", telegram=TelegramCfg(**telegram))


def test_format_cluster_escapes_html_and_includes_cluster_id(tmp_path):
    conn = _db(tmp_path)
    row = conn.execute("SELECT * FROM clusters").fetchone()

    text = format_cluster(conn, _cfg(), row)

    assert "5 &lt; 6 &amp; counting" in text
    assert 'href="https://example.com/a?x=1&amp;y=2"' in text
    assert f"#{row['id']}" in text
    assert "ai_openai" in text
    conn.close()


def test_qualifies_uses_score_and_official_override():
    cfg = _cfg(min_score=0.55, official_min_score=0.45)
    row = {"score": 0.5, "last_seen_ts": now_ts()}

    assert qualifies(cfg, row, ["google_news_ai"], 0.65)[0] is False
    assert qualifies(cfg, row, ["ai_openai"], 0.9)[0] is True
    assert qualifies(cfg, {"score": 0.56, "last_seen_ts": now_ts()}, [], 0.0)[0] is True

    old = {"score": 0.9, "last_seen_ts": now_ts() - 8 * 3600}
    assert qualifies(cfg, old, ["ai_openai"], 0.9)[0] is False


def test_discovery_only_source_cannot_trigger_an_alert():
    cfg = _cfg(discovery_only_sources=["google_news"])
    row = {"score": 1.0, "last_seen_ts": now_ts()}
    assert qualifies(cfg, row, ["google_news"], 1.0) == (False, "discovery only")
    assert qualifies(cfg, row, ["google_news", "primary"], 1.0)[0] is True


def test_telegram_client_sends_and_does_not_leak_token():
    seen: list[httpx.Request] = []

    def ok_handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    async def run() -> int:
        client = httpx.AsyncClient(transport=httpx.MockTransport(ok_handler))
        tg = TelegramClient(_cfg(bot_token="SECRET_TOKEN", chat_id="123"), client=client)
        try:
            return await tg.send("hello")
        finally:
            await client.aclose()

    assert asyncio.run(run()) == 42
    assert len(seen) == 1
    assert seen[0].url.path.endswith("/sendMessage")

    def fail_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    async def fail() -> str:
        client = httpx.AsyncClient(transport=httpx.MockTransport(fail_handler))
        tg = TelegramClient(_cfg(bot_token="SECRET_TOKEN", chat_id="123"), client=client)
        try:
            with pytest.raises(TelegramError) as exc_info:
                await tg.send("hello")
            return str(exc_info.value)
        finally:
            await client.aclose()

    message = asyncio.run(fail())
    assert "SECRET_TOKEN" not in message
    assert "ConnectError" in message

    def unauthorized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"ok": False, "description": "Unauthorized"})

    async def fatal() -> TelegramError:
        client = httpx.AsyncClient(transport=httpx.MockTransport(unauthorized))
        tg = TelegramClient(_cfg(bot_token="SECRET_TOKEN", chat_id="123"), client=client)
        try:
            with pytest.raises(TelegramError) as exc_info:
                await tg.send("hello")
            return exc_info.value
        finally:
            await client.aclose()

    err = asyncio.run(fatal())
    assert err.fatal is True
    assert "SECRET_TOKEN" not in str(err)


class FakeTelegram:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, text: str) -> int:
        self.sent.append(text)
        return len(self.sent)


def _add_cluster(
    conn: sqlite3.Connection,
    *,
    first_seen: int,
    last_seen: int,
    title: str = "catch-up story",
) -> int:
    cur = conn.execute(
        """INSERT INTO clusters
             (account, canonical_title, canonical_url, first_seen_ts, last_seen_ts,
              item_count, source_count, simhash, score, archetype)
           VALUES('oropis', ?, 'https://example.com/c', ?, ?, 1, 1,
                  '1111111111111111', 0.9, 'news')""",
        (title, first_seen, last_seen),
    )
    conn.commit()
    return int(cur.lastrowid or 0)


def _set_meta(conn: sqlite3.Connection, key: str, value: int) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


def test_process_pending_replays_alerts_missed_while_offline(tmp_path):
    conn = _db(tmp_path)
    now = now_ts()
    first_id = conn.execute("SELECT MAX(id) FROM clusters").fetchone()[0]
    _set_meta(conn, "telegram_last_cluster_id", first_id)
    _set_meta(conn, "telegram_last_run_ts", now - 14 * 3600)
    _set_meta(conn, "last_poll_ts", now)

    cluster_id = _add_cluster(conn, first_seen=now - 13 * 3600, last_seen=now - 13 * 3600)
    fake = FakeTelegram()
    cfg = _cfg(min_score=0.0, max_age_h=12.0, backfill_minutes=30)

    stats = asyncio.run(process_pending(cfg, fake, conn, now=now))  # type: ignore[arg-type]

    assert stats["sent"] == 1
    assert len(fake.sent) == 1
    row = conn.execute(
        "SELECT status FROM telegram_notifications WHERE cluster_id=?", (cluster_id,)
    ).fetchone()
    assert row["status"] == "sent"
    assert conn.execute(
        "SELECT value FROM meta WHERE key='telegram_catchup_since_ts'"
    ).fetchone()[0] == "0"
    conn.close()


def test_catchup_stays_armed_until_the_poller_has_run(tmp_path):
    conn = _db(tmp_path)
    now = now_ts()
    first_id = conn.execute("SELECT MAX(id) FROM clusters").fetchone()[0]
    _set_meta(conn, "telegram_last_cluster_id", first_id)
    _set_meta(conn, "telegram_last_run_ts", now - 14 * 3600)
    _set_meta(conn, "last_poll_ts", now - 20 * 3600)

    fake = FakeTelegram()
    cfg = _cfg(min_score=0.0, max_age_h=12.0, backfill_minutes=30)

    asyncio.run(process_pending(cfg, fake, conn, now=now))  # type: ignore[arg-type]
    assert conn.execute(
        "SELECT value FROM meta WHERE key='telegram_catchup_armed_ts'"
    ).fetchone()[0] != "0"

    _set_meta(conn, "last_poll_ts", now)
    asyncio.run(process_pending(cfg, fake, conn, now=now + 1))  # type: ignore[arg-type]
    assert conn.execute(
        "SELECT value FROM meta WHERE key='telegram_catchup_armed_ts'"
    ).fetchone()[0] == "0"
    conn.close()


def test_process_pending_skips_old_alerts_when_online(tmp_path):
    conn = _db(tmp_path)
    now = now_ts()
    first_id = conn.execute("SELECT MAX(id) FROM clusters").fetchone()[0]
    _set_meta(conn, "telegram_last_cluster_id", first_id)
    _set_meta(conn, "telegram_last_run_ts", now - 60)

    cluster_id = _add_cluster(conn, first_seen=now - 13 * 3600, last_seen=now - 13 * 3600)
    fake = FakeTelegram()
    cfg = _cfg(min_score=0.0, max_age_h=12.0, backfill_minutes=30)

    stats = asyncio.run(process_pending(cfg, fake, conn, now=now))  # type: ignore[arg-type]

    assert stats == {"sent": 0, "skipped": 1, "failed": 0}
    assert fake.sent == []
    row = conn.execute(
        "SELECT status, error FROM telegram_notifications WHERE cluster_id=?", (cluster_id,)
    ).fetchone()
    assert row["status"] == "skipped"
    assert row["error"] == "too old"
    conn.close()


def test_rechecks_below_score_clusters_that_later_qualify(tmp_path):
    conn = _db(tmp_path)
    now = now_ts()
    cluster_id = conn.execute("SELECT MAX(id) FROM clusters").fetchone()[0]
    _set_meta(conn, "telegram_last_cluster_id", cluster_id)
    _set_meta(conn, "telegram_last_run_ts", now - 60)
    conn.execute("UPDATE clusters SET score=0.4 WHERE id=?", (cluster_id,))
    conn.execute(
        """INSERT INTO telegram_notifications
             (cluster_id, account, status, score, source_count, error)
           VALUES(?, 'oropis', 'skipped', 0.4, 1, 'below score')""",
        (cluster_id,),
    )
    conn.commit()
    fake = FakeTelegram()
    cfg = _cfg(min_score=0.0, max_age_h=12.0, backfill_minutes=30)

    stats = asyncio.run(process_pending(cfg, fake, conn, now=now))  # type: ignore[arg-type]

    assert stats["sent"] == 1
    assert len(fake.sent) == 1
    row = conn.execute(
        "SELECT status FROM telegram_notifications WHERE cluster_id=?", (cluster_id,)
    ).fetchone()
    assert row["status"] == "sent"
    conn.close()


def test_process_pending_is_idempotent(tmp_path):
    conn = _db(tmp_path)
    fake = FakeTelegram()
    cfg = _cfg(min_score=0.0, max_age_h=0)

    first = asyncio.run(process_pending(cfg, fake, conn))  # type: ignore[arg-type]
    second = asyncio.run(process_pending(cfg, fake, conn))  # type: ignore[arg-type]

    assert first["sent"] == 1
    assert second["sent"] == 0
    assert len(fake.sent) == 1
    assert conn.execute("SELECT COUNT(*) FROM telegram_notifications").fetchone()[0] == 1
    conn.close()
