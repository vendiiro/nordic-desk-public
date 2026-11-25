"""Holdings page: each current holding and its weight, nothing else.

Positions come from the local holdings file (Nordnet report date) and are revalued to the latest close
with the stored Yahoo prices. Positions without a price series and cash keep their report value.
The page is written to out/ (git-ignored) because it describes real holdings.
"""
from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from . import prices
from .config import load_holdings, load_instruments
from .panel import to_eur

FX = "EURUSD=X"


def current_weights(holdings_path: str = "config/holdings.local.toml", price_root: Path = prices.ROOT,
                    end: str | None = None, instruments_path: str = "config/instruments.toml") -> list[tuple[str, float]]:
    h = load_holdings(holdings_path)
    cur = {i.ticker: i.currency for i in load_instruments(instruments_path).values()}
    eurusd = prices.load(FX, root=price_root)
    values: dict[str, float] = {}
    for p in h.positions:
        v = p.value_eur
        if p.ticker:
            s = prices.load(p.ticker, root=price_root)
            if end:
                s = s[s.index <= pd.Timestamp(end)]
            e = to_eur(s, eurusd, cur.get(p.ticker, "USD"))
            at_report = e[e.index <= pd.Timestamp(h.as_of)]
            if len(at_report) and len(e):
                v = v * e.iloc[-1] / at_report.iloc[-1]
        values[p.name] = values.get(p.name, 0.0) + v
    if h.cash_eur:
        values["Cash"] = values.get("Cash", 0.0) + h.cash_eur
    total = sum(values.values())
    return sorted(((n, v / total) for n, v in values.items()), key=lambda r: -r[1])


def render(rows: list[tuple[str, float]], close: str, report: str) -> str:
    top = max(w for _, w in rows)
    body = "".join(
        f'<tr><th scope="row">{html.escape(n.title() if n.isupper() else n)}</th>'
        f'<td class="bar"><span style="--w:{w / top:.4f}"></span></td>'
        f'<td class="num">{w * 100:.1f}%</td></tr>'
        for n, w in rows)
    close_d, report_d = pd.Timestamp(close), pd.Timestamp(report)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Holdings</title>
<meta name="description" content="Current holdings and their weights.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Host+Grotesk:wght@400;500&family=Atkinson+Hyperlegible+Mono&display=swap">
<style>
/* Hallmark · shape: app screen · theme: Console (paper colourway, cooled to hoarfrost) as the Huurre mockup · signature: one weight bar per holding · states: full · v2.0.0 */
/* Hallmark · pre-emit critique: P3 H3 E3 S2 R3 V3 · weakest: S, the page is one table on purpose, holdings and weights only */
:root {{
  color-scheme: light;
  --color-paper: oklch(98.5% 0.004 240); --color-paper-2: oklch(96.5% 0.006 240);
  --color-ink: oklch(21% 0.012 250); --color-muted: oklch(50% 0.014 250);
  --color-rule: oklch(90% 0.008 240); --color-bar: oklch(46% 0.13 250); --color-focus: oklch(55% 0.16 250);
  --font-body: "Host Grotesk", ui-sans-serif, system-ui, sans-serif;
  --font-num: "Atkinson Hyperlegible Mono", ui-monospace, monospace;
  --space-xs: 8px; --space-sm: 12px; --space-md: 16px; --space-xl: 40px;
}}
* {{ box-sizing: border-box; }}
html, body {{ overflow-x: clip; }}
body {{ margin: 0; background: var(--color-paper); color: var(--color-ink); font-family: var(--font-body); font-size: 1rem; line-height: 1.5; }}
:focus-visible {{ outline: 2px solid var(--color-focus); outline-offset: 2px; }}
main {{ max-width: 56rem; margin-inline: auto; padding: var(--space-xl) var(--space-md); }}
h1 {{ margin: 0; font-weight: 500; font-size: 1.728rem; letter-spacing: -0.02em; overflow-wrap: break-word; min-width: 0; text-wrap: balance; }}
.sub {{ margin: var(--space-xs) 0 var(--space-xl); color: var(--color-muted); font-size: 0.875rem; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: var(--space-sm) var(--space-xs); border-bottom: 1px solid var(--color-rule); vertical-align: middle; }}
thead th {{ font-weight: 500; font-size: 0.875rem; color: var(--color-muted); text-align: start; }}
tbody th {{ font-weight: 400; text-align: start; }}
.bar {{ width: 40%; }}
.bar span {{ display: block; height: 10px; inline-size: calc(var(--w) * 100%); background: var(--color-bar); }}
.visually-hidden {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }}
.num {{ font-family: var(--font-num); font-variant-numeric: tabular-nums; text-align: end; white-space: nowrap; }}
thead .num {{ font-family: var(--font-body); }}
@media (max-width: 40rem) {{ .bar {{ width: 30%; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
</style>
</head>
<body>
<main>
<h1>Holdings</h1>
<p class="sub">Weights at the US close on {close_d.day} {close_d:%b %Y}; positions from the Nordnet report of {report_d.day} {report_d:%b %Y}.</p>
<table>
<thead><tr><th scope="col">Holding</th><th scope="col"><span class="visually-hidden">Weight bar</span></th><th scope="col" class="num">Weight</th></tr></thead>
<tbody>{body}</tbody>
</table>
</main>
</body>
</html>
"""
