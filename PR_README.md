# Dwight Fight 2026 reviewer handoff

PR #123 targets the Tuesday, November 24 weekly run, the first run after week 11 is final. Chris merges. The Special Events navigation stays `hidden-dev` until separately approved. Set the empty `postseason.dwight_fight.dwights` string to the intended comma-separated Sleeper usernames before that run.

## 2024 and 2025 reconstructed brackets

There is no record either event was held. It most likely was not, but that is uncertain. Chris reconstructed each season with its 11 poll-voter teams: Arizona State, Minnesota, Wisconsin, Montana, Louisiana Monroe, New Mexico, North Alabama, Eastern Washington, Nebraska, Wake Forest, and Stony Brook. Seeds use regular-season record, points for, and points against. The games span weeks 14–17 and use standard scores checked against Sleeper, stored in `data/ScoresStandard_Historic.csv`.

- **2024:** No. 8 New Mexico defeated Minnesota 143.36–141.48.
- **2025:** Arizona State defeated Nebraska 168.32–109.20.

The 20 records were appended as supplied. The page reads the bracket years and champions from the archive, keeps the 2019 Penn and 2020 finalist-only entries, and waits to show the live season in history until it has a champion. The archive labels reconstructed seasons, and those championships count toward title totals with an asterisk. Managers may not have set lineups for these events.

## Production bracket

There are 2–64 entrants and no reseeding. The final is always week 17. Fields of 33–64 occupy a 64-slot bracket and start in week 12. In a 33-team field, 31 top seeds get a first-round bye. Smaller fields start later. Week 18 is preserved only in the historical record and the 2023 replay.

After week 11 is final, the weekly pipeline draws from the configured Sleeper usernames and preserves the resolved stable IDs. It locks at or after the bracket's first week. A 33–64 entrant bracket may therefore draw and lock on the same run if Sleeper has already rolled to week 12. Invalid roster entries prevent locking. After lock, config changes cannot redraw the bracket. The same-week official max PF and then seed break a standard-score tie. Score corrections display a dagger and never change frozen advancement.

## Verification

- `python3 -m pytest -q tests` includes the 33-team bye count, 65-team rejection, history writer and both reconstructed replays. The replays derive seeds and scores from regular-season standings and standard-score files, then compare all 20 archived games. The 2023 replay is a CSV consistency check, not a separate Sleeper audit.
- `node --test tests/*.test.js`
- `RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_dwight_browser.py` checks the banner-only heading and no document overflow at 320, 390 and 1280 px, light and dark, plus labels, formatting, champions, totals and archive rollover.
- The 2026 isolated dry run uses stored roster/standings data. It writes an initial, unlocked sample and does not modify production or validate Chris's final configured field.
