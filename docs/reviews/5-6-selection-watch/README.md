# Selection Watch — Stage 2 board page: independent review guide

**PR #112 — developer implementation complete; independent audit and production approval outstanding.** Branch `feature/selection-watch-stage2` is rebased on `main` at `916c918`, including merged Transactions #111 and follow-up #113. Both tabs remain `hidden-dev`; this PR adds no public Discord posting. This README is temporary and should be removed at merge.

## Executive scope / frozen requirements

During 2026 CCG week, Week 11 has ended and the rankings are fixed. The 32-team playoff field is all 15 CCG winners (automatic) plus the best 17 non-winners by the shared REAL-TOSS tiebreak order (win %, points for, points against, then unresolved real coin toss). The browser enumerates **all 2^15 = 32,768 possible CCG outcomes**, weighting each by the existing Games win model. No Monte Carlo, no seeding or bowl/NIT logic.

The new prebuilt `reports/selection-watch.html` has five independently collapsible, image-exportable sections, in this order:

1. **Status**: Eastern-time refresh stamp, **Unofficial**, number of CCGs final, confirmed steals, additional projected steals and other possible steals. Historical/provisional previews are visibly labeled.
2. **Steal Board**: two-column thief / at-large-at-risk matchup, one row per CCG with a participant outside the natural top 32. A thief is **outside the natural top 32** and can qualify only by winning; an inside CCG team can still miss the field without becoming a thief. When both participants are outside, a steal is certain and the current leader represents the game. Rows show official team names, ranks, conference, athletics-color edges, light-background logos, scores, final/live state, the thief's win chance, the risk team's enumerated qualification chance and Games links. The dashed break separates currently winning thieves from trailing thieves. Default order: chance; optional sort: margin (closest trailing challenger first). The number of steals and the cut do not change with sorting.
3. **Bubble odds**: each currently at-risk, non-lock natural-field team's exact qualification chance and a brief number-of-steals explanation. Also identifies inside-vs-inside CCGs that might still affect the bubble.
4. **Locks**: unconditional locks, defined as qualifying in **every** outcome set, regardless of current CCG results.
5. **No-impact CCGs**: collapsed by default; includes only games where both participants are unconditional locks and neither participant is a thief.

The shared `--good`, `--bad` and `--neutral` semantic tokens are used for meaning, never hard-coded success/failure red and green. Team identities use their existing official school palette, not invented colors. Fixed white logo tiles use the normal/light variant; the live data builder calls `site_common.logo_html(team, bg="#ffffff")`.

The section image-export buttons use the existing `NCAASnap.save` utility. Each image carries an Unofficial timestamp and provisional status when applicable. Five sections have a Collapse all / Expand all control. The mobile board keeps two columns.

## Implementation and design decisions

