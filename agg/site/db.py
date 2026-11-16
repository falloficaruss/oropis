from __future__ import annotations

import fcntl
import json
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from ..config import AccountCfg
from ..render import build_packet, domain
from ..text import now_ts, slug as make_slug, strip_html, truncate

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK(status IN ('new','draft','published','rejected','archived')),
    slug TEXT UNIQUE,
    headline TEXT NOT NULL DEFAULT '',
    dek TEXT NOT NULL DEFAULT '',
    body_md TEXT NOT NULL DEFAULT '',
    author TEXT NOT NULL DEFAULT 'OropisHQ',
    beat TEXT,
    archetype TEXT,
    format TEXT NOT NULL DEFAULT 'news',
    tags_json TEXT NOT NULL DEFAULT '[]',
    facts_json TEXT NOT NULL DEFAULT '{}',
    hero_url TEXT,
    hero_local TEXT,
    hero_credit TEXT,
    hero_alt TEXT,
    sources_json TEXT NOT NULL DEFAULT '[]',
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    x_post_url TEXT,
    score REAL NOT NULL DEFAULT 0,
    created_ts INTEGER NOT NULL,
    updated_ts INTEGER NOT NULL,
    published_ts INTEGER,
    exported_ts INTEGER,
    dirty INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_stories_status ON stories(status, score DESC);
CREATE INDEX IF NOT EXISTS idx_stories_published ON stories(status, published_ts DESC);
CREATE INDEX IF NOT EXISTS idx_stories_beat ON stories(beat);

CREATE TABLE IF NOT EXISTS story_slugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    is_current INTEGER NOT NULL DEFAULT 0,
    created_ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_story_slugs_story ON story_slugs(story_id);

CREATE TABLE IF NOT EXISTS story_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL,
    headline TEXT NOT NULL,
    dek TEXT NOT NULL,
    body_md TEXT NOT NULL,
    status TEXT NOT NULL,
    editor TEXT,
    created_ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revisions_story ON story_revisions(story_id, created_ts DESC);

CREATE TABLE IF NOT EXISTS story_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'inline' CHECK(kind IN ('inline')),
    path TEXT NOT NULL UNIQUE,
    alt TEXT NOT NULL DEFAULT '',
    caption TEXT NOT NULL DEFAULT '',
    credit TEXT NOT NULL DEFAULT '',
    original_name TEXT,
    mime TEXT,
    width INTEGER,
    height INTEGER,
    bytes INTEGER,
    created_ts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_story_media_story ON story_media(story_id, created_ts);

CREATE TABLE IF NOT EXISTS deployments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_ts INTEGER NOT NULL,
    finished_ts INTEGER,
    status TEXT NOT NULL,
    commit_sha TEXT,
    message TEXT,
    error TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS stories_fts USING fts5(
    headline, dek, body_md, content='stories', content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS stories_ai AFTER INSERT ON stories BEGIN
    INSERT INTO stories_fts(rowid, headline, dek, body_md)
    VALUES (new.id, new.headline, new.dek, new.body_md);
END;
CREATE TRIGGER IF NOT EXISTS stories_ad AFTER DELETE ON stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, headline, dek, body_md)
    VALUES ('delete', old.id, old.headline, old.dek, old.body_md);
END;
CREATE TRIGGER IF NOT EXISTS stories_au AFTER UPDATE ON stories BEGIN
    INSERT INTO stories_fts(stories_fts, rowid, headline, dek, body_md)
    VALUES ('delete', old.id, old.headline, old.dek, old.body_md);
    INSERT INTO stories_fts(rowid, headline, dek, body_md)
    VALUES (new.id, new.headline, new.dek, new.body_md);
