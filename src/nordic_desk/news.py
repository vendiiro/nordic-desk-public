"""Free, non-paywalled news per candidate: GDELT DOC API and Yahoo `Ticker.news`, merged, text extracted locally.

Paywalled sites (config/news.toml) are skipped, never bypassed; robots.txt is respected and page requests are spaced.
Extracted text is cached under data/news/articles/ (spec: docs/superpowers/specs/2026-11-20-idea-discovery-design.md, goal 2).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlparse

CACHE = Path("data/news/articles")
UA = "nordic-desk/0.1 (personal research tool)"
MAX_TEXT = 6000  # characters per article sent to the model: bounds the cost of one brief
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SourceError(RuntimeError):
    """A news source did not answer: the run stops rather than write a thinner or empty brief."""


SUFFIX = re.compile(r",?\s+(and company|inc\.?|incorporated|corp\.?|corporation|co\.?|company|ltd\.?|limited|plc|n\.v\.|ag|s\.a\.|sa|"
                    r"holdings?|group|oyj|abp)$", re.I)


def query_name(name: str) -> str:
    """Company name without legal suffixes, as people write it in news."""
    prev = None
    while prev != name:
        prev, name = name, SUFFIX.sub("", name.strip())
    return name


def http_get(url: str) -> str:
    from urllib.request import Request, urlopen

    with urlopen(Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def gdelt_articles(name: str, days: int, get: Callable[[str], str] = http_get) -> list[dict] | None:
    """Articles, [] when GDELT found none, None when it did not answer (rate limit, timeout, error)."""
    q = quote(f'"{query_name(name)}" sourcelang:english', safe="")
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=artlist&format=json&maxrecords=50&timespan={days}d&sort=datedesc"
    try:
        rows = json.loads(get(url)).get("articles") or []
    except (OSError, ValueError):  # network failure, or GDELT's plain-text answer to rate limits and errors
        return None
    d = lambda s: f"{s[:4]}-{s[4:6]}-{s[6:8]}" if s else ""
    return [{"url": r["url"], "title": r.get("title") or "", "date": d(r.get("seendate") or ""), "sites": [r.get("domain") or urlparse(r["url"]).hostname]}
            for r in rows if r.get("url", "").startswith("http")]


def yf_news(ticker: str) -> list[dict]:
    import yfinance as yf

    return yf.Ticker(ticker).news or []


def yahoo_articles(ticker: str, fetch: Callable[[str], list[dict]] = yf_news) -> list[dict]:
    out = []
    for n in fetch(ticker):
        c = n.get("content") or {}
        url = (c.get("canonicalUrl") or {}).get("url") or ""
        if url.startswith("http"):
            out.append({"url": url, "title": c.get("title") or "", "date": (c.get("pubDate") or "")[:10],
                        "sites": [(c.get("provider") or {}).get("displayName") or urlparse(url).hostname]})
    return out


def merge(articles: list[dict]) -> list[dict]:
    """One item per story: the same headline on several sites keeps the first link and lists every site."""
    seen: dict[str, dict] = {}
    for a in articles:
        key = re.sub(r"[^a-z0-9]+", " ", a["title"].lower()).strip() or a["url"]
        if key in seen:
            seen[key]["sites"] += [s for s in a["sites"] if s not in seen[key]["sites"]]
        else:
            seen[key] = {**a, "sites": list(a["sites"])}
    return list(seen.values())


@lru_cache(maxsize=256)
def _robots(origin: str):
    from urllib.robotparser import RobotFileParser

    rp = RobotFileParser(origin + "/robots.txt")
    try:
        rp.read()
    except Exception:
        return None  # robots.txt unreachable: treated as no rules
    return rp


def robots_ok(url: str) -> bool:
    u = urlparse(url)
    rp = _robots(f"{u.scheme}://{u.netloc}")
    return rp is None or rp.can_fetch(UA, url)


def fetch_page(url: str) -> str | None:
    import trafilatura

    html = trafilatura.fetch_url(url)
    return trafilatura.extract(html) if html else None


def _paywalled(url: str, domains: list[str]) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def collect(ticker: str, name: str, cfg: dict, cache_dir: Path = CACHE, get=http_get, yahoo=yf_news,
            fetch_page=fetch_page, robots_ok=robots_ok, sleep=time.sleep) -> list[dict]:
    """Articles of the last `days` with full text, newest first, numbered 1..n for the model to cite."""
    found = gdelt_articles(name, cfg["days"], get=get)
    sleep(5)  # GDELT allows one request every 5 seconds
    if found is None:
        raise SourceError("GDELT did not answer (rate limit or network); try again in a minute")
    try:
        yahoo_items = yahoo_articles(ticker, fetch=yahoo)
    except Exception as e:
        raise SourceError(f"Yahoo news did not answer: {e}") from e
    dated = [a for a in merge(yahoo_items + found) if DATE.match(a["date"])]  # an undated article cannot be placed in time
    items = sorted(dated, key=lambda a: a["date"], reverse=True)
    out = []
    for a in items:
        if len(out) >= cfg["max_articles"]:
            break
        if _paywalled(a["url"], cfg["paywall"]):
            continue
        f = Path(cache_dir) / (hashlib.sha1(a["url"].encode()).hexdigest() + ".json")
        if f.exists():
            text = json.loads(f.read_text(encoding="utf-8"))["text"]
        else:
            if not robots_ok(a["url"]):
                continue
            try:
                text = fetch_page(a["url"])
            except Exception:
                text = None
            sleep(1)
            if text is None:
                continue
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps({"url": a["url"], "text": text}), encoding="utf-8")
        if len(text) < cfg["min_chars"]:  # too short to be the full article: paywall teaser or a stub
            continue
        out.append({**a, "id": len(out) + 1, "text": text[:MAX_TEXT]})
    return out
