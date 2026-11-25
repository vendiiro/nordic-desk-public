"""Goal page: where the portfolio could be in 1-10 years, the chance of a goal, the saving it takes, and how far to trust it.
Static HTML and SVG from out/goal.json (goalrange.build_goal); the browser computes nothing."""
from __future__ import annotations

from .core import MONTHS, clock, esc, eur, footer, nav, nice_ticks, page, pct, scale
from .huurre import CSS as DESK_CSS

CSS = DESK_CSS + """
.goal { display: grid; gap: var(--space-xl); padding-block: var(--space-lg) var(--space-2xl); }
.goal p { max-width: 70ch; }
.g-head { display: grid; gap: var(--space-xs); }
.g-head .eyebrow { font-size: var(--text-sm); color: var(--color-muted); }
.g-head h1 { font-size: var(--text-2xl); max-width: 44ch; line-height: 1.2; }
.g-main { display: grid; grid-template-columns: minmax(0, 8fr) minmax(0, 4fr); gap: var(--gap); align-items: start; }
.g-side { display: grid; gap: var(--space-md); }
.g-box { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); display: grid; gap: var(--space-xs); }
.g-box h2 { font-size: var(--text-md); }
.g-box .big { font-family: var(--font-num); font-size: var(--text-2xl); line-height: 1.1; }
.g-box dl { margin: 0; display: grid; grid-template-columns: 1fr auto; gap: var(--space-2xs) var(--space-md); font-size: var(--text-sm); }
.g-box dt { color: var(--color-ink-2); } .g-box dd { margin: 0; font-family: var(--font-num); text-align: end; }
.g-box .note, .g-fine { font-size: var(--text-sm); color: var(--color-muted); }
.fan { width: 100%; height: auto; overflow: visible; }
.fan .grid { stroke: var(--color-rule); } .fan .ax { fill: var(--color-muted); font: 11px var(--font-num); }
.fan .band.outer { fill: color-mix(in oklab, var(--color-accent) 12%, transparent); }
.fan .band.inner { fill: color-mix(in oklab, var(--color-accent) 26%, transparent); }
.fan .med { fill: none; stroke: var(--color-accent-deep); stroke-width: 2.5; stroke-linejoin: round; }
.fan .paid { fill: none; stroke: var(--color-muted); stroke-width: 1.5; stroke-dasharray: 4 4; }
.fan .target line { stroke: var(--color-own); stroke-width: 2; } .fan .target text { fill: var(--color-own); font: 600 12px var(--font-body); paint-order: stroke; stroke: var(--color-paper); stroke-width: 4px; stroke-linejoin: round; }
.keys { display: flex; flex-wrap: wrap; gap: var(--space-xs) var(--space-md); font-size: var(--text-sm); color: var(--color-ink-2); margin: var(--space-xs) 0 0; padding: 0; list-style: none; }
.keys span { display: inline-block; width: 14px; height: 10px; margin-inline-end: var(--space-2xs); vertical-align: -1px; border-radius: 2px; }
.k-outer { background: color-mix(in oklab, var(--color-accent) 12%, transparent); } .k-inner { background: color-mix(in oklab, var(--color-accent) 26%, transparent); }
.k-med { background: var(--color-accent-deep); height: 3px !important; vertical-align: 3px !important; }
.k-paid { border-top: 2px dashed var(--color-muted); height: 0 !important; border-radius: 0 !important; vertical-align: 4px !important; }
.k-target { background: var(--color-own); height: 3px !important; vertical-align: 3px !important; }
.g-sec { border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-lg); display: grid; gap: var(--space-md); }
.g-sec h2 { font-size: var(--text-xl); }
.checks { display: grid; gap: var(--space-2xs); font-size: var(--text-sm); color: var(--color-ink-2); margin: 0; max-width: 80ch; }
.checks dt { font-weight: 600; color: var(--color-ink); } .checks dd { margin: 0 0 var(--space-sm); }
.fan.small { display: none; }
@media (max-width: 40rem) { .fan.big { display: none; } .fan.small { display: block; } .goal .q { display: none; } }
@media (max-width: 60rem) { .g-main { grid-template-columns: minmax(0, 1fr); } .g-head h1 { font-size: var(--text-xl); } }
"""

LONG_NOTE = ("Past 5 years, treat the range as a sketch: the stored history holds only about two non-overlapping 5-year spans, "
             "so the long end leans on how the blocks are stitched together.")


def approx(x: float) -> str:
    """Euros rounded so they do not look more precise than a simulation: hundreds below 100k, thousands above."""
    step = 100 if abs(x) < 100_000 else 1000
    return eur(round(x / step) * step).replace("\u2009", "\u202f")  # narrow no-break space: €11 500 never splits a line