END;
"""

SCHEMA_VERSION = 3

EDITABLE = {
    "headline", "dek", "body_md", "author", "beat", "archetype", "format",
    "tags_json", "facts_json", "hero_url", "hero_credit", "hero_alt",
    "x_post_url", "slug", "sources_json",
}


def is_manual_story(story: sqlite3.Row) -> bool:
    return int(story["cluster_id"] or 0) < 0


def _manual_cluster_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MIN(cluster_id) AS lowest FROM stories").fetchone()
    lowest = int(row["lowest"]) if row and row["lowest"] is not None else 0
    return min(lowest, 0) - 1


def create_story(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    *,
    headline: str,
    dek: str = "",
    body_md: str = "",
    author: str = "",
    beat: str = "",
    archetype: str = "news",
    format: str = "news",
) -> sqlite3.Row:
    headline = (headline or "").strip()
    if not headline:
        raise ValueError("headline is required")
    now = now_ts()
    cur = conn.execute(
        """INSERT INTO stories
           (cluster_id, status, headline, dek, body_md, author, beat, archetype,
            format, created_ts, updated_ts)
           VALUES(?, 'draft', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            _manual_cluster_id(conn),
            headline,
            (dek or "").strip(),
            body_md or "",
            (author or "").strip() or cfg.site.default_author,
            (beat or "").strip() or None,
            (archetype or "").strip() or "news",
            (format or "").strip() or "news",
            now,
            now,
        ),
    )
    conn.commit()
    story = get_story(conn, int(cur.lastrowid))
    assert story is not None
    return story


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(stories)")}
    if "beat" not in columns and "game" in columns:
        conn.execute("ALTER TABLE stories RENAME COLUMN game TO beat")
        columns.discard("game")
        columns.add("beat")
    if "hero_alt" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN hero_alt TEXT")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
    conn.commit()
    return conn


