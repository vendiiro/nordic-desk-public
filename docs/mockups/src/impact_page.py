"""Impact frame: the real portfolio's risk and what-if scenarios, in the Huurre style."""
import json, pathlib, datetime as dt
import gen
from gen import pct, eur, esc, cls, nice_ticks, scale, path, page, MINUS

ROOT = pathlib.Path(__file__).parent
J = json.load(open(ROOT / "impact.json"))
for _h in J["holdings"]:
    _h["name"] = _h["name"].replace("NVIDIA", "Nvidia")
for _s in J["scen"]:
    if "name" in _s: _s["name"] = _s["name"].replace("NVIDIA", "Nvidia")
B, H, SC = J["base"], J["holdings"], J["scen"]
REC = J.get("record")  # only the owner's private build has a record
DEFAULT = "add-XOM-1000"
NAMES = {h["t"]: h["name"] for h in H}
CAND_NAME = {"AAPL": "Apple", "AMZN": "Amazon", "META": "Meta", "AVGO": "Broadcom", "JPM": "JPMorgan", "COST": "Costco",
             "LLY": "Eli Lilly", "XOM": "Exxon Mobil", "TSLA": "Tesla", "SPY": "Index fund"}
TK = {"QDVE.DE": "QDVE", "EQQQ.DE": "EQQQ", "CBUT.DE": "CBUT", "ETH-EUR": "ETH", "^OMXH25": "OMXH25"}


def tk(t):
    return TK.get(t, t)


def pp(d):
    s = f"{abs(d) * 100:.2f} pp"
    return ("+" if d > 0 else MINUS if d < 0 else "") + s


def num(x, d=2):
    return (MINUS if x < 0 else "") + f"{abs(x):.{d}f}"


def sg(x, d=2):
    return ("+" if round(x, d) > 0 else "") + num(x, d)


def delta_cls(d, good_when_lower=True):
    if abs(d) < 1e-9:
        return "flat"
    return "up" if (d < 0) == good_when_lower else "down"


# ---------- sections ----------

def strip():
    return f"""
<section class="container strip" aria-label="Real portfolio today">
  <div class="fig"><span class="pl">Example portfolio</span><span class="v num">{eur(J["total"])}</span><span class="note">invented values, 9 holdings and cash</span></div>
  <div class="fig"><span class="pl">Volatility, 1 year</span><span class="v sm num">{pct(B["vol"], 1, False)}</span><span class="note">past year, today’s weights</span></div>
  <div class="fig"><span class="pl">Beta to S&amp;P 500, in euros</span><span class="v sm num">{B["beta"]:.2f}</span><span class="note">moves {B["beta"]:.2f}× the market</span></div>
  <div class="fig"><span class="pl">Effective holdings</span><span class="v sm num">{B["enb"]:.1f}</span><span class="note">of 10 by count</span></div>
  <div class="fig"><span class="pl">Technology share</span><span class="v sm num">{pct(B["tech"], 0, False)}</span><span class="note">Yahoo sector, IT and blockchain ETFs</span></div>
</section>"""


