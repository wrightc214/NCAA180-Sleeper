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

## Additional development and validation pass

- Normalized invalid `save()` values (mode, motion, custom hex) before storage. Previously malformed values could be saved even though `read()` returned fallbacks.
- No-colour mode now overrides the shared solid-fill tokens `--good-fill` and `--bad-fill` with monochrome values. This is still not a complete no-colour audit: inline and unrelated page-specific colours remain.
- Replaced hard-coded positive/negative performance colours in `reports/assets/scoreboard.js` with `var(--good)`/`var(--bad)`.
- Added unit assertions for invalid inputs and monochrome fill tokens.
- Executed an isolated JavaScript parse/logic smoke test against the latest template using a mock module and localStorage: **passed** mode persistence, no-colour fill CSS, and invalid-value normalization. This is not a browser or full Node suite run.
- Queried GitHub Actions for latest test commit `170993483`: **zero workflow runs returned**. CI remains unverified.

**Additional risks for auditor:** the standalone Accessibility HTML currently does not use `site_common.page_head` and does not fully inherit normal page chrome; its CSS has not been visually validated. `motion=off` does not force animations on when the OS requests reduced motion, and the motion override needs specification-level testing. Custom colour contrast uses assumed panel backgrounds; actual pages may differ. Saved images and Discord image isolation remain untested. No claim of complete WCAG compliance.

## Further autonomous development — verification and integration notes

- **Standard-mode regression corrected:** Standard now retains the original `--good-soft` and `--bad-soft` tokens instead of replacing them with generic grey tints.
- **Motion:** `system` now emits a `prefers-reduced-motion: reduce` rule; `on` forces reduced animation; `off` no longer incorrectly forces reduced motion. Browser checks are still necessary to establish override behavior against page-specific rules.
- **All palette fills:** Non-Standard presets and Custom now derive `--good-fill` and `--bad-fill` from the selected colours, adjusted to at least 4.5:1 against white `--on-fill` labels. Standard retains historical fills; No-colour uses distinct dark greys.
- **Bowl projection source:** Migrated hard-coded outcome/movement green/red in `scripts/bowl_projection.py` to `var(--good)`/`var(--bad)`. Existing generated bowl pages have **not** been rebuilt, and the generator must be verified in a controlled non-publishing run.
- **Tests:** Added assertions for exact generated-menu/source equivalence and for both-theme foreground and fill contrast across all five modes. The generated menu was directly compared to the source with embedded nav JSON and was an **exact match** at the time of checking.
- **Checks actually run:** Connector-backed JavaScript smoke tests passed for all five modes' light/dark foreground contrast and white-on-fill contrast, unrelated storage key preservation, blocked localStorage exceptions, and script parsing of access.js/scoreboard.js. These are **not** GitHub Actions/Node/browser results.
- **CI:** Expanded the PR-only workflow's path filters to cover feature assets, config, generated page, service worker, and bowl source. Added Node `--check` and Python `py_compile` steps; execution still unconfirmed.

**Outstanding blockers and review risks:** no confirmed CI runs; no actual browser/screenshot/mobile validation; no full semantic-colour inventory; no proven image export behaviour; the Accessibility page remains standalone rather than sharing the full `page_head` layout; custom colour contrast assumes a representative panel background; no-colour meaning cues are not audited across every page. Do not merge without independent validation.

## Site chrome and generated page integration

The Accessibility page generator now uses `site_common.page_head(..., totop=False)` and `menu_html("access")` rather than copying the entire standalone HTML document. `templates/access.html` remains the editable source for the page-specific CSS and `<main>` content; `scripts/access_page.py` writes `reports/access.html` with the shared site CSS, fonts, app metadata, and dev-only menu. A generated-page structural regression test checks these elements. The committed HTML was rebuilt from the same template and shared head ingredients; **an actual Python generator execution has not been run in this environment**, so the auditor must run `python scripts/access_page.py` and check for a clean diff.

**Generator/asset validation commands for independent reviewer:**
```sh
python scripts/access_page.py
python scripts/menu_build.py
git diff --exit-code -- reports/access.html reports/assets/menu.js
node --test tests/*.test.js
node --check templates/menu.js
node --check reports/assets/menu.js
node --check reports/assets/access.js
python -m py_compile scripts/access_page.py scripts/bowl_projection.py
```
Do not execute the report publication or Discord posting commands during validation.

## Test harness discovery and current status

A connector-backed JavaScript harness fetched the six files needed by `tests/menu.test.js`, emulated the Node test/FS/Module APIs, and executed all registered test callbacks. **17/17 tests passed in this emulated harness** after correcting one stale assertion: the About page is now public in `config/nav.json`, so the previous test incorrectly expected it to be absent from the generated menu. This result is stronger than a parse-only smoke test, but **it is not a native Node.js `node --test` execution** and cannot substitute for CI.

- Added same-device cross-tab synchronisation via the browser `storage` event. Local saves and resets emit `ncaa180:accesschange`; `reports/assets/access.js` listens and refreshes its controls. Isolated event tests caught and corrected a constructor-reference issue; mocked event dispatch now passes.
- Added structural saved-image regression assertion: `snapshot.js` clones current document `<style>` elements, including `#n180-tokens`. This supports viewer-specific image colours but is **not** an actual screenshot comparison.
- PR workflow now also regenerates `reports/access.html` and checks `git diff --exit-code`, with no publishing.
- GitHub Actions workflow execution remains unconfirmed; do not report CI green without an actual run.

**Reviewer priorities:** run native Node tests, check actual rendered Accessibility page (including mobile and dark mode), verify reduced motion and keyboard access, verify images in browser, inspect generated bowl projection output, and check that no-colour semantics remain clear without hue.

## Latest autonomous validation pass

- Added same-device cross-tab settings propagation and a unit test for the `ncaa180:accesschange` event. An isolated event smoke test initially caught a `CustomEvent` reference error; corrected to `new window.CustomEvent(...)` in both menu files and reran successfully.
- Added DOM-mocked test of Accessibility page controls: selecting a preset, editing a custom colour, restoring only custom colours, resetting all accessibility settings, and reflecting another tab's change.
- Fetched current test suite and dependencies through the GitHub connector and executed all registered test callbacks in a custom JavaScript harness emulating Node `test`, `assert`, `fs`, `path`, and `Module` APIs. **18/18 passed** in this environment. This is not a native Node test runner and does not cover actual DOM rendering or browser APIs.
- Current PR remains **draft and unmerged**. Latest commit checked: `62b05f8`. GitHub Actions still returned **zero** runs associated with the head commit.
- No production or `main` changes were made.

**Remaining block:** native CI/browser validation is unavailable in the current execution environment. Reviewer should run the documented commands, visually inspect all presets on mobile/light/dark, test real screenshots, and assess the incomplete semantic/no-colour audit. Do not merge based solely on the emulated test pass.
