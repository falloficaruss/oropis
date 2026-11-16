from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import RawItem
from .text import canonical_url, now_ts

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS sources (
    name TEXT PRIMARY KEY,
    account TEXT NOT NULL,
    kind TEXT NOT NULL,
    url TEXT,
    tier INTEGER DEFAULT 1,
    interval_s INTEGER,
    enabled INTEGER DEFAULT 1,
    authority REAL DEFAULT 0.5,
    last_seen_ts INTEGER,
    last_ok_ts INTEGER,
    fail_count INTEGER DEFAULT 0,
    etag TEXT,
    last_modified TEXT,
    last_error TEXT,
    last_item_ts INTEGER
);

CREATE TABLE IF NOT EXISTS apps (
    appid TEXT PRIMARY KEY,
    name TEXT,
    updated_ts INTEGER
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    guid TEXT NOT NULL,
    url TEXT,
    url_canonical TEXT,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    body TEXT DEFAULT '',
    author TEXT,
    published_ts INTEGER,
    fetched_ts INTEGER NOT NULL,
    media_json TEXT DEFAULT '[]',
    extra_json TEXT DEFAULT '{}',
    cluster_id INTEGER,
    UNIQUE(source, guid)
);
CREATE INDEX IF NOT EXISTS idx_items_pub ON items(published_ts DESC);
CREATE INDEX IF NOT EXISTS idx_items_cluster ON items(cluster_id);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT NOT NULL,
    canonical_title TEXT NOT NULL,
    canonical_url TEXT,
    first_seen_ts INTEGER NOT NULL,
    last_seen_ts INTEGER NOT NULL,
    item_count INTEGER DEFAULT 1,
    source_count INTEGER DEFAULT 1,
    simhash TEXT NOT NULL,
    score REAL DEFAULT 0,
    archetype TEXT DEFAULT 'news'
);
CREATE INDEX IF NOT EXISTS idx_clusters_window ON clusters(account, last_seen_ts DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_score ON clusters(account, score DESC);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    UNIQUE(name, kind)
);

CREATE TABLE IF NOT EXISTS item_entities (
    item_id INTEGER NOT NULL,
    entity_id INTEGER NOT NULL,
    PRIMARY KEY (item_id, entity_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER,
    account TEXT,
    archetype TEXT,
    text TEXT,
    posted_ts INTEGER,
    tweet_id TEXT,
    impressions INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,
    bookmarks INTEGER DEFAULT 0,
    follows INTEGER DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    title, summary, body, content='items', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, title, summary, body)
    VALUES (new.id, new.title, new.summary, new.body);
END;
CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, summary, body)
    VALUES ('delete', old.id, old.title, old.summary, old.body);
END;
CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, title, summary, body)
    VALUES ('delete', old.id, old.title, old.summary, old.body);
    INSERT INTO items_fts(rowid, title, summary, body)
    VALUES (new.id, new.title, new.summary, new.body);
END;

CREATE TABLE IF NOT EXISTS telegram_notifications (
    cluster_id INTEGER PRIMARY KEY,
    account TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_ts INTEGER,
    message_id INTEGER,
    score REAL,
    source_count INTEGER,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_telegram_account_sent
    ON telegram_notifications(account, sent_ts DESC);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_ts INTEGER NOT NULL,
    finished_ts INTEGER,
    fetched INTEGER DEFAULT 0,
    new_items INTEGER DEFAULT 0,
    new_clusters INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def meta_get(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def upsert_source(conn: sqlite3.Connection, account: str, source) -> None:
    conn.execute(
        """INSERT INTO sources(name, account, kind, url, tier, interval_s, enabled, authority)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(name) DO UPDATE SET
             account=excluded.account, kind=excluded.kind, url=excluded.url,
             tier=excluded.tier, interval_s=excluded.interval_s,
             enabled=excluded.enabled, authority=excluded.authority""",
        (source.name, account, source.kind, source.url, source.tier,
         source.interval_s, int(source.enabled), source.authority),
    )
    conn.commit()


def insert_item(conn: sqlite3.Connection, item: RawItem) -> int | None:
    now = now_ts()
    cur = conn.execute(
        """INSERT OR IGNORE INTO items
           (source, kind, guid, url, url_canonical, title, summary, body,
            author, published_ts, fetched_ts, media_json, extra_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item.source, item.kind, item.guid, item.url, canonical_url(item.url),
            item.title, item.summary, item.body, item.author,
            item.published_ts or now, now,
            json.dumps(item.media, ensure_ascii=False),
            json.dumps(item.extra, ensure_ascii=False),
        ),
    )
    if cur.rowcount == 0 or cur.lastrowid is None:
        return None
    return int(cur.lastrowid)


def item_row(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()


def cluster_row(conn: sqlite3.Connection, cluster_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM clusters WHERE id=?", (cluster_id,)).fetchone()


def cluster_items(conn: sqlite3.Connection, cluster_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT i.*, s.authority, s.tier FROM items i
           LEFT JOIN sources s ON s.name = i.source
           WHERE i.cluster_id=? ORDER BY i.published_ts ASC""",
        (cluster_id,),
    ).fetchall()


def recent_clusters(
    conn: sqlite3.Connection, account: str, since_ts: int, limit: int = 200
) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT * FROM clusters
           WHERE account=? AND last_seen_ts >= ?
           ORDER BY score DESC, last_seen_ts DESC LIMIT ?""",
        (account, since_ts, limit),
    ).fetchall()


def get_app_name(conn: sqlite3.Connection, appid: str) -> str | None:
    row = conn.execute("SELECT name FROM apps WHERE appid=?", (str(appid),)).fetchone()
    return row["name"] if row else None


def set_app_name(conn: sqlite3.Connection, appid: str, name: str) -> None:
    conn.execute(
        "INSERT INTO apps(appid, name, updated_ts) VALUES(?,?,?) "
        "ON CONFLICT(appid) DO UPDATE SET name=excluded.name, updated_ts=excluded.updated_ts",
        (str(appid), name, now_ts()),
    )
