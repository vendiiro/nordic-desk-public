# Idea discovery from news: design

Date: 2026-11-20. Owner: Iiro. Builds on search and signals (`2026-11-18-search-and-signals-design.md`), the risk models (`2026-11-19-risk-models-design.md`) and `docs/data-contract.md`.

## Intent and why

The owner invests for the long term, not for trading. Today he follows well-known AI and technology names and broad US technology ETFs (Nasdaq 100, a US IT sector fund), and buys in lumps of a few thousand euros at a time. Two things follow from that habit:

1. **Doubling up without seeing it.** A Nasdaq 100 fund already holds the largest AI names at several percent each. Buying the same company directly on top raises the real exposure to one name more than the card's before-and-after shows, because the card treats the fund as one opaque position.
2. **A narrow funnel.** New ideas come from names that are already famous. Companies one step down the AI supply chain (power, cooling, networking, chip equipment) or good diversifiers only reach him by chance.

This project adds an **idea radar**: AI-assisted reading of public news that proposes names, writes a short sourced brief for each, and hands them to the existing cards, before-and-after, plan and optimiser. The AI reads and summarises; it does not set prices, expected returns or weights.

In the owner's words (2026-11-20): find news broadly from many websites, without paywalls, and use AI on the page to interpret the news and to plan purchases with care.

Success: once a week he opens the Ideas page, sees a handful of new names with a reason and sources, sees for any name how much of it he already owns through his funds, and can decide on a lump purchase in a few minutes.

## Goals

### 1. Look-through exposure (first, no AI needed)

- For each held fund, fetch its top holdings and weights from Yahoo (`yfinance` `Ticker.funds_data.top_holdings`, cached daily under `data/`).
- Portfolio look-through: euros and share of the portfolio in each underlying company = direct holding + sum over funds of (fund value × company weight in the fund). Holdings outside a fund's published top list count as "rest of fund", never guessed.
- On every candidate card, a new line in the before-and-after: "you already own X% of the portfolio in this company through funds; after the purchase Y%". Same for the five largest look-through names on the Desk view.
- The card's amounts become configurable in `config/target.toml` (`card_amounts`), so the owner's usual lump sizes show by default.

### 2. News brief per candidate

- For a candidate ticker, collect the last 30 days of articles from broad, free, keyless sources: the GDELT DOC API (worldwide news, direct article links, at most one request every 5 seconds), Google News RSS search, and Yahoo news (`Ticker.news`, the latest few only). Both GDELT and Google News answered without a key on 2026-11-20.
- **No paywalls.** Each article page is fetched once, politely (robots.txt respected, one request per site per few seconds), and its text extracted locally (for example `trafilatura`). An article is dropped when its site is on the paywall list in `config/news.toml` (seeded with sites such as Seeking Alpha, Investor's Business Daily, WSJ, Bloomberg, FT, Barron's) or when the extracted text is too short to be the full article. Paywalls are never bypassed.
- Duplicates (the same wire story on many sites) are merged into one item that lists every site carrying it.
- Claude writes a brief: what the company does in two plain sentences, up to three points for and three against, upcoming dated events (earnings, product launches) found in the articles, and a tone count (positive, negative, neutral articles). Every point carries the link(s) it rests on; a point without a source is dropped.
- Shown on the card as its own block "News brief (AI summary, unchecked)", with the article count, the date range and the publishers. It never changes the analyst block, thresholds, status or expected return.

### 3. Radar: proposing names

- Themes are the owner's, in `config/themes.toml`: a name, a one-line description, a few search phrases and a few seed tickers each (for example "AI infrastructure: power, cooling, networking, chip equipment"; "diversify: health care, staples, Europe").
- Weekly run: for each theme, search the free sources above for its phrases and seed tickers over the last 30 days, and ask Claude which listed companies the articles point to that fit the theme, with a one-sentence reason and the article links. Massive related companies (`/v1/related-companies/{ticker}`) is an optional extra when a key is set.
- Hard filters after Claude, in code: allowed exchanges and types from `candidates.py`, mid or large company, at least one year of prices, at least 5 analysts. Names already held or already in `ideas.toml` are marked, not repeated.
- Survivors (at most 8 per theme) become candidate cards in a new group `radar`, each with its brief and the reason it was proposed. A name stays on the radar for 4 weeks unless the owner pins it to `ideas.toml`.

### 4. AI on the page: interpreting news and planning a purchase

- Runs through the local server (`nordic-desk serve`, behind its existing guards); the static site shows the last saved answers.
- **Ask about a candidate:** a question box on each card ("what changed this month?", "what is the bear case?"). Claude answers only from that card's collected articles and public facts, and every claim links to an article; a question the articles cannot answer gets "the collected news does not say".
- **Purchase note:** before a lump purchase, a button writes a considered note for the chosen ticker and amount: the thesis in two sentences, what would prove it wrong, dated events in the next months (earnings and the like) and whether they fall before or after the planned buy, and the local numbers next to it (look-through, before-and-after, plan split). The note lists considerations and never says "buy" or "sell".
- For the purchase note only, Claude also sees **rounded shares** computed locally: technology share, the candidate's look-through share, the five largest look-through names, and the before-and-after changes, each rounded to whole percent (owner's decision). Never euro amounts, the full holdings list, account data or names of held positions outside the top five look-through names. The exact text sent is shown under the note on the page.

### 5. Validation: is news tone worth anything at 3 to 12 months?

