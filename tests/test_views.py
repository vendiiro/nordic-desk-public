import re
import copy

from nordic_desk.views.aamu import aamu_page
from nordic_desk.views.core import line_chart, pct
from nordic_desk.views.huurre import desk_page
from nordic_desk.views.impact import impact_page
from nordic_desk.views.site import write_site

MINUS = chr(0x2212)


def test_pct_format():
    assert pct(-0.0123) == MINUS + "1.2%"
    assert pct(0.5, 0, sign=False) == "50%"


def test_line_chart_one_axis_few_gridlines():
    svg = line_chart([([1, 2, 3, 2, 5], "main")], ["2025-12-30", "2025-12-31", "2026-01-02", "2026-01-05", "2026-01-06"])
    assert svg.count("<svg") == 1 and 3 <= svg.count('class="grid"') <= 6


def check_page(html):
    assert html.lstrip().startswith("<!doctype html>")
    assert "/* Hallmark" in html.split("<style>")[1][:20]
    assert "NaN" not in html and "None" not in html


def test_desk_page(built):
    desk, _, _ = built
    html = desk_page(desk)
    check_page(html)
    for r in desk["watchlist"]:
        assert r["ticker"] in html
    assert html.count('<article class="dive" data-panel=') == 3 and html.count('data-panel="AAPL" hidden') + html.count('data-panel="XOM" hidden') == 1


def test_missing_facts_say_not_reported(built):
    desk, _, _ = built
    assert "not reported" in desk_page(desk)


def test_skipped_tickers_named(built):
    desk, _, _ = built
    d = copy.deepcopy(desk)
    d["meta"]["skipped"] = ["BOGUS"]
    html = desk_page(d)
    assert "BOGUS" in html and "left out" in html


def test_impact_page_scenarios_and_record(built):
    desk, _, _ = built
    html = impact_page(desk)
    check_page(html)
    n = len(desk["impact"]["scenarios"])
    assert html.count('<div class="scn" data-scn=') == n
    assert html.count('<div class="scn" data-scn=') - html.count('" hidden><h3>') == 1
    assert "Your record" not in html
    d = copy.deepcopy(desk)
    d["record"] = {"dates": ["2025-01-03", "2025-07-04", "2026-01-09"], "value": [1, 2, 3], "deposits": [1, 1, 1],
                   "twr": [1.0, 1.1, 1.2], "spy": [1.0, 1.05, 1.1], "vol_1y": 0.2}
    assert "Your record" in impact_page(d)


def test_aamu_sentence_ahead_or_behind(built):
    desk, aamu, _ = built
    a = copy.deepcopy(aamu)
    a["portfolio"]["overnight_pct"], a["spy_overnight"] = 0.01, -0.01
    assert "ahead" in aamu_page(a, desk)
    a["portfolio"]["overnight_pct"], a["spy_overnight"] = -0.02, 0.01
    html = aamu_page(a, desk)
    assert "behind" in html
    check_page(html)


def site(out, **kw):
    """write_site on the fixture's invented prices and example holdings, never the real data/ or config/*.local.*"""
    return write_site(out, price_root=out.parent / "prices", ohlc_root=out.parent / "ohlc", fund_root=out.parent / "fund",
                      holdings_path="config/holdings.example.toml", hist_path=out.parent / "hist.csv", **kw)


def test_site_writes_pages(built):
    _, _, out = built
    site(out)
    for name in ("index", "desk", "impact", "compare", "aamu", "goal"):
        assert (out / "site" / f"{name}.html").exists()
    home = (out / "site" / "index.html").read_text(encoding="utf-8")
    assert 'href="goal.html"' in home and "Long range" in home


def test_site_writes_analysis_pages_and_links(built):
    import json as _json
    from nordic_desk.views.analysis import analysis_page  # noqa: F401  (module must import)
    _, _, out = built
    (out / "cards.json").write_text(_json.dumps({"cards": {}, "groups": {}, "errors": {}, "meta": {"close": "2026-01-14", "built": "x"}, "alerts": []}), encoding="utf-8")
    site(out)
    a = out / "site" / "analysis"
    assert (a / "index.html").exists() and (a / "AAPL.html").exists() and (a / "_OMXH25.html").exists()
    assert not (a / "CBUT.DE.html").exists()
    assert 'href="analysis/AAPL.html"' in (out / "site" / "desk.html").read_text(encoding="utf-8")
    assert 'href="analysis/MSFT.html"' in (out / "site" / "impact.html").read_text(encoding="utf-8")
    assert 'href="analysis/index.html"' in (out / "site" / "index.html").read_text(encoding="utf-8")


