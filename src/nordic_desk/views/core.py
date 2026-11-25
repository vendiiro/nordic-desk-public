"""Shared pieces of the views: tokens per look, base CSS, number formats, SVG charts, the page shell.

Ported from docs/mockups/src/gen.py. Every colour and face goes through a token (Hallmark floor).
"""
from __future__ import annotations

import html as _html
import math

MINUS = chr(0x2212)
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

TOKENS = {
    "huurre": """
  color-scheme: light;
  --color-paper: oklch(98.5% 0.004 240); --color-paper-2: oklch(96.5% 0.006 240); --color-paper-3: oklch(92.5% 0.009 240);
  --color-ink: oklch(21% 0.012 250); --color-ink-2: oklch(36% 0.012 250); --color-muted: oklch(50% 0.014 250);
  --color-rule: oklch(90% 0.008 240); --color-rule-2: oklch(80% 0.01 240);
  --color-accent: oklch(46% 0.13 250); --color-accent-deep: oklch(38% 0.12 250); --color-accent-ink: oklch(98.5% 0.004 240);
  --color-focus: oklch(55% 0.16 250); --color-sel: oklch(94.5% 0.025 250); --color-own: oklch(52% 0.13 70);
  --color-up: oklch(50% 0.12 165); --color-down: oklch(52% 0.17 25); --color-line: oklch(30% 0.03 250);
  --color-s1: oklch(42% 0.14 250); --color-s2: oklch(56% 0.13 70); --color-s3: oklch(55% 0.11 165); --color-s4: oklch(62% 0.13 320);
  --color-s5: oklch(70% 0.06 250); --color-s6: oklch(82% 0.04 250);
  --font-display: "Host Grotesk", ui-sans-serif, system-ui, sans-serif; --font-body: var(--font-display);
  --font-num: "Atkinson Hyperlegible Mono", ui-monospace, monospace;
  --radius-card: 8px; --radius-pill: 6px; --rule-hair: 1px; --tracking-display: -0.02em; --display-weight: 500;""",
    "aamu": """
  color-scheme: light;
  --color-paper: oklch(98.5% 0.005 260); --color-paper-2: oklch(95.5% 0.008 260); --color-paper-3: oklch(91% 0.01 260);
  --color-ink: oklch(16% 0.012 260); --color-ink-2: oklch(30% 0.014 260); --color-muted: oklch(46% 0.016 260);
  --color-rule: oklch(88% 0.01 260); --color-rule-2: oklch(72% 0.014 260);
  --color-accent: oklch(42% 0.19 262); --color-accent-deep: oklch(34% 0.16 262); --color-accent-ink: oklch(98.5% 0.004 260);
  --color-focus: oklch(58% 0.22 28); --color-sel: oklch(93% 0.03 262); --color-own: oklch(42% 0.19 262);
  --color-up: oklch(47% 0.12 160); --color-down: oklch(52% 0.19 27); --color-line: oklch(42% 0.19 262);
  --color-s1: oklch(42% 0.19 262); --color-s2: oklch(58% 0.15 262); --color-s3: oklch(72% 0.1 262); --color-s4: oklch(27% 0.1 262);
  --color-s5: oklch(80% 0.06 262); --color-s6: oklch(88% 0.03 262);
  --font-display: "Barlow Condensed", ui-sans-serif, sans-serif; --font-body: "Barlow", ui-sans-serif, sans-serif;
  --font-num: "Barlow", ui-sans-serif, sans-serif;
  --radius-card: 0; --radius-pill: 0; --rule-hair: 1px; --tracking-display: -0.005em; --display-weight: 700;""",
}
FONTS = {
    "huurre": "family=Host+Grotesk:wght@400;500;600&family=Atkinson+Hyperlegible+Mono:wght@400;600",
    "aamu": "family=Barlow+Condensed:wght@700;800&family=Barlow:wght@400;500;600",
}
STAMPS = {
    "huurre": "/* Hallmark · shape: app screen · genre: modern-minimal · theme: Console, paper colourway cooled to hoarfrost (Huurre) · v2.0.0 */",
    "aamu": "/* Hallmark · shape: app screen · genre: modern-minimal · theme: Piste snow with Finnish blue (Aamu) · v2.0.0 */",
}

SCALE = """
  --space-2xs: 4px; --space-xs: 8px; --space-sm: 12px; --space-md: 16px; --space-lg: 24px; --space-xl: 40px; --space-2xl: 64px;
  --text-xs: 0.8125rem; --text-sm: 0.875rem; --text-md: 1rem; --text-lg: 1.2rem; --text-xl: 1.44rem; --text-2xl: 1.728rem; --text-3xl: 2.488rem;
  --dur-micro: 120ms; --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --container: 1440px; --gutter: 40px; --gap: 24px;"""

