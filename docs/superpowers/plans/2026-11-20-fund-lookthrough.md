# Fund look-through implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show how much of the portfolio sits in each company once funds are looked through, on every candidate card (before and after a purchase) and on the Desk view.

**Architecture:** A new pure module `lookthrough.py` turns position values plus each fund's published top holdings into euros and shares per company. Fund holdings come from Yahoo (`Ticker.funds_data.top_holdings`), cached daily under `data/funds/`. `cards.py` and `build.py` call it with an injectable fetcher; the views render the results.

**Tech Stack:** Python 3.12, yfinance 1.8, pytest; static HTML views in `src/nordic_desk/views/`.

**Spec:** `docs/superpowers/specs/2026-11-20-idea-discovery-design.md`, goal 1 only.

## Global Constraints

- Repository is shown to other people: tests and fixtures use invented holdings and invented fund weights only; real output only under `data/` and `out/` (git-ignored). Check `git log -S` before any push.
- Holdings outside a fund's published top list count as "rest of fund", never guessed.
- No network in tests: every Yahoo call sits behind an injectable fetcher, and `tests/conftest.py` stubs the default one.
- Fractions are plain numbers (0.123 = 12.3%); money in euros. Update `docs/data-contract.md` for every new key.
- Pages say where numbers come from ("fund top holdings from Yahoo Finance") and keep the Huurre style and sentence-case labels.
- Run tests with `uv run pytest -q` (use `uv run --no-sync` if a running server holds the venv executable).

## Review Focus

- A held fund with no holdings data (a Nordnet index fund mapped to `^OMXH25`, or a Yahoo failure): listed as "no holdings data", its whole value counted as not broken down, card and Desk still build. Test in Task 1 and Task 2.
- The same company under another symbol: a fund lists `ASML.AS` or `GOOG`, the candidate is `ASML` or `GOOGL`. Must match. Test in Task 1.
- The candidate is itself a fund (buying a Nasdaq 100 ETF while holding a US IT ETF): the card shows the companies whose share rises most, not an empty line. Test in Task 2.
- A fetch error must not be cached as "not a fund": the next run retries. Test in Task 1.
- Weights given in percent instead of fractions (sum above 1): rejected with a clear error, not silently 100× too big. Test in Task 1.

---

### Task 1: Look-through core and fund cache

**Files:**
- Create: `src/nordic_desk/lookthrough.py`
- Modify: `src/nordic_desk/config.py` (`Instrument` gains `holdings_from: str = ""`, read from the optional TOML key `holdings_from`)
- Modify: `config/instruments.toml` (header comment explains `holdings_from`: Yahoo ticker whose fund holdings stand in for this instrument)
- Modify: `tests/conftest.py` (autouse fixture: monkeypatch `nordic_desk.lookthrough.yf_top_holdings` to raise `LookupError("no fund data")`)
- Test: `tests/test_lookthrough.py`

**Interfaces:**
- Produces:
  - `company_key(symbol: str) -> str`: `SAME_COMPANY = {"GOOG": "GOOGL"}` applied first, then the part before the first `"."` (so `ASML.AS` → `ASML`, `NOKIA.HE` → `NOKIA`); `BRK-B` stays `BRK-B`.
  - `yf_top_holdings(ticker: str) -> list[dict]`: `[{"symbol", "name", "weight"}]` from `yf.Ticker(t).funds_data.top_holdings`; raises `LookupError` when Yahoo says there is no fund data (message contains "No Fund data"), re-raises anything else.
  - `fund_holdings(ticker: str, cache_dir: Path = Path("data/funds"), max_age_hours: float = 20, fetch=yf_top_holdings) -> dict | None`: `None` when the ticker is not a fund (cached as `{"fund": false}`); otherwise `{"ticker", "holdings": [...], "covered": float, "fetched": float}`. Tickers starting with `^` return `{"ticker", "holdings": [], "covered": 0.0, "no_data": True}` without a fetch. Any other exception propagates and nothing is cached. Raises `ValueError` when weights sum above 1.0001.
  - `look_through(values: dict[str, float], cash: float, funds: dict[str, dict | None]) -> dict` returning `{"total", "companies": {key: {"name", "direct", "via_funds", "value", "share", "funds": {fund_ticker: eur}}}, "not_broken_down": eur, "no_data": [fund tickers]}`. `total = sum(values) + cash`. A value whose `funds[t]` is `None` (or missing) is a direct holding of `company_key(t)`; a fund adds `value × weight` per holding and `value × (1 − covered)` to `not_broken_down`; a fund with `no_data` adds its whole value to `not_broken_down` and its ticker to `no_data`.
  - `share_after(values, cash, funds, ticker, amount, cand_fund: dict | None) -> dict`: look-through after adding `amount` euros of `ticker` (with `cand_fund` as its holdings, `None` for a stock); same shape as `look_through`.

