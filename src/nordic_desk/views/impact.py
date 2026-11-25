"""Huurre Impact: money against risk per holding, what-if scenarios, glossary, record. Ported from the mockup."""
from __future__ import annotations

from .core import (MONTHS, clock, cls, day, esc, eur, footer, nav, nice_ticks, num, page, path, pct, scale)
from .huurre import CSS as DESK_CSS

AMOUNTS = (500, 1000, 2500, 5000)

CSS = DESK_CSS + """
.legend { display: flex; gap: var(--space-md); flex-wrap: wrap; }
.legend span { display: inline-flex; align-items: center; gap: var(--space-xs); }
.legend i { display: inline-block; width: 14px; height: 8px; }
.kw, .bar-w { background: var(--color-rule-2); }
.kr, .bar-r { background: var(--color-accent); }
.km { background: var(--color-line); height: 2px !important; } .kf { background: var(--color-muted); height: 2px !important; }
.risk th:first-child, .rank th:first-child { padding-inline-start: var(--space-md); }
.risk .nm { display: block; max-width: none; white-space: normal; font-size: var(--text-sm); color: var(--color-muted); }
.bars { width: 28%; min-width: 160px; }
.bars span { display: block; height: 8px; inline-size: calc(var(--w) * 100%); }
.bars span + span { margin-top: var(--space-2xs); }
.whatif { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--gap); }
.controls { display: grid; gap: var(--space-xs); margin-bottom: var(--space-md); }
.controls .chips { margin: 0; align-items: center; }
.lg { float: left; width: 9rem; padding-top: var(--space-xs); color: var(--color-muted); font-size: var(--text-sm); }
.out { border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-md); }
.scn { display: grid; gap: var(--space-sm); }
.scn h3 { font-size: var(--text-lg); }
.scn-grid { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--space-xl); align-items: start; }
.facts.one { grid-template-columns: minmax(0, 1fr); }
.gloss { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr)); gap: var(--space-md) var(--space-lg); }
.g { display: grid; gap: var(--space-2xs); align-content: start; padding-top: var(--space-sm); border-top: var(--rule-hair) solid var(--color-rule); }
.g dt { font-weight: 600; }
.g dd { margin: 0; display: grid; gap: var(--space-xs); }
.fm { font-family: var(--font-num); font-size: var(--text-sm); color: var(--color-ink-2); }
.ex { font-size: var(--text-sm); color: var(--color-accent); }
.chip input[type="radio"] { position: absolute; opacity: 0; width: 1px; height: 1px; }
.lede { padding-top: var(--space-lg); display: grid; gap: var(--space-2xs); }
.lede h1 { font-size: var(--text-2xl); }
.lede p { color: var(--color-ink-2); max-width: 70ch; }
details summary { cursor: pointer; color: var(--color-ink-2); padding-block: var(--space-xs); min-height: 36px; }
.istrip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: var(--space-lg); padding-block: var(--space-lg); border-bottom: var(--rule-hair) solid var(--color-rule); }
@media (max-width: 75rem) { .scn-grid { grid-template-columns: minmax(0, 1fr); } .istrip { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 40rem) { .lg { float: none; width: auto; } }
"""

JS = """
<script>
(() => {
  const f = document.querySelector('.controls');
  const val = n => (f.querySelector('input[name="' + n + '"]:checked') || {}).value;
  const show = () => {
    const m = val('mode');
    f.querySelectorAll('[data-for]').forEach(el => { el.hidden = el.dataset.for !== m; });
    const id = m === 'add' ? 'add-' + val('tk') + '-' + val('amt') : 'sell-' + val('sl');
    document.querySelectorAll('[data-scn]').forEach(el => { el.hidden = el.dataset.scn !== id; });
    const shown = document.querySelector('[data-scn="' + id + '"] h3');
    document.getElementById('scn-say').textContent = shown ? shown.textContent : '';
  };
  f.addEventListener('change', show); show();
})();
</script>"""


def numn(x) -> str:
    return "none" if x is None else num(x)


def pp(d: float) -> str:
    return num(d * 100, 2, sign=True) + chr(0xA0) + "pp"