def risk_section():
    mx = max(max(h["weight"], h["risk"]) for h in H)
    rows = []
    for h in H:
        ratio = h["risk"] / h["weight"]
        note = f'<span class="nm">{esc(h["note"])}</span>' if h["note"] else ""
        rows.append(f"""
<tr>
  <th scope="row"><span class="hn">{esc(h["name"])}</span>{note}</th>
  <td class="bars"><span class="bar-w" style="--w:{h["weight"] / mx:.4f}"></span><span class="bar-r" style="--w:{h["risk"] / mx:.4f}"></span></td>
  <td class="num r">{pct(h["weight"], 1, False)}</td>
  <td class="num r">{pct(h["risk"], 1, False)}</td>
  <td class="num r {"down" if ratio > 1.15 else "up" if ratio < 0.85 else "flat"}">{ratio:.2f}×</td>
  <td class="num r">{pct(h["vol"], 0, False)}</td>
  <td class="num r">{num(h["corr"])}</td>
  <td class="num r">{num(h["down"])}</td>
  <td class="num r {cls(h["ret"])}">{pct(h["ret"], 0)}</td>
</tr>""")
    over = [h["name"] for h in H if h["risk"] / h["weight"] > 1.15]
    under = [h["name"] for h in H if h["risk"] / h["weight"] < 0.85]
    top3 = sum(h["risk"] for h in H[:3])
    sent = (f"{', '.join(over[:-1])} and {over[-1]} carry more risk than their weight. "
            f"{', '.join(under[:-1])} and {under[-1]} carry less. "
            f"The three largest risk sources make up {pct(top3, 0, False)} of the swings.")
    return f"""
<section class="container sec" aria-labelledby="rk-h">
  <div class="panel flush">
    <div class="sec-head"><div><h2 id="rk-h">Where the risk comes from</h2><p class="sub">{esc(sent)}</p></div>
      <p class="legend sub"><span><i class="kw"></i>share of money</span><span><i class="kr"></i>share of risk</span></p></div>
    <div class="table-wrap"><table class="risk">
      <thead><tr><th scope="col">Holding</th><th scope="col">Money and risk</th><th scope="col" class="r">Weight</th><th scope="col" class="r">Risk share</th>
      <th scope="col" class="r">Risk ÷ weight</th><th scope="col" class="r">Volatility</th><th scope="col" class="r">Correlation</th>
      <th scope="col" class="r">On bad days</th><th scope="col" class="r">1 year</th></tr></thead>
      <tbody>{"".join(rows)}</tbody></table></div>
  </div>
</section>"""


def scen_block(s):
    hidden = "" if s["id"] == DEFAULT else " hidden"
    c = s["cand"]
    rows = [
        ("Volatility, 1 year", pct(B["vol"], 1, False), pct(s["vol"], 1, False), pp(s["vol"] - B["vol"]), delta_cls(s["vol"] - B["vol"])),
        ("Beta to S&P 500", f'{B["beta"]:.2f}', f'{s["beta"]:.2f}', sg(s["beta"] - B["beta"]), delta_cls(s["beta"] - B["beta"])),
        ("Worst fall, past year", pct(B["worst"]), pct(s["worst"]), pp(s["worst"] - B["worst"]), delta_cls(s["worst"] - B["worst"], False)),
        ("Effective holdings", f'{B["enb"]:.1f}', f'{s["enb"]:.1f}', sg(s["enb"] - B["enb"], 1), delta_cls(s["enb"] - B["enb"], False)),
        ("Technology share", pct(B["tech"], 1, False), pct(s["tech"], 1, False), pp(s["tech"] - B["tech"]), "flat"),
        ("Past year, these weights", pct(B["ret"]), pct(s["ret"]), pp(s["ret"] - B["ret"]), "flat"),
    ]
    trs = "".join(f'<tr><th scope="row">{a}</th><td class="num r">{b}</td><td class="num r">{c_}</td><td class="num r {k}">{d}</td></tr>'
                  for a, b, c_, d, k in rows)
    if s["kind"] == "add":
        who = f'{CAND_NAME[s["t"]]} ({s["t"]})'
        head = f'Add {eur(s["amount"])} of {who}'
        sent = (f'Over the past year {s["t"]} had a correlation of {num(c["corr"])} with your holdings, '
                f'and {num(c["down"])} on your worst fifth of days. '
                f'Volatility goes from {pct(B["vol"], 1, False)} to {pct(s["vol"], 1, False)}; '
                f'{s["t"]} would carry {pct(s["own_risk"], 1, False)} of the risk.')
        side = [("Correlation with your holdings", num(c["corr"])), ("On your worst 20% of days", num(c["down"])),
                ("Its own volatility", pct(c["vol"], 0, False)), ("Its past year, in euros", pct(c["ret"], 0)),
                ("Its risk share after", pct(s["own_risk"], 1, False))]
    else:
        head = f'Sell {esc(s["name"])} ({eur(s["amount"])}), spread the money over the rest'
        sent = (f'{s["name"]} had a correlation of {num(c["corr"])} with the rest of the portfolio. '
                f'Without it volatility goes from {pct(B["vol"], 1, False)} to {pct(s["vol"], 1, False)} '
                f'and the technology share to {pct(s["tech"], 0, False)}.')
        side = [("Correlation with the rest", num(c["corr"])), ("On your worst 20% of days", num(c["down"])),
                ("Its own volatility", pct(c["vol"], 0, False)), ("Its past year, in euros", pct(c["ret"], 0))]
    dl = "".join(f'<div><dt>{a}</dt><dd class="num">{b}</dd></div>' for a, b in side)
    return f"""
<div class="scn" data-scn="{s["id"]}"{hidden}>
  <h3>{head}</h3>
  <p class="say">{esc(sent)}</p>
  <div class="scn-grid">
    <div class="table-wrap"><table class="ba"><thead><tr><th scope="col">Measure</th><th scope="col" class="r">Now</th><th scope="col" class="r">After</th><th scope="col" class="r">Change</th></tr></thead>
    <tbody>{trs}</tbody></table></div>
    <dl class="facts one">{dl}</dl>
  </div>
</div>"""