- `scripts/selection_watch.py` **Stage 1 is still authoritative**. The only additions are `style` metadata and independent preview-only CLI output; no changes to its Python `field()`, `odds()`, `board()`, historical checks, regular-season gating or Discord alert behavior in normal runs.
- `reports/assets/selection-watch-core.js` contains pure `field`, `odds`, `board`, `sortedBoard` and `locks` functions. It has no DOM or network dependencies. This separation makes Stage 3 what-if and labels easy to attach.
- `reports/assets/selection-watch.js` reuses `scoreboard-core.js` and **`scoreboard-overview-model.js`** for live roster models and win probabilities, the same Sleeper / ESPN inputs, league scoring settings and CCG-week baseline as the Games page. No second probability model is introduced. An already-published Stage 1 final winner overrides the live model; all live CCG outcomes are refreshed in one atomic batch, retaining the last complete snapshot on a failed refresh. Refresh interval: 5 minutes when visible; manual Refresh is provided.
- Pre-CCG **provisional 2026** deliberately shows clearly labeled **50/50 placeholders**, not fabricated live player-based probabilities, because the Week 12 frozen baseline does not exist before the Nov 24 run. Provisional pairings have no Games links. The live route refuses provisional JSON. Before the live file is published, its 404 is shown as a plain availability message. **2025 historical** preview replays actual final scores and winners (0%/100%) without live Games requests. The page and image exports identify the CCG finals as a historical replay, without stamping the current date as the data date.
- The at-risk column is taken directly from Stage 1's `board()` semantics: reverse natural-field ranking excluding currently leading inside-32 CCG teams. The first out pairs with the highest-priority winning thief; the number of winning thieves, `k`, determines exactly which top-32 teams are eliminated. Sort only changes thief row order, never the independent risk list or `k`.
- Margin sorting puts winning thieves first (larger positive margin first), then trailing thieves (smaller deficit first). Default probability sort descends within each group. A both-outside pairing always consumes one thief row.
- For incomplete live odds, use a valid frozen pregame percentage from Games if available. Validate raw frozen values before conversion: null, blank, nonnumeric and out-of-range values are unavailable, but an explicit 0% or 100% is valid. With no usable value, the whole refresh fails. The first load does not render or export an unverified board; later failures keep the last verified board and timestamp and show a stale-data warning. For final tied CCGs, use the better-ranked side under the existing CCG rule unless the underlying ranking tie is unresolved; no hidden coin toss.
- Locks use a 50/50 outcome distribution over all 15 games, not odds conditioned on completed games. A team with probability 1 under this distribution is in under every combination. Results are cached across refreshes and sort toggles.
- Selection style metadata uses the existing `Colors - Teams.csv`, shared `team_colors`, and shared logo helper. The admitted side of each Steal Board pair uses the team fill and whichever of black or white yields readable contrast. The dimmed side is unchanged. Missing logos are hidden rather than replaced with invented artwork.
- The two Dev-only tabs are declared in `config/nav.json`. `python scripts/menu_build.py` reproduced main’s bundle byte for byte from its report filename inventory, then rebuilt it with both tabs; a second build produced identical output. Re-run the menu build against a complete checkout in CI. The static page was regenerated with `python scripts/selection_watch_page.py`.

### Owner settings and template-repo follow-up

- Selection Watch uses `config/league.json` → `brand` for the generated title and heading, and reads it again in the browser for the displayed title, heading, and image branding. The live board uses `refresh.normal_ms` for automatic refresh. If the interval is absent or invalid, manual refresh is still available. Static previews do not poll.
- Feature-specific settings live in `config/SelectionWatch.json`. The first key, `enabled`, defaults to on. Set it to false and rerun `python scripts/menu_build.py` to remove the tab, including from Dev view. The direct URL stops before fetching either live or preview data. The publisher leaves existing live and preview files untouched while disabled. Stage 1 private tie alerts and manual rule checks still run independently. Preview controls do not make committed fixtures private. Section headings stay in the page UI, and required disclosures remain fixed.

| Key in `config/SelectionWatch.json` | Checked-in value | Missing-key default |
| --- | --- | --- |
| `enabled` | `true` | `true` |
| `labels.title` | Selection Watch | Selection Watch |
| `export_filename_prefix` | `ncaa180-selection-watch` | `ncaa180-selection-watch` |
| `availability_message` | Available after the regular season is final (Tue Nov 24). | Available after the regular season is final. |
| `previews.historical.enabled` | `true` | `false` |
| `previews.historical.query` | `2025` | Unset (no route) |
| `previews.historical.url` | `postseason/selection-watch-2025.json` | Unset (no fixture request) |
| `previews.provisional.enabled` | `true` | `false` |
| `previews.provisional.query` | `provisional` | Unset (no route) |
| `previews.provisional.url` | `postseason/selection-watch-provisional-2026.json` | Unset (no fixture request) |

An absent shared `brand` key defaults to NCAA 180 in the generator. At runtime the browser falls back to the brand and feature name baked into the HTML. Missing preview settings never fall through to the live feed for a preview URL.

