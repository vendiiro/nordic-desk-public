# Goal and long-range outcomes: design

Date: 2026-11-25. Owner: Iiro. Status: approved by the owner 2026-11-25. Builds on the risk models (`2026-11-19-risk-models-design.md`), the forecast window (`2026-11-23-forecast-window-design.md`) and the combined expected return (`2026-11-24-expected-return-and-vol-sizing-design.md`). Chosen from the ideation of 2026-11-25 (ideas A + P5, with the forecast ledger G built in from the start).

## Intent and why

The desk tells the owner how risky the portfolio is over the next month and what one stock might return in 12 months. It does not answer the question he invests for: "with this portfolio, this lump and this monthly saving, where could I be in 1–5 years, and how likely is my goal?"

- **A range, not a number.** Long-run returns of a single portfolio are close to unpredictable, but their spread is not. The page shows percentiles of value per year and the chance of reaching a goal, never one expected figure.
- **The drift is an assumption, shown as one.** A bootstrap of the stored history (2015 on) would carry that decade's strong US returns into every path. The paths keep the history's shape (volatility, fat tails, clustering) but are re-centred on a stated yearly return, and the page shows how the goal chance moves when that return is 2 points lower or higher.
- **Checked from day one.** The one-year range is back-tested on history, point in time, and every range the desk shows is written into a forecast ledger, so its own record builds up (idea G).

## Inputs

New git-ignored `config/goals.local.toml`, with a tracked `config/goals.example.toml` holding invented values:

```toml
# Invented example values. Copy to config/goals.local.toml.
target_eur = 50000        # optional: a goal value
target_year = 2031        # optional, needed with target_eur
monthly_eur = 300         # new money at each month start
lump_eur = 0              # extra money put in now, split pro rata to today's weights
max_drawdown = 0.30       # optional: the largest fall from a peak the owner can sit through
years = 5                 # how far the range reaches, 1 to 10
```

The portfolio is `config/holdings.local.toml` as today. Crypto test positions (`forecast.EXCLUDE`) count as cash, as in the risk models. New money is invested pro rata to today's weights of the modelled positions (a simple, stated rule; the allocation choice is the next feature).

## Model (`goalrange.py`)

1. **Daily portfolio returns in euros**, today's weights fixed: the same series `forecast.portfolio_forecast` builds (`rp`). Cash earns 0%.
2. **Re-centre:** log returns minus their mean, plus `ln(1 + drift) / 252`. Volatility, skew and clustering within blocks stay as they were.
3. **Block bootstrap** paths of `years × 252` days, 21-day blocks drawn with replacement from the whole common history, n = 5000, fixed seed. (Existing `bootstrap_range` uses 10-day blocks for one month; monthly blocks keep more of the volatility clustering over years.)
4. **Cash flows:** value starts at today's total + `lump_eur`; `monthly_eur` is added every 21 trading days.
5. **Outputs per path:** value at each year end, the largest peak-to-trough fall of the invested value (contributions removed, so new money does not hide a fall).

Because value is linear in contributions for a fixed return path, `V_T = V_0·G_0 + m·Σ G_t`, so the **monthly saving needed** to reach the target on each path is exact: `m = (target − V_0·G_0) / Σ G_t`. Its 50th and 75th percentiles answer "how much a month for an even chance / a three-in-four chance".

Result:

```
{drift, drift_source, history_start, n_paths, excluded,
 years: [{year, p5, p25, p50, p75, p95}],
 goal: {target, year, prob, prob_low, prob_high, monthly_50, monthly_75} | null,
 drawdown: {limit, prob_exceed, p50, p95} ,
 contributions: total euros put in by each year}
```

`prob_low` / `prob_high` repeat the goal chance with drift − 2 and + 2 percentage points.

## Back-test of the one-year range (point in time)

At every month start from 3 years after the common history begins: bootstrap only from days before that date, re-centred on the fixed drift, no contributions. Record which band the realised one-year return fell in. Report coverage of the 5–95 band (should be near 90%) and of the 25–75 band (near 50%), with n and a Kupiec-style p-value, reusing `forecast._kupiec`. Overlapping 12-month windows make neighbouring checks dependent; the page says so and shows n of non-overlapping years beside it.

## Forecast ledger (`ledger.py`)

- Every `build` run appends one row per range to `data/ledger/forecasts.jsonl` (git-ignored): `made` date, `kind` (`goal_1y`, `goal_Ny`, `risk_21d`), horizon end, quantiles in **returns**, not euros, the drift and a hash of the weights. One row per kind per week (same key rule as the risk cache), so daily runs do not flood it.
- When a row's horizon has passed, the next run scores it: which band the realised return hit, and the pinball loss. The page shows "own record: k of n ranges held" once n ≥ 5, beside the back-test.
- Adding `risk_21d` gives the first matured rows within a month.

## Page

A new page **Goal** (`views/goal.py`, `goal.js` draws only), linked from Today and the bar.

- Headline sentence: "With today's portfolio and 300 € a month, the middle path reaches about X € by 2031; the goal is reached in about N of 10 paths." Numbers come from Python; wording avoids promises ("in about N of 10 simulated paths", never "will").
- Fan chart: years on x, value in euros, bands 5–95 and 25–75, median line, contributions-only line, target marker.
- Goal box: chance, the ±2-point sensitivity, monthly saving for an even and a three-in-four chance.
- Drawdown box: chance of a fall larger than `max_drawdown` along the way.
- Method and checks: drift and its source, history period, the back-test coverage, the ledger record, the survivorship and strong-decade caveats, "not investment advice".
- Without `goals.local.toml`: the range with `monthly_eur = 0` and a line saying how to add a goal.

## Non-goals

- Choosing what to buy with new money (next feature: allocation and rebalancing).
- Taxes, inflation-adjusted values, fees beyond what total-return prices include.
- Per-stock long-range forecasts.
- Any outside service: everything runs on local caches.

## Anti-goals

- One expected value shown without its range.
- A drift taken silently from the history's mean.
- Look-ahead in the back-test.
- Real amounts in tests, docs, screenshots or commit messages.

## Owner decisions (2026-11-25)

- **Drift:** a fixed long-run assumption, `drift = 0.07` (7% a year in euros) under `[goal]` in `config/analysis.toml`, editable. The SPY anchor from `expected.py` is shown beside it for reference only.
- **Where it lives:** a new Goal page (`goal.html`), linked from Today and the bar.
- **Longest horizon:** 10 years (`years` 1 to 10). Past 5 years the page notes that the stored history holds only about two non-overlapping 5-year spans.
- **Where it runs:** `build` computes the range, the back-test and the ledger, because it holds the euro price panel; the result goes into `out/goal.json`. `site` renders it. So the ledger grows on every `build` (and on every `site` that rebuilds stale Desk data).

## Left to the builder

Block length and path count tuning within the stated defaults, the exact JSON field names, chart details within the Huurre tokens, and how the weekly ledger key is formed.
