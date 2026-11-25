"""Ideas and search: one candidate card per stock or ETF, with analyst signals and the portfolio before and after."""
from __future__ import annotations

from .core import cls, day, esc, eur, line_chart, nav, num, page, pct
from .huurre import CSS as DESK_CSS

GROUPS = [("diversify", "Diversify away from IT"), ("growth", "IT and AI growth"), ("searched", "Your searches")]
STATUS_CLASS = {"below buy threshold": "up", "above sell threshold": "down"}

CSS = DESK_CSS + """
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 36rem), 1fr)); gap: var(--gap); }
.card { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-md); align-content: start; min-width: 0; }
.card h3 { font-size: var(--text-xl); }
.tags { display: flex; flex-wrap: wrap; gap: var(--space-xs); }
.tag { font-size: var(--text-sm); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); padding: 0 var(--space-xs); color: var(--color-ink-2); }
.status { font-weight: 600; }
.tkline { font-size: var(--text-md); color: var(--color-ink-2); }
.cols { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr)); gap: var(--space-lg); }
.amounts { margin: 0; }
.amounts .chip input[type="radio"] { position: absolute; opacity: 0; width: 1px; height: 1px; }
.group { padding-block: var(--space-lg); }
.group > h2 { margin-bottom: var(--space-md); }
.errors { color: var(--color-muted); font-size: var(--text-sm); }

.finder { display: grid; gap: var(--space-md); padding: var(--space-md); border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); background: var(--color-paper-2); }
.finder form { display: flex; gap: var(--space-xs); flex-wrap: wrap; align-items: end; }
.finder .field { display: grid; gap: var(--space-2xs); flex: 1 1 18rem; }
.finder label { font-size: var(--text-sm); color: var(--color-muted); }
.finder input[type="search"] { min-height: 40px; padding: 0 var(--space-sm); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); background: var(--color-paper); font-size: var(--text-md); }
.finder input[type="search"]:hover { border-color: var(--color-muted); }
.finder input[type="search"]:focus-visible { outline-offset: -2px; }
.finder input:disabled, .finder button:disabled { opacity: 0.55; cursor: not-allowed; }
.hits { list-style: none; margin: 0; padding: 0; display: grid; }
.hits li { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-sm); align-items: center; padding: var(--space-xs) 0; border-bottom: var(--rule-hair) solid var(--color-rule); }
.hits .who { min-width: 0; }
.hits .meta { display: block; font-size: var(--text-sm); color: var(--color-muted); }
.offline { font-size: var(--text-sm); color: var(--color-ink-2); }
.finder .chip { white-space: nowrap; }
.impact { display: grid; gap: var(--space-sm); min-width: 0; }
.impact > p, .impact [data-amt] > p { margin: 0; }
.impact [data-amt] { display: grid; gap: var(--space-xs); }
.lt-lead { max-width: 62ch; }
.lt-lead b { font-weight: 600; font-variant-numeric: tabular-nums; }
.lt-note { font-size: var(--text-sm); color: var(--color-muted); max-width: 70ch; }
tr.lt-head th { padding-top: var(--space-md); font-size: var(--text-sm); font-weight: 400; color: var(--color-muted); }
.impact th[scope="row"] { white-space: normal; min-width: 9rem; }
.brief { display: grid; gap: var(--space-sm); border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-md); min-width: 0; }
.brief > p, .brief ul { margin: 0; }
.brief-head { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: var(--space-xs); }
.brief-head h4 { margin: 0; }
.badge { font-size: var(--text-xs); border: var(--rule-hair) solid var(--color-own); color: var(--color-own); border-radius: var(--radius-pill); padding: 1px var(--space-xs); white-space: nowrap; }
.brief .meta { font-size: var(--text-sm); color: var(--color-muted); max-width: 70ch; }
.brief .two { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 15rem), 1fr)); gap: var(--space-md); }
.brief h5 { margin: 0 0 var(--space-xs); font-size: var(--text-sm); font-weight: 600; }
.brief .points { list-style: none; padding: 0; display: grid; gap: var(--space-xs); }
.src { font-size: var(--text-xs); color: var(--color-muted); white-space: nowrap; }
.src a { color: inherit; text-underline-offset: 2px; }
.tone-bar { display: flex; height: 8px; border-radius: 4px; overflow: hidden; background: var(--color-paper-3); max-width: 22rem; }
.tone-bar span { display: block; height: 100%; }
.tone-bar .pos { background: var(--color-up); } .tone-bar .neu { background: var(--color-rule-2); } .tone-bar .neg { background: var(--color-down); }
.events { list-style: none; padding: 0; display: grid; gap: var(--space-2xs); font-size: var(--text-sm); }
.events li { display: grid; grid-template-columns: 6.5rem minmax(0, 1fr); gap: var(--space-sm); }
.alerts { border: var(--rule-hair) solid var(--color-own); border-radius: var(--radius-card); padding: var(--space-md); margin-bottom: var(--space-lg); }
.alerts ul { margin: var(--space-xs) 0 0; padding-inline-start: var(--space-lg); }
@media (max-width: 40rem) {
  .card { padding: var(--space-sm); }
  .impact table { font-size: var(--text-sm); }
  .impact th, .impact td { padding-inline: var(--space-2xs); }
  .impact th[scope="row"], .impact thead th:first-child { min-width: 0; white-space: normal; }
  .impact td { white-space: nowrap; }
}
"""

