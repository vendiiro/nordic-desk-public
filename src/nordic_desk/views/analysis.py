"""Single-stock analysis page (layout A): chart left, verdict and boxes right, hover explanations. Data comes from analysis.payload."""
from __future__ import annotations

import json
from pathlib import Path

from .core import cls, esc, nav, page, pct

GROUP_LABEL = {"held": "Holdings", "watch": "Watchlist", "idea": "Ideas"}
FINE = "Fixed rules on the readings above, not AI. A timing aid for a stock you already want, not a prediction."
CHIPS = [("sma50", "50-day average", "s2"), ("sma200", "200-day average", "s1"), ("bb", "Bollinger Bands", "s3"),
         ("h52", "52-week high", "s4"), ("rsi", "RSI", "s1"), ("macd", "MACD", "s2"), ("dd", "Drawdown", "dn"), ("pe", "P/E history", "s1")]
SCRIPT = Path(__file__).with_name("analysis.js")
INFO = ('<svg class="i" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="7"/>'
        '<path d="M8 7.2v4.3M8 4.6v.1"/></svg>')

CSS = """
.an { padding-block: var(--space-lg) var(--space-xl); }
.an-head { display: flex; flex-wrap: wrap; align-items: end; gap: var(--space-sm) var(--space-lg); margin-bottom: var(--space-md); }
.an-head h1 { font-size: var(--text-2xl); }
.an-head h1 .tk { font-size: var(--text-md); color: var(--color-muted); margin-inline-start: var(--space-xs); }
.an-head .px { font-size: var(--text-xl); }
.an-head .px span { font-size: var(--text-sm); margin-inline-start: var(--space-xs); }
.an-head .ctl { flex: 1 1 100%; display: flex; flex-wrap: wrap; gap: var(--space-sm); align-items: center; }
.an-head .ctl .hold { display: flex; gap: var(--space-xs); align-items: center; }
.pick { display: flex; gap: var(--space-xs); align-items: center; font-size: var(--text-sm); color: var(--color-muted); min-width: 0; flex: 0 1 22rem; }
.pick select { width: 100%; min-width: 0; text-overflow: ellipsis; font: inherit; color: var(--color-ink); background: var(--color-paper); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); min-height: 36px; padding: 0 var(--space-xs); }
.seg { display: inline-flex; border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); overflow: hidden; }
.seg button { border: 0; background: var(--color-paper); padding: 0 var(--space-sm); min-height: 36px; font-size: var(--text-sm); cursor: pointer; }
.seg button + button { border-inline-start: var(--rule-hair) solid var(--color-rule-2); }
.seg button[aria-pressed="true"] { background: var(--color-accent); color: var(--color-accent-ink); }
.an-grid { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: var(--space-lg); align-items: start; }
.an-grid > *, .an-head > * { min-width: 0; }
.toolbar { display: flex; flex-wrap: wrap; gap: var(--space-xs) var(--space-md); align-items: center; margin-bottom: var(--space-sm); }
.toolbar .chips { margin: 0; gap: var(--space-2xs); }
.toolbar .segs { display: flex; gap: var(--space-xs); margin-inline-start: auto; }
.chip .sw { width: 12px; height: 3px; margin-inline-end: var(--space-2xs); }
.chip[aria-pressed="false"] .sw { opacity: 0.35; }
.sw.dn { --c: var(--color-down); }
.an-chart { position: relative; user-select: none; touch-action: pan-y; border-radius: var(--radius-card); }
.an-chart svg { width: 100%; height: auto; }
.an-chart .gl { stroke: var(--color-rule); stroke-width: 1; }
.an-chart .dash { stroke-dasharray: 3 3; } .an-chart .dash2 { stroke-dasharray: 6 3; }
.an-chart .ax { fill: var(--color-muted); font: 11px var(--font-num); }
.an-chart .plab { fill: var(--color-muted); font: 11px var(--font-body); }
.an-chart .ln { fill: none; stroke-linejoin: round; }
.an-chart .price { stroke: var(--color-line); stroke-width: 1.6; }
.an-chart .bb-fill { fill: color-mix(in oklab, var(--color-s3) 9%, transparent); }
.an-chart .pbg { fill: var(--color-paper-2); }
.an-chart .rsi-band { fill: color-mix(in oklab, var(--color-accent) 6%, transparent); }
.an-chart .dd-fill { fill: color-mix(in oklab, var(--color-down) 14%, transparent); }
.an-chart .cu line, .an-chart .cu rect { stroke: var(--color-up); } .an-chart .cu rect { fill: var(--color-paper); }
.an-chart .cd line, .an-chart .cd rect { stroke: var(--color-down); } .an-chart .cd rect { fill: var(--color-down); }
.an-chart .hu { stroke: color-mix(in oklab, var(--color-up) 50%, transparent); } .an-chart .hd { stroke: color-mix(in oklab, var(--color-down) 50%, transparent); }
.an-chart .xh line { stroke: var(--color-ink); stroke-opacity: 0.55; stroke-width: 1.2; stroke-dasharray: 3 3; } .an-chart .xh circle { fill: var(--color-paper); stroke: var(--color-ink); stroke-width: 2; }
.tip, .pop { background: var(--color-paper); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-card); box-shadow: 0 6px 24px color-mix(in oklab, var(--color-ink) 14%, transparent); padding: var(--space-sm) var(--space-sm); font-size: var(--text-sm); line-height: 1.45; display: grid; gap: var(--space-2xs); }
.tip { position: absolute; z-index: 5; width: min(300px, 90%); pointer-events: none; }
.pop { position: fixed; z-index: 20; width: min(320px, calc(100vw - 16px)); pointer-events: none; }
.tip h4, .pop h4 { margin: 0; font-size: var(--text-md); font-weight: 600; }
.k { color: var(--color-muted); }
.formula { font-family: var(--font-num); font-size: 0.78rem; background: var(--color-paper-2); border-radius: 4px; padding: var(--space-2xs) var(--space-xs); }
.rows { display: grid; grid-template-columns: auto 1fr; gap: 1px var(--space-sm); margin: 0; }
.rows dt { color: var(--color-muted); } .rows dd { margin: 0; text-align: end; }
.rail { display: grid; gap: var(--space-sm); }
.rail > div { display: grid; gap: var(--space-sm); }
.verdict, .box, .exp { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md); background: var(--color-paper); }
.verdict { border-color: var(--color-rule-2); }
.lab { font-size: var(--text-sm); color: var(--color-muted); display: flex; justify-content: space-between; gap: var(--space-xs); }
.verdict .big { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: var(--display-weight); letter-spacing: var(--tracking-display); margin: var(--space-2xs) 0; }
.verdict ul { list-style: none; margin: var(--space-xs) 0 0; padding: 0; font-size: var(--text-sm); display: grid; gap: 2px; }
.verdict li { display: grid; grid-template-columns: 14px 1fr; gap: var(--space-xs); }
.verdict li b { font-family: var(--font-num); }
.verdict .fine { font-size: 0.75rem; color: var(--color-muted); margin-top: var(--space-xs); }
.track { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md); background: var(--color-paper-2); font-size: var(--text-sm); display: grid; gap: var(--space-2xs); }
.box { cursor: help; transition: border-color var(--dur-micro) var(--ease-out); }
.box:hover, .box:focus-visible { border-color: var(--color-accent); }
.box .v { font-family: var(--font-num); font-size: var(--text-lg); margin: var(--space-2xs) 0 2px; }
.box p { font-size: var(--text-sm); color: var(--color-ink-2); }
.i { flex: none; fill: none; stroke: var(--color-muted); stroke-width: 1.4; stroke-linecap: round; }
.box:hover .i, .box:focus-visible .i { stroke: var(--color-accent); }
.an-index { max-width: 48rem; padding-block: var(--space-xl); display: grid; gap: var(--space-lg); }
.an-index ul { list-style: none; padding: 0; margin: var(--space-xs) 0 0; display: grid; gap: var(--space-2xs); grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr)); }
.an-index a { display: flex; gap: var(--space-xs); padding: var(--space-xs) var(--space-sm); border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); text-decoration: none; min-height: 44px; align-items: center; }
.an-index a:hover { background: var(--color-paper-2); }
.strip { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--space-sm); margin-top: var(--space-md); }
.exp .v { font-size: var(--text-xl); }
.exp .rows { font-size: var(--text-sm); margin-block: var(--space-2xs); }
@media (min-width: 1101px) { .rail { position: sticky; top: var(--space-md); } }
@media (max-width: 1100px) { .an-grid { grid-template-columns: 1fr; } .rail { order: -1; } .strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
"""


