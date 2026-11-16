from __future__ import annotations

import asyncio
import random
import sqlite3
import time

from .config import AccountCfg, SourceCfg
from .db import connect, meta_set, upsert_source
from .dedupe import ingest_items
from .entities import EntityMatcher
from .fetch import fetch_source
from .fetch.base import FetchCtx, make_client
from .relevance import RelevanceMatcher
from .score import rescore
from .text import now_ts


def _source_row(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sources WHERE name=?", (name,)).fetchone()


async def _fetch_one(
    ctx: FetchCtx,
    cfg: AccountCfg,
    source: SourceCfg,
    conn: sqlite3.Connection,
) -> dict:
    started = time.monotonic()
    row = _source_row(conn, source.name)
    probe_source = source.model_copy(deep=True)
    if row and row["etag"]:
        probe_source.options = {**probe_source.options, "etag": row["etag"]}
    try:
        result = await fetch_source(ctx, probe_source)
    except Exception as exc:
        conn.execute(
            """UPDATE sources SET fail_count = fail_count + 1, last_error = ?,
               last_seen_ts = ? WHERE name = ?""",
            (f"{type(exc).__name__}: {exc}"[:300], now_ts(), source.name),
        )
        conn.commit()
        return {
            "name": source.name,
            "ok": False,
            "items": 0,
            "ms": int((time.monotonic() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }

    new_items, new_clusters = 0, 0
    if result.items:
        matcher = ctx.cfg._matcher  # type: ignore[attr-defined]
        relevance = getattr(ctx.cfg, "_relevance", None)
        new_items, new_clusters = ingest_items(conn, cfg, matcher, result.items, relevance)

    latest = max((i.published_ts or 0 for i in result.items), default=0)
    now = now_ts()
    conn.execute(
        """UPDATE sources SET
             last_ok_ts = ?, last_seen_ts = MAX(COALESCE(last_seen_ts, 0), ?),
             last_item_ts = MAX(COALESCE(last_item_ts, 0), ?),
             fail_count = 0, last_error = NULL,
             etag = COALESCE(?, etag), last_modified = COALESCE(?, last_modified)
           WHERE name = ?""",
        (now, now, latest, result.etag, result.last_modified, source.name),
    )
    conn.commit()
    return {
        "name": source.name,
        "ok": True,
        "not_modified": result.not_modified,
        "items": len(result.items),
        "new_items": new_items,
        "new_clusters": new_clusters,
        "ms": int((time.monotonic() - started) * 1000),
        "error": None,
    }


async def poll_once(
    cfg: AccountCfg,
    only: str | None = None,
    once: bool = True,
) -> list[dict]:
    conn = connect(cfg.root / cfg.db)
    matcher = EntityMatcher(cfg)
    cfg._matcher = matcher  # type: ignore[attr-defined]
    cfg._relevance = RelevanceMatcher(cfg)  # type: ignore[attr-defined]
    for source in cfg.sources:
        upsert_source(conn, cfg.account, source)

    run_cur = conn.execute("INSERT INTO runs(started_ts) VALUES(?)", (now_ts(),))
    run_id = run_cur.lastrowid
    conn.commit()

    selected = [s for s in cfg.sources if s.enabled and (only is None or s.name == only)]
    results: list[dict] = []
    async with make_client(cfg) as client:
        ctx = FetchCtx(client=client, cfg=cfg, conn=conn)
        sem = asyncio.Semaphore(cfg.network.max_concurrent)

        async def guarded(source: SourceCfg) -> dict:
            async with sem:
                return await _fetch_one(ctx, cfg, source, conn)

        results = list(await asyncio.gather(*(guarded(s) for s in selected)))

    rescore(conn, cfg)
    fetched = sum(r.get("new_items", 0) for r in results)
    clusters = sum(r.get("new_clusters", 0) for r in results)
    errors = sum(1 for r in results if not r["ok"])
    conn.execute(
        """UPDATE runs SET finished_ts=?, fetched=?, new_items=?, new_clusters=?, errors=?
           WHERE id=?""",
        (now_ts(), fetched, fetched, clusters, errors, run_id),
    )
    conn.commit()
    meta_set(conn, "last_poll_ts", str(now_ts()))
    conn.close()
    return results


async def run_forever(cfg: AccountCfg) -> None:
    conn = connect(cfg.root / cfg.db)
    matcher = EntityMatcher(cfg)
    cfg._matcher = matcher  # type: ignore[attr-defined]
    cfg._relevance = RelevanceMatcher(cfg)  # type: ignore[attr-defined]
    for source in cfg.sources:
        upsert_source(conn, cfg.account, source)
    conn.close()

    next_due: dict[str, float] = {
        s.name: time.monotonic() + random.uniform(0, 90)
        for s in cfg.sources if s.enabled
    }
    print(f"[agg] {cfg.account}: {len(next_due)} sources, catch-up on start", flush=True)

    while True:
        now = time.monotonic()
        due = [name for name, at in next_due.items() if at <= now]
        if due:
            cfg_sources = {s.name: s for s in cfg.sources}
            batch = [cfg_sources[n] for n in due if n in cfg_sources]
            results = await _poll_subset(cfg, batch)
            for result in results:
                source = cfg_sources[result["name"]]
                interval = source.interval_s or cfg.poll.default_interval_s
                jitter = random.uniform(0, cfg.poll.jitter_s)
                next_due[source.name] = time.monotonic() + interval + jitter
            ok = sum(1 for r in results if r["ok"])
            new = sum(r.get("new_items", 0) for r in results)
            print(
                f"[agg] {time.strftime('%H:%M:%S')} polled={len(results)} ok={ok} new={new}",
                flush=True,
            )
        await asyncio.sleep(1.0)


async def _poll_subset(cfg: AccountCfg, sources: list[SourceCfg]) -> list[dict]:
    conn = connect(cfg.root / cfg.db)
    matcher = EntityMatcher(cfg)
    cfg._matcher = matcher  # type: ignore[attr-defined]
    cfg._relevance = RelevanceMatcher(cfg)  # type: ignore[attr-defined]
    run_cur = conn.execute("INSERT INTO runs(started_ts) VALUES(?)", (now_ts(),))
    run_id = run_cur.lastrowid
    conn.commit()
    results: list[dict] = []
    async with make_client(cfg) as client:
        ctx = FetchCtx(client=client, cfg=cfg, conn=conn)
        sem = asyncio.Semaphore(cfg.network.max_concurrent)

        async def guarded(source: SourceCfg) -> dict:
            async with sem:
                return await _fetch_one(ctx, cfg, source, conn)

        results = list(await asyncio.gather(*(guarded(s) for s in sources)))
    rescore(conn, cfg)
    fetched = sum(r.get("new_items", 0) for r in results)
    clusters = sum(r.get("new_clusters", 0) for r in results)
    errors = sum(1 for r in results if not r["ok"])
    conn.execute(
        """UPDATE runs SET finished_ts=?, fetched=?, new_items=?, new_clusters=?, errors=?
           WHERE id=?""",
        (now_ts(), fetched, fetched, clusters, errors, run_id),
    )
    conn.commit()
    meta_set(conn, "last_poll_ts", str(now_ts()))
    conn.close()
    return results
