"""Build three dashboard mockup directions from real Yahoo data in data.json.

Everything is rendered to static HTML/SVG here, so every page reads with scripting off;
a small inline script only switches the selected stock (URL hash) and the compare set.
"""
import json, math, datetime as dt, html, pathlib

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "mock"
OUT.mkdir(exist_ok=True)
D = json.load(open(ROOT / "data.json"))
S, INFO = D["series"], D["info"]
TICK = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA"]
HELD = ["AAPL", "MSFT", "NVDA", "JPM", "COST", "LLY"]   # example portfolio, see PORT_NOTE
PER_HOLDING_EUR = 2000.0
DEFAULT_PICK = "NVDA"
DEFAULT_CMP = ["NVDA", "AVGO", "MSFT"]

dates = S["SPY"]["dates"]
for t in TICK:
    assert S[t]["dates"] == dates, t

# EURUSD (USD per EUR) carried forward onto the US trading dates
fx_raw = dict(zip(S["EURUSD=X"]["dates"], S["EURUSD=X"]["close"]))
fx, last_fx = [], None
for d in dates:
    if d in fx_raw:
        last_fx = fx_raw[d]
    if last_fx is None:
        last_fx = S["EURUSD=X"]["close"][0]
    fx.append(last_fx)
FX_NOW = S["EURUSD=X"]["close"][-1]
FX_NOW_DATE = S["EURUSD=X"]["dates"][-1]

ytd_base_i = max(i for i, d in enumerate(dates) if d < "2026-01-01")
spy = S["SPY"]["close"]


def logrets(c):
    return [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]


def stats(t):
    c = S[t]["close"]
    r, rs = logrets(c), logrets(spy)
    mr, ms = sum(r) / len(r), sum(rs) / len(rs)
    cov = sum((a - mr) * (b - ms) for a, b in zip(r, rs)) / (len(r) - 1)
    var = sum((b - ms) ** 2 for b in rs) / (len(rs) - 1)
    r21 = r[-21:]
    m21 = sum(r21) / 21
    vol = math.sqrt(sum((x - m21) ** 2 for x in r21) / 20) * math.sqrt(252)
    peak, mdd = c[0], 0.0
    for x in c:
        peak = max(peak, x)
        mdd = min(mdd, x / peak - 1)
    hi, lo = max(c), min(c)
    return dict(
        last=c[-1], prev=c[-2], d1=c[-1] / c[-2] - 1, w1=c[-1] / c[-6] - 1, m1=c[-1] / c[-22] - 1,
        m3=c[-1] / c[-64] - 1, m6=c[-1] / c[-127] - 1, ytd=c[-1] / c[ytd_base_i] - 1, y1=c[-1] / c[0] - 1,
        hi=hi, lo=lo, pos=(c[-1] - lo) / (hi - lo), vol=vol, mdd=mdd, beta=cov / var,
    )


ST = {t: stats(t) for t in TICK + ["SPY"]}

# ---- example portfolio: EUR 2 000 into each of six names at the close of the first date ----
shares = {t: PER_HOLDING_EUR * fx[0] / S[t]["close"][0] for t in HELD}
pv = [sum(shares[t] * S[t]["close"][i] for t in HELD) / fx[i] for i in range(len(dates))]
pv_usd = [sum(shares[t] * S[t]["close"][i] for t in HELD) for i in range(len(dates))]
COST = PER_HOLDING_EUR * len(HELD)
P = dict(
    value=pv[-1], day=pv[-1] - pv[-2], day_pct=pv[-1] / pv[-2] - 1, ret=pv[-1] / COST - 1,
    ret_usd=pv_usd[-1] / pv_usd[0] - 1, fx_effect=(pv[-1] / COST - 1) - (pv_usd[-1] / pv_usd[0] - 1),
    spy_day=ST["SPY"]["d1"], spy_y1_eur=(spy[-1] / fx[-1]) / (spy[0] / fx[0]) - 1,
)
weights = {t: shares[t] * S[t]["close"][-1] / fx[-1] / pv[-1] for t in HELD}
first_d = dt.date.fromisoformat(dates[0])
last_d = dt.date.fromisoformat(dates[-1])
PORT_NOTE = (f"Example portfolio, not real holdings: €2,000 put into each of six stocks at the close on "
             f"{first_d:%-d %b %Y}" if False else
             f"Example portfolio, not real holdings: €2,000 put into each of six stocks at the close on "
             f"{first_d.day} {first_d:%b %Y}, valued in euros at Yahoo's EUR/USD rate.")

# ---- formatting ----
MINUS = "−"


def pct(x, d=1, sign=True):
    s = f"{abs(x) * 100:.{d}f}%"
    if not sign:
        return s
    return ("+" if x > 0 else MINUS if x < 0 else "") + s


def eur(x, d=0, sign=False):
    s = f"€{abs(x):,.{d}f}".replace(",", " ")
    if sign:
        return ("+" if x > 0 else MINUS if x < 0 else "") + s
    return s


def usd(x, d=2):
    return f"${x:,.{d}f}".replace(",", " ")


def cls(x):
    return "up" if x > 0 else "down" if x < 0 else "flat"


def big(n):
    if n is None:
        return None
    for unit, v in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if n >= v:
            return f"${n / v:.2f} {unit}"
    return f"${n:,.0f}"


def esc(s):
    return html.escape(str(s))


def name(t):
    n = INFO.get(t, {}).get("shortName") or t
    for cut in (" Corporation", ", Inc.", " Inc.", " Incorporated", " & Co.", " Platforms, Inc."):
        n = n.replace(cut, "")
    return n.title() if n.isupper() else n


MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# ---- SVG ----


def scale(vals, lo, hi, a, b):
    span = (hi - lo) or 1
    return [a + (v - lo) / span * (b - a) for v in vals]


def path(xs, ys):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))


def spark(vals, w=120, h=32, kind=None):
    kind = kind or cls(vals[-1] - vals[0])
    xs = scale(range(len(vals)), 0, len(vals) - 1, 1, w - 1)
    ys = scale(vals, min(vals), max(vals), h - 2, 2)
    return (f'<svg class="spark {kind}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true">'
            f'<path d="{path(xs, ys)}"/></svg>')


def nice_ticks(lo, hi, n=4):
    span = hi - lo
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=10 * mag)
    start = math.ceil(lo / step) * step
    out, v = [], start
    while v <= hi + 1e-9:
        out.append(v)
        v += step
    return out


def month_ticks():
    out, seen = [], set()
    for i, d in enumerate(dates):
        k = d[:7]
        if k not in seen:
            seen.add(k)
            if i > 3:
                out.append((i, MONTHS[int(d[5:7]) - 1]))
    return out