- Field size and CCG week already come from `postseason.playoff.field_size` and `schedule.ccg_week`. This engine assumes one automatic bid per CCG winner, the remaining spots go to ranked non-winners, and a tied CCG goes to the better-ranked side unless the ranking tie remains unresolved. It is not a general interpreter for alternative automatic-bid or tied-game settings.
- **Resolve this during the template-repo phase.** Decide which postseason formats the template will support, then make the selection engine honor those shared rules or explicitly reject unsupported combinations. Add cross-language coverage for supported configurations before exposing those settings to template owners. This PR preserves the NCAA 180 rules.

## Exact enumeration parity

`field(d, winners)` seeds automatic winners, removes them from ranked order, then assigns `field_size - ccg.length` remaining spots. Consecutive tied groups with an unresolved real coin toss share any places left at the boundary, producing fractional shares (two tied teams competing for the final remaining spot receive 0.5 each). `odds(d,p)` loops through each outcome bit mask, multiplies the CCG probabilities (`p[game.id]` = probability side A wins, 0–1; default .5), obtains field shares for that outcome, and accumulates weighted shares. This matches Python Stage 1's `field()` and `odds()` algorithms. In particular, it never assumes the 32nd team qualifies automatically in the presence of a steal.

`tests/test_selection_watch_js_parity.py` invokes Node's exported pure engine and Python's reference on *identical* 2024 and 2025 inputs, including nondegenerate probabilities for every CCG and an exact synthetic tie at the cutoff. It also checks every historical thief row/cut and both frozen final fields. The three committed parity cases passed with native Python and Node during pre-review validation.

## Historical acceptance — independently exercised with a JavaScript runtime

The two seasons were reconstructed from historical standings, historical team-name mappings and recorded CCG/Playoff results, ranked by the exact shared numeric tiebreak order. The field/board checks ran in an isolated JavaScript runtime, then both seasons passed native Python/Node parity and the authoritative Python `--check` against actual playoff participants.

### 2024: 5 thief rows; 3 steals; cut after #27; actual field 32/32
Margin order, with at-risk partner and observed outcome:

| Thief | At-large counterpart | Outcome |
| --- | --- | --- |
| Jackson State #88 | Memphis #31 | **Stolen / out** |
| UAB #52 | Arizona State #30 | **Stolen / out** |
| Eastern Kentucky #50 | UTEP #28 | **Stolen / out** — Eastern Kentucky–Chattanooga both outside |
| North Carolina #46 | Minnesota #27 | Held / in |
| LSU #53 | Purdue #26 | Held / in |

The natural top-32 teams which **did not win** their CCG: **20 = 17 + 3**. Independent JavaScript field versus actual 2024 first-round participants: **32/32 match**.

### 2025: 6 thief rows; 2 steals; cut after #29; actual field 32/32
Margin order:

| Thief | At-large counterpart | Outcome |
| --- | --- | --- |
| Kansas State #75 | UNLV #31 | **Stolen / out** |
| Nevada #35 | Youngstown State #30 | **Stolen / out** |
| UTEP #42 | Columbia #29 | Held / in |
| Monmouth #67 | North Carolina A&T #28 | Held / in |
| North Texas #38 | LSU #27 | Held / in |
| Ohio State #45 | Alcorn State #24 | Held / in |

The natural top-32 teams which **did not win** their CCG: **19 = 17 + 2**. Independent JavaScript field versus actual 2025 first-round participants: **32/32 match**. The committed 2025 preview JSON also reproduces the above six rows and the actual 32-team field. It contains 180 teams and 15 finished CCGs.

## Preview production and viewing — exact commands

From repository root, in a complete local checkout:

```sh
# Recreate the 2025 historical preview from Stage 1 (does not touch live JSON):
python scripts/selection_watch.py --year 2025 --output reports/postseason/selection-watch-2025.json

# Regenerate the explicitly provisional 2026 preview from the CURRENT regular standings:
python scripts/selection_watch.py --year 2026 --provisional --output reports/postseason/selection-watch-provisional-2026.json

# Regenerate the static page and the hidden-dev menu from their authoritative sources:
python scripts/selection_watch_page.py
python scripts/menu_build.py

# Locally serve the repo (do not double-click a file:// URL: fetch() needs HTTP):
python -m http.server 8000
```

