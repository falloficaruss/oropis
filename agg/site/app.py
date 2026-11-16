from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from ..config import AccountCfg, resolve_account
from ..text import now_ts
from . import auth
from .db import (
    add_story_media,
    coverage,
    create_story,
    delete_story_media,
    deploy_site,
    export_site,
    get_story,
    get_story_media,
    is_manual_story,
    last_deploy,
    mark_story_dirty,
    publish_story,
    queue_rows,
    reject_story,
    restore_revision,
    revisions,
    save_story,
    set_slug,
    site_connection,
    snapshot,
    status,
    story_media,
    sync,
    unpublish_story,
)
from .imaging import (
    UploadError,
    delete_upload,
    figure_markup,
    media_url,
    process_upload,
    resolve_media,
    save_upload,
)
from .media import MediaError, cache_hero
from .render import template_globals

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def _cfg_from_env() -> AccountCfg:
    return resolve_account(os.environ.get("AGG_ACCOUNT", "oropis"))


def _redirect(path: str, msg: str | None = None, kind: str = "ok") -> RedirectResponse:
    if msg:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}msg={quote(msg)}&kind={kind}"
    return RedirectResponse(path, status_code=303)


def _story_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _context(request: Request, **extra: Any) -> dict[str, Any]:
    base = {
        "request": request,
        "user": auth.current_user(request),
        "csrf": auth.ensure_csrf(request),
        "msg": request.query_params.get("msg"),
        "kind": request.query_params.get("kind", "ok"),
    }
    base.update(extra)
    return base


def _sources_from_text(text: str) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) == 1:
            publisher, name, url = "", "", parts[0]
        elif len(parts) == 2:
            publisher, name, url = "", parts[0], parts[1]
        else:
            publisher, name, url = parts[0], parts[1], "|".join(parts[2:]).strip()
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"source URL must start with http:// or https://: {url or line}")
        if url in seen:
            continue
        seen.add(url)
        source = {"name": name or publisher or url, "url": url}
        if publisher:
            source["publisher"] = publisher
        sources.append(source)
    return sources


def _sources_to_text(sources: list[Any]) -> str:
    lines: list[str] = []
    for source in sources:
        if not isinstance(source, dict) or not source.get("url"):
            continue
        publisher = str(source.get("publisher") or "").strip()
        name = str(source.get("name") or "").strip()
        url = str(source.get("url") or "").strip()
        if publisher:
            lines.append(f"{publisher} | {name} | {url}")
        elif name:
            lines.append(f"{name} | {url}")
        else:
            lines.append(url)
    return "\n".join(lines)


