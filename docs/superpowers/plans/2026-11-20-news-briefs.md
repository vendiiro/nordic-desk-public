# News briefs implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A sourced, AI-written news brief on each candidate card, built from free, non-paywalled articles, labelled unchecked, never entering any number.

**Architecture:** `news.py` collects articles (GDELT DOC API plus Yahoo `Ticker.news`), merges duplicates, drops paywalled or too-short pages and caches the extracted text under `data/news/`. `brief.py` makes one Claude call per ticker with a JSON-schema output, then keeps only points whose sources are real article ids. It caches by article set and enforces a monthly spend cap. `write_cards` attaches the saved brief, and `views/cards.py` renders it. The command is `nordic-desk brief <ticker>...`.

**Tech stack:** Python 3.12, `anthropic` 2.x (Messages API, `output_config.format`, server-side fallbacks), `trafilatura`, pytest.

**Spec:** `docs/superpowers/specs/2026-11-20-idea-discovery-design.md`, goal 2.

## Global constraints

- Prompts carry only the candidate's ticker, its name and public article text. Held tickers are refused.
- Keys come only from the environment. With no key, the command says so and the site builds as before.
- A monthly cap in `config/news.toml` is checked before every call. Every response is cached.
- Paywalls are never bypassed. robots.txt is respected, and requests are spaced at least 1 s apart.
- Tests use invented articles and a fake client: no network, no spend.
- Model `claude-opus-5-5` at effort `low` (the claude-api skill default; the owner can change it in `config/news.toml`).

## Review focus

- A point the model writes without a valid source id is dropped and never shown.
- An article URL that is not http(s) is never rendered as a link.
- A held ticker is refused before any request leaves the machine.
- The cap is reached: no call is made, and a clear message is shown.
- A refusal or a malformed response gives a clear error, and nothing is cached as a brief.

### Task 1: `news.py`: collect articles
- [ ] Tests: GDELT JSON parsed to `{url, title, date, site}`; company name stripped of legal suffixes for the query; Yahoo items parsed; duplicates by normalised title merged with all sites kept; paywalled domain dropped; text under `min_chars` dropped; text fetched once (cached); robots disallow skips the page.
- [ ] Implement `gdelt_articles`, `yahoo_articles`, `merge`, `collect(ticker, name, cfg, ...)` with injectable `get`, `fetch_page`, `robots_ok`, `sleep`.
- [ ] Commit.

### Task 2: `brief.py` and the `brief` command
- [ ] Tests: `clean_brief` drops unsourced and unknown-id points and caps each list at 3; tone counts only valid ids; `make_brief` with a fake client saves the brief and records spend; a second run on the same articles does not call; the cap blocks the call; a held ticker is refused; no articles means no call; a refusal raises `BriefError`.
- [ ] Implement, add `config/news.toml`, add the `brief` CLI (patches `out/cards.json`, then rewrites the site).
- [ ] Commit.

### Task 3: brief on the card
- [ ] Tests: the brief block shows the unchecked badge, article count and date range, for/against points with source links, tone counts and events; non-http URLs are not linked; a card without a brief shows the one-line command hint; `write_cards` attaches a saved brief.
- [ ] Implement in `cards.py` and `views/cards.py`. Design pass with the impeccable skill at 1280 and 390 px.
- [ ] Commit, full suite, fresh review, fix Important findings test-first, push.
