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

## Review pass — 2026-11-17
**Actual scope currently implemented:** documentation and the legacy movement-colour bridge only. The Accessibility page, settings persistence, preset palettes, custom picker, motion/emphasis controls, offline precache, and browser tests are **not implemented**.

**Bug found and corrected:** the first bridge added `--up`/`--dn` only under `:root`. Existing dark-mode template selectors (`:root[data-theme=dark]` and `:root:not([data-theme=light])` inside the dark media query) have greater specificity and would retain the hard-coded dark colours. The bridge now repeats the alias declaration in those selectors. A regression test was added to `tests/menu.test.js` to assert all three selector cases.

**Generated-file consistency:** both `templates/menu.js` and `reports/assets/menu.js` were updated with the same bridge. The generated asset must be checked against a fresh `python scripts/menu_build.py` run before merge; rebuilding might also change unrelated dynamic menu data.

**Validation limitations:** repository clone was attempted but this execution environment could not resolve github.com. Connector reads confirmed the branch content and matching bridge snippets. No full Node test run, browser run, screenshot comparison, or CI pass is claimed. GitHub commit combined-status endpoint returned no statuses for the latest commit. Independent validator must execute the existing suite and browser checks.

**Remaining concern:** verify CSS cascade in actual browsers, including old report pages, explicit dark mode, automatic dark mode, and a future custom palette. Also check whether the weekly report's original `--up`/`--dn` values should be migrated in its template for newly generated pages, while preserving old-page support.

## PR-only testing and main-branch protection — 2026-11-17

**Workflow committed:** `.github/workflows/pr-safety-tests.yml` on `feature/accessibility-5-8` in PR #109, commit `62d77bd29b4add4a0411d3ba7d30bff4c1db0926`.

**Safety configuration (as committed):**
- Event: `pull_request` (opened, synchronize, reopened), scoped to menu files, `tests/**`, and the workflow file. **No `push`, `pull_request_target`, `workflow_dispatch`, or deployment event.**
- Explicit `permissions: contents: read`; `actions/checkout@v4` with `persist-credentials: false`.
- No secrets, deployment credentials, publishing steps, production-data writes, or auto-merge.
- Job restricted to PRs whose head repository equals this repository; 10-minute timeout; concurrency cancels superseded PR runs.
- Node.js 22 executes `node --test tests/*.test.js`. This is **only the Node test suite**, not Python, Playwright, visual, or accessibility browser validation.

**Verification performed:** PR #109 was confirmed open, draft, and unmerged; head commit `62d77bd` at the time of inspection. GitHub's commit-workflow-runs query returned **zero runs**, so **no passing CI result is claimed**. Whether a newly introduced workflow runs from this PR must be confirmed in GitHub Actions. Do not alter `main` merely to enable it without owner approval.

**Important boundary:** This workflow itself is read-only and has no deployment steps. That does not by itself establish that *other* workflows triggered by PR events are safe; the reviewer should separately audit existing workflows and repository branch protection. PR changes must not be merged or deployed by the author. A green CI result is necessary but does not replace independent validation.

## Implementation progress — subsequent development pass

- Added `NCAA180.access` in shared menu source and generated menu: `read()`, `save(partial)`, `reset()`, `apply()`, `contrast()`, `adjust()`, `defaults`, `modes`. Preferences stored only under `ncaa180.access`. Existing `NCAA180.colors` remains available.
- Added Standard, red-green (blue/orange), blue-yellow (teal/red), no-colour and custom palettes, with per-theme WCAG text-colour adjustment. Existing `--good`, `--bad`, `--up`, `--dn` tokens remain the integration contract.
- Added `templates/access.html`, generated `reports/access.html`, `scripts/access_page.py`, and `reports/assets/access.js`. UI includes native pickers, live previews, individual custom restore, full reset, motion and emphasis.
- Registered hidden-dev Accessibility tab in `config/nav.json` and updated generated `reports/assets/menu.js`; added offline precache in `reports/sw.js` (v4).
- Added Node unit tests for persistence, reset, malformed storage, and contrast.

**Checks actually executed in connector-backed JavaScript runtime:** parsed and executed both menu scripts with mocked `module` and `localStorage`; verified all five modes persist, custom colours save, reset removes the key, malformed JSON falls back safely. Checked preset foreground colours against white and dark (#171b22) panels; all inspected pairs exceed 4.5:1. Verified contrast adjustment of white-on-white yields #767676 at approximately 4.54:1.

**Still unverified:** full Node test runner, GitHub Actions, browser UI, mobile layouts, actual dark-panel colours, snapshot image propagation, all hard-coded colour consumers, service worker caching, motion override, no-colour cue completeness. Do not mark this PR ready for merge. Also check whether the page's bespoke markup should be migrated to the standard `page_head` generator, and regenerate the shared menu using `scripts/menu_build.py` before merge.

**Critical bug fixed during this pass:** literal `\\n` sequences had been inserted between JavaScript statements in the previous bridge commit, breaking parsing. Replaced them with real newlines in both source and generated files before adding the new settings engine.
