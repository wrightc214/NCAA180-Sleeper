# Transactions dashboard

The Transactions page is configured as hidden-dev. It shows completed trades, weekly player movement, and season summaries from the repository's Sleeper data. Trade grades measure the market value each team received, separately for dynasty (Rebuild) and rest-of-season market value (Contender). They are not Team Fit grades.

## Implemented rules

- Use the latest historical FantasyCalc player and pick snapshots dated on or before the trade's UTC date. Never substitute a later snapshot or today's values. Missing history and unresolved players stay ungraded. A recorded zero is a valid observation.
- An identified QB, RB, WR, TE, or FB absent from an otherwise valid player snapshot is worth zero. An identified unlisted kicker or D/ST instead gets the upcoming draft's historical **4.12** estimate in both grades. K and D/ST are required positions without a free-agent acquisition path in NCAA 180. The proxy is labeled on the card, included in point totals, and excluded from the consolidation calculation. If 4.12 cannot be estimated, withhold affected grades. This baseline is not a measurement of a team's lineup need.
- Traded rookie picks count in Rebuild, but are worth zero in Contender. When both sides have zero measured value, show **No measurable value**, not Even.
- The KTC-style fallback is not calibrated to KTC. It computes consolidation using eligible market assets only. Cards show adjusted points and disclose raw totals and credit in grade details.
- Only the team with the positive adjusted dynasty difference gets a surplus badge. Equivalents use the upcoming rookie draft **as of the trade**, and the badge omits the year. Asset listings still show each traded pick's actual year. At or above 4.12, show the nearest single pick through the early-first cap, then up to two picks above the cap. Below 4.12, find the closest estimated same-draft upgrade anchored at 4.12. If no upgrade is within 25% of the actual surplus, show points only. Estimated slots are marked approximate.
- **Blockbuster** highlights size, not fairness or a winning team. The combined raw dynasty market value across both sides must be at least **1.5× the highest player dynasty value in the same snapshot**. Neither consolidation credit nor proxy points count. Incomplete dynasty valuations are ineligible. The threshold is adjustable in `config/transactions.json`; treat it as an initial cutoff to review across seasons.

## Open work

1. **“Why this trade makes sense” narrative — priority follow-up.** Write a short explanation for each team, grounded in trade-date evidence. Explain what the team gains, what it gives up, and what makes the move reasonable or questionable for its competitive window. Distinguish measured market price from lineup value, flag inferred intent, and do not invent a manager's motive. Bass illustrates the difference between a league-level kicker proxy and the strategic value of filling an actual vacancy. If context is missing, say what can be established from the assets without pretending to know the team's plan.
2. **Team Fit.** Build an independent team-specific grade using reconstructable trade-date rosters, standings and lineup context. Grade neither team where required inputs are unavailable for that team. Do not use future standings or today's rosters.
3. **Projected ROS wins and before/after odds.** Validate a historical lineup-aware counterfactual against known baseline forecasts. Account for schedule, injuries and byes known at the time, replacement starters, and playoff and draft-order rules. Show title/playoff odds for contenders and bowl/1.01 odds for rebuilding teams only when supported. Until validated, leave those figures unavailable.
4. **Consolidation calibration.** Run real trade samples through both modes and audit direction, sensitivity and anomalous credits. The Montana–South Dakota trade is a regression example, not an endorsement of the fallback's Even Contender grade.

## Review examples

| Trade ID | Check |
| --- | --- |
| `1426656560473452544` Montana–Old Dominion | 18,798 combined raw dynasty market points and the Blockbuster badge. Old Dominion's adjusted dynasty surplus is 9,809 points. |
| `1426733052746272768` Montana–South Dakota | Not a blockbuster. Review why a 9,178-point credit nearly cancels a 9,603-point raw Contender gap. |
| `1423799198175739904` Arizona State–Oregon | Bass receives the 725-point proxy in both modes. Oregon's +372 adjusted dynasty surplus is displayed as roughly 4.12 → 3.05. The interpolated upgrade is worth 376 points. |