def agg_connection(cfg: AccountCfg) -> sqlite3.Connection:
    path = cfg.root / cfg.db
    if not path.exists():
        raise FileNotFoundError(f"aggregator database not found: {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def site_connection(cfg: AccountCfg) -> sqlite3.Connection:
    return connect(cfg.root / cfg.site.db)


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


def _beats_for(conn: sqlite3.Connection, cluster_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT DISTINCT e.name FROM items i
           JOIN item_entities ie ON ie.item_id=i.id
           JOIN entities e ON e.id=ie.entity_id
           WHERE i.cluster_id=? AND e.kind='beat' ORDER BY e.name""",
        (cluster_id,),
    ).fetchall()
    return [str(r["name"]) for r in rows]


def _sources_for(conn: sqlite3.Connection, cluster_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT source FROM items WHERE cluster_id=? ORDER BY source",
        (cluster_id,),
    ).fetchall()
    return [str(r["source"]) for r in rows]


def snapshot(conn: sqlite3.Connection, cfg: AccountCfg, story_id: int) -> dict[str, Any]:
    story = conn.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()
    if not story:
        raise ValueError(f"no story {story_id}")
    agg = agg_connection(cfg)
    try:
        cluster_id = int(story["cluster_id"])
        text, payload = build_packet(agg, cfg, cluster_id, include_related=False)
        cluster = agg.execute("SELECT * FROM clusters WHERE id=?", (cluster_id,)).fetchone()
        if not cluster:
            raise ValueError(f"no cluster {cluster_id}")
        beats = _beats_for(agg, cluster_id)
        sources: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for item in payload["items"]:
            url = item.get("url") or ""
            if url in seen_urls:
                continue
            seen_urls.add(url)
            extra = item.get("extra") or {}
            publisher = (
                extra.get("publisher")
                or extra.get("handle")
                or domain(url)
                or item.get("source")
            )
            sources.append(
                {
                    "name": item.get("source") or publisher,
                    "url": url,
                    "publisher": publisher,
                }
            )
        primary = payload["items"][0] if payload["items"] else {}
        extra = primary.get("extra") or {}
        facts: dict[str, Any] = {}
        for key in (
            "score1", "score2", "winner", "best_of", "tournament", "stage",
            "status", "start_ts", "patch", "app_name", "company", "form_type",
        ):
            if extra.get(key) not in (None, "", []):
                facts[key] = extra[key]
        if payload.get("numbers"):
            facts["numbers"] = payload["numbers"][:10]
        media = payload.get("media") or []
        hero = media[0] if media else None
        attribution = payload.get("attribution") or ""
        headline = strip_html(cluster["canonical_title"])
        dek = truncate(strip_html(primary.get("summary") or ""), 240)
        updates = {
            "headline": story["headline"] or headline,
            "dek": story["dek"] or dek,
            "beat": story["beat"] or (beats[0] if beats else None),
            "archetype": story["archetype"] or cluster["archetype"],
            "score": float(cluster["score"] or 0),
            "sources_json": json.dumps(sources, ensure_ascii=False),
            "snapshot_json": json.dumps(
                {
                    "cluster": dict(cluster),
                    "payload": payload,
                    "packet": text,
                    "beats": beats,
                    "sources": sources,
                },
                ensure_ascii=False,
                default=str,
            ),
            "facts_json": story["facts_json"]
            if story["facts_json"] not in ("", "{}")
            else json.dumps(facts, ensure_ascii=False),
            "hero_url": story["hero_url"] or hero,
            "hero_credit": story["hero_credit"] or attribution,
            "updated_ts": now_ts(),
        }
        assignments = ", ".join(f"{key}=?" for key in updates)
        conn.execute(
            f"UPDATE stories SET {assignments} WHERE id=?",
            (*updates.values(), story_id),
        )
        conn.commit()
        return updates
    finally:
        agg.close()


def sync(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    since_h: float = 72,
    min_score: float | None = None,
    limit: int = 300,
) -> int:
    since = now_ts() - int(since_h * 3600)
    min_score = cfg.site.min_draft_score if min_score is None else min_score
    covered_beats = [
        name.strip() for name in cfg.watchlist.get("beats", []) if name.strip()
    ]
    for name in cfg.beat_aliases:
        name = name.strip()
        if name and name not in covered_beats:
            covered_beats.append(name)
    beat_filter = ""
    params: list[Any] = [cfg.account, since, min_score]
    if covered_beats:
        placeholders = ",".join("?" for _ in covered_beats)
        beat_filter = f"""
                 AND EXISTS (
                     SELECT 1 FROM items gi
                       JOIN item_entities gie ON gie.item_id=gi.id
                       JOIN entities ge ON ge.id=gie.entity_id
                      WHERE gi.cluster_id=c.id AND ge.kind='beat'
                        AND lower(ge.name) IN ({placeholders})
                 )"""
        params.extend(name.lower() for name in covered_beats)
    params.append(limit)
    agg = agg_connection(cfg)
    try:
        rows = agg.execute(
            f"""SELECT c.*,
                       (SELECT GROUP_CONCAT(DISTINCT e.name) FROM items i
                          JOIN item_entities ie ON ie.item_id=i.id
                          JOIN entities e ON e.id=ie.entity_id
                         WHERE i.cluster_id=c.id AND e.kind='beat') AS beat_names
                FROM clusters c
                WHERE c.account=? AND c.last_seen_ts>=? AND c.score>=?{beat_filter}
                ORDER BY c.score DESC, c.last_seen_ts DESC LIMIT ?""",
            tuple(params),
        ).fetchall()
        existing = {
            int(r["cluster_id"])
            for r in conn.execute("SELECT cluster_id FROM stories").fetchall()
        }
        added = 0
        now = now_ts()
        for row in rows:
            cluster_id = int(row["id"])
            if cluster_id in existing:
                continue
            beat = (row["beat_names"] or "").split(",")[0] or None
            conn.execute(
                """INSERT OR IGNORE INTO stories
                   (cluster_id, status, headline, author, beat, archetype, score,
                    created_ts, updated_ts)
                   VALUES(?, 'new', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cluster_id,
                    strip_html(row["canonical_title"]),
                    cfg.site.default_author,
                    beat,
                    row["archetype"],
                    float(row["score"] or 0),
                    now,
                    now,
                ),
            )
            added += 1
        conn.commit()
        return added
    finally:
        agg.close()


def get_story(conn: sqlite3.Connection, story_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()


def story_media(conn: sqlite3.Connection, story_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM story_media WHERE story_id=? ORDER BY created_ts, id",
        (story_id,),
    ).fetchall()


def get_story_media(conn: sqlite3.Connection, media_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM story_media WHERE id=?", (media_id,)).fetchone()


def add_story_media(
    conn: sqlite3.Connection,
    story_id: int,
    *,
    path: str,
    alt: str = "",
    caption: str = "",
    credit: str = "",
    original_name: str | None = None,
    mime: str | None = None,
    width: int | None = None,
    height: int | None = None,
    bytes_: int | None = None,
) -> sqlite3.Row:
    cur = conn.execute(
        """INSERT INTO story_media
           (story_id, kind, path, alt, caption, credit, original_name, mime,
            width, height, bytes, created_ts)
           VALUES (?, 'inline', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            story_id,
            path,
            alt,
            caption,
            credit,
            original_name,
            mime,
            width,
            height,
            bytes_,
            now_ts(),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM story_media WHERE id=?", (cur.lastrowid,)).fetchone()
    assert row is not None
    return row


def delete_story_media(conn: sqlite3.Connection, media_id: int) -> None:
    conn.execute("DELETE FROM story_media WHERE id=?", (media_id,))
    conn.commit()


def mark_story_dirty(conn: sqlite3.Connection, story_id: int) -> None:
    conn.execute(
        "UPDATE stories SET dirty=CASE WHEN status='published' THEN 1 ELSE dirty END, "
        "updated_ts=? WHERE id=?",
        (now_ts(), story_id),
    )
    conn.commit()


def queue_rows(
    conn: sqlite3.Connection,
    statuses: tuple[str, ...] = ("new", "draft"),
    beat: str | None = None,
    archetype: str | None = None,
    limit: int = 200,
) -> list[sqlite3.Row]:
    marks = ",".join("?" for _ in statuses)
    sql = f"SELECT * FROM stories WHERE status IN ({marks})"
    params: list[Any] = [*statuses]
    if beat:
        sql += " AND lower(beat)=lower(?)"
        params.append(beat)
    if archetype:
        sql += " AND archetype=?"
        params.append(archetype)
    sql += " ORDER BY created_ts DESC, id DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def _unique_slug(conn: sqlite3.Connection, base: str, story_id: int) -> str:
    candidate = make_slug(base, 70)
    n = 2
    while True:
        row = conn.execute(
            "SELECT story_id FROM story_slugs WHERE slug=?", (candidate,)
        ).fetchone()
        if not row or int(row["story_id"]) == story_id:
            return candidate
        candidate = f"{make_slug(base, 64)}-{n}"
        n += 1


def set_slug(conn: sqlite3.Connection, story_id: int, value: str) -> str:
    candidate = _unique_slug(conn, value or "story", story_id)
    now = now_ts()
    conn.execute(
        "UPDATE story_slugs SET is_current=0 WHERE story_id=?", (story_id,)
    )
    conn.execute(
        "INSERT INTO story_slugs(story_id, slug, is_current, created_ts) "
        "VALUES(?, ?, 1, ?) ON CONFLICT(slug) DO UPDATE SET "
        "story_id=excluded.story_id, is_current=1",
        (story_id, candidate, now),
    )
    conn.execute("UPDATE stories SET slug=? WHERE id=?", (candidate, story_id))
    return candidate


def _revision(conn: sqlite3.Connection, story: sqlite3.Row, editor: str) -> None:
    conn.execute(
        """INSERT INTO story_revisions
           (story_id, headline, dek, body_md, status, editor, created_ts)
           VALUES(?,?,?,?,?,?,?)""",
        (
            story["id"], story["headline"], story["dek"], story["body_md"],
            story["status"], editor, now_ts(),
        ),
    )


def save_story(
    conn: sqlite3.Connection,
    story_id: int,
    fields: dict[str, Any],
    editor: str = "admin",
) -> sqlite3.Row:
    story = get_story(conn, story_id)
    if not story:
        raise ValueError(f"no story {story_id}")
    updates = {k: v for k, v in fields.items() if k in EDITABLE}
    if "slug" in updates:
        set_slug(conn, story_id, str(updates.pop("slug")))
    if updates:
        updates["updated_ts"] = now_ts()
        assignments = ", ".join(f"{key}=?" for key in updates)
        conn.execute(
            f"UPDATE stories SET {assignments} WHERE id=?",
            (*updates.values(), story_id),
        )
    story = get_story(conn, story_id)
    assert story is not None
    _revision(conn, story, editor)
    if story["status"] == "published":
        conn.execute("UPDATE stories SET dirty=1 WHERE id=?", (story_id,))
    conn.commit()
    return get_story(conn, story_id)  # type: ignore[return-value]


def publish_story(conn: sqlite3.Connection, story_id: int, editor: str = "admin") -> sqlite3.Row:
    story = get_story(conn, story_id)
    if not story:
        raise ValueError(f"no story {story_id}")
    if not (story["headline"] or "").strip():
        raise ValueError("headline is required")
    if not (story["body_md"] or "").strip():
        raise ValueError("body is required")
    if not json.loads(story["sources_json"] or "[]"):
        raise ValueError("at least one source is required")
    if not story["slug"]:
        set_slug(conn, story_id, story["headline"])
    now = now_ts()
    conn.execute(
        """UPDATE stories SET status='published', published_ts=COALESCE(published_ts, ?),
           updated_ts=?, dirty=1 WHERE id=?""",
        (now, now, story_id),
    )
    story = get_story(conn, story_id)
    assert story is not None
    _revision(conn, story, editor)
    conn.commit()
    return get_story(conn, story_id)  # type: ignore[return-value]


def unpublish_story(conn: sqlite3.Connection, story_id: int, editor: str = "admin") -> sqlite3.Row:
    story = get_story(conn, story_id)
    if not story:
        raise ValueError(f"no story {story_id}")
    conn.execute(
        "UPDATE stories SET status='draft', published_ts=NULL, updated_ts=?, dirty=1 WHERE id=?",
        (now_ts(), story_id),
    )
    story = get_story(conn, story_id)
    assert story is not None
    _revision(conn, story, editor)
    conn.commit()
    return get_story(conn, story_id)  # type: ignore[return-value]


def reject_story(conn: sqlite3.Connection, story_id: int, editor: str = "admin") -> sqlite3.Row:
    story = get_story(conn, story_id)
    if not story:
        raise ValueError(f"no story {story_id}")
    conn.execute(
        "UPDATE stories SET status='rejected', updated_ts=?, dirty=1 WHERE id=?",
        (now_ts(), story_id),
    )
    story = get_story(conn, story_id)
    assert story is not None
    _revision(conn, story, editor)
    conn.commit()
    return get_story(conn, story_id)  # type: ignore[return-value]


def revisions(conn: sqlite3.Connection, story_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM story_revisions WHERE story_id=? ORDER BY created_ts DESC, id DESC",
        (story_id,),
    ).fetchall()


def restore_revision(conn: sqlite3.Connection, story_id: int, revision_id: int, editor: str) -> None:
    row = conn.execute(
        "SELECT * FROM story_revisions WHERE id=? AND story_id=?",
        (revision_id, story_id),
    ).fetchone()
    if not row:
        raise ValueError("revision not found")
    conn.execute(
        "UPDATE stories SET headline=?, dek=?, body_md=?, updated_ts=? WHERE id=?",
        (row["headline"], row["dek"], row["body_md"], now_ts(), story_id),
    )
    story = get_story(conn, story_id)
    assert story is not None
    _revision(conn, story, editor)
    conn.commit()


def _iso(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def _frontmatter(story: sqlite3.Row, cfg: AccountCfg, hero: str | None) -> dict[str, Any]:
    sources = [
        s for s in json.loads(story["sources_json"] or "[]")
        if isinstance(s, dict) and str(s.get("url") or "").startswith(("http://", "https://"))
    ]
    facts = json.loads(story["facts_json"] or "{}")
    tags = json.loads(story["tags_json"] or "[]")
    data: dict[str, Any] = {
        "title": story["headline"],
        "description": story["dek"] or truncate(strip_html(story["body_md"]), 180),
        "pubDate": _iso(story["published_ts"]) or _iso(story["updated_ts"]),
        "author": story["author"] or cfg.site.default_author,
        "beat": story["beat"] or "AI",
        "archetype": story["archetype"] or "news",
        "format": story["format"] or "news",
        "tags": tags,
        "sources": sources,
        "facts": facts,
    }
    if story["updated_ts"] and story["published_ts"]:
        data["updatedDate"] = _iso(story["updated_ts"])
    if hero:
        data["hero"] = hero
    if story["hero_credit"]:
        data["heroCredit"] = story["hero_credit"]
    if story["hero_alt"]:
        data["heroAlt"] = story["hero_alt"]
    if story["x_post_url"]:
        data["xPostUrl"] = story["x_post_url"]
    return data


def _media_rel(value: str | Path) -> Path:
    rel = Path(value)
    if rel.is_absolute() or any(part in ("", ".", "..") for part in rel.parts):
        raise ValueError(f"unsafe media path: {value}")
    return rel


def _write_redirect(path: Path, target: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"refresh\" content=\"0;url={target}\">"
        f"<link rel=\"canonical\" href=\"{target}\"><title>Redirecting…</title></head>"
        f"<body><p>This story moved to <a href=\"{target}\">{target}</a>.</p></body></html>\n"
    )


def export_site(conn: sqlite3.Connection, cfg: AccountCfg) -> dict[str, Any]:
    repo = cfg.root / cfg.site.repo_path
    content_dir = repo / "src" / "content" / "news"
    media_root = repo / "public" / "media"
    content_dir.mkdir(parents=True, exist_ok=True)
    media_root.mkdir(parents=True, exist_ok=True)
    manifest_path = content_dir / ".export.json"
    previous: dict[str, list[str]] = {"files": [], "media": [], "redirects": []}
    if manifest_path.exists():
        try:
            previous.update(json.loads(manifest_path.read_text()))
        except ValueError:
            pass

    stories = conn.execute(
        "SELECT * FROM stories WHERE status='published' AND slug IS NOT NULL "
        "ORDER BY published_ts DESC, id DESC"
    ).fetchall()
    files: list[str] = []
    media: list[str] = []
    redirects: list[str] = []
    for story in stories:
        slug = str(story["slug"])
        filename = f"{slug}.md"
        files.append(filename)
        hero_path: str | None = None
        if story["hero_local"]:
            source = cfg.root / cfg.site.media_dir / str(story["hero_local"])
            if source.exists():
                ext = source.suffix.lower() or ".jpg"
                target = media_root / slug / f"hero{ext}"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                media.append(f"{slug}/hero{ext}")
                hero_path = f"/media/{slug}/hero{ext}"
        body = (story["body_md"] or "").strip()
        for item in conn.execute(
            "SELECT * FROM story_media WHERE story_id=? ORDER BY created_ts, id",
            (story["id"],),
        ).fetchall():
            rel = _media_rel(str(item["path"]))
            if f"/media/{rel.as_posix()}" not in body:
                continue
            source = cfg.root / cfg.site.media_dir / rel
            if not source.exists():
                continue
            target = media_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            media.append(rel.as_posix())
        data = _frontmatter(story, cfg, hero_path)
        front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
        (content_dir / filename).write_text(f"---\n{front}\n---\n\n{body}\n")
        old = conn.execute(
            "SELECT slug FROM story_slugs WHERE story_id=? AND is_current=0",
            (story["id"],),
        ).fetchall()
        for row in old:
            old_slug = str(row["slug"])
            if old_slug == slug:
                continue
            rel = f"news/{old_slug}/index.html"
            _write_redirect(repo / "public" / rel, f"/news/{slug}/")
            redirects.append(rel)

    for old in previous.get("files", []):
        if old not in files:
            path = content_dir / old
            if path.exists():
                path.unlink()
    for old in previous.get("media", []):
        if old not in media:
            path = media_root / old
            if path.exists():
                path.unlink()
    for old in previous.get("redirects", []):
        if old not in redirects:
            path = repo / "public" / old
            if path.exists():
                path.unlink()
            parent = path.parent
            while parent != repo / "public" and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    manifest_path.write_text(json.dumps({"files": files, "media": media, "redirects": redirects}, indent=2))
    return {"stories": len(stories), "files": files, "media": media, "redirects": redirects}


def _run(
    args: list[str],
    cwd: Path,
    *,
    timeout: int = 300,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{' '.join(args)} failed: {output[-2000:]}")
    return result


def _record_deploy(
    conn: sqlite3.Connection,
    status: str,
    *,
    commit_sha: str | None = None,
    message: str | None = None,
    error: str | None = None,
    started_ts: int | None = None,
) -> None:
    now = now_ts()
    conn.execute(
        """INSERT INTO deployments(started_ts, finished_ts, status, commit_sha, message, error)
           VALUES(?,?,?,?,?,?)""",
        (started_ts or now, now, status, commit_sha, message, error),
    )
    conn.commit()


def dirty_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM stories WHERE dirty=1").fetchone()[0])


def deploy_site(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    *,
    push: bool = True,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    if not force and dirty_count(conn) == 0:
        return {"status": "skipped", "message": "no unpublished changes"}
    repo = cfg.root / cfg.site.repo_path
    repo.parent.mkdir(parents=True, exist_ok=True)
    lock_path = cfg.root / ".site-deploy.lock"
    started = now_ts()
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "busy", "message": "another deploy is running"}

        try:
            if not (repo / ".git").exists():
                _run(["git", "clone", cfg.site.repo_url, str(repo)], repo.parent)
            _run(["git", "fetch", "origin"], repo)
            _run(["git", "reset", "--hard", f"origin/{cfg.site.branch}"], repo)
            exported = export_site(conn, cfg)
            node_modules = repo / "node_modules"
            if not node_modules.exists():
                _run(["npm", "ci"], repo, timeout=600)
            build = _run(["npm", "run", "build"], repo, timeout=600)
            _run(["git", "add", "-A"], repo)
            changed = _run(["git", "status", "--porcelain"], repo).stdout.strip()
            if not changed:
                conn.execute("UPDATE stories SET dirty=0 WHERE dirty=1")
                conn.commit()
                _record_deploy(conn, "clean", message="nothing to deploy", started_ts=started)
                return {"status": "clean", "message": "nothing to deploy"}
            if dry_run:
                _record_deploy(
                    conn, "dry-run", message=f"{exported['stories']} stories; build ok",
                    started_ts=started,
                )
                return {
                    "status": "dry-run",
                    "message": "build ok; not committed",
                    "changes": changed.splitlines(),
                    "build": (build.stdout or "")[-2000:],
                }
            _run(
                [
                    "git", "-c", "user.name=Oropis Bot",
                    "-c", "user.email=abhishek.shinde@oropis.com",
                    "commit", "-m", f"content: publish {exported['stories']} stories",
                ],
                repo,
            )
            sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
            if push:
                _run(["git", "push", "origin", cfg.site.branch], repo, timeout=180)
            conn.execute(
                "UPDATE stories SET dirty=0, exported_ts=? WHERE status='published'",
                (now_ts(),),
            )
            conn.commit()
            message = (
                f"{exported['stories']} stories; pushed {sha[:7]}"
                if push
                else f"{exported['stories']} stories; committed {sha[:7]}"
            )
            _record_deploy(conn, "pushed" if push else "committed", commit_sha=sha,
                           message=message, started_ts=started)
            return {
                "status": "pushed" if push else "committed",
                "message": message,
                "commit": sha,
                "exported": exported,
                "build": (build.stdout or "")[-2000:],
            }
        except Exception as exc:  # noqa: BLE001 - surfaced in the admin UI
            _record_deploy(conn, "failed", error=str(exc)[:4000], started_ts=started)
            return {"status": "failed", "message": str(exc)}


def last_deploy(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM deployments ORDER BY id DESC LIMIT 1"
    ).fetchone()


def coverage(conn: sqlite3.Connection, cfg: AccountCfg) -> dict[str, Any]:
    since = now_ts() - cfg.site.plan_days * 86400
    rows = conn.execute(
        "SELECT archetype, COUNT(*) AS n FROM stories "
        "WHERE status='published' AND published_ts>=? GROUP BY archetype",
        (since,),
    ).fetchall()
    counts = {str(r["archetype"] or "news"): int(r["n"]) for r in rows}
    targets = []
    for key, (low, high) in cfg.site.plan_targets.items():
        targets.append(
            {"key": key, "count": counts.get(key, 0), "low": low, "high": high}
        )
    total = sum(counts.values())
    last = conn.execute(
        "SELECT MAX(published_ts) FROM stories WHERE status='published'"
    ).fetchone()[0]
    formats = conn.execute(
        "SELECT format, COUNT(*) AS n FROM stories WHERE status='published' "
        "AND published_ts>=? GROUP BY format",
        (since,),
    ).fetchall()
    return {
        "since": since,
        "targets": targets,
        "total": total,
        "last_published_ts": last,
        "formats": {str(r["format"]): int(r["n"]) for r in formats},
    }


def status(conn: sqlite3.Connection, cfg: AccountCfg) -> dict[str, Any]:
    counts = {
        str(r["status"]): int(r["n"])
        for r in conn.execute(
            "SELECT status, COUNT(*) AS n FROM stories GROUP BY status"
        ).fetchall()
    }
    deploy = last_deploy(conn)
    return {
        "counts": counts,
        "dirty": dirty_count(conn),
        "last_deploy": deploy,
        "repo": str(cfg.root / cfg.site.repo_path),
        "last_sync": meta_get(conn, "last_sync_ts"),
    }
