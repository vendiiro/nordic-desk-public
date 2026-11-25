# Combined Expected Return and Vol-Sized Purchases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (owner chose native execution). Steps use checkbox (`- [ ]`) syntax.

**Goal:** A 12-month combined expected return per stock, and a volatility-sized purchase suggestion with a historical test, both shown on the Forecasts page and in its summary.

**Architecture:** Two small modules (`expected.py`, `volsize.py`) feed `forecasts.build_forecasts`. `lumpspread` gains a vol-sized strategy. The page and its script render new keys from `forecasts.json`; the browser computes nothing.

**Tech Stack:** Python 3.12, pandas, numpy, pytest; vanilla JS/SVG; Huurre tokens.

**Spec:** `docs/superpowers/specs/2026-11-24-expected-return-and-vol-sizing-design.md`. Branch `forecast-page-redesign`.

## Global Constraints

- Anchor = (SPY_EUR last / first)^(252/(n−1)) − 1 over full stored history; label with first and last year.
- Combined = 0.5·anchor + 0.5·mean(pieces); no pieces → anchor ("anchor only").
- Analyst piece = `targets.realistic(upside, overshoot)`, only for used subjects with a card target.
- Signal piece = anchor + pooled 252-day group mean, only when that group's reading ∈ {"helps", "works against"}.
- First part f = clamp((usual/current)², 0.25, 1.0); usual = median of 63-day vol over days ≤ s; needs ≥ 252 vol observations.
- Vol-sized buys f at s and (1−f)/k at each of the next k month starts; valued at s+252; idle cash 0%.
- No promise wording; privacy as before; invented data in screenshots.
- Tests: `uv run --no-sync pytest <files> -q`; never two pytest runs at once.

## Review Focus

1. A stock whose volatility series is all NaN or zero (a flat fund): f must not divide by zero; suggestion "not enough history" or f = 1. Test in Task 2.
2. SPY history shorter than 1 year: the anchor is None and combined falls back cleanly with no NaN. Test in Task 1.
3. Vol-sized never triggered (all f = 1): the page says "never triggered", with no 0% "beat" claims. Test in Task 3.
4. An amount empty while the suggestion shows euros: the euro part is hidden, not NaN. JS smoke in Task 4.
5. A pooled 252-day group missing for today's group: the signal piece is omitted. Test in Task 1.

---

### Task 1: `expected.py`
**Files:** create `src/nordic_desk/expected.py`, `tests/test_expected.py`.
**Produces:** `anchor(spy_eur: pd.Series) -> dict | None` (`{"rate", "from", "to"}`, None if < 253 rows); `combine(anchor_rate: float, analyst: float | None, signal: float | None) -> dict` (`{"anchor", "analyst", "signal", "combined", "pieces"}`); `signal_piece(anchor_rate, group: str | None, pooled252: dict) -> float | None`.
- [ ] Tests: `test_anchor_known_rate` (a series doubling over 252·2 days gives √2 − 1); `test_anchor_short_none`; `test_combine_zero_one_two_pieces` (0 → anchor, pieces 0; analyst 0.20 with anchor 0.10 → 0.15; both 0.20 and 0.00 → 0.5·0.1 + 0.5·0.1 = 0.10); `test_signal_piece_only_with_evidence` ("no clear edge"/"too few"/missing → None; "helps" with mean −0.03 → anchor − 0.03).
- [ ] RED, then implement, then GREEN, then commit `feat: combined expected return`.

### Task 2: `volsize.py`
**Files:** create `src/nordic_desk/volsize.py`, `tests/test_volsize.py`.
**Produces:** `MIN_OBS = 252`; `first_part(current: float, usual: float) -> float`; `usual_series(vol: pd.Series) -> pd.Series` (expanding median, NaN until MIN_OBS non-NaN observations); `suggestion(close_eur: pd.Series) -> dict | None` (`{"current", "usual", "first"}` from `indicators.compute` vol on a close-only frame; None without enough history).
- [ ] Tests: `test_first_part_clamps` (current = usual → 1; current = 2·usual → 0.25; current < usual → 1; current 0 or NaN → 1); `test_usual_point_in_time` (appending a volatile tail doesn't change earlier values); `test_suggestion_short_history_none`; `test_flat_series_no_crash`.
- [ ] RED, implement, GREEN, commit `feat: volatility-sized first part`.

### Task 3: Vol-sized strategy in `lumpspread`
**Files:** modify `src/nordic_desk/lumpspread.py`, `tests/test_lumpspread.py`.
**Produces:** `volsized(close_eur: pd.Series, k: int, horizon: int = 252) -> dict | None` with `{"starts", "held_back", "beat_lump", "beat_spread", "median", "p5", "lump_median", "spread_median"}` (per €1). It covers only the starts with usual volatility (MIN_OBS). Beat shares and the three medians are taken over the starts where f < 1. `held_back` = the count of those starts. None when there are no eligible starts.
- [ ] Tests: `test_volsized_equals_lump_when_calm` (constant-vol series: held_back 0 and the beat fields None); `test_volsized_two_step_arithmetic` (a hand-built case with f = 0.25 known: V = 0.25·p_end/p_s + Σ 0.75/k·p_end/p_{s_i}); `test_volsized_point_in_time`.
- [ ] RED, implement, GREEN, commit `feat: vol-sized purchases tested against lump and spread`.

### Task 4: Wire into forecasts and the page
**Files:** modify `src/nordic_desk/forecasts.py` (keys `expected: {ticker: combine(...)}` plus `anchor`, `volsize: {ticker: {"now": suggestion, "3"|"6"|"12": volsized}}`), `src/nordic_desk/views/forecasts.py` (new section `#expected` with a table; a third column and sentence in the lump section; method notes with references), `src/nordic_desk/views/forecasts.js` (summary fourth fact "Expected return, 12 m"; the suggestion line in the lump fact and section; the vol-sized column). Tests: `tests/test_forecasts.py`, `tests/test_forecasts_view.py`.
- [ ] Tests: `test_expected_keys_and_no_nan`; `test_volsize_keys`; `test_page_has_expected_section_and_vol_column` (`id="expected"`, "Rapach", "Moreira"); `test_no_promise_words` (still passes).
- [ ] RED, implement, GREEN, then a JS smoke (the empty amount hides euros, no NaN, SPY selected), a full suite run, and a commit `feat: expected return and vol sizing on the Forecasts page`.

### Task 5: Real run, look, screenshots, review
- [ ] `nordic-desk site` on real caches. Screenshots at 1280/390 from the invented demo (`demo.py`), checked visually and fixed; save them to `docs/mockups/shots/forecasts-*.png`. README note. Full suite. Commit.
- [ ] A fresh whole-branch review on Opus, then a fix pass, then push and a PR into `forecast-window`.