def test_impact_names_in_sentence_case(built):
    desk, _, _ = built
    d = copy.deepcopy(desk)
    for h in d["impact"]["holdings"]:
        h["name"] = h["name"].upper()
    for s in d["impact"]["scenarios"]:
        if s["kind"] == "sell":
            s["name"] = s["name"].upper()
    assert "MICROSOFT" not in impact_page(d)


def _card(**kw):
    base = {"ticker": "XLV", "name": "Health Care Select", "sector": None, "industry": None, "currency": "USD", "type": "ETF",
            "size": None, "market_cap": None, "results": [], "impact": None, "impact_note": "not enough price history for the portfolio comparison",
            "price": {"dates": ["2025-12-30", "2025-12-31", "2026-01-02", "2026-01-05"], "close": [1, 2, 3, 4], "spy_scaled": [1, 1, 2, 2],
                      "ret": 3.0, "worst_fall": -0.1},
            "analysts": {"count": 3, "rating_share": 0.5, "target_mean": 5.0, "target_low": 4.0, "target_high": 6.0, "upside": 0.25,
                         "buy_below": 4.35, "sell_above": 5.0, "status": "thin coverage"}}
    base.update(kw)
    return base


def test_cards_page_texts():
    from nordic_desk.views.cards import cards_page
    doc = {"meta": {"close": "2026-01-14", "built": "2026-01-15T07:00Z"}, "groups": {"diversify": ["XLV"]},
           "cards": {"XLV": _card()}, "errors": {"BAD": "no such ticker"}}
    html = cards_page(doc)
    check_page(html)
    assert "thin coverage" in html.lower() and "no company results (fund)" in html
    assert "not enough price history for the portfolio comparison" in html and "BAD" in html
    assert 'href="analysis/XLV.html"' in html


def test_worst_fall_words():
    from nordic_desk.views.cards import impact_block
    amt = {"vol": 0.2, "beta": 1.0, "worst": -0.15, "enb": 5.0, "tech": 0.6, "expected": {"value": None, "covered": 0}, "own_risk": 0.01}
    c = _card(impact={"corr": 0.1, "down": 0.1, "before": {"vol": 0.2, "beta": 1.0, "worst": -0.17, "enb": 5.0, "tech": 0.6},
                      "expected_before": {"value": None, "covered": 0}, "amounts": {a: dict(amt) for a in ("500", "1000", "2500", "5000")}})
    html = impact_block(c)
    assert "smaller fall" in html and "raises" not in html.split("Worst fall")[1][:200]


def test_cards_page_has_search_and_discover():
    from nordic_desk.server import DISCOVER
    from nordic_desk.views.cards import cards_page
    html = cards_page({"meta": {"close": "2026-01-14", "built": "x"}, "groups": {}, "cards": {}, "errors": {}})
    assert '<input' in html and 'name="q"' in html and '<label' in html
    for key in DISCOVER:
        assert f'data-list="{key}"' in html
    assert "nordic-desk serve" in html


def test_cards_shown_once_and_honest_label():
    from nordic_desk.views.cards import cards_page
    c = _card(ticker="AVGO", impact={"corr": 0.5, "down": 0.5, "before": {"vol": 0.2, "beta": 1, "worst": -0.1, "enb": 5, "tech": 0.6},
                                    "expected_before": {"value": 0.1, "covered": 0.5},
                                    "amounts": {a: {"vol": 0.2, "beta": 1, "worst": -0.1, "enb": 5, "tech": 0.6, "expected": {"value": 0.11, "covered": 0.5}, "own_risk": 0.01}
                                                for a in ("500", "1000", "2500", "5000")}})
    html = cards_page({"meta": {"close": "2026-01-14", "built": "x"}, "groups": {"growth": ["AVGO"], "searched": ["AVGO"]},
                       "cards": {"AVGO": c}, "errors": {}})
    assert html.count('id="AVGO"') == 1
    assert "Expected return, holdings with targets" in html
    assert "closest('.card')" in html and 'tabindex="-1"' in html and ".focus()" in html


