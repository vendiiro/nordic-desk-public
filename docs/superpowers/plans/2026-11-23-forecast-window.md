# Forecast Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Forecasts page (signal scorecard, lump-vs-spread planner, realistic analyst targets), plus short lines on the Analysis verdict card and the Ideas cards. Every number is checked against what really happened afterwards.

**Architecture:** At `site` time, Python reads the local caches (`data/prices`, `data/ohlc_split`, `data/fundamentals`, `data/analysts_history.csv`, `out/desk.json`). It computes all statistics and writes `out/forecasts.json`. The Forecasts page, the analysis pages and the Ideas cards render from that dict. The page script only switches between precomputed sets and multiplies by the amount typed.

**Tech Stack:** Python 3.12, pandas, numpy, scipy (already a dependency), pytest; hand-written SVG and vanilla JS; Huurre tokens from `views/core.py`.

**Spec:** `docs/superpowers/specs/2026-11-23-forecast-window-design.md` (binding). Mockup: `.superpowers/brainstorm/20383-1795413179/content/forecast-layouts.html` (A = page, B = inline; the owner chose both).

## Global Constraints

- Privacy: no real holding values or results in tracked files, tests, fixtures, docs or commits. Fixtures use invented prices only.
- No AI and no new data sources. Reads local caches only, with no network calls at `site` time.
- Excess return = stock return − SPY return, both from total-return closes (`data/prices`), both in euros (USD → EUR via `EURUSD=X`, read as of each stock date). Only USD and EUR stocks are included.
- Universe: quote types EQUITY, ETF and MUTUALFUND. INDEX, crypto, unknown currency and other currencies are excluded and listed.
- Samples: the first trading day of each month, on the stock's own calendar. Horizons H ∈ {63, 126, 252} trading days, default 126. h = H/21 months.
- Interval: Newey-West, lag L = h − 1, 95% = mean ± 1.96·se. Effective windows = n_months / h. "too few" when effective windows < 12.
- Group readings: "helps" / "works against" / "no clear edge" / "too few". Good-entry groups help when the interval is entirely > 0; Wait and Stretched groups help when it is entirely < 0.
- Per-stock readings are only "too noisy to trust alone" or "consistent with the pooled reading".
- Target snapshots: the first per ticker per calendar month. Checked after 252 of the ticker's trading days. Met is judged on split-only closes (`ohlc_split`). Own record replaces the study at ≥ 30 checked snapshots.
- Study defaults: overshoot 0.15, met at 12 m 0.38, met at some time 0.64 (Bradshaw, Brown & Huang 2013).
- Lump vs spread: monthly start dates; k ∈ {3, 6, 12}; both strategies valued at s + 252 trading days; idle cash earns 0%.
- Survivorship warning, verbatim: "Stocks are the ones you hold or watch today; past winners are over-represented, so these numbers flatter the signals."
- Vanguard line, verbatim: "Lump sum beat spreading about two-thirds of the time in broad markets (Vanguard, *Dollar-cost averaging just means taking risk later*). Spreading buys a smaller worst case, not a better average. History, not a promise."
- No promise wording ("will", "expect to gain") in page copy.
- Tests: `uv run --no-sync pytest <files> -q`. The full suite takes about 7 min. Never run two pytest processes at once (they share `.pytest_tmp`).

## Review Focus

1. **A month where a stock has no trading day** (holiday spanning a month start, or a gap in the cache): sampling must take the first available day of that month and skip months with none, never crash. Test in Task 2.
2. **The interval when a group has few months, or all months equal** (se = 0): no division by zero; reading "too few" or a zero-width interval, never NaN in the JSON. Test in Task 2.
3. **A EUR stock on a day SPY didn't trade** (a US holiday): as-of lookup uses SPY's previous close; no NaN excess. Test in Task 1.
4. **The amount input left empty, zero, negative or with text**: the page shows the per-€1000 result or "enter an amount", never "NaN €". Test in Task 6 (a JS guard that clamps the amount, checked by a headless DOM smoke).
5. **No snapshots or history file missing** (fresh install): the targets section shows study rates and "no snapshots yet", and the Ideas line still works. Test in Task 4.

