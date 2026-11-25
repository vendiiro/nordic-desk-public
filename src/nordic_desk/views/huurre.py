"""Huurre Desk: watchlist ledger, selected stock, portfolio strip, compare, other states. Ported from the mockup."""
from __future__ import annotations

from .core import (big_usd, clock, cls, day, esc, eur, footer, line_chart, nav, page, pct, rangebar, usd)

DEFAULT_CMP = 3

PICK_SCRIPT = """
<script>
(() => {
  const pick = (t, scroll) => {
    const p = document.querySelector('[data-panel="' + t + '"]');
    if (!p) return;
    document.querySelectorAll('[data-panel]').forEach(el => { el.hidden = el !== p; });
    document.querySelectorAll('tr[data-t]').forEach(el => el.toggleAttribute('aria-current', el.dataset.t === t));
    if (scroll && matchMedia('(max-width: 75rem)').matches) p.scrollIntoView({block: 'start'});  // panel sits below the table here
  };
  const fromHash = scroll => { const m = location.hash.match(/^#([A-Z.^-]{1,10})$/); if (m) pick(m[1], scroll); };
  window.addEventListener('hashchange', () => fromHash(true)); fromHash(!!location.hash);
  const body = document.querySelector('.watch tbody'), st = {s: null, dir: -1};
  const val = (r, k) => { const x = r.dataset[k]; return k === 'name' ? x : (x === '' ? null : +x); };
  document.querySelectorAll('.watch thead [data-s]').forEach(b => b.addEventListener('click', () => {
    st.dir = st.s === b.dataset.s ? -st.dir : (b.dataset.s === 'name' ? 1 : -1); st.s = b.dataset.s;
    [...body.rows].sort((a, c) => { const x = val(a, st.s), y = val(c, st.s);
      if (x === null || y === null) return (x === null) - (y === null);
      return (x > y ? 1 : x < y ? -1 : 0) * st.dir; }).forEach(r => body.append(r));
    document.querySelectorAll('.watch thead [data-s]').forEach(h => { const th = h.closest('th'); h === b ? th.setAttribute('aria-sort', st.dir < 0 ? 'descending' : 'ascending') : th.removeAttribute('aria-sort'); });
  }));
  const svg = document.querySelector('#compare svg'), NS = 'http://www.w3.org/2000/svg';
  const label = () => {
    if (!svg) return; svg.querySelectorAll('.end').forEach(e => e.remove());
    svg.querySelectorAll('.cmp-line.s1, .cmp-line.s2, .cmp-line.s3, .cmp-line.s4, path.ref').forEach(l => {
      const pt = l.getPointAtLength(l.getTotalLength()), t = document.createElementNS(NS, 'text');
      t.setAttribute('class', 'ax end'); t.setAttribute('text-anchor', 'end'); t.setAttribute('x', pt.x); t.setAttribute('y', pt.y - 6); t.textContent = l.dataset.t || 'SPY'; svg.append(t);
    });
  };
  const boxes = [...document.querySelectorAll('input[name="cmp"]')];
  let order = boxes.filter(b => b.checked).map(b => b.value);
  const paint = () => {
    document.querySelectorAll('.cmp-line').forEach(l => {
      const k = order.indexOf(l.dataset.t);
      l.classList.remove('s1', 's2', 's3', 's4'); if (k >= 0) l.classList.add('s' + (k + 1));
    });
    document.querySelectorAll('[data-row]').forEach(r => {
      const k = order.indexOf(r.dataset.row); r.hidden = k < 0;
      r.querySelector('.sw').className = 'sw' + (k >= 0 ? ' s' + (k + 1) : '');
    });
    boxes.forEach(b => {
      const k = order.indexOf(b.value);
      b.nextElementSibling.className = 'sw' + (k >= 0 ? ' s' + (k + 1) : '');
      b.disabled = !b.checked && order.length >= 4;
    });
    label();
  };
  boxes.forEach(b => b.addEventListener('change', () => {
    order = b.checked ? [...order, b.value] : order.filter(v => v !== b.value); paint();
  }));
  paint();
})();
</script>"""