def line_chart(series, w=720, h=280, fmt=lambda v: f"{v:.0f}", label="", every=2, base=None):
    """series: list of (values, css class, data-t or None). One y axis, 3-5 hairline grid lines."""
    L, R, T, B = 52, 12, 12, 28
    allv = [v for s, _, _ in series for v in s]
    lo, hi = min(allv), max(allv)
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    n = len(series[0][0])
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">']
    for v in nice_ticks(lo, hi):
        y = scale([v], lo, hi, h - B, T)[0]
        out.append(f'<line class="grid" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                   f'<text class="ax" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{esc(fmt(v))}</text>')
    if base is not None and lo < base < hi:
        y = scale([base], lo, hi, h - B, T)[0]
        out.append(f'<line class="base" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>')
    for k, (i, m) in enumerate(month_ticks()):
        if k % every:
            continue
        x = scale([i], 0, n - 1, L, w - R)[0]
        out.append(f'<text class="ax" x="{x:.1f}" y="{h - 8}" text-anchor="middle">{m}</text>')
    xs = scale(range(n), 0, n - 1, L, w - R)
    for vals, c, t in series:
        ys = scale(vals, lo, hi, h - B, T)
        dt_ = f' data-t="{t}"' if t else ""
        out.append(f'<path class="ln {c}"{dt_} d="{path(xs, ys)}"/>')
    out.append("</svg>")
    return "".join(out)


def rangebar(t):
    s = ST[t]
    return (f'<span class="range" style="--pos:{s["pos"]:.3f}" '
            f'title="52-week closing range {usd(s["lo"])} to {usd(s["hi"])}">'
            f'<span class="range-mark"></span></span>')


def rebased(t, start=0):
    c = S[t]["close"][start:]
    return [v / c[0] * 100 for v in c]

# ---- shared components ----


def deep_dive(t, hidden):
    s, i = ST[t], INFO.get(t, {})
    earn = i.get("earningsTimestamp")
    earn_s = None
    if earn:
        ed = dt.datetime.fromtimestamp(earn, dt.timezone.utc) + dt.timedelta(hours=2)
        earn_s = f"{ed.day} {ed:%b %Y}, {ed:%H:%M}"
    dy = i.get("dividendYield")
    rows = [
        ("Market cap", big(i.get("marketCap"))),
        ("P/E, trailing", f'{i["trailingPE"]:.1f}' if i.get("trailingPE") else None),
        ("P/E, forward", f'{i["forwardPE"]:.1f}' if i.get("forwardPE") else None),
        ("Dividend yield", f"{dy:.2f}%" if dy else "none"),
        ("Beta vs SPY, 1 year", f'{s["beta"]:.2f}'),
        ("Volatility, 21 days", pct(s["vol"], 0, False)),
        ("Worst fall, 1 year", pct(s["mdd"], 1)),
        ("Earnings, Helsinki time", earn_s),
        ("Sector", i.get("sector")),
    ]
    dl = "".join(f'<div><dt>{k}</dt><dd class="num">{esc(v) if v else "<span class=missing>not reported</span>"}</dd></div>'
                 for k, v in rows)
    held = ""
    if t in HELD:
        val = shares[t] * s["last"] / FX_NOW
        held = (f'<p class="held">You hold {shares[t]:.2f} shares, worth {eur(val)}, '
                f'{pct(weights[t], 1, False)} of the example portfolio.</p>')
    chart = line_chart([(S[t]["close"], "main", None), (
        [v * S[t]["close"][0] / spy[0] for v in spy], "ref", None)],
        label=f"{t} daily close for one year, with SPY scaled to the same start",
        fmt=lambda v: f"${v:,.0f}")
    hid = " hidden" if hidden else ""
    return f"""
<article class="dive" data-panel="{t}" aria-labelledby="dive-{t}"{hid}>
  <header class="dive-head">
    <div>
      <h3 id="dive-{t}">{esc(name(t))}</h3>
      <p class="sub"><span class="tk">{t}</span> {esc(i.get("industry") or "")}</p>
    </div>
    <p class="quote"><span class="px num">{usd(s["last"])}</span>
      <span class="chg num {cls(s["d1"])}">{pct(s["d1"], 2)}</span></p>
  </header>
  <div class="periods">
    {''.join(f'<div><span class="pl">{k}</span><span class="num {cls(v)}">{pct(v)}</span></div>' for k, v in
             (("1 week", s["w1"]), ("1 month", s["m1"]), ("3 months", s["m3"]), ("Year to date", s["ytd"]), ("1 year", s["y1"])))}
  </div>
  <figure class="chart-fig">
    {chart}
    <figcaption><span class="key main"></span>{t} close <span class="key ref"></span>SPY, same start</figcaption>
  </figure>
  {held}
  <dl class="facts">{dl}</dl>
</article>"""


def pe(t):
    v = INFO.get(t, {}).get("trailingPE")
    return f"{v:.1f}" if v else "none"


def compare_block(heading_level="h2"):
    cmp_series = [(rebased(t), "cmp-line" + (f" s{DEFAULT_CMP.index(t) + 1}" if t in DEFAULT_CMP else ""), t) for t in TICK]
    cmp_series.append((rebased("SPY"), "ref", None))
    chart = line_chart(cmp_series, w=900, h=300, fmt=lambda v: f"{v:.0f}", base=100,
                       label="Selected stocks rebased to 100 one year ago, with SPY")
    boxes = "".join(
        f'<label class="chip"><input type="checkbox" name="cmp" value="{t}"{" checked" if t in DEFAULT_CMP else ""}>'
        f'<span class="sw"></span>{t}</label>' for t in TICK)
    rows = "".join(
        f'<tr data-row="{t}"{"" if t in DEFAULT_CMP else " hidden"}><th scope="row"><span class="sw {("s" + str(DEFAULT_CMP.index(t) + 1)) if t in DEFAULT_CMP else ""}"></span>{t}</th>'
        f'<td class="num {cls(ST[t]["m1"])}">{pct(ST[t]["m1"])}</td><td class="num {cls(ST[t]["m3"])}">{pct(ST[t]["m3"])}</td>'
        f'<td class="num {cls(ST[t]["ytd"])}">{pct(ST[t]["ytd"])}</td><td class="num {cls(ST[t]["y1"])}">{pct(ST[t]["y1"])}</td>'
        f'<td class="num">{pct(ST[t]["vol"], 0, False)}</td><td class="num">{pct(ST[t]["mdd"])}</td>'
        f'<td class="num">{ST[t]["beta"]:.2f}</td>'
        f'<td class="num">{pe(t)}</td></tr>'
        for t in TICK)
    spy_row = (f'<tr class="ref-row"><th scope="row"><span class="sw ref"></span>SPY</th>'
               f'<td class="num">{pct(ST["SPY"]["m1"])}</td><td class="num">{pct(ST["SPY"]["m3"])}</td>'
               f'<td class="num">{pct(ST["SPY"]["ytd"])}</td><td class="num">{pct(ST["SPY"]["y1"])}</td>'
               f'<td class="num">{pct(ST["SPY"]["vol"], 0, False)}</td><td class="num">{pct(ST["SPY"]["mdd"])}</td>'
               f'<td class="num">1.00</td><td class="num">none</td></tr>')
    return f"""
<section class="compare" aria-labelledby="cmp-h">
  <div class="sec-head"><{heading_level} id="cmp-h">Compare</{heading_level}>
    <p class="sub">Pick up to four. Lines start at 100 one year ago.</p></div>
  <fieldset class="chips"><legend class="visually-hidden">Stocks to compare</legend>{boxes}</fieldset>
  <figure class="chart-fig">{chart}</figure>
  <div class="table-wrap"><table class="cmp-table">
    <thead><tr><th scope="col">Ticker</th><th scope="col">1 month</th><th scope="col">3 months</th><th scope="col">Year to date</th>
    <th scope="col">1 year</th><th scope="col">Volatility</th><th scope="col">Worst fall</th><th scope="col">Beta</th><th scope="col">P/E</th></tr></thead>
    <tbody>{rows}{spy_row}</tbody></table></div>
</section>"""


def watch_table(with_range=True, with_spark=True):
    head = ('<th scope="col">Ticker</th><th scope="col" class="r">Last</th><th scope="col" class="r">Today</th>'
            '<th scope="col" class="r">1 month</th><th scope="col" class="r">Year to date</th>'
            + ('<th scope="col">52-week range</th>' if with_range else "") + ('<th scope="col">3 months</th>' if with_spark else ""))
    rows = []
    for t in TICK:
        s = ST[t]
        held = '<span class="own">held</span>' if t in HELD else ""
        sel = ' aria-current="true"' if t == DEFAULT_PICK else ""
        rows.append(
            f'<tr data-t="{t}"{sel}><th scope="row"><a class="pick" href="#{t}" data-pick="{t}"><span class="tk">{t}</span>'
            f'<span class="nm">{esc(name(t))}</span></a>{held}</th>'
            f'<td class="num r">{usd(s["last"])}</td><td class="num r {cls(s["d1"])}">{pct(s["d1"], 2)}</td>'
            f'<td class="num r {cls(s["m1"])}">{pct(s["m1"])}</td><td class="num r {cls(s["ytd"])}">{pct(s["ytd"])}</td>'
            + (f'<td>{rangebar(t)}</td>' if with_range else "")
            + (f'<td>{spark(S[t]["close"][-64:], w=96, kind=cls(s["m3"]))}</td>' if with_spark else "") + '</tr>')
    return f'<div class="table-wrap"><table class="watch"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def holdings_bar():
    segs = "".join(f'<span class="seg s{k % 6 + 1}" style="flex-grow:{weights[t]:.4f}" title="{t} {pct(weights[t], 1, False)}"></span>'
                   for k, t in enumerate(sorted(HELD, key=lambda x: -weights[x])))
    legend = "".join(
        f'<li><span class="sw s{k % 6 + 1}"></span><span class="tk">{t}</span><span class="num">{pct(weights[t], 1, False)}</span>'
        f'<span class="num {cls(ST[t]["d1"])}">{pct(ST[t]["d1"], 2)}</span></li>'
        for k, t in enumerate(sorted(HELD, key=lambda x: -weights[x])))
    return f'<div class="stack" role="img" aria-label="Portfolio weights">{segs}</div><ul class="weights">{legend}</ul>'


def port_chart(w=560, h=200):
    spy_eur = [(spy[i] / fx[i]) / (spy[0] / fx[0]) * COST for i in range(len(dates))]
    return line_chart([(pv, "main", None), (spy_eur, "ref", None)], w=w, h=h, every=3,
                      fmt=lambda v: f"€{v / 1000:.1f}k", base=COST,
                      label="Example portfolio value in euros for one year, with the same money in SPY")


SCRIPT = """
<script>
(() => {
  const pick = t => {
    const p = document.querySelector('[data-panel="' + t + '"]');
    if (!p) return;
    document.querySelectorAll('[data-panel]').forEach(el => { el.hidden = el !== p; });
    document.querySelectorAll('[data-t]').forEach(el => {
      if (el.tagName === 'TR' || el.classList.contains('dot')) el.toggleAttribute('aria-current', el.dataset.t === t);
    });
    document.querySelectorAll('[data-pick]').forEach(el => {
      if (el.tagName === 'BUTTON') el.setAttribute('aria-pressed', String(el.dataset.pick === t));
    });
  };
  const fromHash = () => { const m = location.hash.match(/^#([A-Z]{1,5})$/); if (m) pick(m[1]); };
  document.querySelectorAll('button[data-pick]').forEach(b => b.addEventListener('click', () => { location.hash = b.dataset.pick; }));
  window.addEventListener('hashchange', fromHash); fromHash();

  const boxes = [...document.querySelectorAll('input[name="cmp"]')];
  let order = boxes.filter(b => b.checked).map(b => b.value);
  const paint = () => {
    document.querySelectorAll('.cmp-line').forEach(l => {
      const k = order.indexOf(l.dataset.t);
      l.classList.remove('s1', 's2', 's3', 's4'); if (k >= 0) l.classList.add('s' + (k + 1));
    });
    document.querySelectorAll('[data-row]').forEach(r => {
      const k = order.indexOf(r.dataset.row); r.hidden = k < 0;
      const sw = r.querySelector('.sw'); sw.className = 'sw' + (k >= 0 ? ' s' + (k + 1) : '');
    });
    boxes.forEach(b => {
      const k = order.indexOf(b.value);
      b.nextElementSibling.className = 'sw' + (k >= 0 ? ' s' + (k + 1) : '');
      b.disabled = !b.checked && order.length >= 4;
    });
  };
  boxes.forEach(b => b.addEventListener('change', () => {
    order = b.checked ? [...order, b.value] : order.filter(v => v !== b.value); paint();
  }));
  paint();
})();
</script>"""

# ---- CSS shared by all three (structure only; every colour and face comes from the page's tokens) ----

SCALE = """
  --space-2xs: 4px; --space-xs: 8px; --space-sm: 12px; --space-md: 16px; --space-lg: 24px; --space-xl: 40px; --space-2xl: 64px;
  --text-xs: 0.8125rem; --text-sm: 0.875rem; --text-md: 1rem; --text-lg: 1.2rem; --text-xl: 1.44rem; --text-2xl: 1.728rem; --text-3xl: 2.488rem;
  --dur-micro: 120ms; --dur-short: 220ms; --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --container: 1440px; --gutter: 40px; --gap: 24px;"""

BASE = """
*, *::before, *::after { box-sizing: border-box; }
html, body { overflow-x: clip; }
html { scrollbar-color: var(--color-rule-2) var(--color-paper); }
body { caret-color: var(--color-accent); }
body { margin: 0; background: var(--color-paper); color: var(--color-ink); font-family: var(--font-body); font-size: var(--text-md); line-height: 1.5; -webkit-font-smoothing: antialiased; }
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

/* top bar */
.bar { border-bottom: var(--rule-hair) solid var(--color-rule); background: var(--color-paper-2); }
.bar .container { display: flex; align-items: center; gap: var(--space-lg); min-height: 60px; flex-wrap: wrap; }
.mark { font-family: var(--font-display); font-weight: var(--display-weight); font-size: var(--text-lg); text-decoration: none; letter-spacing: var(--tracking-display); }
.bar nav { display: flex; gap: var(--space-2xs); }
.bar nav a { padding: var(--space-2xs) var(--space-sm); border-radius: var(--radius-pill); text-decoration: none; color: var(--color-ink-2); min-height: 36px; display: inline-flex; align-items: center; }
.bar nav a:hover { background: var(--color-paper-3); color: var(--color-ink); }
.bar nav a[aria-current] { background: var(--color-paper-3); color: var(--color-ink); }
.clock { margin-inline-start: auto; display: flex; gap: var(--space-lg); font-size: var(--text-sm); color: var(--color-muted); flex-wrap: wrap; }
.clock b { color: var(--color-ink); font-weight: 500; }
.search { min-height: 36px; width: 14rem; padding: 0 var(--space-sm); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); background: var(--color-paper); }
.search::placeholder { color: var(--color-muted); }
.search:hover { border-color: var(--color-muted); }
.search:focus-visible { outline-offset: -2px; }

/* tables */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: var(--space-xs) var(--space-sm); text-align: start; border-bottom: var(--rule-hair) solid var(--color-rule); white-space: nowrap; vertical-align: middle; }
thead th { font-weight: 500; font-size: var(--text-sm); color: var(--color-muted); }
.r { text-align: end; }
tbody th { font-weight: 400; }
.watch tbody tr { transition: background-color var(--dur-micro) var(--ease-out); }
.watch tbody tr:hover { background: var(--color-paper-2); }
.watch tbody tr[aria-current] { background: var(--color-sel); }
.pick { display: inline-flex; flex-direction: column; text-decoration: none; min-height: 44px; justify-content: center; }
.pick:hover .nm { color: var(--color-ink); text-decoration: underline; }
.nm { font-size: var(--text-sm); color: var(--color-muted); max-width: 16ch; overflow: hidden; text-overflow: ellipsis; }
.own { margin-inline-start: 8px; font-size: var(--text-xs); color: var(--color-own); border: var(--rule-hair) solid currentColor; border-radius: var(--radius-pill); padding: 0 var(--space-2xs); vertical-align: top; }
th:has(.own) { display: flex; align-items: center; }

/* 52-week range */
.range { position: relative; display: block; width: 88px; height: 14px; }
.range::before { content: ""; position: absolute; inset: 6px 0 auto; height: 2px; background: var(--color-rule-2); }
.range-mark { position: absolute; top: 1px; left: calc(var(--pos) * 100% - 1.5px); width: 3px; height: 12px; background: var(--color-ink); }

/* svg */
.spark path { fill: none; stroke-width: 1.5; stroke: var(--color-muted); }
.spark.up path { stroke: var(--color-up); } .spark.down path { stroke: var(--color-down); }
.chart { width: 100%; height: auto; overflow: visible; }
.chart .grid { stroke: var(--color-rule); stroke-width: 1; }
.chart .base { stroke: var(--color-rule-2); stroke-width: 1; }
.chart .ax { fill: var(--color-muted); font-family: var(--font-num); font-size: 11px; }
.chart .ln { fill: none; stroke-width: 2; stroke-linejoin: round; }
.chart .main { stroke: var(--color-line); }
.chart .ref { stroke: var(--color-muted); stroke-width: 1.5; }
.cmp-line { stroke: transparent; }
.s1 { --c: var(--color-s1); } .s2 { --c: var(--color-s2); } .s3 { --c: var(--color-s3); } .s4 { --c: var(--color-s4); }
.s5 { --c: var(--color-s5); } .s6 { --c: var(--color-s6); }
.cmp-line.s1, .cmp-line.s2, .cmp-line.s3, .cmp-line.s4 { stroke: var(--c); }
.chart-fig { margin: 0; }
figcaption { display: flex; gap: var(--space-md); align-items: center; margin-top: var(--space-xs); flex-wrap: wrap; }
.key { display: inline-block; width: 14px; height: 2px; margin-inline-end: -8px; }
.key.main { background: var(--color-line); } .key.ref { background: var(--color-muted); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: var(--c, var(--color-rule-2)); margin-inline-end: 8px; }
.sw.ref { background: var(--color-muted); }

/* deep dive */
.dive { display: grid; gap: var(--space-md); }
.dive-head { display: flex; justify-content: space-between; align-items: flex-end; gap: var(--space-md); flex-wrap: wrap; }
.dive-head .tk { font-size: var(--text-md); color: var(--color-muted); font-weight: 400; }
.quote { display: flex; gap: var(--space-sm); align-items: baseline; }
.px { font-size: var(--text-2xl); }
.periods { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); border-block: var(--rule-hair) solid var(--color-rule); }
.periods > div { display: grid; padding: var(--space-xs) 0; }
.periods > div + div { border-inline-start: var(--rule-hair) solid var(--color-rule); padding-inline-start: var(--space-sm); }
.facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 12rem), 1fr)); gap: 0 var(--space-lg); margin: 0; }
.facts > div { display: flex; justify-content: space-between; gap: var(--space-sm); padding: var(--space-xs) 0; border-bottom: var(--rule-hair) solid var(--color-rule); }
.facts dt { color: var(--color-muted); font-size: var(--text-sm); }
.facts dd { margin: 0; text-align: end; }
.held { padding: var(--space-sm); border: var(--rule-hair) solid var(--color-own); border-radius: var(--radius-card); }

/* compare */
.chips { border: 0; padding: 0; margin: 0 0 var(--space-md); display: flex; flex-wrap: wrap; gap: var(--space-xs); }
.chip { display: inline-flex; align-items: center; min-height: 36px; padding: 0 var(--space-sm); border: var(--rule-hair) solid var(--color-rule-2); border-radius: var(--radius-pill); cursor: pointer; font-size: var(--text-sm); transition: border-color var(--dur-micro) var(--ease-out), background-color var(--dur-micro) var(--ease-out); }
.chip:hover { border-color: var(--color-muted); }
.chip input { position: absolute; opacity: 0; width: 1px; height: 1px; }
.chip:has(input:checked) { background: var(--color-paper-3); border-color: var(--color-ink-2); }
.chip:has(input:focus-visible) { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.chip:has(input:disabled) { opacity: 0.55; cursor: not-allowed; }
.chip:active { transform: translateY(1px); }
.cmp-table td, .cmp-table th { text-align: end; } .cmp-table th:first-child { text-align: start; }
.ref-row { color: var(--color-muted); }

/* portfolio */
.stack { display: flex; height: 14px; gap: 2px; margin-block: var(--space-sm); }
.seg { display: block; background: var(--c); }
.seg.s1, .seg.s2, .seg.s3, .seg.s4, .seg.s5, .seg.s6 { background: var(--c); }
.weights { list-style: none; margin: 0; padding: 0; display: grid; }
.weights li { display: grid; grid-template-columns: auto 1fr auto auto; gap: var(--space-sm); align-items: center; padding: var(--space-xs) 0; border-bottom: var(--rule-hair) solid var(--color-rule); }
.weights li .num:last-child { min-width: 5.5rem; text-align: end; }

/* states */
.states { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--gap); }
.state { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); display: grid; gap: var(--space-sm); align-content: start; min-height: 220px; }
.skel { height: 14px; border-radius: 3px; background: var(--color-paper-3); animation: pulse 1.6s ease-in-out infinite; }
.skel.w60 { width: 60%; } .skel.w80 { width: 80%; } .skel.w40 { width: 40%; }
@keyframes pulse { 50% { opacity: 0.45; } }
.btn { display: inline-flex; align-items: center; justify-content: center; min-height: 36px; padding: 0 var(--space-md); border-radius: var(--radius-pill); border: var(--rule-hair) solid transparent; background: var(--color-accent); color: var(--color-accent-ink); cursor: pointer; font-weight: 500; justify-self: start; transition: background-color var(--dur-micro) var(--ease-out); }
.btn:hover { background: var(--color-accent-deep); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }
.btn.ghost { background: transparent; color: var(--color-ink); border-color: var(--color-rule-2); }
.btn.ghost:hover { background: var(--color-paper-3); }

.foot { border-top: var(--rule-hair) solid var(--color-rule); margin-top: var(--space-2xl); padding-block: var(--space-lg); color: var(--color-muted); font-size: var(--text-sm); }
.foot .container { display: grid; gap: var(--space-2xs); }

@media (max-width: 60rem) {
  :root { --gutter: 16px; }
  .states { grid-template-columns: minmax(0, 1fr); }
  .periods { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .clock { margin-inline-start: 0; }
  .search { width: 100%; }
  .watch .nm { display: none; }
  .watch th:first-child, .watch td:first-child { position: sticky; left: 0; background: var(--color-paper); }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition-duration: 0.01ms !important; }
}
"""

FETCH = dt.datetime.strptime(D["fetched_utc"], "%Y-%m-%d %H:%M")
FETCH_HKI = FETCH + dt.timedelta(hours=2)   # EET, UTC+2 in November


def clock():
    return (f'<p class="clock"><span>Prices: US close <b>{last_d.day} {last_d:%b}</b>, 23:00 Helsinki</span>'
            f'<span>New York opens <b>16:30</b> Helsinki time</span>'
            f'<span>EUR/USD <b class="num">{FX_NOW:.4f}</b></span></p>')


def footer():
    return (f'<footer class="foot"><div class="container">'
            f'<p>Prices, company facts and EUR/USD from Yahoo Finance, fetched {FETCH_HKI.day} {FETCH_HKI:%b %Y} '
            f'at {FETCH_HKI:%H:%M} Helsinki time. Returns, volatility, beta and worst fall are computed here from daily closes.</p>'
            f'<p>{esc(PORT_NOTE)}</p><p>A design mockup. Not investment advice.</p></div></footer>')


def page(title, desc, fonts, stamp, tokens, css, body, script=True):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap">
<style>
{stamp}
:root {{{SCALE}
{tokens}
}}
{BASE}
{css}
</style>
</head>
<body>
{body}
{SCRIPT if script else ""}
</body>
</html>"""


def dives():
    return "".join(deep_dive(t, t != DEFAULT_PICK) for t in TICK)


def pick_buttons():
    return '<div class="pickrow" role="group" aria-label="Choose a stock">' + "".join(
        f'<button type="button" class="chip pickbtn" data-pick="{t}" aria-pressed="{str(t == DEFAULT_PICK).lower()}">{t}</button>'
        for t in TICK) + "</div>"


def states_block():
    return f"""
<section class="container sec" aria-labelledby="st-h">
  <div class="sec-head"><h2 id="st-h">Watchlist, other states</h2>
  <p class="sub">The same panel while loading, with nothing in it, and when Yahoo fails.</p></div>
  <div class="states">
    <div class="state" aria-busy="true"><p class="pl">Loading</p><span class="skel w80"></span><span class="skel w60"></span><span class="skel w80"></span><span class="skel w40"></span><span class="skel w60"></span></div>
    <div class="state"><p class="pl">Empty</p><p>Your watchlist has no tickers yet. Add a US ticker such as AAPL to see its price, range and trend here.</p>
      <label class="visually-hidden" for="add-{id(object())}">Ticker</label><button type="button" class="btn">Add a ticker</button></div>
    <div class="state"><p class="pl">Error</p><p>Yahoo did not answer at 13:34. The table shows the close from {last_d.day} {last_d:%b}, so today’s change may be stale.</p>
      <button type="button" class="btn ghost">Try again</button></div>
  </div>
</section>"""

# ======================= Direction 1: Huurre (hoarfrost) =======================


def huurre():
    tokens = """
  color-scheme: light;
  --color-paper: oklch(98.5% 0.004 240); --color-paper-2: oklch(96.5% 0.006 240); --color-paper-3: oklch(92.5% 0.009 240);
  --color-ink: oklch(21% 0.012 250); --color-ink-2: oklch(36% 0.012 250); --color-muted: oklch(50% 0.014 250);
  --color-rule: oklch(90% 0.008 240); --color-rule-2: oklch(80% 0.01 240);
  --color-accent: oklch(46% 0.13 250); --color-accent-deep: oklch(38% 0.12 250); --color-accent-ink: oklch(98.5% 0.004 240);
  --color-focus: oklch(55% 0.16 250); --color-sel: oklch(94.5% 0.025 250);
  --color-own: oklch(52% 0.13 70);
  --color-up: oklch(50% 0.12 165); --color-down: oklch(52% 0.17 25);
  --color-line: oklch(30% 0.03 250);
  --color-s1: oklch(42% 0.14 250); --color-s2: oklch(56% 0.13 70); --color-s3: oklch(55% 0.11 165); --color-s4: oklch(62% 0.13 320);
  --color-s5: oklch(70% 0.06 250); --color-s6: oklch(82% 0.04 250);
  --font-display: "Host Grotesk", ui-sans-serif, system-ui, sans-serif; --font-body: var(--font-display);
  --font-num: "Atkinson Hyperlegible Mono", ui-monospace, monospace;
  --radius-card: 8px; --radius-pill: 6px; --rule-hair: 1px; --tracking-display: -0.02em; --display-weight: 500;"""
    stamp = """/* Hallmark · shape: app screen · genre: modern-minimal · theme: Console (deal 3/3, seed nordic-technical-stock-research-853a·791679f5·2026-11-18·r0), colourway paper, cooled to hoarfrost
 * nav: top bar · signature: the watchlist ledger, 52-week range rule per row · states: full, loading, empty, error · console: paper
 * axes: light/grotesk-sans/cool-blue · posture: restrained · contrast: pass · data: real (Yahoo), portfolio example · v2.0.0 */
/* Hallmark · pre-emit critique: P3 H3 E3 S2 R3 V3 · weakest: S, the ledger carries the screen but the portfolio strip is plain; kept plain on purpose, density first */"""
    css = """
.mark { color: var(--color-accent); }
.strip { display: grid; grid-template-columns: repeat(4, minmax(0, auto)) minmax(0, 1fr); gap: var(--space-xl); align-items: end; padding-block: var(--space-lg); border-bottom: var(--rule-hair) solid var(--color-rule); }
.fig { display: grid; gap: 2px; }
.fig .v { font-family: var(--font-num); font-size: var(--text-2xl); font-variant-numeric: tabular-nums; line-height: 1.1; }
.fig .v.sm { font-size: var(--text-xl); }
.strip .mini { max-width: 420px; justify-self: end; width: 100%; }
.desk { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--gap); padding-block: var(--space-lg); }
.panel { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); background: var(--color-paper); padding: var(--space-md); min-width: 0; }
.panel.flush { padding: 0; }
.panel.flush .sec-head { padding: var(--space-md) var(--space-md) var(--space-xs); }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-sm); }
.watch th:first-child { padding-inline-start: var(--space-md); }
@media (max-width: 90rem) { .watch .nm { display: none; } }
.dive h3 { font-size: var(--text-xl); }
.sec { padding-block: var(--space-lg); }
.compare { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); }
@media (max-width: 75rem) { .desk { grid-template-columns: minmax(0, 1fr); } .strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .strip .mini { grid-column: 1 / -1; justify-self: stretch; max-width: none; } }
"""
    body = f"""