def good(d: float, lower_is_better: bool = True) -> str:
    if abs(d) < 1e-9:
        return "flat"
    return "up" if (d < 0) == lower_is_better else "down"


def istrip(p: dict, n: int, cap: float = 0.5) -> str:
    return f"""
<section class="container istrip" aria-label="Portfolio risk">
  <div class="fig"><span class="pl">Portfolio</span><span class="v">{eur(p["value"])}</span><span class="note">{n} holdings and cash</span></div>
  <div class="fig"><span class="pl">Volatility, 1 year</span><span class="v sm">{pct(p["vol"], 1, False)}</span><span class="note">past year, today’s weights</span></div>
  <div class="fig"><span class="pl">Beta to S&amp;P 500, in euros</span><span class="v sm">{p["beta"]:.2f}</span></div>
  <div class="fig"><span class="pl">Effective holdings</span><span class="v sm">{p["enb"]:.1f}</span><span class="note">of {n + 1} by count</span></div>
  <div class="fig"><span class="pl">Technology share</span><span class="v sm">{pct(p["tech"], 0, False)}</span><span class="note">cap {pct(cap, 0, False)}</span></div>
</section>"""


MODEL_NAMES = {"ewma": "EWMA", "garch": "GARCH-t", "bootstrap": "Block bootstrap", "regime": "Markov regimes"}


def forecast_section(f: dict | None) -> str:
    if not f:
        return ""
    head = f["models"][f["headline"]] if "models" in f else f
    name = lambda m: (f.get("models", {}).get(m) or {}).get("label") or MODEL_NAMES.get(m, m)
    rg = f.get("regime")
    regime = (f'<p>Probability of the high-volatility regime now: <b class="num">{pct(rg["p_high"], 0, False)}</b> '
              f'(volatility {pct(rg["sigma_low"] * 252 ** 0.5, 0, False)} a year in the calm regime, {pct(rg["sigma_high"] * 252 ** 0.5, 0, False)} in the volatile one).</p>'
              if rg else "")
    rows = []
    for m, d in (f.get("models") or {}).items():
        c = d.get("calibration")
        check = (f'<td class="num r">{pct(c["rate"], 1, False)} of {c["n"]}</td><td class="num r">{c["kupiec_p"]:.2f}</td><td class="num r">{c["christoffersen_p"]:.2f}</td>'
                 if c else '<td class="r" colspan="3">not enough history</td>')
        star = " (shown above)" if m == f.get("headline") else ""
        rows.append(f'<tr><th scope="row">{name(m)}{star}</th><td class="num r">{eur(d["low"])} to {eur(d["high"])}</td>'
                    f'<td class="num r">{pct(d["vol_ann"], 1, False)}</td>{check}</tr>')
    table = ('<div class="table-wrap"><table><thead><tr><th scope="col">Model</th><th scope="col" class="r">95% range, next month</th>'
             '<th scope="col" class="r">Volatility now</th><th scope="col" class="r">Days beyond the 95% line</th>'
             '<th scope="col" class="r">Rate test p</th><th scope="col" class="r">Clustering test p</th></tr></thead><tbody>'
             + "".join(rows) + "</tbody></table></div>") if rows else ""
    b = f.get("backtest")
    if b:
        ok = min(b["p_value"], b.get("christoffersen_p", 1.0)) >= 0.05
        check = (f'<p class="note">Checked without look-ahead since {day(b["start"])}: each day’s line uses only earlier days '
                 f'(GARCH and Markov are refitted monthly, EWMA updates daily, the bootstrap uses the past 500 days). '
                 f'Expected 5% of days beyond the line, {name(f.get("headline"))} had {pct(b["rate"], 1, False)}; '
                 f'{"consistent" if ok else "not consistent"} with its 95% line. A p-value under 0.05 in either test means the model misjudges risk.</p>')
    else:
        check = '<p class="note">The models cannot be checked yet: that needs about two years of history shared by the holdings.</p>'
    excl = (f'<p class="note">Left out of the models and counted as cash: {esc(", ".join(f["excluded"]))}.</p>' if f.get("excluded") else "")
    return f"""<section class="container sec" aria-labelledby="fc-h"><div class="panel"><h2 id="fc-h">Next month</h2>
<p>Over the next {f["horizon_days"]} trading days the portfolio has a 95% range of <b class="num">{eur(head["low"])}</b> to <b class="num">{eur(head["high"])}</b>,
from {eur(f["value"])} today ({name(f.get("headline")) + (", the best-calibrated model" if f.get("backtest") else "; the models cannot be checked yet")}).</p>
{regime}{f"<details><summary>How well each model has done</summary>{table}{check}</details>" if table else check}{excl}</div></section>"""


