# CCG Race — reviewer audit / project-manager handoff (temporary; keep until merge)

## Scope and release controls
- PR targets `main`; **do not merge** before independent review.
- New Selection Watch sub-row: **CCG** then **Playoffs**.
- Both sub-items and the Selection Watch parent start **hidden-dev**; page is public by direct URL (dev-hidden is not security).
- CCG race runs **only** during `schedule.ccg_week - 1` (2026 Week 11); no CCG-week or early-season processing.
- Current-season-only build. Historical season selector is deliberately postponed.

## What changed
- `scripts/ccg_race.py` produces an entering-week contender snapshot using `_postseason_common.standings`, current schedule and the existing exhaustive `postseason_odds._Conf` machinery (`MAX_ENUM=20`).
- `reports/postseason/ccg-race-2026.json` is committed from the current standard-scoring inputs so the page is immediately reviewable.
- `reports/assets/ccg-race-model.js` performs 20,000 seeded browser simulations per conference using scoreboard-provided score distributions.
- `reports/assets/ccg-race.js` reuses the Games page's ESPN/Sleeper endpoints, four-conference concurrency, frozen Tuesday baseline, and `ScoreboardOverview.summarize` / `ScoreboardCore.teamModel`.
- `reports/ccg-race.html` displays 15 conferences, division 1 left / division 2 right, responsive cards, logos/colors, status, timestamp and live percentages.
- Navigation sources: `config/nav.json`, `templates/menu.js`, compiled `reports/assets/menu.js`; Playoffs page only receives the new row placeholder.
- `config/selection_watch.json` owner-tunable `ccg` block; workflow `.github/workflows/update-leagues.yml` calls generator after standings.
- `reports/postseason/ccg-race-preview-2026.json` provides an offline `?preview=midweek` with pre-week clinched divisions, live divisions and a Pac-12 South division clinched during Week 11. Preview avoids live NFL endpoints.

## Configuration and model assumptions
- Standard scoring from 2026 via shared standings and Games baseline, never Sleeper's official standings.
- Tuesday pregame mean is frozen; pregame per-team standard deviation is `config/league.json:spread` (24). In-progress mean/variance comes from the scoreboard. Final scores have variance 0.
- Normal score draws are independent across teams. Sampled scores are rounded to hundredths, and games tied at 0.01 are draws (each receives one tie).
- Division tiebreak order is loaded from `config/league.json`: win_pct, points_for, points_against, coin_toss. A pending real coin toss is **not simulated or pre-decided**. Each tied team gets 1/n of that draw's championship probability.
- Mathematical Clinched/Out is distinct from Monte Carlo display bounds: no label is inferred from a sampled 0% or 100%. Before all games finish, the proof uses conservative floor/ceiling bounds, so it can delay a mathematically clinched label but must not declare one early.
- League short names and team display come from existing shared data; player live projections use Games scoring code.
- No 2027 multiple-week extension is included.

## Commands and tests
```sh
python scripts/ccg_race.py --year 2026
python -m unittest tests/test_ccg_race.py
node tests/ccg-race-model.test.js
python scripts/menu_build.py
git diff --exit-code -- reports/assets/menu.js
```

On the current Week 10 snapshot, expect **30 divisions: 18 live + 12 pre-clinched**. Confirm:
Big Sky Colonies—William & Mary; Big Sky Frontier—Youngstown State;
Big Ten West—Iowa; Ohio Valley Yankee—Monmouth; Mountain West Sin—BYU;
USA Twister—Middle Tennessee State; Ivy Smart—Cornell; Pioneer Patriot—UT Martin;
Sun Belt Bible—Southern Miss; ACC Coastal—Georgia Tech;
Pac-12 North—Washington State; SEC East—Kentucky.
Pac-12 South entering Week 11: Colorado 9-1, UCLA 8-2, Arizona State 8-2.

### Browser verification
Serve repo root via `python -m http.server 8000`; open
`http://localhost:8000/reports/ccg-race.html?preview=midweek`.
Turn on Dev view first to verify tab/row behavior. Inspect all 15 conference cards;
confirm Pac-12 North preclinched, Pac-12 South final-with-dimmed-Out competitors,
and a competitive division elsewhere. Exercise collapse all, section images, mobile
stacking, label and timestamp in PNG.
Then visit `reports/ccg-race.html` in active Week 11 to inspect ESPN/Sleeper live feeds.
Verify page stops refreshing once games are final; no requests outside configured week.
Inspect the selection-watch.html navigation and parent-tab destination with Dev view
on and off, and after locally simulating the owner changing CCG to visible while
Playoffs remains hidden-dev. Leave actual config hidden-dev on PR.

### Review/validation status
- Current conference/contender data was cross-checked against source CSVs and verified to be **18/12**; the twelve named clinches and Pac-12 South records matched.
- New JS source was syntax-parsed and the deterministic simulation was smoke-tested in an isolated JS runtime, including all 15 fixture conferences.
- **PR CI validation succeeded** in GitHub Actions run #44769915555: committed-menu regeneration/diff, accessibility generation, all Python and JS tests, CCG preview browser acceptance (desktop light/mobile dark), existing transaction, Dwight Fight and Selection Watch browser tests. The preview acceptance generated two full-page screenshots in the CI artifact `transactions-preview` (`work/ccg-race-preview/desktop.png` and `mobile.png`).
- **Still requires human reviewer verification:** inspect CI screenshots and PNG export behavior, confirm actual live Sleeper/ESPN updates and data freshness during Week 11, and review UI/colors on representative devices. These are not proven by the offline fixture.
- Current source uses the existing weekly workflow's update; production activation/publication must be managed separately from the PR. No automatic public-state change is included.

## Risks and reviewer focus
1. Verify `ccg_race.py` reproduces the committed snapshot byte-for-byte except timestamp, ordering of equivalent data, and whitespace; investigate any standard-scoring difference.
2. Review the scoreboard live feed across late player injury/status transitions; page intentionally retains last verified results on incomplete data.
3. A conference can remain unproven after a mathematical clinch until every applicable point-for possibility is resolved; this is conservative by design.
4. Check any simultaneous menu/nav PR merge against regenerated `menu.js`; do not hand-edit the bundle.
5. The short name for USA/CUSA comes from `LeagueShortNames.csv`; follow source naming rather than hard-code a historic label.

## Project manager handoff — next season (NOT in this PR)
In 2027, consider extending the active window from **`ccg_week - 1` to `ccg_week - 3 .. ccg_week - 1`**.
Regenerate mathematical contenders after each completed regular-season week, dropping
eliminated teams from the following week's published list, while preserving each
week's entering contenders until its live games finish so newly eliminated teams
display **Out**. Store immutable per-week snapshots for week-over-week race changes.
This requires adapting the JS model to sample multiple games per team/week (not
reusing one team score draw across different weeks) and reviewing the data-publishing
cadence. Do not implement or turn on in 2026 without explicit approval.
