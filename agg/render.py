from __future__ import annotations

import json
import sqlite3
from urllib.parse import urlsplit

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import AccountCfg
from .db import cluster_items, cluster_row, meta_get
from .text import (
    extract_numbers,
    fmt_age,
    fmt_ts,
    now_ts,
    sparkline,
    strip_html,
    truncate,
)

console = Console()

BEAT_LABEL = {
    "AI": "AI",
    "Robotics": "Robotics",
}

ARCH_LABEL = {
    "research": "research",
    "product": "product",
    "deployment": "deploy",
    "funding": "funding",
    "policy": "policy",
    "business": "biz",
    "news": "news",
}


def domain(url: str | None) -> str:
    if not url:
        return "?"
    try:
        host = urlsplit(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return "?"


def _sources_for(conn: sqlite3.Connection, cluster_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT source FROM items WHERE cluster_id=? ORDER BY source",
        (cluster_id,),
    ).fetchall()
    return [r["source"] for r in rows]


def inbox_table(rows: list[sqlite3.Row], show_sources: bool = False) -> Table:
    table = Table(title=None, box=None, header_style="bold", pad_edge=False)
    table.add_column("ID", justify="right", style="dim", width=5)
    table.add_column("Score", justify="right", width=5)
    table.add_column("Age", justify="right", width=4)
    table.add_column("Src", justify="right", width=3)
    table.add_column("Beat", width=9, style="cyan")
    table.add_column("Arch", width=7)
    table.add_column("Title", overflow="fold")
    if show_sources:
        table.add_column("Sources", style="dim", overflow="ellipsis", no_wrap=True, width=22)
    for row in rows:
        cells = [
            str(row["id"]),
            f"{row['score']:.2f}",
            fmt_age(row["last_seen_ts"]),
            str(row["source_count"]),
            _beats_inline(row)[0],
            ARCH_LABEL.get(row["archetype"], row["archetype"]),
            truncate(row["canonical_title"], 96),
        ]
        if show_sources:
            cells.append(",".join(_sources_for_inline(row)))
        table.add_row(*cells)
    return table


def _sources_for_inline(row: sqlite3.Row) -> list[str]:
    raw = row["source_names"] if "source_names" in row.keys() else ""
    return [s for s in (raw or "").split(",") if s]


def _beats_inline(row: sqlite3.Row) -> list[str]:
    raw = row["beat_names"] if "beat_names" in row.keys() else ""
    beats = [BEAT_LABEL.get(b, b) for b in (raw or "").split(",") if b]
    return beats or ["-"]


def topics_table(topics: list[dict]) -> Table:
    table = Table(box=None, header_style="bold", pad_edge=False)
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Topic", overflow="fold")
    table.add_column("Docs", justify="right", width=4)
    table.add_column("Src", justify="right", width=3)
    table.add_column("Burst", justify="right", width=5)
    table.add_column("Score", justify="right", width=6)
    table.add_column("24h", width=24, style="cyan")
    table.add_column("Also", style="dim", overflow="fold")
    for i, topic in enumerate(topics, 1):
        table.add_row(
            str(i),
            topic["label"],
            str(topic["df"]),
            str(topic["sources"]),
            f"{topic['burst']:.1f}x",
            f"{topic['score']:.1f}",
            sparkline(topic["hourly"]),
            ", ".join(m for m in topic["members"] if m != topic["label"])[:48],
        )
    return table


def feeds_table(rows: list[dict]) -> Table:
    table = Table(box=None, header_style="bold", pad_edge=False)
    table.add_column("Source")
    table.add_column("Kind", style="dim")
    table.add_column("Tier", justify="right", width=4)
    table.add_column("Status", width=8)
    table.add_column("ms", justify="right", width=6)
    table.add_column("Items", justify="right", width=5)
    table.add_column("Latest", width=6)
    table.add_column("Error", style="red", overflow="fold")
    for row in rows:
        status = "[green]ok[/green]" if row["ok"] else "[red]FAIL[/red]"
        if row.get("not_modified"):
            status = "[cyan]304[/cyan]"
        table.add_row(
            row["name"],
            row["kind"],
            str(row["tier"]),
            status,
            str(row["ms"]),
            str(row["items"]),
            fmt_age(row["latest_ts"]) if row["latest_ts"] else "-",
            (row["error"] or "")[:60],
        )
    return table


def stats_panel(conn: sqlite3.Connection, cfg: AccountCfg, days: int = 7) -> Panel:
    since = now_ts() - days * 86400
    items = conn.execute(
        "SELECT COUNT(*) AS n FROM items WHERE fetched_ts>=?", (since,)
    ).fetchone()["n"]
    clusters = conn.execute(
        "SELECT COUNT(*) AS n FROM clusters WHERE account=? AND last_seen_ts>=?",
        (cfg.account, since),
    ).fetchone()["n"]
    ratio = (items / clusters) if clusters else 0
    archetypes = conn.execute(
        """SELECT archetype, COUNT(*) AS n FROM clusters
           WHERE account=? AND last_seen_ts>=? GROUP BY archetype ORDER BY n DESC""",
        (cfg.account, since),
    ).fetchall()
    sources = conn.execute(
        """SELECT source, COUNT(*) AS n FROM items WHERE fetched_ts>=?
           GROUP BY source ORDER BY n DESC LIMIT 8""",
        (since,),
    ).fetchall()
    body = (
        f"items: {items}   clusters: {clusters}   dedup ratio: {ratio:.2f}x   window: {days}d\n\n"
        "archetypes: "
        + "  ".join(f"{r['archetype']}={r['n']}" for r in archetypes)
        + "\n\ntop sources: "
        + "  ".join(f"{r['source']}={r['n']}" for r in sources)
    )
    return Panel(body, title=f"{cfg.account} stats", border_style="dim")


def show_cluster(conn: sqlite3.Connection, cfg: AccountCfg, cluster_id: int) -> None:
    cluster = cluster_row(conn, cluster_id)
    if not cluster:
        console.print(f"[red]no cluster {cluster_id}[/red]")
        return
    items = cluster_items(conn, cluster_id)
    console.print(
        Panel(
            f"[bold]{cluster['canonical_title']}[/bold]\n"
            f"id={cluster['id']}  archetype={cluster['archetype']}  score={cluster['score']:.2f}  "
            f"items={cluster['item_count']}  sources={cluster['source_count']}\n"
            f"first={fmt_ts(cluster['first_seen_ts'])}  last={fmt_ts(cluster['last_seen_ts'])}  "
            f"url={cluster['canonical_url'] or '-'}",
            border_style="cyan",
        )
    )
    for item in items:
        console.print(
            f"[bold cyan][{item['source']}][/bold cyan] {fmt_age(item['published_ts'])} ago  "
            f"{item['kind']}  {item['url'] or ''}"
        )
        console.print(f"  {item['title']}")
        if item["summary"]:
            console.print(f"  [dim]{truncate(item['summary'], 400)}[/dim]")
        media = json.loads(item["media_json"] or "[]")
        for m in media[:3]:
            console.print(f"  [magenta]media[/magenta] {m.get('url')}")


def _related(conn: sqlite3.Connection, cfg: AccountCfg, cluster_id: int, limit: int = 5):
    rows = conn.execute(
        """SELECT DISTINCT c.id, c.canonical_title, c.score, c.last_seen_ts
           FROM clusters c
           JOIN items i ON i.cluster_id = c.id
           JOIN item_entities ie ON ie.item_id = i.id
           WHERE c.account=? AND c.id != ?
             AND ie.entity_id IN (
                SELECT ie2.entity_id FROM items i2
                JOIN item_entities ie2 ON ie2.item_id = i2.id
                WHERE i2.cluster_id = ?)
             AND c.last_seen_ts >= ?
           ORDER BY c.score DESC LIMIT ?""",
        (cfg.account, cluster_id, cluster_id, now_ts() - 72 * 3600, limit),
    ).fetchall()
    return rows


def _entities(conn: sqlite3.Connection, cluster_id: int) -> list[tuple[str, str]]:
    rows = conn.execute(
        """SELECT DISTINCT e.name, e.kind FROM items i
           JOIN item_entities ie ON ie.item_id = i.id
           JOIN entities e ON e.id = ie.entity_id
           WHERE i.cluster_id=? ORDER BY e.kind, e.name""",
        (cluster_id,),
    ).fetchall()
    return [(r["kind"], r["name"]) for r in rows]


def _angles(cluster: sqlite3.Row, items: list[sqlite3.Row]) -> list[str]:
    primary = items[0]
    title = truncate(strip_html(primary["title"]), 180)
    numbers = extract_numbers(primary["summary"] or primary["body"] or "")
    arch = cluster["archetype"]
    angles: list[str] = [title]
    if arch == "research":
        angles.append("Name the institution, method, benchmark, and main limitation.")
        angles.append("Lead with the result, not the model name; define the metric.")
    elif arch == "product":
        angles.append("Lead with the capability, availability, and price; no adjectives.")
        angles.append("Say what it replaces and what still does not work.")
    elif arch == "deployment":
        angles.append("Lead with where, at what scale, run by whom, and the measured result.")
        angles.append("Separate a pilot from production; name the site and operator.")
    elif arch == "funding":
        if numbers:
            angles.append("Key figures: " + ", ".join(numbers[:5]))
        angles.append("Lead with the amount, investor, and valuation; explain the gap it funds.")
    elif arch == "policy":
        angles.append("Name the jurisdiction, rule, effective date, and who must comply.")
        angles.append("Separate what is proposed from what is now enforceable.")
    elif arch == "business":
        if numbers:
            angles.append("Key figures: " + ", ".join(numbers[:5]))
        angles.append("Lead with the money or org impact, not the announcement.")
    else:
        angles.append("Lead with what changed and why it matters.")
        if numbers:
            angles.append("Numbers available: " + ", ".join(numbers[:5]))
    angles.append("Add one sentence of context the headline omits.")
    return angles


def build_packet(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    cluster_id: int,
    max_chars: int = 4000,
    include_related: bool = True,
) -> tuple[str, dict]:
    cluster = cluster_row(conn, cluster_id)
    if not cluster:
        raise SystemExit(f"no cluster {cluster_id}")
    items = cluster_items(conn, cluster_id)
    primary = items[0]
    extra = json.loads(primary["extra_json"] or "{}")
    entities = _entities(conn, cluster_id)
    media: list[str] = []
    for item in items:
        for m in json.loads(item["media_json"] or "[]"):
            url = m.get("url")
            if url and url not in media:
                media.append(url)
    numbers = extract_numbers(
        " ".join(f"{i['title']} {i['summary']}" for i in items)
    )
    angles = _angles(cluster, items)
    related = _related(conn, cfg, cluster_id) if include_related else []

    body = primary["body"] or primary["summary"]
    body = strip_html(body)[:max_chars]

    lines: list[str] = [
        f"# PACKET {cfg.account}/{cluster_id}",
        f"archetype: {cluster['archetype']} | score: {cluster['score']:.2f} | "
        f"sources: {cluster['source_count']} | items: {cluster['item_count']}",
        f"first seen: {fmt_ts(cluster['first_seen_ts'])} | last seen: {fmt_ts(cluster['last_seen_ts'])} "
        f"| age: {fmt_age(cluster['last_seen_ts'])}",
        "",
        "## Titles as published",
    ]
    for item in items:
        lines.append(f"- [{item['source']}] {item['title']}")
    lines += ["", "## Links"]
    for item in items:
        lines.append(f"- {item['source']}: {item['url'] or '-'}")
    if entities:
        lines += ["", "## Entities"]
        lines.append(" | ".join(f"{kind}:{name}" for kind, name in entities))
    if numbers:
        lines += ["", "## Key numbers"]
        lines.append(", ".join(numbers[:20]))
    if extra:
        keys = {k: v for k, v in extra.items() if v not in (None, "", [])}
        if keys:
            lines += ["", "## Source metadata"]
            lines.append(json.dumps(keys, ensure_ascii=False))
    lines += ["", "## Primary text", body or "(no body captured)"]
    if media:
        lines += ["", "## Media"]
        lines += [f"- {url}" for url in media[:6]]
    lines += ["", "## Suggested angles"]
    lines += [f"- {angle}" for angle in angles]
    attribution = extra.get("handle") or domain(primary["url"]) or primary["source"]
    lines += [
        "",
        "## Attribution",
        f"via {attribution} — {primary['url'] or ''}".strip(),
        "",
        "## Style",
        "280 chars max | no hashtags | no 'BREAKING' | hook <= 15 words | one idea per post",
        f"voice: {cfg.voice.get('tone', 'direct')}",
    ]
    if related:
        lines += ["", "## Related (72h)"]
        for row in related:
            lines.append(f"- #{row['id']} ({row['score']:.2f}) {truncate(row['canonical_title'], 80)}")

    text = "\n".join(lines)
    payload = {
        "account": cfg.account,
        "cluster_id": cluster_id,
        "archetype": cluster["archetype"],
        "score": cluster["score"],
        "title": cluster["canonical_title"],
        "items": [
            {
                "source": i["source"],
                "kind": i["kind"],
                "title": i["title"],
                "url": i["url"],
                "summary": i["summary"],
                "published_ts": i["published_ts"],
                "media": json.loads(i["media_json"] or "[]"),
                "extra": json.loads(i["extra_json"] or "{}"),
            }
            for i in items
        ],
        "entities": [{"kind": k, "name": n} for k, n in entities],
        "numbers": numbers,
        "media": media,
        "angles": angles,
        "attribution": attribution,
    }
    return text, payload


def sources_table(conn: sqlite3.Connection, cfg: AccountCfg) -> Table:
    rows = conn.execute(
        """SELECT name, kind, interval_s, last_ok_ts, last_item_ts,
                  fail_count, last_error, enabled
           FROM sources ORDER BY name"""
    ).fetchall()
    now = now_ts()
    table = Table(box=None, header_style="bold", pad_edge=False)
    table.add_column("Source", no_wrap=True, min_width=16)
    table.add_column("Age", justify="right", width=4, no_wrap=True)
    table.add_column("State", width=7, no_wrap=True)
    table.add_column("Note", overflow="ellipsis", no_wrap=True)
    for row in rows:
        interval = int(row["interval_s"] or cfg.poll.default_interval_s)
        last_ok = int(row["last_ok_ts"] or 0)
        stale = not last_ok or (now - last_ok) > interval * 3
        if not row["enabled"]:
            status = "[dim]off[/dim]"
        elif row["fail_count"] and int(row["fail_count"]) >= 3:
            status = "[red]failing[/red]"
        elif stale:
            status = "[yellow]stale[/yellow]"
        else:
            status = "[green]ok[/green]"
        fails = int(row["fail_count"] or 0)
        note = f"fails={fails} {(row['last_error'] or '')[:40]}" if fails else ""
        table.add_row(
            row["name"],
            fmt_age(row["last_item_ts"]) if row["last_item_ts"] else "-",
            status,
            note,
        )
    return table


def status_panel(conn: sqlite3.Connection, cfg: AccountCfg) -> Panel:
    last_poll = int(meta_get(conn, "last_poll_ts", "0") or 0)
    last_run = conn.execute("SELECT MAX(finished_ts) FROM runs").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    day = conn.execute(
        "SELECT COUNT(*) FROM items WHERE fetched_ts>=?", (now_ts() - 86400,)
    ).fetchone()[0]
    clusters = conn.execute(
        "SELECT COUNT(*) FROM clusters WHERE account=? AND last_seen_ts>=?",
        (cfg.account, now_ts() - 86400),
    ).fetchone()[0]
    enabled = conn.execute("SELECT COUNT(*) FROM sources WHERE enabled=1").fetchone()[0]
    failing = conn.execute(
        "SELECT COUNT(*) FROM sources WHERE fail_count>=3"
    ).fetchone()[0]
    freshness = fmt_age(last_poll) if last_poll else "never"
    body = (
        f"last poll: {freshness} ago   last run finished: "
        f"{fmt_age(last_run) if last_run else 'never'} ago\n"
        f"items: {total} total / {day} in 24h   clusters(24h): {clusters}   "
        f"sources: {enabled} enabled / {failing} failing"
    )
    return Panel(body, title=f"{cfg.account} status", border_style="cyan")
