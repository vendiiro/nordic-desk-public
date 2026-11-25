"""Risk view of an EXAMPLE portfolio and what-if scenarios, from Yahoo daily closes in EUR (mockup data).

The holdings below are invented round numbers so the mockup can be shown publicly; the real build reads
the owner's holdings from a git-ignored file. Methods mirror lovable-continuous src/lib/quant: covariance
risk, Euler risk contributions, conditional (downside) correlation on the worst 20 % of portfolio days,
constant-weight replay for drawdown.
"""
import json, math, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).parent
D = json.load(open(ROOT / "data2.json"))
S = D["series"]
END = "2026-11-17"          # last full US close
USD = {"GOOGL", "MSFT", "NVDA", "ORCL", "AAPL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA", "SPY"}

# Example holdings (invented values, EUR). proxy = Yahoo series used for returns.
HOLD = [
    # name, proxy, value_eur, tech, proxy note
    ("iShares S&P 500 IT ETF", "QDVE.DE", 8000.0, True, "same fund, Xetra listing"),
    ("Alphabet A", "GOOGL", 6000.0, False, ""),
    ("NVIDIA", "NVDA", 4000.0, True, ""),
    ("Microsoft", "MSFT", 4000.0, True, ""),
    ("Nordnet Suomi Indeksi", "^OMXH25", 3000.0, False, "OMX Helsinki 25 index as stand-in"),
    ("Amundi Nasdaq-100 ETF", "EQQQ.DE", 2500.0, False, "Invesco Nasdaq-100 as stand-in"),
    ("Oracle", "ORCL", 1500.0, True, ""),
    ("iShares Blockchain ETF", "CBUT.DE", 500.0, True, "same fund, Xetra listing"),
    ("Ether tracker", "ETH-EUR", 500.0, False, "ETH in euros as stand-in"),
]
CASHLIKE = 1000.0
TOTAL = sum(h[2] for h in HOLD) + CASHLIKE
CANDS = ["AAPL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA", "SPY"]
AMOUNTS = [500, 1000, 2500, 5000]

# ---- EUR price panel on weekdays, forward-filled ----
fx = dict(zip(S["EURUSD=X"]["dates"], S["EURUSD=X"]["close"]))
alld = sorted({d for t in S for d in S[t]["dates"] if d <= END})
alld = [d for d in alld if np.datetime64(d).astype("datetime64[D]").item().weekday() < 5]
tick = [h[1] for h in HOLD] + [c for c in CANDS if c not in [h[1] for h in HOLD]]
panel, last_fx, fxs = {}, None, []
for d in alld:
    last_fx = fx.get(d, last_fx)
    fxs.append(last_fx)
for t in tick:
    m = dict(zip(S[t]["dates"], S[t]["close"]))
    v, out = None, []
    for d, f in zip(alld, fxs):
        v = m.get(d, v)
        out.append(None if v is None or f is None else (v / f if t in USD else v))
    panel[t] = out
start = len(alld) - 253
dates = alld[start:]
P = np.array([panel[t][start:] for t in tick], dtype=float).T          # T x N, EUR
assert not np.isnan(P).any()
R = P[1:] / P[:-1] - 1                                                    # simple daily returns
col = {t: i for i, t in enumerate(tick)}
spy_r = R[:, col["SPY"]]
TECH = {h[1]: h[3] for h in HOLD} | {"AAPL": True, "AVGO": True}   # candidates by Yahoo sector Technology


def stats_for(wmap, cash):
    """wmap: ticker -> EUR value; cash: EUR at zero return."""
    tot = sum(wmap.values()) + cash
    keys = list(wmap)
    w = np.array([wmap[k] / tot for k in keys])
    X = R[:, [col[k] for k in keys]]
    rp = X @ w
    cov = np.cov(X.T, ddof=1) * 252
    vol = math.sqrt(w @ cov @ w)
    rc = w * (cov @ w) / vol
    beta = np.cov(rp, spy_r)[0, 1] / np.var(spy_r, ddof=1)
    path = np.cumprod(1 + rp)
    worst = float(np.min(path / np.maximum.accumulate(path) - 1))
    tech = sum(wmap[k] for k in keys if TECH.get(k)) / tot
    enb = 1 / float(np.sum(np.append(w, cash / tot) ** 2))
    return dict(vol=vol, beta=float(beta), worst=worst, ret=float(path[-1] - 1), tech=tech, enb=enb,
                rc=dict(zip(keys, (rc / vol).tolist())), w=dict(zip(keys, w.tolist())), rp=rp, tot=tot)


base_map = {h[1]: h[2] for h in HOLD}
BASE = stats_for(base_map, CASHLIKE)
rp = BASE["rp"]
worst_days = rp <= np.quantile(rp, 0.2)


def asset_view(t):
    x = R[:, col[t]]
    vol = float(np.std(x, ddof=1) * math.sqrt(252))
    rest = rp - BASE["w"].get(t, 0) * x if t in BASE["w"] else rp
    return dict(vol=vol, corr=float(np.corrcoef(x, rest)[0, 1]), down=float(np.corrcoef(x[worst_days], rp[worst_days])[0, 1]),
                beta_p=float(np.cov(x, rp)[0, 1] / np.var(rp, ddof=1)), ret=float(np.prod(1 + x) - 1))


holdings = []
for name, t, v, tech, note in HOLD:
    holdings.append(dict(name=name, t=t, value=v, weight=v / TOTAL, risk=BASE["rc"][t], tech=tech, note=note, **asset_view(t)))
holdings.sort(key=lambda h: -h["risk"])

scen = []
for c in CANDS:
    a = asset_view(c)
    for amt in AMOUNTS:
        m = dict(base_map)
        m[c] = m.get(c, 0) + amt
        s = stats_for(m, CASHLIKE)
        scen.append(dict(id=f"add-{c}-{amt}", kind="add", t=c, amount=amt, cand=a, own_risk=s["rc"][c],
                         **{k: s[k] for k in ("vol", "beta", "worst", "ret", "tech", "enb", "tot")}))
for name, t, v, *_ in HOLD:
    m = {k: val for k, val in base_map.items() if k != t}
    scale_up = sum(base_map.values()) / sum(m.values())     # proceeds spread pro rata over the other holdings
    s = stats_for({k: val * scale_up for k, val in m.items()}, CASHLIKE)
    scen.append(dict(id=f"sell-{t}", kind="sell", t=t, name=name, amount=v, cand=asset_view(t),
                     **{k: s[k] for k in ("vol", "beta", "worst", "ret", "tech", "enb", "tot")}))

OUT = dict(dates=[dates[0], dates[-1]], base={k: BASE[k] for k in ("vol", "beta", "worst", "ret", "tech", "enb", "tot")},
           holdings=holdings, scen=scen, total=TOTAL, cashlike=CASHLIKE, fetched=D["fetched_utc"])
json.dump(OUT, open(ROOT / "impact.json", "w"), indent=1)

if __name__ == "__main__":
    b = BASE
    print(f"window {dates[0]}..{dates[-1]} vol {b['vol']:.4f} beta {b['beta']:.3f} enb {b['enb']:.2f} tech {b['tech']:.3f}")