CSS += """
.ideas { display: grid; gap: var(--space-sm); }
.tabs { display: flex; gap: var(--space-xs); overflow-x: auto; padding-bottom: 2px; scrollbar-width: thin; }
.tabs button { flex: none; border: var(--rule-hair) solid var(--color-rule-2); background: var(--color-paper); border-radius: 999px; min-height: 40px; padding: 0 var(--space-sm); font-size: var(--text-sm); cursor: pointer; white-space: nowrap; transition: background-color var(--dur-micro) var(--ease-out); }
.tabs button:hover { background: var(--color-paper-2); }
.tabs button[aria-pressed="true"] { background: var(--color-accent); border-color: var(--color-accent); color: var(--color-accent-ink); }
.tabs .n { font-family: var(--font-num); opacity: 0.75; margin-inline-start: var(--space-2xs); }
.idea-head, details.idea > summary { display: grid; grid-template-columns: minmax(0, 2.6fr) minmax(0, 1.3fr) repeat(3, minmax(0, 0.9fr)) minmax(0, 1.7fr); gap: var(--space-sm); align-items: center; padding: var(--space-xs) var(--space-sm); }
.idea-head { font-size: var(--text-sm); color: var(--color-muted); border-bottom: var(--rule-hair) solid var(--color-rule); }
.idea-head .r, details.idea > summary .r { text-align: end; }
details.idea { border-bottom: var(--rule-hair) solid var(--color-rule); }
details.idea > summary { cursor: pointer; list-style: none; min-height: 52px; transition: background-color var(--dur-micro) var(--ease-out); }
details.idea > summary::-webkit-details-marker { display: none; }
details.idea > summary:hover { background: var(--color-paper-2); }
details.idea[open] > summary { background: var(--color-sel); }
details.idea .nm b { display: block; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
details.idea .nm .tk { font-size: var(--text-sm); color: var(--color-muted); }
details.idea > summary .num { white-space: nowrap; }
details.idea .st .status { font-size: var(--text-sm); white-space: nowrap; }
details.idea .st { display: flex; justify-content: space-between; align-items: center; gap: var(--space-xs); }
details.idea .st::after { content: ""; flex: none; width: 8px; height: 8px; border-right: 2px solid var(--color-muted); border-bottom: 2px solid var(--color-muted); transform: rotate(45deg); margin-inline-end: var(--space-2xs); transition: transform var(--dur-micro) var(--ease-out); }
details.idea[open] .st::after { transform: rotate(-135deg); }
details.idea > .card { margin: var(--space-sm) 0 var(--space-lg); }
@media (max-width: 720px) {
  .idea-head { display: none; }
  details.idea > summary { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: var(--space-2xs); }
  details.idea > summary .nm, details.idea > summary .st { grid-column: 1 / -1; }
  details.idea .nm b { white-space: normal; }
  details.idea > summary .r { text-align: start; }
  details.idea > summary [data-l]::before { content: attr(data-l) " "; color: var(--color-muted); font-family: var(--font-body); font-size: var(--text-sm); }
}
"""