def _slug(t: str) -> str:
    from ..analysis import slug
    return slug(t)


def _bar() -> str:
    return (f'<header class="bar"><div class="container"><a class="mark" href="../index.html" aria-label="Huurre, home">Huurre</a>'
            f'<nav aria-label="Views">{nav("Analysis").replace(chr(34) + chr(34), "").replace("href=" + chr(34), "href=" + chr(34) + "../")}</nav></div></header>')


def _picker(subs, current: str) -> str:
    out = []
    for g, label in GROUP_LABEL.items():
        opts = "".join(f'<option value="{esc(_slug(s.ticker))}.html"{" selected" if s.ticker == current else ""}>{esc(s.name)} ({esc(s.ticker)})</option>'
                       for s in subs if s.groups and s.groups[0] == g)
        if opts:
            out.append(f'<optgroup label="{label}">{opts}</optgroup>')
    return f'<label class="pick">Stock <select id="pick">{"".join(out)}</select></label>'


def _verdict(v: dict | None, label: str, kind: str = "fund") -> str:
    if v is None:
        why = ("Company data has not been fetched yet; run nordic-desk update." if kind == "unknown"
               else "Funds and indices have no P/E or company quality, so there is no long-haul valuation verdict.")
        return f'<div class="verdict"><div class="lab">{label}</div><div class="big neu">No verdict</div><p>{why}</p></div>'
    why = "".join(f"<li><b>{esc(s)}</b><span>{esc(t)}</span></li>" for s, t in v["why"])
    return (f'<div class="verdict"><div class="lab">{label}</div><div class="big {v["cls"]}">{esc(v["v"])}</div>'
            f'<p>{esc(v["line"])}.</p><ul>{why}</ul><p class="fine">{FINE}</p></div>')


