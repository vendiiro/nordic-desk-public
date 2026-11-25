"""Forecasts page, stock first: one stock and amount drive a summary, the signal scorecard, lump vs spread and
realistic analyst targets. Data from forecasts.build_forecasts; the page script only picks precomputed sets and scales euros."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .core import esc, nav, page, pct

VANGUARD = ("Lump sum beat spreading about two-thirds of the time in broad markets (Vanguard, *Dollar-cost averaging just means "
            "taking risk later*). Spreading buys a smaller worst case, not a better average. History, not a promise.")
SCRIPT = Path(__file__).with_name("forecasts.js")
GROUP_LABEL = {"held": "Holdings", "watch": "Watchlist", "idea": "Ideas"}

CSS = """
.fc { padding-block: var(--space-lg) var(--space-2xl); display: grid; gap: var(--space-xl); }
.fc p { max-width: 68ch; }
.fc-head { display: grid; gap: var(--space-2xs); }
.fc-head h1 { font-size: var(--text-2xl); }
.asof { font-size: var(--text-sm); color: var(--color-muted); }
fieldset { border: 0; margin: 0; padding: 0; min-width: 0; }
legend, .ctl-l { font-size: var(--text-sm); color: var(--color-muted); padding: 0; margin-bottom: 2px; }
.seg { display: inline-flex; border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); }
.seg button { border: 0; background: var(--color-paper); padding: 0 var(--space-sm); min-height: 40px; font-size: var(--text-sm); cursor: pointer; }
.seg button:first-child { border-radius: var(--radius-pill) 0 0 var(--radius-pill); }
.seg button:last-child { border-radius: 0 var(--radius-pill) var(--radius-pill) 0; }
.seg button + button { border-inline-start: var(--rule-hair) solid var(--color-rule-2); }
.seg button[aria-pressed="true"] { background: var(--color-accent); color: var(--color-accent-ink); }
.seg button:focus-visible { outline-offset: -4px; outline-color: var(--color-accent-ink); }
.seg button[aria-pressed="false"]:focus-visible { outline-color: var(--color-focus); }
/* decide: one stock + amount for the whole page */
.decide { border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-card); background: var(--color-paper);
  box-shadow: 0 1px 2px color-mix(in oklab, var(--color-ink) 6%, transparent), 0 8px 24px -12px color-mix(in oklab, var(--color-ink) 18%, transparent); }
.decide-ctl { display: flex; flex-wrap: wrap; gap: var(--space-sm) var(--space-lg); align-items: end; padding: var(--space-md) var(--space-lg);
  border-bottom: var(--rule-hair) solid var(--color-rule); background: var(--color-paper-2); border-radius: var(--radius-card) var(--radius-card) 0 0; }
.decide-ctl > div { display: grid; gap: 2px; min-width: 0; }
.decide-ctl select { font: inherit; color: var(--color-ink); background: var(--color-paper); border: var(--rule-hair) solid var(--color-rule-2);
  border-radius: var(--radius-pill); min-height: 44px; padding: 0 var(--space-xs); width: min(26rem, 100%); }
