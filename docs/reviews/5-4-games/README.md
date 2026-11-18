# 5.4 Games overview — independent audit guide

**PR #105 is a draft. Do not merge without independent validation.** This document is intentionally retained for the reviewer.

## Scope and behavior
- Both ranked sections sort games by the smallest valid poll rank in each matchup; ties preserve input order.
- Regular-season overview cards put the higher-ranked team first, preserving input order when both are unranked. Each team's score, projection, and win probability stays attached to that team.
- Postseason pairings preserve their existing seed order; multi-team NIT cards retain their own ordering.
- The accessible card label follows the displayed team order. Live cards' additional Pregame line also follows the displayed top team and complements the percentage if it is the second source-side.
- Win probability uses `--bad` (0%) → `--neutral` (50%) → `--good` (100%) with **OKLab** interpolation. Live is 100% color strength, pregame 60%, and final 30% (each relative to distance from 50%). Favorites (>50%) are bold only before the game is final; final percentages use normal weight so the winner retains visual emphasis. `--neutral` falls back to `--mute` if absent.
- The shared theme tokens are already defined by `templates/menu.js` (PR #102). This PR does **not** redefine them or modify menu/header behavior.

## Changed files
- `reports/assets/scoreboard-overview.js` — ranked-section selection/sorting, row ordering, accessible labels, probability style values.
- `reports/assets/scoreboard-overview.css` — six OKLab probability rules (including two final-state rules), neutral fallback, favorite weight only on nonfinal cards.
- `tests/games-5-4.test.js` — regression checks for ranked-section selection, ties, card/seed order, final-state CSS/mix, pregame summary, accessible labels.
- `docs/reviews/5-4-games/README.md` — this audit guide.

**Generated page:** `reports/scoreboard.html` was restored to the version on `main`; it has **not** been regenerated or committed for these source changes. The authoritative generator still needs to run; its output must be reviewed and committed separately. Do not treat source-only changes as shipped. Do not manually patch generated HTML.

## Architecture / data impact
Only the Games overview renderer and its CSS change. No scoring formulas, APIs, persisted data, league schema, other report pages, or navigation logic should change. `rankedSections(all)` is a small extracted helper to make actual section filtering and sorting directly testable.

The probability CSS uses `color-mix(in oklab, …)` rather than calling `NCAA180.colors.scale()` directly. This is an intentional design decision: accessibility theme-token changes immediately recolor the cards without a JavaScript re-render. Pregame and final strengths change saturation relative to neutral, **not opacity**. A 50% midpoint is used consistently even for NIT advancement groups; red indicates advancement is less likely than elimination, not below-average group performance. Record these accepted decisions in the 5.4 Project Manager entry.

## Required developer validation and independent reviewer recheck

Run and record the generator, pytest, all Node suites, and browser suites, including failures and skipped checks. The independent reviewer repeats the checks before acceptance. **Current status: generator not run; pytest not run; full Node suites not run; browser suites not run.** Targeted production-helper checks are not a substitute for these suites.

## Validation commands
From repository root:
```sh
python3 scripts/scoreboard_data.py --page-only
python3 -m pytest -q tests
for file in tests/*.test.js; do node "$file" || exit 1; done
RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_scoreboard_browser.py tests/test_scoreboard_postseason_browser.py tests/test_games_follows_browser.py
```

Commit only the intended generated `reports/scoreboard.html` change. Check the diff for unrelated CSS/page churn. Re-run tests after regeneration.

## Manual verification
1. Confirm #3 vs #18 precedes #5 vs #6 in **both** ranked sections; ties remain stable.
2. Confirm ranked team appears first in Featured, follows, conference, and ranked cards; two unranked teams keep original order.
3. Confirm postseason seed order and probabilities remain correct, and screen-reader labels match displayed rows.
4. In Chromium, inspect computed colors at **10%, 40%, 50%, 60%, 90%** in **live (100%), pregame (60%), and final (30%)** states in light and dark modes. Verify OKLab interpolation, neutral 50%, favorite font-weight 800 only on nonfinal cards, and normal weight 500 on final percentages. Include NIT group cards with their own status logic.
5. Measure text contrast against the actual `--panel` background at each tested value and **explicitly at the new 30% final strength** in both light and dark; target at least **4.5:1**. Previous sRGB measurements do **not** validate the OKLab intermediates.
6. Confirm final regular and NIT group cards say **Pregame %** (not Live %, Pre %, or Adv %) and check the 46px column on mobile **in light and dark**. **Not yet verified.** If it does not fit, propose **Pre %** as a candidate fallback and obtain reviewer approval **before** changing the label; the fallback is not approved or implemented. Verify final favorite percentage is not bold, including when the favorite lost. Check the live Pregame summary when the top team was originally match[1].
7. Check mobile layout, browser console, follows, CCG/postseason, and detailed scoreboard navigation. Capture light/dark screenshots if possible.

## Validation history and remaining risks
- Independent reviewer previously reported: pytest **95 passed, 10 skipped**; four existing Node suites passed; browser suites **3 passed / 8 subchecks**. The reviewer also measured sRGB colors with adequate contrast.
- Those results **predate** the latest OKLab and regression-test changes. They must not be presented as current passing results.
- Developer targeted checks executed against the production JavaScript fetched from the feature branch: **6 passed** (ranked game order, ranked side first, neutral 50%, 90% live mix, 90% final mix, final favorite color-class retention). After adding NIT final-header coverage, **all 7 cases** in `tests/games-5-4.test.js` passed in an isolated JavaScript compatibility harness (not the native Node test runner). These are targeted runtime assertions, **not** the full Node test suite. A separate static source/CSS inspection confirmed six OKLab probability rules and the final-state selectors; it is not a rendered browser check.
- Developer verification identified a defect: removing the `favorite` class on final cards also removed the final green color. Corrected by retaining the class and overriding font-weight through `.r3.final-odds .chance`; added a regression assertion. Fix commits: `692f19b`, `bc0e9cb`. The native Node regression suite has **not** been run after this correction; the feature-specific cases were executed in a compatibility harness.
- No GitHub Actions workflow runs were found for `bc0e9cb` at the time of inspection. This does not establish that tests passed or failed.
- **30% final-state contrast calculated:** using OKLab interpolation, the committed standard `--good`, `--bad`, `--neutral` theme tokens and `--panel` backgrounds (`#ffffff` light, `#16213a` dark). WCAG contrast ratios (rounded to 2 decimals):

  | Pregame probability | Light | Dark |
  | ---: | ---: | ---: |
  | 0% | 5.18:1 | 5.65:1 |
  | 10% | 5.08:1 | 5.59:1 |
  | 40% | 4.80:1 | 5.41:1 |
  | 50% | 4.71:1 | 5.36:1 |
  | 60% | 4.73:1 | 5.47:1 |
  | 90% | 4.79:1 | 5.83:1 |
  | 100% | 4.81:1 | 5.95:1 |

  All sampled values exceed **4.5:1** mathematically. This is a source-token calculation, **not** a computed-style browser measurement; accessibility presets/custom colors can change the result. Independent browser measurements remain mandatory.
- **Incomplete:** generator and generated HTML diff/commit; full pytest; all native Node suites; browser suites; mobile light/dark header fit; browser-computed OKLab contrast at 30% in both themes; manual NIT and winner emphasis review. These remain mandatory before acceptance.
- Local testing is partially possible via extracted production helpers, but a complete repository checkout and browser test environment were not available for these checks. Do not describe the targeted checks as full-suite validation.
- Before merging, compare against current `main` and resolve any divergence. **The assistant must not merge this PR.**