def whatif():
    adds = sorted({s["t"] for s in SC if s["kind"] == "add"}, key=lambda t: list(CAND_NAME).index(t))
    radio = lambda name, val, label, checked: (
        f'<label class="chip"><input type="radio" name="{name}" value="{val}"{" checked" if checked else ""}>{label}</label>')
    mode = radio("mode", "add", "Add a stock", True) + radio("mode", "sell", "Sell a holding", False)
    addt = "".join(radio("tk", t, t, t == "XOM") for t in adds)
    amts = "".join(radio("amt", a, eur(a), a == 1000) for a in (500, 1000, 2500, 5000))
    sells = "".join(radio("sl", h["t"], esc(h["name"]), i == 0) for i, h in enumerate(H))
    ranked = sorted([s for s in SC if s["kind"] == "add" and s["amount"] == 1000], key=lambda s: s["vol"])
    rank_rows = "".join(
        f'<tr><th scope="row"><span class="tk">{s["t"]}</span> <span class="nm2">{CAND_NAME[s["t"]]}</span></th>'
        f'<td class="num r">{num(s["cand"]["corr"])}</td><td class="num r">{num(s["cand"]["down"])}</td>'
        f'<td class="num r {delta_cls(s["vol"] - B["vol"])}">{pp(s["vol"] - B["vol"])}</td>'
        f'<td class="num r {delta_cls(s["beta"] - B["beta"])}">{sg(s["beta"] - B["beta"])}</td>'
        f'<td class="num r {delta_cls(s["worst"] - B["worst"], False)}">{pp(s["worst"] - B["worst"])}</td>'
        f'<td class="num r {cls(s["cand"]["ret"])}">{pct(s["cand"]["ret"], 0)}</td></tr>' for s in ranked)
    return f"""
<section class="container sec" aria-labelledby="wi-h">
  <div class="whatif">
    <div class="panel">
      <div class="sec-head"><div><h2 id="wi-h">Try a change</h2><p class="sub">Replayed on the past year of daily prices in euros. A description of the past, not a forecast.</p></div></div>
      <form class="controls" aria-label="Scenario" onsubmit="return false">
        <fieldset class="chips"><legend class="lg">Change</legend>{mode}</fieldset>
        <fieldset class="chips" data-for="add"><legend class="lg">Stock, new money</legend>{addt}</fieldset>
        <fieldset class="chips" data-for="add"><legend class="lg">Amount</legend>{amts}</fieldset>
        <fieldset class="chips" data-for="sell" hidden><legend class="lg">Holding</legend>{sells}</fieldset>
      </form>
      <div class="out" aria-live="polite">{"".join(scen_block(s) for s in SC)}</div>
    </div>
    <div class="panel flush">
      <div class="sec-head"><div><h2 id="rank-h">Each candidate at €1,000</h2><p class="sub">Sorted by the change in volatility, largest drop first.</p></div></div>
      <div class="table-wrap"><table class="rank" aria-labelledby="rank-h">
        <thead><tr><th scope="col">Stock</th><th scope="col" class="r">Correlation</th><th scope="col" class="r">Bad days</th>
        <th scope="col" class="r">Volatility</th><th scope="col" class="r">Beta</th><th scope="col" class="r">Worst fall</th><th scope="col" class="r">Its year</th></tr></thead>
        <tbody>{rank_rows}</tbody></table></div>
    </div>
  </div>
</section>"""