<header class="bar"><div class="container">
  <a class="mark" href="#" aria-label="Huurre, home">Huurre</a>
  <nav aria-label="Views"><a href="#" aria-current="page">Desk</a><a href="#cmp-h">Compare</a><a href="#st-h">States</a></nav>
  <label class="visually-hidden" for="q">Find a US ticker</label><input id="q" class="search" type="search" name="q" placeholder="Find a ticker" autocomplete="off">
  {clock()}
</div></header>
<main>
<h1 class="visually-hidden">Stock desk</h1>
<section class="container strip" aria-label="Example portfolio today">
  <div class="fig"><span class="pl">Example portfolio</span><span class="v">{eur(P["value"])}</span></div>
  <div class="fig"><span class="pl">Overnight</span><span class="v sm {cls(P["day"])}">{eur(P["day"], 0, True)}</span><span class="num {cls(P["day"])}">{pct(P["day_pct"], 2)}</span></div>
  <div class="fig"><span class="pl">Since start, in euros</span><span class="v sm {cls(P["ret"])}">{pct(P["ret"])}</span><span class="note">in dollars {pct(P["ret_usd"])}</span></div>
  <div class="fig"><span class="pl">SPY, same money</span><span class="v sm {cls(P["spy_y1_eur"])}">{pct(P["spy_y1_eur"])}</span><span class="note">overnight {pct(P["spy_day"], 2)}</span></div>
  <figure class="chart-fig mini">{port_chart(w=420, h=120)}</figure>
