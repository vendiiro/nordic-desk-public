# Single-Stock Analysis Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One analysis page per held, watched or Ideas ticker. It has a horizon switch (6–12 months / Long haul), toggleable indicators, hover explanations, a rules-based verdict and info boxes, in the approved layout A.

**Architecture:** `update` fetches daily OHLC and company fundamentals into git-ignored caches under `data/`. At `site` time, Python computes every indicator, P/E-vs-history series and per-day verdict for each ticker. It embeds them as JSON in a self-contained page under `out/site/analysis/`. A small inline script only draws the SVG chart and shows hover boxes. It formats numbers but never computes an indicator.

**Tech Stack:** Python 3.12, pandas, numpy, yfinance, pytest; hand-written SVG and vanilla JS; Huurre tokens from `views/core.py`.

**Spec:** `docs/superpowers/specs/2026-11-20-stock-analysis-page-design.md` (read it first; the approved mockup is `.superpowers/brainstorm/19019-1795185574/content/chart-layouts.html`, layout "A · Desk", git-ignored, invented data).

## Global Constraints

- Privacy: no real holding values, amounts, results or tickers-with-values in tracked files, tests, fixtures, docs or commit messages. Real data only in `config/*.local.*`, `data/`, `out/`. Fixtures use invented prices.
- Verdict box always ends with: "Fixed rules on the readings above, not AI. A timing aid for a stock you already want, not a prediction."
- Verdict words: 6–12 months `Good entry` / `Wait` / `Stretched`; long haul `Attractive` / `Fair` / `Expensive`. No other wording ("Buy" never appears).
- Every page says where numbers come from and "Not investment advice."
- No new dependency and no chart library. Hand-drawn SVG plus inline vanilla JS.
- JavaScript never computes an indicator, verdict or percentile; it only reads arrays from the embedded JSON and formats them.
- Crypto (`quoteType == "CRYPTOCURRENCY"` or a ticker in `forecast.EXCLUDE`) gets no page and no link.
- Indicator definitions: SMA 50/200; 200-day "rising" means compared with 21 trading days earlier; Bollinger 20 periods, 2 population σ; %B = (price − lower)/(upper − lower); RSI 14 Wilder; MACD 12/26/9; drawdown over the full stored history; 52-week high = rolling max of daily **high** over 252 days; volatility = std of daily log returns over 63 days × √252; 12-1 momentum = close[t−21]/close[t−252] − 1; 3-year return = close/close[t−756] − 1.
- Long-haul P/E is point in time. EPS from a fiscal year becomes usable 90 days after its year-end, with no interpolation. Percentile and median come from the trailing 1260 trading days ending that day. At least 504 days of P/E are needed for a verdict. Negative or missing EPS → P/E null.
- Run tests with `uv run --no-sync pytest <files> -q`; the full suite takes about 10 minutes (background limit 40 min).
- Chart in the instrument's trading currency.

## Review Focus

1. **Short history** (a recent listing, under 252 days): the page must render. The verdict reads `Wait` / "Not enough history yet", and overlays without data are simply not drawn. Test in Task 4 and Task 8.
2. **Earnings in another currency** (`financialCurrency` ≠ `currency`, e.g. an ADR): P/E must be null with the reason "earnings reported in another currency", never a wrong ratio. Test in Task 2.
3. **Tickers with `^`, `=`, `.` or `-`** (`^OMXH25`, `BRK-B`, `NOVO-B.CO`): the file name and every link must use the same `slug()`. Test in Task 7 and Task 9.
4. **NaN/inf reaching the page**: JSON must contain `null`, never `NaN`/`Infinity`, or the whole script dies. Test in Task 7 (payload) and Task 8 (page).
5. **Flat or nearly flat prices** (a suspended stock, a money-market fund): RSI with no moves → null, Bollinger width 0 → %B null, no ZeroDivision. Test in Task 4.

---

### Task 1: OHLC store

**Files:**
- Create: `src/nordic_desk/ohlc.py`
- Modify: `src/nordic_desk/build.py` (the `update` command)
- Test: `tests/test_ohlc.py`

