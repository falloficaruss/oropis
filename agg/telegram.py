from __future__ import annotations

import asyncio
import html
import json
import sqlite3
from typing import Any

import httpx

from .config import AccountCfg
from .db import cluster_items, connect, meta_get, meta_set
from .score import rescore
from .text import fmt_age, now_ts, strip_html, truncate

ARCH_LABEL = {
    "research": "RESEARCH",
    "product": "PRODUCT",
    "deployment": "DEPLOYMENT",
    "funding": "FUNDING",
    "policy": "POLICY",
    "business": "BUSINESS",
    "news": "NEWS",
}

_WATERMARK = "telegram_last_cluster_id"
_LAST_RUN = "telegram_last_run_ts"
_CATCHUP = "telegram_catchup_since_ts"
_CATCHUP_ARMED = "telegram_catchup_armed_ts"


class TelegramError(RuntimeError):
    def __init__(
        self,
        message: str,
        retry_after: int | None = None,
        permanent: bool = False,
        fatal: bool = False,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.permanent = permanent
        self.fatal = fatal


class TelegramClient:
    def __init__(self, cfg: AccountCfg, client: httpx.AsyncClient | None = None):
        self.cfg = cfg
        self.token = cfg.telegram.bot_token.strip()
        self.chat_id = str(cfg.telegram.chat_id).strip()
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> TelegramClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.cfg.network.timeout_s))
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def send(self, text: str) -> int:
        if not self.token or not self.chat_id:
            raise TelegramError(
                "telegram bot_token/chat_id is not configured; set TELEGRAM_BOT_TOKEN "
                "and TELEGRAM_CHAT_ID"
            )
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(self.cfg.network.timeout_s))
            self._owns_client = True

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": self.cfg.telegram.disable_preview,
        }
        try:
            resp = await self._client.post(url, json=payload)
        except httpx.HTTPError as exc:
            raise TelegramError(f"telegram request failed: {type(exc).__name__}") from None

        if resp.status_code == 429:
            retry_after = 1
            try:
                retry_after = int((resp.json().get("parameters") or {}).get("retry_after") or 1)
            except (ValueError, TypeError):
                pass
            raise TelegramError("telegram rate limited", retry_after=max(1, retry_after))

        if resp.status_code >= 400:
            description = ""
            try:
                description = str(resp.json().get("description") or "")
            except (ValueError, TypeError):
                pass
            permanent = resp.status_code not in {500, 502, 503, 504}
            fatal = resp.status_code in {401, 403}
            raise TelegramError(
                f"telegram HTTP {resp.status_code}: {description}"[:300],
                permanent=permanent,
                fatal=fatal,
            )

        try:
            data = resp.json()
        except ValueError:
            raise TelegramError("telegram returned invalid JSON", permanent=True) from None
        if not data.get("ok"):
            raise TelegramError(
                f"telegram rejected message: {str(data.get('description') or '')}"[:300],
                permanent=True,
            )
        return int((data.get("result") or {}).get("message_id") or 0)


async def send_with_retry(
    client: TelegramClient, text: str, attempts: int = 3
) -> int:
    last: TelegramError | None = None
    for attempt in range(max(1, attempts)):
        try:
            return await client.send(text)
        except TelegramError as exc:
            last = exc
            if exc.permanent or attempt + 1 >= attempts:
                raise
            wait = exc.retry_after or (2 ** attempt)
            await asyncio.sleep(min(60, max(1, wait)))
    raise last or TelegramError("telegram send failed")


def _source_info(conn: sqlite3.Connection, cluster_id: int) -> tuple[list[str], float]:
    items = cluster_items(conn, cluster_id)
    sources: list[str] = []
    authority = 0.0
    for item in items:
        source = str(item["source"])
        if source not in sources:
            sources.append(source)
        authority = max(authority, float(item["authority"] or 0.0))
    return sources, authority


def _upcoming_only(conn: sqlite3.Connection, cluster_id: int) -> bool:
    rows = conn.execute(
        "SELECT extra_json FROM items WHERE cluster_id=?", (cluster_id,)
    ).fetchall()
    statuses = {
        json.loads(row["extra_json"] or "{}").get("status")
        for row in rows
    }
    statuses.discard(None)
    return bool(statuses) and statuses == {"upcoming"}


