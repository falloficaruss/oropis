from __future__ import annotations

from agg.config import SourceCfg
from agg.fetch.telegram import parse_messages
from agg.fetch.x import parse_statuses
from agg.text import now_ts


def test_x_parser_keeps_text_media_and_engagement():
    now = now_ts()
    payload = {
        "results": [
            {
                "type": "status",
                "id": "123",
                "url": "https://x.com/OpenAI/status/123",
                "text": "GPT-5.5 rolls out with a new reasoning mode.",
                "created_timestamp": now - 600,
                "author": {"screen_name": "OpenAI", "name": "OpenAI", "followers": 3000000},
                "likes": 1200,
                "reposts": 90,
                "media": {"all": [{"type": "photo", "url": "https://pbs.twimg.com/media/test.jpg"}]},
            }
        ]
    }
    source = SourceCfg(name="ai_openai_x", kind="x", options={"limit": 10, "max_age_h": 72})
    items = parse_statuses("OpenAI", payload, source)
    assert len(items) == 1
    assert items[0].extra["source_type"] == "x"
    assert items[0].extra["likes"] == 1200
    assert items[0].media[0]["url"] == "https://pbs.twimg.com/media/test.jpg"
    assert items[0].guid == "x:OpenAI:123"


def test_x_parser_drops_posts_outside_age_window():
    payload = {
        "results": [
            {
                "type": "status",
                "id": "old",
                "text": "Old robotics news",
                "created_timestamp": now_ts() - 10 * 86400,
                "author": {"screen_name": "old_robotics"},
            }
        ]
    }
    source = SourceCfg(name="old_robotics_x", kind="x", options={"max_age_h": 72})
    assert parse_statuses("old_robotics", payload, source) == []


def test_telegram_parser_extracts_public_channel_posts():
    markup = '''
    <div class="tgme_widget_message_wrap">
      <div class="tgme_widget_message" data-post="OpenAI/42">
        <a class="tgme_widget_message_date" href="https://t.me/OpenAI/42">
          <time datetime="2026-11-03T10:00:00+00:00"></time>
        </a>
        <div class="tgme_widget_message_text">A new reasoning model is live. <b>Evaluation details</b> follow.</div>
        <a class="tgme_widget_message_photo_wrap" style="background-image:url('https://cdn.example.com/model.jpg')"></a>
      </div>
    </div>
    '''
    source = SourceCfg(name="ai_openai_telegram", kind="telegram", options={"channel": "OpenAI", "limit": 5})
    items = parse_messages(markup, "OpenAI", source)
    assert len(items) == 1
    assert "Evaluation details" in items[0].summary
    assert items[0].url == "https://t.me/OpenAI/42"
    assert items[0].media[0]["url"] == "https://cdn.example.com/model.jpg"
