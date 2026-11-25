# Risk models and optimiser: design

Date: 2026-11-19. Owner: Iiro. Builds on `forecast.py` (EWMA) and `plan.py` (greedy split).

## Intent

Next-month risk from more than one model, each checked against history without look-ahead, so the page can lead with the model that has actually been right. And a proper optimiser for new money next to the greedy split.

## Decided by the owner

- New libraries allowed: `arch`, `statsmodels`, `scipy`.
- Crypto positions (iShares Blockchain ETF, Ether tracker) are left out of the models; they count as zero return like cash. They were a test position.
- History for the models starts no later than 2015 (the IT ETF's Xetra listing starts in December 2015, which sets the common start).

## Models (all on daily portfolio returns in euros, today's weights held fixed)

- **EWMA** (existing): lambda 0.94.
- **GARCH(1,1) with Student-t errors** (`arch`), fitted on percent returns.
- **Block bootstrap**: 21-day sums of returns drawn as 10-day blocks from the past history; no parameters.
- **Markov switching variance** (`statsmodels` MarkovRegression, 2 regimes): today's probability of the high-volatility regime and each regime's volatility; the one-day sigma mixes the regimes by the filtered probabilities.

Each gives a one-day sigma (for calibration) and a 21-day 95% value range.

## Calibration

Rolling and out of sample: refit every 21 trading days on all data up to that day, predict each following day's one-day 95% loss line with the fitted parameters (GARCH and Markov update with the new returns, no refit; bootstrap uses the empirical 5% of the past 500 days). Over all predicted days report hit rate, Kupiec p-value and Christoffersen independence p-value. The headline model on the page is the one with the highest minimum of the two p-values; the others are shown in a table. Calibration is cached in `data/forecast_cache.json` per ISO week and set of weights, because refitting takes about a minute.

## Optimiser

`scipy.optimize.minimize` (SLSQP) over non-negative euro amounts for the ideas that sum to the new money, minimising portfolio variance with the technology share at or under the cap (or under the lowest reachable share when the cap cannot be met). Shown next to the greedy split.

## Non-goals

Forecasting returns or prices; intraday data; models per single stock.
