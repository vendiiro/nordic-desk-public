"""Plain-language explanations shown on hover. `now` templates use {payload_field|format}; the page fills them per day.

Evidence wording follows the research summary in docs/superpowers/specs/2026-11-20-stock-analysis-page-design.md.
"""
from __future__ import annotations

import re

FORMATS = {"price", "pct", "pct0", "num1", "num2", "date"}

EXPLAIN: dict[str, dict[str, str]] = {
    "price": {
        "title": "Price",
        "what": "The closing price of the day you point at, with how it moved over a week, a month and a year.",
        "formula": "",
        "use": "Read it together with the trend and stretch lines: the verdict under it sums them up for that day.",
        "now": "",
    },
    "sma50": {
        "title": "50-day moving average",
        "what": "The average closing price of the last 50 trading days (about 2.5 months). It smooths out daily noise so you see the medium-term direction.",
        "formula": "SMA50 = (close₁ + … + close₅₀) / 50",
        "use": "Price above a rising 50-day line means the medium-term trend is up. When the 50-day crosses above the 200-day it is called a golden cross.",
        "now": "The 50-day average is {sma50|price}.",
    },
    "sma200": {
        "title": "200-day moving average",
        "what": "The average close over the last 200 trading days (about 10 months), the most watched long-term trend line.",
        "formula": "SMA200 = (close₁ + … + close₂₀₀) / 200",
        "use": "Buying dips while the price stays above a rising 200-day line means buying weakness inside an uptrend; below a falling line it is catching a falling knife. Evidence: moderate, it mainly cuts drawdowns (Faber).",
        "now": "The 200-day average is {sma200|price}; the price is {dist200|pct} from it.",
    },
    "bb": {
        "title": "Bollinger Bands (20, 2σ)",
        "what": "A band around the 20-day average, two standard deviations wide. If daily moves were normal, about 95% of closes would land inside it.",
        "formula": "mid = SMA20, upper/lower = mid ± 2σ₂₀;  %B = (price − lower) / (upper − lower)",
        "use": "Near the lower band while the long trend is up is the classic pullback entry. Evidence: weak or mixed on its own; use it to pick the day, not the stock.",
        "now": "%B is {pct_b|pct0} (0% = lower band, 100% = upper band); bands {bb_lo|price} to {bb_up|price}.",
    },
    "h52": {
        "title": "52-week high",
        "what": "The highest price of the last year. Investors anchor on it, so stocks close to it tend to keep drifting up when good news arrives.",
        "formula": "distance = price / max(daily high, last 252 days) − 1",
        "use": "Being close to the high (within about 10%) is a sign of strength, not a reason to avoid the stock. Evidence: strong (George & Hwang 2004).",
        "now": "The 52-week high is {high52|price}; the price is {dist52|pct} from it.",
    },
    "rsi": {
        "title": "RSI (14)",
        "what": "Relative Strength Index: compares the size of recent up days with recent down days on a 0–100 scale.",
        "formula": "RSI = 100 − 100 / (1 + average gain₁₄ / average loss₁₄)",
        "use": "Below 30 is oversold, above 70 overbought. In an uptrend, RSI at 30–40 is a common pullback zone. Evidence: weak or mixed; a timing aid only.",
        "now": "RSI is {rsi|num1}.",
    },
    "macd": {
        "title": "MACD (12, 26, 9)",
        "what": "The difference between a fast and a slow exponential moving average. It shows whether momentum is speeding up or slowing down.",
        "formula": "MACD = EMA₁₂ − EMA₂₆;  signal = EMA₉(MACD)",
        "use": "MACD crossing above its signal line means momentum is turning up; shrinking bars mean the move is losing steam. Evidence: weak or mixed (many such rules fail out of sample).",
        "now": "MACD {macd|num2}, signal {macd_signal|num2}, bars {macd_hist|num2}.",
    },
    "dd": {
        "title": "Drawdown",
        "what": "How far the price is below its highest point so far. It shows how deep the falls have been and how long they lasted.",
        "formula": "drawdown = price / running peak − 1",
        "use": "It tells you the pain you must be ready to sit through. It does not predict returns, but helps size the lump you buy.",
        "now": "The price is {drawdown|pct} below its peak.",
    },
    "pe": {
        "title": "P/E vs its own history",
        "what": "Price divided by earnings per share: how many euros you pay for one euro of yearly profit, compared with the stock's own past, not with other stocks.",
        "formula": "P/E = price / EPS of the last reported year (counted from 90 days after year-end)",
        "use": "Low compared with its own history means a cheaper entry for a long hold; high means you are paying up. Only about 4–5 years of history, so treat it as rough.",
        "now": "P/E {pe|num1} against a median of {pe_median|num1}; {pe_pct|pct0} of days in the window were at or below it.",
    },
    "mom": {
        "title": "12-1 month momentum",
        "what": "The return over the past 12 months, skipping the latest month (which tends to bounce back).",
        "formula": "momentum = price 21 days ago / price 252 days ago − 1",
        "use": "The measure quants use most: positive momentum tends to continue for 3–12 months. Evidence: strong (Jegadeesh & Titman 1993). Watch for momentum crashes after sharp market rebounds (Daniel & Moskowitz 2016).",
        "now": "12-1 momentum is {mom|pct}.",
    },
    "vol": {
        "title": "Volatility",
        "what": "How much the price swings, as a yearly figure from the last 3 months of daily moves.",
        "formula": "volatility = stdev(daily log return, 63 days) × √252",
        "use": "Higher means bigger swings both ways. It does not predict return; use it to judge how much to buy at once.",
        "now": "About {vol|pct0} a year.",
    },
    "quality": {
        "title": "Quality",
        "what": "Is the business itself good? Profitable firms have historically earned more, independent of price.",
        "formula": "ROE = net income / equity;  net margin = net income / revenue",
        "use": "For a long hold, quality protects you when you overpay a little. Evidence: strong (Novy-Marx 2013). Today's figures only, so past days leave it out.",
        "now": "",
    },
    "ltrev": {
        "title": "Long-term reversal",
        "what": "Stocks that rose or fell a lot over 3–5 years tend to partly reverse.",
        "formula": "3-year return = price / price 3 years ago − 1",
        "use": "A huge 3-year run is a mild warning for a multi-year hold; a long slump in a quality company a mild positive (De Bondt & Thaler 1985).",
        "now": "The 3-year return is {ret3y|pct}.",
    },
}

FIELDS_USED: set[str] = {f for e in EXPLAIN.values() for f, _ in re.findall(r"\{(\w+)\|(\w+)\}", e["now"])}