**Interfaces:**
- Produces: `ROOT = Path("data/ohlc")`; `load_ohlc(ticker: str, root: Path = ROOT) -> pd.DataFrame` (DatetimeIndex, float columns `open, high, low, close`, empty frame with those columns when missing); `update_ohlc(tickers: list[str], start: str = prices.DEFAULT_START, root: Path = ROOT, fetch: Callable[[str, str], pd.DataFrame] = yf_fetch_ohlc) -> dict[str, str]` (same status strings as `prices.update`); `yf_fetch_ohlc(ticker, start) -> pd.DataFrame` using `yf.download(..., auto_adjust=True)` so it matches the close store.
- File naming: reuse `prices._file(ticker, root)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_update_then_load_roundtrip(tmp_path):
    idx = pd.bdate_range("2026-01-05", periods=5)
    df = pd.DataFrame({"open": [1,2,3,4,5.], "high": [2,3,4,5,6.], "low": [0.5,1,2,3,4], "close": [1.5,2.5,3.5,4.5,5.5]}, index=idx)
    st = update_ohlc(["^OMXH25"], root=tmp_path, fetch=lambda t, s: df)
    assert st["^OMXH25"] == "ok"
    out = load_ohlc("^OMXH25", tmp_path)
    assert list(out.columns) == ["open", "high", "low", "close"] and out["close"].iloc[-1] == 5.5

def test_incremental_overlap_overwrites_last_week(tmp_path): ...  # second fetch with a revised last close replaces it, keeps earlier rows
def test_missing_file_gives_empty_frame(tmp_path):
    assert load_ohlc("NOPE", tmp_path).empty
def test_fetch_error_keeps_old_and_reports(tmp_path): ...  # status starts with "error:"
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_ohlc.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement `ohlc.py`.** Mirror `prices.update` (OVERLAP_DAYS re-fetch, merge keep-last). Flatten yfinance MultiIndex columns and lower-case them.
- [ ] **Step 4: Hook into `update`.** After `prices.update(...)`, call `update_ohlc` on the same ticker list plus the Ideas tickers from `config/ideas.toml`. Leave out `forecast.EXCLUDE`, `MARKET` and `FX`. Print a one-line summary like the facts line.
- [ ] **Step 5: Run** the tests. Expected: PASS.
- [ ] **Step 6: Commit** `feat: daily OHLC store for candle charts`

---

### Task 2: Fundamentals cache (quote type, quality fields, EPS history)

**Files:**
- Create: `src/nordic_desk/fundamentals.py`
- Modify: `src/nordic_desk/build.py` (`update`)
- Test: `tests/test_fundamentals.py`

**Interfaces:**
- Produces: `ROOT = Path("data/fundamentals")`; `fetch_fundamentals(ticker: str, fetch_info=yf_info, fetch_eps=yf_eps) -> dict` with keys `ticker, name, quote_type, currency, financial_currency, sector, returnOnEquity, profitMargins, debtToEquity, freeCashflow, revenueGrowth, marketCap, eps: list[{"year_end": "YYYY-MM-DD", "eps": float}], fetched`. Also `update_fundamentals(tickers, root=ROOT, fetch=fetch_fundamentals) -> dict[str, str]` (writes `<slug>.json` via `prices._file` naming but `.json`; on error keep the old file) and `load_fundamentals(ticker, root=ROOT) -> dict | None`.
- `eps_available(eps: list[dict], lag_days: int) -> list[tuple[pd.Timestamp, float]]`: sorted by available date = year_end + lag_days.
- `pe_reason(f: dict | None) -> str | None`: `None` when P/E can be computed. Otherwise one of `"not a company (fund or index)"`, `"no earnings history"`, `"earnings reported in another currency"`.
- `yf_eps(t)` reads `yf.Ticker(t).income_stmt` row `"Diluted EPS"`, falling back to `"Basic EPS"`. Columns are fiscal year-ends. NaN is skipped.

- [ ] **Step 1: Write the failing tests**

```python
def test_eps_available_lags_90_days():
    rows = [{"year_end": "2024-12-31", "eps": 2.0}, {"year_end": "2023-12-31", "eps": 1.5}]
    out = eps_available(rows, 90)
    assert out == [(pd.Timestamp("2024-03-30"), 1.5), (pd.Timestamp("2025-03-31"), 2.0)]