def risk_section(H: list) -> str:
    mx = max(max(h["weight"], h["risk"]) for h in H)
    from ..analysis import analysis_href
    link = lambda h: f'<a href="{esc(analysis_href(h["ticker"]))}">{esc(h["name"])}</a>' if analysis_href(h["ticker"]) else esc(h["name"])
    rows = "".join(f"""<tr><th scope="row">{link(h)}{f'<span class="nm">{esc(h["note"])}</span>' if h["note"] else ""}</th>
<td class="bars"><span class="bar-w" style="--w:{h["weight"] / mx:.4f}"></span><span class="bar-r" style="--w:{h["risk"] / mx:.4f}"></span></td>
<td class="num r">{pct(h["weight"], 1, False)}</td><td class="num r">{pct(h["risk"], 1, False)}</td>
<td class="num r {"down" if h["risk"] / h["weight"] > 1.15 else "up" if h["risk"] / h["weight"] < 0.85 else "flat"}">{h["risk"] / h["weight"]:.2f}×</td>
<td class="num r">{pct(h["vol"], 0, False)}</td><td class="num r">{numn(h["corr"])}</td><td class="num r">{num(h["down"])}</td>
<td class="num r {cls(h["ret"])}">{pct(h["ret"], 0)}</td></tr>""" for h in H)
    top3 = (f'<p class="sub">The three largest risk sources make up {pct(sum(h["risk"] for h in H[:3]), 0, False)} of the swings.</p>'
            if len(H) >= 3 else "")
    return f"""
<section class="container sec" aria-labelledby="rk-h"><div class="panel flush">
  <div class="sec-head"><div><h2 id="rk-h">Where the risk comes from</h2>{top3}</div>
  <p class="legend sub"><span><i class="kw"></i>share of money</span><span><i class="kr"></i>share of risk</span></p></div>
  <div class="table-wrap"><table class="risk"><thead><tr><th scope="col">Holding</th><th scope="col">Money and risk</th><th scope="col" class="r">Weight</th>
  <th scope="col" class="r">Risk share</th><th scope="col" class="r">Risk ÷ weight</th><th scope="col" class="r">Volatility</th>
  <th scope="col" class="r">Correlation</th><th scope="col" class="r">On bad days</th><th scope="col" class="r">1 year</th></tr></thead>
  <tbody>{rows}</tbody></table></div></div></section>"""