Open:

- `http://localhost:8000/reports/selection-watch.html?preview=2025`
- `http://localhost:8000/reports/selection-watch.html?preview=provisional`
- After real 2026 data exists: `http://localhost:8000/reports/selection-watch.html`

The preview JSON files are both committed separately at `reports/postseason/`. Neither uses `reports/postseason/selection-watch.json`. The provisional file explicitly contains `"provisional": true`, and the live page rejects such a file.

**The 2025 committed fixture was independently reconstructed from existing historical CSVs and validated 32/32. Run the authoritative CLI above as an additional build verification; it may update generated timestamps, approved name abbreviations and style metadata, so review diff rather than mechanically committing timestamp churn.** The provisional fixture is a Nov 17/18 standing snapshot, not the final regular season.

## Test inventory and execution record

Written:
- `tests/selection_watch_core.test.js` — **10** Node unit cases: field rule, both-outside CCG, inside CCG team that can miss, exact odds, fractional tie, unconditional locks, sort cut invariance, trailing-margin order, 2025 real board acceptance.
- `tests/selection_watch_live.test.js` — **9 Node regression cases** for odds, refresh, team fill, config-driven presentation, preview isolation and disclosures, the off switch, and the unpublished live page.
- `tests/test_selection_watch_js_parity.py` — **3 parameterized cases** (2024, 2025, synthetic tie), full JS/Python reference comparison.
- `tests/test_selection_watch_page.py` — **5 cases** for page shell, preview fixtures, generator fallbacks, compiled menu behavior and paused data publication.
- `tests/test_selection_watch_browser.py` — **2 opt-in browser methods**: four preview/viewport combinations (2025 and provisional × desktop/mobile), checking status, counts, cut, sort, folds and overflow; plus one fully mocked Week 12 live refresh across 15 conferences that exercises the existing Games data model without external requests. The live browser case covers a missing first-load input, recovery, and preservation of the verified board when the frozen odds subsequently go blank.

Actually executed in this environment:
- **19/19 native Node tests passed** (10 core plus 9 page-controller regression tests).
- **Eight targeted Python test cases passed via a standalone runner** (five page/menu/publisher cases and three Python/Node parity cases). This workspace did not have pytest available.
- The authoritative `selection_watch.py --year YEAR --check` returned **32/32 matches** for both 2024 and 2025.
- **2024 and 2025 historical field and board validation passed** using the same JS core: 32/32 for each, row/count checks and 20/19 nonwinning top-32 teams.
- **JavaScript syntax compilation passed** for client and engine.
- The generated page and menu are committed. The base menu reproduced byte for byte before reconciliation, and the resulting bundle reproduced byte for byte on a second build from the same report filename inventory.

**Still open:** full repository-wide Python and Node suites, Playwright preview and mocked live checks, a visual PNG export check, and a real 2026 Week 12 end-to-end refresh. Chromium startup was attempted and failed because socket creation was denied in this environment. Targeted tests used a subset of files from the branch; run the full suites and asset rebuilds from a complete checkout.

Suggested validation commands:

```sh
python3 -m pytest -q tests
for test in tests/*.test.js; do node --test "$test" || exit 1; done
RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_selection_watch_browser.py
python scripts/selection_watch.py --year 2024 --check
python scripts/selection_watch.py --year 2025 --check
```

Browser test notes: when `RUN_SCOREBOARD_BROWSER_TESTS=1`, install Playwright and Chromium first. The previews intentionally make no Sleeper/ESPN calls. The mocked Week 12 integration test intercepts those requests and is ready to run in Chromium. Also use **Save image** on the provisional Steal Board and inspect the PNG for the cut line, Eastern timestamp, and PROVISIONAL / UNOFFICIAL labels. Real Week 12 feeds can only be exercised after Nov 24.

## Files modified / PR overlap