def _track(t: dict | None) -> str:
    if not t:
        return ""
    s = t["stats"]
    link = '<a href="../forecasts.html#scorecard">How this is scored</a>'
    if not s:
        return f'<div class="track"><b>Track record for this stock</b><p>No past {esc(t["label"])} months for this stock. {link}</p></div>'
    return (f'<div class="track"><b>Track record for this stock</b><p>{esc(t["label"])} in {s["n_months"]} months since {esc(s["since"])}. '
            f'Beat SPY over the next 6 months {pct(s["beat"], 0, False)} of those times, average {pct(s["mean"])} '
            + (f'({pct(s["lo"])} to {pct(s["hi"])}). ' if s.get("lo") is not None and s.get("hi") is not None
               else "(too few months for an interval). ") + f'<span class="tag neu">{esc(s["reading"])}</span> {link}</p></div>')


def _expected(e: dict | None) -> str:
    if not e:
        return ""
    used = lambda v, d: f'<span class="num">{pct(v, d)}</span>' if v is not None else "not used"  # noqa: E731
    return (f'<div class="exp"><div class="lab">Expected 12 m</div><div class="v num">{pct(e["combined"], 1)}</div>'
            f'<dl class="rows"><dt>Market anchor (SPY, euros)</dt><dd class="num">{pct(e["anchor"], 1)}</dd>'
            f'<dt>Analyst, realistic</dt><dd>{used(e["analyst"], 0)}</dd>'
            f'<dt>Signal history</dt><dd>{used(e["signal"], 1)}</dd></dl>'
            + ('<p class="sub">No stock-specific piece yet: this is the market anchor alone.</p>' if not e["pieces"] else "")
            + '<p class="sub">Half the market anchor, half the average of the stock’s pieces. '
            '<a href="../forecasts.html#expected">How it is made</a></p></div>')


def _boxes(boxes: list[dict]) -> str:
    return "".join(f'<div class="box" tabindex="0" data-k="{b["key"]}"><div class="lab"><span>{esc(b["label"])}</span>{INFO}</div>'
                   f'<div class="v">{esc(b["value"])}</div><p>{esc(b["text"])}</p></div>' for b in boxes)