.amt { display: inline-flex; align-items: center; border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); background: var(--color-paper); min-height: 44px; }
.amt span { padding-inline: var(--space-sm) 0; color: var(--color-muted); font-family: var(--font-num); }
.amt input { font: inherit; font-family: var(--font-num); color: var(--color-ink); border: 0; background: transparent; width: 8rem; min-height: 42px; padding: 0 var(--space-sm) 0 var(--space-2xs); }
.amt:focus-within { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.amt input:focus-visible { outline: 0; }
.summary { padding: var(--space-md) var(--space-lg) var(--space-lg); display: grid; gap: var(--space-md); }
.summary .now { font-family: var(--font-display); font-size: var(--text-xl); font-weight: var(--display-weight); letter-spacing: var(--tracking-display); }
.facts { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 1100px) { .facts { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: var(--space-md); } .facts > div:nth-child(3) { padding-inline-start: 0; border-inline-start: 0; } }
.facts > div { padding-inline: var(--space-md); display: grid; gap: var(--space-2xs); align-content: start; }
.facts > div:first-child { padding-inline-start: 0; }
.facts > div + div { border-inline-start: var(--rule-hair) solid var(--color-rule); }
.facts h3 { font-family: var(--font-body); font-size: var(--text-sm); font-weight: 500; color: var(--color-muted); letter-spacing: 0; }
.facts .big { font-family: var(--font-num); font-size: var(--text-xl); line-height: 1.15; }
.facts p { font-size: var(--text-sm); color: var(--color-ink-2); }
/* sections */
.blk { border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-lg); display: grid; gap: var(--space-md); scroll-margin-top: var(--space-md); }
.blk-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: var(--space-sm) var(--space-lg); }
.blk-head > div:first-child { display: grid; gap: var(--space-2xs); max-width: 68ch; }
.blk h2 { font-size: var(--text-xl); }
.ctls { display: flex; flex-wrap: wrap; gap: var(--space-md); }
.panels { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-md); }
.panel { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md) var(--space-xs); display: grid; gap: var(--space-2xs); min-width: 0; align-content: start; }
.panel h3 { font-size: var(--text-md); }
.panel .sub { font-size: var(--text-sm); }
.chart { width: 100%; min-height: 40px; }
.chart svg { display: block; width: 100%; height: auto; overflow: visible; }
.chart .gl { stroke: var(--color-rule); } .chart .zero { stroke: var(--color-ink-2); stroke-dasharray: 3 3; }
.chart .good { fill: color-mix(in oklab, var(--color-up) 7%, transparent); }
.chart .ax { fill: var(--color-muted); font: 12px var(--font-num); }
.chart .lab { fill: var(--color-ink); font: 13px var(--font-body); }
.chart .lab.cur { font-weight: 600; }
.chart .ci { stroke: var(--color-ink-2); stroke-width: 2; stroke-linecap: round; }
.chart .dot { stroke: var(--color-paper); stroke-width: 2; }
.chart .ring { fill: none; stroke: var(--color-accent); stroke-width: 2; }
.chart .halo { paint-order: stroke; stroke: var(--color-paper); stroke-width: 4px; stroke-linejoin: round; }
.chart .bar { fill: color-mix(in oklab, var(--color-down) 45%, transparent); } .chart .bar.pos { fill: color-mix(in oklab, var(--color-up) 60%, transparent); }
.chart .med { stroke: var(--color-ink); stroke-width: 1.5; }
.tag { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 0 var(--space-xs); border-radius: 999px; border: 1px solid currentColor; white-space: nowrap; }
.t-helps, .t-consistent { color: var(--color-up); } .t-str { color: var(--color-own); } .t-against { color: var(--color-down); } .t-noedge, .t-few, .t-noisy { color: var(--color-muted); }
tr[aria-current] > * { background: var(--color-sel); }
.ticker { font-family: var(--font-num); font-weight: 600; } .sep { color: var(--color-muted); padding-inline: var(--space-2xs); }
.checks { display: grid; gap: var(--space-2xs); font-size: var(--text-sm); color: var(--color-ink-2); }
.checks dt { font-weight: 600; color: var(--color-ink); } .checks dd { margin: 0 0 var(--space-xs); }
.headline { font-family: var(--font-display); font-size: var(--text-3xl); font-weight: var(--display-weight); letter-spacing: var(--tracking-display); line-height: 1; }
.lump { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--space-lg); align-items: start; }
.lump-out { display: grid; gap: var(--space-sm); }
.fine { font-size: var(--text-sm); color: var(--color-muted); }
.vs-h { font-size: var(--text-md); margin-top: var(--space-sm); padding-top: var(--space-sm); border-top: var(--rule-hair) solid var(--color-rule); }
.warn { font-size: var(--text-sm); color: var(--color-ink-2); }
@media (max-width: 1000px) { .panels, .lump { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
  .facts { grid-template-columns: 1fr; gap: var(--space-sm); }
  .facts > div { padding: 0; } .facts > div + div { border-inline-start: 0; border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-sm); }
  .decide-ctl, .summary { padding-inline: var(--space-md); }
  .stack thead { display: none; }
  .stack tr { display: grid; grid-template-columns: 1fr auto; gap: 2px var(--space-sm); padding-block: var(--space-xs); border-bottom: var(--rule-hair) solid var(--color-rule); }
  .stack th, .stack td { border: 0; padding: 0; white-space: normal; text-align: start; }
  .stack td[data-l]::before { content: attr(data-l) " "; color: var(--color-muted); font-family: var(--font-body); }
  .stack td.r { text-align: end; }
}
"""


def _pct(x, d=0, sign=False):
    return "–" if x is None else pct(x, d, sign)


def _p(x) -> str:
    return "–" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}"


def _risk(r: dict | None) -> str:
    if not r:
        return "<dt>Portfolio 95% risk range</dt><dd>Not checked yet.</dd>"
    ok = min(r["p_value"], r.get("christoffersen_p") or 1.0) >= 0.05  # same rule as the Impact page
    clus = f', clustering test p {_p(r["christoffersen_p"])}' if r.get("christoffersen_p") is not None else ""
    return (f'<dt>Portfolio 95% risk range (21 days) <span class="tag {"t-helps" if ok else "t-against"}">{"calibrated" if ok else "off"}</span></dt>'
            f'<dd>Outside the range on {r["hits"]}/{r["n"]:,} checked days, {_pct(r["rate"], 1)} against {_pct(r["expected"], 0)} expected '
            f'(rate test p {_p(r["p_value"])}{clus}). Calibrated means both tests pass at 5%.</dd>')


def _targets(t: dict) -> str:
    r = t["rates"]
    own = r["n_checked"] >= 30
    lead = (f'Only {_pct(r["met_12m"])} of analyst targets are met after 12 months; {_pct(r["met_any"])} are touched at some point '
            f'during the year ({esc(r["source"])}). Realistic upside is the analyst upside minus {_pct(r["overshoot"], 0)}'
            f'{"" if own else ", the average overshoot in that study"}.')
    later = (f' The desk has checked {r["n_checked"]} of its own targets so far; the first can be checked on {esc(r["first_check"])}.'
             if r.get("first_check") else " The desk has no analyst snapshots yet.")
    rows = "".join(f'<tr data-t="{esc(x["ticker"])}"><th scope="row">{esc(x["name"])}<span class="sep">·</span><span class="ticker">{esc(x["ticker"])}</span></th>'
                   f'<td class="num r" data-l="Price">{esc(x.get("currency") or "")} {x["price"]:,.2f}</td>'
                   f'<td class="num r" data-l="Target">{x["target"]:,.2f}</td><td class="num r" data-l="Analyst upside">{_pct(x["upside"], 0, True)}</td>'
                   f'<td class="num r {"up" if (x["realistic"] or 0) > 0 else "down"}" data-l="Realistic">{_pct(x["realistic"], 0, True)}</td>'
                   f'<td data-l="Our record">{x["record"] or "too few yet"}</td></tr>' for x in t["rows"] if x.get("price"))
    table = ('<div class="table-wrap"><table class="stack"><thead><tr><th scope="col">Stock</th><th scope="col" class="r">Price</th><th scope="col" class="r">Analyst target</th>'
             '<th scope="col" class="r">Analyst upside</th><th scope="col" class="r">Realistic upside</th><th scope="col">Our record</th></tr></thead>'
             f'<tbody id="tg-rows">{rows}</tbody></table></div>') if rows else '<p class="fine">No Ideas cards with an analyst target yet.</p>'
    return f'<p class="sub">{lead}{later}</p>{table}'


def _expected(d: dict) -> str:
    anc, ex = d.get("anchor"), d.get("expected") or {}
    if not anc or not ex:
        return '<p class="fine">Not enough SPY history for an anchor yet.</p>'
    names = {s["ticker"]: s["name"] for s in d["subjects"]}
    rows = "".join(f'<tr data-t="{esc(t)}"><th scope="row">{esc(names.get(t, t))}<span class="sep">·</span><span class="ticker">{esc(t)}</span></th>'
                   f'<td class="num r" data-l="Combined"><b>{_pct(e["combined"], 1, True)}</b></td>'
                   f'<td class="num r" data-l="Analyst">{_pct(e["analyst"], 0, True)}</td><td class="num r" data-l="Signal">{_pct(e["signal"], 1, True)}</td>'
                   f'<td class="num r" data-l="Pieces">{e["pieces"] or "anchor only"}</td></tr>'
                   for t, e in sorted(ex.items(), key=lambda kv: -(kv[1]["combined"] or 0)))
    return (f'<p class="sub">Half of each number is the market anchor, SPY’s own return in euros {esc(anc["from"])}–{esc(anc["to"])}: '
            f'<span class="num">{_pct(anc["rate"], 1, True)}</span> a year. The other half is the average of what the stock adds: the realistic analyst upside '
            f'(price-only, listing currency) and how today’s verdict did across all stocks over 12 months, used only when that history points one way. '
            f'Simple averages like this beat single forecasts out of sample (Rapach, Strauss &amp; Zhou 2010), but the anchor comes from a strong decade '
            f'and the signal piece shares the scorecard’s survivorship bias.</p>'
            '<div class="table-wrap"><table class="stack"><thead><tr><th scope="col">Stock</th><th scope="col" class="r">Combined, 12 m</th>'
            '<th scope="col" class="r">Analyst piece</th><th scope="col" class="r">Signal piece</th><th scope="col" class="r">Pieces used</th></tr></thead>'
            f'<tbody id="ex-rows">{rows}</tbody></table></div>')


def _options(subjects: list[dict]) -> str:
    out = []
    for g, label in GROUP_LABEL.items():
        opts = "".join(f'<option value="{esc(s["ticker"])}">{esc(s["name"])} · {esc(s["ticker"])}</option>'
                       for s in subjects if s["groups"] and s["groups"][0] == g)
        if opts:
            out.append(f'<optgroup label="{label}">{opts}</optgroup>')
    return "".join(out) + '<optgroup label="Market"><option value="SPY">S&amp;P 500 · SPY</option></optgroup>'


def _seg(name: str, attr: str, vals, on) -> str:
    btns = "".join(f'<button type="button" data-{attr}="{v}" aria-pressed="{str(v == on).lower()}">{t}</button>' for v, t in vals)
    return f'<fieldset><legend>{name}</legend><div class="seg">{btns}</div></fieldset>'


def forecasts_page(d: dict, card_default: int) -> str:
    excl = "; ".join(f'{esc(e["ticker"])} ({esc(e["why"])})' for e in d["excluded"])
    asof = max((v["date"] for v in (d.get("today") or {}).values()), default=None)
    vanguard = esc(VANGUARD).replace("*Dollar-cost averaging just means taking risk later*", "<em>Dollar-cost averaging just means taking risk later</em>")
    rates = d["targets"]["rates"]
    analyst_check = ("<dt>Analyst targets</dt><dd>" + (f'{rates["n_checked"]} checked so far; see the last section.' if rates["n_checked"]
                     else f'Too early: the first 12-month check is on {esc(rates["first_check"] or "the first snapshot plus a year")}.') + "</dd>")
    data = json.dumps(d, allow_nan=False, ensure_ascii=False).replace("</", "<\\/")
    body = f"""<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Huurre, home">Huurre</a>
