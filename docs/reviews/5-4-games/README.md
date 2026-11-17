# 5.4 Games overview — independent review

## Scope
This PR changes only the Games overview: rank-based ordering of the two ranked sections, higher-ranked team first in regular-season cards, and token-based win-probability text colors. No menu/header or other page logic is intentionally changed. **Do not merge until independently validated.**

## Files
- `reports/assets/scoreboard-overview.js`: numeric poll-rank helpers, stable ranked-section sorting, regular-season card row ordering, probability classes/strength.
- `reports/assets/scoreboard-overview.css`: probability text colors derived from `--good`, `--bad`, and `--mute`, with pregame colors muted and favorites bold.
- `docs/reviews/5-4-games/README.md`: this reviewer guide.

## Behavior and rationale
- Best (smallest) numeric rank determines the order of games in both ranked sections; JavaScript stable sorting preserves original order for equal ranks.
- Regular-season game rows sort by published poll rank, not live score or probability. Unranked teams follow ranked teams; two unranked teams retain their input order.
- Postseason cards retain frozen pairing/seed order. Multi-team NIT race cards retain their separate score-based ordering.
- 50% has zero color strength (neutral `--mute`); divergence increases toward 0% (`--bad`) or 100% (`--good`). Live uses full strength; pregame uses 60%. Favorites (>50%) are bold independent of color. Exactly 50% is neutral and not bold.
- Colors are CSS theme-token based; no literal red/green values introduced.

## Architecture and data impact
Client-only changes to the existing overview renderer and CSS. No API, scoring, persisted data, or league schema changes. The pre-built `reports/scoreboard.html` **has not been regenerated in this environment** because the repository cannot be cloned here. The page generator embeds the CSS and therefore MUST run before approval.

## Validation required (not executed here)
From repository root, on this branch:
```sh
python3 scripts/scoreboard_data.py --page-only
python3 -m pytest -q tests
for file in tests/*.test.js; do node "$file" || exit 1; done
RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_scoreboard_browser.py tests/test_scoreboard_postseason_browser.py tests/test_games_follows_browser.py
```
Commit only `reports/scoreboard.html` from page generation, excluding unrelated menu churn. Confirm no other ~100 HTML pages changed. Re-run tests after regeneration.

## Manual reviewer checklist
1. In both ranked sections, #3 vs #18 precedes #5 vs #6, independent of conference order.
2. A ranked team is first in every regular-season card (Featured, follows, conference, ranked), even if losing; two unranked teams retain input order.
3. Postseason seed order is unchanged, including repeated appearances of a card.
4. Win %: 50/50 neutral gray; 90/10 stronger positive/negative than 60/40; >50 bold. Pre colors visibly fainter than live.
5. Light and dark modes: inspect actual computed colors and measure WCAG text contrast against the card background (target 4.5:1 for small text); do not assume theme tokens satisfy it. Test any accessibility-token overrides separately.
6. Verify responsive mobile layout, browser console, followed teams, CCG and postseason, and no changes to detailed game pages.
7. Capture screenshots of the Games overview in light and dark modes and attach to PR.

## Risks / unresolved
- Browser compatibility for `color-mix()` and percentage math in `calc()` requires confirmation.
- Color contrast has **not** been measured; extreme endpoint colors may fail on one theme. If so, adjust theme-specific tokens or the mixing strategy, not hard-coded red/green.
- No automated tests were added or executed in this environment; the review cannot be marked passing.
- Before merge, fetch main and rebase if header/menu work landed after branch creation. Specifically inspect conflicts in scoreboard JS, `site_common`, and `app.html` (the latter two are not intentionally touched).