def analysis_page(p: dict, picker: list) -> str:
    c = [x for x in p["c"] if x is not None]
    d1 = c[-1] / c[-2] - 1 if len(c) > 1 else None
    has_pe = p["kind"] == "stock" and not p["pe_reason"]
    chips = "".join(f'<button type="button" class="chip" data-k="{k}" aria-pressed="false"><span class="sw {sw}" aria-hidden="true"></span>{t}</button>'
                    for k, t, sw in CHIPS if k != "pe" or has_pe)
    ranges = "".join(f'<button type="button" data-r="{n}" aria-pressed="false">{t}</button>' for n, t in ((21, "1M"), (126, "6M"), (252, "1Y"), (1260, "5Y")))
    style = '<button type="button" data-s="line" aria-pressed="false">Line</button>' + (
        '<button type="button" data-s="candle" aria-pressed="false">Candles</button>' if p["has_ohlc"] else "")
    note = f'<p class="sub">{esc(p["note"])}</p>' if p["note"] else ""
    data = json.dumps(p, allow_nan=False, ensure_ascii=False).replace("</", "<\\/")
    body = f"""{_bar()}
<main class="container an">
<div class="an-head">
  <div><h1>{esc(p["name"])}<span class="tk">{esc(p["ticker"])}</span></h1>{note}</div>
  <p class="px num">{esc(p["currency"] or "")} {c[-1]:,.2f}<span class="{cls(d1 or 0)}">{pct(d1, 2) if d1 is not None else ""} last day</span></p>
  <div class="ctl">{_picker(picker, p["ticker"])}
  <div class="hold"><span class="sub">Holding for</span><div class="seg" role="group" aria-label="Holding period"><button type="button" data-h="entry" aria-pressed="true">6–12 months</button><button type="button" data-h="long" aria-pressed="false">Long haul (years)</button></div></div></div>
</div>
<div class="an-grid">
  <section aria-label="Chart">
    <div class="toolbar"><div class="chips" role="group" aria-label="Indicators">{chips}</div>
      <div class="segs"><div class="seg" role="group" aria-label="Range">{ranges}</div><div class="seg" role="group" aria-label="Chart style">{style}</div></div></div>
    <div class="an-chart" id="chart" tabindex="0" aria-label="Price chart. Hover, tap or use the arrow keys to read a day."><noscript><p class="note">The chart needs JavaScript; the verdict and readings work without it.</p></noscript></div>
    <div class="strip" data-h-panel="entry">{_boxes(p["boxes"]["entry"])}</div>
    <div class="strip" data-h-panel="long" hidden>{_boxes(p["boxes"]["long"])}</div>
  </section>
  <aside class="rail" aria-label="Verdict and expected return">
    <div data-h-panel="entry">{_verdict(p["today"]["entry"], "Entry for 6–12 months")}{_expected(p.get("expected"))}{_track(p.get("track"))}</div>
    <div data-h-panel="long" hidden>{_verdict(p["today"]["long"], "Long-haul value", p["kind"])}{_expected(p.get("expected"))}</div>
  </aside>
</div>
</main>
<div class="pop" id="pop" role="tooltip" hidden></div>
<footer class="foot"><div class="container"><p>Prices and company data from Yahoo Finance. Indicators, P/E history and verdicts are computed from daily prices and
annual earnings; earnings count from 90 days after each fiscal year-end. Built {esc(p["built"])}.</p><p>Not investment advice.</p></div></footer>
<script type="application/json" id="analysis-data">{data}</script>"""
    return page(f"{p['ticker']} analysis", f"Chart, indicators and verdict for {p['name']}.", "huurre",
                "P3 H3 E3 S3 R3 V3 · weakest: E, hover boxes carry the teaching", CSS, body,
                f"<script>{SCRIPT.read_text(encoding='utf-8')}</script>")


