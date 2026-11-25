import json
import re

from nordic_desk.forecasts import WARNING
from nordic_desk.views.forecasts import VANGUARD, forecasts_page

STATS = {"n_samples": 80, "n_months": 80, "eff_windows": 13.3, "beat": 0.58, "mean": 0.021, "lo": 0.004, "hi": 0.038,
         "reading": "helps", "label": "Good entry · pullback"}
LUMP = {"starts": 100, "lump_ahead": 0.68, "median_diff": 0.031, "lump_median": 1.14, "spread_median": 1.11, "lump_p5": 0.77,
        "spread_p5": 0.85, "worst_lump_regret": -0.23, "worst_spread_regret": -0.14,
        "hist": {"edges": [i / 100 - 0.1 for i in range(21)], "counts": [1] * 20}}
D = {"built": "2026-11-23", "excluded": [{"ticker": "CCC.ST", "why": "quoted in SEK, only USD and EUR are compared"}], "warning": WARNING,
     "scorecard": {h: {"groups": {"pullback": STATS}, "per_stock": {"AAA": {"pullback": {**STATS, "reading": "too noisy to trust alone"}}}}
                   for h in ("63", "126", "252")},
     "risk": {"n": 240, "hits": 13, "rate": 0.054, "expected": 0.05, "p_value": 0.6},
     "targets": {"rates": {"overshoot": 0.15, "met_12m": 0.38, "met_any": 0.64, "source": "Bradshaw, Brown & Huang (2013)",
                           "n_checked": 0, "first_check": "2027-11-17"},
                 "rows": [{"ticker": "AAA", "name": "Example A", "price": 100.0, "target": 130.0, "upside": 0.3, "realistic": 0.15, "record": 0}]},
     "lump": {"AAA": {"3": LUMP, "6": LUMP, "12": None}, "SPY": {"3": LUMP, "6": LUMP, "12": LUMP}},
     "subjects": [{"ticker": "AAA", "name": "Example A", "groups": ["held"]}]}


def visible(html):
    return re.sub(r"<script.*?</script>", "", html, flags=re.S)


def test_page_sections_and_nav():
    html = forecasts_page(D, 2000)
    for i in ('id="scorecard"', 'id="lump"', 'id="targets"', 'href="forecasts.html"', "Not investment advice."):
        assert i in html
    raw = re.search(r'id="fc-data">(.*?)</script>', html, re.S).group(1)
    assert json.loads(raw.replace("<\\/", "</"))["targets"]["rows"][0]["ticker"] == "AAA"


def test_no_nan_and_no_promise_words():
    v = visible(forecasts_page(D, 2000))
    assert "NaN" not in v and not re.search(r"\bwill\b", v, re.I) and "expect to gain" not in v


def test_warning_and_vanguard_verbatim():
    v = visible(forecasts_page(D, 2000))
    assert WARNING in v and VANGUARD.replace("*", "") in re.sub(r"</?em>", "", v)


def test_one_stock_and_amount_drive_the_page():
    html = forecasts_page(D, 2000)
    assert '<label for="fc-stock"' in html and '<label for="fc-amount"' in html
    assert re.search(r'<input id="fc-amount" type="number" inputmode="numeric" min="1" max="10000000" value="2000"', html)
    assert html.count("<select") == 1 and 'id="fc-summary"' in html and 'aria-live="polite"' in html


def test_segmented_controls_use_fieldset_legend():
    html = forecasts_page(D, 2000)
    assert "<legend>Horizon</legend>" in html and "<legend>Spread over</legend>" in html and "<legend>Show</legend>" in html
    assert "<label>Horizon" not in html


def test_two_scorecard_panels():
    html = forecasts_page(D, 2000)
    assert 'id="sc-buy"' in html and 'id="sc-wait"' in html
    v = visible(html)
    assert "you want them right of 0" in v and "you want them left of 0" in v


def test_risk_row_without_clustering_p_has_no_nan():
    d = {**D, "risk": {k: v for k, v in D["risk"].items() if k != "christoffersen_p"}}
    assert not re.search(r"nan", visible(forecasts_page(d, 2000)), re.I)


def test_targets_table_and_rates_line():
    v = visible(forecasts_page(D, 2000))
    assert "Example A" in v and "38%" in v and "64%" in v and "Bradshaw" in v and "2027-11-17" in v
    assert "SEK" in v  # excluded list shown


def test_risk_row():
    assert "5.4%" in visible(forecasts_page(D, 2000))


def test_risk_row_uses_impact_rule_and_shows_numbers():
    d = {**D, "risk": {**D["risk"], "christoffersen_p": 0.01}}
    v = visible(forecasts_page(d, 2000))
    assert "13/240" in v and "p 0.60" in v and "clustering test p 0.01" in v and ">off<" in v.replace("</span>", "<")


def test_page_has_expected_section_and_vol_sizing():
    d = {**D, "anchor": {"rate": 0.12, "from": "2015", "to": "2026"},
         "expected": {"AAA": {"anchor": 0.12, "analyst": 0.15, "signal": None, "combined": 0.135, "pieces": 1}},
         "volsize": {"AAA": {"now": {"current": 0.38, "usual": 0.24, "first": 0.4}, "6": None}}}
    html = forecasts_page(d, 2000)
    v = visible(html)
    assert 'id="expected"' in html and "Rapach" in v and "Moreira" in v and "2015–2026" in v
    assert not re.search(r"\bwill\b", v, re.I)