CSS = """
.strip { display: grid; grid-template-columns: repeat(5, minmax(0, auto)) minmax(0, 1fr); gap: var(--space-xl); align-items: end; padding-block: var(--space-lg); border-bottom: var(--rule-hair) solid var(--color-rule); }
.fig { display: grid; gap: 2px; }
.fig .v { font-family: var(--font-num); font-size: var(--text-2xl); font-variant-numeric: tabular-nums; line-height: 1.1; }
.fig .v.sm { font-size: var(--text-xl); }
.strip .mini { max-width: 420px; justify-self: end; width: 100%; }
.desk { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr); gap: var(--gap); padding-block: var(--space-lg); }
.panel { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); background: var(--color-paper); padding: var(--space-md); min-width: 0; }
.panel.flush { padding: 0; }
.panel.flush .sec-head { padding: var(--space-md) var(--space-md) var(--space-xs); }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-sm); }
.sec { padding-block: var(--space-lg); }
.watch th, .watch td { padding-inline: 6px; }
@media (max-width: 90rem) { .watch .wk { display: none; } }  /* shortcut: 52-week range hidden below 1440 px so the table fits; revisit with the euro-returns change */
.watch th:first-child { padding-inline-start: var(--space-md); }
.watch tbody tr { transition: background-color var(--dur-micro) var(--ease-out); }
.watch tbody tr:hover { background: var(--color-paper-2); }
.watch tbody tr[aria-current] { background: var(--color-sel); }
.pick { display: inline-flex; flex-direction: column; text-decoration: none; min-height: 44px; justify-content: center; }
.pick:hover .nm { color: var(--color-ink); text-decoration: underline; }
.nm { font-size: var(--text-sm); color: var(--color-muted); max-width: 16ch; overflow: hidden; text-overflow: ellipsis; }
.own { margin-inline-start: var(--space-xs); font-size: var(--text-xs); color: var(--color-own); border: var(--rule-hair) solid currentColor; border-radius: var(--radius-pill); padding: 0 var(--space-2xs); }
th:has(.own) { display: flex; align-items: center; }
.dive { display: grid; gap: var(--space-md); }
.dive-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--space-md); flex-wrap: wrap; }
.quote { display: flex; gap: var(--space-sm); align-items: baseline; }
.px { font-size: var(--text-2xl); }
.periods { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-block: var(--rule-hair) solid var(--color-rule); }
.periods > div { display: grid; padding: var(--space-xs) 0; }
.periods > div + div { border-inline-start: var(--rule-hair) solid var(--color-rule); padding-inline-start: var(--space-sm); }
.facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 12rem), 1fr)); gap: 0 var(--space-lg); margin: 0; }
.facts > div { display: flex; justify-content: space-between; gap: var(--space-sm); padding: var(--space-xs) 0; border-bottom: var(--rule-hair) solid var(--color-rule); }
.facts dt { color: var(--color-muted); font-size: var(--text-sm); }
.facts dd { margin: 0; text-align: end; }
.compare { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); }
.lookthrough { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); display: grid; gap: var(--space-sm); }
.lookthrough .table-wrap { max-width: 46rem; }
.lookthrough .note { max-width: 70ch; margin: 0; }
@media (max-width: 40rem) {
  .lookthrough table { font-size: var(--text-sm); }
  .lookthrough th, .lookthrough td { padding-inline: var(--space-2xs); }
  .lookthrough th { white-space: normal; }
}
.cmp-table td, .cmp-table th { text-align: end; } .cmp-table th:first-child { text-align: start; }
.ref-row { color: var(--color-muted); }
.vbox { border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md); display: grid; gap: var(--space-2xs); }
.vbox .big { font-family: var(--font-display); font-size: var(--text-xl); font-weight: var(--display-weight); }
.btn { display: inline-flex; align-items: center; min-height: 36px; padding: 0 var(--space-md); border-radius: var(--radius-pill); border: var(--rule-hair) solid transparent; background: var(--color-accent); color: var(--color-accent-ink); cursor: pointer; font-weight: 500; justify-self: start; transition: background-color var(--dur-micro) var(--ease-out); }
.btn:hover { background: var(--color-accent-deep); }
.btn:active { transform: translateY(1px); }
.btn.ghost { background: transparent; color: var(--color-ink); border-color: var(--color-rule-2); }
.btn.ghost:hover { background: var(--color-paper-3); }
@media (max-width: 75rem) { .desk { grid-template-columns: minmax(0, 1fr); } .strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .strip .mini { grid-column: 1 / -1; justify-self: stretch; max-width: none; } }
@media (max-width: 60rem) { .periods { grid-template-columns: repeat(3, minmax(0, 1fr)); } .watch .nm { display: none; } }
"""