INDEX_CSS = """
.screen { display: none; padding-block: var(--space-lg) var(--space-2xl); }
.phone-list { display: grid; }
@media (min-width: 900px) { .screen { display: grid; gap: var(--space-md); } .phone-list { display: none; } }
.sc-top { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: end; gap: var(--space-sm) var(--space-lg); }
.sc-top h1 { font-size: var(--text-2xl); }
.chipset { display: flex; flex-wrap: wrap; gap: var(--space-2xs); }
.chipset button, .mix button { cursor: pointer; font: inherit; color: inherit; }
.chipset button { border: var(--rule-hair) solid var(--color-rule-2); background: var(--color-paper); border-radius: 999px; min-height: 36px; padding: 0 var(--space-sm); font-size: var(--text-sm); }
.chipset button[aria-pressed="true"] { background: var(--color-accent); border-color: var(--color-accent); color: var(--color-accent-ink); }
.chipset .n, .mix small { font-family: var(--font-num); opacity: 0.75; }
.mix { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); overflow: hidden; }
.mix button { border: 0; border-inline-end: var(--rule-hair) solid var(--color-rule); background: var(--color-paper); padding: var(--space-xs) var(--space-md); text-align: start; display: grid; gap: 2px; }
.mix button:last-child { border-inline-end: 0; }
.mix button[aria-pressed="true"] { background: var(--color-sel); }
.mix .k { font-size: var(--text-sm); color: var(--color-muted); }
.mix .v { font-family: var(--font-num); font-size: var(--text-xl); }
.mix small { font-size: 0.75rem; margin-inline-start: var(--space-xs); font-family: var(--font-body); }
.sc-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-lg); align-items: start; }
@media (min-width: 1360px) { .sc-grid { grid-template-columns: minmax(0, 1fr) 260px; } .sc-side { position: sticky; top: var(--space-sm); } }
@media (max-width: 1359px) { .sc-side { grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: start; } }
.sc-grid > * { min-width: 0; }
.sc-table th, .sc-table td { padding: 6px 6px; }
.sc-table thead th { position: sticky; top: 0; background: var(--color-paper); z-index: 1; font-size: 0.75rem; }
.sc-table tbody tr { cursor: pointer; }
.sc-table tbody tr:hover { background: var(--color-paper-2); }
.sc-table .nm { max-width: 210px; }
.nmw { display: flex; align-items: baseline; min-width: 0; }
.nmw a { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.nmw .tk, .nmw .grp { flex: none; }
.sc-table .nm a { text-decoration: none; font-weight: 500; }
.sc-table .nm a:hover { text-decoration: underline; }
.sc-table .nm .tk { font-size: 0.75rem; color: var(--color-muted); margin-inline-start: var(--space-2xs); }
.grp { font-size: 0.7rem; color: var(--color-muted); border: var(--rule-hair) solid var(--color-rule-2); border-radius: 4px; padding: 0 4px; margin-inline-start: var(--space-2xs); }
.new { font-size: 0.7rem; color: var(--color-accent); font-weight: 600; margin-inline-start: var(--space-2xs); }
.cell { display: inline-block; min-width: 58px; padding: 1px 6px; border-radius: 5px; font: 500 0.75rem var(--font-num); text-align: center; }
.c-pos { background: color-mix(in oklab, var(--color-up) 14%, var(--color-paper)); color: color-mix(in oklab, var(--color-up) 80%, var(--color-ink)); }
.c-neg { background: color-mix(in oklab, var(--color-down) 12%, var(--color-paper)); color: color-mix(in oklab, var(--color-down) 80%, var(--color-ink)); }
.c-warn { background: color-mix(in oklab, var(--color-own) 14%, var(--color-paper)); color: color-mix(in oklab, var(--color-own) 75%, var(--color-ink)); }
.c-neu { background: var(--color-paper-3); color: var(--color-ink-2); }
.spark { display: block; } .spark .p { fill: none; stroke: var(--color-ink-2); stroke-width: 1.3; } .spark .m { fill: none; stroke: var(--color-accent); stroke-width: 1; stroke-dasharray: 2 2; }
.r52 { display: inline-block; width: 54px; height: 6px; background: var(--color-paper-3); border-radius: 3px; position: relative; vertical-align: middle; }
.r52 i { position: absolute; top: -2px; width: 3px; height: 10px; background: var(--color-ink); border-radius: 1px; }
.sc-side { display: grid; gap: var(--space-sm); }
.sc-side .box { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md); display: grid; gap: var(--space-xs); font-size: var(--text-sm); }
.sc-side h2 { font-size: var(--text-md); }
.mixrow { display: grid; grid-template-columns: 72px 1fr; gap: var(--space-xs); align-items: center; }
.stack { display: flex; height: 10px; border-radius: 3px; overflow: hidden; background: var(--color-paper-3); }
.stack i { display: block; } .stack .g { background: var(--color-up); } .stack .s { background: var(--color-own); } .stack .w { background: var(--color-down); }
.mix-key { display: flex; gap: var(--space-sm); flex-wrap: wrap; color: var(--color-muted); font-size: 0.75rem; }
.mix-key i { display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-inline-end: 4px; vertical-align: -1px; }
.tipbox { position: fixed; z-index: 30; pointer-events: none; background: var(--color-paper); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-card);
  box-shadow: 0 8px 24px -8px color-mix(in oklab, var(--color-ink) 25%, transparent); padding: var(--space-xs) var(--space-sm); width: 280px; font-size: var(--text-sm); }
.tipbox b { display: block; }
"""
SIGNALS = ("Trend", "Stretch", "Momentum", "Risk", "Valuation")