BASE = """
*, *::before, *::after { box-sizing: border-box; }
html, body { overflow-x: clip; }
html { scrollbar-color: var(--color-rule-2) var(--color-paper); }
body { margin: 0; background: var(--color-paper); color: var(--color-ink); font-family: var(--font-body); font-size: var(--text-md); line-height: 1.5; caret-color: var(--color-accent); -webkit-font-smoothing: antialiased; }
::selection { background: color-mix(in oklab, var(--color-accent) 30%, transparent); }
:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
a { color: inherit; text-underline-offset: 0.16em; text-decoration-thickness: 1px; }
h1, h2, h3 { margin: 0; font-family: var(--font-display); font-weight: var(--display-weight); letter-spacing: var(--tracking-display); line-height: 1.1; overflow-wrap: break-word; min-width: 0; text-wrap: balance; }
h2 { font-size: var(--text-lg); } h3 { font-size: var(--text-xl); }
p { margin: 0; }
[hidden] { display: none !important; }
button, input { font: inherit; color: inherit; }
svg { display: block; }
.container { width: 100%; max-width: var(--container); margin-inline: auto; padding-inline: var(--gutter); }
.num { font-family: var(--font-num); font-variant-numeric: tabular-nums; }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.up { color: var(--color-up); } .down { color: var(--color-down); } .flat { color: var(--color-muted); }
.sub, .pl, figcaption, .note { color: var(--color-muted); font-size: var(--text-sm); }
.missing { color: var(--color-muted); }
.tk { font-family: var(--font-num); font-weight: 600; }
.bar { border-bottom: var(--rule-hair) solid var(--color-rule); background: var(--color-paper-2); }
.bar .container { display: flex; align-items: center; gap: var(--space-lg); min-height: 60px; flex-wrap: wrap; }
.mark { font-family: var(--font-display); font-weight: var(--display-weight); font-size: var(--text-lg); text-decoration: none; color: var(--color-accent); }
.bar nav { display: flex; gap: var(--space-2xs); flex-wrap: wrap; }
.bar nav a { padding: var(--space-2xs) var(--space-sm); border-radius: var(--radius-pill); text-decoration: none; color: var(--color-ink-2); min-height: 36px; display: inline-flex; align-items: center; transition: background-color var(--dur-micro) var(--ease-out); }
.bar nav a:hover, .bar nav a[aria-current] { background: var(--color-paper-3); color: var(--color-ink); }
.clock { margin-inline-start: auto; display: flex; gap: var(--space-lg); font-size: var(--text-sm); color: var(--color-muted); flex-wrap: wrap; }
.clock b { color: var(--color-ink); font-weight: 500; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: var(--space-xs) var(--space-sm); text-align: start; border-bottom: var(--rule-hair) solid var(--color-rule); white-space: nowrap; vertical-align: middle; }
thead th { font-weight: 500; font-size: var(--text-sm); color: var(--color-muted); }
.r { text-align: end; }
tbody th { font-weight: 400; }
.spark path { fill: none; stroke-width: 1.5; stroke: var(--color-muted); }
.spark.up path { stroke: var(--color-up); } .spark.down path { stroke: var(--color-down); }
.chart { width: 100%; height: auto; overflow: visible; }
.chart .grid { stroke: var(--color-rule); stroke-width: 1; }
.chart .base { stroke: var(--color-rule-2); stroke-width: 1; }
.chart .ax { fill: var(--color-muted); font-family: var(--font-num); font-size: 11px; }
.chart .ln { fill: none; stroke-width: 2; stroke-linejoin: round; }
.chart .main { stroke: var(--color-line); }
.chart .ref { stroke: var(--color-muted); stroke-width: 1.5; }
.chart .dep { stroke: var(--color-own); stroke-width: 2; }
.cmp-line { stroke: transparent; }
.s1 { --c: var(--color-s1); } .s2 { --c: var(--color-s2); } .s3 { --c: var(--color-s3); } .s4 { --c: var(--color-s4); } .s5 { --c: var(--color-s5); } .s6 { --c: var(--color-s6); }
.cmp-line.s1, .cmp-line.s2, .cmp-line.s3, .cmp-line.s4 { stroke: var(--c); }
.chart-fig { margin: 0; }
figcaption { display: flex; gap: var(--space-md); align-items: center; margin-top: var(--space-xs); flex-wrap: wrap; }
.key { display: inline-block; width: 14px; height: 2px; }
.key.main { background: var(--color-line); } .key.ref { background: var(--color-muted); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: var(--c, var(--color-rule-2)); margin-inline-end: var(--space-xs); }
.sw.ref { background: var(--color-muted); }
.range { position: relative; display: block; width: 88px; height: 14px; }
.range::before { content: ""; position: absolute; inset: 6px 0 auto; height: 2px; background: var(--color-rule-2); }
.range-mark { position: absolute; top: 1px; left: calc(var(--pos) * 100% - 1.5px); width: 3px; height: 12px; background: var(--color-ink); }
.chips { border: 0; padding: 0; margin: 0 0 var(--space-md); display: flex; flex-wrap: wrap; gap: var(--space-xs); }
.chip { display: inline-flex; align-items: center; min-height: 36px; padding: 0 var(--space-sm); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); cursor: pointer; font-size: var(--text-sm); background: var(--color-paper); transition: border-color var(--dur-micro) var(--ease-out), background-color var(--dur-micro) var(--ease-out); }
.chip:hover { border-color: var(--color-muted); }
.chip input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.chip:has(input:checked), .chip[aria-pressed="true"] { background: var(--color-paper-3); border-color: var(--color-ink-2); }
.chip:has(input:focus-visible) { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.chip:has(input:disabled) { opacity: 0.55; cursor: not-allowed; }
.chip:active { transform: translateY(1px); }
.tag { display: inline-block; font-size: var(--text-xs); font-weight: 600; padding: 0 var(--space-xs); border-radius: var(--radius-pill); border: var(--rule-hair) solid currentColor; white-space: nowrap; }
.good { color: var(--color-up); } .wait { color: var(--color-down); } .str { color: var(--color-own); } .neu { color: var(--color-muted); }
thead button { border: 0; background: none; padding: 0; font: inherit; color: inherit; cursor: pointer; }
th[aria-sort] button::after { content: ""; display: inline-block; width: 5px; height: 5px; margin-inline-start: 5px; border-right: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: translateY(-2px) rotate(45deg); }
th[aria-sort="ascending"] button::after { transform: translateY(1px) rotate(-135deg); }
.foot { border-top: var(--rule-hair) solid var(--color-rule); margin-top: var(--space-2xl); padding-block: var(--space-lg); color: var(--color-muted); font-size: var(--text-sm); }
.foot .container { display: grid; gap: var(--space-2xs); }
@media (max-width: 60rem) { :root { --gutter: 16px; } .clock { margin-inline-start: 0; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition-duration: 0.01ms !important; } }
"""