- A backtest command checks whether the news tone predicts excess return over SPY at 3, 6 and 12 months, before tone may ever enter the maths. The free sources above do not reach back far enough, so the backtest uses Massive's dated news archive (needs `MASSIVE_API_KEY`); without it the check reports "cannot be checked".
- Monthly rebalance dates over the period Massive's archive covers (articles back to at least 2022 were seen). On each date, use only articles published before that day's close; tone per ticker over the previous 30 days; universe = every ticker tagged in those articles that passes the radar's hard filters on that date (news-based, so it is point-in-time and avoids picking today's survivors).
- Measure: rank correlation between tone and forward excess return per date, its mean and a block-bootstrap confidence interval (overlapping horizons), and the top-minus-bottom third spread. The pass bar is fixed in the config before the first run: the interval for the 6-month horizon excludes zero on the later half of the period, held out.
- Result written to `out/news_check.json` and shown on the Ideas page. Until it passes, every tone number carries the label "unchecked: no evidence it predicts returns". If it passes, a later design decides how it enters the expected-return row; that is not in this project.

## Non-goals

- Day trading, intraday news alerts, price targets of our own.
- Social media in this version. Later, X can be added to the brief as an optional "social pulse" through an xAI API key, labelled unchecked; never through the owner's X login cookies (automated use of a logged-in account may breach X's terms and risk the account). Meanwhile the `last30days` skill can be run by hand in a chat.
- Tone or any AI output entering the expected return, plan or optimiser in this project.
- Placing orders.

## Anti-goals (a failure even if it works)

- Any euro amount, the holdings list or account data sent to Claude, Massive or any other outside service. Briefs and radar prompts carry only candidate tickers, theme text and public article text. The one exception is the purchase note's rounded shares, described in goal 4.
- An AI claim on a page without its source link, or a brief that reads like advice ("buy", "strong buy"). The brief describes; the analyst block and the owner decide.
- A radar that fills up with tiny, thinly covered or meme stocks because they are loud in the news.
- A tone number shown without its "unchecked" label, or a backtest that uses an article published after the rebalance date.
- Surprise costs: an API bill the owner did not see coming.
- Paywalled text scraped, a paywall bypassed, or a site hammered with requests.

## Constraints

- Keys only from environment variables (`ANTHROPIC_API_KEY`, `MASSIVE_API_KEY`), never in config or the repository. Without a key the feature says so and the rest of the site builds as before.
- Every Claude response and every fetched article cached under `data/news/` by article id, so a rerun costs nothing; a monthly spend cap in `config/news.toml`, checked before each call, stops the run with a clear message when reached.
- Claude through the Anthropic Python SDK; model ids, structured output and pricing from the `claude-api` skill at build time, not from memory. Use a small model for tagging and tone, a larger one only for briefs.
- Static pages and command-line runs like the rest of the desk: `nordic-desk lookthrough`, `nordic-desk brief <ticker>...`, `nordic-desk radar`, `nordic-desk news-check`. The local server may later get a "write brief" button behind its existing guards.
- Repository is shown to other people: test fixtures use invented articles and invented holdings; real output only in `data/` and `out/`.
- Pages keep the Huurre style, say where numbers come from, and say "not investment advice".
- **Visual quality (owner, 2026-11-20):** the card additions and the AI assistant (question box, answers, purchase note) must look professional and work well, on desktop and phone. Each UI task ends with a design pass (`impeccable` skill, polish and critique) and screenshots checked at desktop and phone width; loading, empty, error and "no key" states are designed, not left as raw text.

## Decided by the owner

- Long-term holdings, not day trading.
- Signals from news, social media and other public sources feed the existing cards, before-and-after, plan and optimiser.
- No holdings or values to outside services, except rounded portfolio shares in the purchase note (decided 2026-11-20).
- An AI signal is shown separately from the analyst number, and a signal that cannot be checked is shown as unchecked.
- The owner skipped the question round and asked for the design directly (2026-11-20).
- Build order: look-through, briefs, radar, backtest (approved 2026-11-20).
- News from many free websites, no paywalls; AI on the page interprets the news and helps plan purchases with care.
- X later through an xAI API key, not through the owner's account.

## My calls (the owner can change these)

- **Order:** look-through first (most useful for his buying habit, no cost, no AI), then briefs, then radar, then the backtest.
- **Sources:** GDELT for breadth (free, keyless), Yahoo news as an extra, Massive only for the backtest archive. Paid search services (Firecrawl and the like) are left out.
- **Google News RSS left out (decided while building, 2026-11-20):** its item links are Google redirect tokens that need an undocumented call to resolve, so robots.txt and the paywall list cannot be checked against the real site first.
- **Model:** `claude-opus-5-5` at effort `low`, one call per ticker for both brief and tone (cheaper than two calls); model, effort, prices and the monthly cap live in `config/news.toml`.
- **Tone never enters the maths in this project**, even if the backtest passes; that needs its own decision.
- **Radar filters:** mid or large company, at least 5 analysts, at least one year of prices, at most 8 names per theme, 4 weeks on the radar.
- **Brief language:** English like the rest of the site.
- **Briefs only for candidates, not for held tickers**, so the set of holdings never leaves the machine through this feature.

## Open points to check at build time

- Massive free-tier limits (calls per minute, how far back the archive goes, whether the `insights` sentiment field exists for older articles). If the archive or limits do not support the backtest, it is reported as "cannot be checked" and tone stays unchecked.
- Claude cost per brief and per radar run, measured on the first runs and shown in the run log, to set the default monthly cap.
- Whether Yahoo's fund top holdings cover the owner's European-listed fund share classes; where they do not, map the fund to its US equivalent in `config/instruments.toml` (for example a Nasdaq 100 UCITS fund to QQQ's holdings), stated on the page.

## Left to the builder

Module layout (suggested `lookthrough.py`, `news.py`, `brief.py`, `radar.py`, `newscheck.py`), cache formats, prompt wording, the card and Ideas page layout within Huurre, and the tests (fixtures with invented articles; Claude and Massive calls behind injectable fetchers like `candidates.py`).
