# Search and signals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (chosen: native). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Search stocks and ETFs by ticker or name, and show for each a candidate card: multi-year price and results, size and sector, analyst ratings with buy and sell thresholds, and the before-and-after effect on the owner's portfolio.

**Architecture:** Three new engine modules: `candidates.py` (Yahoo search and per-ticker data, cached), `signals.py` (pure maths: thresholds, status, size, implied return), `cards.py` (assembles a card dict incl. portfolio impact via `panel.py` and `risk.py`). CLI commands `search`, `card`, `ideas` write `out/cards.json`; the view `views/cards.py` renders `out/site/cards.html`.

**Tech Stack:** Python 3.12, uv, pandas, numpy, yfinance, pytest; Hallmark floor for the page.

**Spec:** `docs/superpowers/specs/2026-11-18-search-and-signals-design.md`.

## Global Constraints

- Exchanges allowed (Yahoo exchange codes): `NYQ`, `NMS`, `NGM`, `NCM`, `ASE`, `PCX`, `BTS`, `HEL`, `GER`. Quote types: `EQUITY`, `ETF`.
- Buy margin 0.15 and thin-coverage limit 5 analysts from `config/signals.toml`; size cut-offs 10e9 and 2e9 USD.
- Portfolio comparison needs ≥ 254 aligned daily closes, else "not enough price history for the portfolio comparison".
- Targets and thresholds in the listing currency; risk and expected return in euros.
- Missing data shows "not available"; never guessed. Real data only under `data/` and `out/`.

## Review Focus

- A search hit on an allowed exchange but with no analyst data → card shows "no analyst coverage", status absent, not an error.
- A listing in SEK or GBP → no crash; risk numbers say "not available (currency)" unless Yahoo FX for it exists.
- Network failure during `card` → that ticker is reported by name and the other cards are still written.
- An ETF → results section says "no company results (fund)".
- Upside negative (price above mean target) → status "above sell threshold".

---

### Task 1: Signals maths (`src/nordic_desk/signals.py`, `tests/test_signals.py`)
Produces: `load_signal_config(path="config/signals.toml") -> dict` (`buy_margin`, `thin_coverage`); `thresholds(target_mean, margin) -> (buy_below, sell_above)`; `status(price, buy_below, sell_above, n_analysts, thin) -> str` one of `"below buy threshold" | "between thresholds" | "above sell threshold" | "thin coverage" | "no analyst coverage"`; `size_label(market_cap) -> "large" | "mid" | "small" | None`; `rating_share(counts: dict) -> float | None` (strongBuy+buy over total); `implied_return(weights: dict[str, float], upside: dict[str, float | None]) -> (value | None, covered_share)`.
Tests: margin 0.15 with target 115 gives buy_below 100 and sell_above 115; status for price 99, 110, 120; thin coverage at 4 analysts; size cut-offs; rating share with zeros gives None; implied return weighting and covered share.

### Task 2: Candidate data (`src/nordic_desk/candidates.py`, `tests/test_candidates.py`)
Produces: `search(text, fetch=yf_search) -> list[dict]` (symbol, name, exchange, type), filtered by Global Constraints; `fetch_candidate(ticker, fetch_info, fetch_recs, fetch_fin) -> dict` (name, sector, industry, currency, quote_type, market_cap, target_mean/low/high, n_analysts, rating_counts, results: list of {year, revenue, net_income}); `load_or_fetch(ticker, cache_dir=Path("data/candidates"), max_age_hours=20, **fetchers)`.
Tests with fakes: exchange and type filter; ETF has empty results; cache hit does not call fetchers; fetch error raises a named error.

### Task 3: Card assembly (`src/nordic_desk/cards.py`, `tests/test_cards.py`)
Consumes: Tasks 1–2, `prices`, `panel.eur_panel`, `risk.portfolio_stats`, `risk.add_scenario`, `config.load_holdings`.
Produces: `build_card(ticker, data: dict, holdings_path, price_root, end, analysts: dict[str, dict]) -> dict` with `price` (5-year dates, close, spy_scaled, worst_fall, ret), `size`, `sector`, `results`, `analysts` (count, rating_share, targets, upside, buy_below, sell_above, status), `impact` (None or per amount 500/1000/2500/5000: vol, beta, worst, enb, tech, expected_return before and after, covered share, corr with portfolio). Candidate counts as tech when sector is "Technology".
Tests on a synthetic store: impact None with < 254 closes; impact keys per amount; tech flag from sector; expected return uses analyst upside of holdings.

### Task 4: CLI and ideas (`config/ideas.toml`, `config/signals.toml`, `build.py`)
`nordic-desk search <text>` prints matches; `nordic-desk card <tickers...>` updates prices for those tickers, fetches analyst data for holdings and candidates, writes or merges `out/cards.json`; `nordic-desk ideas` does the same for every ticker in `config/ideas.toml` (groups `diversify` and `growth`). One failing ticker is reported and skipped. Test: card command on fakes writes cards.json with the failing ticker listed under `errors`.

### Task 5: Cards view (`src/nordic_desk/views/cards.py`, `views/site.py`, `tests/test_views.py`, `docs/data-contract.md`)
Huurre style page: ideas grouped, then searched cards; each card shows price chart vs SPY with worst fall, size, sector line with correlation sentence, results table, analyst block (rating share %, count, targets, buy below / sell above, status), before/after table with an amount switch (500 to 5,000), raising/lowering marks. Site index links "Ideas and search". Tests: thin coverage text, ETF results text, impact missing text, no NaN.

### Task 6: Real run and checks
`uv run nordic-desk ideas`, `card` for two searched tickers, `site`; `sloplint --scope app` clean; screenshots at 1440 and 500; full test suite green.
