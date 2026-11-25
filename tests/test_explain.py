import re

from nordic_desk.explain import EXPLAIN, FIELDS_USED, FORMATS

KEYS = ["sma50", "sma200", "bb", "h52", "rsi", "macd", "dd", "pe", "mom", "vol", "quality", "ltrev", "price"]


def test_every_indicator_has_full_entry():
    for k in KEYS:
        e = EXPLAIN[k]
        assert all(e[f] for f in ("title", "what", "use")) and "now" in e and "formula" in e


def test_templates_parse_and_fields_collected():
    found = set()
    for e in EXPLAIN.values():
        for field, fmt in re.findall(r"\{(\w+)\|(\w+)\}", e["now"]):
            assert fmt in FORMATS
            found.add(field)
        assert "{" not in re.sub(r"\{\w+\|\w+\}", "", e["now"])
    assert found == FIELDS_USED and "sma200" in FIELDS_USED


def test_evidence_strength_matches_research():
    for k in ("rsi", "bb", "macd"):
        assert "weak" in EXPLAIN[k]["use"].lower()
    assert "strong" in EXPLAIN["mom"]["use"].lower() and "Jegadeesh" in EXPLAIN["mom"]["use"]
    assert "George & Hwang" in EXPLAIN["h52"]["use"] and "moderate" in EXPLAIN["sma200"]["use"].lower()
    assert "Novy-Marx" in EXPLAIN["quality"]["use"]