def qualifies(
    cfg: AccountCfg,
    row: Any,
    sources: list[str],
    authority: float,
    now: int | None = None,
    conn: sqlite3.Connection | None = None,
    max_age_h: float | None = None,
) -> tuple[bool, str]:
    now = now or now_ts()
    discovery_only = set(cfg.telegram.discovery_only_sources)
    if sources and not set(sources).difference(discovery_only):
        return False, "discovery only"
    age_limit_h = cfg.telegram.max_age_h if max_age_h is None else max_age_h
    score = float(row["score"] or 0.0)
    last_seen = int(row["last_seen_ts"] or 0)
    if conn is not None:
        if _upcoming_only(conn, int(row["id"])):
            return False, "scheduled"
    elif last_seen > now + 6 * 3600:
        return False, "scheduled"
    age_s = max(0, now - last_seen)
    if age_limit_h > 0 and age_s > age_limit_h * 3600:
        return False, "too old"
    if conn is not None and age_limit_h > 0:
        published = conn.execute(
            "SELECT MAX(published_ts) FROM items WHERE cluster_id=?",
            (int(row["id"]),),
        ).fetchone()[0]
        if published and now - int(published) > age_limit_h * 3600:
            return False, "too old"
    if score >= cfg.telegram.min_score:
        return True, "score"
    instant = set(cfg.telegram.instant_sources)
    if (instant.intersection(sources) or authority >= 0.85) and score >= cfg.telegram.official_min_score:
        return True, "official"
    return False, "below score"


def _beats(conn: sqlite3.Connection, cluster_id: int) -> list[str]:
    rows = conn.execute(
        """SELECT DISTINCT e.name FROM items i
           JOIN item_entities ie ON ie.item_id=i.id
           JOIN entities e ON e.id=ie.entity_id
           WHERE i.cluster_id=? AND e.kind='beat'
           ORDER BY e.name""",
        (cluster_id,),
    ).fetchall()
    return [str(r["name"]) for r in rows]


def format_cluster(conn: sqlite3.Connection, cfg: AccountCfg, row: sqlite3.Row) -> str:
    items = cluster_items(conn, int(row["id"]))
    sources: list[str] = []
    for item in items:
        source = str(item["source"])
        if source not in sources:
            sources.append(source)

    title = strip_html(row["canonical_title"]) or "Untitled"
    url = row["canonical_url"] or next((item["url"] for item in items if item["url"]), None)
    archetype = ARCH_LABEL.get(str(row["archetype"]), str(row["archetype"]).upper())
    beats = _beats(conn, int(row["id"]))
    label = f"{beats[0]} · {archetype}" if beats else archetype
    source_text = ", ".join(sources[:3]) if sources else "unknown"
    if len(sources) > 3:
        source_text += f" +{len(sources) - 3}"
    published = min((int(item["published_ts"] or 0) for item in items), default=0)
    found = min((int(item["fetched_ts"] or 0) for item in items), default=0)
    time_text = f"published {fmt_age(published)} ago" if published else "publication time unavailable"
    if found and published and found - published > 300:
        time_text += f" · found {fmt_age(found)} ago"

    lines = [
        f"<b>[{html.escape(label)}]</b> {html.escape(truncate(title, 180))}",
        f"{html.escape(source_text)} · {time_text} · #{int(row['id'])}",
    ]
    if url:
        lines.append(f'<a href="{html.escape(str(url), quote=True)}">Open</a>')
    return "\n".join(lines)