def test_pe_reason_other_currency():
    f = {"quote_type": "EQUITY", "currency": "USD", "financial_currency": "DKK", "eps": [{"year_end": "2024-12-31", "eps": 3.0}]}
    assert pe_reason(f) == "earnings reported in another currency"

def test_pe_reason_fund_and_empty():
    assert pe_reason({"quote_type": "ETF", "eps": []}) == "not a company (fund or index)"
    assert pe_reason({"quote_type": "EQUITY", "currency": "USD", "financial_currency": "USD", "eps": []}) == "no earnings history"
    assert pe_reason(None) == "no earnings history"

def test_update_writes_and_keeps_old_on_error(tmp_path): ...  # fake fetch ok then raising; file content unchanged after error
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_fundamentals.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement `fundamentals.py`.** `financial_currency` comes from info `financialCurrency`, falling back to `currency`. Store numbers through a finite-or-None helper.
- [ ] **Step 4: Hook into `update`** for the same ticker list as Task 1. Print a one-line summary.
- [ ] **Step 5: Run** the tests. Expected: PASS.
- [ ] **Step 6: Commit** `feat: cache fundamentals and EPS history for analysis pages`

---

### Task 3: Quality checks (port) and `config/analysis.toml`

**Files:**
- Create: `src/nordic_desk/quality.py` (port of `market-leaderboard/engine/quality.py`), `config/analysis.toml`, `src/nordic_desk/analysis_config.py`
- Test: `tests/test_quality.py` (port of `market-leaderboard/tests/test_quality.py`)

**Interfaces:**
- Produces: `QualitySettings(min_score: int, roe_min: float, margin_min: float, debt_to_equity_max: float, market_cap_min: float, must_pass: tuple[str, ...], distorted_roe_above: float)` defined in `quality.py`. Also `quality_detail(fund, q, fx_to_usd=None, sector=None, must_pass=..., distorted_roe_above=...) -> QualityResult`, unchanged from the source. Add `fails(r: QualityResult, q: QualitySettings) -> bool | None`: `None` when `r.status in ("thin", "distorted", "no_data")`; otherwise `True` iff `r.score < q.min_score or r.must_failed`.
- `analysis_config.load(path="config/analysis.toml") -> AnalysisConfig`, a frozen dataclass with `entry: EntryTh`, `long: LongTh`, `quality: QualitySettings`.
- `EntryTh(pullback_pct_b=0.2, pullback_rsi=40, stretched_rsi=70, stretched_pct_b=0.95, trend_lookback=21)`; `LongTh(attractive_below=0.30, expensive_above=0.70, window_days=1260, min_days=504, eps_lag_days=90, big_3y=1.0)`.
- `config/analysis.toml` holds exactly those values plus `[quality]` copied from market-leaderboard `settings.toml`: `min_score = 60, roe_min = 0.12, margin_min = 0.08, debt_to_equity_max = 150, market_cap_min = 1_000_000_000, must_pass = ["net_margin_positive"], distorted_roe_above = 1.0`.

- [ ] **Step 1: Port the tests.** Copy `market-leaderboard/tests/test_quality.py`, change imports to `nordic_desk.quality`, and build `QualitySettings` directly. Add:

```python
def test_fails_none_when_thin_or_distorted(): ...   # status thin -> fails() is None
def test_fails_true_on_low_score_or_must_pass(): ... # score 50 -> True; margin -0.01 with score 67 -> True
def test_config_loads_defaults(): assert load().long.min_days == 504 and load().quality.min_score == 60
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_quality.py -q`. Expected: FAIL.
- [ ] **Step 3: Port `quality.py`.** Put a provenance comment on line 1: "Ported from market-leaderboard engine/quality.py". Replace `usd_value` with a local helper: `value * fx_to_usd[currency]`, or None when the currency is unknown. Add `fails()`. Write `analysis_config.py` and the TOML.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: quality checks and analysis thresholds`

---

### Task 4: Indicators

**Files:**
- Create: `src/nordic_desk/indicators.py`
- Test: `tests/test_indicators.py`

**Interfaces:**
- Consumes: `eps_available` (Task 2), `LongTh` (Task 3).
- Produces: `compute(ohlc: pd.DataFrame, trend_lookback: int = 21) -> pd.DataFrame` (input columns `open, high, low, close`, where open/high/low may be all-NaN when only closes exist). It returns the same index with columns `close, open, high, low, sma50, sma200, trend, bb_up, bb_mid, bb_lo, pct_b, rsi, macd, macd_signal, macd_hist, drawdown, high52, dist52, vol, mom, ret3y, chg_1w, chg_1m, chg_1y`. `trend` holds `"up" | "down" | "mixed"`, or None while sma200 or its lagged value is missing. When `high` is all-NaN, `high52` uses close.
- `pe_frame(close: pd.Series, eps_avail: list[tuple[pd.Timestamp, float]], th: LongTh) -> pd.DataFrame` with columns `pe, pe_pct, pe_median, pe_n`. `pe` = close / latest available EPS (as-of join), null when EPS ≤ 0 or none available. `pe_pct` = share of the trailing-window non-null P/E values ≤ today's value. `pe_median` = trailing-window median. `pe_n` = count of non-null P/E in the window. All are point in time.

- [ ] **Step 1: Write the failing tests** (known answers):

```python
def test_sma_on_linear_series():
    s = _frame(np.arange(1, 301, dtype=float)); out = compute(s)
    assert out["sma50"].iloc[-1] == pytest.approx(275.5) and out["sma200"].iloc[-1] == pytest.approx(200.5)
    assert out["trend"].iloc[-1] == "up"

def test_flat_series_no_crash():
    out = compute(_frame(np.full(300, 10.0)))
    assert np.isnan(out["rsi"].iloc[-1]) and np.isnan(out["pct_b"].iloc[-1]) and out["drawdown"].iloc[-1] == 0

def test_rsi_all_gains_is_100(): ...
def test_bollinger_matches_population_std(): ...  # compare to manual np.std(ddof=0) on last 20
def test_high52_uses_daily_high_not_close(): ...
def test_mom_skips_last_month(): ...             # close[t-21]/close[t-252]-1 on a constructed series
def test_short_history_trend_none():
    out = compute(_frame(np.linspace(10, 20, 150)))
    assert out["trend"].iloc[-1] is None and np.isnan(out["sma200"].iloc[-1])

def test_pe_point_in_time_no_lookahead():
    # EPS year_end 2024-12-31 available 2025-03-31: a day before that must use the previous EPS
def test_pe_null_for_negative_eps(): ...
def test_pe_pct_uses_trailing_window_only(): ...  # appending a later huge P/E does not change an earlier day's pe_pct
```

`_frame(close)` builds a bdate-indexed frame with open=high=low=close.

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_indicators.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement `indicators.py`.** Use pandas rolling and ewm (Wilder RSI: `ewm(alpha=1/14, adjust=False)` on gains and losses; when both are 0 → NaN, when only losses are 0 → 100). For `pe_pct` use rolling apply over `window_days` with `min_periods=1`; returning NaN when the day's P/E is NaN is fine.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: indicator and point-in-time P/E series`

---

### Task 5: Verdict rules

**Files:**
- Create: `src/nordic_desk/verdict.py`
- Test: `tests/test_verdict.py`

**Interfaces:**
- Consumes: `EntryTh`, `LongTh`, `QualityResult`, `fails` (Task 3).
- Produces: `@dataclass(frozen=True) Verdict(v: str, cls: str, line: str, why: tuple[tuple[str, str], ...])`. `cls` is one of `good, wait, str, neu`; each `why` item is `(sign, text)` with sign in `"+", "–", "·"`.
- `entry_verdict(r: Mapping, th: EntryTh) -> Verdict`, where `r` has `trend, pct_b, rsi, mom, dist52`. Rules in this order:
  1. any of trend/pct_b/rsi missing → `Wait`, "Not enough history yet"
  2. `rsi > stretched_rsi or pct_b > stretched_pct_b` → `Stretched` (cls `str`), "Price ran ahead of its trend; a dip is common next"
  3. trend up and (`pct_b < pullback_pct_b or rsi < pullback_rsi`) → `Good entry`, "Pullback inside an uptrend"
  4. trend up and mom not None and mom > 0 → `Good entry`, "Steady uptrend, nothing stretched"
  5. otherwise `Wait`: "Trend is down" if trend down, else "No clear trend yet".
  `why` = trend, Bollinger position, RSI, momentum (when present), 52-week distance, with the texts as in the mockup.