JS = """
<script>
document.addEventListener('change', e => {
  const card = e.target.closest('.card');
  if (!card || e.target.type !== 'radio') return;
  card.querySelectorAll('[data-amt]').forEach(el => { el.hidden = el.dataset.amt !== e.target.value; });
});
</script>""" + """
<script>
(() => {
  // group buttons: one group visible at a time, remembered in the URL; #TICKER opens that card
  const tabs = () => [...document.querySelectorAll('.tabs [data-g]')];
  const pick = g => {
    tabs().forEach(b => b.setAttribute('aria-pressed', b.dataset.g === g));
    document.querySelectorAll('details.idea').forEach(d => { d.hidden = g !== 'all' && d.dataset.group !== g; });
    history.replaceState(null, '', '#g=' + g);
  };
  window.pickGroup = pick;
  const open = id => {
    const el = document.getElementById(id), d = el && el.closest('details.idea');
    if (!d) return false;
    pick(d.dataset.group); d.open = true; d.scrollIntoView({block: 'start'}); return true;
  };
  tabs().forEach(b => b.addEventListener('click', () => pick(b.dataset.g)));
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href^="#"]');
    if (a && a.getAttribute('href').length > 1 && open(decodeURIComponent(a.getAttribute('href').slice(1)))) e.preventDefault();
  });
  const route = () => {
    const h = decodeURIComponent(location.hash.slice(1)), g = h.startsWith('g=') ? h.slice(2) : '';
    const ok = g && tabs().some(b => b.dataset.g === g && !b.hidden);
    if (!(h && !g && open(h))) pick(ok ? g : (tabs().find(b => b.dataset.g === 'growth') ? 'growth' : (tabs().find(b => !b.hidden) || {dataset: {g: 'all'}}).dataset.g));
  };
  window.addEventListener('hashchange', route);  // a typed or pasted #TICKER / #g=... on an open page
  route();
})();
</script>
<script>
(() => {
  const f = document.querySelector('.finder');
  if (!f) return;
  const live = location.protocol.startsWith('http');
  const status = f.querySelector('[role=status]');
  const list = f.querySelector('.hits');
  if (!live) {
    f.querySelectorAll('input, button').forEach(el => { el.disabled = true; });
    f.querySelector('.offline').hidden = false;
    return;
  }
  const say = t => { status.textContent = t; };
  const row = h => {
    const li = document.createElement('li');
    const who = document.createElement('div'); who.className = 'who';
    const name = document.createElement('b'); name.textContent = h.symbol + '  ' + h.name;
    const meta = document.createElement('span'); meta.className = 'meta';
    meta.textContent = [h.exchange, h.type === 'ETF' ? 'fund (ETF)' : 'stock', h.rating ? 'analysts ' + h.rating : ''].filter(Boolean).join(', ');
    who.append(name, meta);
    const b = document.createElement('button'); b.type = 'button'; b.className = 'btn ghost'; b.textContent = 'Show card';
    b.addEventListener('click', async () => {
      b.disabled = true; say('Building the card for ' + h.symbol + '. This takes a few seconds.');
      try {
        const r = await fetch('/api/card?t=' + encodeURIComponent(h.symbol), {headers: {'X-Desk': '1'}});
        if (!r.ok) throw new Error((await r.json()).error);
        const old = document.getElementById(h.symbol); if (old) (old.closest('details') || old).remove();
        const d = document.createElement('details'); d.className = 'idea'; d.dataset.group = 'found'; d.open = true;
        const s = document.createElement('summary'); const nm = document.createElement('span'); nm.className = 'nm';
        const b2 = document.createElement('b'); b2.textContent = h.name; const tk = document.createElement('span'); tk.className = 'tk'; tk.textContent = h.symbol;
        nm.append(b2, tk); s.append(nm); d.append(s); d.insertAdjacentHTML('beforeend', await r.text());
        document.getElementById('idea-list').prepend(d);
        const ft = document.querySelector('.tabs [data-g=found]'); ft.hidden = false;
        ft.querySelector('.n').textContent = document.querySelectorAll('details.idea[data-group=found]').length;
        window.pickGroup('found'); d.scrollIntoView({behavior: 'smooth'}); d.querySelector('h3').focus();
        say('Card ready: ' + h.symbol + '.');
      } catch (e) { say('Could not build the card: ' + e.message); }
      b.disabled = false;
    });
    li.append(who, b); return li;
  };
  const show = async (url, label) => {
    say('Searching ' + label + '.'); list.replaceChildren();
    try {
      const r = await fetch(url, {headers: {'X-Desk': '1'}}); const rows = await r.json();
      if (!r.ok) throw new Error(rows.error);
      rows.forEach(h => list.append(row(h)));
      say(rows.length ? rows.length + ' results for ' + label + '.' : 'Nothing found for ' + label + ' on the US, Helsinki or Xetra exchanges.');
    } catch (e) { say('Search failed: ' + e.message); }
  };
  f.querySelector('form').addEventListener('submit', e => {
    e.preventDefault(); const q = f.querySelector('input[name=q]').value.trim();
    if (q) show('/api/search?q=' + encodeURIComponent(q), '"' + q + '"');
  });
  f.querySelectorAll('[data-list]').forEach(b => b.addEventListener('click', () => show('/api/discover?list=' + b.dataset.list, b.textContent)));
})();
</script>"""


def money(v, cur) -> str:
    if v is None:
        return "not available"
    return f"{v:,.2f}".replace(",", chr(0x202F)) + f" {cur or ''}".rstrip()


def big(v) -> str:
    if v is None:
        return "not available"
    return (chr(0x2212) if v < 0 else "") + (f"{abs(v) / 1e9:.1f} bn" if abs(v) >= 1e9 else f"{abs(v) / 1e6:.0f} m")


def move_sentence(corr: float) -> str:
    if corr >= 0.6:
        return "moves mostly with your holdings"
    if corr >= 0.3:
        return "moves partly with your holdings"
    return "moves differently from your holdings"


