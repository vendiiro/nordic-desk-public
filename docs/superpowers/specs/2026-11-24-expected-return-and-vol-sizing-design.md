# Combined expected return and volatility-sized purchases: design

Date: 2026-11-24. Owner: Iiro. Builds on the forecast window (`2026-11-23-forecast-window-design.md`) and the stock-first Forecasts page (branch `forecast-page-redesign`). This covers research ideas 4 and 7. Ideas 5 and 6 were not chosen.

## Intent and why

The Forecasts page tells the owner how the desk's signals did and whether to buy a lump at once or spread it. It does not say what return to expect from a stock, and it gives no sizing advice when markets are jumpy. He buys lumps of a few thousand euros for the long term.

- **Idea 4, combined expected return.** One 12-month expected return per stock, built from pieces the desk already has, pulled toward a market anchor. It replaces "analyst upside" as the number he looks at first. Basis: Rapach, Strauss & Zhou (2010): simple averages of forecasts beat single predictors out of sample, and shrinking toward a benchmark limits noise.
- **Idea 7, volatility-sized purchases.** When a stock's volatility is far above its usual level, suggest putting only part of the lump in now and the rest over the next months. Then test that rule on history next to lump and spread, so he can see whether it would actually have helped. Basis: Moreira & Muir (2017, *Journal of Finance*), "Volatility-Managed Portfolios". That evidence comes from factor portfolios, not single purchases, so the page says so.

## Owner decisions (2026-11-24)

- **Anchor:** SPY's own annualised total return in euros since 2015, from the desk's data.
- **Blend:** an equal average of the available pieces, then pulled halfway toward the anchor.
- **Volatility sizing:** both a suggestion and a historical test as a third strategy in the lump planner.
- **Placement:** new sections on the Forecasts page, each feeding the stock summary at the top. No other page changes.

## Goals

### Idea 4: combined expected return (`expected.py`)

- **Anchor** = (SPY_EUR last / SPY_EUR first)^(252 / trading days) − 1, over the stored total-return history. It is shown with its period, for example "SPY 2015–2026: x%/yr".
- **Pieces** per stock, each a 12-month return forecast:
  - *Analyst*: realistic upside (`targets.realistic`, analyst upside − overshoot), when the stock has an Ideas card with a mean target.
  - *Signal*: anchor + the pooled 12-month (252-day) mean excess vs SPY for today's verdict group. It is used only when that pooled group's reading is not "too few". Pooled means across all stocks; per-stock numbers are too noisy.
- **Combined** = 0.5 × anchor + 0.5 × mean(available pieces). With no pieces it equals the anchor, marked "anchor only".
- **Output** per subject: `{anchor, analyst, signal, combined, pieces}` in `forecasts.json` under `expected`, plus the anchor's period.
- **Page:** a new section "Expected return, 12 months" with a table of every subject (combined, then each piece, then a "pieces used" count; the selected stock's row is highlighted). A one-line method note credits Rapach et al. and warns that the signal piece shares the scorecard's survivorship bias and that the anchor comes from a strong decade. The summary at the top gains a fourth fact, "Expected return, 12 m", showing the combined value and its pieces.

### Idea 7: volatility-sized purchases (`volsize.py` + `lumpspread.py`)

- **Volatility** = the existing 63-day annualised volatility (`indicators.compute` → `vol`), on total-return closes in euros.
- **Usual volatility at date s** = the median of the 63-day volatility over all days up to and including s. This is point in time.
- **First part at s** = clamp((usual / current)², 0.25, 1.0). Calm or normal markets give 1.0, which is the same as a lump. Doubled volatility gives 0.25.
- **Suggestion (today)**, per stock: current and usual volatility, and the first part as a share and in euros of the typed amount. The rest is split equally over the selected spread period. Wording: "Volatility now 38% vs usual 24%: put about 40% in now and the rest over 6 months." When the first part is 1.0: "Volatility is normal: no reason to hold back."
- **Historical test:** a third strategy, "vol-sized", in `lumpspread.outcomes`. At each start s it invests the first part f_s at s and spreads the remaining (1 − f_s) equally over the k month starts s₀…s_{k−1}, using the same k as spread. It is valued at s + 252 with idle cash at 0%. Statistics: the share of starts where vol-sized beat lump, the share where it beat spread, the median value, and the worst 5% (per €1).
- **Page:** the lump planner gains a third column "Vol-sized", a sentence comparing it with the other two, and the suggestion line. The summary's lump fact gains the suggestion when the first part is below 1.0.

## My calls (settled after the builder check)

- **Vol-sized timing:** the first part f is bought at s. The rest (1 − f) is bought in k equal parts at the next k month starts (s₁…s_k), so "now" means f alone. Valued at s + 252; a start needs s_k ≤ s + 252. With f = 1 it equals lump.
- **Usual volatility needs ≥ 252 observations of 63-day volatility up to s.** Vol-sized statistics use only the starts that have this, and lump and spread are compared on that same subset, with its own n shown. The existing lump/spread statistics stay unchanged. Today's suggestion needs the same minimum; otherwise it says "not enough history to judge volatility".
- **Ties:** the page reports how often vol-sizing held back (f < 1). The "beat lump" and "beat spread" shares and medians are computed only over those starts. If it never held back: "never triggered in this history".
- **Expected-return table:** only stocks used in the scorecard (not SPY, not excluded tickers). The analyst piece applies only to those stocks, and a note says it is price-only, in the listing currency.
- **Signal piece:** included only when the pooled 252-day group reading is "helps" or "works against" (evidence either way). It is omitted for "no clear edge", "too few", or no group today.
- **Anchor period:** SPY's full stored history. The label shows the real first and last year.

## Non-goals

- Ideas 5 (1–5-year ranges) and 6 (recession risk).
- Changes to the optimiser or to the Ideas cards' expected-return row.
- Valuation (P/E) or momentum as separate pieces. Momentum is already inside the verdict signal, and the P/E history is too short.
- Any AI. No new data sources.

## Anti-goals

- A combined number shown without its pieces, or without saying it is pulled toward the anchor.
- Look-ahead in the usual volatility (it must use only data up to each date).
- Claiming vol-sizing helps when the historical test says it doesn't.
- Promise wording ("will return", "expect to gain").

## Constraints

- Computed at `site` time from local caches. The browser only picks values and scales euros.
- Known-answer tests: the anchor formula, the blend with 0, 1 and 2 pieces, the clamp bounds, point-in-time usual volatility, and the vol-sized arithmetic (f = 1 equals lump; the hand-computed two-step case).
- Reuse `eur.eur_closes`/`asof`, `indicators.compute`, `scorecard` stats, `targets.realistic`, `lumpspread.outcomes`, and the page patterns of the redesigned Forecasts page.
- Privacy and wording rules as before. Screenshots use invented data.

## Left to the builder

Module split; JSON shapes; histogram for vol-sized (not required); copy within the wording rules; tests and fixtures.