def _signal_cells(r: dict) -> list[tuple[str, str, str, float | None]]:
    """(css class, short text, explanation, sort value) for the five signals behind the verdict."""
    d, rsi, pb, mom, dd, vol, pe = (r.get(k) for k in ("dist200", "rsi", "pct_b", "mom", "drawdown", "vol", "pe_pct"))
    trend = ("c-neu", "–", "Not enough history for the 200-day average.", None) if d is None else (
        "c-pos" if d > 0.02 else "c-neg" if d < -0.02 else "c-neu", ("Up " if d > 0.02 else "Down " if d < -0.02 else "Flat ") + pct(d, 0),
        f"Price {pct(d, 1)} against its 200-day average.", d)
    stretch = ("c-neu", "–", "Not enough history for RSI.", None) if rsi is None else (
        "c-warn" if rsi > 70 or (pb or 0) > 0.95 else "c-pos" if rsi < 40 or (pb is not None and pb < 0.2) else "c-neu", f"RSI {rsi:.0f}",
        f"RSI {rsi:.1f}" + (f", Bollinger %B {pb * 100:.0f}%" if pb is not None else "") + ". Below 40 or near the lower band is a dip; above 70 is stretched.", rsi)
    momc = ("c-neu", "–", "Less than a year of prices.", None) if mom is None else (
        "c-pos" if mom > 0 else "c-neg", pct(mom, 0), f"12-1 month return {pct(mom, 1)}; positive tends to continue for months (strong evidence).", mom)
    risk = ("c-neu", "–", "No drawdown yet.", None) if dd is None else (
        "c-neg" if dd < -0.25 else "c-warn" if dd < -0.1 else "c-neu", pct(dd, 0),
        f"{pct(dd, 1)} below its peak" + (f"; volatility {pct(vol, 0, False)} a year." if vol is not None else "."), dd)
    val = ("c-neu", "n/a", "No P/E: a fund, or too little earnings history.", None) if pe is None else (
        "c-pos" if pe < 0.3 else "c-neg" if pe > 0.7 else "c-neu", "Cheap" if pe < 0.3 else "Rich" if pe > 0.7 else "Fair",
        f"P/E cheaper than {round((1 - pe) * 100)}% of its own window.", pe)
    return [trend, stretch, momc, risk, val]


def _spark(vals: list[float], w: int = 76, h: int = 24) -> str:
    if len(vals) < 2:
        return ""
    ma = [sum(vals[max(0, i - 19):i + 1]) / len(vals[max(0, i - 19):i + 1]) for i in range(len(vals))]
    lo, hi = min(vals + ma), max(vals + ma)
    X = lambda i: i / (len(vals) - 1) * w
    Y = lambda v: h - 2 - (h - 4) * ((v - lo) / (hi - lo) if hi > lo else 0.5)
    path = lambda a: "".join(("L" if i else "M") + f"{X(i):.1f} {Y(v):.1f}" for i, v in enumerate(a))
    return f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true"><path class="m" d="{path(ma)}"/><path class="p" d="{path(vals)}"/></svg>'


