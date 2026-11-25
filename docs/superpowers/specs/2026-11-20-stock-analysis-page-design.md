# Single-stock analysis page: design

Date: 2026-11-20. Owner: Iiro. Builds on the Huurre views (`views/core.py`, `views/huurre.py`), the Ideas cards (`views/cards.py`), the price store (`prices.py`) and `docs/data-contract.md`. Approved layout: mockup "A · Desk" from the brainstorming session (kept locally in `.superpowers/brainstorm/`, git-ignored; it uses an invented stock).

## Intent and why

In his broker's app the owner can switch chart indicators on, but he doesn't remember what each one means, and the help sits behind a "?" he has to click. He wants a professional-looking chart for one stock where:

1. he first says **how long he plans to hold** the stock, and the page shows the metrics that matter for that horizon;
2. **hovering** over any indicator line, panel, toggle or info box explains, at a student level, what it measures, its formula in one line, how to use it when buying, and what its value means on that day;
3. **hovering over the price** gives a reading of that day: how the price has moved (week, month, year), where it sits against its trend and its high, and a plain verdict;
4. info boxes beside the chart summarise today's readings, and a **verdict** says whether this looks like a good moment to buy, with the reasons listed.

He invests for the long term, in lumps of a few thousand euros, so the page answers "is now a reasonable time to put money in, or should I wait?" for a stock he is already interested in. It is not a trading tool.

Success: he opens a holding, a watchlist name or an Ideas candidate, picks a horizon, and within a minute understands what the chart is saying and why the verdict says what it says, without remembering any indicator by heart.

## Goals

### 1. Two horizons

A segmented control at the top: **6–12 months** and **Long haul (years)**. The horizon sets the defaults; every indicator can still be toggled in either horizon.

| | 6–12 months | Long haul |
|---|---|---|
| Default range | 1Y | 5Y |
| Default style | candles | line |
| Overlays on by default | 200-day average, Bollinger Bands, 52-week high | 200-day average |
| Lower panels on by default | RSI | drawdown, P/E vs own history |
| Info boxes | Trend, Stretch, Momentum, Risk | Valuation, Quality, Long-term, Risk |
| Verdict | Good entry / Wait / Stretched | Attractive / Fair / Expensive |

Range buttons: 1M, 6M, 1Y, 5Y. Line/candles toggle. When candles would be too thin (5Y), bars are grouped (for example weekly) so at most about 150 are drawn; overlays are read at each group's last day.

A third horizon (1–3 months) is a possible later addition; not in this project.

### 2. Indicators (all computed in Python at build time)

Overlays on the price panel:
- **50-day and 200-day simple moving average.** Also "rising/falling" for the 200-day: compare with its value 21 trading days earlier.
- **Bollinger Bands (20, 2σ)** with **%B** = (price − lower) / (upper − lower). Population standard deviation over the 20-day window.
- **52-week high**: rolling maximum of the daily high over 252 days, so the line is drawn from highs, not closes. Distance = price / 52w high − 1.

Lower panels:
- **RSI (14)**, Wilder smoothing, guide lines at 30 and 70.
- **MACD (12, 26, 9)**: line, signal and histogram.
- **Drawdown**: price / running peak − 1, over the full stored history, not only the visible range.
- **P/E vs own history** (long haul; stocks only): daily price / trailing-12-month EPS, with the median of the window as a guide line. Built from annual or quarterly EPS from yfinance, so roughly 4–5 years of history. Labelled "short history" in its explanation.

Readings that appear in boxes and hovers but are not drawn:
- **12-1 month momentum** = price 21 days ago / price 252 days ago − 1.
- **Volatility**: standard deviation of daily log returns over 63 days × √252.
- **3-year return** (long-term reversal).
- **Quality** (stocks only): ROE, net margin, free cash flow sign and yield, debt/equity. Reuse the checks and the distorted-ROE guard from market-leaderboard's `engine/quality.py` (port them, don't import across repos).

The formulas for RSI-14, the 52-week distance and the 200-day slope already exist in `dip-dashboard` and `market-leaderboard` `metrics.py`. Port them with their tests.

### 3. Hover explanations

Every indicator has an explanation entry: title, what it measures (one or two plain sentences), the formula in one line, how to use it when deciding to buy (including how strong the evidence is: strong, moderate, or weak/mixed), and a sentence built from that day's value. They show:
- on hovering or focusing a toggle chip;
- on hovering an info box;
- on the chart: within about 8 px of an overlay line, that line's explanation; inside a lower panel, that panel's explanation; otherwise the **price reading**.

