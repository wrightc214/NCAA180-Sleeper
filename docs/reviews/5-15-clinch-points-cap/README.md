# 5.15 Points-for cap for Clinched / Out — build notes (delete at merge)

## Rule (Chris, 2026-11-23)
`cap = max(points_per_minute × player-minutes left, burst_per_player × starters still to play)`, with `0.45` and `18` in `config/league.json` → `postseason.clinch`.
- On a tie in wins, the points-for tiebreak is **settled** when one team's floor beats the other's ceiling. The floor is points so far; the ceiling is points so far + cap.
- A settled tie counts like any decided outcome, for Clinched and for Out. Points against is never capped.
- With both values 0 or missing, the old rule applies: every points-for tie stays unknown. This is tested.

## Where it applies
| Place | How |
|---|---|
| `scripts/clinch_cap.py` (new) | settings, `points_cap`, `week_cap`, `starter_slots(year)`, page-note sentence |
| `scripts/postseason_odds.py` proofs | `_Conf` gets an optional points-for floor and ceiling. `ccg`, `most_ahead` and `fewest_ahead` settle ties on wins when the floor beats the ceiling. CCG, Playoff, Bowl/NIT/Natty flags all flow from these. Cross-conference caches key on the set of settled teams. |
| `scripts/ccg_race.py` | Contenders entering the week use the same rule (`alive_members(..., points_for, caps)`). |
| `reports/assets/ccg-race-model.js` | `pointsCap`, `weekCap`, `proveDivision`. Exact enumeration of open games involving contenders (≤16), live minutes and starters left per team. |
| `reports/assets/ccg-race.js` | Models carry `minutes_left` / `players_left`; `clinchOptions` comes from config. Page note sentence comes from config. |
| Page notes | Bowl projection (two notes) and Standings via `clinch_cap.note()`; CCG race via JS. |

**Full week still to play:** every starter slot × 60 minutes. Slots come from `data/LeagueIDs_AllYears.csv` `RosterPositions` without BN/IR/TAXI/RES; 2026 is 11 for all 15 leagues, so one week = max(297, 198) = **297**.

**Live minutes and starters:**
- A starter in a live game counts as a player left even at 0 minutes. Overtime reads as 0 minutes in `remaining()`, but he can still score.
- A starter with no game data (`unknown`) counts as a full 60 minutes.
- Bye, inactive and finished starters count 0.

## Calls made
- **JS proof is exact enumeration (when the cap is on):** like Python, not the old per-team win bounds, so Python and JS agree on the same inputs. With the cap off, the old JS code path runs unchanged.
- **JS Out with the cap on:** no longer waits for the team's own game to be final. A proven Out mid-game is still a proof.
- **Not regenerated here:** generated pages (`postseason.html`, `standings.html`) and `reports/postseason/*.json`. Tuesday's weekly run (Nov 24) rebuilds them with the new notes and flags. `ccg-race-2026.json` (published Nov 17) is not rewritten: the generator never overwrites after the week, and the live page applies the cap itself.
- **Selection Watch locks:** not changed. They run after the regular season, when points for is final.
- **Guillotine, Champions League, Dwight Fight:** have no Clinched/Out proofs.

## Replay at 0.45 / 18
**Week 10 final** (repo data; `postseason_odds.proofs`; also pinned in `tests/test_clinch_cap.py`):
| Team | Conference / division | Record, PF | Gap to the leader | Change |
|---|---|---|---|---|
| Montana | Wild Plains | 6-4, 1560.66 | — | CCG clinched |
| Wichita State | Wild Plains | 5-5, 1190.00 | 371 | CCG / Playoff / Natty out |
| South Dakota | Wild Plains | 5-5, 1236.46 | 324 | CCG / Playoff / Natty out |
| Howard | HBCU Hurricane | 6-4, 1166.42 | 311 (vs NC A&T) | CCG / Playoff / Natty out |

Gaps under 297 stay unknown: Delaware State 266, West Virginia 258, Texas A&M 236, Davidson 209, UCLA 189. CCG race contenders: 18 live / 12 clinched → 17 / 13.

**Week 11 live** (Mon Nov 23 ~11 AM ET, Sunday final, MNF pending). This is the branch JS run on live Sleeper data in the browser; the published page showed these as >99% / <1%:
- **Clinched:** Clemson (ACC), Baylor (Big 12), Campbell (Pioneer), Montana and Old Dominion (Wild).
- **Out:** NC State, Texas A&M, West Virginia, UConn, UCLA, Davidson, South Dakota, Wichita State, UNC Charlotte.
- **Example:** NC State is 8-2, PF 1603.00, with no starters left. Clemson's floor of 1738.90 beats that, so a tie at 9 can't go to NC State.

## Tests
- `python3 -m pytest -q tests` → 325 passed, 34 skipped. New: `tests/test_clinch_cap.py`.
  - Cap curve examples; config and note; off when missing; 11 slots.
  - The shared fixture.
  - Off equals the old rule on real data.
  - The week-10 replay diff.
  - Contenders inside/outside the cap.
- `tests/test_ccg_race.py`: the snapshot test now runs with the cap off (the snapshot predates the cap). A new test pins the capped result: Wild Plains = Montana; HBCU Hurricane drops Howard; Pac-12 South unchanged; 13 clinched.
- `node tests/clinch-cap.test.js` (new) runs the same 6 fixture cases as Python (`tests/fixtures/clinch-cap-cases.json`), including kickoff open → late clinched as the chaser's players finish. All `node tests/*.test.js` pass.
- `RUN_SCOREBOARD_BROWSER_TESTS=1 pytest tests/test_ccg_race_browser.py tests/test_selection_watch_page.py tests/test_menu_browser.py` → 13 passed.

## Open for Chris (5.15.2)
Tune `points_per_minute` / `burst_per_player` after looking at the replay. Today only gaps over 297 for a full week flip.