def scenario(s: dict, B: dict, cand: dict, hidden: bool, cap: float = 0.5) -> str:
    rows = [("Volatility, 1 year", pct(B["vol"], 1, False), pct(s["vol"], 1, False), pp(s["vol"] - B["vol"]), good(s["vol"] - B["vol"])),
            ("Beta to S&P 500", f'{B["beta"]:.2f}', f'{s["beta"]:.2f}', num(s["beta"] - B["beta"], 2, True), good(s["beta"] - B["beta"])),
            ("Worst fall, past year", pct(B["worst"]), pct(s["worst"]), pp(s["worst"] - B["worst"]), good(s["worst"] - B["worst"], False)),
            ("Effective holdings", f'{B["enb"]:.1f}', f'{s["enb"]:.1f}', num(s["enb"] - B["enb"], 1, True), good(s["enb"] - B["enb"], False)),
            (f"Technology share, cap {pct(cap, 0, False)}", pct(B["tech"], 1, False), pct(s["tech"], 1, False),
             pp(s["tech"] - B["tech"]), "down" if s["tech"] > cap else "flat"),
            ("Past year, these weights", pct(B["ret"]), pct(s["ret"]), pp(s["ret"] - B["ret"]), "flat")]
    trs = "".join(f'<tr><th scope="row">{esc(a)}</th><td class="num r">{b}</td><td class="num r">{c}</td><td class="num r {k}">{d}</td></tr>'
                  for a, b, c, d, k in rows)
    if s["kind"] == "add":
        head = f'Add {eur(s["amount"])} of {esc(s["ticker"])}'
        say = (f'Over the past year {s["ticker"]} had a correlation of {num(cand["corr"])} with your holdings and {num(cand["down"])} '
               f'on your worst fifth of days. Volatility goes from {pct(B["vol"], 1, False)} to {pct(s["vol"], 1, False)}.')
        side = [("Correlation with your holdings", num(cand["corr"])), ("On your worst 20% of days", num(cand["down"])),
                ("Its own volatility", pct(cand["vol"], 0, False)), ("Its past year, in euros", pct(cand["ret"], 0)),
                ("Its risk share after", pct(s["own_risk"], 1, False))]
    else:
        head = f'Sell {esc(s["name"])} and spread the money over the rest'
        say = (f'{s["name"]} had a correlation of {num(cand["corr"])} with the rest of the portfolio. Without it volatility goes from '
               f'{pct(B["vol"], 1, False)} to {pct(s["vol"], 1, False)}.')
        side = [("Correlation with the rest", num(cand["corr"])), ("On your worst 20% of days", num(cand["down"])),
                ("Its own volatility", pct(cand["vol"], 0, False)), ("Its past year, in euros", pct(cand["ret"], 0))]
    if s["tech"] > cap:
        say += f' Technology share goes to {pct(s["tech"], 0, False)}, over the {pct(cap, 0, False)} cap.'
    dl = "".join(f"<div><dt>{a}</dt><dd class=\"num\">{b}</dd></div>" for a, b in side)
    return (f'<div class="scn" data-scn="{esc(s["id"])}"{" hidden" if hidden else ""}><h3>{head}</h3><p>{esc(say)}</p>'
            f'<div class="scn-grid"><div class="table-wrap"><table><thead><tr><th scope="col">Measure</th><th scope="col" class="r">Now</th>'
            f'<th scope="col" class="r">After</th><th scope="col" class="r">Change</th></tr></thead><tbody>{trs}</tbody></table></div>'
            f'<dl class="facts one">{dl}</dl></div></div>')