def _month(iso: str) -> str:
    return f"{MONTHS[int(iso[5:7]) - 1]} {iso[:4]}"


def _paths10(p: float) -> str:
    n = round(p * 10)
    return "fewer than 1" if n == 0 and p > 0 else "almost all 10" if n == 10 and p < 1 else str(n)


def _money(g: dict) -> str:
    m, lump = g["monthly"], g["lump"]
    s = f"{eur(m)} a month" if m else "no new money"
    return s + (f" and {eur(lump)} now" if lump else "")


def headline(g: dict) -> str:
    goal = g.get("goal")
    if goal and goal.get("prob") is not None:
        y = g["years"][goal["years_ahead"] - 1]
        return (f"With today’s portfolio and {_money(g)}, the middle path reaches about {approx(y['p50'])} by {_month(y['date'])}; "
                f"the goal of {approx(goal['target'])} is reached in about {_paths10(goal['prob'])} of 10 simulated paths.")
    y = g["years"][-1]
    return (f"With today’s portfolio and {_money(g)}, the middle path reaches about {approx(y['p50'])} by {_month(y['date'])}; "
            f"9 in 10 simulated paths end between {approx(y['p5'])} and {approx(y['p95'])}.")


def summary_line(g: dict) -> str | None:
    """One line for the Today page."""
    if not g or not g.get("available"):
        return None
    goal = g.get("goal")
    if goal and goal.get("prob") is not None:
        return f"Goal of {eur(goal['target'])} by {goal['year']}: reached in about {_paths10(goal['prob'])} of 10 simulated paths."
    y = g["years"][-1]
    return f"In {y['year']} years the middle path is about {approx(y['p50'])} ({_month(y['date'])})."


def _k(v: float) -> str:
    return eur(v / 1000, 0 if v % 1000 == 0 else 1) + "k" if abs(v) >= 1000 else eur(v)