def glossary():
    nv = next(h for h in H if h["t"] == "NVDA")
    om = next(h for h in H if h["t"] == "^OMXH25")
    al = next(h for h in H if h["t"] == "GOOGL")
    items = [
        ("Volatility", "How much the value swings in a typical year. About two years in three stay within one volatility of the average.",
         "σ = std(daily returns) × √252",
         f"{pct(B['vol'], 1, False)}: on {eur(J['total'])}, a typical year moves the value by about {eur(B['vol'] * J['total'])} either way."),
        ("Beta", "How strongly the portfolio follows the S&P 500, both measured in euros. 1.0 moves with the market.",
         "β = cov(portfolio, market) ÷ var(market)",
         f"{B['beta']:.2f}: a 10% market fall has come with about {B['beta'] * 10:.1f}% for you."),
        ("Correlation", "Whether a stock moves with the rest of your holdings: 1 together, 0 unrelated, negative in opposite directions.",
         "ρ = cov(stock, rest) ÷ (σ_stock σ_rest)",
         f"Nvidia {num(nv['corr'])}, Suomi Indeksi {num(om['corr'])}."),
        ("On bad days", "The same correlation measured only on your worst fifth of days. Diversification that disappears in a sell-off shows up here.",
         "ρ on days where portfolio return ≤ its 20th percentile",
         f"Alphabet rises from {num(al['corr'])} to {num(al['down'])}: it falls with the rest more often than it seems."),
        ("Risk share", "How much of the portfolio’s swing each holding causes. The shares add up to 100%.",
         "RCᵢ = wᵢ (Σw)ᵢ ÷ σ²",
         f"Nvidia is {pct(nv['weight'], 0, False)} of the money and {pct(nv['risk'], 0, False)} of the risk."),
        ("Effective holdings", "How many equal-sized positions your weights are worth.",
         "N = 1 ÷ Σ wᵢ²",
         f"{B['enb']:.1f}: ten positions behave like about five equal ones."),
        ("Worst fall", "The deepest drop from a high point during the past year, with today’s weights held fixed.",
         "min (value ÷ running peak − 1)",
         f"{pct(B['worst'])} with the current mix."),
    ]
    rows = "".join(f'<div class="g"><dt>{a}</dt><dd><p>{b}</p><p class="fm">{c}</p><p class="ex">{d}</p></dd></div>' for a, b, c, d in items)
    return f"""
<section class="container sec" aria-labelledby="gl-h">
  <div class="panel">
    <div class="sec-head"><div><h2 id="gl-h">What the numbers mean</h2><p class="sub">The idea, the formula, then your own number.</p></div></div>
    <dl class="gloss">{rows}</dl>
  </div>
</section>"""