</section>
<div class="container desk">
  <section class="panel flush" aria-labelledby="wl-h">
    <div class="sec-head"><h2 id="wl-h">Watchlist</h2><p class="sub">12 US stocks. Pick one to open it on the right.</p></div>
    {watch_table()}
  </section>
  <section class="panel" aria-label="Selected stock">{dives()}</section>
</div>
<div class="container sec">{compare_block()}</div>
{states_block()}
</main>
{footer()}"""
    return page("Huurre stock desk", "A light, dense stock desk: watchlist ledger, selected stock and example portfolio.",
                "family=Host+Grotesk:wght@400;500;600&family=Atkinson+Hyperlegible+Mono:wght@400;600",
                stamp, tokens, css, body)

# ======================= Direction 2: Kaamos (polar night) =======================


def momentum_map(w=760, h=460):
    L, R, T, B = 56, 24, 24, 44
    xs_v = [ST[t]["m6"] for t in TICK] + [ST["SPY"]["m6"]]
    ys_v = [ST[t]["m1"] for t in TICK] + [ST["SPY"]["m1"]]
    xlo, xhi = min(xs_v) - 0.06, max(xs_v) + 0.06
    ylo, yhi = min(ys_v) - 0.03, max(ys_v) + 0.03
    X = lambda v: L + (v - xlo) / (xhi - xlo) * (w - L - R)
    Y = lambda v: (h - B) - (v - ylo) / (yhi - ylo) * (h - T - B)
    o = [f'<svg class="chart map" viewBox="0 0 {w} {h}" role="img" aria-label="Momentum map: 6-month return across, 1-month return up, SPY as the crosshair">']
    for v in nice_ticks(xlo, xhi, 5):
        o.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{h - B}"/><text class="ax" x="{X(v):.1f}" y="{h - B + 18}" text-anchor="middle">{pct(v, 0)}</text>')
    for v in nice_ticks(ylo, yhi, 4):
        o.append(f'<line class="grid" x1="{L}" x2="{w - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/><text class="ax" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{pct(v, 0)}</text>')
    sx, sy = X(ST["SPY"]["m6"]), Y(ST["SPY"]["m1"])
    o.append(f'<line class="cross" x1="{sx:.1f}" x2="{sx:.1f}" y1="{T}" y2="{h - B}"/><line class="cross" x1="{L}" x2="{w - R}" y1="{sy:.1f}" y2="{sy:.1f}"/>')
    o.append(f'<text class="q" x="{sx:.1f}" y="{T - 6}" text-anchor="middle">SPY, 6 months</text>'
             f'<text class="q" x="{w - R}" y="{sy - 6:.1f}" text-anchor="end">SPY, 1 month</text>')
    o.append(f'<text class="ax" x="{w - R}" y="{h - 6}" text-anchor="end">6-month return</text>'
             f'<text class="ax" x="{L - 44}" y="{T - 8}">1 month</text>')
    for t in TICK:
        x, y = X(ST[t]["m6"]), Y(ST[t]["m1"])
        ring = f'<circle class="ring" cx="{x:.1f}" cy="{y:.1f}" r="11"/>' if t in HELD else ""
        cur = ' aria-current="true"' if t == DEFAULT_PICK else ""
        o.append(f'<a href="#{t}" class="dot" data-t="{t}"{cur} aria-label="{t}: 6 months {pct(ST[t]["m6"])}, 1 month {pct(ST[t]["m1"])}">'
                 f'{ring}<circle class="pt" cx="{x:.1f}" cy="{y:.1f}" r="6"/>'
                 f'<text class="lb" x="{x + 15:.1f}" y="{y + 4:.1f}">{t}</text></a>')
    o.append("</svg>")
    return "".join(o)


def kaamos():
    tokens = """
  color-scheme: dark;
  --color-paper: oklch(14% 0.014 245); --color-paper-2: oklch(17.5% 0.016 245); --color-paper-3: oklch(22% 0.018 245);
  --color-ink: oklch(95% 0.006 230); --color-ink-2: oklch(84% 0.012 230); --color-muted: oklch(69% 0.016 230);
  --color-rule: oklch(27% 0.014 245); --color-rule-2: oklch(36% 0.016 245);
  --color-accent: oklch(86% 0.16 158); --color-accent-deep: oklch(80% 0.16 158); --color-accent-ink: oklch(18% 0.04 158);
  --color-focus: oklch(86% 0.16 158); --color-sel: oklch(23% 0.03 158);
  --color-own: oklch(84% 0.12 85);
  --color-up: oklch(82% 0.15 158); --color-down: oklch(74% 0.14 20);
  --color-line: oklch(86% 0.16 158);
  --color-s1: oklch(86% 0.16 158); --color-s2: oklch(84% 0.12 85); --color-s3: oklch(76% 0.11 240); --color-s4: oklch(74% 0.14 330);
  --color-s5: oklch(60% 0.06 240); --color-s6: oklch(45% 0.04 240);
  --font-display: "Geologica", ui-sans-serif, system-ui, sans-serif; --font-body: var(--font-display);
  --font-num: "Geologica", ui-sans-serif, system-ui, sans-serif;
  --radius-card: 4px; --radius-pill: 999px; --rule-hair: 1px; --tracking-display: -0.03em; --display-weight: 300;"""
    stamp = """/* Hallmark · shape: app screen · genre: modern-minimal · theme: Vantage (deal 1/3, seed nordic-technical-stock-research-853a·791679f5·2026-11-18·r0), signal moved from lime to aurora green
 * nav: top bar · signature: the momentum map, 12 stocks placed by 6-month and 1-month return around SPY · states: full (loading, empty, error drawn on Huurre) · vantage: terrain/steel
 * axes: dark/grotesk-sans/chromatic-green · posture: restrained · contrast: pass · data: real (Yahoo), portfolio example · v2.0.0 */