def test_impact_live_region_is_short(built):
    desk, _, _ = built
    html = impact_page(desk)
    assert 'class="out" aria-live' not in html and 'id="scn-say"' in html


def test_alert_banner_and_change_line():
    from nordic_desk.views.cards import cards_page
    c = _card(history={"since": "2026-01-10", "target": 0.03, "rating_points": -5.0, "status_before": "between thresholds"})
    doc = {"meta": {"close": "2026-01-14", "built": "x"}, "groups": {"diversify": ["XLV"]}, "cards": {"XLV": c}, "errors": {},
           "alerts": [{"ticker": "XLV", "name": "Health", "now": "below buy threshold", "before": "between thresholds"}]}
    html = cards_page(doc)
    assert "Since 10 Jan 2026" in html and "+3.0%" in html
    assert 'aria-labelledby="alerts-h"' in html and 'class="alerts" role="status"' not in html and "below buy threshold" in html.lower()


def test_aamu_alert_banner(built):
    desk, aamu, _ = built
    html = aamu_page(aamu, desk, alerts=[{"ticker": "XOM", "name": "Exxon", "now": "above sell threshold", "before": "between thresholds"}])
    assert "XOM" in html and "above sell threshold" in html.lower()


def test_impact_shows_forecast_and_calibration(built):
    desk, _, _ = built
    html = impact_page(desk)
    assert "Next month" in html and "95%" in html and "about two years" in html     # fixture history is short
    d = copy.deepcopy(desk)
    cal = {"n": 2000, "hits": 98, "rate": 0.049, "kupiec_p": 0.8, "christoffersen_p": 0.4, "start": "2018-01-02"}
    for m in d["forecast"]["models"].values():
        m["calibration"] = dict(cal)
    d["forecast"]["models"]["garch"]["calibration"]["christoffersen_p"] = 0.9
    d["forecast"]["headline"] = "garch"
    d["forecast"]["excluded"] = ["ETH-EUR"]
    html = impact_page(d)
    for name in ("EWMA", "GARCH-t", "Bootstrap, last 500 days", "Markov regimes"):
        assert name in html
    assert "high-volatility regime" in html and "ETH-EUR" in html and "4.9%" in html


def test_forecast_verdict_uses_both_tests_and_honest_short_wording(built):
    desk, _, _ = built
    from nordic_desk.views.impact import forecast_section
    f = copy.deepcopy(desk["forecast"])
    assert "best-calibrated" not in forecast_section(f)        # nothing calibrated on short history
    for m in f["models"].values():
        m["calibration"] = {"n": 2000, "hits": 100, "rate": 0.05, "kupiec_p": 0.8, "christoffersen_p": 0.01, "start": "2018-01-02"}
    f["headline"] = "ewma"
    f["backtest"] = {"n": 2000, "hits": 100, "rate": 0.05, "expected": 0.05, "p_value": 0.8, "christoffersen_p": 0.01, "start": "2018-01-02"}
    html = forecast_section(f)
    assert "not consistent" in html and "refits every month" not in html


AMT = {"vol": 0.2, "beta": 1.0, "worst": -0.15, "enb": 5.0, "tech": 0.6, "expected": {"value": None, "covered": 0}, "own_risk": 0.01}
BEFORE = {"vol": 0.2, "beta": 1.0, "worst": -0.15, "enb": 5.0, "tech": 0.6}


def _lt_card(lt, amounts=("2000", "3000"), type="EQUITY"):
    return _card(ticker="MSFT", name="Microsoft", type=type, lookthrough=lt,
                 impact={"corr": 0.5, "down": 0.5, "before": dict(BEFORE), "expected_before": {"value": None, "covered": 0},
                         "amounts": {a: dict(AMT) for a in amounts}})


LT = {"focus": ["MSFT"], "names": {"MSFT": "Microsoft"}, "before": {"MSFT": 0.04}, "via_funds": {"MSFT": 0.015},
      "amounts": {"2000": {"MSFT": 0.095}, "3000": {"MSFT": 0.12}}, "not_broken_down": 0.30, "no_data": ["^OMXH25"]}


def test_card_shows_lookthrough_rows():
    from nordic_desk.views.cards import impact_block
    html = impact_block(_lt_card(LT), default_amount=2000)
    assert "Share of your portfolio, funds included" in html
    row = html.split('Microsoft<span class="visually-hidden"> share, including funds</span>')[1][:300]
    assert "4.0%" in row and "9.5%" in row and '"r flat">raises' in row


