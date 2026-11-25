# Overnight work, 2026-11-19

Branch `overnight` (from `frontend`). Local commits only; the owner reviews in the morning. TDD per task.

1. Deferred minors: no chart under one year of prices; clear error when the report predates a series; zero-division guards (one holding, zero cost); stray header lines kept out of wrapped PDF names; short live sentence on Impact.
2. Other listing currencies (SEK, GBP, DKK, NOK, CHF...): portfolio comparison through Yahoo `EUR<CCY>=X` rates.
3. Analyst history: each card run appends a dated snapshot per ticker to `data/analysts_history.csv`; cards show the change since the previous snapshot.
4. Threshold alerts: `nordic-desk alerts` compares the latest status with the previous snapshot and writes `out/alerts.json`; Ideas and Aamu show a banner.
