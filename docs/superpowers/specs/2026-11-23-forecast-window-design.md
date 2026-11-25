# Forecast window: design

Date: 2026-11-23. Owner: Iiro. Builds on the analysis page (`2026-11-20-stock-analysis-page-design.md`), the analyst history (`history.py`), the risk forecast check (`forecast.py`), and the Huurre views. The approved mockup is "A + B" from the brainstorming session (`.superpowers/brainstorm/20383-1795413179/content/forecast-layouts.html`, git-ignored, invented data).

## Intent and why

The desk now gives verdicts, analyst targets and risk ranges, but the owner can't tell whether any of them deserve trust for his stocks. He invests for the long term in lumps of a few thousand euros, and he keeps facing the same three questions:

1. **Do the desk's signals actually help?** ("Good entry" versus "Wait", the analyst targets, the 95% risk range)
2. **Should this lump go in now, or be spread over a few months?**
3. **How far should I trust an analyst target's upside?**

This project answers all three with forecasts that are checked against what really happened afterwards, using data already on his computer. Owner's choice (2026-11-23): ideas 1–3 from the research summary, shown **both** on one new Forecasts page **and** as short lines inside the Analysis and Ideas pages.

Success: before a purchase he opens the stock's Analysis or Ideas card and sees three things: the verdict's own track record for that stock, a realistic upside next to the analyst target, and how often buying at once beat spreading. The Forecasts page holds the full evidence.

## Goals

### 1. Scorecard: did the signals help? (`scorecard.py`)