def test_card_lookthrough_sentence():
    from nordic_desk.views.cards import impact_block
    text = lambda h: __import__("re").sub(r"<[^>]+>", "", h)
    html = text(impact_block(_lt_card(LT)))
    assert "You already own 4.0% of the portfolio in Microsoft: 2.5% directly and 1.5% through funds." in html
    new = dict(LT, before={"MSFT": 0.0}, via_funds={"MSFT": 0.0})
    assert "You do not own Microsoft yet, directly or through funds." in impact_block(_lt_card(new))


def test_fund_card_lookthrough_sentence():
    from nordic_desk.views.cards import impact_block
    lt = dict(LT, focus=["MSFT", "LLY"], names={"MSFT": "Microsoft", "LLY": "Eli Lilly"}, before={"MSFT": 0.5, "LLY": 0.0},
              via_funds={"MSFT": 0.0, "LLY": 0.0}, amounts={"2000": {"MSFT": 0.45, "LLY": 0.07}, "3000": {"MSFT": 0.44, "LLY": 0.1}})
    html = impact_block(_lt_card(lt, type="ETF"))
    assert "largest holdings are Microsoft and Eli Lilly." in html
    assert "lowers" in html.split('Microsoft<span class="visually-hidden"> share, including funds</span>')[1][:300]


def test_card_lookthrough_notes():
    from nordic_desk.views.cards import impact_block
    html = impact_block(_lt_card(LT))
    assert "30% of the portfolio sits in funds outside their published top holdings and is not broken down." in html
    assert "No holdings data: ^OMXH25." in html
    assert "Fund top holdings from Yahoo Finance" in html


def test_amount_chips_follow_card():
    from nordic_desk.views.cards import impact_block
    html = impact_block(_lt_card(LT), default_amount=3000)
    assert html.count('type="radio"') == 2
    assert 'value="3000" checked' in html and 'value="2000" checked' not in html
    assert 'data-amt="3000">' in html and 'data-amt="2000" hidden' in html


def test_card_without_lookthrough():
    from nordic_desk.views.cards import impact_block
    html = impact_block(_lt_card(None))
    assert "including funds" not in html and "Volatility" in html


def test_desk_lookthrough_block():
    from nordic_desk.views.huurre import lookthrough_block
    top = [{"key": k, "name": n, "share": s, "direct": s - v, "via_funds": v}
           for k, n, s, v in (("MSFT", "Microsoft", 0.30, 0.05), ("NVDA", "NVIDIA", 0.12, 0.12), ("AAPL", "Apple", 0.04, 0.04),
                              ("ORCL", "Oracle", 0.03, 0.0), ("AVGO", "Broadcom", 0.02, 0.02))]
    html = lookthrough_block({"lookthrough": {"top": top, "not_broken_down": 0.18, "no_data": ["^OMXH25"],
                                              "source": "Yahoo Finance fund top holdings"}})
    assert "Largest companies, including funds" in html and html.count("<tr") == 6
    assert "18% of the portfolio sits in funds outside their published top holdings" in html
    assert "No holdings data: ^OMXH25." in html and "Yahoo Finance" in html
    assert lookthrough_block({"lookthrough": None}) == ""


def test_desk_page_has_lookthrough(built):
    desk, _, _ = built
    assert "Largest companies, including funds" in desk_page(desk)


def test_desk_lookthrough_ticker_once_when_no_name():
    from nordic_desk.views.huurre import lookthrough_block
    html = lookthrough_block({"lookthrough": {"top": [{"key": "ORCL", "name": "ORCL", "share": 0.04, "direct": 0.04, "via_funds": 0.0}],
                                              "not_broken_down": 0.0, "no_data": [], "source": "Yahoo Finance fund top holdings"}})
    assert html.count("ORCL") == 1 and 'class="num r"' in html