- [ ] **Step 1: Write the failing tests** in `tests/test_lookthrough.py` (invented numbers):

```python
FUND = {"ticker": "QQQ", "covered": 0.18, "holdings": [
    {"symbol": "MSFT", "name": "Microsoft", "weight": 0.10}, {"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08}]}

def test_direct_plus_fund():
    lt = look_through({"MSFT": 1000.0, "QQQ": 2000.0}, 0.0, {"MSFT": None, "QQQ": FUND})
    m = lt["companies"]["MSFT"]
    assert (m["direct"], m["via_funds"], m["value"]) == (1000.0, 200.0, 1200.0)
    assert m["share"] == pytest.approx(0.4)
    assert lt["companies"]["NVDA"]["share"] == pytest.approx(160 / 3000)
    assert lt["not_broken_down"] == pytest.approx(2000 * 0.82)

def test_share_after_stock_purchase():
    after = share_after({"MSFT": 1000.0, "QQQ": 2000.0}, 0.0, {"MSFT": None, "QQQ": FUND}, "NVDA", 1000.0, None)
    assert after["companies"]["NVDA"]["share"] == pytest.approx(1160 / 4000)

def test_symbol_variants_match():
    f = {"ticker": "F", "covered": 0.2, "holdings": [{"symbol": "ASML.AS", "name": "ASML", "weight": 0.1},
                                                     {"symbol": "GOOG", "name": "Alphabet C", "weight": 0.1}]}
    lt = look_through({"ASML": 500.0, "GOOGL": 500.0, "F": 1000.0}, 0.0, {"F": f})
    assert lt["companies"]["ASML"]["value"] == pytest.approx(600.0)
    assert lt["companies"]["GOOGL"]["value"] == pytest.approx(600.0)

def test_fund_without_data_not_guessed():
    nd = {"ticker": "^OMXH25", "holdings": [], "covered": 0.0, "no_data": True}
    lt = look_through({"MSFT": 1000.0, "^OMXH25": 500.0}, 100.0, {"^OMXH25": nd})
    assert lt["no_data"] == ["^OMXH25"] and lt["not_broken_down"] == 500.0
    assert "OMXH25" not in lt["companies"] and lt["total"] == 1600.0
```

Plus cache tests with `tmp_path` and a counting fake fetcher: `test_fund_cached_within_a_day` (second call does not fetch), `test_not_a_fund_cached` (`LookupError` → `None`, cached, not refetched), `test_fetch_error_not_cached` (`RuntimeError` propagates; a later call with a working fetcher fetches), `test_index_ticker_skips_fetch` (`"^OMXH25"` → `no_data`, fetcher never called), `test_percent_weights_rejected` (weights 10.0 and 8.0 → `ValueError`). Config test in `tests/test_config.py`: an instrument with `holdings_from = "XLK"` loads it; one without has `""`.

- [ ] **Step 2: Run** `uv run pytest tests/test_lookthrough.py tests/test_config.py -q`. Expected: FAIL (module missing).

- [ ] **Step 3: Implement** the interfaces above in `src/nordic_desk/lookthrough.py` (module docstring cites the spec), the `Instrument` field, and the conftest stub. Cache file name as in `candidates.load_or_fetch` (`^` and `=` replaced by `_`), JSON, `fetched` timestamp.

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass (existing tests unaffected by the conftest stub).

- [ ] **Step 5: Commit** `feat: fund look-through core and fund holdings cache`.

---

### Task 2: Look-through on candidate cards, configurable amounts

**Files:**
- Modify: `src/nordic_desk/cards.py` (`build_card`, `write_cards`, `AMOUNTS` → config)
- Modify: `config/target.toml` (add `card_amounts = [1000, 2000, 3000, 5000]` and `card_default = 2000`, with a comment)
- Modify: `docs/data-contract.md` (cards.json: `amounts` keyed by the configured amounts, new `lookthrough` and `meta.default_amount`)
- Test: `tests/test_cards.py`, `tests/test_write_cards.py`

