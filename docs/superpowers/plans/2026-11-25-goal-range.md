# Goal and Long-Range Outcomes Implementation Plan

**Goal:** A Goal page with the portfolio's 1–10-year value range, the chance of reaching a goal, the monthly saving needed, a drawdown check, a point-in-time back-test of the one-year range and a forecast ledger.

**Architecture:** `goalrange.py` (portfolio returns, re-centred block bootstrap, cash flows, back-test) and `ledger.py` (append, score, summarise) are called from `build`, which owns the euro price panel, and write `out/goal.json`. `views/goal.py` renders the page as static HTML and SVG; there is no page script, so the browser computes nothing. `site` writes `goal.html`; the bar and Today link to it.

**Tech stack:** Python 3.12, numpy, pandas, pytest; Huurre tokens.

**Spec:** `docs/superpowers/specs/2026-11-25-goal-range-design.md`. Branch `claude/project-thread-ftcqvd`.

## Global constraints

- Daily portfolio returns: today's weights fixed, weight = position value ÷ (all positions + cash); `forecast.EXCLUDE` positions count as cash; cash earns 0%.
- Re-centre in log space: `lr − mean(lr) + ln(1 + drift) / 252`.
- 21-day blocks, drawn with replacement from all start days, fixed seed. 5000 paths for the range, 2000 per back-test date.
- Contributions: the lump at day 0 (split pro rata), `monthly_eur` at day 0, 21, 42, … (12 a year). Year y ends at day 252·y.
- Monthly saving needed per path: `max(0, (target − V0·G_T) / Σ_k G(t_k→T))`; report its 50th and 75th percentiles.
- ±2-point drift sensitivity shifts every path's log growth by `Δ·days/252`; no re-simulation.
- Drawdown: of the growth index (contributions removed), daily, over the whole horizon.
- Back-test: month starts from day 756, only earlier days in the pool, no contributions, realised one-year log return against the 5–95 and 25–75 bands, Kupiec p with p = 0.10 and 0.50.
- Ledger: `data/ledger/forecasts.jsonl`; one row per kind per ISO week; quantiles as returns; scored when the panel holds `days` trading days after `made`; realised return = Σ wᵢ·(Pᵢ,end / Pᵢ,made − 1).
- No promise wording, "not investment advice", invented values in tests and docs, no outside service.
- Tests: `uv run --no-sync pytest <file> -q`; never two pytest runs at once.

## Tasks

1. **Config.** `GoalTh(drift, n_paths, block)` under `[goal]` in `config/analysis.toml`; `goalrange.load_goals(path)` reads `config/goals.local.toml` with validation (years 1–10, target needs a year inside the horizon), defaults when the file is missing; tracked `config/goals.example.toml`.
2. **Range.** `portfolio_returns`, `recentre`, `simulate` (percentiles by year, contributions, goal box, monthly needed, sensitivity, drawdown). Tests: zero-volatility returns give the exact compound value; monthly-needed reproduces the target on a known path; sensitivity orders low < base < high; drawdown of a monotone path is 0; seed makes runs repeatable.
3. **Back-test.** `backtest_1y(rp, drift)`; tests: too little history gives None; no look-ahead (changing days after a check date leaves its band unchanged); i.i.d. returns centred on the drift cover close to 90% / 50%.
4. **Ledger.** `ledger.record`, `ledger.score`, `ledger.summary`; tests: weekly de-duplication, scoring only after maturity, realised return and pinball loss on invented prices, "own record" shown from n ≥ 5.
5. **Build.** `goal_range(...)` from `build` writes `out/goal.json`, records and scores the ledger; test through the `built` fixture.
6. **Page.** `views/goal.py` (headline, fan chart SVG with a table fallback, goal box, drawdown box, method and checks), `site` writes `goal.html`, nav gets Goal, Today links to it. Tests on the HTML: no promise words, the no-goal state, the 5-year note past 5 years.
7. **Browser check** at 1280 and 390 px on invented data; then a whole-branch review; fix Critical/Important findings test-first; PR.

## Review focus

1. A goal already met by the start value: monthly needed is 0, never negative.
2. A target year past the horizon or in the past: the goal box explains, nothing crashes.
3. Everything excluded (only crypto): no Goal data, the page says why.
4. Ledger rows from an older weight set still score with their own weights.