/* Hallmark · pre-emit critique: P3 H3 E3 S3 R2 V3 · weakest: R, a dark finance screen is a familiar look; the map and the polar-night ground carry it instead of glow */"""
    css = """
.mark { font-weight: 400; }
.frame { position: relative; border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); padding: var(--space-md); background: var(--color-paper-2); min-width: 0; }
.frame::before, .frame::after { content: ""; position: absolute; width: 10px; height: 10px; border-color: var(--color-accent); border-style: solid; }
.frame::before { top: -1px; left: -1px; border-width: 1px 0 0 1px; } .frame::after { bottom: -1px; right: -1px; border-width: 0 1px 1px 0; }
.top { display: grid; grid-template-columns: minmax(0, 8fr) minmax(0, 4fr); gap: var(--gap); padding-block: var(--space-lg); }
.sec-head { display: flex; justify-content: space-between; align-items: baseline; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-sm); }
.map .cross { stroke: var(--color-rule-2); stroke-width: 1; }
.map .q { fill: var(--color-muted); font-size: 12px; font-family: var(--font-body); }
.map .pt { fill: var(--color-ink-2); transition: fill var(--dur-micro) var(--ease-out); }
.map .ring { fill: none; stroke: var(--color-own); stroke-width: 1.5; }
.map .lb { fill: var(--color-ink-2); font-family: var(--font-num); font-size: 13px; }
.map .dot:hover .pt, .map .dot:focus-visible .pt { fill: var(--color-ink); }
.map .dot[aria-current] .pt { fill: var(--color-accent); }
.map .dot[aria-current] .lb { fill: var(--color-ink); font-weight: 600; }
.map .dot:focus-visible { outline: none; } .map .dot:focus-visible .lb { text-decoration: underline; }
.big { font-size: var(--text-3xl); font-weight: 300; letter-spacing: -0.03em; line-height: 1; }
.port { display: grid; gap: var(--space-sm); align-content: start; }
.port .row { display: flex; gap: var(--space-lg); flex-wrap: wrap; }
.port .row > div { display: grid; }
.lower { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--gap); }
.watch td, .watch th { padding-block: var(--space-2xs); }
.watch .nm { display: none; }
.sec { padding-block: var(--space-lg); }
.legend { display: flex; gap: var(--space-lg); flex-wrap: wrap; }
.legend span { display: inline-flex; align-items: center; gap: var(--space-xs); }
.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: var(--color-ink-2); }
.legend i.own { background: none; border: 1.5px solid var(--color-own); }
.legend i.cur { background: var(--color-accent); }
@media (max-width: 75rem) { .top, .lower { grid-template-columns: minmax(0, 1fr); } }
"""
    body = f"""