def record_chart(w=900, h=260):
    d, twr, spy = REC["dates"], REC["twr"], REC["spy"]
    a = [(v - 1) * 100 for v in twr]
    b = [(v - 1) * 100 for v in spy]
    L, R, T, Bm = 48, 12, 12, 28
    lo, hi = min(a + b) - 3, max(a + b) + 3
    n = len(d)
    xs = scale(range(n), 0, n - 1, L, w - R)
    o = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Your time-weighted return since September 2024 against the S&P 500 in euros">']
    for v in nice_ticks(lo, hi, 4):
        y = scale([v], lo, hi, h - Bm, T)[0]
        o.append(f'<line class="{"base" if abs(v) < 1e-9 else "grid"}" x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 f'<text class="ax" x="{L - 8}" y="{y + 4:.1f}" text-anchor="end">{v:.0f}%</text>')
    seen = set()
    for i, dd in enumerate(d):
        if dd[5:7] in ("01", "07") and dd[:7] not in seen:
            seen.add(dd[:7])
            o.append(f'<text class="ax" x="{xs[i]:.1f}" y="{h - 8}" text-anchor="middle">{gen.MONTHS[int(dd[5:7]) - 1]} {dd[2:4]}</text>')
    dep = REC["deposits"]
    for i in range(1, n):
        if dep[i] - dep[i - 1] > 1:
            o.append(f'<line class="dep" x1="{xs[i]:.1f}" x2="{xs[i]:.1f}" y1="{h - Bm}" y2="{h - Bm - 8}"/>')
    o.append(f'<path class="ln ref" d="{path(xs, scale(b, lo, hi, h - Bm, T))}"/>')
    o.append(f'<path class="ln main" d="{path(xs, scale(a, lo, hi, h - Bm, T))}"/>')
    o.append("</svg>")
    return "".join(o)


def record():
    if not REC:
        return ""
    n_dep = sum(1 for i in range(1, len(REC["deposits"])) if REC["deposits"][i] - REC["deposits"][i - 1] > 1)
    first = dt.date.fromisoformat(REC["dates"][0])
    return f"""
<section class="container sec" aria-labelledby="rc-h">
  <div class="panel">
    <div class="sec-head"><div><h2 id="rc-h">Your record since {first.day} {first:%b %Y}</h2>
      <p class="sub">Time-weighted, so the {n_dep + 1} deposits ({eur(REC["deposits"][-1])} in all) do not count as gains. Ticks on the axis mark deposits.</p></div>
      <p class="legend sub"><span><i class="km"></i>you {pct(REC["twr"][-1] - 1)}</span><span><i class="kf"></i>S&amp;P 500 in euros {pct(REC["spy"][-1] - 1)}</span></p></div>
    <figure class="chart-fig">{record_chart()}</figure>
    <p class="note">Nordnet’s own figure for the same period is {REC["nordnet_cum"][-1].replace(",", ".")}; it weighs deposits differently.</p>
  </div>
</section>"""


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
  };
  f.addEventListener('change', show); show();
})();
</script>"""


def build():
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
 * nav: top bar · signature: money against risk, two bars per holding · states: full; scenarios switch in place · console: paper
 * axes: light/grotesk-sans/cool-blue · posture: restrained · contrast: pass · data: Yahoo prices, example holdings (invented) · v2.0.0 */
/* Hallmark · pre-emit critique: P3 H3 E3 S3 R3 V2 · weakest: V, many figures on one screen; the sentence above each block says what they add up to */"""
    css = """
.mark { color: var(--color-accent); }
.strip { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: var(--space-lg); align-items: start; padding-block: var(--space-lg); border-bottom: var(--rule-hair) solid var(--color-rule); }
.fig { display: grid; gap: 2px; align-content: start; }
.fig .v { font-family: var(--font-num); font-size: var(--text-2xl); font-variant-numeric: tabular-nums; line-height: 1.1; }
.fig .v.sm { font-size: var(--text-xl); }
.panel { border: var(--rule-hair) solid var(--color-rule); border-radius: var(--radius-card); background: var(--color-paper); padding: var(--space-md); min-width: 0; }
.panel.flush { padding: 0; }
.panel.flush .sec-head { padding: var(--space-md) var(--space-md) var(--space-xs); }
.sec { padding-top: var(--space-lg); }
.sec-head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-md); flex-wrap: wrap; margin-bottom: var(--space-sm); }
.sec-head .sub { max-width: 80ch; margin-top: var(--space-2xs); }
.legend { display: flex; gap: var(--space-md); flex-wrap: wrap; }
.legend span { display: inline-flex; align-items: center; gap: var(--space-xs); }
.legend i { display: inline-block; width: 14px; height: 8px; }
.kw, .bar-w { background: var(--color-rule-2); }
.kr, .bar-r { background: var(--color-accent); }
.km { background: var(--color-line); height: 2px !important; } .kf { background: var(--color-muted); height: 2px !important; }
.risk th:first-child, .rank th:first-child { padding-inline-start: var(--space-md); }
.hn { display: block; }
.risk .nm { display: block; max-width: none; white-space: normal; }
.bars { width: 28%; min-width: 180px; }
.bars span { display: block; height: 8px; inline-size: calc(var(--w) * 100%); }
.bars span + span { margin-top: var(--space-2xs); }
.whatif { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--gap); }
.controls { display: grid; gap: var(--space-xs); margin-bottom: var(--space-md); }
.controls .chips { margin: 0; align-items: center; }
.lg { float: left; width: 9rem; padding-top: var(--space-xs); color: var(--color-muted); font-size: var(--text-sm); }
.out { border-top: var(--rule-hair) solid var(--color-rule); padding-top: var(--space-md); }
.scn { display: grid; gap: var(--space-sm); }
.scn h3 { font-size: var(--text-lg); }
.say { max-width: 70ch; }
.scn-grid { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: var(--space-xl); align-items: start; }
.facts.one { grid-template-columns: minmax(0, 1fr); }
.ba th[scope="row"] { color: var(--color-ink-2); }
.nm2 { color: var(--color-muted); font-size: var(--text-sm); }
.gloss { margin: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr)); gap: var(--space-md) var(--space-lg); }
.g { display: grid; gap: var(--space-2xs); align-content: start; padding-top: var(--space-sm); border-top: var(--rule-hair) solid var(--color-rule); }
.g dt { font-weight: 600; }
.g dd { margin: 0; display: grid; gap: var(--space-xs); }
.fm { font-family: var(--font-num); font-size: var(--text-sm); color: var(--color-ink-2); }
.ex { font-size: var(--text-sm); color: var(--color-accent); }
.chart .dep { stroke: var(--color-own); stroke-width: 2; }
.chip input[type="radio"] { position: absolute; opacity: 0; width: 1px; height: 1px; }
@media (max-width: 75rem) { .strip { grid-template-columns: repeat(3, minmax(0, 1fr)); } .whatif, .scn-grid { grid-template-columns: minmax(0, 1fr); } }
@media (max-width: 40rem) { .strip { grid-template-columns: repeat(2, minmax(0, 1fr)); } .lg { float: none; width: auto; } }
"""
    fetched = dt.datetime.strptime(J["fetched"], "%Y-%m-%d %H:%M") + dt.timedelta(hours=2)
    body = f"""
<header class="bar"><div class="container">
  <a class="mark" href="huurre.html" aria-label="Huurre, desk">Huurre</a>
  <nav aria-label="Views"><a href="huurre.html">Desk</a><a href="#" aria-current="page">Impact</a></nav>
  {gen.clock()}
</div></header>
<main>
<h1 class="visually-hidden">Portfolio impact</h1>
{strip()}
{risk_section()}
{whatif()}
{glossary()}
{record()}
</main>
<footer class="foot"><div class="container">
  <p>Example portfolio with invented values; the real build reads the owner’s holdings from a private local file. Prices and EUR/USD from Yahoo Finance, fetched {fetched.day} {fetched:%b %Y} at {fetched:%H:%M} Helsinki time; risk window {J["dates"][0]} to {J["dates"][1]}.</p>
  <p>Stand-ins where Yahoo has no series: OMX Helsinki 25 for Nordnet Suomi Indeksi, Invesco Nasdaq-100 for the Amundi Nasdaq-100 ETF, ETH in euros for the Ether tracker. Cash ({eur(J["cashlike"])}) counts as zero return.</p>
  <p>Today’s weights are held fixed over the past year, so the figures describe this mix, not your actual history. Not investment advice.</p>
</div></footer>"""
    html = page("Huurre impact", "Risk of the real portfolio and what adding or selling one stock would change.",
                "family=Host+Grotesk:wght@400;500;600&family=Atkinson+Hyperlegible+Mono:wght@400;600",
                stamp, tokens, css, body, script=False)
    return html.replace("</body>", JS + "\n</body>")


if __name__ == "__main__":
    (ROOT / "mock" / "impact.html").write_text(build(), encoding="utf-8")
    print("ok")