def create_app(cfg: AccountCfg | None = None) -> FastAPI:
    cfg = cfg or _cfg_from_env()
    app = FastAPI(title=cfg.site.name, docs_url=None, redoc_url=None)
    secret = os.environ.get("SITE_SECRET_KEY") or "dev-only-change-me"
    app.add_middleware(SessionMiddleware, secret_key=secret, max_age=12 * 3600,
                       same_site="lax", https_only=False)
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.state.cfg = cfg
    app.state.db = site_connection(cfg)
    templates.env.globals.update(template_globals(cfg))
    app.mount("/admin/static", StaticFiles(directory=str(HERE / "static")), name="static")

    @app.middleware("http")
    async def headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' https: data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if exc.status_code == 303 and exc.headers and "Location" in exc.headers:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        return templates.TemplateResponse(
            request,
            "error.html",
            _context(request, code=exc.status_code, detail=exc.detail),
            status_code=exc.status_code,
        )

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/admin", status_code=307)

    @app.get("/healthz")
    def healthz():
        return JSONResponse({"ok": True, "ts": now_ts()})

    @app.get("/admin/login", response_class=HTMLResponse)
    def login_page(request: Request):
        if auth.current_user(request):
            return RedirectResponse("/admin", status_code=303)
        return templates.TemplateResponse(
            request,
            "login.html",
            _context(request, configured=auth.credentials() is not None),
        )

    @app.post("/admin/login")
    def login(
        request: Request,
        username: str = Form(""),
        password: str = Form(""),
        csrf: str = Form(""),
    ):
        auth.verify_csrf(request, csrf)
        if not auth.allowed(request):
            return _redirect("/admin/login", "Too many attempts. Wait 15 minutes.", "error")
        if not auth.check_credentials(username, password):
            auth.record_failure(request)
            return _redirect("/admin/login", "Wrong username or password.", "error")
        auth.reset(request)
        request.session["user"] = username
        return _redirect("/admin", "Signed in.")

    @app.post("/admin/logout")
    def logout(request: Request, csrf: str = Form("")):
        auth.verify_csrf(request, csrf)
        request.session.clear()
        return _redirect("/admin/login", "Signed out.")

    @app.get("/admin", response_class=HTMLResponse)
    def dashboard(request: Request):
        user = auth.require_user(request)
        conn = app.state.db
        sync(conn, cfg)
        rows = queue_rows(conn, limit=8)
        state = status(conn, cfg)
        cov = coverage(conn, cfg)
        deploy = last_deploy(conn)
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _context(
                request, user=user, rows=rows, state=state, coverage=cov,
                deploy=deploy, dirty=state["dirty"],
            ),
        )

    @app.get("/admin/queue", response_class=HTMLResponse)
    def queue_page(
        request: Request,
        beat: str | None = None,
        archetype: str | None = None,
        status_filter: str = "open",
    ):
        user = auth.require_user(request)
        conn = app.state.db
        sync(conn, cfg)
        names = {
            "open": ("new", "draft"),
            "new": ("new",),
            "draft": ("draft",),
            "published": ("published",),
            "rejected": ("rejected",),
        }
        rows = queue_rows(
            conn,
            statuses=names.get(status_filter, ("new", "draft")),
            beat=beat,
            archetype=archetype,
            limit=300,
        )
        beats = [
            r["beat"] for r in conn.execute(
                "SELECT DISTINCT beat FROM stories WHERE beat IS NOT NULL ORDER BY beat"
            ).fetchall()
        ]
        return templates.TemplateResponse(
            request,
            "queue.html",
            _context(
                request, user=user, rows=rows, beats=beats, beat=beat,
                archetype=archetype, status_filter=status_filter,
            ),
        )

    @app.get("/admin/new", response_class=HTMLResponse)
    def new_story_page(request: Request):
        user = auth.require_user(request)
        return templates.TemplateResponse(
            request,
            "new.html",
            _context(request, user=user, default_author=cfg.site.default_author),
        )

    @app.post("/admin/new")
    def new_story(
        request: Request,
        csrf: str = Form(""),
        headline: str = Form(""),
        dek: str = Form(""),
        body_md: str = Form(""),
        author: str = Form(""),
        beat: str = Form(""),
        archetype: str = Form("news"),
        format: str = Form("news"),
    ):
        auth.require_user(request)
        auth.verify_csrf(request, csrf)
        try:
            story = create_story(
                app.state.db,
                cfg,
                headline=headline,
                dek=dek,
                body_md=body_md,
                author=author,
                beat=beat,
                archetype=archetype,
                format=format,
            )
        except ValueError as exc:
            return _redirect("/admin/new", str(exc), "error")
        return _redirect(f"/admin/story/{story['id']}", "Draft created.")

    def _load_story(story_id: int) -> tuple[sqlite3.Connection, sqlite3.Row]:
        conn = app.state.db
        story = get_story(conn, story_id)
        if not story:
            raise HTTPException(status_code=404, detail="story not found")
        return conn, story

    @app.get("/admin/story/{story_id}", response_class=HTMLResponse)
    def editor(request: Request, story_id: int, refresh: int = 0):
        user = auth.require_user(request)
        conn, story = _load_story(story_id)
        manual = is_manual_story(story)
        if not manual and (refresh or story["snapshot_json"] in ("", "{}")):
            snapshot(conn, cfg, story_id)
            story = get_story(conn, story_id)
            assert story is not None
        snap = json.loads(story["snapshot_json"] or "{}")
        sources = json.loads(story["sources_json"] or "[]")
        payload = snap.get("payload") or {}
        media = [
            {
                **dict(row),
                "url": media_url(str(row["path"])),
                "markdown": figure_markup(
                    str(row["path"]),
                    alt=str(row["alt"] or ""),
                    caption=str(row["caption"] or ""),
                    credit=str(row["credit"] or ""),
                    width=row["width"],
                    height=row["height"],
                ),
            }
            for row in story_media(conn, story_id)
        ]
        return templates.TemplateResponse(
            request,
            "editor.html",
            _context(
                request, user=user, story=story, manual=manual,
                sources=sources,
                sources_text=_sources_to_text(sources),
                tags=", ".join(json.loads(story["tags_json"] or "[]")),
                facts=json.dumps(json.loads(story["facts_json"] or "{}"), indent=2),
                items=payload.get("items") or [],
                angles=payload.get("angles") or [],
                numbers=payload.get("numbers") or [],
                packet=snap.get("packet") or "",
                media=media,
            ),
        )

    @app.post("/admin/story/{story_id}/save")
    def save(
        request: Request,
        story_id: int,
        csrf: str = Form(""),
        action: str = Form("save"),
        headline: str = Form(""),
        slug: str = Form(""),
        dek: str = Form(""),
        body_md: str = Form(""),
        author: str = Form(""),
        beat: str = Form(""),
        archetype: str = Form(""),
        format: str = Form("news"),
        tags: str = Form(""),
        facts_json: str = Form("{}"),
        hero_url: str = Form(""),
        hero_credit: str = Form(""),
        hero_alt: str = Form(""),
        x_post_url: str = Form(""),
        sources: str | None = Form(None),
    ):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, story = _load_story(story_id)
        try:
            facts = json.loads(facts_json or "{}")
            if not isinstance(facts, dict):
                raise ValueError("facts must be a JSON object")
        except ValueError as exc:
            return _redirect(f"/admin/story/{story_id}", str(exc), "error")
        fields = {
            "headline": headline.strip(),
            "dek": dek.strip(),
            "body_md": body_md,
            "author": author.strip() or cfg.site.default_author,
            "beat": beat.strip() or None,
            "archetype": archetype.strip() or "news",
            "format": format.strip() or "news",
            "tags_json": json.dumps(
                [t.strip() for t in tags.split(",") if t.strip()], ensure_ascii=False
            ),
            "facts_json": json.dumps(facts, ensure_ascii=False),
            "hero_url": hero_url.strip() or None,
            "hero_credit": hero_credit.strip() or None,
            "hero_alt": hero_alt.strip() or None,
            "x_post_url": x_post_url.strip() or None,
        }
        if slug.strip():
            fields["slug"] = slug.strip()
        if sources is not None:
            try:
                fields["sources_json"] = json.dumps(
                    _sources_from_text(sources), ensure_ascii=False
                )
            except ValueError as exc:
                return _redirect(f"/admin/story/{story_id}", str(exc), "error")
        try:
            save_story(conn, story_id, fields, user)
        except (ValueError, sqlite3.IntegrityError) as exc:
            return _redirect(f"/admin/story/{story_id}", str(exc), "error")
        if fields["hero_url"] and story["hero_local"]:
            old = str(story["hero_local"])
            conn.execute("UPDATE stories SET hero_local=NULL WHERE id=?", (story_id,))
            conn.commit()
            delete_upload(cfg, old)
        if action == "publish":
            return _publish(request, story_id, user)
        return _redirect(f"/admin/story/{story_id}", "Saved.")

    def _publish(request: Request, story_id: int, user: str):
        conn, story = _load_story(story_id)
        try:
            manual = is_manual_story(story)
            needs_snapshot = not manual and (
                story["status"] != "published"
                or story["sources_json"] in ("", "[]")
                or story["snapshot_json"] in ("", "{}")
            )
            if needs_snapshot:
                snapshot(conn, cfg, story_id)
                story = get_story(conn, story_id)
                assert story is not None
            if not story["slug"]:
                set_slug(conn, story_id, story["headline"])
                conn.commit()
                story = get_story(conn, story_id)
                assert story is not None
            if story["hero_url"] and not story["hero_local"] and cfg.site.cache_heroes:
                try:
                    filename = _cache_hero(story, str(story["slug"]))
                    if filename:
                        conn.execute(
                            "UPDATE stories SET hero_local=? WHERE id=?",
                            (filename, story_id),
                        )
                        conn.commit()
                except MediaError as exc:
                    publish_story(conn, story_id, user)
                    return _redirect(
                        f"/admin/story/{story_id}",
                        f"Published without a cached image: {exc}",
                        "warn",
                    )
            publish_story(conn, story_id, user)
        except (ValueError, MediaError) as exc:
            return _redirect(f"/admin/story/{story_id}", str(exc), "error")
        return _redirect("/admin/queue?status_filter=published", "Published. Deploy is queued.")

    def _cache_hero(story: sqlite3.Row, slug: str) -> str | None:
        import asyncio

        return asyncio.run(cache_hero(cfg, story, slug))

    @app.get("/media/{path:path}")
    def admin_media(request: Request, path: str):
        auth.require_user(request)
        try:
            target = resolve_media(cfg, path)
        except ValueError:
            raise HTTPException(status_code=404, detail="image not found") from None
        if not target.is_file():
            raise HTTPException(status_code=404, detail="image not found")
        return FileResponse(target, headers={"Cache-Control": "private, max-age=60"})

    @app.post("/admin/story/{story_id}/image")
    async def upload_image(
        request: Request,
        story_id: int,
        csrf: str = Form(""),
        kind: str = Form("hero"),
        alt: str = Form(""),
        caption: str = Form(""),
        credit: str = Form(""),
        file: UploadFile = File(...),
    ):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, story = _load_story(story_id)
        if kind not in ("hero", "inline"):
            return JSONResponse({"ok": False, "error": "unknown image kind"}, status_code=400)
        alt = alt.strip()
        credit = credit.strip()
        if kind == "inline" and not alt:
            return JSONResponse({"ok": False, "error": "alt text is required"}, status_code=400)
        raw = await file.read(12 * 1024 * 1024 + 1)
        await file.close()
        try:
            image = process_upload(raw, kind=kind)
            rel = save_upload(cfg, story_id, kind, image)
        except (UploadError, OSError) as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
        try:
            if kind == "hero":
                old = story["hero_local"]
                conn.execute(
                    "UPDATE stories SET hero_local=?, hero_url=NULL, hero_alt=?, "
                    "hero_credit=?, updated_ts=? WHERE id=?",
                    (rel, alt or None, credit or None, now_ts(), story_id),
                )
                conn.commit()
                delete_upload(cfg, str(old) if old else None)
                return JSONResponse(
                    {
                        "ok": True,
                        "kind": "hero",
                        "url": media_url(rel),
                        "path": rel,
                        "alt": alt,
                        "credit": credit,
                    }
                )
            row = add_story_media(
                conn,
                story_id,
                path=rel,
                alt=alt,
                caption=caption.strip(),
                credit=credit.strip(),
                original_name=file.filename,
                mime=image.mime,
                width=image.width,
                height=image.height,
                bytes_=len(image.data),
            )
            return JSONResponse(
                {
                    "ok": True,
                    "kind": "inline",
                    "id": row["id"],
                    "url": media_url(rel),
                    "path": rel,
                    "markdown": figure_markup(
                        rel,
                        alt=alt,
                        caption=caption.strip(),
                        credit=credit.strip(),
                        width=image.width,
                        height=image.height,
                    ),
                }
            )
        except Exception:
            delete_upload(cfg, rel)
            raise

    @app.post("/admin/story/{story_id}/hero/delete")
    def remove_hero(request: Request, story_id: int, csrf: str = Form("")):
        auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, story = _load_story(story_id)
        old = story["hero_local"]
        conn.execute(
            "UPDATE stories SET hero_local=NULL, hero_url=NULL, hero_alt=NULL, "
            "hero_credit=NULL, updated_ts=? WHERE id=?",
            (now_ts(), story_id),
        )
        conn.commit()
        mark_story_dirty(conn, story_id)
        delete_upload(cfg, str(old) if old else None)
        return _redirect(f"/admin/story/{story_id}", "Hero image removed.")

    @app.post("/admin/story/{story_id}/image/{media_id}/delete")
    def remove_inline_image(
        request: Request, story_id: int, media_id: int, csrf: str = Form("")
    ):
        auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, story = _load_story(story_id)
        row = get_story_media(conn, media_id)
        if not row or int(row["story_id"]) != story_id:
            raise HTTPException(status_code=404, detail="image not found")
        path = str(row["path"])
        if f"/media/{path}" in (story["body_md"] or ""):
            return _redirect(
                f"/admin/story/{story_id}",
                "Remove this image from the body before deleting it.",
                "warn",
            )
        delete_story_media(conn, media_id)
        mark_story_dirty(conn, story_id)
        delete_upload(cfg, path)
        return _redirect(f"/admin/story/{story_id}", "Inline image deleted.")

    @app.post("/admin/story/{story_id}/publish")
    def publish(request: Request, story_id: int, csrf: str = Form("")):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        return _publish(request, story_id, user)

    @app.post("/admin/story/{story_id}/unpublish")
    def unpublish(request: Request, story_id: int, csrf: str = Form("")):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, _ = _load_story(story_id)
        unpublish_story(conn, story_id, user)
        return _redirect(f"/admin/story/{story_id}", "Unpublished; deploy queued.")

    @app.post("/admin/story/{story_id}/reject")
    def reject(request: Request, story_id: int, csrf: str = Form("")):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, _ = _load_story(story_id)
        reject_story(conn, story_id, user)
        return _redirect("/admin/queue", "Story rejected.")

    @app.get("/admin/story/{story_id}/preview", response_class=HTMLResponse)
    def preview(request: Request, story_id: int):
        user = auth.require_user(request)
        conn, story = _load_story(story_id)
        return templates.TemplateResponse(
            request,
            "preview.html",
            _context(request, user=user, story=story),
        )

    @app.get("/admin/story/{story_id}/revisions", response_class=HTMLResponse)
    def revision_page(request: Request, story_id: int):
        user = auth.require_user(request)
        conn, story = _load_story(story_id)
        return templates.TemplateResponse(
            request,
            "revisions.html",
            _context(request, user=user, story=story, revisions=revisions(conn, story_id)),
        )

    @app.post("/admin/story/{story_id}/restore/{revision_id}")
    def restore(request: Request, story_id: int, revision_id: int, csrf: str = Form("")):
        user = auth.require_user(request)
        auth.verify_csrf(request, csrf)
        conn, _ = _load_story(story_id)
        try:
            restore_revision(conn, story_id, revision_id, user)
        except ValueError as exc:
            return _redirect(f"/admin/story/{story_id}/revisions", str(exc), "error")
        return _redirect(f"/admin/story/{story_id}", "Revision restored.")

    @app.get("/admin/coverage", response_class=HTMLResponse)
    def coverage_page(request: Request):
        user = auth.require_user(request)
        conn = app.state.db
        return templates.TemplateResponse(
            request,
            "coverage.html",
            _context(request, user=user, coverage=coverage(conn, cfg)),
        )

    @app.get("/admin/deploy", response_class=HTMLResponse)
    def deploy_page(request: Request):
        user = auth.require_user(request)
        conn = app.state.db
        rows = conn.execute(
            "SELECT * FROM deployments ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return templates.TemplateResponse(
            request,
            "deploy.html",
            _context(
                request, user=user, deploy=last_deploy(conn), deploys=rows,
                dirty=conn.execute("SELECT COUNT(*) FROM stories WHERE dirty=1").fetchone()[0],
                repo=str(cfg.root / cfg.site.repo_path),
            ),
        )

    @app.post("/admin/deploy/now")
    def deploy_now(request: Request, csrf: str = Form("")):
        auth.require_user(request)
        auth.verify_csrf(request, csrf)
        result = deploy_site(app.state.db, cfg, push=True, force=True)
        kind = "ok" if result.get("status") in {"pushed", "clean", "committed"} else "error"
        return _redirect("/admin/deploy", result.get("message") or result.get("status", ""), kind)

    @app.post("/admin/export")
    def export_now(request: Request, csrf: str = Form("")):
        auth.require_user(request)
        auth.verify_csrf(request, csrf)
        result = export_site(app.state.db, cfg)
        return _redirect("/admin/deploy", f"Exported {result['stories']} stories.")

    return app