<nav aria-label="Views">{nav("Forecasts")}</nav></div></header>
<main class="container fc">
<header class="fc-head"><h1>Forecasts</h1>
<p class="sub">Pick a stock and an amount: how its buy-timing signal has done, whether to put the money in at once or spread it, and how far to trust the analysts. Every number is checked against what happened afterwards.</p>
<p class="asof">{f"Prices to {esc(asof)} · " if asof else ""}built {esc(d["built"])}</p></header>
<section class="decide" aria-label="Your decision">
<div class="decide-ctl"><div><label for="fc-stock" class="ctl-l">Stock</label><select id="fc-stock">{_options(d["subjects"])}</select></div>
<div><label for="fc-amount" class="ctl-l">Amount</label><span class="amt"><span aria-hidden="true">€</span><input id="fc-amount" type="number" inputmode="numeric" min="1" max="10000000" value="{int(card_default)}"></span></div></div>
<div class="summary" id="fc-summary" aria-live="polite"><noscript><p class="fine">The summary, charts and lump planner need JavaScript. The method notes and the analyst table below work without it.</p></noscript></div>
</section>
<section class="blk" id="expected" aria-labelledby="ex-h"><div class="blk-head"><div><h2 id="ex-h">Expected return, 12 months</h2></div></div>{_expected(d)}</section>
<section class="blk" id="scorecard" aria-labelledby="sc-h">
<div class="blk-head"><div><h2 id="sc-h">Did the timing signal help?</h2>
<p class="sub">Each 6–12-month verdict the desk would have given in the past, rebuilt from prices with no look-ahead, then compared with SPY over the chosen horizon, in euros. One sample per stock per month; the 95% intervals allow for overlapping windows.</p></div>
<div class="ctls">{_seg("Horizon", "hz", (("63", "3 m"), ("126", "6 m"), ("252", "12 m")), "126")}{_seg("Show", "scope", (("all", "All stocks"), ("one", "This stock")), "all")}</div></div>
<div class="panels"><div class="panel"><h3>Buy signals</h3><p class="sub">Good entry: you want them right of 0, ahead of SPY.</p><div class="chart" id="sc-buy"></div></div>
<div class="panel"><h3>Wait signals</h3><p class="sub">Wait and Stretched: you want them left of 0, behind SPY.</p><div class="chart" id="sc-wait"></div></div></div>
<div class="table-wrap"><table class="stack"><thead><tr><th scope="col">Signal</th><th scope="col" class="r">Months</th><th scope="col" class="r">Beat SPY</th>
<th scope="col" class="r" id="sc-avg">Average vs SPY</th><th scope="col" class="r">95% interval</th><th scope="col">Reading</th></tr></thead><tbody id="sc-rows"></tbody></table></div>
<p class="warn">{esc(d["warning"])}</p>
<dl class="checks">{_risk(d.get("risk"))}{analyst_check}</dl>{f'<p class="fine">Left out: {excl}.</p>' if excl else ""}</section>
<section class="blk" id="lump" aria-labelledby="ls-h">
<div class="blk-head"><div><h2 id="ls-h">Lump now or spread it?</h2>
<p class="sub">Every past start month: the whole amount on day one, or equal parts at the start of each month. Both are valued 12 months after the money was ready; money waiting to be invested earns 0%.</p></div>
<div class="ctls">{_seg("Spread over", "k", (("3", "3 m"), ("6", "6 m"), ("12", "12 m")), "6")}</div></div>
<div class="lump"><div class="lump-out" id="ls-out"></div><div class="panel"><h3>Lump minus spread, after 12 months</h3><div class="chart" id="ls-plot"></div></div></div>
<p class="fine">{vanguard} Vol-sized puts less in now when the stock is much jumpier than usual: first part = (usual ÷ current volatility)², at least 25%, the rest over the next months. Volatility management helped factor portfolios (Moreira &amp; Muir 2017); for single purchases it is a rule of thumb, so the block above tests it on this stock's history.</p></section>
<section class="blk" id="targets" aria-labelledby="tg-h"><div class="blk-head"><div><h2 id="tg-h">Analyst targets, made realistic</h2></div></div>{_targets(d["targets"])}</section>
</main>
<footer class="foot"><div class="container"><p>Prices and EUR/USD from Yahoo Finance; analyst snapshots from the desk's own history.</p><p>Not investment advice.</p></div></footer>
<script type="application/json" id="fc-data">{data}</script>"""
    return page("Forecasts", "Stock-first forecasts: signal track record, lump vs spread, realistic analyst targets.", "huurre",
                "P3 H3 E3 S3 R3 V3 · weakest: S, three answers for one stock", CSS, body, f"<script>{SCRIPT.read_text(encoding='utf-8')}</script>")
