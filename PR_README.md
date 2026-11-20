# PR README: task 5.14, logo clash quick fix (`logos.force`)

Delete this file and `pr-assets/` at merge.

## What changed
A new top-level `logos.force` in `config/league.json` maps each team to a file under `assets/logos/teams/`. Wherever a team logo sits on a **fixed team-colour background**, that file wins. Without an override, the old rule still applies: on a dark colour, `alt-dark/` is used, then `glow-dark/`. Otherwise the regular logo is used. The six teams in the config are Tennessee, Clemson, Illinois, North Carolina, Purdue and Oklahoma State. Each one points at its existing `glow-dark/<Team>.png`.

## Every touched spot
| Spot | Change |
|---|---|
| `config/league.json` | New top-level `logos` key (`_note` + `force`), inserted before `about`. The nested postseason `logos` keys (~line 980) are untouched and not merged. |
| `scripts/site_common.py` | `forced_logos(config=None)`: reads and validates the config (cached in `_FORCED`). New `LogoConfigError`. `logo_info()` now also returns `"forced"` (a URL, or `""`). New `fixed_bg_src(info, bg)` holds the one rule for fixed backgrounds. `logo_html(bg=…)` uses it. New `is_white_tile()`. `is_dark()` is unchanged. |
| `scripts/scoreboard_data.py` (`logo_fields`) | Adds `"logo_forced"` to every team in `data/scoreboard/index.json`. |
| `data/scoreboard/index.json` | Regenerated. Only `logo_forced` was added; 6 teams have a value. |
| `reports/assets/scoreboard-overview.js` (team icon on `t.primary`) | `logo_forced` → dark rule → regular. |
| `reports/assets/guillotine.js` (team icon on `x.primary`) | Same. |
| `reports/transactions.html` | Regenerated. Only North Carolina's logo changed (2 swaps), on team-colour blocks. |
| `reports/postseason-*.html` | **Deliberately not committed.** 5.13 rebuilds these pages and will pull in this change (Chris, 2026-11-20). |
| `tests/test_logo_force.py` | New unit tests. |
| `tests/test_scoreboard_overview_browser.py` | Asserts that the team-colour icons use `logo_forced` and never the regular file for those teams. |

### Checked and deliberately left unchanged
- **`scripts/selection_watch.py` (~93) and `scripts/orphan_card.py`.** Both call `logo_html(bg="#ffffff")`, and the logo sits on a real white tile (`.sw-logo` / `.oc .top img` have `background:#fff`). The call now goes through `fixed_bg_src`, but white tiles are excluded, so the output is identical.
- **`scripts/roster_map.py` (~279, `logoDark`).** It only feeds theme-following markup (the `tl-hd`/`tl-d` pair on the chart and card). There is no team-colour block, so per the spec the theme-following output is unchanged. I left its inline alt/glow lookup as it is, because it deliberately emits unencoded paths, unlike `logo_info`.
- **`reports/assets/scoreboard.js` (header, line ~108).** The logo there is theme-following (`tl-hd`/`tl-d`) and sits beside the team-colour name chip, not on it. Unchanged.
- **`scripts/poll_page.py` / `poll_bot_cards.py` / `weekly_report.py`.** These are theme-following only (`bg=None`). `transactions_page.py` already passes the team bg and picks up the fix automatically.
- **`templates/weekly_report.html`.** CSS comment only.

## Decisions
1. **White tiles are excluded from `force`.** The spec says "`logo_html()` with a fixed `bg` uses forced first". Taken literally, that would also put the glow file on the white logo tiles in Selection Watch and the orphan cards: those two callers pass `bg="#ffffff"`. That contradicts the spec's own point that a dark-background glow can look wrong on white. It would also break Acceptance 3, which requires team-colour blocks only. So `is_white_tile()` (all channels ≥ 235 and chroma ≤ 12) skips the override. No team's row colour is that close to white. **For Chris to confirm:** forced = "team-colour blocks only, not white tiles".
2. **Forced beats dark alts too.** A forced team on a dark fixed bg also gets the forced file. None of the six has an `alt-dark`, so nothing changes today. It is still the precedence the offseason rebuild inherits.
3. **Validation runs at the first logo lookup, so it fails the build.** A forced path that is missing, absolute, contains `..` or is empty raises `LogoConfigError`, naming the team and the path. Every page generator (and the scoreboard JSON) calls `logo_info`, so a bad entry stops the workflow. A team with no `<Team>.png` prints a `WARNING` to stderr and is otherwise ignored, because `logo_info` returns `None` for that team. `_`-prefixed keys inside `force` are skipped.
4. **The JS doesn't re-check for white.** The two front-end spots always draw on the team's primary, so `logo_forced` wins outright there.