def esc(s) -> str:
    return _html.escape(str(s))


def pct(x: float, d: int = 1, sign: bool = True) -> str:
    x = round(x * 100, d)  # sign from the shown digits: -0.04% prints as 0.0%, not -0.0%
    s = f"{abs(x):.{d}f}%"
    if not sign:
        return s
    return ("+" if x > 0 else MINUS if x < 0 else "") + s


def num(x: float, d: int = 2, sign: bool = False) -> str:
    s = f"{abs(x):.{d}f}"
    lead = "+" if sign and round(x, d) > 0 else ""
    return (MINUS if round(x, d) < 0 else lead) + s


def eur(x: float, d: int = 0, sign: bool = False) -> str:
    x = round(x, d)
    s = "€" + f"{abs(x):,.{d}f}".replace(",", chr(0x2009))
    if sign:
        return ("+" if x > 0 else MINUS if x < 0 else "") + s
    return s


def usd(x: float, d: int = 2) -> str:
    return "$" + f"{x:,.{d}f}".replace(",", chr(0x2009))


def big_usd(n) -> str | None:
    if not n:
        return None
    for unit, v in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if n >= v:
            return f"${n / v:.2f}{chr(0x2009)}{unit}"
    return usd(n, 0)


def cls(x: float) -> str:
    return "up" if x >= 0.0005 else "down" if x <= -0.0005 else "flat"  # under 0.05% prints as 0.0% and stays grey


def day(iso: str, year: bool = True) -> str:
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]}" + (f" {y}" if year else "")


def scale(vals, lo, hi, a, b):
    span = (hi - lo) or 1
    return [a + (v - lo) / span * (b - a) for v in vals]


def path(xs, ys) -> str:
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def spark(vals, w: int = 96, h: int = 32, kind: str | None = None) -> str:
    kind = kind or cls(vals[-1] - vals[0])
    xs = scale(range(len(vals)), 0, len(vals) - 1, 1, w - 1)
    ys = scale(vals, min(vals), max(vals), h - 2, 2)
    return f'<svg class="spark {kind}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true"><path d="{path(xs, ys)}"/></svg>'


