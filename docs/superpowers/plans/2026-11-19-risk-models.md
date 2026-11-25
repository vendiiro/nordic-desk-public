# Risk models Implementation Plan

> **For agentic workers:** executed natively (superpowers:executing-plans). TDD per task.

**Goal:** GARCH-t, block bootstrap and Markov switching next to EWMA, with out-of-sample calibration that picks the headline model; and an SLSQP optimiser next to the greedy split.

**Spec:** `docs/superpowers/specs/2026-11-19-risk-models-design.md`.

## Global Constraints
- Crypto tickers left out of the model panel: `CBUT.DE`, `ETH-EUR` (their value joins cash).
- Horizon 21 days; one-day line at the 5% level (z 1.645 for normal models); refit every 21 days; bootstrap blocks of 10 days.
- Run every `uv` command with `--no-sync` while the owner's server holds `nordic-desk.exe`.

### Task 1: Model one-day sigmas (`forecast.py`)
`garch_t_sigma(r) -> (sigma_next, params)`, `regime_sigma(r) -> (sigma_next, p_high, sig_low, sig_high)`, `bootstrap_range(r, horizon, block, n, seed) -> (q05, q95)` of 21-day returns. Tests on simulated data: GARCH sigma near the true level; regime finds the high-vol state on data with a volatile stretch at the end; bootstrap quantiles bracket zero and scale with the input.

### Task 2: Rolling calibration (`forecast.py`)
`rolling_lines(r, model, refit=21, min_train=504) -> (one-day sigma or loss line per predicted day)`; `christoffersen(hits) -> p`; `calibrate(r) -> {model: {n, hits, rate, kupiec_p, christoffersen_p}}`. Tests: no look-ahead (changing a later return never changes an earlier line); Christoffersen low p on clustered hits.

### Task 3: Portfolio forecast with all models, cache, headline (`forecast.py`, `build.py`)
`portfolio_forecast` returns `models` (per model: sigma_daily, low, high, calibration) and `headline`; crypto excluded; cache per ISO week and weights. Contract updated. Test with synthetic panel; cache hit skips refits.

### Task 4: Impact view
"Next month" shows the headline range, regime probability, and a table of the four models with hit rate and both p-values. Test texts.

### Task 5: SLSQP optimiser (`plan.py`)
`optimise_allocation(panel, values, cash, tech, candidates, amount, tech_max) -> dict` like `plan_allocation`. `run_plan` returns both (`greedy`, `optimised`); Ideas page shows both. Tests: two uncorrelated assets split near half-half; tech cap respected.

### Task 6: Real run, lint, review.