def _screener(rows: list[dict]) -> str:
    counts = {k: sum(1 for r in rows if r["cls"] == k) for k in ("good", "str", "wait")}
    n = {g: sum(1 for r in rows if r["group"] == g) for g in GROUP_LABEL}
    chips = (f'<button type="button" data-g="all" aria-pressed="true">All <span class="n">{len(rows)}</span></button>'
             + "".join(f'<button type="button" data-g="{g}" aria-pressed="false">{lab} <span class="n">{n[g]}</span></button>'
                       for g, lab in GROUP_LABEL.items() if n[g]))
    mix = ('<div class="mix" role="group" aria-label="Filter by verdict">'
           f'<button type="button" data-v="all" aria-pressed="true"><span class="k">All verdicts</span><span class="v">{len(rows)}</span></button>'
           f'<button type="button" data-v="good" aria-pressed="false"><span class="k">Good entry</span><span class="v good">{counts["good"]}<small>pullbacks and steady uptrends</small></span></button>'
           f'<button type="button" data-v="str" aria-pressed="false"><span class="k">Stretched</span><span class="v str">{counts["str"]}<small>far above their range</small></span></button>'
           f'<button type="button" data-v="wait" aria-pressed="false"><span class="k">Wait</span><span class="v wait">{counts["wait"]}<small>down or no clear trend</small></span></button></div>')
    head = "".join(f'<th scope="col"{" class=r" if r else ""}><button type="button" data-s="{k}">{lab}</button></th>' for k, lab, r in (
        ("name", "Stock", 0), ("price", "Price", 1), ("d1", "1 day", 1))) + '<th scope="col">Verdict</th>' + "".join(
        f'<th scope="col"><button type="button" data-s="s{i}">{lab}</button></th>' for i, lab in enumerate(SIGNALS)) + "".join(
        f'<th scope="col" class="r"{" aria-sort=descending" if k == "expected" else ""}><button type="button" data-s="{k}">{lab}</button></th>'
        for k, lab in (("expected", "Expected 12 m"), ("upside", "Analyst"))) + '<th scope="col">3 months</th><th scope="col"><button type="button" data-s="pos52">52 w</button></th>'
    body = []
    for r in sorted(rows, key=lambda r: -(r["expected"] if r["expected"] is not None else -9)):
        cells = _signal_cells(r)
        sortv = " ".join(f'data-s{i}="{"" if v is None else round(v, 4)}"' for i, (*_, v) in enumerate(cells))
        num = lambda x: "" if x is None else round(x, 6)
        body.append(
            f'<tr data-t="{esc(r["ticker"])}" data-g="{r["group"]}" data-v="{r["cls"]}" data-name="{esc(r["name"].lower())}" data-price="{num(r["price"])}" '
            f'data-d1="{num(r["d1"])}" data-expected="{num(r["expected"])}" data-upside="{num(r["upside"])}" data-pos52="{num(r["pos52"])}" {sortv}>'
            f'<th scope="row" class="nm" title="{esc(r["name"])}"><div class="nmw"><a href="{esc(_slug(r["ticker"]))}.html">{esc(r["name"])}</a><span class="tk">{esc(r["ticker"])}</span>'
            f'<span class="grp">{r["group"]}</span></div></th>'
            f'<td class="num r">{r["price"]:,.2f}</td><td class="num r {cls(r["d1"] or 0)}">{pct(r["d1"], 1) if r["d1"] is not None else "–"}</td>'
            f'<td><span class="tag {r["cls"]}" title="{esc(r["line"])}">{esc(r["verdict"])}</span>{"<span class=new>new</span>" if r["changed"] else ""}</td>'
            + "".join(f'<td><span class="cell {c}" tabindex="0" data-tip="{esc(SIGNALS[i])}: {esc(t)}|{esc(x)}">{esc(t)}</span></td>' for i, (c, t, x, _) in enumerate(cells))
            + f'<td class="num r"><b>{pct(r["expected"], 1) if r["expected"] is not None else "–"}</b></td>'
            f'<td class="num r">{pct(r["upside"], 0) if r["upside"] is not None else "–"}</td>'
            f'<td>{_spark(r["spark"])}</td><td><span class="r52" title="{r["pos52"] * 100:.0f}% of its 52-week range"><i style="left:calc({r["pos52"] * 100:.0f}% - 1px)"></i></span></td></tr>')
    stack = lambda rs: "".join(f'<i class="{k[0]}" style="width:{sum(1 for r in rs if r["cls"] == k) / max(1, len(rs)) * 100:.0f}%"></i>' for k in ("good", "str", "wait"))
    side_mix = "".join(f'<div class="mixrow"><span>{lab}</span><div class="stack" title="verdicts in {lab.lower()}">{stack([r for r in rows if r["group"] == g])}</div></div>'
                       for g, lab in GROUP_LABEL.items() if n[g])
    changed = [r for r in rows if r["changed"]]
    ch = "".join(f'<div><a href="{esc(_slug(r["ticker"]))}.html">{esc(r["ticker"])}</a> now <span class="tag {r["cls"]}">{esc(r["verdict"])}</span></div>' for r in changed) or "<p>No verdict changed since the last run.</p>"
    return f"""<section class="container screen" id="screener" aria-label="Screener">
<div class="sc-top"><div><h1>Analysis</h1><p class="sub">{len(rows)} stocks and funds. Each verdict comes from fixed rules on the five signals to its right; hover or focus a cell for the number and the rule.</p></div>
<div class="chipset" role="group" aria-label="Filter by group">{chips}</div></div>
{mix}
<div class="sc-grid"><div class="table-wrap"><table class="sc-table"><thead><tr>{head}</tr></thead><tbody id="sc-body">{"".join(body)}</tbody></table></div>
<aside class="sc-side" aria-label="Summary"><div class="box"><h2>Verdict mix</h2>{side_mix}
<div class="mix-key"><span><i style="background:var(--color-up)"></i>Good entry</span><span><i style="background:var(--color-own)"></i>Stretched</span><span><i style="background:var(--color-down)"></i>Wait</span></div></div>
<div class="box"><h2>Changed since last run</h2>{ch}</div>
<div class="box"><h2>How to read it</h2><p>Green helps a purchase now, red warns, amber means stretched, grey is neutral or unknown; every cell also says it in words. Expected return is half SPY’s own return, half the stock’s analyst and signal pieces. Click a stock for its chart.</p></div></aside></div>
</section>"""


