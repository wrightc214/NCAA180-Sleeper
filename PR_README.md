# Dwight Fight 2026 — reviewer/build handoff (delete at merge)

**PR:** #123 · branch `feature/dwight-fight-2026` → `main` · **Chris merges, not the developer**.
**Deployment requirement:** Merge before the Tuesday 2026-11-24 weekly update, the intended first production pull. **Nav remains `hidden-dev`** until separately approved.

## Design and data contract

- `config/league.json → postseason.dwight_fight` contains the single comma-separated `dwights` string, `last_week: 17`, `from_season: 2026`, name, logo paths and explanatory `_note` keys.
- `scripts/dwight_fight.py` initially does nothing while the real regular season is unfinished. From the first complete weekly run it resolves Sleeper usernames to stable user IDs and season rosters, ranks them through `_postseason_common.rank_ties` / `tiebreak.py`, writes a fixed top-seed-bye bracket, and labels it initial.
- At or after Sleeper's first start-week rollover, the list is resolved again; an unchanged set of IDs is locked with no redraw; a changed set redraws before locking. A stale username can be recovered using its saved ID. Errors prevent locking, emit log warnings and appear on the page. Once locked, names in the configuration do not affect the saved bracket—even if the list is cleared.
- Bracket sizing: next power of two, 2–32 entrants, fixed pairings, no reseeding. Weeks end at week 17; 5–8 entrants start week 15, 9–16 in week 14 and 17–32 in week 13. Standard-scoring points use `_postseason_common.week_points` / `ScoresStandard_Season.csv`. Ties use the same week's `MaxPoints_Season.csv:MaxPoints` **on Sleeper official scoring** because per-player standard max PF is not stored, then lower seed number.
- Once a completed week is frozen the winner is never changed. Later score corrections update displayed scores while original `snapshot_*` scores and advancement remain fixed; `Sleeper differs` is marked in the UI and history notes.
- Saves `data/scoreboard/<season>/dwight.json` and rewrites only the current season in `data/Dwight_Historic.csv`; prior years are untouched by the running script. Includes 2021 verified historical rows and the requested 2022 status change.
- The Special Events page generator now writes `reports/dwight-fight.html` in addition to the unchanged Guillotine shell. `reports/assets/dwight-fight.js` displays the full bracket, recorded historical rounds, champion and HTML plaque overlay. Bracket scores use the weekly run (live in-browser scores are intentionally deferred). Trophy plaque uses image fractions left 24.6%, top 82.5%, width 50.6%, height 11.1%, with autosizing lettering.
- Original art blobs were copied from the existing `dwight-fight` branch without modifying the images. The Beet logo is not included. Navigation is a hidden-dev sub-tab from `config/nav.json → rows.special`.
- `update-leagues.yml` executes `dwight_fight.py` directly after `guillotine.py` and before `special_page.py`; manual selector also accepts `dwight_fight`.

## Validation and reproducible commands

```bash
python3 -m pytest -q tests
node --test tests/*.test.js
python3 scripts/menu_build.py
git diff --exit-code -- reports/assets/menu.js
python3 scripts/special_page.py
git diff --exit-code -- reports/special.html reports/dwight-fight.html
python3 scripts/dwight_fight.py --replay-2023 --out-dir /tmp/dwight-2023-replay
python3 scripts/dwight_fight.py --year 2026 --sample-count 11 --out-dir /tmp/dwight-2026-sample
```

The PR validation workflow executes Python and JS tests, relevant browser smoke checks, the 2023 replay, 2026 offline sample bracket and generated-page check. The **2023 fixture contains only recorded matches**: the replay reconstructs 11 seeds, byes, every pairing and winner using historical CSV scores, and checks Arizona State defeats Minnesota. It is a consistency replay of the recorded results, **not an independent Sleeper score audit**.

The sample flag uses actual 2026 owner IDs and regular-season standings without contacting Sleeper, writes an isolated JSON and verifies it is **not locked**. This never publishes or changes production.

## Reviewer checklist / unresolved

- [ ] PR CI is green including new replay/sample tests.
- [ ] Verify `menu_build.py` from final branch regenerates the committed `menu.js` with no diff. If another PR changes nav or accessibility, regenerate only from the merged sources; do not manually edit the compiled bundle.
- [ ] Inspect the Dwight page in dev view at widths 320, 390 and 1280, in light and dark, and confirm no horizontal overflow.
- [ ] Confirm the blank trophy art/text fit including long school names.
- [ ] After Chris sets `dwights`, verify that each supplied account resolves to exactly the intended roster and that no initial bracket locks ahead of the first start-week run.
- [ ] Confirm prior-season archive order and 2021–2023 champion display with Chris.
- [ ] Check the site links to its data directory correctly when hosted under GitHub Pages.
- [ ] Remove this PR_README at merge, after reviewer notes are transferred to the PR description.

## Caveats

- No live-in-browser scoring, push/Discord or image export in this PR.
- Historic 2023 replay reconstructs the archived brackets from CSV scores rather than independently reconciling every fixture to Sleeper API records; this limitation is intentional and disclosed.
- A locked bracket is immutable with respect to participants and winners, but scores and visual labels can refresh.
