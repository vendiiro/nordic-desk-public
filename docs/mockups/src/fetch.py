"""Fetch real Yahoo data for the mockups: daily closes (1y) for a US watchlist, EURUSD, plus a few info fields."""
import json, datetime as dt
import yfinance as yf

TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA"]
BENCH = "SPY"
out = {"fetched_utc": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "series": {}, "info": {}}

df = yf.download(TICKERS + [BENCH, "EURUSD=X"], period="1y", interval="1d", auto_adjust=True, progress=False)
close = df["Close"].dropna(how="all")
vol = df["Volume"]
for t in TICKERS + [BENCH, "EURUSD=X"]:
    s = close[t].dropna()
    out["series"][t] = {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "close": [round(float(x), 4) for x in s.values]}
    if t in TICKERS:
        out["series"][t]["volume"] = [int(x) for x in vol[t].reindex(s.index).fillna(0).values]

for t in TICKERS:
    try:
        i = yf.Ticker(t).info
        out["info"][t] = {k: i.get(k) for k in ["shortName", "sector", "industry", "marketCap", "trailingPE", "forwardPE",
                                                 "dividendYield", "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
                                                 "earningsTimestamp", "profitMargins", "revenueGrowth"]}
    except Exception as e:  # keep going; the mockup marks missing fields
        out["info"][t] = {"error": str(e)}

json.dump(out, open("data.json", "w"))
print("ok", out["fetched_utc"], {t: len(v["close"]) for t, v in out["series"].items()})