<header class="bar"><div class="container">
  <a class="mark" href="#" aria-label="Kaamos, home">kaamos</a>
  <nav aria-label="Views"><a href="#" aria-current="page">Map</a><a href="#wl-h">Watchlist</a><a href="#cmp-h">Compare</a></nav>
  <label class="visually-hidden" for="q">Find a US ticker</label><input id="q" class="search" type="search" name="q" placeholder="Find a ticker" autocomplete="off">
  {clock()}
</div></header>
<main>
<h1 class="visually-hidden">Momentum map</h1>
<div class="container top">
  <section class="frame" aria-labelledby="map-h">
    <div class="sec-head"><div><h2 id="map-h">Where the watchlist stands</h2><p class="sub">Up and right is ahead of SPY over both the last month and six months.</p></div>
      <p class="legend sub"><span><i class="cur"></i>selected</span><span><i class="own"></i>held</span><span><i></i>watched</span></p></div>
    {momentum_map()}
  </section>
  <section class="frame port" aria-labelledby="pf-h">
    <h2 id="pf-h">Example portfolio</h2>
    <p class="big num">{eur(P["value"])}</p>
    <div class="row">
      <div><span class="pl">Overnight</span><span class="num {cls(P["day"])}">{eur(P["day"], 0, True)} ({pct(P["day_pct"], 2)})</span></div>
      <div><span class="pl">Since start</span><span class="num {cls(P["ret"])}">{pct(P["ret"])}</span></div>
      <div><span class="pl">Currency effect</span><span class="num {cls(P["fx_effect"])}">{pct(P["fx_effect"])}</span></div>
    </div>
    <figure class="chart-fig">{port_chart(w=440, h=170)}<figcaption><span class="key main"></span>portfolio, euros <span class="key ref"></span>SPY, same money</figcaption></figure>
    {holdings_bar()}
  </section>
