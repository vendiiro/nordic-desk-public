"""Yahoo prices (3y daily) for the real holdings' tickers or proxies, candidate stocks, SPY and EURUSD."""
import json, datetime as dt
import yfinance as yf

TICKERS = ["GOOGL", "MSFT", "NVDA", "ORCL", "QDVE.DE", "EQQQ.DE", "CBUT.DE", "ETH-EUR", "^OMXH25",
           "AAPL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA", "SPY", "EURUSD=X"]
df = yf.download(TICKERS, period="3y", interval="1d", auto_adjust=True, progress=False)["Close"]
out = {"fetched_utc": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "series": {}, "info": {}}
for t in TICKERS:
    s = df[t].dropna()
    out["series"][t] = {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "close": [round(float(x), 5) for x in s.values]}
for t in ["GOOGL", "MSFT", "NVDA", "ORCL", "AAPL", "AMZN", "META", "AVGO", "JPM", "COST", "LLY", "XOM", "TSLA"]:
    try:
        i = yf.Ticker(t).info
        out["info"][t] = {k: i.get(k) for k in ["shortName", "sector", "industry", "trailingPE", "forwardPE", "dividendYield"]}
    except Exception as e:
        out["info"][t] = {"error": str(e)}
for t in ["QDVE.DE", "EQQQ.DE", "CBUT.DE", "^OMXH25"]:
    try:
        out["info"][t] = {"shortName": yf.Ticker(t).info.get("shortName"), "currency": yf.Ticker(t).info.get("currency")}
    except Exception as e:
        out["info"][t] = {"error": str(e)}
json.dump(out, open("data2.json", "w"))
for t, v in out["series"].items():
    print(t, len(v["close"]), v["dates"][0], v["dates"][-1], v["close"][-1], out["info"].get(t, {}).get("shortName"))