def whatif(imp: dict, B: dict) -> str:
    cands = {c["ticker"]: c for c in imp["candidates"]}
    hold = {h["ticker"]: h for h in imp["holdings"]}
    adds = list(cands)
    t0 = adds[0]
    amounts, a0, cap = imp.get("amounts", AMOUNTS), imp.get("default_amount", 1000), imp.get("tech_max", 0.5)
    default = f"add-{t0}-{a0}"
    blocks = "".join(scenario(s, B, cands[s["ticker"]] if s["kind"] == "add" else hold[s["ticker"]], s["id"] != default, cap)
                     for s in imp["scenarios"])
    radio = lambda n, v, label, on: f'<label class="chip"><input type="radio" name="{n}" value="{esc(v)}"{" checked" if on else ""}>{esc(label)}</label>'
    sells = [s for s in imp["scenarios"] if s["kind"] == "sell"]
    ranked = sorted([s for s in imp["scenarios"] if s["kind"] == "add" and s["amount"] == a0], key=lambda s: s["vol"])
    rank = "".join(f'<tr><th scope="row"><span class="tk">{esc(s["ticker"])}</span></th><td class="num r">{num(cands[s["ticker"]]["corr"])}</td>'
                   f'<td class="num r">{num(cands[s["ticker"]]["down"])}</td><td class="num r {good(s["vol"] - B["vol"])}">{pp(s["vol"] - B["vol"])}</td>'
                   f'<td class="num r {good(s["beta"] - B["beta"])}">{num(s["beta"] - B["beta"], 2, True)}</td>'
                   f'<td class="num r{" down" if s["tech"] > cap else ""}">{pct(s["tech"], 0, False)}</td>'
                   f'<td class="num r {cls(cands[s["ticker"]]["ret"])}">{pct(cands[s["ticker"]]["ret"], 0)}</td></tr>' for s in ranked)
    return f"""
<section class="container sec" aria-labelledby="wi-h"><div class="whatif">
  <div class="panel"><div class="sec-head"><div><h2 id="wi-h">Try a change</h2><p class="sub">Replayed on the past year of daily prices in euros. A description of the past, not a forecast.</p></div></div>
    <form class="controls" aria-label="Scenario" onsubmit="return false">
      <fieldset class="chips"><legend class="lg">Change</legend>{radio("mode", "add", "Add a stock", True)}{radio("mode", "sell", "Sell a holding", False)}</fieldset>
      <fieldset class="chips" data-for="add"><legend class="lg">Stock, new money</legend>{"".join(radio("tk", t, t, t == t0) for t in adds)}</fieldset>
      <fieldset class="chips" data-for="add"><legend class="lg">Amount</legend>{"".join(radio("amt", a, eur(a), a == a0) for a in amounts)}</fieldset>
      <fieldset class="chips" data-for="sell" hidden><legend class="lg">Holding</legend>{"".join(radio("sl", s["ticker"], s["name"], i == 0) for i, s in enumerate(sells))}</fieldset>
    </form>
    <p class="visually-hidden" id="scn-say" aria-live="polite"></p><div class="out">{blocks}</div></div>
  <div class="panel flush"><div class="sec-head"><div><h2 id="rank-h">Each candidate at {eur(a0)}</h2><p class="sub">Sorted by the change in volatility, largest drop first. Red technology share is over the {pct(cap, 0, False)} cap.</p></div></div>
    <div class="table-wrap"><table class="rank" aria-labelledby="rank-h"><thead><tr><th scope="col">Stock</th><th scope="col" class="r">Correlation</th>
    <th scope="col" class="r">Bad days</th><th scope="col" class="r">Volatility change</th><th scope="col" class="r">Beta change</th><th scope="col" class="r">Technology after</th><th scope="col" class="r">Its year</th></tr></thead>
    <tbody>{rank}</tbody></table></div></div>
</div></section>"""


def glossary(B: dict, H: list) -> str:
    top = H[0]
    items = [("Volatility", "How much the value swings in a typical year.", "σ = std(daily returns) × √252", f"{pct(B['vol'], 1, False)} for this mix."),
             ("Beta", "How strongly the portfolio follows the S&P 500, both in euros.", "β = cov(portfolio, market) ÷ var(market)",
              f"{B['beta']:.2f}: a 10% market fall has come with about {B['beta'] * 10:.1f}%."),
             ("Correlation", "Whether a holding moves with the rest: 1 together, 0 unrelated, negative opposite.",
              "ρ = cov(stock, rest) ÷ (σ_stock σ_rest)", f"{top['name']} {numn(top['corr'])}."),
             ("On bad days", "The same correlation on your worst fifth of days only.", "ρ on days where portfolio return ≤ its 20th percentile",
              f"{top['name']} {num(top['down'])}."),
             ("Risk share", "How much of the portfolio's swing each holding causes. The shares add up to 100%.", "RCᵢ = wᵢ (Σw)ᵢ ÷ σ²",
              f"{top['name']} is {pct(top['weight'], 0, False)} of the money and {pct(top['risk'], 0, False)} of the risk."),
             ("Effective holdings", "How many equal-sized positions your weights are worth.", "N = 1 ÷ Σ wᵢ²", f"{B['enb']:.1f}."),
             ("Worst fall", "The deepest drop from a high point during the past year, today's weights held fixed.",
              "min (value ÷ running peak − 1)", f"{pct(B['worst'])}.")]
    rows = "".join(f'<div class="g"><dt>{a}</dt><dd><p>{esc(b)}</p><p class="fm">{c}</p><p class="ex">{esc(d)}</p></dd></div>' for a, b, c, d in items)
    return f"""<section class="container sec" aria-labelledby="gl-h"><div class="panel"><div class="sec-head"><div><h2 id="gl-h">What the numbers mean</h2>
<p class="sub">The idea, the formula, then your own number.</p></div></div><dl class="gloss">{rows}</dl></div></section>"""