BRIEF = {"ticker": "XLV", "name": "Health Care Select", "model": "claude-opus-5-5", "written": "2026-11-20", "cost_usd": 0.05,
         "range": ["2026-10-22", "2026-11-19"], "what": {"text": "A health care fund.", "sources": [1]},
         "for": [{"text": "Defensive sales.", "sources": [1, 2]}], "against": [{"text": "Drug price rules.", "sources": [2]}],
         "events": [{"date": "2026-12-04", "text": "Rebalance", "sources": [1]}], "tone": {"positive": 2, "neutral": 1, "negative": 0},
         "articles": [{"id": 1, "url": "https://a.example/x?a=1&b=2", "title": "T1", "date": "2026-11-19", "sites": ["a.example"]},
                      {"id": 2, "url": "javascript:alert(1)", "title": "T2", "date": "2026-10-22", "sites": ["b.example"]}]}


def test_card_brief_block():
    from nordic_desk.views.cards import brief_block
    html = brief_block(_card(brief=BRIEF))
    assert "AI summary" in html and "unchecked" in html
    assert "2 articles" in html and "22 Oct" in html and "19 Nov" in html
    assert "Defensive sales." in html and "Drug price rules." in html and "Rebalance" in html
    assert 'href="https://a.example/x?a=1&amp;b=2"' in html and 'rel="noopener noreferrer"' in html
    assert "javascript:" not in html  # a non-http link is shown as text only
    assert "2 positive, 1 neutral, 0 negative" in html and "does not enter any number" in html


def test_card_without_brief_shows_command():
    from nordic_desk.views.cards import brief_block
    assert "uv run nordic-desk brief XLV" in brief_block(_card())
    empty = dict(BRIEF, articles=[], what=None, **{"for": [], "against": [], "events": []}, range=None)
    assert "No free articles" in brief_block(_card(brief=empty))


def test_no_brief_has_no_ai_badge():
    from nordic_desk.views.cards import brief_block
    assert "AI summary" not in brief_block(_card())


def test_site_writes_forecasts(built):
    _, _, out = built
    site(out)
    assert (out / "site" / "forecasts.html").exists() and (out / "forecasts.json").exists()
    assert 'href="forecasts.html"' in (out / "site" / "index.html").read_text(encoding="utf-8")


FC = {"targets": {"rates": {"overshoot": 0.15, "source": "Bradshaw, Brown & Huang (2013)", "n_checked": 0}},
      "lump": {"XLV": {"6": {"lump_ahead": 0.68, "lump_p5": 0.77, "spread_p5": 0.85}}}}


def test_card_realistic_upside_and_lump_line():
    from nordic_desk.views.cards import card_html
    c = _card()
    html = card_html(c, 2000, FC)
    if c["analysts"].get("upside") is not None:
        assert "Realistic upside" in html and "(study)" in html
    assert "Lump ended ahead in 68% of past start dates" in html and "€1 540" in html and "€1 700" in html
    assert 'href="forecasts.html#lump"' in html


def test_card_lump_line_hidden_without_data():
    from nordic_desk.views.cards import card_html
    assert "Lump ended ahead" not in card_html(_card(), 2000, {"targets": FC["targets"], "lump": {}})
    assert "Lump ended ahead" not in card_html(_card(), 2000)


def test_card_lump_line_honest_when_spreading_is_worse():
    from nordic_desk.views.cards import card_html
    fc = {"targets": FC["targets"], "lump": {"XLV": {"6": {"lump_ahead": 0.9, "lump_p5": 0.95, "spread_p5": 0.9}}}}
    html = card_html(_card(), 2000, fc)
    assert "did not improve the bad case" in html and "cut the bad case" not in html


def test_cards_page_groups_as_buttons_and_compact_rows():
    from nordic_desk.views.cards import cards_page
    c1, c2 = _card(), {**_card(), "ticker": "AVGO", "name": "Broadcom"}
    doc = {"meta": {"close": "2026-01-14", "built": "x"}, "groups": {"diversify": ["XLV"], "growth": ["AVGO"], "searched": ["XLV"]},
           "cards": {"XLV": c1, "AVGO": c2}, "errors": {}}
    html = cards_page(doc)
    assert re.search(r'data-g="growth" aria-pressed="true">IT and AI growth <span class="n">1</span>', html)
    assert 'data-g="diversify"' in html and 'data-g="all"' in html and 'data-g="searched"' not in html  # XLV already shown
    assert html.count('<details class="idea"') == 2 and 'data-group="growth"' in html
    row = re.search(r'<details class="idea"[^>]*data-group="diversify"[^>]*>\s*<summary>(.*?)</summary>', html, re.S).group(1)
    assert "Health Care Select" in row and "XLV" in row and "+25%" in row.replace(chr(0x2212), "-")


