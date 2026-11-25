# Nordic Desk: design

Date: 2026-11-18. Owner: Iiro. Repo: `vendiiro/nordic-desk` (private).

## Goal

A personal research tool for US stocks, seen from Helsinki, in euros. Two views over one engine:

- **Aamu** (morning): a quick review on the phone after New York has closed. Portfolio value in euros, last night's move against SPY in one sentence, top and bottom movers, the watchlist as small multiples on one scale, the currency effect.
- **Huurre** (hoarfrost): the deep-dive desk on the computer. Three tabs:
  - **Desk**: watchlist ledger (price, today, 1 month, YTD, 52-week range, 3-month trace), the selected stock (chart against SPY, periods, facts), the portfolio strip.
  - **Impact**: the real portfolio's risk (money share against risk share per holding, volatility, beta, effective holdings, technology share, correlation and bad-day correlation), what-if (add new money to a stock, or sell a holding and spread the money pro rata), a glossary (idea, formula, your number), the time-weighted record against SPY in euros.
  - **Compare**: up to four stocks rebased to 100 with SPY, plus a metrics table.

The approved mockups are in `docs/mockups/` (`aamu.html`, `huurre.html`, `impact.html`); their generator scripts are in `docs/mockups/src/` as reference for the numbers and the markup. Kaamos is dropped.

## Data

- Prices: Yahoo Finance through `yfinance`, auto-adjusted daily closes. The Massive MCP is a manual fallback, not wired into the engine.
- A local price store (`data/prices/<ticker>.csv`, git-ignored) that updates incrementally. Default history starts 2015-01-01 so longer history is already there when forecasting comes.
- Euro conversion with `EURUSD=X` (USD per EUR), carried forward onto trading days.
- Holdings come from the Nordnet portfolio report PDF or by hand, stored only in `config/holdings.local.toml` (git-ignored). The weekly record comes from Nordnet's daily-development export (UTF-16, tab-separated, comma decimals), read from a path given at run time and never copied into the repo.
- Instruments Yahoo cannot price use a stand-in from `config/instruments.toml`: QDVE.DE and CBUT.DE (same funds), EQQQ.DE for Amundi Nasdaq-100, ^OMXH25 for Nordnet Suomi Indeksi, ETH-EUR for the Ether tracker. Nordnet One Balanced and cash count as zero return.

## Numbers (must match the mockups for the same inputs)

- Returns over 1 week, 1 month, 3 months, 6 months, YTD and 1 year use 5, 21, 63, 126 trading days, the last close of the previous year, and the first close of the window.
- Volatility: sample std of daily returns × √252 (21 days for the short figure). Beta: cov/var against SPY over the window. Worst fall: min of value ÷ running peak − 1.
- Portfolio risk in euros on a weekday calendar, forward-filled, 252 daily returns, today's weights held fixed. Euler risk shares RCᵢ = wᵢ(Σw)ᵢ/σ². Effective holdings 1/Σwᵢ² with cash included. Bad-day correlation on days where the portfolio return is at or below its 20th percentile.
- Time-weighted record: weekly rᵢ = (Vᵢ − ΔDᵢ)/Vᵢ₋₁ − 1.
- Reference values from the mockup run on the owner's real holdings are kept outside the repository, in the git-ignored `config/reference.local.md`.

## Privacy

The repo is private and may hold code that reads real holdings, but real holdings, export files and the Nordnet account number are never committed: `config/*.local.toml`, `data/` and `out/` are git-ignored. Tests use invented holdings.

## Copy and design rules

From the mockups: sentence-case labels, no tracked capitals, a proper minus sign, Helsinki times (US close 23:00, open 16:30), every page says where its numbers come from and that it is not investment advice. Hallmark floor applies to the front end.

## Later (not in the first build)

Longer history in the views, forecasts (GARCH-t, block bootstrap, regime switching) with calibration, hosting Aamu where the phone can reach it without exposing holdings.
