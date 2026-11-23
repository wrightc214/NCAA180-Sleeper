# Task 5.1: trophy display and plaque engraving (build notes, decisions, open questions)

Delete this file and `docs/reviews/5-1-trophies/` (the screenshots) when the PR is merged.

## What this PR adds

| Piece | File(s) |
|---|---|
| Trophy ledger: historic (frozen) | `data/Trophies_Historic.csv` (359 rows, built once by `python scripts/trophies.py --backfill`) |
| Trophy ledger: current season | `data/Trophies_Season.csv` (header only today: 2026 has no published postseason results yet) |
| Ledger builder, safety check, rollover, Python component, PNG helper | `scripts/trophies.py` |
| Config | `config/trophies.json` (`_note` on every key) |
| JS component (same output as Python) | `reports/assets/trophy.js` |
| Engraving font (Barlow, OFL) + width table | `assets/fonts/` (woff/woff2 400 + 700, `Barlow-OFL.txt`, `barlow-trophy-metrics.json`) |
| Pages | `scripts/postseason_page.py`, `scripts/bracket.py` (champion card), `scripts/special_page.py`, `reports/assets/dwight-fight.js`, `reports/assets/guillotine.js` |
| Save image fix | `reports/assets/snapshot.js`: lazy images in the hidden export frame are switched to eager, so they still load |
| Workflows | `update-leagues.yml` (new `trophies` and `trophies_allow_changes` steps), new `trophies-rollover.yml`, and `pr-check.yml` (a step for the trophy browser tests) |
| Tests | `tests/test_trophies.py` (27), `tests/test_trophies_browser.py` (4, opt-in Playwright), `tests/trophy.test.js` (5) |

No image is stored for any trophy. Every display draws the shared art and puts the plaque text on top as HTML from a ledger row. `engrave_png(row)` builds a `PIL.Image` in memory and never writes a file.

## How it works

- **Ledger columns:** `Season, EventType, Event, Round, Team, Conference, LeagueID, RosterID, ManagerUserID, ManagerName, ArtKey, Status, Source`.
  - EventTypes are `CCG`, `Bowl`, `PlayoffRound` (Elite 8 / Final Four on the host bowl), `NationalTitle`, `NIT`, `Guillotine` and `DwightFight`.
  - For a CCG, `Event` is "<Conference> Championship". For a bowl or playoff round, `Event` is the bowl name as played.
- **Team:** that season's name. The roster slot comes from `team_names.slot(year, name)`. Every one of the 359 rows resolved a slot.
- **Manager:** the roster's owner at the week of the game, taken from that season's matchup data (`Matchups_Historic`, the 2019–2020 backfill, or `Matchups_Season`). An `Orphan` owner gives a blank manager.
  - For the Dwight Fight, the manager is the champion's own `user_id` and `username` from `dwight.json`.
- **Weekly job:** `run trophies trophies.py all` runs after `dwight_fight`, before `special_page` and `postseason_page`.
  - It also runs inside the manual publish block (playoff_field, playoff_bracket, playoff_publish, bowls, bowls_publish, nit, nit_publish), before `postseason_page`. A published result therefore gets its trophy in the same run.
  - It only ever writes `Trophies_Season.csv`. A test also checks that no `trophies.py` call in the workflow uses `--backfill` or `--rollover`.
- **Safety check:** each trophy is keyed on (Season, EventType, Event, Round), and its holder is (Team, LeagueID, RosterID).
  - If a key disappears or its holder changes, the script keeps the old file, prints `DROPPED …` / `CHANGED …`, and exits 1. Only that step fails, and the run's existing "Fail run if any script failed" step reports it at the end.
  - Additions always pass.
  - Once the change has been checked, run the workflow with `script_to_run = trophies_allow_changes`.
  - A team rename after a trophy row exists also trips the check (conservative on purpose).
- **Rollover:** run the *Trophy ledger rollover* workflow with the season.
  - It runs `trophies.py --rollover YEAR`, pushes branch `trophies-rollover-YEAR`, and opens a PR. It never commits to main.
  - If repo settings don't allow Actions to create PRs, the branch is still pushed and the job warns you to open the PR by hand.
  - After rollover, the weekly job skips any season already in the historic file.
  - If a new season starts before the rollover, the safety check trips and its message says to roll over first.
- **Component:** `trophy_html(event, winner, year, line2=None, …)` in Python and `NCAATrophy.html(event, winner, year, line2, opts)` in JS. `event` can be a ledger row or an EventType dict.
  - The plaque is positioned in percentages of the image. Font sizes are in `cqw` (container-query width), so the text scales with the trophy, stays crisp, and is selectable.
  - The `<img>` has a real alt, e.g. "2026 Big Sky Championship trophy, won by Montana State".
