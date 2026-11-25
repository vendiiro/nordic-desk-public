# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **The owner**, the only real user. A long-term private investor in Finland who holds US stocks and funds through Nordnet and makes occasional lump-sum purchases. Reads Aamu on the phone in the morning after New York has closed, and does deep research on the desktop browser before a purchase.
- **Demo viewers**, secondary. People the owner shows the repository to. They only ever see the pages with invented data. The pages should look like a professional research desk to them, but are not written to teach them the basics.

## Product Purpose

A personal research desk for US stocks seen in euros. It turns local price, fundamentals, analyst and news caches into static pages that answer: what happened, what the evidence says, and whether to act or do nothing.

Success is a calm, evidence-backed buy or hold decision on a long-term purchase, not more trading. Doing nothing is a valid outcome the pages must make easy to reach.

## Positioning

The desk is built around one owner's real portfolio and euro view, not a generic market screen. Every number is computed and tested in Python, with point-in-time checks (no look-ahead). The desk checks its own verdicts against what happened afterwards (scorecard, calibrated risk models) instead of only showing signals.

## Operating Context

- Run order: `update` → `import-report <pdf>` → `build --record <csv>` → `ideas` → `plan` → `site` → `serve` (`--lan` for the phone). Pages are static HTML in `out/site`, served locally.
- Morning ritual on the phone (Aamu) after the US close (23:00 Helsinki). Research sessions on a desktop browser at about 1280 px and wider.
- Pages: home (`index.html`, a "today" overview), Aamu, Desk (with Compare), Impact, Ideas (cards, plan, before/after), Analysis (screener and one page per stock), Forecasts.
- Nordnet is the broker; holdings come from its portfolio report PDF and daily-development export.

## Capabilities and Constraints

- Python CLI renders HTML (`src/nordic_desk/views/`); small page scripts only draw and format, they never compute numbers.
- Data: Yahoo Finance (prices, OHLC, fundamentals), GDELT and Yahoo news, Claude API for news briefs (by ticker only, spend cap).
- Holdings and their values are never sent to outside services and never appear in tracked files, tests, docs, screenshots or commit messages. Real data lives only in git-ignored `config/*.local.*`, `data/`, `out/`.
- Crypto positions (`CBUT.DE`, `ETH-EUR`) are a test position and are left out of the risk models.
- Terminology: Aamu (morning view), Huurre (desk look and the Desk / Impact / Compare tabs), verdict, signal, scorecard, lump vs spread, expected return.

## Brand Commitments

- Name: Nordic Desk. Finnish names stay as names: Aamu, Huurre.
- Voice: a plain, sober analyst. Short English sentences, sentence-case labels, a proper minus sign, Helsinki times. Sources named, uncertainty stated. A term is explained once (hover), not repeatedly.
- Never promise wording ("will return"). Every page says where its numbers come from and that it is not investment advice.

## Evidence on Hand

- Real data only on the owner's machine (git-ignored). Anything shown, committed or screenshotted for others uses invented holdings and prices.
- Approved early mockups: `docs/mockups/` (Aamu, Huurre, Impact). Feature designs: `docs/superpowers/specs/`.
- No testimonials, users or performance claims exist; none may be invented. Backtests carry their caveats (for example survivorship: today's stocks only).

## Product Principles

1. Doing nothing is a first-class answer. Pages lead with what changed and whether it matters, not with a call to trade.
2. Every number has a source and a test. Show where it comes from and how sure it is.
3. The desk grades itself. Past verdicts and models are checked against outcomes and shown honestly.
4. Private by construction. Real holdings never leave the machine or the git-ignored folders.
5. One desk, two scenes: deep research on the desktop, a quick read on the phone. Both must stay usable.

## Accessibility & Inclusion

No product-specific requirement set yet. Pages must work at 1280 px desktop and 390 px phone width. An accessibility review of all pages is on the backlog.