</div>
<div class="container lower">
  <section class="frame" aria-label="Selected stock">{dives()}</section>
  <section class="frame" aria-labelledby="wl-h"><div class="sec-head"><h2 id="wl-h">Watchlist</h2></div>{watch_table(with_range=False, with_spark=False)}</section>
</div>
<div class="container sec"><div class="frame">{compare_block()}</div></div>
</main>
{footer()}"""
    return page("Kaamos stock map", "A dark polar-night stock screen built around a momentum map of the watchlist.",
                "family=Geologica:wght@300;400;600", stamp, tokens, css, body)

# ======================= Direction 3: Aamu (morning report) =======================


def aamu():
    tokens = """
  color-scheme: light;
  --color-paper: oklch(98.5% 0.005 260); --color-paper-2: oklch(95.5% 0.008 260); --color-paper-3: oklch(91% 0.01 260);
  --color-ink: oklch(16% 0.012 260); --color-ink-2: oklch(30% 0.014 260); --color-muted: oklch(46% 0.016 260);
  --color-rule: oklch(88% 0.01 260); --color-rule-2: oklch(72% 0.014 260);
  --color-accent: oklch(42% 0.19 262); --color-accent-deep: oklch(34% 0.16 262); --color-accent-ink: oklch(98.5% 0.004 260);
  --color-focus: oklch(58% 0.22 28); --color-sel: oklch(93% 0.03 262);
  --color-own: oklch(42% 0.19 262);
  --color-up: oklch(47% 0.12 160); --color-down: oklch(52% 0.19 27);
  --color-line: oklch(42% 0.19 262);
  --color-s1: oklch(42% 0.19 262); --color-s2: oklch(58% 0.15 262); --color-s3: oklch(72% 0.1 262); --color-s4: oklch(27% 0.1 262);
  --color-s5: oklch(80% 0.06 262); --color-s6: oklch(88% 0.03 262);
  --font-display: "Barlow Condensed", ui-sans-serif, sans-serif; --font-body: "Barlow", ui-sans-serif, sans-serif;
  --font-num: "Barlow", ui-sans-serif, sans-serif;
  --radius-card: 0; --radius-pill: 0; --rule-hair: 1px; --tracking-display: -0.005em; --display-weight: 700;"""
    stamp = """/* Hallmark · shape: app screen · genre: modern-minimal · theme: Piste (by choice, outside the deal, for the Finnish blue on snow) · piste: snow
 * nav: masthead and a top bar · signature: the morning sentence, last night in New York told in one line with the portfolio figure set huge · states: full (loading, empty, error drawn on Huurre)
 * axes: light/condensed-sans/cobalt · posture: committed · contrast: pass · data: real (Yahoo), portfolio example · v2.0.0 */
