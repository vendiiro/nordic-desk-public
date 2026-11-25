"""Home page: today at a glance. What changed since the last run, and whether anything needs the owner."""
from __future__ import annotations

from .aamu import sentence
from .core import clock, cls, day, esc, eur, footer, nav, page, pct
from .huurre import CSS as DESK_CSS

STALE_DAYS = 4  # a long weekend is 3 days without a close

# The page is static and may be read days after it was built, so the age is measured when it is opened.
STALE_JS = f"""<script>
(() => {{
  const w = document.getElementById('stale'), age = Math.floor((Date.now() - Date.parse(w.dataset.close)) / 864e5);
  if (age > {STALE_DAYS}) {{ w.querySelector('span').textContent = age; w.hidden = false; }}
}})();
</script>"""

CSS = DESK_CSS + """
.today { display: grid; gap: var(--space-lg); padding-block: var(--space-lg) var(--space-xl); }
.answer h1 { font-size: var(--text-3xl); }
.answer p { color: var(--color-ink-2); max-width: 70ch; margin-top: var(--space-xs); }
.warn { border: var(--rule-hair) solid var(--color-down); color: var(--color-down); border-radius: var(--radius-card); padding: var(--space-sm) var(--space-md); }
.two { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: var(--gap); align-items: start; }
.today tbody th { white-space: normal; }
.changes { margin: 0; padding-inline-start: var(--space-lg); display: grid; gap: var(--space-2xs); }
@media (max-width: 60rem) { .two { grid-template-columns: minmax(0, 1fr); } }
"""


def today_page(desk: dict, aamu: dict, alerts: list, verdicts: dict, goal: dict | None = None) -> str:
    meta, p = desk["meta"], aamu["portfolio"]
    from ..analysis import analysis_href
    href = lambda t: analysis_href(t) or "desk.html"  # noqa: E731
    changed = [(t, v) for t, v in verdicts.items() if v.get("changed")]
    items = ([f'<li><a href="cards.html#{esc(a["ticker"])}">{esc(a["name"])}</a> is now {esc(a["now"])}'
              + (f', was {esc(a["before"])}' if a.get("before") else "") + ".</li>" for a in alerts]
             + [f'<li><a href="{esc(href(t))}">{esc(v.get("name") or t)}</a> verdict is now '
                f'<span class="tag {v["cls"]}">{esc(v["verdict"])}</span>.</li>' for t, v in changed])
    n = len(items)
    if n:
        answer = f'<h1>{n} thing{"s" if n > 1 else ""} changed since the last run</h1><p>Look at these before anything else.</p>'
    else:
        answer = ('<h1>Nothing needs you today</h1><p>No threshold crossed and no verdict changed since the last run. '
                  'Holding as you are is a valid answer.</p>')
    stale = (f'<p class="warn" id="stale" data-close="{esc(meta["close"])}" hidden>Prices are <span></span> days old (US close {day(meta["close"])}). '
             'Run <code>nordic-desk update</code>, then <code>site</code>.</p>')
    held = [(t, v) for t, v in verdicts.items() if v.get("group") == "held" and v.get("verdict")]
    rows = "".join(f'<tr><th scope="row"><a href="{esc(href(t))}">{esc(v.get("name") or t)}</a> <span class="tk">{esc(t)}</span></th>'
                   f'<td><span class="tag {v["cls"]}" title="{esc(v["line"])}">{esc(v["verdict"])}</span></td>'
                   f'<td class="num r">{pct(v["expected"], 1) if v.get("expected") is not None else "–"}</td></tr>' for t, v in held)
    hold = (f'<section class="panel flush" aria-labelledby="h-h"><div class="sec-head"><h2 id="h-h">Your holdings</h2>'
            f'<p class="sub">Entry verdict for 6–12 months and expected 12 m.</p></div><div class="table-wrap"><table><thead><tr>'
            f'<th scope="col">Holding</th><th scope="col">Verdict</th><th scope="col" class="r">Expected 12 m</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></section>') if rows else ""
    from .goal import summary_line
    line = summary_line(goal) if goal else None
    longer = (f'<section class="panel" aria-labelledby="g-h"><h2 id="g-h">Long range</h2><p>{esc(line)}</p>'
              '<p><a href="goal.html">See the range, the saving it takes and how far to trust it</a></p></section>') if line else ""
    body = f"""
<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Nordic Desk, home">Nordic Desk</a>
<nav aria-label="Views">{nav("")}</nav>{clock(meta)}</div></header>
<main class="container today">
  <div class="answer">{answer}</div>
  {stale}
  <div class="two">
    <section class="panel" aria-labelledby="o-h"><h2 id="o-h">Last night</h2>
      <div class="fig"><span class="pl">Portfolio, in euros</span><span class="v">{eur(p["value"])}</span>
      <span class="num {cls(p["overnight"])}">{eur(p["overnight"], 0, True)} overnight</span></div>
      <p>{esc(sentence(p, aamu["spy_overnight"]))}</p>
      {f'<h2>Changed</h2><ul class="changes">{"".join(items)}</ul>' if items else ""}
    </section>
    {hold}
  </div>
  {longer}
</main>
{footer(meta)}"""
    return page("Nordic Desk", "Today: what changed since the last run and whether anything needs you.", "huurre",
                "P3 H3 E3 S3 R3 V3 · weakest: E, the quiet day is the common day", CSS, body, STALE_JS)