def record(rec: dict | None) -> str:
    if not rec:
        return ""
    w, h, L, R, T, Bm = 900, 260, 48, 12, 12, 28
    a = [(v - 1) * 100 for v in rec["twr"]]
    b = [(v - 1) * 100 for v in rec["spy"]]
    lo, hi = min(a + b) - 3, max(a + b) + 3
    n = len(a)
    xs = scale(range(n), 0, max(n - 1, 1), L, w - R)
    o = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Time-weighted return against the S&amp;P 500 in euros">']
    for v in nice_ticks(lo, hi, 4):
        y = scale([v], lo, hi, h - Bm, T)[0]
        o.append(f'<line class="{"base" if abs(v) < 1e-9 else "grid"}" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 f'<text class="ax" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{v:.0f}%</text>')
    seen = set()
    for i, d in enumerate(rec["dates"]):
        if d[5:7] in ("01", "07") and d[:7] not in seen:
            seen.add(d[:7])
            o.append(f'<text class="ax" x="{xs[i]:.1f}" y="{h - 8}" text-anchor="middle">{MONTHS[int(d[5:7]) - 1]} {d[2:4]}</text>')
    dep = rec["deposits"]
    o += [f'<line class="dep" x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{h - Bm}" y2="{h - Bm - 8}"/>' for i in range(1, n) if dep[i] - dep[i - 1] > 1]
    o.append(f'<path class="ln ref" d="{path(xs, scale(b, lo, hi, h - Bm, T))}"/><path class="ln main" d="{path(xs, scale(a, lo, hi, h - Bm, T))}"/></svg>')
    return f"""<section class="container sec" aria-labelledby="rc-h"><div class="panel"><div class="sec-head"><div><h2 id="rc-h">Your record since {day(rec["dates"][0])}</h2>
<p class="sub">Time-weighted, so deposits do not count as gains. Ticks on the axis mark deposits.</p></div>
<p class="legend sub"><span><i class="km"></i>you {pct(rec["twr"][-1] - 1)}</span><span><i class="kf"></i>S&amp;P 500 in euros {pct(rec["spy"][-1] - 1)}</span></p></div>
<figure class="chart-fig">{"".join(o)}</figure></div></section>"""


def lede(H: list) -> str:
    if not H:
        return "No holding has a price series yet, so there is no risk split to show."
    top = H[0]
    ratio = top["risk"] / top["weight"] if top["weight"] else 1.0
    tail = ("more than its share" if ratio > 1.15 else "less than its share" if ratio < 0.85 else "about its share")
    return (f'{esc(top["name"])} carries {pct(top["risk"], 0, False)} of the risk on {pct(top["weight"], 0, False)} of the money, '
            f'{tail}. Holding as you are is a valid answer; the what-if below shows what a change would do.')


def impact_page(desk: dict) -> str:
    import copy
    imp, B = copy.deepcopy(desk["impact"]), desk["portfolio"]
    fix = lambda n: n.title() if n.isupper() else n  # Nordnet writes some names in capitals
    for x in imp["holdings"] + [s for s in imp["scenarios"] if s["kind"] == "sell"]:
        x["name"] = fix(x["name"])
    body = f"""
<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Huurre, home">Huurre</a>
<nav aria-label="Views">{nav("Impact")}</nav>{clock(desk["meta"])}</div></header>
<main><div class="container lede"><h1>Portfolio impact</h1><p>{lede(imp["holdings"])}</p></div>
{istrip(B, len(imp["holdings"]) + len(imp["unmodelled"]), imp.get("tech_max", 0.5))}{risk_section(imp["holdings"])}{forecast_section(desk.get("forecast"))}{whatif(imp, B)}{glossary(B, imp["holdings"])}{record(desk.get("record"))}
</main>
{footer(desk["meta"], f'<p>Risk window {day(imp["window"]["start"])} to {day(imp["window"]["end"])}; today’s weights held fixed. Positions without a price series and cash count as zero return.</p>')}"""
    return page("Huurre impact", "Risk of the portfolio and what adding or selling one stock would change.", "huurre",
                "P3 H3 E3 S3 R3 V2 · weakest: V, many figures; the sentence above each block says what they add up to", CSS, body, JS)