def fan(g: dict, w: int = 760, h: int = 340, cls: str = "fan") -> str:
    L, R, T, B = 60, 16, 16, 30
    ys = g["years"]
    xs = [0] + [y["year"] for y in ys]
    v0 = g["start_value"]
    col = lambda k: [v0] + [y[k] for y in ys]  # noqa: E731
    target = (g.get("goal") or {}).get("target") if (g.get("goal") or {}).get("prob") is not None else None
    hi = max(col("p95") + ([target] if target else []))
    lo = 0.0
    X = lambda i: scale([i], 0, xs[-1], L, w - R)[0]  # noqa: E731
    Y = lambda v: scale([v], lo, hi * 1.04, h - B, T)[0]  # noqa: E731
    area = lambda a, b: ("M" + " L".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in zip(xs, col(a)))  # noqa: E731
                         + " L" + " L".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in zip(xs[::-1], col(b)[::-1])) + " Z")
    line = lambda vals: "M" + " L".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in zip(xs, vals))  # noqa: E731
    out = [f'<svg class="{cls}" viewBox="0 0 {w} {h}" role="img" aria-label="Range of portfolio value by year, in euros: '
           f'5 to 95 and 25 to 75 percent bands, middle path and money paid in. The table below holds the same numbers.">']
    for v in nice_ticks(lo, hi * 1.04, 5):
        out.append(f'<line class="grid" x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                   f'<text class="ax" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{esc(_k(v))}</text>')
    step = 1 if xs[-1] * 110 <= w else 2 if xs[-1] * 40 <= w else 5
    ticks = list(xs[::step])
    if ticks[-1] != xs[-1]:  # always label the last year; drop a neighbour that would crowd it
        ticks[-1:] = [xs[-1]] if xs[-1] - ticks[-1] < step and len(ticks) > 1 else [ticks[-1], xs[-1]]
    for x in ticks:
        lab = "Now" if x == 0 else ys[x - 1]["date"][:4]
        out.append(f'<text class="ax" x="{X(x):.1f}" y="{h - 8}" text-anchor="middle">{lab}</text>')
    out.append(f'<path class="band outer" d="{area("p95", "p5")}"/><path class="band inner" d="{area("p75", "p25")}"/>')
    out.append(f'<path class="paid" d="{line([v0] + g["contributions"])}"/><path class="med" d="{line(col("p50"))}"/>')
    if target:
        x = X(g["goal"]["years_ahead"])
        out.append(f'<g class="target"><line x1="{x - 14:.1f}" x2="{x + 14:.1f}" y1="{Y(target):.1f}" y2="{Y(target):.1f}"/>'
                   f'<text x="{x - 18 if x - L > 120 else x + 18:.1f}" y="{Y(target) - 8:.1f}" text-anchor="{"end" if x - L > 120 else "start"}">Goal {esc(_k(target))}</text></g>')
    out.append("</svg>")
    return "".join(out)


def _table(g: dict) -> str:
    rows = "".join(f'<tr><th scope="row">{_month(y["date"])}</th><td class="num r">{eur(c)}</td><td class="num r">{approx(y["p5"])}</td>'
                   f'<td class="num r q">{approx(y["p25"])}</td><td class="num r"><b>{approx(y["p50"])}</b></td>'
                   f'<td class="num r q">{approx(y["p75"])}</td><td class="num r">{approx(y["p95"])}</td></tr>'
                   for y, c in zip(g["years"], g["contributions"]))
    return ('<div class="table-wrap"><table><caption class="visually-hidden">Value by year, in euros</caption><thead><tr>'
            '<th scope="col">Year end</th><th scope="col" class="r">Paid in</th><th scope="col" class="r">5%</th><th scope="col" class="r q">25%</th>'
            '<th scope="col" class="r">Middle</th><th scope="col" class="r q">75%</th><th scope="col" class="r">95%</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def _goal_box(g: dict) -> str:
    goal = g.get("goal")
    if not goal:
        how = ("Add <code>target_eur</code> and <code>target_year</code> to <code>config/goals.local.toml</code> to see the chance of a goal."
               if g["goals_file"] else
               "No goal set. Copy <code>config/goals.example.toml</code> to <code>config/goals.local.toml</code> and put in a target, "
               "a monthly saving and a drawdown limit. Until then the range assumes no new money.")
        return f'<section class="g-box" aria-labelledby="gb-h"><h2 id="gb-h">Goal</h2><p class="note">{how}</p></section>'
    if goal["prob"] is None:
        return (f'<section class="g-box" aria-labelledby="gb-h"><h2 id="gb-h">Goal: {eur(goal["target"])} by {goal["year"]}</h2>'
                f'<p class="note">{esc(goal["note"])}</p></section>')
    d, s = g["drift"], g["sensitivity"]
    return (f'<section class="g-box" aria-labelledby="gb-h"><h2 id="gb-h">Goal: {eur(goal["target"])} by {goal["year"]}</h2>'
            f'<p class="big">{pct(goal["prob"], 0, False)}</p><p class="note">of simulated paths reach it with {_money(g)}.</p>'
            f'<dl><dt>If the yearly return is {pct(d - s, 0, False)}</dt><dd>{pct(goal["prob_low"], 0, False)}</dd>'
            f'<dt>If it is {pct(d + s, 0, False)}</dt><dd>{pct(goal["prob_high"], 0, False)}</dd>'
            f'<dt>Monthly saving for an even chance</dt><dd>{eur(goal["monthly_50"])}</dd>'
            f'<dt>For a three-in-four chance</dt><dd>{eur(goal["monthly_75"])}</dd></dl></section>')


def _dd_box(g: dict) -> str:
    d = g["drawdown"]
    lim = (f'<p class="big">{pct(d["prob_exceed"], 0, False)}</p><p class="note">of paths fall more than {pct(d["limit"], 0, False)} '
           f'from a peak at some point in {g["horizon_years"]} years.</p>') if d["limit"] else \
          '<p class="note">Add <code>max_drawdown</code> to the goals file to see the chance of a larger fall.</p>'
    return (f'<section class="g-box" aria-labelledby="dd-h"><h2 id="dd-h">Falls along the way</h2>{lim}'
            f'<dl><dt>Typical largest fall</dt><dd>{pct(d["p50"], 0, False)}</dd><dt>Largest fall, 1 path in 20</dt><dd>{pct(d["p95"], 0, False)}</dd></dl>'
            '<p class="note">Measured on the invested money, so new savings do not hide a fall.</p></section>')


def _checks(g: dict) -> str:
    anc = g.get("anchor")
    drift = (f'<dt>Yearly return assumed</dt><dd><span class="num">{pct(g["drift"], 1, False)}</span> in euros, set in <code>config/analysis.toml</code>. '
             'The paths keep the history’s ups and downs, its fat tails and calm and rough spells, but not its average: '
             + (f'SPY returned <span class="num">{pct(anc["rate"], 1, False)}</span> a year in euros {esc(anc["from"])}–{esc(anc["to"])}, '
                'a strong decade that would flatter every path. ' if anc else "")
             + 'The goal box shows how much the answer moves with 2 points less or more.</dd>')
    hist = (f'<dt>History</dt><dd>{esc(g["history_start"])} to {esc(g["history_end"])} ({g["history_years"]:.1f} years), today’s positions with '
            f'today’s weights, drawn in {g["block"]}-day blocks, {g["n_paths"]} paths. Cash and the left-out test positions earn 0%. '
            'Only stocks held today are in it, so firms that failed are missing.</dd>')
    bt = g.get("backtest")
    btl = ("<dt>Back-test of the one-year range</dt>"
           + (f'<dd>At {bt["n"]} month starts from {esc(bt["start"])}, using only earlier days: the year that followed fell inside the 5–95% band '
              f'<span class="num">{pct(bt["inside_90"], 0, False)}</span> of the time (aim 90%, Kupiec p {bt["p_90"]:.3f}) and inside the 25–75% band '
              f'<span class="num">{pct(bt["inside_50"], 0, False)}</span> (aim 50%, p {bt["p_50"]:.3f}). Neighbouring checks share most of their year, '
              f'so this is closer to {bt["n_independent"]} independent years than {bt["n"]}.</dd>'
              if bt else "<dd>Needs four years of common history; not enough yet.</dd>"))
    led = g.get("ledger") or {}
    kinds = {"goal_1y": "one-year ranges (5–95%)", "risk_21d": "next-month ranges (95%)"}
    held = "; ".join(f'{k["held"]} of {k["matured"]} {kinds.get(n, n.replace("goal_", "").replace("y", "-year") + " ranges (5–95%)")}'
                     for n, k in sorted((led.get("by_kind") or {}).items()))
    ledl = "<dt>Own record</dt>" + (
        f'<dd>Ranges the desk has shown that held: {held} ({led["pending"]} still running).</dd>' if led.get("show")
        else f'<dd>Every range shown is written down and scored when its time is up. {led.get("matured", 0)} matured so far, '
             f'{led.get("pending", 0)} running; the record shows from 5.</dd>')
    return f'<dl class="checks">{drift}{hist}{btl}{ledl}</dl>'


def goal_page(g: dict, meta: dict) -> str:
    top = (f'<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Nordic Desk, home">Nordic Desk</a>'
           f'<nav aria-label="Views">{nav("Goal")}</nav>{clock(meta)}</div></header>')
    if not g.get("available"):
        body = f'{top}<main class="container goal"><div class="g-head"><h1>Goal</h1><p>{esc(g.get("why", "No data yet."))}</p></div></main>{footer(meta)}'
        return page("Goal", "Where the portfolio could be in 1-10 years.", "huurre", "P3 H3 E3 S3 R3 V3", CSS, body)
    long = f'<p class="g-fine">{LONG_NOTE}</p>' if g["horizon_years"] > 5 else ""
    excl = f' Left out as cash: {esc(", ".join(g["excluded"]))}.' if g["excluded"] else ""
    body = f"""{top}
<main class="container goal">
<div class="g-head"><p class="eyebrow">Goal · {g["horizon_years"]} years · prices to {esc(g["close"])}</p><h1>{esc(headline(g))}</h1>
<p class="sub">A range, not a forecast: {g["n_paths"]} paths built from the portfolio’s own past days, re-centred on an assumed
{pct(g["drift"], 1, False)} a year. Half the paths end above the middle line, half below.{excl}</p></div>
<div class="g-main">
<figure class="chart-fig" style="margin:0">{fan(g, cls="fan big")}{fan(g, 360, 300, "fan small")}
<ul class="keys" aria-hidden="true"><li><span class="k-outer"></span>9 in 10 paths</li><li><span class="k-inner"></span>Middle half</li>
<li><span class="k-med"></span>Middle path</li><li><span class="k-paid"></span>Money paid in</li>{'<li><span class="k-target"></span>Goal</li>' if (g.get("goal") or {}).get("prob") is not None else ""}</ul>
{long}</figure>
<div class="g-side">{_goal_box(g)}{_dd_box(g)}</div>
</div>
<section class="g-sec" aria-labelledby="t-h"><h2 id="t-h">Value by year</h2>{_table(g)}</section>
<section class="g-sec" aria-labelledby="m-h"><h2 id="m-h">How far to trust it</h2>{_checks(g)}
<p class="g-fine">No taxes, inflation or fees beyond what total-return prices include. New money is split like today’s portfolio;
what to buy with it is a separate question.</p></section>
</main>
{footer(meta)}"""
    return page("Goal", "Where the portfolio could be in 1-10 years, the chance of a goal and the saving it takes.", "huurre",
                "P3 H3 E3 S3 R3 V3 · weakest: E, a range is harder to read than a number", CSS, body)
