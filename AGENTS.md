# Agent guide: Nordic Desk

A personal long-term stock research desk, shown in euros: static HTML pages built from local caches by a Python CLI.

## Commands

- Set up: `uv sync`. When a running `nordic-desk serve` locks `.venv/Scripts/nordic-desk.exe`, use `uv run --no-sync ...`.
- Tests: `uv run --no-sync pytest -q` (about 440 tests, 7 min). Run single files while working. Never run two pytest processes at once: they share `.pytest_tmp`.
- Desk run order: `update` → `import-report <pdf>` → `build [--record <csv>]` → `ideas` → `plan` → `site` → `serve` (`--lan` for the phone). `site` takes about 40 s.

## Map

- Data: `prices.py` (total-return closes) and `ohlc.py` (split-only OHLC) refetch the full history on every update. `fundamentals.py`, `history.py` (analyst snapshots), `candidates.py`/`cards.py` (Ideas cards), `news.py`/`brief.py` (news briefs, Claude API, spend cap).
- Maths: `indicators.py`, `verdict.py` (fixed rules, thresholds in `config/analysis.toml`), `risk.py`/`forecast.py` (risk models), `scorecard.py`, `lumpspread.py`, `targets.py`, `expected.py`, `volsize.py`, `forecasts.py` (writes `out/forecasts.json`).
- Pages: `views/` renders HTML in Python with the Huurre tokens from `views/core.py`. Interactive pages embed JSON and a small script (`analysis.js`, `forecasts.js`). The scripts only draw and format; every number is computed in Python and tested.
- Designs live in `docs/superpowers/specs/` and plans in `docs/superpowers/plans/`. Each feature has both.

## Rules

- **Privacy:** the repo can be shown to others. No real holding values, amounts, results, account numbers or personal email go in tracked files, tests, docs, screenshots or commit messages. Real data lives only in the git-ignored `config/*.local.*`, `data/` and `out/`. Before a push, check the diff for the values in `config/holdings.local.toml`.
- Pages say where their numbers come from and that they are not investment advice. Never write promise wording ("will return").
- Point in time: no look-ahead in any backtest or rebuilt signal.
- Tests use invented prices only. Work test-first: write the failing test, then the code.
- Never send holdings to outside services. Analysis calls go out by ticker only.
- Git: branch off `main`, open a PR, merge with merge commits. Commit or push only when the owner asks.

## Working with the owner

- Decisions go to the owner as multiple-choice questions, with the recommended option first.
- Bigger work follows: brainstorm → written design → plan → build test-first → fresh whole-branch review (most capable model) → fix Critical/Important findings test-first → PR.
- Design work uses the `impeccable` skill (critique → shape → mockups → build → polish), within the Huurre look.
- Check UI in a browser at 1280 and 390 px. Headless Chrome has a window minimum of 504 px, so use the Playwright MCP's resize or a 390-px iframe for phone views.