- `long_verdict(r: Mapping, kind: str, q: QualityResult | None, qs: QualitySettings, th: LongTh, today: bool) -> Verdict | None`. `r` has `pe, pe_pct, pe_median, pe_n, ret3y, vol, worst_dd`. It returns `None` when `kind != "stock"`.
  - `pe_n < min_days` or pe null → `Fair` (cls `neu`), "Not enough P/E history".
  - Otherwise pe_pct < attractive_below → `Attractive`; > expensive_above → `Expensive` (cls `str`); else `Fair` (cls `neu`).
  - Lines when `today`: "Quality business at a below-normal price" / "…at a normal price" / "Good business, but priced above its own history". When not today: "Below its normal price" / "Normal price" / "Above its normal price".
  - When `today` and `fails(q, qs) is True`: cap Attractive at Fair, and add the why item `("–", "Quality checks fail: …")`. When `fails(...) is None`: why `("·", "Quality could not be judged (…status…)")`. When not today: why `("·", "quality: today's snapshot, not used for past days")`.
  - `ret3y > big_3y` adds `("–", "3-year return …: big long-run winners tend to cool")`.
- `VERDICT_TABLE: list[tuple[str, str, str]]` holds every `(v, cls, line)` the two functions can return. Order is fixed; it is used to index per-day verdicts.