VERDICTS = {"AAPL": {"verdict": "Good entry", "cls": "good", "line": "Pullback inside an uptrend", "expected": 0.12},
            "MSFT": {"verdict": "Wait", "cls": "wait", "line": "Trend is down", "expected": None}}


def test_desk_watchlist_speaks_screener_language(built):
    desk, _, _ = built
    html = desk_page(desk, VERDICTS)
    table = html.split('<table class="watch">', 1)[1].split("</table>", 1)[0]
    assert '<span class="tag good" title="Pullback inside an uptrend">Good entry</span>' in table
    assert "+12.0%" in table and 'data-s="expected"' in table and 'data-s="d1"' in table
    assert 'data-expected="0.12"' in table
    assert "Watchlist, other states" not in html and "on the right" not in html


def test_desk_dive_has_verdict_and_full_analysis_link(built):
    desk, _, _ = built
    html = desk_page(desk, VERDICTS)
    aapl = html.split('data-panel="AAPL"', 1)[1].split("</article>", 1)[0]
    assert "Good entry" in aapl and "Pullback inside an uptrend" in aapl and 'href="analysis/AAPL.html">Open full analysis' in aapl
    assert "Good entry" not in desk_page(desk).split('data-panel="AAPL"', 1)[1].split("</article>", 1)[0]


def test_desk_name_not_repeated_when_it_is_the_ticker(built):
    desk, _, _ = built
    table = desk_page(desk).split('<table class="watch">', 1)[1]
    assert '<span class="nm">XOM</span>' not in table


def test_compare_folded_into_desk(built):
    from nordic_desk.views.core import nav
    desk, _, out = built
    assert "compare.html" not in nav("Desk")
    html = desk_page(desk)
    cmp = html.split('id="compare"', 1)[1].split("</section>", 1)[0]
    assert '<tr class="ref-row"><th scope="row"><span class="sw ref"></span>SPY</th>' in cmp
    assert 'class="own">held</span>' in cmp
    site(out)
    assert 'url=desk.html#compare' in (out / "site" / "compare.html").read_text(encoding="utf-8")
    assert "compare.html" not in (out / "site" / "index.html").read_text(encoding="utf-8")


def test_impact_leads_with_an_answer(built):
    desk, _, _ = built
    html = impact_page(desk)
    top = desk["impact"]["holdings"][0]
    assert '<h1 class="visually-hidden">' not in html and "<h1>Portfolio impact</h1>" in html
    assert f'carries {pct(top["risk"], 0, False)} of the risk on {pct(top["weight"], 0, False)} of the money' in html


def test_impact_model_table_folds_away_below_the_risk_table(built):
    desk, _, _ = built
    d = copy.deepcopy(desk)
    d["forecast"] = {"horizon_days": 21, "value": 1000.0, "headline": "ewma", "excluded": [],
                     "models": {"ewma": {"low": 900.0, "high": 1100.0, "vol_ann": 0.2}}}
    html = impact_page(d)
    assert "<details><summary>How well each model has done</summary>" in html
    assert html.index('id="rk-h"') < html.index('id="fc-h"') < html.index('id="wi-h"')


def test_impact_three_largest_only_with_three(built):
    desk, _, _ = built
    n = len(desk["impact"]["holdings"])
    html = impact_page(desk)
    assert ("three largest" in html) == (n >= 3)


def test_impact_whatif_uses_card_amounts_and_tech_cap(built):
    desk, _, _ = built
    imp = desk["impact"]
    assert imp["amounts"] == [1000, 2000, 3000, 5000] and imp["default_amount"] == 2000 and imp["tech_max"] == 0.5
    html = impact_page(desk)
    assert 'value="2000" checked' in html and 'value="500"' not in html
    assert "cap 50%" in html
    over = [s for s in imp["scenarios"] if s["tech"] > 0.5]
    assert ("over the 50% cap" in html) == bool(over)
    assert "Each candidate at €2" in html


TODAY_V = {"MSFT": {"verdict": "Good entry", "cls": "good", "line": "Steady uptrend, nothing stretched", "expected": 0.1,
                    "name": "Microsoft", "group": "held", "changed": False},
           "AAPL": {"verdict": "Wait", "cls": "wait", "line": "Trend is down", "expected": None, "name": "Apple", "group": "watch", "changed": False}}