**Interfaces:**
- Consumes: `fund_holdings`, `look_through`, `share_after`, `company_key` (Task 1); `Instrument.holdings_from`.
- Produces:
  - `load_card_amounts(target_path: str = "config/target.toml") -> tuple[tuple[int, ...], int]`: `(amounts ascending, default)`; falls back to `((500, 1000, 2500, 5000), 1000)` when the keys are absent; `ValueError` when the default is not among the amounts.
  - `build_card(..., funds: dict[str, dict | None] | None = None, cand_fund: dict | None = None, amounts: tuple[int, ...] = (500, 1000, 2500, 5000))`. `impact.amounts` keyed by `str(a)` for `a in amounts`. New `card["lookthrough"]`: `None` when `funds is None` or impact is unavailable; else `{"focus": [keys], "names": {key: name}, "before": {key: share}, "amounts": {str(a): {key: share}}, "not_broken_down": share, "no_data": [tickers]}`. `focus` = `[company_key(ticker)]` for a stock; for a fund (`cand_fund` given) the 3 companies whose share rises most at the largest amount.
  - `write_cards(..., get_fund=fund_holdings, target_path="config/target.toml")`: resolves funds for every held ticker (using `holdings_from` when set) and for the candidate when its `quote_type` is `"ETF"`; a held fund whose fetch raises becomes `{"ticker", "holdings": [], "covered": 0.0, "no_data": True}` for this run; writes `doc["meta"]["default_amount"]`.

- [ ] **Step 1: Write the failing tests:**
  - `test_lookthrough_on_stock_card`: holdings example (MSFT + `^OMXH25`), `funds={"MSFT": None, "^OMXH25": <no_data dict>}`, candidate LLY, amounts `(1000, 2000)` → `lookthrough["focus"] == ["LLY"]`, `before` share of LLY is 0 (absent → treat as 0.0), `amounts["2000"]["LLY"] == pytest.approx(2000 / 5250, abs=1e-4)` (example holdings 1800 + 1200 plus cash 250 = 3250), and `no_data == ["^OMXH25"]`.
  - `test_lookthrough_on_fund_card`: candidate `"ETFX"` (type ETF, prices from the `store` fixture: add it there) with `cand_fund` holding MSFT 0.3 and LLY 0.2 → `"MSFT" in lookthrough["focus"]` and its share rises from before to after.
  - `test_card_amounts_from_config(tmp_path)`: a target file with `card_amounts = [2000, 3000]`, `card_default = 3000` → `((2000, 3000), 3000)`; missing keys → the fallback; default not listed → `ValueError`.
  - `test_impact_per_amount` updated: passes `amounts=(1000, 2000)` and checks those keys.
  - In `tests/test_write_cards.py`, `test_fund_fetch_failure_does_not_stop_card`: `get_fund` raising `RuntimeError` for a held ticker → card built, that ticker in `lookthrough["no_data"]`; `meta["default_amount"]` present.

- [ ] **Step 2: Run** `uv run pytest tests/test_cards.py tests/test_write_cards.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** In `build_card`, compute look-through from the same `values` and `cash` the risk block uses (positions without ticker go into cash, as now), so the shares and the risk numbers rest on one total. Shares are rounded to 4 decimals in JSON.

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass.

- [ ] **Step 5: Commit** `feat: look-through shares and configurable amounts on candidate cards`.

---

### Task 3: Card view shows look-through

**Files:**
- Modify: `src/nordic_desk/views/cards.py` (`impact_block`, `AMOUNTS` removed: chips come from the card's `impact.amounts` keys in ascending order; the checked chip is `doc["meta"]["default_amount"]`, falling back to the first)
- Test: `tests/test_views.py`

**Interfaces:**
- Consumes: `card["lookthrough"]`, `doc["meta"]["default_amount"]` (Task 2).
- Produces: `impact_block(c: dict, default_amount: int | None = None) -> str`; `card_html(c, default_amount=None)`; `cards_page(doc)` passes the default through. Server route `/api/card` passes `doc["meta"].get("default_amount")`.

- [ ] **Step 1: Write the failing tests** (cards dicts built by hand with invented numbers):
  - `test_card_shows_lookthrough_rows`: each amount block has a row per focus company labelled `"<name> share, including funds"` with now and after percentages (e.g. `"4.0%"` → `"9.5%"`) and effect `"raises"`.
  - `test_card_lookthrough_sentence`: a stock already held through funds shows `"You already own 4.0% of the portfolio in <name>, 1.5% of it through funds."`; one not held shows `"You do not own <name> yet, directly or through funds."`
  - `test_card_lookthrough_notes`: `not_broken_down` 0.30 shows `"30% of your fund money is outside the funds' published top holdings and is not broken down."`; `no_data` lists the tickers as `"No holdings data: ^OMXH25."`; the source line `"Fund top holdings from Yahoo Finance."` appears.
  - `test_amount_chips_follow_card`: amounts `"2000"`, `"3000"` and default 3000 → two chips, the 3000 chip `checked`, its block not `hidden`.
  - `test_card_without_lookthrough`: `lookthrough` `None` renders the existing table only, no error.

- [ ] **Step 2: Run** `uv run pytest tests/test_views.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** The sentence sits above the amount chips; the rows go after "Technology share" with lower-is-better marking (a larger single-company share is more concentration). Use the existing `pct`, `esc`, `mark` helpers.

