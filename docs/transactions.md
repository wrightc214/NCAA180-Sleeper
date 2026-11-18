# Transactions dashboard

The Transactions page is configured as hidden-dev. It shows completed trades, weekly player movement, and season summaries from the repository's Sleeper data. Trade grades measure the market value each team received, separately for dynasty (Rebuild) and rest-of-season market value (Contender). They are not Team Fit grades.

## Implemented rules

- Use the latest historical FantasyCalc player and pick snapshots dated on or before the trade's UTC date. Never substitute a later snapshot or today's values. Missing history and unresolved players stay ungraded. A recorded zero is a valid observation.
- An identified QB, RB, WR, TE, or FB absent from an otherwise valid player snapshot is worth zero. An identified unlisted kicker or D/ST instead gets the upcoming draft's historical **4.12** estimate in both grades. K and D/ST are required positions without a free-agent acquisition path in NCAA 180. The proxy is labeled on the card, included in point totals, and excluded from the consolidation calculation. If 4.12 cannot be estimated, withhold affected grades. The NCAA 180 K/DST pool is fully rostered, undrafted rookie kickers are claimed quickly, and a weak rookie kicker usually costs about a fourth. This market baseline is not itself a measurement of a team's lineup need.
- Traded rookie picks count in Rebuild, but are worth zero in Contender. When both sides have zero measured value, show **No measurable value**, not Even.
- The experimental KTC-style fallback is not calibrated to KTC. Cards label its credit “Experimental consolidation adjustment (KTC-style)”. It computes consolidation using eligible market assets only. Cards show adjusted points and disclose raw totals and credit in grade details.
- Only the team with the positive adjusted dynasty difference gets a surplus badge. Equivalents use the upcoming rookie draft **as of the trade**, and the badge omits the year. Asset listings still show each traded pick's actual year. At or above 4.12, show the nearest single pick through the early-first cap, then start with 1.01 and match the remaining value to a different slot above the cap when slot estimates are available. Below 4.12, find the closest estimated same-draft upgrade anchored at 4.12. If no upgrade is within 25% of the actual surplus, show points only. Estimated slots are marked approximate.
- **Blockbuster** marks a big deal with a headliner, not fairness or a winner. Both cutoffs use the most valuable player in the **full trade-date FantasyCalc snapshot**, even if that player was not traded. The combined raw dynasty market value of both sides must reach **1.40×** that benchmark, and at least one actual traded player must reach **60%** of it individually. Picks count toward the combined total but cannot be the headliner. Neither consolidation credit nor K/DST proxy points count toward either test. Incomplete dynasty valuations are ineligible. The repo owner can change both cutoffs, the grade bands, the consolidation coefficients, the K/DST proxy slot and the surplus swap tolerance in `config/transactions.json` under `transactions`. Changing the proxy slot also changes the swap anchor.
  - With an 11,000-point market leader, the thresholds are 15,400 combined and 6,600 for one player. A 1,000-point player for two 750-point players fails both; a 17,000-point pile with no qualifying player fails the second. A star plus filler can still qualify. Review real examples before adding another rule.

## Task 5.11 owner configuration

- `config/transactions.json` → `transactions` controls the grade bands, consolidation method and coefficients, Blockbuster cutoffs, proxy and small-swap settings, draft field size and interpolation anchors, movement types, and visible feature labels. A missing file, section, or key keeps the NCAA 180 defaults. The report generator embeds the resolved values in the static page. To disable consolidation and grade raw totals, set `consolidation.method` to `none`.
- `config/transactions.json` → `fantasycalc` controls the public API endpoint, scoring format, timeout and minimum acceptable response size. Changing the format affects new snapshots only. Do not mix formats in historical comparisons without checking comparability.
- Transaction cards, both week selectors, and the summary share the site’s schedule and week-label settings via `league_config.week_label()`. Week filter values stay numeric.
- `config/nav.json` owns the menu label, link and visibility. Missing state defaults to `hidden-dev`; removing the tab omits it from the menu. Dev visibility is not access control. Shared site colour tokens and CSV team colours remain the sources for styling.

## Team Fit

Team Fit is a separate, experimental team-goal grade. It compares trade-date best lineup changes and future value versus holding against the team's archived situation. The Git archive verifies pre-trade input timing and corroborates roster/pick ownership. An unverified or incomplete trade is shown as `-`, not Even. Age decline uses immutable birth dates, position-specific onset and steep decline rates, and separate one- and two-year horizons. Current market price and Blockbuster eligibility are unchanged. Missing player IDs count as zero for Team Fit. Projected wins and odds changes remain unavailable.

Owner controls live in `config/transactions.json` under `team_fit`. These are review-model settings, not direct output from FantasyCalc. Full Git history is required for historical evidence. Trade-time inference uses completed transaction records with creation timestamps and a second roster archive as a consistency check.

## Open work

1. **“Why this trade makes sense” narrative — priority follow-up.** Write a short explanation for each team, grounded in trade-date evidence. Explain what the team gains, what it gives up, and what makes the move reasonable or questionable for its competitive window. Distinguish measured market price from lineup value, flag inferred intent, and do not invent a manager's motive. Bass illustrates the difference between a league-level kicker proxy and the strategic value of filling an actual vacancy. If context is missing, say what can be established from the assets without pretending to know the team's plan.
2. **Trade-time team tags (follow-up).** Explore Rebuilder, Bowl Aspirant, Championship Contender and other clearly defined tags using roster value, record and manager activity known before each trade. Show evidence and uncertainty, then test whether tags should select goal-specific formulas. Do not turn a team's eventual result or current tags into historical intent.
3. **Projected ROS wins and before/after odds.** Validate a historical lineup-aware counterfactual against known baseline forecasts. Account for schedule, injuries and byes known at the time, replacement starters, and playoff and draft-order rules. Show title/playoff odds for contenders and bowl/1.01 odds for rebuilding teams only when supported. Until validated, leave those figures unavailable.
4. **Consolidation calibration.** Run real trade samples through both modes and audit direction, sensitivity and anomalous credits. The Montana–South Dakota trade is a regression example, not an endorsement of the fallback's Even Contender grade.

## Review examples

| Trade ID | Check |
| --- | --- |
| `1426656560473452544` Montana–Old Dominion | 18,798 combined raw dynasty market points and the Blockbuster badge. Old Dominion's adjusted dynasty surplus is 9,809 points, shown as an estimated 1.01 + 1.02. |
| `1426733052746272768` Montana–South Dakota | Not a blockbuster. Review why a 9,178-point credit nearly cancels a 9,603-point raw Contender gap. |
| `1423799198175739904` Arizona State–Oregon | Bass receives the 725-point proxy in both modes. Oregon's +372 adjusted dynasty surplus is displayed as roughly 4.12 → 3.05. The interpolated upgrade is worth 376 points. |
| `1425957598431035392` Citadel–UNC Charlotte | Qualifies. Kenneth Walker III is 6,907 raw dynasty points (63% of the snapshot leader), and the trade totals 15,922 (1.45×). |
