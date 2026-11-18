# Accessibility 5.8 — independent validator handoff

**Status: implementation in progress; NOT approved for merge.** This file is a living review record, not a claim that features have shipped.

## Scope and approved decisions
- Per-device `localStorage["ncaa180.access"]` stores mode, custom bad/good colours, text size (only if proven safe), motion, and emphasis. Never modify `ncaa180.push` or team/follow preferences.
- Presets: Standard, red-green colour blind, blue-yellow colour blind, No colour, Custom. Light and dark text tokens must reach 4.5:1 against the relevant panel; custom warnings are advisory.
- No colour retains readable endpoints and uses explicit non-colour cues.
- Native colour inputs, live previews, **Restore default custom colours** beside the pickers, and a separate **Reset all accessibility settings** control. Neither reset affects unrelated preferences.
- Reduce motion: Follow device / On / Off. Stronger emphasis includes visible focus and non-colour meaning cues.
- Keep brand/alert red independent of `--bad`; LIVE state is semantic, not a positive result. League-facing Discord images always use Standard.
- Navigation starts `hidden-dev`; independent approval is required to make it visible.
- Optional text size is a separate, removable experiment; do not ship if mobile overflow or saved-image regressions remain.

## Baseline inspection
- `config/nav.json` is the source of truth; `scripts/menu_build.py` and `scripts/site_common.py` generate `reports/assets/menu.js` from `templates/menu.js`. Do **not** hand-edit the generated menu.
- `templates/menu.js` already defines `--good`, `--bad`, `--neutral`, their soft/fill variants, and OKLab scale. It injects `#n180-tokens` synchronously and exposes `NCAA180.colors`.
- `templates/weekly_report.html` still hard-codes `--up` and `--dn` for light and dark themes. Old pages bake that CSS, so shared-menu token overrides are preferred over rebuilding all historical pages.
- `reports/sw.js` currently uses shell version `v3` and precaches menu/app but not Accessibility.
- `docs/color-tokens.md` lists further audits (bowl projection, scoreboard, Guillotine, Selection Watch, standings).
- PRs #102 and #105 are merged; #106/#107 are merged. Selection Watch stage 2 (5.6) remains an integration dependency.

## Validator checklist (pending)
- [ ] Compare Standard mode screenshots against current main (light/dark, desktop/mobile).
- [ ] Validate all preset token contrast >= 4.5:1 against actual panel colours.
- [ ] Test malformed, stale, or unavailable localStorage; settings persist across navigation.
- [ ] Test custom colours, warning thresholds, both reset controls, and immediate preview.
- [ ] Verify meaning is conveyed without colour (bars, favourite, movement, Clinched/Out).
- [ ] Check saved images inherit custom colours and exclude optional zoom; Discord images stay Standard.
- [ ] Verify reduce-motion override and focus visibility.
- [ ] Confirm hidden-dev nav behavior, direct URL, and offline PWA cache.
- [ ] Run existing tests and browser regression suite.
- [ ] Re-audit 5.6 once it lands; resolve conflicts before independent approval.

## Architectural change log
Append each significant code change with: affected paths, necessity, rejected alternatives, tests run, and remaining risks. The author must never merge this PR.
