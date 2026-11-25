"""Aamu: the morning report, phone first. Last night in New York, in euros. Ported from the mockup."""
from __future__ import annotations

from .core import cls, day, esc, eur, footer, helsinki, nav, page, path, pct, scale, usd
from .huurre import name_of

CSS = """
.bar { background: var(--color-paper); }
.mast { padding-block: var(--space-xl) var(--space-lg); border-bottom: 2px solid var(--color-ink); }
.mast .container { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-lg); align-items: end; }
.mast h1 { font-size: clamp(2.5rem, 7vw, 5.5rem); text-transform: uppercase; line-height: 1; font-weight: 800; }
.mast .date { text-align: end; font-size: var(--text-lg); }
.lead { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--space-xl); padding-block: var(--space-xl); border-bottom: var(--rule-hair) solid var(--color-rule); }
.figure { font-family: var(--font-display); font-weight: 800; font-size: clamp(3rem, 8vw, 7rem); line-height: 0.95; font-variant-numeric: tabular-nums; }
.sentence { font-size: var(--text-xl); line-height: 1.35; max-width: 34ch; margin-top: var(--space-md); }
.meta { display: flex; gap: var(--space-xl); margin-top: var(--space-lg); flex-wrap: wrap; }
.meta > div { display: grid; }
.movers { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-lg); align-content: start; }
.movers h2 { font-size: var(--text-lg); text-transform: uppercase; border-bottom: 2px solid var(--color-ink); padding-bottom: var(--space-2xs); margin-bottom: var(--space-xs); }
.movers ol { list-style: none; margin: 0; padding: 0; }
.mv { display: grid; grid-template-columns: auto 1fr; column-gap: var(--space-sm); padding: var(--space-xs) 0; border-bottom: var(--rule-hair) solid var(--color-rule); text-decoration: none; min-height: 44px; }
.mv:hover .tk { color: var(--color-accent); }
.mvp { font-family: var(--font-display); font-weight: 700; font-size: var(--text-2xl); text-align: end; line-height: 1; }
.mv .nm { grid-column: 1 / -1; font-size: var(--text-sm); color: var(--color-muted); }
.sec { padding-block: var(--space-xl); border-bottom: var(--rule-hair) solid var(--color-rule); }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-md); }
.sec-head h2 { font-size: var(--text-2xl); text-transform: uppercase; }
.tiles { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); border-top: 2px solid var(--color-ink); }
.tile { display: grid; gap: var(--space-xs); padding: var(--space-sm) var(--space-sm) var(--space-md); text-decoration: none; border-bottom: var(--rule-hair) solid var(--color-rule); transition: background-color var(--dur-micro) var(--ease-out); }
.tile:hover { background: var(--color-paper-2); }
.th { display: flex; justify-content: space-between; align-items: baseline; }
.th .tk { font-family: var(--font-display); font-weight: 700; font-size: var(--text-xl); }
.mini-chart { width: 100%; height: auto; }
.mini-chart .base { stroke: var(--color-rule); stroke-width: 1; }
.mini-chart .ln { fill: none; stroke-width: 1.75; stroke: var(--color-accent); }
.mini-chart .ln.down { stroke: var(--color-down); }
.tp { font-size: var(--text-sm); color: var(--color-muted); }
.clear { margin-top: var(--space-lg); padding: var(--space-sm) var(--space-md); border: 2px solid var(--color-ink); }
.own { font-size: var(--text-xs); color: var(--color-accent); border: var(--rule-hair) solid currentColor; padding: 0 var(--space-2xs); }
.alerts { border: 2px solid var(--color-ink); padding: var(--space-md); margin-top: var(--space-lg); }
.alerts h2 { font-size: var(--text-lg); text-transform: uppercase; }
.alerts ul { margin: var(--space-xs) 0 0; padding-inline-start: var(--space-lg); }
@media (max-width: 75rem) { .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); } .lead { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 40rem) { .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } .movers { grid-template-columns: minmax(0, 1fr); } .mast .container { grid-template-columns: minmax(0, 1fr); } .mast .date { text-align: start; } }
"""


def sentence(p: dict, spy: float) -> str:
    verdict = "so you finished ahead." if p["overnight_pct"] > spy else "so you finished behind the market."
    return f"Overnight your holdings moved {pct(p['overnight_pct'], 2)} and SPY moved {pct(spy, 2)}, {verdict}"