def _pending_rows(
    conn: sqlite3.Connection, cfg: AccountCfg, after_id: int, limit: int = 200
) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT c.* FROM clusters c
           LEFT JOIN telegram_notifications n ON n.cluster_id = c.id
           WHERE c.account=? AND c.id>? AND n.cluster_id IS NULL
           ORDER BY c.id ASC LIMIT ?""",
        (cfg.account, after_id, limit),
    ).fetchall()


def _recheck_rows(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    now: int,
    age_limit_h: float,
    limit: int = 200,
) -> list[sqlite3.Row]:
    """Clusters skipped for a low score that are still fresh enough to matter.

    A story often arrives single-source and takes the single-source penalty,
    then gains a corroborating source minutes later and rescores above the
    threshold. Without this second look those clusters stay dropped forever.
    """
    cutoff = 0 if age_limit_h <= 0 else now - int(age_limit_h * 3600)
    return conn.execute(
        """SELECT c.* FROM clusters c
           JOIN telegram_notifications n ON n.cluster_id = c.id
           WHERE c.account=? AND n.status='skipped' AND n.error='below score'
             AND c.last_seen_ts>=?
           ORDER BY c.id ASC LIMIT ?""",
        (cfg.account, cutoff, limit),
    ).fetchall()


def _record(
    conn: sqlite3.Connection,
    cfg: AccountCfg,
    row: sqlite3.Row,
    status: str,
    message_id: int | None = None,
    error: str | None = None,
) -> None:
    sent_ts = now_ts() if status == "sent" else None
    conn.execute(
        """INSERT INTO telegram_notifications
             (cluster_id, account, status, sent_ts, message_id, score, source_count, error)
           VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(cluster_id) DO UPDATE SET
             status=excluded.status, sent_ts=excluded.sent_ts,
             message_id=excluded.message_id, score=excluded.score,
             source_count=excluded.source_count, error=excluded.error""",
        (
            int(row["id"]),
            cfg.account,
            status,
            sent_ts,
            message_id,
            float(row["score"] or 0.0),
            int(row["source_count"] or 1),
            error,
        ),
    )
    conn.commit()


def _sent_count(conn: sqlite3.Connection, cfg: AccountCfg, since_ts: int) -> int:
    row = conn.execute(
        """SELECT COUNT(*) AS n FROM telegram_notifications
           WHERE account=? AND status='sent' AND sent_ts>=?""",
        (cfg.account, since_ts),
    ).fetchone()
    return int(row["n"] if row else 0)


def _within_limits(conn: sqlite3.Connection, cfg: AccountCfg, now: int) -> bool:
    if cfg.telegram.max_per_hour > 0 and _sent_count(conn, cfg, now - 3600) >= cfg.telegram.max_per_hour:
        return False
    if cfg.telegram.max_per_day > 0 and _sent_count(conn, cfg, now - 86400) >= cfg.telegram.max_per_day:
        return False
    return True


def _max_cluster_before(conn: sqlite3.Connection, cfg: AccountCfg, cutoff: int) -> int:
    row = conn.execute(
        """SELECT COALESCE(MAX(id), 0) AS n FROM clusters
           WHERE account=? AND last_seen_ts < ?""",
        (cfg.account, cutoff),
    ).fetchone()
    return int(row["n"] if row else 0)


def _watermark(conn: sqlite3.Connection, cfg: AccountCfg, now: int | None = None) -> int:
    now = now or now_ts()
    last_id = int(meta_get(conn, _WATERMARK, "0") or 0)
    backfill = max(0, cfg.telegram.backfill_minutes) * 60

    if last_id <= 0:
        last_id = _max_cluster_before(conn, cfg, now - backfill)
        meta_set(conn, _WATERMARK, str(last_id))
    return last_id


def _catchup_window(
    conn: sqlite3.Connection, cfg: AccountCfg, now: int
) -> tuple[bool, float]:
    """Detect downtime and widen the age window so missed alerts still send.

    A normal restart keeps the regular max_age_h freshness window. If the bot
    was down for longer than that, any cluster that arrived during the outage
    is allowed through, capped by the poller's own catch-up retention window.
    """
    last_run = int(meta_get(conn, _LAST_RUN, "0") or 0)
    backfill = max(0, cfg.telegram.backfill_minutes) * 60
    catchup_since = int(meta_get(conn, _CATCHUP, "0") or 0)
    armed = int(meta_get(conn, _CATCHUP_ARMED, "0") or 0)
    gap_s = now - last_run

    if not armed and last_run > 0 and gap_s > max(600, backfill):
        catchup_since = last_run
        armed = now
        meta_set(conn, _CATCHUP, str(catchup_since))
        meta_set(conn, _CATCHUP_ARMED, str(armed))
    if not armed:
        return False, cfg.telegram.max_age_h

    catchup_since = catchup_since or last_run or now
    age_limit_h = max(cfg.telegram.max_age_h, (now - catchup_since) / 3600 + 1.0)
    if cfg.poll.catchup_hours > 0:
        age_limit_h = min(float(cfg.poll.catchup_hours), age_limit_h)
    return True, age_limit_h


async def _handle_row(
    cfg: AccountCfg,
    client: TelegramClient,
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    now: int,
    age_limit_h: float,
) -> str:
    """Qualify, send, and record a single cluster.

    Returns ``sent``, ``skipped``, ``failed``, or ``deferred`` (retry later,
    without recording a decision).
    """
    cid = int(row["id"])
    sources, authority = _source_info(conn, cid)
    ok, reason = qualifies(
        cfg, row, sources, authority, now, conn, max_age_h=age_limit_h
    )
    if not ok:
        _record(conn, cfg, row, "skipped", error=reason)
        return "skipped"
    if not _within_limits(conn, cfg, now):
        print("[agg-bot] rate limit reached; deferring remaining alerts", flush=True)
        return "deferred"

    text = format_cluster(conn, cfg, row)
    try:
        message_id = await send_with_retry(client, text, cfg.telegram.max_attempts)
    except TelegramError as exc:
        if exc.fatal:
            raise
        if not exc.permanent:
            print(f"[agg-bot] send failed for #{cid}: {exc}; will retry", flush=True)
            return "deferred"
        _record(conn, cfg, row, "failed", error=str(exc))
        print(f"[agg-bot] dropped #{cid}: {exc}", flush=True)
        return "failed"

    _record(conn, cfg, row, "sent", message_id=message_id)
    print(
        f"[agg-bot] sent #{cid} score={float(row['score'] or 0):.2f} "
        f"sources={int(row['source_count'] or 1)}",
        flush=True,
    )
    return "sent"


async def process_pending(
    cfg: AccountCfg,
    client: TelegramClient,
    conn: sqlite3.Connection,
    now: int | None = None,
) -> dict[str, int]:
    now = now or now_ts()
    rescore(conn, cfg)
    catchup, age_limit_h = _catchup_window(conn, cfg, now)
    last_id = _watermark(conn, cfg, now)
    rows = _pending_rows(conn, cfg, last_id)
    sent = skipped = failed = 0

    if catchup and rows:
        since = int(meta_get(conn, _CATCHUP, "0") or 0)
        print(
            f"[agg-bot] catch-up after {fmt_age(since, now)} offline: "
            f"replaying up to {len(rows)} missed alert(s), age limit {age_limit_h:.0f}h",
            flush=True,
        )

    for row in rows:
        result = await _handle_row(cfg, client, conn, row, now, age_limit_h)
        if result == "deferred":
            break
        last_id = int(row["id"])
        meta_set(conn, _WATERMARK, str(last_id))
        if result == "sent":
            sent += 1
        elif result == "failed":
            failed += 1
        else:
            skipped += 1

    for row in _recheck_rows(conn, cfg, now, age_limit_h):
        result = await _handle_row(cfg, client, conn, row, now, age_limit_h)
        if result == "deferred":
            break
        if result == "sent":
            sent += 1
        elif result == "failed":
            failed += 1
        else:
            skipped += 1

    meta_set(conn, _LAST_RUN, str(now))
    if catchup and not _pending_rows(conn, cfg, last_id, limit=1):
        armed = int(meta_get(conn, _CATCHUP_ARMED, "0") or 0)
        last_poll = int(meta_get(conn, "last_poll_ts", "0") or 0)
        # Wait for the poller to run after catch-up was armed. Otherwise a boot
        # could clear catch-up before the aggregator has fetched missed items.
        if last_poll >= armed:
            meta_set(conn, _CATCHUP, "0")
            meta_set(conn, _CATCHUP_ARMED, "0")
            print("[agg-bot] catch-up complete", flush=True)
    return {"sent": sent, "skipped": skipped, "failed": failed}


def validate_config(cfg: AccountCfg) -> None:
    if not cfg.telegram.enabled:
        raise TelegramError("telegram notifications are disabled in config")
    if not cfg.telegram.bot_token or not cfg.telegram.chat_id:
        raise TelegramError(
            "telegram bot_token/chat_id missing; set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
        )


async def run_forever(cfg: AccountCfg) -> None:
    validate_config(cfg)
    conn = connect(cfg.root / cfg.db)
    try:
        async with TelegramClient(cfg) as client:
            print(f"[agg-bot] {cfg.account}: watching for new clusters", flush=True)
            while True:
                try:
                    stats = await process_pending(cfg, client, conn)
                    if stats["sent"]:
                        print(f"[agg-bot] {stats}", flush=True)
                except TelegramError:
                    raise
                except Exception as exc:
                    print(f"[agg-bot] loop error: {type(exc).__name__}: {exc}", flush=True)
                await asyncio.sleep(max(5, cfg.telegram.poll_interval_s))
    finally:
        conn.close()


async def run_once(cfg: AccountCfg) -> dict[str, int]:
    validate_config(cfg)
    conn = connect(cfg.root / cfg.db)
    try:
        async with TelegramClient(cfg) as client:
            return await process_pending(cfg, client, conn)
    finally:
        conn.close()


async def send_test(cfg: AccountCfg) -> int:
    async with TelegramClient(cfg) as client:
        return await client.send(
            f"<b>agg test</b>\n{html.escape(cfg.account)} notifications are working."
        )


def preview(cfg: AccountCfg, since_h: float = 24.0, limit: int = 20) -> int:
    conn = connect(cfg.root / cfg.db)
    try:
        rescore(conn, cfg)
        since = now_ts() - int(since_h * 3600)
        rows = conn.execute(
            """SELECT * FROM clusters WHERE account=? AND last_seen_ts>=?
               ORDER BY score DESC, last_seen_ts DESC LIMIT 500""",
            (cfg.account, since),
        ).fetchall()
        shown = 0
        for row in rows:
            sources, authority = _source_info(conn, int(row["id"]))
            ok, reason = qualifies(cfg, row, sources, authority, conn=conn)
            if not ok:
                continue
            print(format_cluster(conn, cfg, row))
            print(f"[score={float(row['score'] or 0):.2f} reason={reason}]")
            print("---")
            shown += 1
            if shown >= limit:
                break
        print(f"{shown} alert(s) would send from the last {since_h:g}h")
        return shown
    finally:
        conn.close()


def status(cfg: AccountCfg) -> None:
    conn = connect(cfg.root / cfg.db)
    try:
        now = now_ts()
        last_id = int(meta_get(conn, _WATERMARK, "0") or 0)
        last_run = int(meta_get(conn, _LAST_RUN, "0") or 0)
        pending = conn.execute(
            """SELECT COUNT(*) AS n FROM clusters c
               LEFT JOIN telegram_notifications n ON n.cluster_id=c.id
               WHERE c.account=? AND c.id>? AND n.cluster_id IS NULL""",
            (cfg.account, last_id),
        ).fetchone()["n"]
        sent_24h = _sent_count(conn, cfg, now - 86400)
        failed = conn.execute(
            "SELECT COUNT(*) AS n FROM telegram_notifications WHERE account=? AND status='failed'",
            (cfg.account,),
        ).fetchone()["n"]
        last = conn.execute(
            """SELECT n.cluster_id, n.sent_ts, c.canonical_title
               FROM telegram_notifications n
               LEFT JOIN clusters c ON c.id=n.cluster_id
               WHERE n.account=? AND n.status='sent'
               ORDER BY n.sent_ts DESC LIMIT 1""",
            (cfg.account,),
        ).fetchone()

        print(f"telegram: {'enabled' if cfg.telegram.enabled else 'disabled'}")
        print(f"token configured: {bool(cfg.telegram.bot_token)}")
        print(f"chat configured: {bool(cfg.telegram.chat_id)}")
        print(f"watermark: {last_id}   pending: {pending}   sent_24h: {sent_24h}   failed: {failed}")
        print(f"last run: {fmt_age(last_run) + ' ago' if last_run else 'never'}")
        if last:
            print(
                f"last sent: #{last['cluster_id']} at {fmt_age(last['sent_ts'])} ago — "
                f"{truncate(last['canonical_title'] or '', 80)}"
            )
        else:
            print("last sent: never")
    finally:
        conn.close()