def nice_ticks(lo: float, hi: float, n: int = 4) -> list[float]:
    raw = (hi - lo) / n or 1
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=10 * mag)
    out, v = [], math.ceil(lo / step) * step
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def month_ticks(dates: list[str]) -> list[tuple[int, str]]:
    out, seen = [], set()
    for i, d in enumerate(dates):
        if d[:7] not in seen:
            seen.add(d[:7])
            if i > 3:
                out.append((i, MONTHS[int(d[5:7]) - 1]))
    return out


def line_chart(series, dates, w=720, h=280, fmt=lambda v: f"{v:.0f}", label="", every=2, base=None) -> str:
    """series: list of (values, css class[, data-t]). One y axis, 3-5 hairline grid lines."""
    L, R, T, B = 52, 12, 12, 28
    allv = [v for s in series for v in s[0]]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    n = len(series[0][0])
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">']
    for v in nice_ticks(lo, hi, 5):
        y = scale([v], lo, hi, h - B, T)[0]
        out.append(f'<line class="grid" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="ax" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{esc(fmt(v))}</text>')
    if base is not None and lo < base < hi:
        y = scale([base], lo, hi, h - B, T)[0]
        out.append(f'<line class="base" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>')
    for k, (i, m) in enumerate(month_ticks(dates)):
        if not k % every:
            x = scale([i], 0, max(n - 1, 1), L, w - R)[0]
            out.append(f'<text class="ax" x="{x:.1f}" y="{h - 8}" text-anchor="middle">{m}</text>')
    xs = scale(range(n), 0, max(n - 1, 1), L, w - R)
    for s in series:
        vals, c = s[0], s[1]
        t = f' data-t="{esc(s[2])}"' if len(s) > 2 and s[2] else ""
        out.append(f'<path class="ln {c}"{t} d="{path(xs, scale(vals, lo, hi, h - B, T))}"/>')
    out.append("</svg>")
    return "".join(out)


def rangebar(pos: float, lo: float, hi: float) -> str:
    return (f'<span class="range" style="--pos:{pos:.3f}" title="52-week closing range {usd(lo)} to {usd(hi)}">'
            f'<span class="range-mark"></span></span>')


def helsinki(close: str, h: int, m: int) -> str:
    """New York wall time on the close date as Helsinki time; the two switch to summer time on different dates."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    y, mo, d = map(int, close[:10].split("-"))
    return datetime(y, mo, d, h, m, tzinfo=ZoneInfo("America/New_York")).astimezone(ZoneInfo("Europe/Helsinki")).strftime("%H:%M")


def clock(meta: dict) -> str:
    c = meta["close"]
    return (f'<p class="clock"><span>Prices: US close <b>{day(c, False)}</b>, {helsinki(c, 16, 0)} Helsinki</span>'
            f'<span>New York opens <b>{helsinki(c, 9, 30)}</b> Helsinki time</span><span>EUR/USD <b class="num">{meta["eurusd"]:.4f}</b></span></p>')


def built(stamp: str) -> str:
    """'2026-11-24T08:18Z' as '24 Nov 2026, 10:18 Helsinki time'."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    t = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Helsinki"))
    return f"{day(t.date().isoformat())}, {t:%H:%M} Helsinki time"


def footer(meta: dict, extra: str = "") -> str:
    skipped = meta.get("skipped") or []
    skip = (f"<p>Tickers left out for lack of a year of prices: {esc(', '.join(skipped))}.</p>" if skipped else "")
    return (f'<footer class="foot"><div class="container"><p>Prices, company facts and EUR/USD from Yahoo Finance; '
            f'holdings from the Nordnet report of {day(meta["holdings_as_of"])}. Returns, volatility, beta and worst fall '
            f'are computed from daily closes. Built {built(meta["built"])}.</p>{skip}{extra}'
            f'<p>Not investment advice.</p></div></footer>')


def page(title: str, desc: str, look: str, critique: str, css: str, body: str, script: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS[look]}&display=swap">
<style>
{STAMPS[look]}
/* Hallmark · pre-emit critique: {critique} */
:root {{{SCALE}
{TOKENS[look]}
}}
{BASE}
{css}
</style>
</head>
<body>
{body}
{script}
</body>
</html>"""


def nav(current: str) -> str:
    items = [("desk.html", "Desk"), ("impact.html", "Impact"), ("cards.html", "Ideas"), ("analysis/index.html", "Analysis"), ("forecasts.html", "Forecasts"), ("goal.html", "Goal"), ("aamu.html", "Aamu")]
    return "".join(f'<a href="{h}"{" aria-current=\"page\"" if n == current else ""}>{n}</a>' for h, n in items)