- [ ] **Step 1: Write the failing tests.** One per rule above. They should cover: Stretched beats a pullback when RSI is 75 and %B 0.1 in an uptrend; quality failure caps Attractive at Fair; past-day verdicts leave quality out; a fund gives None; `pe_n` of 503 gives "Not enough P/E history"; every returned `(v, cls, line)` is in `VERDICT_TABLE`, checked over a parameter grid; no line matches `\bBuy\b`.
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_verdict.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement `verdict.py`.**
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: rules-based entry and long-haul verdicts`

---

### Task 6: Explanation texts

**Files:**
- Create: `src/nordic_desk/explain.py`
- Test: `tests/test_explain.py`

**Interfaces:**
- Produces: `EXPLAIN: dict[str, dict]`. Keys are `sma50, sma200, bb, h52, rsi, macd, dd, pe, mom, vol, quality, ltrev, price`. Each value has `title, what, formula, use, now` (all `str`). `now` is a template with placeholders `{field|fmt}`, where `field` is a payload array name from Task 7 and `fmt` is one of `price, pct, pct0, num1, num2, date`. Example for sma200: `"Today {sma200|price}; price is {dist200|pct} from it."`
- `FIELDS_USED: set[str]` collects every field named in any `now` template.
- Texts: take them from the mockup's `EX` object. Evidence statements must match the spec's "Research summary" exactly in strength (strong / moderate / weak or mixed) and citation.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_indicator_has_full_entry():
    for k in ["sma50","sma200","bb","h52","rsi","macd","dd","pe","mom","vol","quality","ltrev","price"]:
        e = EXPLAIN[k]; assert all(e[f] for f in ("title","what","use")) and "now" in e
def test_templates_parse():  # every {x|y} has y in the allowed fmt set
def test_no_strong_claim_for_timing_indicators():
    for k in ("rsi", "bb", "macd"): assert "weak" in EXPLAIN[k]["use"].lower()
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_explain.py -q`. Expected: FAIL.
- [ ] **Step 3: Write `explain.py`.**
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: plain-language indicator explanations`

---

### Task 7: Subjects and page payload

**Files:**
- Create: `src/nordic_desk/analysis.py`
- Test: `tests/test_analysis.py`

**Interfaces:**
- Consumes: `load_ohlc` (T1); `load_fundamentals, eps_available, pe_reason` (T2); `quality_detail, fails`, `analysis_config.load` (T3); `compute, pe_frame` (T4); `entry_verdict, long_verdict, VERDICT_TABLE` (T5); `EXPLAIN, FIELDS_USED` (T6); `prices.load`, `config.load_instruments`, `config.load_holdings`, `config.load_watchlist`, `forecast.EXCLUDE`.
- Produces:
  - `slug(ticker: str) -> str`, the same transform as `prices._file` without the extension (`^`→`_`, `=`→`_`), used for every file name and link.
  - `analysis_href(ticker: str) -> str | None`: `f"analysis/{slug(t)}.html"`, or None for crypto. Links from site-root pages use it.
  - `@dataclass(frozen=True) Subject(ticker: str, name: str, groups: tuple[str, ...], note: str)`. Groups come from `"held", "watch", "idea"`. `note` is the instrument note for stand-ins, else "".
  - `subjects(holdings_path, instruments_path, watchlist: list[str], cards_doc: dict | None) -> list[Subject]`. It de-duplicates by ticker and merges groups. Holdings take their name from the instrument name, cards from the card name, the watchlist from fundamentals or the ticker. Crypto is left out.
  - `kind_of(f: dict | None) -> str`: `"stock"` for EQUITY, `"fund"` for ETF/MUTUALFUND/INDEX/unknown, `"crypto"` for CRYPTOCURRENCY.
  - `payload(s: Subject, ohlc: pd.DataFrame, close_fallback: pd.Series, f: dict | None, cfg: AnalysisConfig, fx_to_usd: dict[str, float], built: str) -> dict`.
- Payload schema (JSON-safe: every non-finite value → `None`; floats rounded to 4 decimals; arrays cover the last 1260 rows, but indicators are computed on the full history before slicing):
  - `ticker, name, note, kind, currency, built, has_ohlc` (False when OHLC is missing and `close_fallback` is used)
  - `dates` (ISO strings); arrays `o, h, l, c, sma50, sma200, bb_up, bb_mid, bb_lo, pct_b, rsi, macd, macd_signal, macd_hist, drawdown, high52, dist52, dist200, vol, mom, ret3y, chg_1w, chg_1m, chg_1y, trend`
  - `pe, pe_pct, pe_median` (all-null arrays when `pe_reason` is set), `pe_reason`
  - `entry_day: list[int | None]` and `long_day: list[int | None]`: indexes into `verdicts`, the `VERDICT_TABLE` rows as `{v, cls, line}` (`long_day` uses `today=False`)
  - `today: {"entry": Verdict-as-dict, "long": Verdict-as-dict | None}`, where long uses `today=True` with quality
  - `quality: {score, status, checks, fcf_yield} | None` (`fcf_yield = freeCashflow / marketCap`, shown only)
  - `boxes: {"entry": [...4], "long": [...4]}`, each `{key, label, value, text}`. Entry boxes are Trend/sma200, Stretch/bb, Momentum/mom, Risk/dd. Long boxes are Valuation/pe, Quality/quality, Long-term/ltrev, Risk/dd. A fund's long boxes Valuation and Quality read "not available for funds" and point to the look-through.
  - `explain`: `EXPLAIN` as is
  - `defaults`: `{"entry": {"range": 252, "style": "candle", "on": ["sma200", "bb", "h52", "rsi"]}, "long": {"range": 1260, "style": "line", "on": ["sma200", "dd", "pe"]}}`. A fund's long `on` leaves out `pe`, and `style` is `"line"` when `has_ohlc` is False.

- [ ] **Step 1: Write the failing tests.** Use invented data only; build fundamentals dicts inline.

```python
def test_slug_and_href(): assert slug("^OMXH25") == "_OMXH25" and analysis_href("ETH-EUR") is None and analysis_href("BRK-B") == "analysis/BRK-B.html"
def test_subjects_merge_groups_and_drop_crypto(tmp_path): ...  # example holdings toml with a stock that is also on the watchlist -> groups ("held","watch")
def test_standin_note_and_name(tmp_path): ...  # instrument with note -> Subject.note non-empty, name = instrument name
def test_payload_json_has_no_nan(): s = json.dumps(payload(...), allow_nan=False)  # must not raise
def test_payload_fields_cover_explain_templates(): assert FIELDS_USED <= set(payload(...).keys())
def test_payload_without_ohlc_falls_back_to_line(): p = payload(..., ohlc=empty, close_fallback=series); assert not p["has_ohlc"] and p["defaults"]["entry"]["style"] == "line" and all(v is None for v in p["o"])
def test_fund_has_no_long_verdict(): assert payload(... f={"quote_type": "ETF"} ...)["today"]["long"] is None
def test_today_verdict_matches_last_entry_day(): p = payload(...); assert p["verdicts"][p["entry_day"][-1]]["v"] == p["today"]["entry"]["v"]
def test_short_history_payload(): ...  # 150 rows -> renders, today entry verdict line "Not enough history yet"
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_analysis.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement `analysis.py`.** `dist200 = close / sma200 − 1` is added here. `worst_dd` for the long why = min drawdown over the payload window. Box texts follow the mockup's `cards()`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat: analysis subjects and page payload`

