from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys

from .config import AccountCfg, resolve_account
from .db import cluster_row, connect, meta_get, meta_set
from .enrich import fill_bodies
from .render import (
    build_packet,
    console,
    feeds_table,
    inbox_table,
    show_cluster,
    sources_table,
    stats_panel,
    status_panel,
    topics_table,
)
from .runner import poll_once, run_forever
from .score import rescore
from .telegram import (
    TelegramError,
    preview as telegram_preview,
    run_forever as telegram_forever,
    run_once as telegram_once,
    send_test as telegram_test,
    status as telegram_status,
)
from .text import fmt_age, fmt_ts, now_ts
from .topics import compute_topics

ARCHETYPES = ["research", "product", "deployment", "funding", "policy", "business", "news"]


def _account(args) -> AccountCfg:
    cfg = resolve_account(getattr(args, "account", None))
    return cfg


def _db(cfg: AccountCfg) -> sqlite3.Connection:
    return connect(cfg.root / cfg.db)


def _rows(conn, cfg, since_h: float, top: int, beat: str | None = None):
    since = now_ts() - int(since_h * 3600)
    return conn.execute(
        """SELECT c.*,
                  (SELECT GROUP_CONCAT(DISTINCT source) FROM items WHERE cluster_id=c.id) AS source_names,
                  (SELECT GROUP_CONCAT(DISTINCT e.name) FROM items i
                     JOIN item_entities ie ON ie.item_id=i.id
                     JOIN entities e ON e.id=ie.entity_id
                    WHERE i.cluster_id=c.id AND e.kind='beat') AS beat_names
           FROM clusters c
           WHERE c.account=? AND c.last_seen_ts>=?
             AND (? IS NULL OR EXISTS (
                   SELECT 1 FROM items i
                     JOIN item_entities ie ON ie.item_id=i.id
                     JOIN entities e ON e.id=ie.entity_id
                    WHERE i.cluster_id=c.id AND e.kind='beat'
                      AND lower(e.name)=lower(?)))
           ORDER BY c.score DESC, c.last_seen_ts DESC LIMIT ?""",
        (cfg.account, since, beat, beat, top),
    ).fetchall()


def cmd_feeds(args) -> int:
    from .fetch.base import make_client, probe

    cfg = _account(args)
    conn = _db(cfg)
    rows = []
    sources = [s for s in cfg.sources if args.only is None or s.name == args.only]

    async def run() -> None:
        async with make_client(cfg) as client:
            for source in sources:
                result = await probe(client, source, cfg, conn)
                rows.append({**result, "name": source.name, "kind": source.kind, "tier": source.tier})
                status = "ok" if result["ok"] else "FAIL"
                print(
                    f"{status:5} {source.name:28} {result['ms']:6}ms "
                    f"{result['items']:3} items  {(result['error'] or '')[:80]}",
                    flush=True,
                )

    asyncio.run(run())
    failed = [r for r in rows if not r["ok"]]
    if failed and not args.only:
        console.print(f"\n[red]{len(failed)} failed of {len(rows)}[/red]")
        return 1
    return 0


def cmd_fetch(args) -> int:
    cfg = _account(args)
    results = asyncio.run(poll_once(cfg, only=args.only, once=not args.loop))
    total_new = sum(r.get("new_items", 0) for r in results)
    failed = [r for r in results if not r["ok"]]
    for r in results:
        mark = "ok " if r["ok"] else "ERR"
        print(f"{mark} {r['name']:28} {r.get('items', 0):3} fetched  {r.get('new_items', 0):3} new")
    print(f"\nnew items: {total_new}   failed: {len(failed)}")
    return 1 if failed and len(failed) == len(results) else 0


def cmd_run(args) -> int:
    cfg = _account(args)
    try:
        asyncio.run(run_forever(cfg))
    except KeyboardInterrupt:
        return 0
    return 0


def cmd_bot(args) -> int:
    cfg = _account(args)
    if args.status:
        telegram_status(cfg)
        return 0
    if args.preview:
        telegram_preview(cfg, since_h=args.since, limit=args.limit)
        return 0
    if args.test:
        message_id = asyncio.run(telegram_test(cfg))
        print(f"sent test message id={message_id}")
        return 0
    if args.once:
        stats = asyncio.run(telegram_once(cfg))
        print(f"sent={stats['sent']} skipped={stats['skipped']} failed={stats['failed']}")
        return 0
    try:
        asyncio.run(telegram_forever(cfg))
    except KeyboardInterrupt:
        return 0
    return 0