INDEX_JS = """<script>
(() => {
  const body = document.getElementById('sc-body'); if (!body) return;
  const rows = [...body.rows], st = {g: 'all', v: 'all', s: 'expected', dir: -1};
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.get('g')) st.g = h.get('g'); if (h.get('v')) st.v = h.get('v'); if (h.get('s')) st.s = h.get('s'); if (h.get('d')) st.dir = +h.get('d') || -1;
  const val = (r, k) => { const x = r.dataset[k]; return k === 'name' ? x : (x === '' || x === undefined ? null : +x); };
  function draw() {
    rows.sort((a, b) => { const x = val(a, st.s), y = val(b, st.s);
      if (x === null && y === null) return 0; if (x === null) return 1; if (y === null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * st.dir; }).forEach(r => body.append(r));
    rows.forEach(r => { r.hidden = (st.g !== 'all' && r.dataset.g !== st.g) || (st.v !== 'all' && r.dataset.v !== st.v); });
    document.querySelectorAll('[data-g]').forEach(b => b.tagName === 'BUTTON' && b.setAttribute('aria-pressed', b.dataset.g === st.g));
    document.querySelectorAll('.mix [data-v]').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === st.v));
    document.querySelectorAll('thead [data-s]').forEach(b => { const th = b.closest('th'); b.dataset.s === st.s ? th.setAttribute('aria-sort', st.dir < 0 ? 'descending' : 'ascending') : th.removeAttribute('aria-sort'); });
    history.replaceState(null, '', '#' + new URLSearchParams({g: st.g, v: st.v, s: st.s, d: st.dir}));
  }
  document.querySelectorAll('.chipset [data-g]').forEach(b => b.addEventListener('click', () => { st.g = b.dataset.g; draw(); }));
  document.querySelectorAll('.mix [data-v]').forEach(b => b.addEventListener('click', () => { st.v = b.dataset.v; draw(); }));
  document.querySelectorAll('thead [data-s]').forEach(b => b.addEventListener('click', () => { st.dir = st.s === b.dataset.s ? -st.dir : (b.dataset.s === 'name' ? 1 : -1); st.s = b.dataset.s; draw(); }));
  body.addEventListener('click', e => { if (e.target.closest('a, .cell')) return; const tr = e.target.closest('tr'); if (tr) location.href = tr.querySelector('a').href; });
  const tip = document.createElement('div'); tip.className = 'tipbox'; tip.hidden = true; tip.setAttribute('role', 'tooltip'); document.body.append(tip);
  const show = el => { const [t, x] = el.dataset.tip.split('|'); tip.replaceChildren(Object.assign(document.createElement('b'), {textContent: t}), x); tip.hidden = false;
    const r = el.getBoundingClientRect(); let y = r.bottom + 6; if (y + tip.offsetHeight > innerHeight) y = r.top - tip.offsetHeight - 6;
    tip.style.left = Math.min(innerWidth - 290, r.left) + 'px'; tip.style.top = y + 'px'; };
  document.addEventListener('mouseover', e => { const el = e.target.closest('[data-tip]'); el ? show(el) : (tip.hidden = true); });
  document.addEventListener('focusin', e => { const el = e.target.closest('[data-tip]'); el ? show(el) : (tip.hidden = true); });
  draw();
})();
</script>"""


def analysis_index(picker: list, rows: list[dict] | None = None) -> str:
    groups = []
    for g, label in GROUP_LABEL.items():
        items = "".join(f'<li><a href="{esc(_slug(s.ticker))}.html"><span class="tk">{esc(s.ticker)}</span><span>{esc(s.name)}</span></a></li>'
                        for s in picker if s.groups and s.groups[0] == g)
        if items:
            groups.append(f'<section><h2>{label}</h2><ul>{items}</ul></section>')
    phone = f"""<main class="container an-index phone-list"><h1>Analysis</h1><p class="sub">Pick a stock: chart, indicators with explanations, and a rules-based verdict for 6–12 months or the long haul.</p>
{"".join(groups)}</main>"""
    body = f"""{_bar()}{_screener(rows) if rows else ""}{phone if rows else phone.replace(" phone-list", "")}<footer class="foot"><div class="container"><p>Prices from Yahoo Finance; verdicts are fixed rules, not AI.</p><p>Not investment advice.</p></div></footer>"""
    return page("Analysis", "Signal screener for holdings, watchlist and ideas.", "huurre", "P3 H3 E3 S3 R3 V3 · weakest: V, a dense table; colour always paired with words",
                CSS + INDEX_CSS, body, INDEX_JS if rows else "")