---

### Task 1: Euro return series and as-of alignment

**Files:**
- Create: `src/nordic_desk/eur.py`
- Test: `tests/test_eur.py`

**Interfaces:**
- Produces:
  - `currency_of(ticker: str, fund_root: Path, instruments: dict[str, Instrument]) -> str | None`: `fundamentals.load_fundamentals(...)["currency"]`, else the instrument whose `.ticker == ticker`, else None.
  - `asof(s: pd.Series, index: pd.DatetimeIndex) -> pd.Series`: last value on or before each date (NaN before the first).
  - `eur_closes(close: pd.Series, currency: str, eurusd: pd.Series) -> pd.Series | None`: EUR unchanged; USD converted as `close / asof(eurusd, close.index)` (EURUSD=X is USD per EUR); any other currency → None.
  - `quote_ok(f: dict | None) -> bool`: True for EQUITY, ETF and MUTUALFUND.

- [ ] **Step 1: Failing tests:** `test_usd_converted_with_asof_rate` (a USD close of 110 with an EURUSD of 1.1 the day before a missing FX day → 100); `test_eur_unchanged_and_sek_none`; `test_asof_on_us_holiday` (a SPY series missing a date → the previous value); `test_currency_from_fundamentals_then_instruments(tmp_path)`; `test_quote_ok` (INDEX/CRYPTOCURRENCY/None → False).
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_eur.py -q`. Expected: FAIL (import).
- [ ] **Step 3: Implement `eur.py`.** `asof` = `s.reindex(s.index.union(index)).ffill().reindex(index)`.
- [ ] **Step 4: Run.** Expected: PASS. **Step 5: Commit** `feat: euro return series with as-of alignment`.

### Task 2: Scorecard statistics

**Files:**
- Create: `src/nordic_desk/scorecard.py`
- Test: `tests/test_scorecard.py`

**Interfaces:**
- Consumes: `indicators.compute`, `verdict.entry_verdict`, `analysis_config.EntryTh`.
- Produces:
  - `GROUPS = {"Pullback inside an uptrend": "pullback", "Steady uptrend, nothing stretched": "steady", "Far above its recent range; evidence that a dip follows is weak": "stretched", "Trend is down": "wait_down", "No clear trend yet": "wait_mixed"}` (verdict line → group key; "Not enough history yet" is skipped).
  - `GOOD = {"pullback", "steady"}`.
  - `verdict_series(ohlc: pd.DataFrame, th: EntryTh) -> pd.Series`: group key or None per day. It uses `compute()` once, then `entry_verdict` per row.
  - `month_starts(index: pd.DatetimeIndex) -> pd.DatetimeIndex`: the first available date of each month.
  - `samples(groups: pd.Series, stock_eur: pd.Series, spy_eur: pd.Series, H: int) -> pd.DataFrame`. Columns `date, month, group, excess, beat`. H counts the stock's own days; SPY is read with `eur.asof`. Rows whose window runs past the end are dropped.
  - `nw_interval(x: np.ndarray, lag: int) -> tuple[float, float, float]` returning `(mean, lo, hi)`. se² = (γ₀ + 2·Σ_{l=1..L} (1 − l/(L+1))·γ_l)/n, with γ_l the lag-l autocovariance (divide by n). Returns NaN bounds when n < 2.
  - `group_stats(s: pd.DataFrame, H: int, good: bool) -> dict` with keys `n_samples, n_months, eff_windows, beat, mean, lo, hi, reading`. Monthly averages come first; then the NW interval with lag h−1; then the reading rules from Global Constraints.
  - `stock_reading(st: dict, pooled_reading: str, good: bool) -> str`.

- [ ] **Step 1: Failing tests** (known answers, invented data):
  - `test_nw_lag0_equals_plain_se`: x=[1,2,3,4,5] → se = std(ddof=0)/√5 → lo/hi = 3 ± 1.96·√2/√5.
  - `test_nw_wider_with_positive_autocorrelation`: a smooth AR series gives a wider interval at lag 5 than at lag 0.
  - `test_nw_constant_series_zero_width` (no NaN, no ZeroDivision).
  - `test_month_starts_skips_missing_months_and_uses_first_available`.
  - `test_samples_horizon_and_dropped_tail`: a linear stock vs flat SPY gives a known excess; the last H days produce no rows.
  - `test_verdicts_point_in_time`: appending 100 future days does not change any earlier `verdict_series` value.
  - `test_group_stats_too_few_and_helps`: 60 months of +2% excess at H=21 → "helps"; at H=126, 60 months → eff 10 → "too few"; for a Wait group (good=False) with −2% → "helps".
  - `test_stock_reading_never_says_helps`.
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_scorecard.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the functions above in `scorecard.py`.
- [ ] **Step 4: Run.** Expected: PASS. **Step 5: Commit** `feat: scorecard statistics with overlap-corrected intervals`.

### Task 3: Lump vs spread

**Files:**
- Create: `src/nordic_desk/lumpspread.py`
- Test: `tests/test_lumpspread.py`

**Interfaces:**
- Consumes: `scorecard.month_starts`.
- Produces: `lump_vs_spread(close_eur: pd.Series, k: int, horizon: int = 252, bins: int = 20) -> dict | None`. Keys:
  - `starts` (int), `lump_ahead` (share), `median_diff`;
  - `lump_median, spread_median, lump_p5, spread_p5`;
  - `worst_lump_regret` (min L−S), `worst_spread_regret` (min S−L);
  - `hist: {"edges": [...], "counts": [...]}`.
  All values are per €1 invested. Returns None when there are no valid starts. Spread buys 1/k at the month starts s₀…s_{k−1} (those indexed from s's position in `month_starts`), all valued at index(s)+horizon.

- [ ] **Step 1: Failing tests:**
  - `test_rising_line_lump_always_ahead` (a strictly rising series → lump_ahead 1.0, median_diff > 0);
  - `test_flat_series_equal` (L = S = 1, hist all in the zero bin);
  - `test_known_two_step_value` (a hand-built series where the price doubles after month 1, k=3 → S known exactly: (1/3)(2/1)+(1/3)(2/2)+(1/3)(2/2) relative to the end);
  - `test_short_history_none` (200 days → None);
  - `test_k12_values_last_tranche_at_same_end_date`.
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_lumpspread.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. **Step 5: Commit** `feat: lump-sum versus spread simulation over past start dates`.

### Task 4: Realistic analyst targets

**Files:**
- Create: `src/nordic_desk/targets.py`
- Test: `tests/test_targets.py`

**Interfaces:**
- Consumes: `history.PATH`, `history._read`, `ohlc.load_ohlc`.
- Produces:
  - `STUDY = {"overshoot": 0.15, "met_12m": 0.38, "met_any": 0.64, "source": "Bradshaw, Brown & Huang (2013)"}`; `MIN_OWN = 30`.
  - `monthly_snapshots(rows: list[dict]) -> list[dict]`: the first row per (ticker, YYYY-MM), sorted by date.
  - `check(rows: list[dict], load_close: Callable[[str], pd.Series]) -> list[dict]`: adds `met_12m, met_any, implied, actual` for snapshots with 252 later trading days. `implied = target/price − 1`; `actual = close[+252]/close_at_snapshot − 1`, both on split-only closes.
  - `rates(checked: list[dict], first_date: str | None) -> dict` with keys `overshoot, met_12m, met_any, source, n_checked, first_check`. It returns STUDY values while n_checked < MIN_OWN, with `source = "own record (n)"` after that. `first_check` = the oldest snapshot date + 365 days (ISO), or None.
  - `realistic(upside: float | None, overshoot: float) -> float | None`: upside − overshoot.
  - `per_ticker(checked) -> dict[str, int]` (checked count per ticker).

- [ ] **Step 1: Failing tests:** `test_monthly_dedupe`; `test_check_met_flags` (target crossed in month 3 then fell → met_any True, met_12m False); `test_rates_use_study_until_30`; `test_rates_switch_to_own_record`; `test_realistic_subtracts_overshoot` (0.21 → 0.06); `test_missing_history_file(tmp_path)` → rates come from the study, `n_checked` 0, `first_check` None.
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_targets.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. **Step 5: Commit** `feat: analyst targets checked against outcomes, realistic upside`.

### Task 5: Forecasts dict (`out/forecasts.json`)

**Files:**
- Create: `src/nordic_desk/forecasts.py`
- Test: `tests/test_forecasts.py`

**Interfaces:**
- Consumes: Tasks 1–4; `analysis.subjects`, `analysis.slug`, `analysis_config.load`, `prices.load`, `ohlc.load_ohlc`, `fundamentals.load_fundamentals`, `config.load_instruments`.
- Produces: `build_forecasts(subs: list[Subject], desk: dict, cards_doc: dict | None, price_root, ohlc_root, fund_root, hist_path, instruments_path) -> dict`, JSON-safe (non-finite → None). Keys:
  - `built`, `excluded: [{ticker, why}]`, `warning` (survivorship text);
  - `scorecard: {"63"|"126"|"252": {"groups": {key: stats}, "per_stock": {ticker: {key: stats + "reading"}}}}`;
  - `risk: desk["forecast"]["backtest"] or None`;
  - `targets: {"rates": ..., "rows": [{ticker, name, price, target, upside, realistic, record}]}`, with rows taken from the cards that have a mean target;
  - `lump: {ticker: {"3": res, "6": res, "12": res}}` including `"SPY"`;
  - `subjects: [{ticker, name, groups}]`.
- Also `write_forecasts(out_dir, ...) -> dict`, which writes `out/forecasts.json` and returns the dict.

- [ ] **Step 1: Failing tests** on invented prices for 3 tickers (USD stock, EUR stock, SEK stock) plus SPY and EURUSD in tmp roots:
  - `test_excludes_other_currency_and_index`;
  - `test_json_has_no_nan` (`json.dumps(d, allow_nan=False)`);
  - `test_horizons_present_and_per_stock_keys`;
  - `test_lump_for_spy_and_stock`;
  - `test_targets_rows_from_cards_and_study_rates`;
  - `test_warning_text_verbatim`.
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_forecasts.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. **Step 5: Commit** `feat: forecasts data for the site`.

### Task 6: Forecasts page

**Files:**
- Create: `src/nordic_desk/views/forecasts.py`, `src/nordic_desk/views/forecasts.js`
- Modify: `src/nordic_desk/views/core.py` (`nav`: add `("forecasts.html", "Forecasts")` before Aamu), `src/nordic_desk/views/site.py` (index link plus `write_forecasts` + page), `src/nordic_desk/build.py` (`site` help text)
- Test: `tests/test_forecasts_view.py`, `tests/test_views.py` (extend)

**Interfaces:**
- Consumes: the Task 5 dict.
- Produces: `forecasts_page(d: dict, card_default: int) -> str`, using `page(..., "huurre", ...)`. Section ids: `scorecard`, `lump`, `targets`.
- Page content (mockup A, with the spec §4 controls):
  - §1: horizon seg 3/6/12 m (`data-hz`), stock filter `<select id="sc-stock">` ("All stocks" plus per_stock tickers), an SVG **dot-and-interval plot** (one row per group: dot at mean, a line lo→hi, a zero line, a direct text label and a reading tag), and the same numbers in a `<table>` (fallback). Then the risk row, the analyst-target row and the warning paragraph.
  - §2: stock `<select id="ls-stock">` (optgroups from subject groups plus "Market (SPY)"), amount `<input id="ls-amount" type="number" inputmode="numeric" min="1">` with a visible label and € suffix (default `card_default`), and a spread seg 3/6/12 (default 6). Then the headline %, median gain in € and %, the summary table, the histogram SVG with the zero line and median label, and the Vanguard line.
  - §3: the base-rate line (from `rates` + source), then the targets table.
  - Data is embedded as `<script type="application/json" id="fc-data">` with `</` escaped.
  - `forecasts.js` re-renders §1 and §2 from the data on control change. It clamps the amount: an empty or ≤ 0 value shows "Enter an amount" instead of € figures. Hover or focus on a dot or bar shows the table numbers. No statistics are computed in JS.
- [ ] **Step 1: Failing tests:** `test_page_sections_and_nav` (ids present, nav link, "Not investment advice."); `test_no_nan_and_no_promise_words` (`\bwill\b`, "expect to gain" absent from the visible text); `test_warning_and_vanguard_verbatim`; `test_amount_input_labelled` (`<label for="ls-amount"`); `test_site_writes_forecasts(built)` (extend the `site()` helper in `test_views.py`: `out/site/forecasts.html` and `out/forecasts.json` exist).
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_forecasts_view.py tests/test_views.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS.
- [ ] **Step 5: JS smoke.** Write the page from invented data, inject a script that sets the amount to "" and to 3000 and switches the horizon, then `--dump-dom` with headless Chrome. Expected: "Enter an amount" for the empty case, no "NaN" in the DOM, and both SVGs present.
- [ ] **Step 6: Commit** `feat: Forecasts page`.

### Task 7: Inline lines on the Analysis and Ideas pages

**Files:**
- Modify: `src/nordic_desk/analysis.py` (`payload` gains an optional `track: dict | None`; `write_analysis` takes `forecasts: dict | None` and passes `forecasts["scorecard"]["126"]["per_stock"].get(ticker)`), `src/nordic_desk/views/analysis.py` (`_verdict` renders the track block for the entry panel), `src/nordic_desk/views/cards.py` (`analyst_block`: realistic upside; `impact_block`: lump line), `src/nordic_desk/views/site.py` (pass forecasts to cards and analysis)
- Test: `tests/test_analysis.py`, `tests/test_analysis_view.py`, `tests/test_views.py` (extend)

**Interfaces:**
- Consumes: Task 5 dict shapes; `targets.realistic`.
- Produces:
  - `payload(..., track: dict | None = None)` adds `"track": {"group": key, "stats": {...}, "reading": str} | None` for today's group.
  - `cards_page(doc, plan=None, forecasts=None)`, `card_html(c, default_amount, forecasts=None)`.
- Copy:
  - **Analysis:** "Track record for this stock: <group label> in N months since <year>. Beat SPY over the next 6 months X% of those times, average ±." It is hidden when today's line is "Not enough history yet" or there is no per-stock entry. "No past <group label> months for this stock" when the group has no months. It links to `../forecasts.html#scorecard`.
  - **Ideas analysts block:** "Realistic upside <pct>" with "(study)" or "(own record)".
  - **Ideas before/after:** "Lump ended ahead in X% of past start dates; spreading over 6 months cut the bad case from €A to €B." €A and €B are p5 × default amount. It links to `forecasts.html#lump` and is hidden when there is no lump data.