def results_table(c: dict) -> str:
    if c.get("type") == "ETF":
        return '<p class="note">no company results (fund)</p>'
    rows = c.get("results") or []
    if not rows:
        return '<p class="note">results not available</p>'
    rows = sorted(rows, key=lambda r: r["year"])
    trs = []
    for i, r in enumerate(rows):
        prev = rows[i - 1]["revenue"] if i else None
        g = (r["revenue"] / prev - 1) if prev and r["revenue"] else None
        trs.append(f'<tr><th scope="row">{r["year"]}</th><td class="num r">{big(r["revenue"])}</td>'
                   f'<td class="num r">{big(r["net_income"])}</td><td class="num r {cls(g or 0)}">{pct(g) if g is not None else "–"}</td></tr>')
    return ('<div class="table-wrap"><table><thead><tr><th scope="col">Year</th><th scope="col" class="r">Revenue</th>'
            '<th scope="col" class="r">Net income</th><th scope="col" class="r">Revenue growth</th></tr></thead><tbody>'
            + "".join(trs).replace("–", "none") + f'</tbody></table></div><p class="note">In {esc(c.get("currency") or "")}, from Yahoo annual statements.</p>')


def analyst_block(c: dict) -> str:
    a, cur = c.get("analysts"), c.get("currency")
    if not a or not a["count"]:
        return '<p class="note">no analyst coverage</p>'
    share = pct(a["rating_share"], 0, False) if a["rating_share"] is not None else "not available"
    rows = [("Analysts", str(a["count"])), ("Buy or strong buy", share),
            ("Target, low to high", f'{money(a["target_low"], cur)} to {money(a["target_high"], cur)}'),
            ("Target, mean", money(a["target_mean"], cur)), ("Upside to mean target", pct(a["upside"]) if a["upside"] is not None else "not available"),
            ("Buy threshold, below", money(a["buy_below"], cur)), ("Sell threshold, above", money(a["sell_above"], cur))]
    dl = "".join(f"<div><dt>{k}</dt><dd class=\"num\">{esc(v)}</dd></div>" for k, v in rows)
    h = c.get("history")
    since = ""
    if h:
        bits = []
        if h.get("target") is not None:
            bits.append(f'mean target {pct(h["target"])}')
        if h.get("rating_points") is not None:
            bits.append(f'buy share {num(h["rating_points"], 0, True)} points')
        since = f'<p class="note">Since {day(h["since"])}: {", ".join(bits) or "no comparable change"}.</p>'
    return (f'<p class="status {STATUS_CLASS.get(a["status"], "flat")}">{esc(a["status"].capitalize())}</p>'
            f'{since}<dl class="facts">{dl}</dl>')