- **Universe:** every analysis subject with quote type EQUITY, ETF or MUTUALFUND (not crypto, and not INDEX: a price index has no dividends and can't be bought), with split-only OHLC (`data/ohlc_split/`) and total-return closes (`data/prices/`). Stocks and funds are pooled in the group rows; the stock filter shows one ticker at a time.
- **Currency:** from `data/fundamentals/<t>.json` `currency`, falling back to the instrument's currency in `config/instruments.toml`. A ticker with no known currency, or one other than USD or EUR, is left out and listed under the table.
- **Calendar:** each stock's own trading days. SPY and EUR/USD are read as of each stock date (the last available close on or before it). "Next H trading days" counts the stock's own days. For a EUR stock, SPY's return is measured in euros, so the EUR/USD move is included.
- **Verdicts back in time:** for each subject, compute the 6–12-month entry verdict (`indicators.compute` + `verdict.entry_verdict`) on every day of the full stored history. Indicators use only past data, so the rebuilt verdicts are point in time. A test proves it: appending future prices must not change any earlier verdict.
- **Samples:** the first trading day of each month from the first month with a verdict that isn't "Not enough history yet". One sample per stock per month.
- **Outcome:** the excess return over the next H trading days, H ∈ {63, 126, 252}, default **126 (6 months)**. Excess = stock return − SPY return, both from total-return closes and both in euros (USD converted with `EURUSD=X`). Stocks quoted in other currencies (SEK, DKK, GBp, …) are left out of the scorecard and listed as such. A sample whose window runs past the last close is dropped.
- **Groups:** one row per verdict line: pullback, steady, stretched, wait (trend down), wait (no clear trend).
- **Statistics per group, clustered by month and corrected for overlap:**
  - first average the excess within each month (stocks in the same month move together);
  - n months, n samples, and the share of samples that beat SPY;
  - the mean of the monthly averages, with a 95% interval from a Newey-West (HAC) standard error with lag h − 1, where h = H/21 months. Consecutive monthly windows overlap by (h − 1)/h, so a plain t-interval would be far too narrow;
  - effective windows = n months / h.
- **Reading** (fixed rules):
  - "too few" when there are fewer than 12 effective windows (for example, 72 months at the 6-month horizon);
  - for Good entry rows, "helps" when the interval is entirely above 0 and "works against" when it is entirely below 0;
  - for Wait and Stretched rows the direction is reversed (helps = interval entirely below 0);
  - otherwise "no clear edge".
- **Per stock:** the same statistics for each ticker and verdict group, computed from its own monthly samples (no clustering needed). These feed the line on the Analysis page. Many per-stock tests run at once, so a per-stock reading says only "too noisy to trust alone" (fewer than 12 effective windows, or an interval that crosses 0) or "consistent with the pooled reading" (the interval clears 0 in the same direction as a group reading of "helps"). It never says "helps" on its own.
- **Risk-range row:** show the existing portfolio 95% range check (`desk.json` → forecast → backtest: hits / n, expected 5%, Kupiec p) as it is. No new computation.
- **Analyst-target row:** from `data/analysts_history.csv`, de-duplicated to the first snapshot per ticker per calendar month (daily rows are near-copies). A snapshot is checked once 252 of the ticker's trading days have passed:
  - "met at 12 m" means the split-only close (`ohlc_split`; targets are price targets, so no dividends) 252 trading days later is ≥ the mean target;
  - "met at some time" means any close in between was ≥ the target.
  - Until 30 de-duplicated snapshots can be checked, show "too early: first check <date of oldest snapshot + 12 months>".
- **Survivorship warning, always shown:** "Stocks are the ones you hold or watch today; past winners are over-represented, so these numbers flatter the signals."

### 2. Lump now or spread it? (`lumpspread.py`)

- **Subjects:** the same universe, currency rules and calendar as the scorecard, plus SPY. Returns are in euros, from total-return closes.
- **Start dates:** the first trading day of each month s in the stored history.
- **Spread periods:** k ∈ {3, 6, 12} months.
- **The two strategies,** both judged at T = s + 12 months (252 trading days); a start date is used only when T exists:
  - "lump" buys everything at s;
  - "spread" buys 1/k of the amount on the first trading day of each of the k months starting at s. Cash waiting to be invested earns 0% (shortcut, stated on the page). Both are valued on the same end date, s + 12 months, so with k = 12 the last part is held for about one month. This is intended: it compares what each choice is worth one year after the money was ready.
  - A subject with no valid start date (under about 12 months + k of history) gets no lump/spread data. The page says "not enough history", and the Ideas line is hidden.
- **Per € invested:**
  - lump value L and spread value S at T;
  - the share of start dates where L > S, the median of L − S, the 5th percentile of L and of S (the "bad case"), and the worst L − S and worst S − L ("worst regret").
- **Output:** a 20-bin histogram of L − S, with bin edges stored.
- **Amount:** the page scales every euro figure by the amount typed, using values per €1. The browser only multiplies; it computes no statistics.
- **Wording on the page:** "Lump sum beat spreading about two-thirds of the time in broad markets (Vanguard, *Dollar-cost averaging just means taking risk later*). Spreading buys a smaller worst case, not a better average. History, not a promise."

### 3. Analyst targets, made realistic (`targets.py`)

- **Realistic upside** = analyst upside − overshoot.
  - Overshoot defaults to **0.15** (15 percentage points): Bradshaw, Brown & Huang (2013) found implied returns from 12-month targets exceeded actual returns by 15% on average.
  - Once the desk has ≥ 30 checked snapshots of its own, overshoot = the mean of (implied upside − actual 12-month return) over those snapshots. The page says which source is in use.
- **Base rates,** shown as one line rather than as a column: "Only 38% of targets are met after 12 months; 64% are met at some point during the year (Bradshaw et al. 2013)". They are replaced by the desk's own rates once ≥ 30 snapshots are checked.
- **Table:** one row per Ideas card with a mean target: price, mean target, analyst upside, realistic upside, and "our record so far" (checked snapshots for that ticker, or "too few").

### 4. Front end

**Forecasts page** (`out/site/forecasts.html`, a new "Forecasts" item in the menu, Huurre look, layout as mockup A):

- **Header:** title, one-line purpose, and data date.
- **§1 Scorecard:**
  - a horizon control (3 / 6 / 12 months) and a stock filter (all, or one ticker);
  - a **dot-and-interval plot**: one row per verdict group, with the point at the mean excess, a 95% interval line, and a zero line. It is labelled directly, and colour is never the only cue (each row also shows a text tag);
  - next to it, the same numbers as a table (the accessible fallback): times given, months, beat SPY %, mean ± interval, reading tag;
  - the risk-range and analyst-target rows go in the table;
  - the survivorship warning sits under the table.
- **§2 Lump or spread:**
  - stock select (optgroups Holdings / Watchlist / Ideas, plus SPY);
  - an amount input (`type="number"`, `inputmode="numeric"`, visible label, € suffix, default = `card_default` from `config/target.toml`);
  - a spread control (3 / 6 / 12 m, default 6);
  - the headline "X% of start dates, buying all at once ended ahead after 12 months", followed by the median gain in € and %;
  - a summary table (median value, bad case, worst regret, for lump vs spread);
  - a histogram with the zero line and the median labelled;
  - the Vanguard wording.
- **§3 Realistic targets:** the base-rate line, then the table.
- **Footer:** data sources, built date, "Not investment advice."
- **Hover and focus on chart marks** show the same numbers as the table. On a phone a tap does the same, and tables scroll sideways inside a wrapper.

**Inline additions** (mockup B):

- **Analysis page, 6–12-month verdict card:** under the reasons, a block "Track record for this stock: <verdict group> in N months since <year>. Beat SPY over the next 6 months X% of those times, average ±." with the per-stock reading tag. N counts sample months. When today's verdict is "Not enough history yet", or the stock is outside the scorecard universe, the block is hidden. When the stock has no past months in today's group, it reads "No past <group> months for this stock". The block links to `../forecasts.html#scorecard`.
- **Ideas card, analysts block:** "Realistic upside <x>" next to the raw upside, with the source (study or own record).
- **Ideas card, before-and-after block:** one line for the default amount and a 6-month spread: "Lump ended ahead in X% of past start dates; spreading cut the bad case from €A to €B", linking to `forecasts.html#lump`.

## Non-goals

- No AI and no new data sources. Everything comes from local caches the desk already fills (`update`).
- No changes to the optimiser or the expected-return row. The combined expected return is a later project (idea 4).
- No sell advice and no automatic purchase sizing (idea 7 is later).
- No intraday data, and no backtest of trading costs.

## Anti-goals (a failure even if it works)

- Calling a signal useful when its interval crosses zero.
- Hiding the survivorship bias, or rebuilding verdicts with any look-ahead.
- Treating overlapping or same-month samples as independent evidence.
- Real holding values, amounts or results in tracked files, tests, docs, commit messages or screenshots.
- Wording that reads as a promise ("will", "expect to gain").

## Constraints

- Static site, built by `nordic-desk site` from caches, like the analysis pages. The scorecard and lump statistics are computed in Python at build time and embedded as JSON. The page's script only switches between precomputed sets and multiplies by the amount.
- The build must stay reasonably fast: about 40 tickers × about 2,700 days of verdicts. Compute indicators once per ticker (vectorised); `entry_verdict` per row is fine.
- Reuse `indicators`, `verdict`, `analysis.subjects`/`slug`, `ohlc`, `prices`, `history.PATH`, `views.core` helpers and the Huurre tokens.
- All tests use invented prices. Known-answer tests for the clustering, the interval, the lump/spread arithmetic, the overshoot, and the no-look-ahead property.
- Professional finish as for the other views: a design pass and screenshots at 1280 and 390 px from invented data.

## Research basis (for page wording)

- Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*, JASA 102: score forecasts against outcomes.
- Vanguard research, *Dollar-cost averaging just means taking risk later*: lump sum outperformed about two-thirds of the time.
- Bradshaw, Brown & Huang (2013), *Do sell-side analysts exhibit differential target price forecasting ability?*, Review of Accounting Studies 18(4): implied returns 15% above actual; 38% of targets met at 12 months, 64% at some time.

## Decided by the owner

- Build ideas 1–3 (scorecard, lump vs spread, realistic targets).
- Show them both on a Forecasts page and inline in the Analysis and Ideas pages.
- Use the existing Huurre look, with UI guidance from ui-ux-pro-max.

## My calls (the owner can change these)

- Default scorecard horizon 6 months, comparing against SPY in euros. Non-USD/EUR stocks are left out for now.
- One sample per stock per month; intervals clustered by month, with a Newey-West correction for overlapping windows; "too few" below 12 effective windows; per-stock lines never say "helps" on their own.
- Each stock's own trading calendar, with SPY and FX read as of each date; INDEX quote types left out; funds pooled with stocks.
- Target snapshots de-duplicated to one per ticker per month, scored on split-only closes.
- 30 checked (de-duplicated) snapshots before the desk's own target record replaces the study.
- Lump vs spread judged 12 months after the start, with idle cash at 0%.
- Realistic upside = upside − 15 points, with no extra shrinkage.
- A dot-and-interval plot for the scorecard instead of bars (uncertainty is the point).

## Left to the builder

Module names (suggested above); JSON shapes; histogram bin placement; exact copy within the wording rules; how the stock filter, horizon and amount controls are wired; CSS within the Huurre tokens; test fixtures.