Price reading for the hovered day: date, price, change over 1 week, 1 month and 1 year, distance from the 52-week high, trend state (up/down/mixed against the 200-day), RSI, P/E in long haul, and that day's verdict with its one-line reason.

Explanation texts live in one place (a Python dict or TOML file) and are tested to exist for every indicator key. Evidence wording must match the research summary below; no new claims.

### 4. Verdict rules (fixed rules, no AI)

6–12 months, evaluated on a given day:
- trend **up** = price above the 200-day average and the average higher than 21 trading days earlier; **down** = below and falling; otherwise **mixed**.
- **Good entry**: trend up and (%B < 0.2 or RSI < 40): "pullback inside an uptrend"; or trend up and 12-1 momentum > 0 with nothing stretched: "steady uptrend".
- **Stretched**: RSI > 70 or %B > 0.95.
- **Wait**: everything else ("trend is down" or "no clear trend").
- Reasons listed under the verdict, each marked +, – or ·: trend, Bollinger position, RSI, 12-1 momentum, distance from the 52-week high.

Long haul:
- P/E percentile of today within the window: < 30% → **Attractive**, > 70% → **Expensive**, else **Fair**.
- Reasons: P/E vs the window median, quality checks, 3-year return (over +100% flagged as "long-run winners tend to cool"), volatility and the worst drawdown in 5 years.
- If quality fails, the verdict cannot be better than Fair, and the reason says why.
- **Point in time.** The P/E percentile and median for a day use only the trailing window ending that day (up to 5 years, 1260 trading days), never the visible chart range or later data. Trailing EPS on a day is the latest annual (or quarterly TTM) EPS whose report was available by then; when only the fiscal year-end date is known, treat it as available 90 days after year-end. No interpolation between years. Negative or missing EPS → P/E "not available" for that day.
- At least 2 years of P/E history are needed before a long-haul verdict is shown; otherwise "not enough history" with the reasons that are available.
- Quality is a current snapshot only. Today's verdict uses it; the hover verdict for past days leaves quality out and says so ("quality: today's snapshot, not used for past days").
- **Quality fails** = the ported quality score is below its pass mark, or a must-pass rule fails (net margin > 0), using the same six checks and thresholds as `market-leaderboard/engine/quality.py` (ROE, net margin, debt/equity, FCF > 0, revenue growth, market cap). Statuses `thin`, `distorted` and `no_data` mean "quality not available": they don't cap the verdict, but the reason line says quality could not be judged. FCF yield is shown, not scored.
- If both a Good entry and a Stretched condition hold on the 6–12-month side, Stretched wins.

The thresholds live in config (`config/analysis.toml`) and the verdict box always carries the line: "Fixed rules on the readings above, not AI. A timing aid for a stock you already want, not a prediction."

### 5. Which stocks get a page, and how you get there