| File | Purpose |
| --- | --- |
| `scripts/selection_watch.py` | Additional style metadata, explicit isolated output and provisional preview generation |
| `scripts/selection_watch_page.py` | New authoritative prebuilt HTML page generator |
| `reports/selection-watch.html` | Generated static page |
| `reports/assets/selection-watch-core.js` | Pure rule/odds/board engine |
| `reports/assets/selection-watch.js` | Live refresh, rendering, sorts and image export |
| `reports/postseason/selection-watch-2025.json` | Unlisted real 2025 preview |
| `reports/postseason/selection-watch-provisional-2026.json` | Unlisted provisional 2026 preview |
| `config/nav.json` | Selection Watch entry, Dev-only alongside Transactions |
| `config/SelectionWatch.json` | Page master switch, feature labeling, export and preview settings |
| `scripts/league_config.py`, `scripts/site_common.py` | Load the feature settings and omit the tab when disabled |
| `reports/assets/menu.js` | Regenerated shared menu asset |
| `tests/selection_watch_core.test.js` | 10 Node tests |
| `tests/test_selection_watch_js_parity.py` | JS/Python equality and historical board |
| `tests/selection_watch_live.test.js` | Missing-odds and refresh-state regressions |
| `tests/test_selection_watch_page.py` | Page/build preview contracts |
| `tests/test_selection_watch_browser.py` | Opt-in preview browser checks |
| This README | Temporary auditor guide |

Transactions #111 and #113 are already in the rebased main. Preserve both Dev-only tabs. If Accessibility #109 changes the menu after this base, rebuild again from the final `config/nav.json` and `templates/menu.js` without overwriting its tokens.

## Risks, remaining independent validation and owner decisions

1. **Live correctness before Nov 24 cannot be confirmed**: the Week 12 frozen Games baseline, actual CCG pairings and player results do not exist yet. Before launch, verify 15 distinct CCGs, 180 ranked teams, valid matching keys, complete Games projections, scores, and win chances.
2. Full browser visual/screenshot testing is outstanding; a network-free mocked Week 12 browser test is written but unexecuted. Check 390px and desktop, light/dark themes, contrast/tokens, full exported PNGs and mobile scroll overflow. Validate no save-image clipping and fixed-white logo selection.
3. Historical/replay ranks and counts and the synthetic cutoff tie passed native Python/Node parity. The browser and real-feed paths remain unverified; reviewers should pay particular attention to final-tied games.
4. The two preview JSONs are static snapshots, not automatically updated by live-refresh. Regenerate the provisional fixture if standings change and preview is needed before Nov 24. No need to regenerate the page for live data once merged.
5. Owner approval is required to change `hidden-dev` to visible. Do not expose nav or publish public/Discord images before approval.

## Tuesday Nov 24 launch checklist

1. Confirm Week 11 is completely final and the weekly GitHub Actions run builds CCG pairings first, then `selection_watch.py` (already ordered in `.github/workflows/update-leagues.yml`).
2. Check `reports/postseason/selection-watch.json` exists **without** `provisional`, with exactly 180 `order` entries, 15 `ccg` entries, valid IDs, real-toss `tie` data, official school color/logo metadata and timestamp.
3. Verify `reports/selection-watch.html` loads the real file **without** `?preview=` and that the scoreboard 2026 Week 12 baseline is available.
4. Compare at least one live CCG matchup's score and win chance to the Games page on Thu Nov 26, and check the cut remains stable when sorting. Ensure final CCG results resolve 0/100 probabilities.
5. Check mobile + dark mode + saved-image timestamps; ask owner to approve menu visibility independently. No Discord or public posting is part of this PR.

**Stage 3 deferred:** live Steal/Possible/No-impact → Stolen/Held labels, on-screen WHAT-IF picks and saved-image banner, a COIN TOSS visual row. **Stage 4 deferred:** five-point bubble timelines, additional Thanksgiving/Black Friday refresh slots, and Discord card. Their data hooks can use the pure JS core and the existing client refresh.
