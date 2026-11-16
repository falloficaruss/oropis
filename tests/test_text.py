from __future__ import annotations

from agg.text import (
    canonical_url,
    extract_numbers,
    hamming,
    jaccard,
    proper_tokens,
    simhash64,
    sparkline,
    strip_html,
    tokenize,
)


def test_canonical_url_strips_tracking_and_sorts():
    a = canonical_url("https://www.Example.com/path/?utm_source=x&b=2&a=1#frag")
    b = canonical_url("http://example.com/path?a=1&b=2")
    assert a == "https://example.com/path?a=1&b=2"
    assert a == b


def test_canonical_url_strips_amp():
    assert canonical_url("https://x.com/a/amp") == "https://x.com/a"


def test_strip_html():
    assert strip_html("<p>Hello&nbsp;<b>world</b></p>") == "Hello world"


def test_simhash_identical_and_different():
    a = simhash64("Nintendo Switch 2 price revealed at retail")
    b = simhash64("Nintendo Switch 2 price revealed at retail")
    c = simhash64("Capcom announces a new Mega Man game")
    assert hamming(a, b) == 0
    assert hamming(a, c) > 4


def test_jaccard():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard(set(), {"a"}) == 0.0


def test_tokenize_drops_stopwords():
    assert tokenize("The new game is out now") == ["game"]


def test_proper_tokens():
    tokens = proper_tokens("Nintendo reveals Switch 2 at the event")
    assert "nintendo" in tokens
    assert "switch" in tokens
    assert "the" not in tokens


def test_extract_numbers():
    nums = extract_numbers("Price drops 30% to $48.99 on 2026-11-14, 120fps")
    assert "30%" in nums
    assert "$48.99" in nums
    assert "2026-11-14" in nums


def test_sparkline_shapes():
    line = sparkline([0, 1, 2, 3, 4])
    assert len(line) == 5
    assert line.startswith("▁")
    assert line.endswith("█")
