import json
import re

from test_analysis import SUBJ, STOCK, make, ohlc

from nordic_desk.analysis import Subject
from nordic_desk.views.analysis import analysis_index, analysis_page

PICK = [SUBJ, Subject("^OMXH25", "Example Index Fund", ("held",), "Index stands in."), Subject("NEWCO", "New Co", ("idea",), "")]


def data_of(html):
    raw = re.search(r'<script type="application/json" id="analysis-data">(.*?)</script>', html, re.S).group(1)
    return json.loads(raw.replace("<\\/", "</"))


def visible(html):
    return re.sub(r"<script.*?</script>", "", html, flags=re.S)


def test_page_basics():
    html = analysis_page(make(), PICK)
    assert html.lstrip().startswith("<!doctype html>")
    raw = re.search(r'id="analysis-data">(.*?)</script>', html, re.S).group(1)
    assert "NaN" not in raw and "Infinity" not in raw and "NaN" not in visible(html)
    assert "Not investment advice." in html and "Fixed rules on the readings above, not AI." in html
    assert not re.search(r"\bBuy\b", html)
    assert data_of(html)["ticker"] == "EXMPL" and "function draw" in html


def test_both_horizons_server_rendered():
    html = analysis_page(make(), PICK)
    assert html.count('class="verdict"') == 2
    assert re.search(r'data-h-panel="long"[^>]*hidden', html) and not re.search(r'data-h-panel="entry"[^>]*hidden', html)


def test_no_candle_toggle_without_ohlc():
    df = ohlc()
    html = analysis_page(make(df=df.iloc[0:0], fallback=df["close"]), PICK)
    assert 'data-s="candle"' not in html


def test_script_close_tag_escaped():
    html = analysis_page(make(s=Subject("EXMPL", "Bad </script><b>x", ("watch",), "")), PICK)
    assert data_of(html)["name"] == "Bad </script><b>x" and "<b>x" not in visible(html)


def test_fund_long_boxes_say_not_available():
    html = analysis_page(make(f={"quote_type": "ETF", "currency": "USD"}), PICK)
    assert visible(html).count("not available for funds") == 2 and 'class="chip" data-k="pe"' not in html


def test_standin_note_shown():
    html = analysis_page(make(s=Subject("^OMXH25", "Example Index Fund", ("held",), "Index stands in.")), PICK)
    assert "Index stands in." in html


def test_picker_groups_and_slug_links():
    html = analysis_page(make(), PICK)
    assert '<optgroup label="Holdings">' in html and 'value="_OMXH25.html"' in html and 'value="EXMPL.html" selected' in html
    idx = analysis_index(PICK)
    assert 'href="_OMXH25.html"' in idx and "Ideas" in idx and 'href="../desk.html"' in idx


TRACK = {"group": "pullback", "label": "Good entry · pullback",
         "stats": {"n_months": 37, "beat": 0.62, "mean": 0.026, "lo": -0.005, "hi": 0.057, "since": "2016", "reading": "too noisy to trust alone"}}


def test_track_block_shown_and_hidden():
    p = make()
    assert "Track record for this stock" not in analysis_page(p, PICK)
    html = analysis_page({**p, "track": TRACK}, PICK)
    v = visible(html)
    assert "Track record for this stock" in v and "37 months since 2016" in v and "62%" in v and "too noisy to trust alone" in v
    assert 'href="../forecasts.html#scorecard"' in html
    none = analysis_page({**p, "track": {**TRACK, "stats": None}}, PICK)
    assert "No past Good entry · pullback months for this stock" in visible(none)


def test_track_never_says_helps():
    v = visible(analysis_page({**make(), "track": TRACK}, PICK))
    assert not re.search(r"\bhelps\b", v)


def test_track_with_one_month_has_no_interval_and_does_not_crash():
    t = {**TRACK, "stats": {**TRACK["stats"], "n_months": 1, "lo": None, "hi": None}}
    v = visible(analysis_page({**make(), "track": t}, PICK))
    assert "1 months since 2016" in v and "too few months for an interval" in v


ROWS = [{"ticker": "EXMPL", "name": "Example Corp", "group": "held", "price": 100.0, "d1": 0.012, "verdict": "Good entry", "cls": "good",
         "line": "Pullback inside an uptrend", "dist200": 0.08, "rsi": 34.0, "pct_b": 0.1, "mom": 0.2, "drawdown": -0.06, "vol": 0.3,
         "pe_pct": 0.25, "expected": 0.12, "upside": 0.2, "spark": [1.0] * 63, "pos52": 0.8, "changed": True},
        {"ticker": "NEWCO", "name": "New Co", "group": "idea", "price": 5.0, "d1": -0.01, "verdict": "Wait", "cls": "wait",
         "line": "Trend is down", "dist200": -0.1, "rsi": 45.0, "pct_b": 0.4, "mom": -0.1, "drawdown": -0.3, "vol": 0.5,
         "pe_pct": None, "expected": None, "upside": None, "spark": [1.0] * 63, "pos52": 0.1, "changed": False}]


def test_index_screener_desktop_and_phone_list():
    idx = analysis_index(PICK, ROWS)
    v = visible(idx)
    assert 'id="screener"' in idx and idx.count('<tr data-t=') == 2 and 'href="EXMPL.html"' in idx
    assert 'data-v="good"' in idx and "Good entry <span" in idx or "Good entry" in v
    assert "Up +8%" in v.replace(chr(0x2212), "-") and "RSI 34" in v and "Cheap" in v and "n/a" in v
    assert "new" in v and "Verdict mix" in v and 'phone-list' in idx  # phones keep the simple list
    assert not re.search(r"\bNaN\b|undefined", v)


def test_boxes_sit_in_a_strip_under_the_chart_not_in_the_rail():
    html = analysis_page(make(), PICK)
    rail = html.split('<aside class="rail"', 1)[1].split("</aside>", 1)[0]
    assert 'class="box"' not in rail
    assert re.search(r'<div class="strip" data-h-panel="entry">.*?class="box"', html, re.S)
    assert re.search(r'<div class="strip" data-h-panel="long" hidden>', html)


EXPECTED = {"anchor": 0.139, "analyst": 0.12, "signal": None, "combined": 0.1294, "pieces": 1}


def test_expected_card_in_rail_only_when_known():
    p = make()
    assert "Expected 12 m" not in visible(analysis_page(p, PICK))
    html = analysis_page({**p, "expected": EXPECTED}, PICK)
    rail = visible(html).split('<aside class="rail"', 1)[1].split("</aside>", 1)[0]
    assert "Expected 12 m" in rail and "+12.9%" in rail and "+12%" in rail and "not used" in rail
    assert 'href="../forecasts.html#expected"' in rail


def test_labels_are_sentence_case():
    assert "uppercase" not in analysis_page(make(), PICK)