- **Auto-fit:** text sizes come from one character-width table generated from the vendored font. Python and JS read the same table, so they compute identical sizes (the test compares all 359 rows plus edge cases).
  - Widths are unkerned sums plus 3%, so they are always at least as wide as what the browser draws. The longest real name is checked against the real kerned font.
  - Sizes only shrink from a maximum. Text is never truncated and centred both ways.
  - The font is vendored and declared locally (`"Barlow Trophy"`), so the measurements hold even when Google Fonts doesn't load.
- **Missing art:** a plain plaque-style block shows the event's logo (approved bowl logos only) and the same two lines.
  - Python checks the file at build time. In JS, the `<img onerror>` swaps in the fallback that was rendered alongside it.
- **Adding art later** (e.g. `special/Triad Cup.png`): drop in the file and add one `events` entry. Rows with the new EventType start appearing once a builder writes them.

## Decisions to review

1. **Engraving look.** Line 1 is the team in Barlow 700. Line 2 is in Barlow 400, uppercase, with −0.02em tracking. This matches the Dwight Fight, so all trophies look like a set.
   - Ink colour is `#1b2340`; the Dwight Fight keeps its brown `#4a260d`.
   - The text in the DOM stays mixed case, e.g. "2026 Big Sky Champion". Only the display is uppercase, via CSS. Set `uppercase_line2: false` to turn that off.
2. **The Dwight Fight is unchanged in look.** It uses its own art (1254 px) with the old box as a config override (24.6 / 82.5 / 50.6 / 11.1 %), at 10 px per line on a 300 px trophy. The before/after screenshots are pixel-identical (see screenshots).
3. **The box in the prompt vs the real plaque.** 160/1200 is **13.33 %** tall, not 13.25 %. The code uses the measured plaque (left 23.33 %, top 76.16 %, width 53.33 %, height 13.33 %), rounded down so the text never leaves the plaque. A test samples every one of the 61 art files: inside the box is all `#CFD4D8`, and just outside each edge is not.
4. **Placement on the Postseason page.**
   - Each finished CCG, bowl, Elite 8 / Final Four game and the NIT final card has its trophy at the right of the game.
   - The trophy is 180 px wide on desktop and 26vw (~100 px) on phones. Below 400 px wide it drops under the scores, so that 320 px phones don't clip team names (checked: 0 clipped names at 320 and 390 on every season page).
   - The National Championship trophy is engraved on the bracket champion card (240 px on the page, 300 px in Save image). It also appears on the title game only when a season has no clean bracket.
5. **On phones the list engravings are small** (about 4–5 px text on a 100 px trophy). The information is still in the alt text and the selectable text, and it is crisp on the champion cards and in Save image. A tap-to-enlarge could be a follow-up.
6. **The Guillotine trophy** appears in the champion banner on Special Events once `guillotine.json` is `final`, one trophy per co-champion.
7. **Pages that draw in the browser** (Dwight Fight, Guillotine) read both ledger files. Until the weekly job has written the row, they fall back to the event's own final file, so the trophy shows as soon as the result is final.
8. **No trophy for a live or unplayed game.** Ledger rows exist only for Final results, and pages also check that the game is final.
9. **A font is now vendored** (`assets/fonts/`, about 85 KB, OFL licence included). It is not per-trophy art. It is what makes Python, JS and the PNG helper fit text identically.

## Ledger counts (historic)

| Season | CCG | Bowl | PlayoffRound | NationalTitle | NIT | DwightFight | Total |
|---|---|---|---|---|---|---|---|
| 2019 | 11 | 27 | 6 | 1 | 1 | 1 | 47 |
| 2020 | 15 | 30 | 6 | 1 | 1 | 0 | 53 |
| 2021 | 15 | 28 | 0 | 1 | 1 | 1 | 46 |
| 2022 | 15 | 26 | 6 | 1 | 1 | 1 | 50 |
| 2023 | 15 | 31 | 6 | 1 | 1 | 1 | 55 |
| 2024 | 15 | 30 | 6 | 1 | 1 | 1 | 54 |
| 2025 | 15 | 30 | 6 | 1 | 1 | 1 | 54 |

The Guillotine starts in 2026, so it has no history. 2025 spot check (tested): national champion Arizona State; Rose Bowl Final Four Arizona State, Sugar Bowl Final Four Montana; NIT champion Tuskegee; all 15 CCG winners match `Postseason_Historic.csv`.

