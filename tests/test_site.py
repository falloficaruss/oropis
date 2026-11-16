from __future__ import annotations

import asyncio
import json
import re
import sqlite3
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from agg.config import AccountCfg, SiteCfg
from agg.site import db
from agg.site.app import create_app
from agg.site.imaging import resolve_media
from agg.site.media import MediaError, cache_hero
from agg.text import now_ts


def make_cfg(tmp_path):
    cfg = AccountCfg(
        account="oropis",
        site=SiteCfg(
            enabled=True,
            db="site.db",
            media_dir="site-media",
            repo_path="site-repo",
            auto_deploy=False,
        ),
    )
    cfg._root = tmp_path  # type: ignore[attr-defined]
    (tmp_path / "site-repo" / "src" / "content" / "news").mkdir(parents=True)
    return cfg


def make_agg_db(cfg):
    conn = sqlite3.connect(cfg.root / cfg.db)
    conn.executescript(
        """
        CREATE TABLE clusters (
            id INTEGER PRIMARY KEY,
            account TEXT,
            canonical_title TEXT,
            archetype TEXT,
            score REAL,
            last_seen_ts INTEGER
        );
        CREATE TABLE items (
            id INTEGER PRIMARY KEY,
            cluster_id INTEGER,
            source TEXT
        );
        CREATE TABLE item_entities (
            item_id INTEGER,
            entity_id INTEGER
        );
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY,
            name TEXT,
            kind TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def insert_story(
    conn: sqlite3.Connection,
    *,
    cluster_id: int = 1,
    headline: str = "A test headline",
    body: str = "Original copy with enough detail to publish.",
    sources: str = '[{"name":"test","url":"https://example.com/story"}]',
    status: str = "new",
    snapshot_json: str = "{}",
):
    now = now_ts()
    cur = conn.execute(
        """INSERT INTO stories
           (cluster_id, status, headline, dek, body_md, author, beat, archetype,
            format, tags_json, facts_json, sources_json, snapshot_json, score,
            created_ts, updated_ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            cluster_id,
            status,
            headline,
            "A short description for the test story.",
            body,
            "OropisHQ",
            "AI",
            "news",
            "news",
            '["test"]',
            '{"best_of":"Bo3"}',
            sources,
            snapshot_json,
            0.9,
            now,
            now,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def test_schema_status_and_slug_uniqueness(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    first = insert_story(conn, cluster_id=1, headline="Same headline")
    second = insert_story(conn, cluster_id=2, headline="Same headline")

    slug_one = db.set_slug(conn, first, "Same headline")
    slug_two = db.set_slug(conn, second, "Same headline")

    assert slug_one == "same-headline"
    assert slug_two == "same-headline-2"
    assert db.get_story(conn, first)["slug"] == slug_one
    state = db.status(conn, cfg)
    assert state["counts"]["new"] == 2
    assert state["dirty"] == 0


def test_queue_rows_are_latest_first_without_scoring(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    newer = insert_story(conn, cluster_id=1, headline="Newest story")
    older = insert_story(conn, cluster_id=2, headline="Older story")
    now = now_ts()
    conn.execute(
        "UPDATE stories SET score=0.1, created_ts=?, updated_ts=? WHERE id=?",
        (now + 10, now + 10, newer),
    )
    conn.execute(
        "UPDATE stories SET score=0.99, created_ts=?, updated_ts=? WHERE id=?",
        (now - 100, now - 100, older),
    )
    conn.commit()

    rows = db.queue_rows(conn, statuses=("new",))

    assert [row["id"] for row in rows] == [newer, older]


def test_publish_requires_editorial_fields(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story = insert_story(conn, sources="[]")

    with pytest.raises(ValueError, match="source"):
        db.publish_story(conn, story)

    conn.execute("UPDATE stories SET sources_json=? WHERE id=?", (
        '[{"name":"test","url":"https://example.com/story"}]',
        story,
    ))
    conn.execute("UPDATE stories SET body_md='' WHERE id=?", (story,))
    conn.commit()

    with pytest.raises(ValueError, match="body"):
        db.publish_story(conn, story)


def test_publish_creates_slug_and_revision_then_exports(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story = insert_story(conn)

    published = db.publish_story(conn, story)
    assert published["status"] == "published"
    assert published["slug"] == "a-test-headline"
    assert published["dirty"] == 1
    assert len(db.revisions(conn, story)) == 1

    result = db.export_site(conn, cfg)
    path = cfg.root / cfg.site.repo_path / "src" / "content" / "news" / "a-test-headline.md"
    assert result["stories"] == 1
    assert path.exists()

    text = path.read_text()
    frontmatter = text.split("---\n", 2)[1]
    assert "title: A test headline" in frontmatter
    assert "beat: " in frontmatter
    assert "AI" in frontmatter
    assert "hero" not in frontmatter
    assert "Original copy with enough detail to publish." in text

    manifest = json.loads(
        (path.parent / ".export.json").read_text()
    )
    assert manifest["files"] == ["a-test-headline.md"]


def test_export_removes_stories_that_are_no_longer_published(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story = insert_story(conn)
    db.publish_story(conn, story)
    db.export_site(conn, cfg)

    path = cfg.root / cfg.site.repo_path / "src" / "content" / "news" / "a-test-headline.md"
    assert path.exists()

    db.unpublish_story(conn, story)
    result = db.export_site(conn, cfg)

    assert result["stories"] == 0
    assert not path.exists()


def test_export_writes_redirect_for_old_slug(tmp_path):
    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story = insert_story(conn)
    db.publish_story(conn, story)
    db.export_site(conn, cfg)

    db.save_story(conn, story, {"slug": "a-better-headline", "headline": "A better headline"})
    result = db.export_site(conn, cfg)

    assert "news/a-test-headline/index.html" in result["redirects"]
    redirect = cfg.root / cfg.site.repo_path / "public" / "news" / "a-test-headline" / "index.html"
    assert redirect.exists()
    assert "/news/a-better-headline/" in redirect.read_text()


def test_admin_login_and_pages(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    make_agg_db(cfg)
    conn = db.site_connection(cfg)
    insert_story(conn, status="new")

    app = create_app(cfg)
    client = TestClient(app)

    login = client.get("/admin/login")
    assert login.status_code == 200
    assert "Sign in" in login.text

    token = re.search(r'name="csrf" value="([^"]+)"', login.text)
    assert token

    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret", "csrf": token.group(1)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin")

    for path in ("/admin", "/admin/queue", "/admin/coverage", "/admin/deploy"):
        page = client.get(path)
        assert page.status_code == 200, path
        assert "Oropis" in page.text

    dashboard = client.get("/admin")
    queue = client.get("/admin/queue")
    assert "Latest in the queue" in dashboard.text
    assert "Min score" not in queue.text
    assert "<th>Score</th>" not in queue.text


def test_manual_story_create_publish_and_export(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    make_agg_db(cfg)
    client = TestClient(create_app(cfg))
    login(client)

    page = client.get("/admin/new")
    assert page.status_code == 200
    token = re.search(r'name="csrf" value="([^"]+)"', page.text)
    assert token

    response = client.post(
        "/admin/new",
        data={
            "csrf": token.group(1),
            "headline": "My own story",
            "dek": "A story written from scratch.",
            "body_md": "This is my own reporting.",
            "author": "OropisHQ",
            "beat": "AI",
            "archetype": "news",
            "format": "news",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"].split("?", 1)[0]
    story_id = int(location.rsplit("/", 1)[-1])

    conn = db.site_connection(cfg)
    story = db.get_story(conn, story_id)
    assert story is not None
    assert db.is_manual_story(story)
    assert story["status"] == "draft"
    conn.close()

    editor = client.get(location)
    assert editor.status_code == 200
    assert "manual draft" in editor.text
    token = re.search(r'name="csrf" value="([^"]+)"', editor.text)
    assert token

    response = client.post(
        f"/admin/story/{story_id}/save",
        data={
            "csrf": token.group(1),
            "action": "publish",
            "headline": "My own story",
            "dek": "A story written from scratch.",
            "body_md": "This is my own reporting.",
            "author": "OropisHQ",
            "beat": "AI",
            "archetype": "news",
            "format": "news",
            "tags": "AI, Original",
            "facts_json": "{}",
            "hero_url": "",
            "hero_credit": "",
            "hero_alt": "",
            "x_post_url": "",
            "slug": "",
            "sources": "Oropis | Example source | https://example.com/mine",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/queue")

    conn = db.site_connection(cfg)
    story = db.get_story(conn, story_id)
    assert story["status"] == "published"
    assert story["slug"] == "my-own-story"
    sources = json.loads(story["sources_json"])
    assert sources == [
        {"name": "Example source", "url": "https://example.com/mine", "publisher": "Oropis"}
    ]

    result = db.export_site(conn, cfg)
    assert result["stories"] == 1
    path = cfg.root / cfg.site.repo_path / "src" / "content" / "news" / "my-own-story.md"
    assert path.exists()
    assert "https://example.com/mine" in path.read_text()
    conn.close()


def test_manual_story_requires_source_before_publish(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story = db.create_story(conn, cfg, headline="Unsourced story", body_md="Body copy.")
    with pytest.raises(ValueError, match="source"):
        db.publish_story(conn, int(story["id"]))
    conn.close()


def test_admin_rejects_bad_csrf(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    make_agg_db(cfg)
    client = TestClient(create_app(cfg))
    client.get("/admin/login")

    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret", "csrf": "wrong"},
    )
    assert response.status_code == 400


def test_hero_cache_blocks_private_addresses(tmp_path):
    cfg = make_cfg(tmp_path)

    with pytest.raises(MediaError, match="public address"):
        asyncio.run(cache_hero(cfg, {"hero_url": "http://127.0.0.1/hero.jpg"}, "test"))

    with pytest.raises(MediaError, match="http"):
        asyncio.run(cache_hero(cfg, {"hero_url": "file:///etc/passwd"}, "test"))


def insert_cluster(conn, cluster_id, title, beat, score=0.9):
    now = now_ts()
    conn.execute(
        """INSERT INTO clusters(id, account, canonical_title, archetype, score, last_seen_ts)
           VALUES(?, 'oropis', ?, 'news', ?, ?)""",
        (cluster_id, title, score, now),
    )
    conn.execute(
        "INSERT INTO items(id, cluster_id, source) VALUES(?, ?, 'test')",
        (cluster_id, cluster_id),
    )
    if beat:
        cur = conn.execute(
            "INSERT INTO entities(name, kind) VALUES(?, 'beat')", (beat,)
        )
        conn.execute(
            "INSERT INTO item_entities(item_id, entity_id) VALUES(?, ?)",
            (cluster_id, cur.lastrowid),
        )
    conn.commit()


def test_sync_only_imports_covered_beats(tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.watchlist = {"beats": ["AI", "Robotics"]}
    make_agg_db(cfg)
    agg = sqlite3.connect(cfg.root / cfg.db)
    insert_cluster(agg, 1, "OpenAI ships a new reasoning model", "AI")
    insert_cluster(agg, 2, "A rival lab's model launch", "Other")
    insert_cluster(agg, 3, "Waymo expands robotaxi service", "Robotics")
    insert_cluster(agg, 4, "Untagged AI roundup", None)
    agg.close()

    conn = db.site_connection(cfg)
    added = db.sync(conn, cfg, since_h=72, min_score=0.0)

    assert added == 2
    rows = conn.execute(
        "SELECT headline, beat FROM stories ORDER BY cluster_id"
    ).fetchall()
    assert [(r["headline"], r["beat"]) for r in rows] == [
        ("OpenAI ships a new reasoning model", "AI"),
        ("Waymo expands robotaxi service", "Robotics"),
    ]


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (320, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (90, 45, 20)).save(buffer, format=fmt)
    return buffer.getvalue()


def login(client: TestClient) -> None:
    page = client.get("/admin/login")
    token = re.search(r'name="csrf" value="([^"]+)"', page.text)
    assert token
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "secret", "csrf": token.group(1)},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_republish_keeps_curated_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    make_agg_db(cfg)
    conn = db.site_connection(cfg)
    sources = '[{"name":"curated","url":"https://example.com/curated"}]'
    story_id = insert_story(
        conn,
        status="published",
        sources=sources,
        snapshot_json='{"payload":{}}',
    )
    db.set_slug(conn, story_id, "source-safe")
    conn.commit()
    conn.close()

    client = TestClient(create_app(cfg))
    login(client)
    editor = client.get(f"/admin/story/{story_id}")
    token = re.search(r'name="csrf" value="([^"]+)"', editor.text)
    assert token

    response = client.post(
        f"/admin/story/{story_id}/save",
        data={
            "csrf": token.group(1),
            "action": "publish",
            "headline": "A reviewed headline",
            "body_md": "A reviewed body that is long enough to publish.",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/admin/queue")
    conn = db.site_connection(cfg)
    row = db.get_story(conn, story_id)
    assert row["sources_json"] == sources
    assert row["headline"] == "A reviewed headline"
    conn.close()


def test_upload_hero_and_export(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story_id = insert_story(conn, status="published", snapshot_json='{"payload":{}}')
    db.set_slug(conn, story_id, "hero-story")
    conn.commit()
    conn.close()

    client = TestClient(create_app(cfg))
    login(client)
    editor = client.get(f"/admin/story/{story_id}")
    token = re.search(r'name="csrf" value="([^"]+)"', editor.text)
    assert token

    response = client.post(
        f"/admin/story/{story_id}/image",
        data={"csrf": token.group(1), "kind": "hero", "alt": "Arena stage", "credit": "Oropis"},
        files={"file": ("hero.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    conn = db.site_connection(cfg)
    row = db.get_story(conn, story_id)
    assert row["hero_local"] == payload["path"]
    assert row["hero_url"] is None
    assert row["hero_alt"] == "Arena stage"
    assert row["hero_credit"] == "Oropis"
    assert row["dirty"] == 0
    conn.close()
    local = cfg.root / cfg.site.media_dir / payload["path"]
    assert local.is_file()
    assert local.read_bytes().startswith(b"RIFF")

    conn = db.site_connection(cfg)
    exported = db.export_site(conn, cfg)
    conn.close()
    assert "hero-story/hero.webp" in exported["media"]
    markdown = (
        cfg.root / cfg.site.repo_path / "src" / "content" / "news" / "hero-story.md"
    ).read_text()
    assert "hero: /media/hero-story/hero.webp" in markdown
    assert "heroAlt: Arena stage" in markdown
    assert "heroCredit: Oropis" in markdown
    assert (
        cfg.root / cfg.site.repo_path / "public" / "media" / "hero-story" / "hero.webp"
    ).is_file()


def test_upload_inline_and_export_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story_id = insert_story(conn, status="published", snapshot_json='{"payload":{}}')
    db.set_slug(conn, story_id, "inline-story")
    conn.commit()
    conn.close()

    client = TestClient(create_app(cfg))
    login(client)
    editor = client.get(f"/admin/story/{story_id}")
    token = re.search(r'name="csrf" value="([^"]+)"', editor.text)
    assert token

    response = client.post(
        f"/admin/story/{story_id}/image",
        data={
            "csrf": token.group(1),
            "kind": "inline",
            "alt": "Crowd at the venue",
            "caption": "The crowd on finals day.",
            "credit": "Oropis",
        },
        files={"file": ("crowd.png", image_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["markdown"].startswith('<figure class="article-figure">')
    assert "loading=\"lazy\"" in payload["markdown"]
    conn = db.site_connection(cfg)
    assert db.story_media(conn, story_id)[0]["path"] == payload["path"]
    conn.close()

    conn = db.site_connection(cfg)
    conn.execute(
        "UPDATE stories SET body_md=? WHERE id=?",
        (f"Intro copy.\n\n{payload['markdown']}\n\nOutro copy.", story_id),
    )
    conn.commit()
    exported = db.export_site(conn, cfg)
    conn.close()
    assert payload["path"] in exported["media"]
    public = cfg.root / cfg.site.repo_path / "public" / "media" / payload["path"]
    assert public.is_file()
    markdown = (
        cfg.root / cfg.site.repo_path / "src" / "content" / "news" / "inline-story.md"
    ).read_text()
    assert "/media/uploads/inline/" in markdown

    conn = db.site_connection(cfg)
    conn.execute("UPDATE stories SET body_md='Intro copy only.' WHERE id=?", (story_id,))
    conn.commit()
    db.export_site(conn, cfg)
    conn.close()
    assert not public.exists()


def test_upload_rejects_bad_image_and_traversal(tmp_path, monkeypatch):
    monkeypatch.setenv("SITE_ADMIN_USER", "admin")
    monkeypatch.setenv("SITE_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SITE_SECRET_KEY", "test-secret-key")

    cfg = make_cfg(tmp_path)
    conn = db.site_connection(cfg)
    story_id = insert_story(conn, status="draft", snapshot_json='{"payload":{}}')
    conn.close()
    client = TestClient(create_app(cfg))
    login(client)
    editor = client.get(f"/admin/story/{story_id}")
    token = re.search(r'name="csrf" value="([^"]+)"', editor.text)
    assert token

    response = client.post(
        f"/admin/story/{story_id}/image",
        data={"csrf": token.group(1), "kind": "hero"},
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "readable image" in response.json()["error"]
    conn = db.site_connection(cfg)
    assert db.get_story(conn, story_id)["hero_local"] is None
    conn.close()

    with pytest.raises(ValueError, match="escapes"):
        resolve_media(cfg, "../site.db")