def aamu_page(aamu: dict, desk: dict, alerts: list | None = None) -> str:
    from .cards import alert_banner

    p, meta = aamu["portfolio"], aamu["meta"]
    from datetime import datetime
    from zoneinfo import ZoneInfo
    built = datetime.fromisoformat(meta["built"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Helsinki")).date()
    movers = lambda rows: "".join(
        f'<li><a href="desk.html#{esc(r["ticker"])}" class="mv"><span class="tk">{esc(r["ticker"])}</span>'
        f'<span class="mvp num {cls(r["d1"])}">{pct(r["d1"], 1)}</span>'
        + (f'<span class="nm">{esc(name_of(desk, r["ticker"]))}</span>' if name_of(desk, r["ticker"]) != r["ticker"] else "") + '</a></li>'
        for r in rows) or '<li class="nm">None tonight.</li>'
    held = {r["ticker"] for r in desk["watchlist"] if r["held"]}
    tiles = sorted(aamu["tiles"], key=lambda t: t["ticker"] not in held)  # your holdings first
    lo = min(min(t["rebased"]) for t in aamu["tiles"])
    hi = max(max(t["rebased"]) for t in aamu["tiles"])

    def tile(t):
        v = t["rebased"]
        xs = scale(range(len(v)), 0, len(v) - 1, 0, 200)
        y100 = scale([100], lo, hi, 78, 2)[0]
        return (f'<li><a class="tile" href="desk.html#{esc(t["ticker"])}"><span class="th"><span class="tk">{esc(t["ticker"])}</span>'
                + ('<span class="own">held</span>' if t["ticker"] in held else "") + f'<span class="num {cls(t["y1"])}">{pct(t["y1"], 0)}</span></span>'
                f'<svg class="mini-chart" viewBox="0 0 200 80" aria-hidden="true"><line class="base" x1="0" x2="200" y1="{y100:.1f}" y2="{y100:.1f}"/>'
                f'<path class="ln {cls(t["y1"])}" d="{path(xs, scale(v, lo, hi, 78, 2))}"/></svg>'
                f'<span class="num tp">{usd(t["last_usd"])}</span></a></li>')

    body = f"""
<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Aamu, home">AAMU</a>
<nav aria-label="Views">{nav("Aamu")}</nav></div></header>
<main>
<div class="mast"><div class="container"><h1>Last night in New York</h1>
  <p class="date">{built:%A} {day(built.isoformat())}<br><span class="note">US close {day(meta["close"], False)}, {helsinki(meta["close"], 16, 0)} Helsinki</span></p></div></div>
{alert_banner(alerts, "cards.html#") if alerts else '<div class="container"><p class="clear">No thresholds crossed since the last run.</p></div>'}<div class="container lead">
  <div><p class="pl">Portfolio, in euros</p><p class="figure">{eur(p["value"])}</p>
    <p class="sentence">{esc(sentence(p, aamu["spy_overnight"]))}</p>
    <div class="meta"><div><span class="pl">Overnight</span><span class="num {cls(p["overnight"])}">{eur(p["overnight"], 0, True)}</span></div>
      <div><span class="pl">On cost</span><span class="num {cls(p["since_cost_pct"])}">{pct(p["since_cost_pct"])}</span></div>
      <div><span class="pl">Of which currency, overnight</span><span class="num {cls(p["fx_effect_1d"])}">{eur(p["fx_effect_1d"], 0, True)}</span></div></div></div>
  <div class="movers"><div><h2>Up most</h2><ol>{movers(aamu["movers"]["up"])}</ol></div><div><h2>Down most</h2><ol>{movers(aamu["movers"]["down"])}</ol></div></div>
</div>
<section class="container sec" aria-labelledby="wl-h"><div class="sec-head"><h2 id="wl-h">The watchlist, one year</h2>
  <p class="sub">Every chart on one scale, rebased to 100. The rule marks the start.</p></div>
  <ul class="tiles">{"".join(tile(t) for t in tiles)}</ul></section>
</main>
{footer(meta)}"""
    return page("Aamu", "Morning report of last night's US session, in euros.", "aamu",
                "P3 H3 E3 S3 R3 V2 · weakest: V, a report reads slower than a desk; the desk is one tap away", CSS, body)
