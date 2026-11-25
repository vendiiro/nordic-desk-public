# Data contract: `out/desk.json`, `out/aamu.json` and `out/goal.json`

Written by `nordic-desk build`. The front end reads these files. Fractions are plain numbers (0.123 = 12.3%); money is in euros unless the key says `usd`; dates are `YYYY-MM-DD`. All three files are git-ignored because they hold real holdings.

The test `tests/test_build.py` checks that the top-level keys below are exactly the keys in each file.

## desk.json

- `meta`: `close` (last US close used), `built` (UTC timestamp), `holdings_as_of`, `eurusd` (USD per EUR at `close`), `source`, `skipped` (watchlist tickers left out for lack of a year of prices).
- `watchlist`: list, one row per watchlist ticker: `ticker`, `held` (bool), `last_usd`, `d1`, `w1`, `m1`, `m3`, `m6`, `ytd`, `y1`, `hi_usd`, `lo_usd`, `pos` (0 to 1 in the 52-week closing range), `vol` (21-day, annualised), `mdd` (worst fall over the year), `beta` (to SPY, in USD), `spark` (last 64 closes, USD).
- `detail`: object keyed by ticker: `dates`, `close_usd` (last 253 closes), `spy_scaled` (SPY scaled to the stock's first close), `facts` (`name`, `sector`, `industry`, `market_cap` USD, `pe_trailing`, `pe_forward`, `dividend_yield` in percent, `earnings` date; any may be null; `{}` when Yahoo gave nothing).
- `compare`: `dates`, `series` (ticker to list, rebased to 100 at the first date), `spy` (same for SPY).
- `portfolio`: `value` (positions revalued at `close` plus cash and unmodelled), `value_report` (sum at the report date), `cost` (positions only, no cash), `unrealised` (`value` − `cost` − cash), `cash`, `vol`, `beta`, `worst`, `ret`, `tech`, `enb`, `history` (`dates`, `value`: today's positions valued over the window), `spy_history` (same money in SPY, in euros).
- `impact`: `window` (`start`, `end`), `holdings` (list sorted by risk share: `name`, `ticker`, `note`, `value`, `weight`, `risk`, `vol`, `corr`, `down`, `ret`, `tech`), `unmodelled` (list of `name`, `value`; counted as zero return), `candidates` (list of `ticker`, `vol`, `corr`, `down`, `ret`), `scenarios` (list; adds: `id` = `add-<ticker>-<amount>`, `kind`, `ticker`, `amount`, `own_risk`; sells: `id` = `sell-<ticker>`, `kind`, `ticker`, `name`, `amount`; both: `vol`, `beta`, `worst`, `ret`, `tech`, `enb`, `total`).
- `lookthrough`: funds opened up into their published top holdings (Yahoo; `holdings_from` in `config/instruments.toml` names a stand-in fund): `top` (up to five, largest first: `key`, `name`, `share`, `direct`, `via_funds`, all shares of the portfolio), `not_broken_down` (share in funds outside their published top holdings or without data), `no_data` (held tickers without holdings data), `source`.
- `forecast`: next 21 trading days with today's positions: `horizon_days`, `sigma_daily` and `vol_ann` (EWMA, lambda 0.94), `value`, `low` and `high` (95% range in euros), `backtest` (`n` days, `hits`, `rate`, `expected` 0.05, `p_value` Kupiec, `start`) over all history the holdings share.
- `record`: `null` without `--record`; otherwise `dates`, `value`, `deposits`, `twr` (growth of 1), `spy` (SPY in euros, growth of 1 on the same dates), `vol_1y` (weekly, annualised over the last 52 weeks).

## aamu.json

- `meta`: same as in desk.json.
- `portfolio`: `value`, `overnight` (euros), `overnight_pct`, `since_cost_pct`, `fx_effect_1d` (part of the overnight move that came from EUR/USD).
- `spy_overnight`: SPY's last daily return in euros.
- `movers`: `up` and `down`, three watchlist rows each (`ticker`, `d1`, `last_usd`).
- `tiles`: list per watchlist ticker: `ticker`, `last_usd`, `y1`, `rebased` (one year, 100 at the start, all on one scale).

## goal.json

Written by `build` from `goalrange.build_goal` (spec `docs/superpowers/specs/2026-11-25-goal-range-design.md`). Values are in euros, fractions plain.

- `available`: false when only excluded test positions are held; then only `why` follows.
- `close`, `value` (today's total, including cash and excluded positions), `excluded`, `goals_file` (whether `config/goals.local.toml` was read).
- `history_start`, `history_end`, `history_years`: the common daily history the paths are drawn from.
- `drift` (stated yearly return of the invested part), `invested` (share of the value in modelled positions; the paths centre on `invested` × `drift` because cash earns 0%), `sensitivity` (0.02), `n_paths`, `block` (days per block), `horizon_years`.
- `start_value` (`value` + lump), `monthly`, `lump`, `contributions` (money put in by each year end, start value included).
- `years`: list per year: `year`, `date`, `p5`, `p25`, `p50`, `p75`, `p95` (value with savings), `growth` (quantiles of the return without new money, keyed `"0.05"` to `"0.95"`).
- `goal`: null without a target; else `target`, `year`, `years_ahead`, `note` (why the chance is missing), `prob`, `prob_low`, `prob_high` (drift −2 / +2 points), `monthly_50`, `monthly_75` (monthly saving for an even and a three-in-four chance).
- `drawdown`: `limit`, `prob_exceed`, `p50`, `p95` (largest fall of the invested value along the way, savings removed).
- `anchor`: SPY's yearly return in euros over the stored history (`rate`, `from`, `to`), for reference only.
- `backtest`: null under four years of history; else `n`, `inside_90`, `inside_50`, `p_90`, `p_50` (Kupiec), `n_independent`, `start`, `end`.
- `ledger`: `matured`, `held`, `pending`, `show` (from 5 matured rows), `by_kind`, `first`. Rows are in `data/ledger/forecasts.jsonl`.

## Method notes

- Risk weights use the holdings values from the Nordnet report date; `portfolio.value` revalues the same positions at `close`. The risk window is the 252 daily returns ending at `close`.
- Watchlist metrics are in USD (log returns for `vol` and `beta`); portfolio risk is in euros with simple returns.

## cards.json

Written by `nordic-desk card` and `nordic-desk ideas` (merged on each run).

- `meta`: `close`, `built`, `default_amount` (the amount selected when the page opens, from `card_default` in `config/target.toml`).
- `groups`: `diversify`, `growth`, `searched`, each a list of tickers.
- `cards`: object keyed by ticker: `name`, `sector`, `industry`, `currency`, `type` (`EQUITY` or `ETF`), `size` (`large`, `mid`, `small` or null), `market_cap`, `results` (list of `year`, `revenue`, `net_income`, listing currency), `price` (`dates`, `close`, `spy_scaled`, `ret`, `worst_fall`; up to 5 years), `analysts` (`count`, `rating_share`, `target_mean`, `target_low`, `target_high`, `upside`, `buy_below`, `sell_above`, `status`), `impact` (null or `corr`, `down`, `before`, `expected_before` {`value`, `covered`}, `amounts` keyed by the amounts in `card_amounts` (`config/target.toml`; default "500", "1000", "2500", "5000") with `vol`, `beta`, `worst`, `enb`, `tech`, `expected`, `own_risk`), `impact_note`.
- `lookthrough` on each card (null when the portfolio comparison is not available): funds looked through with their published top holdings (Yahoo). `focus` (company keys: the candidate itself, or for a fund the three companies it adds most money to), `names` (key to name), `before` (key to portfolio share now), `amounts` (amount to {key: share after}), `not_broken_down` (share of the portfolio in funds outside their published top holdings, or in funds without holdings data), `no_data` (held tickers with no holdings data). Company keys are Yahoo symbols; only listings and share classes in `SAME_COMPANY` (`lookthrough.py`) are joined (`ASML.AS` is `ASML`, `GOOG` is `GOOGL`), so different companies that share a base symbol stay apart.
- `brief` on each card (null until `nordic-desk brief <ticker>` has run; saved in `data/news/briefs/`): `ticker`, `name`, `model`, `written`, `cost_usd`, `range` (first and last article date, or null), `what` and `for` / `against` (up to three each) as {`text`, `sources`: article ids}, `events` ({`date`, `text`, `sources`}), `tone` (`positive`, `neutral`, `negative` article counts), `articles` (`id`, `url`, `title`, `date`, `sites`). AI-written and unchecked: it never enters any number on the card.
- `errors`: ticker to message for tickers that could not be built.
- Each card also has `price_note` (why there is no chart) and `history` (null on the first run; otherwise `since` date, `target` change of the mean target, `rating_points` change of the buy share in points, `status_before`).
- `alerts` in cards.json and the file `out/alerts.json`: cards from the latest run whose status became "below buy threshold" or "above sell threshold" since the previous snapshot (`ticker`, `name`, `now`, `before`).
- Snapshots: `data/analysts_history.csv`, one row per ticker and day (git-ignored).