---

### Task 8: The page (layout A)

**Files:**
- Create: `src/nordic_desk/views/analysis.py`, `src/nordic_desk/views/analysis.js`
- Test: `tests/test_analysis_view.py`

**Interfaces:**
- Consumes: payload (T7), `views.core.page, esc, nav`.
- Produces: `analysis_page(p: dict, picker: list[Subject]) -> str` and `analysis_index(picker: list[Subject]) -> str` (a list grouped as Holdings / Watchlist / Ideas, linking `<slug>.html`).
- Page structure (from mockup A):
  - Header: name, ticker, last price and day change, the stand-in note when non-empty, a `<select>` picker with `<optgroup>`s Holdings/Watchlist/Ideas, and the horizon segmented control.
  - Main: chips (real `<button aria-pressed>`), range seg 1M/6M/1Y/5Y, line/candle seg (candle button hidden when `has_ohlc` is false), chart container `tabindex="0"`.
  - Right column: the verdict card and the info boxes. These are server-rendered for **both** horizons, and the hidden one gets `hidden`, so the page reads correctly without JS.
  - Footer: data source (Yahoo prices and company data), "built <date>", "Not investment advice."
  - Payload in `<script type="application/json" id="analysis-data">`, with `</` escaped as `<\/`.
  - The page uses Huurre tokens through `page(..., look="huurre")`, with the mockup's CSS adapted to the token names (`--color-*`, `--space-*`).
- `analysis.js` (inlined by `analysis_page` with `Path(__file__).with_name("analysis.js").read_text()`) ports the mockup's `desk()`: `draw`, `hover`, bar grouping (`step = ceil(n/150)` for candles), line-hover hit test (8 px), panel hit test, arrow keys, pointerdown = hover for touch. The differences: all values come from the payload; `now` templates are filled by `fill(template, i)` using the formats `price, pct, pct0, num1, num2, date`; the day verdict comes from `verdicts[entry_day[i]]` / `verdicts[long_day[i]]`. No indicator math.
- Responsive: under 1100 px the right column moves below the chart. Respect `prefers-reduced-motion`.

- [ ] **Step 1: Write the failing tests**

```python
def test_page_basics(sample_payload):
    html = analysis_page(sample_payload, picker)
    assert html.lstrip().startswith("<!doctype html>") and "NaN" not in html and "Infinity" not in html
    assert "Not investment advice." in html and "Fixed rules on the readings above, not AI." in html
    assert 'id="analysis-data"' in html and not re.search(r"\bBuy\b", html)
def test_both_horizons_server_rendered(sample_payload): ...  # both verdict cards present, long one hidden
def test_no_candle_toggle_without_ohlc(payload_no_ohlc): assert 'data-s="candle"' not in analysis_page(payload_no_ohlc, picker)
def test_script_close_tag_escaped(): ...  # a name containing "</script>" does not break out
def test_fund_long_boxes_say_not_available(fund_payload): ...
def test_picker_groups_and_slug_links(): ...  # "^OMXH25" -> value "_OMXH25.html"
```

- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_analysis_view.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `views/analysis.py` and `views/analysis.js`.
- [ ] **Step 4: Run** the tests. Expected: PASS.
- [ ] **Step 5: Smoke-check the JS in headless Chrome.** Write the page from an invented payload into `out/site/analysis/_smoke.html`. Then run `"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --virtual-time-budget=4000 --dump-dom <file-url-or-served-url>`. Expected: the DOM contains `<svg viewBox=` inside the chart container (the script ran). Delete the smoke file afterwards.
- [ ] **Step 6: Commit** `feat: single-stock analysis page`

---

### Task 9: Wire into the site, links and CLI

**Files:**
- Modify: `src/nordic_desk/views/site.py`, `src/nordic_desk/views/huurre.py` (`dive`), `src/nordic_desk/views/impact.py` (holdings table name cell), `src/nordic_desk/views/cards.py` (`card_html` header), `src/nordic_desk/views/core.py` (`nav`: add `("analysis/index.html", "Analysis")`), `src/nordic_desk/build.py` (help text for `site`), `README.md`, `START_HERE.md`
- Test: `tests/test_views.py`, `tests/test_cards.py` (extend)

**Interfaces:**
- Consumes: `subjects, payload, analysis_href, slug` (T7); `analysis_page, analysis_index` (T8).
- Produces: `write_analysis(out_dir: Path, holdings_path: str = HOLDINGS, ohlc_root=ohlc.ROOT, price_root=prices.ROOT, fund_root=fundamentals.ROOT) -> list[Path]`, called from `write_site`. It reads caches only (no network), writes `out/site/analysis/<slug>.html` plus `index.html`, and skips a subject that has neither OHLC nor closes. It uses `fx_to_usd = {"USD": 1.0, "EUR": last EURUSD=X close}`.
- Links: Desk `dive` panel gets "Analyse chart →" to `analysis_href(t)`. Impact holdings rows link the name when `analysis_href` is not None. Each Ideas card header gets "Analyse". Pages inside `analysis/` link back with `../`.

- [ ] **Step 1: Write the failing tests.** `write_site` on the `built` fixture (extend it with an OHLC root of invented data) writes `site/analysis/index.html` and one page per watchlist ticker. The Desk page contains `href="analysis/AAPL.html"`. A card for `^OMXH25` links `analysis/_OMXH25.html`. No `analysis/CBUT.DE.html` is written even when it is held (example holdings).
- [ ] **Step 2: Run** `uv run --no-sync pytest tests/test_views.py tests/test_cards.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement the wiring.** Update README (run order unchanged: `update` now also fetches OHLC and fundamentals; `site` writes the analysis pages) and START_HERE (state line).
- [ ] **Step 4: Run** the tests. Expected: PASS. Then run the full suite in the background (40-minute limit): `uv run --no-sync pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: analysis pages in the site with links from Desk, Impact and Ideas`

---

### Task 10: Real-data run, design pass and screenshots

**Files:**
- Modify: `src/nordic_desk/views/analysis.py` / `analysis.js` only for fixes found here
- Screenshots: `docs/mockups/shots/` (**only** from an invented-data page; real-data screenshots stay in `out/`)

- [ ] **Step 1: Real run.** Run `uv run --no-sync nordic-desk update`, then `uv run --no-sync nordic-desk site`. Expected: one page per non-crypto subject and an index; the summary lines show no unexpected errors.
- [ ] **Step 2: Serve and check in the browser.** Serve on `127.0.0.1` with the owner's server or `nordic-desk serve`. Open three pages: a stock, a fund and a stand-in. Check the hover, chips, horizon switch and that the numbers match the boxes.
- [ ] **Step 3: Run the `impeccable` skill** on the analysis page (polish pass) and fix what it finds.
- [ ] **Step 4: Screenshots** at 1280 and 390 px width with headless Chrome (`--window-size=1280,1000` / `390,900 --screenshot`). Save the invented-data versions to `docs/mockups/shots/analysis-1280.png` and `analysis-390.png`.
- [ ] **Step 5: Run** the full test suite again. Expected: PASS.
- [ ] **Step 6: Commit** `style: analysis page polish and screenshots`. Before any push, run `git log -S` for a few real holding names and values (START_HERE rule).