- [ ] **Step 4: Run** `uv run pytest -q`. Expected: all pass. Then build the real page once: `uv run nordic-desk ideas` and open `out/site/cards.html`.

- [ ] **Step 4b: Design pass.** Use the `impeccable` skill (polish) on the new card section: hierarchy of the sentence, rows and notes; spacing and alignment with the existing table; numbers right-aligned in tabular figures. Screenshot one stock card and one ETF card at 1280 px and 390 px wide (deviceScaleFactor 1, for yourself) and fix anything cramped, wrapped or misaligned.

- [ ] **Step 5: Commit** `feat: look-through on candidate cards`.

---

### Task 4: Desk view and `nordic-desk lookthrough`

**Files:**
- Modify: `src/nordic_desk/build.py` (`build(..., get_fund=fund_holdings)` adds `desk["lookthrough"]`; new subcommand `lookthrough`)
- Modify: `src/nordic_desk/views/huurre.py` (`lookthrough_block(desk) -> str`, placed in `desk_page` after the compare section)
- Modify: `docs/data-contract.md`, `README.md` (run order mentions `lookthrough`)
- Test: `tests/test_build.py`, `tests/test_views.py`

**Interfaces:**
- Consumes: Task 1 functions; `Instrument.holdings_from`.
- Produces: `desk["lookthrough"]` = `{"top": [{"key", "name", "share", "direct", "via_funds"} × up to 5, sorted by share], "not_broken_down": share, "no_data": [tickers], "source": "Yahoo Finance fund top holdings"}`; shares only, no euro amounts beyond what `portfolio` already holds. CLI `nordic-desk lookthrough` prints the same top 5 (name, share, of which through funds) and the not-broken-down share to the terminal, from the latest holdings, without building the site.

- [ ] **Step 1: Write the failing tests:**
  - `test_build_offline` keeps passing with `"lookthrough"` added to the desk.json contract section (the contract test reads the doc).
  - `test_desk_lookthrough_with_fund(tmp_path)`: an instruments file in `tmp_path` gives the example holding "Nordnet Suomi Indeksi" (`^OMXH25`) `holdings_from = "XLK"`; a stub `get_fund` returns `None` for `"MSFT"` and, for `"XLK"`, MSFT at weight 0.2 (covered 0.2) → `top[0]["key"] == "MSFT"`, its `via_funds > 0`, and `no_data == []`.
  - `test_desk_lookthrough_block`: hand-made desk dict renders a table captioned `"Largest companies, including funds"` with five rows and the not-broken-down note.
  - `test_cli_lookthrough(capsys, monkeypatch)`: runs `main(["lookthrough", ...])` against the example holdings with the conftest stub and prints `"Largest companies, including funds"`.

- [ ] **Step 2: Run** `uv run pytest tests/test_build.py tests/test_views.py -q`. Expected: FAIL.

- [ ] **Step 3: Implement.** In `build`, funds are resolved once per held ticker (via `holdings_from` when set); a fetch error becomes `no_data` for this run, as in Task 2. Shares use the risk total (`sum(values) + cash`).

- [ ] **Step 4: Run** `uv run pytest -q` (about 7 min). Expected: all pass. Then `uv run nordic-desk build && uv run nordic-desk site` on real data and check the Desk block by eye; confirm `git status` shows no files under `data/` or `out/` and `git diff` holds no real numbers.

- [ ] **Step 5: Commit** `feat: look-through on the desk and a lookthrough command`.

---

## After the plan

Fresh reviewer on the whole branch, fix Critical and Important findings test-first, then update `START_HERE.md` (state, next phase: news briefs) and push only on request.