def name_of(desk: dict, t: str) -> str:
    return (desk["detail"].get(t, {}).get("facts") or {}).get("name") or t


def watch_table(desk: dict, pick: str, verdicts: dict) -> str:
    rows = []
    for r in desk["watchlist"]:
        t = r["ticker"]
        held = '<span class="own">held</span>' if r["held"] else ""
        cur = ' aria-current="true"' if t == pick else ""
        nm = name_of(desk, t)
        v = verdicts.get(t) or {}
        ex = v.get("expected")
        tag = (f'<span class="tag {v["cls"]}" title="{esc(v["line"])}">{esc(v["verdict"])}</span>' if v.get("verdict")
               else '<span class="missing">–</span>')
        rows.append(
            f'<tr data-t="{esc(t)}"{cur} data-name="{esc(nm.lower())}" data-d1="{r["d1"]:.6f}" data-ytd="{r["ytd"]:.6f}" '
            f'data-expected="{"" if ex is None else round(ex, 6)}"><th scope="row"><a class="pick" href="#{esc(t)}"><span class="tk">{esc(t)}</span>'
            + (f'<span class="nm">{esc(nm)}</span>' if nm != t else "") + f'</a>{held}</th>'
            f'<td class="num r">{usd(r["last_usd"])}</td><td class="num r {cls(r["d1"])}">{pct(r["d1"], 2)}</td>'
            f'<td class="num r {cls(r["ytd"])}">{pct(r["ytd"])}</td>'
            f'<td>{tag}</td><td class="num r">{pct(ex, 1) if ex is not None else "–"}</td>'
            f'<td class="wk">{rangebar(r["pos"], r["lo_usd"], r["hi_usd"])}</td></tr>')
    sb = lambda k, lab: f'<button type="button" data-s="{k}">{lab}</button>'  # noqa: E731
    return ('<div class="table-wrap"><table class="watch"><thead><tr>'
            f'<th scope="col">{sb("name", "Ticker")}</th><th scope="col" class="r">Last</th>'
            f'<th scope="col" class="r">{sb("d1", "Today")}</th>'
            f'<th scope="col" class="r">{sb("ytd", "Year to date")}</th><th scope="col">Verdict</th>'
            f'<th scope="col" class="r">{sb("expected", "Expected 12 m")}</th>'
            '<th scope="col" class="wk">52-week range</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>")


def _verdict_box(t: str, v: dict | None) -> str:
    from ..analysis import analysis_href
    h = analysis_href(t)
    link = f'<a href="{esc(h)}">Open full analysis</a>' if h else ""
    if not v or not v.get("verdict"):
        return f'<p class="sub">{link}</p>' if link else ""
    ex = v.get("expected")
    return (f'<div class="vbox"><span class="pl">Entry for 6–12 months</span><span class="big {v["cls"]}">{esc(v["verdict"])}</span>'
            f'<p>{esc(v["line"])}.' + (f' Expected 12 m <span class="num">{pct(ex, 1)}</span>.' if ex is not None else "")
            + f'</p><p class="sub">{link}</p></div>')


def dive(desk: dict, r: dict, hidden: bool, v: dict | None = None) -> str:
    t = r["ticker"]
    d = desk["detail"][t]
    f = d.get("facts") or {}
    dy = f.get("dividend_yield")
    rows = [("Market cap", big_usd(f.get("market_cap"))),
            ("P/E, trailing", f"{f['pe_trailing']:.1f}" if f.get("pe_trailing") else None),
            ("P/E, forward", f"{f['pe_forward']:.1f}" if f.get("pe_forward") else None),
            ("Dividend yield", f"{dy:.2f}%" if dy else None), ("Beta vs SPY, 1 year", f"{r['beta']:.2f}"),
            ("Volatility, 21 days", pct(r["vol"], 0, False)), ("Worst fall, 1 year", pct(r["mdd"])),
            ("Earnings", day(f["earnings"]) if f.get("earnings") else None), ("Sector", f.get("sector"))]
    dl = "".join(f'<div><dt>{k}</dt><dd class="num">{esc(v) if v else "<span class=missing>not reported</span>"}</dd></div>'
                 for k, v in rows)
    held = ""
    if r["held"]:
        h = next((x for x in desk["impact"]["holdings"] if x["ticker"] == t), None)
        if h:
            held = f'<p class="note">You hold this: {pct(h["weight"], 1, False)} of the portfolio, {pct(h["risk"], 1, False)} of its risk.</p>'
    chart = line_chart([(d["close_usd"], "main"), (d["spy_scaled"], "ref")], d["dates"],
                       label=f"{t} daily close for one year, with SPY scaled to the same start", fmt=lambda v: f"${v:,.0f}")
    periods = "".join(f'<div><span class="pl">{k}</span><span class="num {cls(r[key])}">{pct(r[key])}</span></div>'
                      for k, key in (("1 week", "w1"), ("1 month", "m1"), ("3 months", "m3"), ("Year to date", "ytd"), ("1 year", "y1")))
    return f"""
<article class="dive" data-panel="{esc(t)}"{" hidden" if hidden else ""} aria-labelledby="dive-{esc(t)}">
  <header class="dive-head"><div><h3 id="dive-{esc(t)}">{esc(name_of(desk, t))}</h3>
    <p class="sub"><span class="tk">{esc(t)}</span> {esc(f.get("industry") or "")}</p></div>
    <p class="quote"><span class="px num">{usd(r["last_usd"])}</span><span class="num {cls(r["d1"])}">{pct(r["d1"], 2)}</span></p></header>
  {_verdict_box(t, v)}
  <div class="periods">{periods}</div>
  <figure class="chart-fig">{chart}<figcaption><span class="key main"></span>{esc(t)} close <span class="key ref"></span>SPY, same start</figcaption></figure>
  {held}
  <dl class="facts">{dl}</dl>
</article>"""


def compare_block(desk: dict) -> str:
    c = desk["compare"]
    tickers = list(c["series"])
    default = tickers[:DEFAULT_CMP]
    series = [(c["series"][t], "cmp-line" + (f" s{default.index(t) + 1}" if t in default else ""), t) for t in tickers]
    series.append((c["spy"], "ref"))
    chart = line_chart(series, c["dates"], w=900, h=300, base=100, label="Selected stocks rebased to 100 one year ago, with SPY")
    by = {r["ticker"]: r for r in desk["watchlist"]}
    boxes = "".join(f'<label class="chip"><input type="checkbox" name="cmp" value="{esc(t)}"{" checked" if t in default else ""}>'
                    f'<span class="sw"></span>{esc(t)}{"<span class=\"own\">held</span>" if by[t]["held"] else ""}</label>' for t in tickers)
    pe = lambda t: (lambda v: f"{v:.1f}" if v else "none")((desk["detail"][t].get("facts") or {}).get("pe_trailing"))
    rows = "".join(
        f'<tr data-row="{esc(t)}"{"" if t in default else " hidden"}><th scope="row"><span class="sw"></span>{esc(t)}</th>'
        + "".join(f'<td class="num {cls(by[t][k])}">{pct(by[t][k])}</td>' for k in ("m1", "m3", "ytd", "y1"))
        + f'<td class="num">{pct(by[t]["vol"], 0, False)}</td><td class="num">{pct(by[t]["mdd"])}</td>'
        f'<td class="num">{by[t]["beta"]:.2f}</td><td class="num">{pe(t)}</td></tr>' for t in tickers)
    sp = c.get("spy_stats")
    if sp:
        rows += ('<tr class="ref-row"><th scope="row"><span class="sw ref"></span>SPY</th>'
                 + "".join(f'<td class="num">{pct(sp[k])}</td>' for k in ("m1", "m3", "ytd", "y1"))
                 + f'<td class="num">{pct(sp["vol"], 0, False)}</td><td class="num">{pct(sp["mdd"])}</td><td class="num">1.00</td><td class="num">–</td></tr>')
    return f"""
<section class="compare" id="compare" aria-labelledby="cmp-h">
  <div class="sec-head"><h2 id="cmp-h">Compare</h2><p class="sub">Pick up to four. Lines start at 100 one year ago, in dollars; grey is SPY.</p></div>
  <fieldset class="chips"><legend class="visually-hidden">Stocks to compare</legend>{boxes}</fieldset>
  <figure class="chart-fig">{chart}</figure>
  <div class="table-wrap"><table class="cmp-table"><thead><tr><th scope="col">Ticker</th><th scope="col">1 month</th><th scope="col">3 months</th>
  <th scope="col">Year to date</th><th scope="col">1 year</th><th scope="col">Volatility, 21 days</th><th scope="col">Worst fall, 1 year</th><th scope="col">Beta vs SPY</th><th scope="col">P/E</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
</section>"""


def strip(desk: dict) -> str:
    p = desk["portfolio"]
    since = p["unrealised"] / p["cost"] if p["cost"] else 0.0
    chart = line_chart([(p["history"]["value"], "main"), (p["spy_history"], "ref")], p["history"]["dates"], w=420, h=120,
                       every=3, fmt=lambda v: f"€{v / 1000:.0f}k", label="Portfolio value over the year with the same money in SPY")
    return f"""
<section class="container strip" aria-label="Portfolio today">
  <div class="fig"><span class="pl">Portfolio</span><span class="v">{eur(p["value"])}</span></div>
  <div class="fig"><span class="pl">On cost</span><span class="v sm {cls(since)}">{pct(since)}</span></div>
  <div class="fig"><span class="pl">Volatility, 1 year</span><span class="v sm">{pct(p["vol"], 1, False)}</span></div>
  <div class="fig"><span class="pl">Beta to S&amp;P 500</span><span class="v sm">{p["beta"]:.2f}</span></div>
  <div class="fig"><span class="pl">Effective holdings</span><span class="v sm">{p["enb"]:.1f}</span></div>
  <figure class="chart-fig mini">{chart}</figure>
</section>"""


def lookthrough_block(desk: dict) -> str:
    lt = desk.get("lookthrough")
    if not lt or not lt["top"]:
        return ""
    who = lambda r: esc(r["name"]) + ("" if r["name"] == r["key"] else f' <span class="tk">{esc(r["key"])}</span>')
    rows = "".join(f'<tr><th scope="row">{who(r)}</th><td class="num r">{pct(r["share"], 1, False)}</td>'
                   f'<td class="num r">{pct(r["direct"], 1, False)}</td><td class="num r">{pct(r["via_funds"], 1, False)}</td></tr>' for r in lt["top"])
    bits = []
    if lt["not_broken_down"] >= 0.005:
        bits.append(f'{pct(lt["not_broken_down"], 0, False)} of the portfolio sits in funds outside their published top holdings and is not broken down.')
    if lt["no_data"]:
        bits.append(f'No holdings data: {esc(", ".join(lt["no_data"]))}.')
    bits.append("Fund top holdings from Yahoo Finance (up to ten per fund); weights from the Nordnet report.")
    return f"""
<section class="lookthrough" aria-labelledby="lt-h">
  <div class="sec-head"><h2 id="lt-h">Largest companies, including funds</h2><p class="sub">What you own once each fund is opened up into its largest holdings. Shares of the whole portfolio.</p></div>
  <div class="table-wrap"><table><thead><tr><th scope="col">Company</th><th scope="col" class="r">Share</th><th scope="col" class="r">Directly</th><th scope="col" class="r">Through funds</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
  <p class="note">{" ".join(bits)}</p>
</section>"""


def desk_page(desk: dict, verdicts: dict | None = None) -> str:
    verdicts = verdicts or {}
    pick = desk["watchlist"][0]["ticker"]
    dives = "".join(dive(desk, r, r["ticker"] != pick, verdicts.get(r["ticker"])) for r in desk["watchlist"])
    body = f"""
<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Huurre, home">Huurre</a>
<nav aria-label="Views">{nav("Desk")}</nav>{clock(desk["meta"])}</div></header>
<main><h1 class="visually-hidden">Stock desk</h1>
{strip(desk)}
<div class="container desk">
  <section class="panel flush" aria-labelledby="wl-h"><div class="sec-head"><h2 id="wl-h">Watchlist</h2>
  <p class="sub">{len(desk["watchlist"])} US stocks. Pick one to open it; sort by a column heading.</p></div>{watch_table(desk, pick, verdicts)}</section>
  <section class="panel" aria-label="Selected stock">{dives}</section>
</div>
<div class="container sec">{compare_block(desk)}</div>
{f'<div class="container sec">{lookthrough_block(desk)}</div>' if desk.get("lookthrough") else ""}
</main>
{footer(desk["meta"])}"""
    return page("Huurre desk", "Watchlist, selected stock, portfolio strip and compare.", "huurre",
                "P3 H3 E3 S2 R3 V3 · weakest: S, the ledger carries the screen; density first", CSS, body, PICK_SCRIPT)


COMPARE_REDIRECT = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Compare moved to Desk</title>
<meta http-equiv="refresh" content="0; url=desk.html#compare"></head>
<body><p>Compare is now part of the <a href="desk.html#compare">Desk</a>.</p></body></html>"""
