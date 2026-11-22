# Champions League — code notes

Rules and decisions live in the planning repo (`todo/todo-champions-league.md`, build plan
`todo/todo-champions-league-build.md`). This file covers the code only.

| Piece | File |
|---|---|
| Settings (own file — special events never go in `league.json`) | `config/champions_league.json` |
| Fixed 33-position schedule (16 weeks × 11 pods; every pair meets once) | `data/champions_league/schedule.csv` |
| Locked field for a season (seed, slot, route, ranks, OwnerID at lock) | `data/champions_league/field_<season>.csv` |
| Teams removed by the ownership check | `data/champions_league/excluded_<season>.csv` |
| Engine: selection, tiebreaks, pod scoring, standings, Triad Cup, projection | `scripts/champions_league.py` |
| Page shells (Standings, Schedule, Scoreboard, Field, Selection, Rules) | `scripts/champions_league_page.py` → `reports/cl-*.html` |
| Page script | `reports/assets/champions-league.js` |
| Page data | `data/scoreboard/<season>/champions-league.json` |

## Running
- Weekly job: `champions_league.py` (every season in `seasons` + `dev_seasons` that has a field file), then
  `champions_league_page.py`.
- After a season ends: `python3 scripts/champions_league.py --lock <season>` writes next season's field
  (refuses to overwrite; `--force` rebuilds). Review the printed tiebreak log; record any real coin toss in
  `tiebreak.coin_toss_results`.
- Before week 1: `python3 scripts/champions_league.py --verify-owners <season>` replaces teams whose
  owner changed since the lock (re-seeds before `schedule_publish_date`, else the newcomer takes the open seed).
  It refuses once week 1 has started.

## Notes
- Team identity = (LeagueName, RosterID); names are labels (`team_names.season_name`).
- Scores: `_postseason_common.week_points` (standard from 2026, official before). Best ball: Sleeper official
  max points (`MaxPoints_Season.csv`, or the history backfill via `poll_bots.history_extra`).
- Measure ranks share the best rank on equal values (`rank(method="min")`); the field and every tie group are
  ordered by `Ties.rank_order` / `Ties.order` (multi-team rule: beats-all wins, loses-all drops and the rest
  restart, else next step).
- Hidden-dev: `config/nav.json` (`rows.special` item + `rows.champions-league`).
- Not built yet: live pod scoring on the Scoreboard page (shows final weeks only) and the Triad Cup live view.
