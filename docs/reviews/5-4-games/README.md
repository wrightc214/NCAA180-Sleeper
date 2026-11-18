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

**Generated page:** `reports/scoreboard.html` was restored to the version on `main`; it has **not** been regenerated or committed for these source changes. The independent reviewer will run the authoritative generator and commit its output. Do not manually patch generated HTML.

## Architecture / data impact
Only the Games overview renderer and its CSS change. No scoring formulas, APIs, persisted data, league schema, other report pages, or navigation logic should change. `rankedSections(all)` is a small extracted helper to make actual section filtering and sorting directly testable.

The probability CSS uses `color-mix(in oklab, …)` rather than calling `NCAA180.colors.scale()` directly. This is an intentional design decision: accessibility theme-token changes immediately recolor the cards without a JavaScript re-render. Pregame and final strengths change saturation relative to neutral, **not opacity**. A 50% midpoint is used consistently even for NIT advancement groups; red indicates advancement is less likely than elimination, not below-average group performance. Record these accepted decisions in the 5.4 Project Manager entry.

## Reviewer commands
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
6. Confirm final regular and NIT group cards say **Pregame %** (not Live %, Pre %, or Adv %) and that the label fits the 46px column on mobile. If it does not fit, the reviewer may use the documented shorter fallback **Pre %** after checking visual fit. Verify final favorite percentage is not bold, including when the favorite lost. Check the live Pregame summary when the top team was originally match[1].
7. Check mobile layout, browser console, follows, CCG/postseason, and detailed scoreboard navigation. Capture light/dark screenshots if possible.

## Validation history and remaining risks
- Independent reviewer previously reported: pytest **95 passed, 10 skipped**; four existing Node suites passed; browser suites **3 passed / 8 subchecks**. The reviewer also measured sRGB colors with adequate contrast.
- Those results **predate** the latest OKLab and regression-test changes. They must not be presented as current passing results.
- The expanded `games-5-4.test.js` suite previously had an obsolete fallback-chain assertion; that assertion has been corrected, but this revision's tests have **not** been run in this environment.
- Per reviewer instructions, implementation does not run or report checks. The reviewer owns regeneration, all tests, browser inspection, and final generated HTML commit.
- Before merging, compare against current `main` and resolve any divergence. **The assistant must not merge this PR.**
