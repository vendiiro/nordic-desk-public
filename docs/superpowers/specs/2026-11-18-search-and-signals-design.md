# Search and signals: design

Date: 2026-11-18. Owner: Iiro. Builds on the engine and views in this repo (`docs/data-contract.md`, `src/nordic_desk/views/`).

## Intent and why

The portfolio is heavily IT (about 62% technology) because IT is the sector the owner knows. He wants to diversify away from it over time, and also to keep finding strong-growth IT and AI names. Nordnet shows a stock on its own. It does not say whether that stock suits *this* portfolio, or whether analysts think it is cheap. This feature adds a search page that answers, for any stock or ETF he looks up, four questions:

1. What has it done over the last years (price and results)?
2. Is it a well-known large company or a small one, and what sector is it, in plain words?
3. What do analysts think: share of buy ratings, target prices, and from those a buy threshold and a sell threshold?
4. What would adding it do to my portfolio: risk, IT weight, concentration, and the analyst-implied expected return, before and after?

Success: he can type a name or a ticker and decide in a couple of minutes, with the numbers' sources visible.

## Goals

- **Search by ticker or name**, like the Nordnet app, using Yahoo's search (`yfinance.Search`). Results list each listing separately (for example NOK on NYSE, NOKIA.HE in Helsinki, NOA3.DE on Xetra), with exchange, currency and type (stock or ETF).
- **Listings included:** US exchanges, Helsinki and Xetra, for stocks and ETFs. A result that has less than one year of daily prices on Yahoo is shown as "not enough price history" with no charts. Other exchanges are not shown, so duplicate or thin listings do not distort the charts. (Owner's rule: include them only if search stays simple and honest.)
- **Per result page ("candidate card"):**
  - Price history over 5 years (or since listing), in its own currency, with SPY scaled to the same start for comparison; worst fall over that period shown next to the return.
  - Size: market cap, with a plain label (large, mid or small company) using fixed cut-offs stated on the page.
  - Sector and industry in plain words, plus its correlation with the owner's portfolio over the past year and a one-line plain explanation ("moves mostly with your holdings" or "moves differently from your holdings").
  - Results: annual revenue and net income for the last 4 fiscal years from Yahoo, with growth per year. ETFs show "no company results (fund)".
  - Analysts: number of analysts, share of strong buy and buy ratings in percent (from Yahoo's latest recommendation counts), mean, low and high target prices, and the upside from the current price to the mean target.
  - **Buy threshold:** the price at which the upside to the mean target reaches the buy margin (default 15%, set in `config/signals.toml`): `buy_below = target_mean / (1 + margin)`.
  - **Sell threshold:** the mean target price (`sell_above = target_mean`), at which no upside to the consensus is left.
  - A status line from those: "below buy threshold", "between thresholds" or "above sell threshold", always shown together with the analyst count and rating share. Fewer than 5 analysts: the status is shown as "thin coverage".
- **Before and after in the portfolio**, for an amount the owner picks (500, 1,000, 2,500, 5,000 euros of new money): volatility, beta, worst fall, effective holdings, technology share, and the analyst-implied expected return of the portfolio. Each change is marked as raising or lowering risk or expected return.
- **Analyst-implied expected return:** each holding's upside to its mean target, weighted by portfolio weight. Holdings without targets (funds, ETFs, ETH) count as "no estimate". The share of the portfolio with an estimate is shown next to the number, so a figure resting on a small part of the portfolio is visible as such.
- **Suggestions without searching:** a short list of ideas in two groups from `config/ideas.toml`: "diversify away from IT" (for example health care, consumer staples, energy, financials, Europe and Finland ETFs) and "IT and AI growth". Each idea is shown as the same candidate card. The lists are the owner's to edit; the app does not pick stocks itself.

## Non-goals

- Forecasts of future prices beyond what the analysts' targets say (GARCH-t and other forecasts stay in the later plan).
- News, social media sentiment, or text analysis.
- Placing orders or connecting to Nordnet.

## Anti-goals (a failure even if it works)

- A buy or sell signal shown without its basis: the analyst count, rating share and target range must always sit next to it.
- Mixing listings or currencies on one chart, or filling missing data with guesses. Missing data says "not available".
- Recent winners shown without their worst fall: a strong past return must never look risk-free.
- Real holdings or values in tracked files: the page is written to `out/` like the other views.

## Constraints

- Data from Yahoo through `yfinance` only (Massive MCP stays a manual fallback). Cache fetched candidate data under `data/` so repeat searches do not refetch within a day.
- Portfolio maths reuses `risk.py` (EUR panel, `add_scenario`); non-USD and non-EUR listings are converted to EUR with Yahoo FX before risk numbers are computed.
- Static pages like the other views: search runs in the command line, not in the browser. `nordic-desk search <text>` prints the matches; `nordic-desk card <ticker>` (one or more tickers) adds candidate cards to the site; the ideas list builds cards for every entry.
- Page style: Huurre (light desk), Hallmark floor, sentence-case labels, Helsinki times, "not investment advice" on the page.

## Decided by the owner

- Signals rest on the last years' results, the last years' price development, and analyst ratings and targets.
- Buy and sell thresholds come from analyst target prices.
- Expected return in the before-and-after uses the position's weight in the portfolio.
- Both diversifying ideas and IT/AI growth ideas are wanted.
- Helsinki and European listings only if they fit simply and honestly.

## My calls (the owner can change these)

- Buy margin 15%; sell at the mean target; "thin coverage" below 5 analysts.
- Size labels: large above 10 billion USD, mid 2 to 10 billion, small below 2 billion.
- Search runs in the command line and the results become static pages, because the site has no server. A browser search box would need a local server, which is a later decision.
- Exchanges allowed: US (NYSE, Nasdaq, NYSE Arca), Helsinki, Xetra.

## Builder questions settled (my calls)

- **Short history:** the before-and-after needs at least 254 aligned daily closes in the risk window, the same rule as held tickers. With fewer, the card shows "not enough price history for the portfolio comparison" and still shows the other sections.
- **Where cards live:** a new `out/cards.json` (the data contract gains this third file) and `out/site/cards.html` with one card per candidate. `nordic-desk card` loads the holdings and builds its own euro panel (reusing `panel.py` and `risk.py`), so it does not depend on `build` having run, only on prices being updated; it fetches the candidate's prices itself.
- **Expected return of held positions:** analyst targets are fetched for every held ticker too and cached daily in `data/analysts.json`. A holding whose fetch fails or that has no targets counts as "no estimate".
- **Currencies:** price charts, targets and the buy and sell thresholds stay in the listing's own currency (taken from Yahoo); only the risk and expected-return numbers are converted to euros.
- **Technology share for candidates:** a candidate counts as technology when Yahoo's sector is "Technology"; held positions keep the flag from `config/instruments.toml`.

## Left to the builder

File layout, caching format, the exact card layout within the Huurre style, the tests.
