from __future__ import annotations

import asyncio

import httpx

from agg.config import AccountCfg, SourceCfg
from agg.fetch.base import FetchCtx
from agg.fetch.web import fetch, parse_items


MARKUP = """
<main>
  <article><a href="/news/first"><time>October 30, 2026</time><h2>First update</h2><p>Official details</p></a></article>
  <article><a href="/news/first"><time>October 30, 2026</time><h2>First update</h2></a></article>
</main>
"""


def _source() -> SourceCfg:
    return SourceCfg(
        name="official", kind="web", url="https://example.com/news",
        options={
            "item_xpath": "//article",
            "title_xpath": ".//h2",
            "summary_xpath": ".//p",
            "link_xpath": ".//a/@href",
            "published_xpath": ".//time",
            "date_formats": ["%B %d, %Y"],
            "url_base": "https://example.com",
        },
    )


def test_web_parser_extracts_and_deduplicates_official_articles():
    items = parse_items(MARKUP, _source())
    assert len(items) == 1
    assert items[0].title == "First update"
    assert items[0].url == "https://example.com/news/first"
    assert items[0].summary == "Official details"
    assert items[0].extra["source_type"] == "official_web"
    assert items[0].published_ts == 1793318400


def test_web_fetch_uses_the_configured_page():
    async def run():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, text=MARKUP)))
        try:
            return await fetch(FetchCtx(client, AccountCfg(account="oropis"), None), _source())
        finally:
            await client.aclose()

    assert len(asyncio.run(run()).items) == 1
