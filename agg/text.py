from __future__ import annotations

import hashlib
import html
import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "ref", "ref_src", "ref_url", "fbclid", "gclid", "mc_cid",
    "mc_eid", "igshid", "s", "share", "sr_share", "cmpid", "smid",
}

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9][a-z0-9'+\-.!]*")

STOPWORDS = frozenset("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further had has have having he her here hers herself him
himself his how i if in into is it its itself just me more most my myself no
nor not now of off on once only or other our ours ourselves out over own same
she should so some such than that the their theirs them themselves then there
these they this those through to too under until up very was we were what when
where which while who whom why will with would you your yours yourself
yourselves says said say new now first last get got make makes made
""".split())


def now_ts() -> int:
    return int(time.time())


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(_TAG.sub(" ", text))
    return _WS.sub(" ", text).strip()


def canonical_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or "/"
    path = re.sub(r"/amp/?$", "", path) or "/"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k.lower() not in TRACKING]
    query.sort()
    return urlunsplit(("https", host, path, urlencode(query), ""))


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


def _h64(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big")


def simhash64(text: str) -> str:
    tokens = tokenize(text)
    if not tokens:
        return "0" * 16
    weights = [0] * 64
    for tok in tokens:
        h = _h64(tok)
        for i in range(64):
            weights[i] += 1 if (h >> i) & 1 else -1
    value = 0
    for i in range(64):
        if weights[i] > 0:
            value |= 1 << i
    return f"{value:016x}"


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


_NUM = re.compile(
    r"(?<!\w)([$€£]\s?\d[\d,.]*\s?(?:bn|b|m|k|million|billion|trillion)?"
    r"|\d[\d,.]*\s?%"
    r"|\d[\d,.]*\s?(?:million|billion|trillion|bn|bps|fps|GB|TB|MB|Hz|GHz|MHz|W|Wh|mAh|GB/s)"
    r"|(?:19|20)\d{2}(?:-\d{1,2}(?:-\d{1,2})?)?"
    r"|Q[1-4]\s?(?:FY)?\d{2,4})(?!\w)",
    re.IGNORECASE,
)


GENERIC_PROPER = frozenset("""
reveals revealed announces announced confirms confirmed report reports reported
model models update updates release released launches launching coming
available price prices raises raised drops drop best first last next week
month year today tomorrow yesterday here now how why what when where who watch
""".split())

_PROPER = re.compile(r"\b([A-Z][a-z0-9]+)\b")


def proper_tokens(text: str) -> set[str]:
    return {m.group(1).lower() for m in _PROPER.finditer(text or "")} - STOPWORDS


def extract_numbers(text: str, limit: int = 40) -> list[str]:
    seen: list[str] = []
    for m in _NUM.finditer(text or ""):
        val = m.group(0).strip()
        if val not in seen:
            seen.append(val)
        if len(seen) >= limit:
            break
    return seen


def money_value(text: str) -> float | None:
    m = re.search(r"[$€£]\s?(\d[\d,.]*)", text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def pct_value(text: str) -> float | None:
    m = re.search(r"(\d[\d,.]*)\s?%", text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def truncate(text: str, limit: int) -> str:
    text = text or ""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def fmt_age(ts: int | None, ref: int | None = None) -> str:
    if not ts:
        return "?"
    delta = max(0, (ref or now_ts()) - ts)
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}m"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}d"


def fmt_ts(ts: int | None) -> str:
    if not ts:
        return "?"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))


def sparkline(values: list[int]) -> str:
    if not values:
        return ""
    blocks = "▁▂▃▄▅▆▇█"
    peak = max(values) or 1
    return "".join(blocks[min(len(blocks) - 1, int(v / peak * (len(blocks) - 1)))] for v in values)


def slug(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit] or "item"
