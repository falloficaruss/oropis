from __future__ import annotations

import json
from typing import Any

from markdown_it import MarkdownIt

from ..text import fmt_age, fmt_ts, now_ts

md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})


def render_markdown(text: str) -> str:
    return md.render(text or "")


def json_load(value: str | None, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default


def template_globals(cfg) -> dict[str, Any]:
    return {
        "site": cfg.site,
        "fmt_age": fmt_age,
        "fmt_ts": fmt_ts,
        "now_ts": now_ts,
        "json_load": json_load,
        "render_markdown": render_markdown,
    }