## Gaps and data notes

- **2019:** only 11 CCGs (11 leagues that year). The American CCG (Ohio) has no art, so it uses the fallback.
- **2020:** the Southland CCG has no art (fallback). There is no Dwight Fight champion: the page lists "Finalist: Penn · champion unknown".
- **2021:** the playoff had no host bowls, so there are no Elite 8 / Final Four trophies. The national title still has its trophy.
- **Dwight Fight:**
  - 2019 Penn has `Status=Recorded`, taken from the Dwight Fight page's past-champions list; no bracket was recorded.
  - 2024 (New Mexico) and 2025 (Arizona State) have `Status=Reconstructed`: field = poll voters, event likely not held.
  - All three are kept as rows so the trophy rooms can decide what to show, filtering on `Status`.
- **Bowls without art (27 rows, all use the fallback):** Belk (2019–22), Duke's Mayonnaise (2022), Outback (2019–22), EA Sports (2019–22), Ice (2019–22), FedEx (2020–21), Geico (2020–21), PlayStation (2019–20), Xbox (2019–20).
- **Older or sponsored names mapped to today's art:**
  - Already in `league.json` `history_names`: Brooklyn→Gotham, Texas→Bluebonnet, Arizona→Copper, Birmingham→Vulcan, New Mexico→Zia, LA→Freedom, Miami Beach/Boca Raton→Palm.
  - Added in `trophies.json bowl_art`: Capital One→Citrus, TaxSlayer→Gator, Chick-fil-A→Peach.
- **Orphaned winners (blank manager, 11 rows):**
  - 2019: Capital One Bowl, Michigan State
  - 2020: Southland CCG Dixie State; Alamo Bowl Arizona; Belk Bowl Furman; Geico Bowl Rutgers; Independence Bowl UNC Charlotte; Liberty Bowl Georgia Tech; Music City Bowl Yale
  - 2021: Ivy CCG Yale; Idaho Potato Bowl Furman; Independence Bowl Grambling State
  - Caretakers: the data has no record of anyone running an orphan for a season, so none are credited. If a caretaker should be credited, add `ManagerName` in a hand-edit PR.

## Open questions for Chris

1. **Sponsored bowl names on plaques.** The no-sponsor rule says the engraving should not show them, so Capital One, TaxSlayer and Chick-fil-A engrave as Citrus, Gator and Peach. Belk, Duke's Mayonnaise, Outback, EA Sports, FedEx, Geico, Ice, PlayStation and Xbox still engrave as played, because I couldn't pick legacy names for them.
   - For each one, give the legacy name: one line in `bowl_labels` fixes the engraving, and one line in `bowl_art` fixes the art if a matching file exists.
2. **Reconstructed and pre-bracket Dwight Fight titles** (2019 Penn, 2024, 2025): keep them as trophies (the current rows) or drop them? Nothing displays historic Dwight trophies yet.
3. **Phone size for list trophies:** keep ~100 px beside the game, or show a smaller trophy icon with tap-to-enlarge?
4. **Rollover PR permission:** the rollover workflow needs "Allow GitHub Actions to create and approve pull requests" turned on in the repo settings. Without it, it pushes the branch and you open the PR yourself.

## Acceptance results

- `python3 -m pytest -q tests`: **341 passed, 34 skipped** (the 27 new ledger, config, geometry, fit, fallback, parity, PNG and page tests are included).
- `node --test tests/*.test.js`: **80 passed** (5 new).
- Browser tests (`RUN_SCOREBOARD_BROWSER_TESTS=1`): trophies 4/4; Dwight Fight, Guillotine, bracket, scoreboard postseason and CCG race all still pass.
- Crawl of all 120 generated pages under `reports/`: **360 trophies drawn, 0 broken trophy images**, and no plaque text overflow at 390 or 1280, light or dark.
- Save image of the champion card shows the engraving: `docs/reviews/5-1-trophies/save-image-champion-card.png`. The browser test also checks for ink inside the plaque.
- No new image file under `assets/` or `reports/` for any trophy won (tested).
- Screenshots are in `docs/reviews/5-1-trophies/`:
  - `postseason-2025-{390,1280}-{light,dark}.png`: champion card, Rose/Sugar Final Four, NIT, bowls, CCGs.
  - `special-{390,1280}-{light,dark}.png`: Guillotine and Dwight Fight.
  - The Guillotine and Dwight Fight screenshots use fixture data, because 2026 hasn't finished.
