from __future__ import annotations

import asyncio
import sqlite3

from .config import AccountCfg
from .fetch.base import fetch_body
from .text import strip_html, truncate


async def fill_bodies(
    conn: sqlite3.Connection, cfg: AccountCfg, cluster_id: int, max_items: int = 3
) -> int:
    rows = conn.execute(
        """SELECT id, url, summary FROM items
           WHERE cluster_id=? AND TRIM(COALESCE(body,''))='' AND url IS NOT NULL
           ORDER BY published_ts LIMIT ?""",
        (cluster_id, max_items),
    ).fetchall()
    filled = 0
    sem = asyncio.Semaphore(3)

    async def one(row: sqlite3.Row) -> None:
        nonlocal filled
        async with sem:
            body = await fetch_body(row["url"], cfg)
            if body:
                conn.execute(
                    "UPDATE items SET body=? WHERE id=?",
                    (truncate(strip_html(body), 20000), row["id"]),
                )
                filled += 1

    await asyncio.gather(*(one(r) for r in rows))
    conn.commit()
    return filled