## Acceptance results
1. **Tests.** `python3 -m pytest -q tests`: 238 passed, 13 skipped (the opt-in browser suites). The baseline before this change was 230 passed. `node --test tests/*.test.js`: 72/72 pass. The new `tests/test_logo_force.py` covers:
   - config shape;
   - the forced file winning on fixed team-colour and dark backgrounds;
   - theme-following and white-tile output being unchanged for the six;
   - every other team's fixed-bg output matching the old rule;
   - a missing, absolute or `..` file failing, including through `logo_html`;
   - an unknown team warning;
   - `index.json` carrying `logo_forced` and matching `logo_info`;
   - both JS files preferring `logo_forced`.

   Browser suites with `RUN_SCOREBOARD_BROWSER_TESTS=1` (overview, scoreboard, postseason scoreboard, guillotine, selection watch): 8 passed, 32 subtests. The overview suite now also checks the forced icons.
2. **Before/after renders.** `pr-assets/logo-force-light.png` and `pr-assets/logo-force-dark.png` show each team on its own `team_colors` row, light and dark theme.
3. **Regenerated pages.** Ran `scoreboard_data.py --offline`, `transactions_page.py`, `postseason_page.py`, `poll_page.py`, `records_page.py`, `managers_page.py`, `standings_page.py`, `roster_map.py`, `special_page.py`, `selection_watch_page.py`, `matchups_page.py` and `orphan_card.py`. A/B check (`force` off vs on): the only differences are `<img src>` swaps from `<Team>.png` to `glow-dark/<Team>.png` for the six teams; everything else was byte-identical.
   - **Committed:** `transactions.html` (2 swaps, North Carolina) and `data/scoreboard/index.json` (`logo_forced` only; the offline build's `players.json` / `built_at` / `metadata_source` changes were reverted).
   - **Not committed: `postseason-2019…2025.html`.** These would get 72 swaps (Clemson 22, North Carolina 10, Purdue 12, Tennessee 11, Oklahoma State 9, Illinois 8). 5.13 rebuilds these pages and picks the fix up through `logo_html(team, bg=…)`. The committed copies on `main` are also stale against their generator (`.lo/.hi` colours, 2020 image order); that is for 5.13's regeneration, not this PR.
4. **No broken images.** I crawled all 113 HTML pages under `reports/`. 5,311 local `<img src>` checked (HTML-unescaped, URL-decoded): 0 unresolved. I also checked the 366 logo paths in `data/scoreboard/index.json` (`logo`/`logo_dark`/`logo_forced`): 0 unresolved.

## Unresolved / for Chris
- **The glow helps, but for 4 of the 6 it is only a partial fix.** Rough measure: the share of logo pixels with contrast below 1.5:1 against the row colour.

  | Team | Before | After |
  |---|---|---|
  | Tennessee | 100% | 75% |
  | Clemson | 100% | 74% |
  | Illinois | 73% | 60% |
  | North Carolina | 62% | 51% |
  | Purdue | 59% | 52% |
  | Oklahoma State | 57% | 44% |

  The glow restores the silhouette, so Tennessee and Clemson become readable. The interior still matches the row, though, and on Illinois, Oklahoma State, Purdue and North Carolina the halo is thin. Hand-picked dark alts (or the offseason chooser) would do better for those four. With this PR in place, that is a one-line config change per team.
- **Bracket redesign (5.13).** Its rows use `logo_html(team, bg=<row bg>)`, so it gets the fix with no extra work. Any JSON it emits for JS should include `logo_info(...)["forced"]` the same way `scoreboard_data.py` does.
