import json

import pytest

from nordic_desk.news import collect, gdelt_articles, merge, query_name, yahoo_articles

CFG = {"days": 30, "max_articles": 20, "min_chars": 200, "paywall": ["paywalled.example"]}
LONG = "Invented article text about Nordlys Systems and its cooling units. " * 10


def gdelt_json(*rows):
    return json.dumps({"articles": [{"url": u, "title": t, "seendate": d, "domain": s, "language": "English"}
                                    for u, t, d, s in rows]})


def test_query_name_strips_legal_suffixes():
    assert query_name("Nordlys Systems Inc.") == "Nordlys Systems"
    assert query_name("Eli Lilly and Company") == "Eli Lilly"
    assert query_name("Example Holdings Corporation") == "Example"


def test_gdelt_parsed():
    seen = []
    get = lambda url: seen.append(url) or gdelt_json(("https://a.example/1", "Nordlys wins contract", "20261119T233000Z", "a.example"))
    rows = gdelt_articles("Nordlys Systems", 30, get=get)
    assert rows == [{"url": "https://a.example/1", "title": "Nordlys wins contract", "date": "2026-11-19", "sites": ["a.example"]}]
    assert "%22Nordlys%20Systems%22" in seen[0] and "timespan=30d" in seen[0]


def test_gdelt_failure_is_none_not_empty():
    assert gdelt_articles("X", 30, get=lambda url: "Please limit requests to one every 5 seconds") is None

    def down(url):
        raise OSError("timed out")
    assert gdelt_articles("X", 30, get=down) is None
    assert gdelt_articles("X", 30, get=lambda url: json.dumps({})) == []  # answered, nothing found


def test_source_failure_stops_collect(tmp_path):
    from nordic_desk.news import SourceError
    with pytest.raises(SourceError, match="GDELT"):
        collect("NRDL", "Nordlys", CFG, cache_dir=tmp_path, get=lambda url: "rate limited", yahoo=lambda t: [],
                fetch_page=lambda u: LONG, robots_ok=lambda u: True, sleep=lambda s: None)

    def yahoo_down(t):
        raise RuntimeError("yahoo down")
    with pytest.raises(SourceError, match="Yahoo"):
        collect("NRDL", "Nordlys", CFG, cache_dir=tmp_path, get=lambda url: gdelt_json(), yahoo=yahoo_down,
                fetch_page=lambda u: LONG, robots_ok=lambda u: True, sleep=lambda s: None)


def test_undated_articles_dropped(tmp_path):
    undated = {"content": {"title": "No date", "canonicalUrl": {"url": "https://y.example/n"}, "provider": {"displayName": "Wire"}}}
    no_seen = json.dumps({"articles": [{"url": "https://g.example/1", "title": "No seen date", "domain": "g.example"}]})
    arts = collect("NRDL", "Nordlys", CFG, cache_dir=tmp_path, get=lambda url: no_seen, yahoo=lambda t: [undated],
                   fetch_page=lambda u: LONG, robots_ok=lambda u: True, sleep=lambda s: None)
    assert arts == []


def test_yahoo_parsed():
    item = {"content": {"title": "Nordlys beats estimates", "pubDate": "2026-11-18T12:00:00Z",
                        "canonicalUrl": {"url": "https://y.example/n"}, "provider": {"displayName": "Wire"}}}
    assert yahoo_articles("NRDL", fetch=lambda t: [item]) == [
        {"url": "https://y.example/n", "title": "Nordlys beats estimates", "date": "2026-11-18", "sites": ["Wire"]}]


def test_merge_joins_same_story():
    a = {"url": "https://a.example/1", "title": "Nordlys wins contract!", "date": "2026-11-19", "sites": ["a.example"]}
    b = {"url": "https://b.example/2", "title": "nordlys wins contract", "date": "2026-11-18", "sites": ["b.example"]}
    out = merge([a, b])
    assert len(out) == 1 and out[0]["sites"] == ["a.example", "b.example"] and out[0]["url"] == a["url"]


def make(tmp_path, pages, robots=lambda url: True):
    calls = []

    def fetch_page(url):
        calls.append(url)
        return pages.get(url)

    rows = [("https://a.example/1", "Nordlys wins contract", "20261119T233000Z", "a.example"),
            ("https://paywalled.example/2", "Nordlys deep dive", "20261118T100000Z", "paywalled.example"),
            ("https://c.example/3", "Nordlys short note", "20261117T100000Z", "c.example")]
    arts = collect("NRDL", "Nordlys Systems Inc.", CFG, cache_dir=tmp_path, get=lambda url: gdelt_json(*rows),
                   yahoo=lambda t: [], fetch_page=fetch_page, robots_ok=robots, sleep=lambda s: None)
    return arts, calls


def test_collect_drops_paywall_and_short(tmp_path):
    arts, calls = make(tmp_path, {"https://a.example/1": LONG, "https://c.example/3": "too short"})
    assert [a["url"] for a in arts] == ["https://a.example/1"]
    assert arts[0]["id"] == 1 and arts[0]["text"].startswith("Invented")
    assert "https://paywalled.example/2" not in calls


def test_collect_caches_text(tmp_path):
    pages = {"https://a.example/1": LONG}
    make(tmp_path, pages)
    _, calls = make(tmp_path, pages)
    assert "https://a.example/1" not in calls


def test_robots_disallow_skips(tmp_path):
    arts, calls = make(tmp_path, {"https://a.example/1": LONG}, robots=lambda url: False)
    assert arts == [] and calls == []