- One page per ticker for **holdings, the watchlist (`config/watchlist.toml`) and Ideas candidates**, written as `out/site/analysis/<ticker>.html` (or one page with embedded data per ticker; builder's choice, see below).
- Links: each Desk watchlist row, each holding, and an "Analyse" link on each Ideas card. A ticker picker on the analysis page switches between them.
- **Funds and ETFs**: chart, trend, momentum, stretch and risk work as for stocks. P/E, quality and the long-haul valuation verdict are replaced by "not available for funds", with a link to the fund look-through. The long-haul verdict for a fund is not shown.
- Type comes from yfinance `quoteType`: EQUITY is a stock; ETF, MUTUALFUND and INDEX are handled like funds.
- **Stand-ins** (`config/instruments.toml`, a holding priced through another Yahoo series such as an index or a different share class): the page is titled with the holding's name, the chart uses the stand-in series, and a note under the header says which series stands in and why.
- **Crypto** (CRYPTOCURRENCY, and the crypto test positions already excluded from the risk models) gets no page.

### 6. Layout (mockup A)

- Header: name, ticker, last price and day change, horizon control on the right.
- Left (main): indicator chips, range and style controls, the price panel and the lower panels.
- Right column (about 330 px): the verdict card, then the four info boxes.
- Hover box floats next to the cursor on the chart; chips and boxes show their explanation in a popover beside them.
- Under about 1100 px wide the right column moves below the chart. On touch, tapping does what hovering does. Arrow keys move the crosshair when the chart has focus; chips are real buttons with `aria-pressed`.
- Huurre tokens and fonts from `views/core.py` (Host Grotesk, Atkinson Hyperlegible Mono). Candles: hollow = up, filled = down, so up and down don't depend on colour alone.
- Professional finish as for the other views: an impeccable pass and screenshots at 1280 and 390 px wide before calling it done.

## Non-goals

- Short-term trading or anything under about 3 months, intraday data, alerts on indicator crossings.
- AI-written verdicts or explanations generated at run time. The explanations are fixed text.
- News and social signals. The page links to the stock's news brief once the discovery project has built it.
- Price targets, expected returns or position sizes from these indicators. The page does not feed the optimiser.
- Backtesting the verdict rules in this project (possible later).

## Anti-goals (a failure even if it works)

- A verdict that reads like advice or certainty ("Buy now!"). The wording stays "Good entry / Wait / Stretched" with reasons and the disclaimer.
- An explanation that claims stronger evidence than the research supports (for example calling RSI predictive).
- Numbers in the hover that differ from the numbers in the boxes, or JavaScript recomputing indicators differently from Python.
- Any real holding value, amount or result in tracked files, commit messages, tests or screenshots meant for the repo.
- A cluttered chart: everything on at once by default.

## Constraints

- Static site built by the existing CLI, like the other views; no new server needed. The page works from `out/site` served on `127.0.0.1`.
- Data from yfinance only, cached under the git-ignored `data/`. **The price store holds closes only**, so candles need daily open, high and low: add an OHLC store (for example `data/ohlc/<ticker>.csv`, adjusted like the closes), updated incrementally the same way as `prices.update`. If OHLC is missing for a ticker, the page falls back to the line chart and hides the candle toggle.
- EPS history and quality fields from yfinance, cached; missing values show "not available", never guessed.
- No new JavaScript chart library: hand-drawn SVG like the rest of the desk, plus a small hover script.
- Holdings are never sent to outside services; this page needs no outside service except yfinance downloads by ticker.
- Indicator code tested with known-answer cases (for example a constant series gives RSI undefined/50 handling as specified, a linear series gives a known SMA; Bollinger width zero on a flat series) and fixtures with invented prices.
- Reported numbers must match code output.

## Research summary (for explanation wording)

- 12-1 momentum: strong (Jegadeesh & Titman 1993; replicated worldwide). Momentum crashes after sharp market rebounds (Daniel & Moskowitz 2016).
- Nearness to the 52-week high: strong (George & Hwang 2004, *Journal of Finance*); better predictor than raw past returns, profits do not reverse.
- Price against the 200-day / 10-month average: moderate; mainly cuts drawdowns (Faber, "A Quantitative Approach to Tactical Asset Allocation").
- RSI, Bollinger Bands, MACD: weak or mixed; single-market studies show profits, but many rules fail after correcting for data snooping (Sullivan, Timmermann & White 1999). Use for timing an entry, not choosing the stock.
- Profitability/quality: strong (Novy-Marx 2013, gross profitability premium).
- Long-term reversal over 3–5 years: De Bondt & Thaler (1985).

## Decided by the owner

- Pick the holding horizon first; the chart and metrics follow from it.
- Two horizons are enough for now: 6–12 months and long haul.
- A verdict is wanted, with the reasons shown.
- Start with the four groups: trend, stretch, momentum, risk; long haul adds valuation and quality.
- Explanations appear on hover, not behind a click.
- Layout A (chart left, verdict and boxes right, floating hover box).
- Pages for holdings, watchlist and Ideas candidates.

## My calls (the owner can change these)

- Indicators and verdicts computed in Python at build time and embedded as data; the browser only draws and looks up values.
- P/E history rebuilt from price ÷ trailing EPS, about 4–5 years, labelled as short history.
- Funds get no P/E, quality or long-haul verdict.
- Chart drawn in the stock's trading currency, as on the Desk view.
- Verdict thresholds as in section 4, kept in `config/analysis.toml`.
- Long-haul P/E is point in time (trailing window, EPS available 90 days after fiscal year-end, no interpolation); at least 2 years needed for a verdict; past-day verdicts leave out quality.
- "Quality fails" follows the ported market-leaderboard rules; thin/distorted/no-data means "not available", not a fail.
- Stretched beats Good entry when both hold.
- Indices count as funds; stand-ins get a page under the holding's name with a note; crypto gets no page.
- Hand-drawn SVG, no chart library; Huurre look rather than the dark theme the design tool suggested.

## Left to the builder

Module layout (suggested `indicators.py`, `verdict.py`, `explain.py`, `views/analysis.py`); one HTML file per ticker versus one page loading per-ticker JSON; how bars are grouped for long ranges; exact popover positioning; how the ticker picker is built; the CLI command name; test fixtures (invented prices only).