- [ ] **Step 1: Failing tests:** `test_track_block_shown_and_hidden`; `test_track_never_says_helps`; `test_card_realistic_upside_line`; `test_card_lump_line_hidden_without_data`; `test_site_passes_forecasts(built)`.
- [ ] **Step 2: Run** the four test files. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: PASS. Then run the full suite in the background (40-min limit). Expected: all pass.
- [ ] **Step 5: Commit** `feat: track record, realistic upside and lump line inside Analysis and Ideas`.

### Task 8: Real run, design pass, screenshots

- [ ] **Step 1:** Run `uv run --no-sync nordic-desk site` on the real caches. Expected: `out/forecasts.json` and the page are written, and the excluded list is printed with reasons.
- [ ] **Step 2:** Headless Chrome at 1280 and in a 390-px iframe (the headless window's minimum width is 504). Check the forecasts page, one analysis page and the Ideas page. Fix overflow or cramped controls within Huurre tokens. Use ui-ux-pro-max guidance: tables as fallback, labels, no colour-only meaning, 44-px-ish touch targets on the segs.
- [ ] **Step 3:** Screenshots from **invented** data only: `docs/mockups/shots/forecasts-1280.png` and `forecasts-390.png`.
- [ ] **Step 4:** Update README (what the Forecasts page does) and START_HERE (state line). Run the full suite. **Commit** `style: forecasts polish, screenshots and docs`.
