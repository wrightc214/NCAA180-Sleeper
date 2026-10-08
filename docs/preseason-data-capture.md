# Preseason data capture (every season)

Feeds the Professor poll bot's frozen preseason prior. The prior blends, as percentiles across
every team that season (weights in `config/poll.json` -> `professor.prior`):

| Input | Weight | Source file |
|---|---|---|
| Preseason Starter Value (PSV): redraft value of each team's best legal lineup | 30% | `data/TeamValuesPreseason_Historic.csv` (`PSV`) - or a preseason ranking in `data/PreseasonRank_Historic.csv` when a season has no values |
| Week-1 projected starter points | 50% | `data/TeamProjectionsWk1_Historic.csv` (2026+), `data/backfill/TeamProjections_History.csv` (2019-2025) |
| Preseason dynasty team value | 10% | `data/TeamValuesPreseason_Historic.csv` (`DynastyValue`) |
| Last season's final rank | 10% | final poll in `data/Poll_Historic.csv` (standings if no poll) |

A team missing an input gets the other weights rescaled to 100%. Nothing is left blank.

## Each season
1. **Before week 1 kicks off, after the rookie drafts:** capture team values. One row per
   team: `Year, CaptureDate, LeagueID, LeagueName, RosterID, Team, OwnerName, DynastyValue,
   PSV, Note` into `data/TeamValuesPreseason_Historic.csv` (player-level values, if kept:
   `data/PlayerValuesPreseason_Historic.csv`). A capture taken after week 1 leaks results:
   note the date; list the season in `professor.exclude_value_years` if it shouldn't count.
2. **After week-1 lineups lock (any time after; the projections feed keeps past weeks):** run
   the **Week-1 Projection** workflow (Actions -> Week-1 Projection -> Run; blank year =
   current season). It writes `data/TeamProjectionsWk1_Historic.csv` and, once the poll
   engine is on main, rebuilds the prior (`data/PollPrior_Season.csv`).
3. **Rollover:** move the season's `PollPrior_Season.csv` rows to `PollPrior_Historic.csv`
   with the other `_Season` -> `_Historic` moves.

## Adding a missing past season (2019, 2020 and 2026 have no preseason values today)
1. Add the rows to `data/TeamValuesPreseason_Historic.csv` (values) or
   `data/PreseasonRank_Historic.csv` (`Year, SourceDate, LeagueID, LeagueName, RosterID, Team,
   Rank, ListedAs, Note`; rank 1 = best). Map every row to a roster slot (LeagueID + RosterID)
   by that season's names (`data/TeamNames_Historic.csv`); leave unresolved rows without IDs.
2. Rebuild that season **and every season after it**, in order (each season's final poll
   feeds the next season's prior):
   `python scripts/poll_backfill.py --years <year> ... <current year> --force`
   then `python scripts/poll_page.py`.

## Coverage today
| Season | PSV | Week-1 projection | Dynasty | Last final |
|---|---|---|---|---|
| 2019 | - | yes | - | - (first season) |
| 2020 | - | yes | - | yes (new leagues: -) |
| 2021 | yes (Chris's 9/6/21 ranking; 3 slots unresolved) | yes | - | yes (Ohio Valley: -) |
| 2022 | yes (9/13/22 sheet, after week 1) | yes | yes | yes |
| 2023 | yes | yes | yes | yes |
| 2024-2025 | yes (FantasyCalc) | yes | yes | yes |
| 2026 | - (only a 10/02 mid-season capture exists) | yes | - | yes |