def _names(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def lookthrough_lead(c: dict) -> str:
    """One sentence on how much of the portfolio already sits in this company (or this fund's largest holdings)."""
    lt = c["lookthrough"]
    if not lt["focus"]:
        return '<p class="lt-lead">No holdings data for this fund, so its overlap with what you own cannot be shown.</p>'
    if c.get("type") == "ETF":
        names = _names([esc(lt["names"][k]) for k in lt["focus"]])
        return f'<p class="lt-lead">This fund&#8217;s largest holdings are {names}. Their share of your portfolio, funds included, is in the table.</p>'
    k = lt["focus"][0]
    name, total, via = esc(lt["names"][k]), lt["before"][k], lt["via_funds"].get(k, 0.0)
    if total <= 0:
        return f'<p class="lt-lead">You do not own {name} yet, directly or through funds.</p>'
    direct = total - via
    how = ("all of it through funds" if direct < 5e-5 else "all of it directly" if via < 5e-5
           else f"{pct(direct, 1, False)} directly and {pct(via, 1, False)} through funds")
    return f'<p class="lt-lead">You already own <b>{pct(total, 1, False)}</b> of the portfolio in {name}: {how}.</p>'


def lookthrough_note(lt: dict) -> str:
    bits = []
    if lt["not_broken_down"] >= 0.005:
        bits.append(f'{pct(lt["not_broken_down"], 0, False)} of the portfolio sits in funds outside their published top holdings and is not broken down.')
    if lt["no_data"]:
        bits.append(f'No holdings data: {esc(", ".join(lt["no_data"]))}.')
    bits.append("Fund top holdings from Yahoo Finance (up to ten per fund).")
    return f'<p class="lt-note">{" ".join(bits)}</p>'


def impact_block(c: dict, default_amount: int | None = None) -> str:
    imp = c.get("impact")
    if not imp:
        return f'<p class="note">{esc(c.get("impact_note") or "portfolio comparison not available")}</p>'
    t = esc(c["ticker"])
    amounts = sorted(imp["amounts"], key=int)
    pick = str(default_amount) if str(default_amount) in amounts else amounts[0]
    lt = c.get("lookthrough")
    radios = "".join(f'<label class="chip"><input type="radio" name="amt-{t}" value="{a}"{" checked" if a == pick else ""}>€{int(a):,}</label>'.replace(",", chr(0x202F))
                     for a in amounts)
    b, eb = imp["before"], imp["expected_before"]

    def mark(d, lower_is_better=True):
        if abs(d) < 1e-9:
            return "flat", "no change"
        better = (d < 0) == lower_is_better
        return ("up" if better else "down"), ("lowers" if d < 0 else "raises")

    blocks = []
    for a in amounts:
        s = imp["amounts"][a]
        rows = []
        for label, k, f, lower in (("Volatility", "vol", lambda v: pct(v, 1, False), True), ("Beta to S&P 500", "beta", lambda v: f"{v:.2f}", True),
                                   ("Worst fall, past year", "worst", pct, False), ("Effective holdings", "enb", lambda v: f"{v:.1f}", False),
                                   ("Technology share", "tech", lambda v: pct(v, 1, False), True)):
            c_, word = mark(s[k] - b[k], lower)
            if k == "worst" and word != "no change":
                word = "smaller fall" if s[k] > b[k] else "deeper fall"
            rows.append(f'<tr><th scope="row">{label}</th><td class="num r">{f(b[k])}</td><td class="num r">{f(s[k])}</td><td class="r {c_}">{word}</td></tr>')
        ea = s["expected"]
        if eb["value"] is not None and ea["value"] is not None:
            c_, word = mark(ea["value"] - eb["value"], lower_is_better=False)
            rows.append(f'<tr><th scope="row">Expected return, holdings with targets</th><td class="num r">{pct(eb["value"])}</td><td class="num r">{pct(ea["value"])}</td>'
                        f'<td class="r {c_}">{word}</td></tr>')
            cover = f'<p class="note">Expected return rests on {pct(ea["covered"], 0, False)} of the portfolio that has analyst targets.</p>'
        else:
            cover = '<p class="note">Expected return not available: too few holdings with analyst targets.</p>'
        if lt and lt["focus"]:  # concentration: shown neutrally, a share is neither good nor bad on its own
            rows.append('<tr class="lt-head"><th scope="colgroup" colspan="4">Share of your portfolio, funds included</th></tr>')
            for k in lt["focus"]:
                now, after = lt["before"][k], lt["amounts"][a][k]
                word = "no change" if abs(after - now) < 5e-5 else "raises" if after > now else "lowers"
                rows.append(f'<tr class="lt-row"><th scope="row">{esc(lt["names"][k])}<span class="visually-hidden"> share, including funds</span></th>'
                            f'<td class="num r">{pct(now, 1, False)}</td><td class="num r">{pct(after, 1, False)}</td><td class="r flat">{word}</td></tr>')
        blocks.append(f'<div data-amt="{a}"{"" if a == pick else " hidden"}><div class="table-wrap"><table><thead><tr><th scope="col">If you add €{int(a):,}</th>'
                      f'<th scope="col" class="r">Now</th><th scope="col" class="r">After</th><th scope="col" class="r">Effect</th></tr></thead>'
                      f'<tbody>{"".join(rows)}</tbody></table></div>{cover}</div>'.replace(f"€{int(a):,}", "€" + f"{int(a):,}".replace(",", chr(0x202F))))
    return (f'<p>{esc(c["name"])} {move_sentence(imp["corr"])}: correlation {num(imp["corr"])} over the past year, '
            f'{num(imp["down"])} on your worst fifth of days.</p>'
            + (lookthrough_lead(c) if lt else "")
            + f'<fieldset class="chips amounts"><legend class="visually-hidden">Amount of new money</legend>{radios}</fieldset>{"".join(blocks)}'
            + (lookthrough_note(lt) if lt else ""))


def _sources(ids: list[int], arts: dict[int, dict]) -> str:
    out = []
    for i in ids:
        a = arts.get(i)
        if not a:
            continue
        label = f'[{i}] {esc(a["sites"][0] if a["sites"] else "source")}'
        out.append(f'<a href="{esc(a["url"])}" rel="noopener noreferrer" target="_blank">{label}</a>' if a["url"].startswith(("https://", "http://"))
                   else label)  # only web links are clickable
    return f' <span class="src">{" ".join(out)}</span>' if out else ""


def brief_block(c: dict) -> str:
    t, b = esc(c["ticker"]), c.get("brief")
    title = f'<h4 class="pl" id="brief-{t}">News brief</h4>'
    head = f'<div class="brief-head">{title}<span class="badge">AI summary · unchecked</span></div>'
    if not b:
        return (f'<section class="brief" aria-labelledby="brief-{t}">{title}<p class="meta">No news brief yet. Run '
                f'<code>uv run nordic-desk brief {t}</code> to write one from free news sites (needs a Claude key).</p></section>')
    if not b["articles"]:
        return (f'<section class="brief" aria-labelledby="brief-{t}">{title}<p class="meta">No free articles about {esc(b.get("name") or c["name"])} '
                f'in the last 30 days, so no brief. Checked {day(b["written"])}.</p></section>')
    arts = {a["id"]: a for a in b["articles"]}
    n, (lo, hi) = len(b["articles"]), b["range"]
    sites = len({s for a in b["articles"] for s in a["sites"]})
    li = lambda pts: "".join(f'<li>{esc(p["text"])}{_sources(p["sources"], arts)}</li>' for p in pts) or '<li class="meta">Nothing in the articles.</li>'
    tn = b["tone"]
    tot = sum(tn.values()) or 1
    bar = "".join(f'<span class="{k}" style="width:{tn[v] / tot * 100:.0f}%"></span>' for k, v in (("pos", "positive"), ("neu", "neutral"), ("neg", "negative")))
    events = "".join(f'<li><span>{esc(e["date"])}</span><span>{esc(e["text"])}{_sources(e["sources"], arts)}</span></li>' for e in b["events"])
    what = f'<p>{esc(b["what"]["text"])}{_sources(b["what"]["sources"], arts)}</p>' if b.get("what") else ""
    return f"""<section class="brief" aria-labelledby="brief-{t}">{head}
<p class="meta">{n} articles from {sites} free sites, {day(lo, False)} to {day(hi)}. Paywalled sites skipped. Written {day(b["written"])} by {esc(b["model"])}.</p>
{what}<div class="two"><div><h5>Points for</h5><ul class="points">{li(b["for"])}</ul></div><div><h5>Points against</h5><ul class="points">{li(b["against"])}</ul></div></div>
<div><p class="meta">Tone of the {n} articles: {tn["positive"]} positive, {tn["neutral"]} neutral, {tn["negative"]} negative.</p>
<div class="tone-bar" role="img" aria-label="{tn["positive"]} positive, {tn["neutral"]} neutral, {tn["negative"]} negative">{bar}</div>
<p class="meta">News tone is not checked against later returns, so it does not enter any number on this card.</p></div>
{f'<div><h5>Coming up</h5><ul class="events">{events}</ul></div>' if events else ""}</section>"""


def _href(t: str) -> str | None:
    from ..analysis import analysis_href
    return analysis_href(t)


def realistic_line(c: dict, fc: dict | None) -> str:
    up = (c.get("analysts") or {}).get("upside")
    if not fc or up is None:
        return ""
    r = fc["targets"]["rates"]
    src = "own record" if r["n_checked"] >= 30 else "study"
    return (f'<p class="note">Realistic upside <span class="num">{pct(up - r["overshoot"])}</span> ({src}): targets ran about '
            f'{pct(r["overshoot"], 0, False)} too high on average. <a href="forecasts.html#targets">Why</a></p>')


def lump_line(c: dict, fc: dict | None, amount: int | None) -> str:
    r = ((fc or {}).get("lump", {}).get(c["ticker"]) or {}).get("6")
    if not r or not amount:
        return ""
    a, b = eur(r["lump_p5"] * amount), eur(r["spread_p5"] * amount)
    bad = (f"spreading over 6 months cut the bad case from {a} to {b}" if r["spread_p5"] > r["lump_p5"]
           else f"spreading over 6 months did not improve the bad case ({a} lump, {b} spread)")
    return (f'<p class="note">Lump ended ahead in {pct(r["lump_ahead"], 0, False)} of past start dates; {bad}. '
            f'<a href="forecasts.html#lump">Plan it</a></p>')


def card_html(c: dict, default_amount: int | None = None, fc: dict | None = None) -> str:
    p = c.get("price")
    tags = [x for x in (c.get("type") == "ETF" and "fund (ETF)", c.get("size") and f"{c['size']} company", c.get("sector"), c.get("industry"), c.get("currency")) if x]
    chart = ""
    if p:
        chart = (f'<figure class="chart-fig">{line_chart([(p["close"], "main"), (p["spy_scaled"], "ref")], p["dates"], h=220, every=6, label=c["ticker"] + " against SPY")}'
                 f'<figcaption><span class="key main"></span>{esc(c["ticker"])} <span class="key ref"></span>SPY, same start</figcaption></figure>'
                 f'<p><span class="num {cls(p["ret"])}">{pct(p["ret"], 0)}</span> since {day(p["dates"][0])}, '
                 f'worst fall on the way <span class="num down">{pct(p["worst_fall"], 0)}</span>.</p>')
    return f"""<article class="card" id="{esc(c['ticker'])}"><header><h3 tabindex="-1">{esc(c['name'])}</h3><p class="tkline"><span class="tk">{esc(c['ticker'])}</span>{f' · <a href="{esc(h)}">Analyse</a>' if (h := _href(c['ticker'])) else ""}</p></header>
<div class="tags">{"".join(f'<span class="tag">{esc(t)}</span>' for t in tags)}</div>
{chart or f'<p class="note">{esc(c.get("price_note") or "no prices from Yahoo")}</p>'}
<div class="cols"><section aria-label="Analysts"><h4 class="pl">Analysts</h4>{analyst_block(c)}{realistic_line(c, fc)}</section>
<section aria-label="Results"><h4 class="pl">Results</h4>{results_table(c)}</section></div>
{brief_block(c)}
<section class="impact" aria-label="Portfolio before and after"><h4 class="pl">Your portfolio, before and after</h4>{impact_block(c, default_amount)}{lump_line(c, fc, default_amount)}</section></article>"""


def alert_banner(items: list, href_base: str) -> str:
    if not items:
        return ""
    was = lambda a: f", was {esc(a['before'])}" if a.get("before") else ""
    lis = "".join(f'<li><a href="{href_base}{esc(a["ticker"])}">{esc(a["name"])} ({esc(a["ticker"])})</a> is now {esc(a["now"])}'
                  f'{was(a)}.</li>' for a in items)
    return (f'<div class="container"><section class="alerts" aria-labelledby="alerts-h">'
            f'<h2 id="alerts-h">Crossed a threshold since the last run</h2><ul>{lis}</ul></section></div>')


def finder() -> str:
    from ..server import DISCOVER
    chips = "".join(f'<button type="button" class="chip" data-list="{k}">{esc(v)}</button>' for k, v in DISCOVER.items())
    return f"""<section class="finder" aria-labelledby="find-h"><h2 id="find-h">Find a stock or fund</h2>
<form role="search"><div class="field"><label for="q">Name or ticker</label>
<input id="q" name="q" type="search" placeholder="for example Nokia, KNEBV.HE or health care ETF" autocomplete="off"></div>
<button type="submit" class="btn">Search</button></form>
<div><p class="pl">Or browse Yahoo lists</p><div class="chips">{chips}</div></div>
<p class="offline" hidden>Search needs the local server. Run <code>uv run nordic-desk serve</code> and open the address it prints.</p>
<p role="status" class="note" aria-live="polite"></p><ul class="hits"></ul></section>"""


def plan_section(plan: dict | None) -> str:
    if not plan:
        return ""
    b, a = plan["before"], plan["after"]
    rows = "".join(f'<tr><th scope="row"><a class="tk" href="#{esc(t)}">{esc(t)}</a></th><td class="num r">€{v:,.0f}</td></tr>'.replace(",", chr(0x202F))
                   for t, v in sorted(plan["split"].items(), key=lambda kv: -kv[1]))
    eff = "".join(f'<tr><th scope="row">{lab}</th><td class="num r">{f(b[k])}</td><td class="num r">{f(a[k])}</td></tr>'
                  for lab, k, f in (("Volatility", "vol", lambda x: pct(x, 1, False)), ("Technology share", "tech", lambda x: pct(x, 1, False)),
                                    ("Worst fall, past year", "worst", pct), ("Effective holdings", "enb", lambda x: f"{x:.1f}")))
    note = f'<p class="note">{esc(plan["note"])}.</p>' if plan.get("note") else ""
    o = plan.get("optimised")
    if o:
        orows = "".join(f'<tr><th scope="row"><a class="tk" href="#{esc(t)}">{esc(t)}</a></th><td class="num r">€{v:,.0f}</td></tr>'.replace(",", chr(0x202F))
                        for t, v in sorted(o["split"].items(), key=lambda kv: -kv[1]))
        note += (f'<h3>Optimiser</h3><p class="sub">The lowest-volatility mix found in one go (SLSQP): volatility {pct(o["after"]["vol"], 1, False)}, '
                 f'technology {pct(o["after"]["tech"], 1, False)}.</p><div class="table-wrap"><table><thead><tr><th scope="col">Idea</th>'
                 f'<th scope="col" class="r">Amount</th></tr></thead><tbody>{orows}</tbody></table></div>'
                 + (f'<p class="note">{esc(o["note"])}.</p>' if o.get("note") else ""))
    skip = f'<p class="note">Left out (no year of prices or other currency): {esc(", ".join(plan["skipped"]))}.</p>' if plan.get("skipped") else ""
    return f"""<section class="container sec" aria-labelledby="plan-h"><div class="panel"><h2 id="plan-h">Suggested split of €{plan["amount"]:,.0f} new money</h2>
<p class="sub">Each €500 goes to the idea that lowers volatility most, keeping technology at or under {pct(plan["tech_max"], 0, False)} where possible. Past year of prices; not a forecast.</p>
<div class="cols"><div class="table-wrap"><table><thead><tr><th scope="col">Idea</th><th scope="col" class="r">Amount</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="table-wrap"><table><thead><tr><th scope="col">Portfolio</th><th scope="col" class="r">Now</th><th scope="col" class="r">After</th></tr></thead><tbody>{eff}</tbody></table></div></div>
{note}{skip}</div></section>""".replace(f"€{plan['amount']:,.0f}", "€" + f"{plan['amount']:,.0f}".replace(",", chr(0x202F)))


def idea_row(c: dict, fc: dict | None) -> str:
    """The compact one-line summary that opens into the full card."""
    a = c.get("analysts") or {}
    up, tm = a.get("upside"), a.get("target_mean")
    price = money(tm / (1 + up), c.get("currency")) if tm and up is not None and up > -1 else "–"
    real = pct(up - fc["targets"]["rates"]["overshoot"], 0) if fc and up is not None else "–"
    exp = ((fc or {}).get("expected") or {}).get(c["ticker"])
    status = a.get("status") or "no analyst view"
    return (f'<span class="nm"><b>{esc(c["name"])}</b><span class="tk">{esc(c["ticker"])}</span></span>'
            f'<span class="num r" data-l="Price">{esc(price)}</span>'
            f'<span class="num r" data-l="Analyst upside">{pct(up, 0) if up is not None else "–"}</span>'
            f'<span class="num r" data-l="Realistic">{real}</span>'
            f'<span class="num r" data-l="Expected 12 m">{pct(exp["combined"], 1) if exp and exp.get("combined") is not None else "–"}</span>'
            f'<span class="st"><span class="status {STATUS_CLASS.get(status, "flat")}">{esc(status.capitalize())}</span></span>')


def cards_page(doc: dict, plan: dict | None = None, forecasts: dict | None = None) -> str:
    rows, tabs, shown = [], [], set()
    amount = doc.get("meta", {}).get("default_amount")
    for key, title in GROUPS:
        tickers = [t for t in doc.get("groups", {}).get(key, []) if t in doc["cards"] and t not in shown]  # each card once
        shown.update(tickers)
        if tickers:
            tabs.append(f'<button type="button" data-g="{key}" aria-pressed="{str(key == "growth").lower()}">{title} <span class="n">{len(tickers)}</span></button>')
            rows += [f'<details class="idea" data-group="{key}"><summary>{idea_row(doc["cards"][t], forecasts)}</summary>'
                     f'{card_html(doc["cards"][t], amount, forecasts)}</details>' for t in tickers]
    tabs.sort(key=lambda b: 'data-g="growth"' not in b)  # the owner's main area first; dedupe order above stays as it was
    if tabs:
        tabs.append(f'<button type="button" data-g="all" aria-pressed="false">All <span class="n">{len(shown)}</span></button>')
    head = ('<div class="idea-head" aria-hidden="true"><span>Stock</span><span class="r">Price</span><span class="r">Analyst upside</span>'
            '<span class="r">Realistic</span><span class="r">Expected 12 m</span><span>Status</span></div>')
    found = '<button type="button" data-g="found" aria-pressed="false" hidden>Found now <span class="n">0</span></button>'
    groups = [f'<section class="container sec ideas" aria-label="Ideas"><div class="tabs" role="group" aria-label="Idea groups">{found}{"".join(tabs)}</div>'
              f'{head}<div class="idea-list" id="idea-list">{"".join(rows)}</div>'
              '<p class="note">Click a row to open the full card: chart, analysts, results, news brief and what it does to your portfolio.</p></section>']
    errors = doc.get("errors") or {}
    banner = alert_banner(doc.get("alerts") or [], "#")
    err = (f'<p class="container errors">Skipped: {esc("; ".join(f"{t} ({e})" for t, e in errors.items()))}</p>' if errors else "")
    body = f"""<header class="bar"><div class="container"><a class="mark" href="index.html" aria-label="Huurre, home">Huurre</a>
<nav aria-label="Views">{nav("Ideas")}</nav></div></header>
<main><div class="container sec"><h1>Ideas and search</h1><p class="sub">Analyst views and what each would do to your portfolio. Prices and targets in the listing currency, portfolio numbers in euros. Data from Yahoo Finance, close {day(doc["meta"]["close"])}.</p></div>
{banner}{plan_section(plan)}<div class="container">{finder()}</div>
{"".join(groups)}{err}</main>
<footer class="foot"><div class="container"><p>Buy threshold: the price that leaves the configured margin of upside to the analysts' mean target. Sell threshold: the mean target. Ideas come from config/ideas.toml and are a list to edit, not recommendations.</p><p>Not investment advice.</p></div></footer>"""
    return page("Huurre ideas", "Search results and ideas with analyst signals and portfolio impact.", "huurre",
                "P3 H3 E3 S3 R3 V2 · weakest: V, a card holds many numbers; the status line and the effect column carry the read", CSS, body, JS)