def cmd_inbox(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    rows = _rows(conn, cfg, args.since, args.top, args.beat)
    if args.json:
        print(json.dumps([dict(r) for r in rows], default=str, indent=2))
        return 0
    if not rows:
        console.print(f"[dim]no clusters in the last {args.since:g}h — run `agg fetch`[/dim]")
        return 0
    console.print(
        f"[bold]{cfg.account}[/bold] — last {args.since:g}h — {len(rows)} clusters",
        style="bold",
    )
    console.print(inbox_table(rows))
    console.print("[dim]agg packet <ID>  |  agg show <ID>  |  agg topics[/dim]")
    return 0


def cmd_digest(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    rows = _rows(conn, cfg, args.since, args.cap, args.beat)
    if not rows:
        console.print("[dim]nothing in window[/dim]")
        return 0
    console.print(
        f"[bold]While you were away[/bold] — {cfg.account} — "
        f"last {args.since:g}h — top {len(rows)} of window",
    )
    if args.group == "none":
        console.print(inbox_table(rows))
        return 0
    groups: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        if args.group == "beat":
            keys = [(row["beat_names"] or "Other").split(",")[0] or "Other"]
        else:
            keys = [row["archetype"] or "news"]
        for key in keys:
            groups.setdefault(key.strip(), []).append(row)
    for key in sorted(groups):
        console.print(f"\n[bold]{key}[/bold]")
        console.print(inbox_table(groups[key]))
    return 0


def cmd_topics(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    topics = compute_topics(
        conn, cfg,
        since_h=args.since,
        min_df=args.min_df,
        min_sources=args.min_sources,
        limit=args.limit,
    )
    if args.diff:
        key = f"topics_seen:{cfg.account}:{args.since:g}"
        previous = set(json.loads(meta_get(conn, key, "[]") or "[]"))
        topics = [t for t in topics if t.label not in previous]
        meta_set(conn, key, json.dumps([t.label for t in compute_topics(
            conn, cfg, since_h=args.since, min_df=args.min_df,
            min_sources=args.min_sources, limit=args.limit,
        )]))
    if args.json:
        print(json.dumps([t.as_dict() for t in topics], indent=2))
        return 0
    if not topics:
        console.print(
            "[dim]no topics matched — need more clusters, or lower --min-df/--min-sources[/dim]"
        )
        return 0
    console.print(
        f"[bold]{cfg.account} topics[/bold] — {args.since:g}h — "
        f"df>={args.min_df}, sources>={args.min_sources}",
    )
    console.print(topics_table([t.as_dict() for t in topics]))
    return 0


def cmd_show(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    show_cluster(conn, cfg, args.id)
    return 0


def cmd_packet(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    if args.fetch_body:
        filled = asyncio.run(fill_bodies(conn, cfg, args.id))
        if filled:
            print(f"[ fetched bodies for {filled} item(s) ]", file=sys.stderr)
    text, payload = build_packet(conn, cfg, args.id, max_chars=args.max_chars)
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(text)
    return 0


def cmd_status(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    console.print(status_panel(conn, cfg))
    if not args.quiet:
        console.print(sources_table(conn, cfg))
    return 0


def cmd_stats(args) -> int:
    cfg = _account(args)
    conn = _db(cfg)
    rescore(conn, cfg)
    console.print(stats_panel(conn, cfg, args.days))
    return 0


def cmd_site(args) -> int:
    from .site.db import (
        coverage,
        deploy_site,
        export_site,
        get_story,
        last_deploy,
        publish_story,
        set_slug,
        site_connection,
        snapshot,
        status,
        sync,
        unpublish_story,
    )
    from .site.media import MediaError, cache_hero

    cfg = _account(args)
    conn = site_connection(cfg)
    action = args.site_action

    if action == "serve":
        import uvicorn

        from .site.app import create_app

        console.print(
            f"[bold]{cfg.site.name}[/bold] admin on http://{cfg.site.host}:{cfg.site.port}/admin"
        )
        uvicorn.run(create_app(cfg), host=cfg.site.host, port=cfg.site.port, log_level="info")
        return 0

    if action == "sync":
        added = sync(
            conn, cfg, since_h=args.since,
            min_score=args.min_score, limit=args.limit,
        )
        print(f"new drafts: {added}")
        return 0

    if action == "status":
        state = status(conn, cfg)
        deploy = last_deploy(conn)
        print(f"stories: {state['counts']}")
        print(f"dirty: {state['dirty']}   repo: {state['repo']}")
        print(f"last deploy: {deploy['status'] if deploy else 'never'}"
              f" {deploy['message'] or deploy['error'] or '' if deploy else ''}")
        return 0

    if action == "coverage":
        cov = coverage(conn, cfg)
        for t in cov["targets"]:
            print(f"{t['key']:12} {t['count']:3}  target {t['low']}-{t['high']}")
        print(f"total: {cov['total']}")
        return 0

    if action == "export":
        result = export_site(conn, cfg)
        print(f"exported {result['stories']} stories to {cfg.root / cfg.site.repo_path}")
        return 0

    if action == "deploy":
        result = deploy_site(
            conn, cfg,
            push=not args.no_push,
            dry_run=args.dry_run,
            force=not args.if_dirty,
        )
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") not in {"failed", "busy"} else 1

    if action in {"publish", "unpublish"}:
        story = get_story(conn, args.id)
        if not story:
            console.print(f"[red]no story {args.id}[/red]")
            return 2
        try:
            if action == "unpublish":
                unpublish_story(conn, args.id, "cli")
                print(f"unpublished story {args.id}")
                return 0
            if not story["slug"]:
                set_slug(conn, args.id, story["headline"])
                conn.commit()
                story = get_story(conn, args.id)
                assert story is not None
            if story["hero_url"] and not story["hero_local"]:
                try:
                    filename = asyncio.run(cache_hero(cfg, story, str(story["slug"])))
                    if filename:
                        conn.execute(
                            "UPDATE stories SET hero_local=? WHERE id=?",
                            (filename, args.id),
                        )
                        conn.commit()
                except MediaError as exc:
                    print(f"image cache failed: {exc}", file=sys.stderr)
            snapshot(conn, cfg, args.id)
            publish_story(conn, args.id, "cli")
            print(f"published story {args.id} at /news/{story['slug']}/")
            return 0
        except (ValueError, MediaError) as exc:
            console.print(f"[red]{exc}[/red]")
            return 2

    console.print(f"[red]unknown site action {action}[/red]")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agg", description="Terminal news aggregator")
    parser.add_argument("--account", "-a", help="account name or path to config")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("feeds", help="source inventory and health")
    p.add_argument("action", nargs="?", choices=["check"], default="check")
    p.add_argument("--only")
    p.add_argument("--check", action="store_true", dest="check_flag")
    p.set_defaults(func=cmd_feeds)

    p = sub.add_parser("fetch", help="one poll cycle")
    p.add_argument("--only")
    p.add_argument("--loop", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("run", help="daemon loop (systemd)")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("bot", help="Telegram notification bot")
    p.add_argument("--once", action="store_true", help="process pending clusters and exit")
    p.add_argument("--preview", action="store_true", help="show alerts without sending")
    p.add_argument("--test", action="store_true", help="send a test message")
    p.add_argument("--status", action="store_true", help="show bot state")
    p.add_argument("--since", type=float, default=24.0, help="hours for --preview")
    p.add_argument("--limit", type=int, default=20, help="max alerts for --preview")
    p.set_defaults(func=cmd_bot)

    p = sub.add_parser("inbox", help="ranked review queue")
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--since", type=float, default=18.0, help="hours")
    p.add_argument("--beat", help="filter by beat entity, e.g. Robotics")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_inbox)

    p = sub.add_parser("digest", help="catch-up summary")
    p.add_argument("--since", type=float, default=12.0, help="hours")
    p.add_argument("--cap", type=int, default=30)
    p.add_argument("--beat", help="filter by beat entity, e.g. Robotics")
    p.add_argument("--group", choices=["none", "beat", "archetype"], default="none")
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("topics", help="trending keywords/topics")
    p.add_argument("--since", type=float, default=24.0, help="hours")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--min-df", type=int, default=2)
    p.add_argument("--min-sources", type=int, default=2)
    p.add_argument("--diff", action="store_true", help="only new entrants since last run")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_topics)

    p = sub.add_parser("show", help="cluster detail")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("packet", help="full drafting context for one cluster")
    p.add_argument("id", type=int)
    p.add_argument("--json", action="store_true")
    p.add_argument("--fetch-body", action="store_true", help="extract article text on demand")
    p.add_argument("--max-chars", type=int, default=4000)
    p.set_defaults(func=cmd_packet)

    p = sub.add_parser("status", help="is it running and are sources healthy")
    p.add_argument("--quiet", action="store_true", help="summary only")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("stats", help="volume and health")
    p.add_argument("--days", type=int, default=7)
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("site", help="static news site admin and deploy")
    site_sub = p.add_subparsers(dest="site_action", required=True)

    sp = site_sub.add_parser("serve", help="run the local admin app")
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("sync", help="turn recent clusters into drafts")
    sp.add_argument("--since", type=float, default=72.0, help="hours")
    sp.add_argument("--min-score", type=float, default=None)
    sp.add_argument("--limit", type=int, default=300)
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("status", help="site and deploy status")
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("coverage", help="published counts against the plan")
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("export", help="write published stories into the Astro repo")
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("deploy", help="export, build, commit, and push")
    sp.add_argument("--if-dirty", action="store_true", help="skip when nothing changed")
    sp.add_argument("--no-push", action="store_true")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("publish", help="publish a story by ID")
    sp.add_argument("id", type=int)
    sp.set_defaults(func=cmd_site)

    sp = site_sub.add_parser("unpublish", help="unpublish a story by ID")
    sp.add_argument("id", type=int)
    sp.set_defaults(func=cmd_site)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "feeds" and not getattr(args, "check", True):
        args.check = True
    try:
        return int(args.func(args) or 0)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2
    except TelegramError as exc:
        console.print(f"[red]{exc}[/red]")
        return 2