/* Hallmark · pre-emit critique: P3 H3 E3 S3 R3 V2 · weakest: V, a report reads slower than a desk; it is the morning view, the desk is still one click away */"""
    s = sorted(TICK, key=lambda t: ST[t]["d1"])
    downs, ups = s[:3], s[::-1][:3]
    beat = P["day_pct"] - P["spy_day"]
    sentence = (f"Overnight your six holdings moved {pct(P['day_pct'], 2)} and SPY moved {pct(P['spy_day'], 2)}"
                f"{', so you finished ahead.' if beat > 0 else ', so you trailed the market.'}")
    movers = lambda lst: "".join(
        f'<li><a href="#{t}" class="mv"><span class="tk">{t}</span><span class="mvp num {cls(ST[t]["d1"])}">{pct(ST[t]["d1"], 1)}</span>'
        f'<span class="nm">{esc(name(t))}</span></a></li>' for t in lst)
    lo = min(min(rebased(t)) for t in TICK)
    hi = max(max(rebased(t)) for t in TICK)
    def tile(t):
        v = rebased(t)
        xs = scale(range(len(v)), 0, len(v) - 1, 0, 200)
        ys = scale(v, lo, hi, 78, 2)
        y100 = scale([100], lo, hi, 78, 2)[0]
        return (f'<li><a class="tile" href="#{t}"><span class="th"><span class="tk">{t}</span>'
                f'<span class="num {cls(ST[t]["y1"])}">{pct(ST[t]["y1"], 0)}</span></span>'
                f'<svg class="mini-chart" viewBox="0 0 200 80" aria-hidden="true"><line class="base" x1="0" x2="200" y1="{y100:.1f}" y2="{y100:.1f}"/>'
                f'<path class="ln {cls(ST[t]["y1"])}" d="{path(xs, ys)}"/></svg>'
                f'<span class="num tp">{usd(ST[t]["last"])}</span></a></li>')
    css = """
.bar { background: var(--color-paper); }
.mast { padding-block: var(--space-xl) var(--space-lg); border-bottom: 2px solid var(--color-ink); }
.mast .container { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: var(--space-lg); align-items: end; }
.mast h1 { font-size: clamp(3rem, 7vw, 5.5rem); text-transform: uppercase; line-height: 1; font-weight: 800; }
.mast .date { text-align: end; font-size: var(--text-lg); }
.lead { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--space-xl); padding-block: var(--space-xl); border-bottom: var(--rule-hair) solid var(--color-rule); }
.lead .figure { font-family: var(--font-display); font-weight: 800; font-size: clamp(3.5rem, 8vw, 7rem); line-height: 0.9; letter-spacing: -0.01em; font-variant-numeric: tabular-nums; }
.lead .sentence { font-size: var(--text-xl); line-height: 1.35; max-width: 34ch; margin-top: var(--space-md); }
.lead .meta { display: flex; gap: var(--space-xl); margin-top: var(--space-lg); flex-wrap: wrap; }
.lead .meta > div { display: grid; }
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
.pickrow { display: flex; flex-wrap: wrap; gap: 0; border: var(--rule-hair) solid var(--color-ink); width: fit-content; max-width: 100%; margin-bottom: var(--space-lg); }
.pickbtn { border: 0; border-inline-end: var(--rule-hair) solid var(--color-ink); background: var(--color-paper); min-height: 40px; padding: 0 var(--space-md); font-family: var(--font-display); font-weight: 700; font-size: var(--text-md); }
.pickbtn:last-child { border-inline-end: 0; }
.pickbtn:hover { background: var(--color-paper-3); }
.pickbtn[aria-pressed="true"] { background: var(--color-accent); color: var(--color-accent-ink); }
.dive h3 { font-size: var(--text-3xl); text-transform: uppercase; }
.dive .px { font-family: var(--font-display); font-weight: 700; font-size: var(--text-3xl); }
.two { display: grid; grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: var(--space-xl); }
.two .port-col { display: grid; gap: var(--space-md); align-content: start; }
.compare .sec-head h2 { font-size: var(--text-2xl); text-transform: uppercase; }
@media (max-width: 75rem) { .tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); } .lead, .two { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 40rem) { .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } .movers { grid-template-columns: minmax(0, 1fr); } .mast .container { grid-template-columns: minmax(0, 1fr); } .mast .date { text-align: start; } }
"""
    body = f"""
<header class="bar"><div class="container">
  <a class="mark" href="#" aria-label="Aamu, home">AAMU</a>
  <nav aria-label="Views"><a href="#" aria-current="page">Morning</a><a href="#wl-h">Watchlist</a><a href="#cmp-h">Compare</a><a href="#dv-h">Stock</a></nav>
  {clock()}
</div></header>
<main>
<div class="mast"><div class="container"><h1>Last night in New York</h1>
  <p class="date">Wednesday {FETCH_HKI.day} {FETCH_HKI:%B %Y}<br><span class="sub">Report built {FETCH_HKI:%H:%M} Helsinki time</span></p></div></div>
<div class="container lead">
  <div>
    <p class="pl">Example portfolio, in euros</p>
    <p class="figure">{eur(P["value"])}</p>
    <p class="sentence">{esc(sentence)}</p>
    <div class="meta">
      <div><span class="pl">Overnight</span><span class="num {cls(P["day"])}">{eur(P["day"], 0, True)}</span></div>
      <div><span class="pl">Since start</span><span class="num {cls(P["ret"])}">{pct(P["ret"])}</span></div>
      <div><span class="pl">Of which currency</span><span class="num {cls(P["fx_effect"])}">{pct(P["fx_effect"])}</span></div>
    </div>
  </div>
  <div class="movers">
    <div><h2>Up most</h2><ol>{movers(ups)}</ol></div>
    <div><h2>Down most</h2><ol>{movers(downs)}</ol></div>
  </div>
</div>
<section class="container sec" aria-labelledby="wl-h">
  <div class="sec-head"><h2 id="wl-h">The watchlist, one year</h2><p class="sub">Every chart on the same scale, rebased to 100. The rule marks the start.</p></div>
  <ul class="tiles">{"".join(tile(t) for t in TICK)}</ul>
</section>
<section class="container sec" aria-labelledby="dv-h">
  <div class="sec-head"><h2 id="dv-h">One stock</h2></div>
  {pick_buttons()}
  <div class="two">
    <div class="port-col"><h3 class="visually-hidden">Portfolio</h3>
      <p class="pl">Example portfolio weights</p>{holdings_bar()}
      <figure class="chart-fig">{port_chart(w=480, h=180)}<figcaption><span class="key main"></span>portfolio, euros <span class="key ref"></span>SPY, same money</figcaption></figure>
    </div>
    <div>{dives()}</div>
  </div>
</section>
<div class="container sec">{compare_block()}</div>
</main>
{footer()}"""
    return page("Aamu morning report", "A printed-style morning report of last night's US session, in euros, for a reader in Helsinki.",
                "family=Barlow+Condensed:wght@700;800&family=Barlow:wght@400;500;600",
                stamp, tokens, css, body)


if __name__ == "__main__":
    for fn, f in (("huurre.html", huurre), ("kaamos.html", kaamos), ("aamu.html", aamu)):
        (OUT / fn).write_text(f(), encoding="utf-8")
    json.dump(dict(P=P, weights=weights, ST={t: ST[t] for t in TICK + ["SPY"]}), open(OUT / "numbers.json", "w"), indent=1)
    print("portfolio", {k: round(v, 4) for k, v in P.items()})
    print({t: (round(ST[t]["d1"] * 100, 2), round(ST[t]["y1"] * 100, 1)) for t in TICK + ["SPY"]})