def test_today_page_all_clear(built):
    from nordic_desk.views.today import today_page
    desk, aamu, _ = built
    desk = copy.deepcopy(desk)
    desk["meta"]["built"] = desk["meta"]["close"] + "T08:00Z"
    html = today_page(desk, aamu, [], TODAY_V)
    check_page(html)
    assert "Nothing needs you today" in html and "Not investment advice." in html and 'href="desk.html"' in html
    assert "Microsoft" in html and "Good entry" in html and "Apple" not in html  # holdings only
    assert 'id="stale"' in html and 'hidden>Prices are' in html  # shown by the page script only when old


def test_today_page_lists_changes(built):
    from nordic_desk.views.today import today_page
    desk, aamu, _ = built
    v = copy.deepcopy(TODAY_V)
    v["AAPL"]["changed"] = True
    alerts = [{"ticker": "NVDA", "name": "Nvidia", "now": "a buy", "before": "a hold"}]
    html = today_page(desk, aamu, alerts, v)
    assert "2 things changed since the last run" in html and "Nvidia" in html and 'href="analysis/AAPL.html"' in html
    assert "Nothing needs you today" not in html


def test_today_page_warns_when_prices_are_stale(built):
    from nordic_desk.views.today import today_page
    desk, aamu, _ = built
    d = copy.deepcopy(desk)
    d["meta"]["close"] = "2026-01-02"
    html = today_page(d, aamu, [], TODAY_V)
    assert '<p class="warn" id="stale" data-close="2026-01-02" hidden>' in html and "getDate" not in html and "Date.parse" in html


def test_aamu_all_clear_and_holdings_first(built):
    desk, aamu, _ = built
    html = aamu_page(aamu, desk, [])
    assert "No thresholds crossed since the last run." in html
    tiles = html.split('class="tiles"', 1)[1]
    held = [r["ticker"] for r in desk["watchlist"] if r["held"]]
    assert held and tiles.index(f'>{held[0]}<') < min(tiles.index(f'>{r["ticker"]}<') for r in desk["watchlist"] if not r["held"])
    assert '<span class="own">held</span>' in tiles


def test_site_home_is_today(built):
    _, _, out = built
    site(out)
    assert "Nothing needs you today" in (out / "site" / "index.html").read_text(encoding="utf-8") or "changed since the last run" in (out / "site" / "index.html").read_text(encoding="utf-8")


def test_rounded_zero_has_no_sign_and_no_colour():
    from nordic_desk.views.core import cls, eur
    assert pct(-0.0004) == "0.0%" and cls(-0.0004) == "flat" and pct(0.0006) == "+0.1%"
    assert eur(-0.3, 0, True) == "€0"


def test_footer_build_time_in_helsinki():
    from nordic_desk.views.core import footer
    f = footer({"built": "2026-11-24T08:18Z", "holdings_as_of": "2026-11-12"})
    assert "Built 24 Nov 2026, 10:18 Helsinki time" in f and "08:18Z" not in f


def test_clock_follows_daylight_saving_gap():
    from nordic_desk.views.core import clock
    gap = clock({"close": "2026-03-10", "eurusd": 1.1})  # US on summer time, EU not yet
    assert "22:00 Helsinki" in gap and "<b>15:30</b>" in gap
    assert "23:00 Helsinki" in clock({"close": "2026-11-23", "eurusd": 1.1})


def test_aamu_empty_movers_and_no_repeated_name(built):
    desk, aamu, _ = built
    a = copy.deepcopy(aamu)
    a["movers"]["down"] = []
    html = aamu_page(a, desk, [])
    assert "None tonight" in html
    assert '<span class="nm">XOM</span>' not in html


def test_expected_market_only_says_so():
    from nordic_desk.views.analysis import _expected
    card = _expected({"anchor": 0.139, "analyst": None, "signal": None, "combined": 0.139, "pieces": 0})
    assert "market anchor alone" in card


def test_impact_without_modelled_holdings_does_not_crash():
    from nordic_desk.views.impact import lede
    assert "No holding has a price series" in lede([])


def test_sort_state_sits_on_the_header_cell(built):
    desk, _, _ = built
    html = desk_page(desk)
    assert "closest('th')" in html and "th[aria-sort]" in html
