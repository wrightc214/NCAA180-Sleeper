# Accessibility 5.8 — PR #109 independent review handoff

**Status (2026-11-18): DRAFT / NOT MERGE-READY.** Branch: `feature/accessibility-5-8` → `main`. Owner has explicitly required independent review before any merge or deployment. This document is the canonical current-state handoff; older progress notes are superseded by the status below.

## 1. Purpose and approved behavior

Accessibility preferences are device/browser-local under **only** `localStorage["ncaa180.access"]`. No migration or modification of team/follow/push/dev settings. The agreed modes are Standard (red/green), red-green colourblind (blue/orange), blue-yellow colourblind (teal/red), No colour, and Custom. Expose native custom colour pickers, immediate preview, separate **Restore default custom colours** and **Reset all accessibility settings** (neither needs confirmation), motion Follow device/On/Off, and stronger emphasis. Keep LIVE/brand/alert red independent from win/loss semantic colours. Hide the navigation item behind Dev view until approved. Saved user images should inherit the viewer's selected colours; public/Discord graphics should remain Standard. Optional text zoom must be omitted unless mobile and saved-image compatibility is proven.

Contrast target: 4.5:1 for semantic text on actual light/dark panels, including presets and adjusted custom colours. Do not assume that a token calculation against a sample background proves site-wide WCAG compliance. Meaning must not depend on hue alone.

## 2. Implemented on this PR branch

| Area | Implementation | Caveat |
| --- | --- | --- |
| Settings API | `templates/accessibility.js` independently owns `NCAA180.access.read/save/reset/apply/contrast/adjust/defaults/modes`; bundled into `reports/assets/menu.js` | Browser integration needs validation |
| Persistence | `ncaa180.access` JSON with safe malformed/denied-storage fallback and input validation | No `text` field: zoom deliberately omitted |
| Palette tokens | `templates/accessibility.js`: `--good`, `--bad`, `--up`, `--dn`, soft and fill variants; light/dark modes; contrast-adjusted custom colours | Uses representative white and #171b22 backgrounds; audit real surfaces |
| Modes | Standard, `rg`, `by`, `none`, `custom` | No colour is intentionally partial; full implementation deferred per project-manager decision in §8 |
| UI | `templates/access.html`, `scripts/access_page.py`, `reports/access.html`, `reports/assets/access.js`; previews, native pickers, resets, motion, emphasis | Verify mobile, dark mode, keyboard and focus |
| Navigation | `config/nav.json` `access` tab is `hidden-dev`; generated menu includes it | Do not make public without approval |
| PWA | `reports/sw.js` cache version v4; precaches access page and JS | Real offline behavior untested |
| Other tabs | Browser `storage` listener and `ncaa180:accesschange` event | Test in two real tabs |
| Colour migration | `reports/assets/scoreboard.js` and `scripts/bowl_projection.py` use semantic outcome tokens | Generated bowl pages not rebuilt; remaining consumers un-audited |
| Saved images | `reports/assets/snapshot.js` already clones page `<style>` nodes, including shared `#n180-tokens` | Structural assertion only; PNG output not visually tested |
| Tests | `tests/menu.test.js` (navigation) and `tests/accessibility.test.js` (settings/colours/UI/bundle), plus read-only PR workflow | No confirmed GitHub Actions execution |

Standard mode preserves historical soft/fill colours. The shared `--up/--dn` bridge overrides old hard-coded report CSS for light, automatic dark, and explicit dark selectors without regenerating all historical reports. This is deliberately compatible with the existing `NCAA180.colors` API. New code should consume semantic tokens, not hard-code outcome red/green.

## 3. Testing — accurately separated

**Executed:** The GitHub-connected JavaScript harness fetched the current test suite and its dependent files, emulated the Node test/assert/fs/path/Module interfaces, and executed **18 of 18 test callbacks successfully**. Separate mocked tests checked all five modes' contrast against white and #171b22, solid-fill contrast against white labels, malformed/blocked localStorage, preservation of unrelated storage keys, change events, and simulated UI control interactions. Source and generated menu content matched exactly when substituting both the standalone accessibility source and embedded navigation data. Syntax parsing succeeded for inspected JS assets.

**Not executed or not confirmed:** Native `node --test`, GitHub Actions (last head check returned **zero** workflow runs), actual browser/Playwright, visual snapshots, real screen-reader/keyboard audit, offline PWA, actual saved PNG output, generated bowl pages, and site-wide semantic-colour audit. No claim of CI green, WCAG certification, or production readiness is made.

**Module architecture (post-review refactor):** The settings and semantic-colour engine now lives in `templates/accessibility.js`, independent of the navigation renderer in `templates/menu.js`. `scripts/site_common.py::write_menu` bundles the accessibility source into the generated `reports/assets/menu.js` using `/*__ACCESSIBILITY__*/` before embedding navigation JSON. This deliberately preserves synchronous first-paint token application, all existing static pages that only reference `assets/menu.js`, the `NCAA180.colors` and `NCAA180.access` APIs, and snapshot CSS inheritance. There is **no extra browser request or separate runtime accessibility.js**; the module is separate at source/build time. Test fixtures substitute the same source, and a generated-bundle equality assertion prevents drift. `tests/accessibility.test.js` contains 12 accessibility tests; `tests/menu.test.js` contains 6 navigation tests.

**Historical defects corrected while developing:** invalid literal `\\n` tokens broke JavaScript parsing; dark-theme CSS specificity initially defeated the alias bridge; Standard soft colours were unintentionally changed; event dispatch initially used unqualified `CustomEvent`; and a stale test incorrectly expected the now-public About page to be hidden. All were corrected on this branch; regression tests cover relevant behavior. Recheck independently.

## 4. Reproducible safe checks

Run in a local checkout of the PR branch. **Do not run deployment/publishing/report distribution jobs.**

```sh
git checkout feature/accessibility-5-8
node --test tests/*.test.js
node --check templates/accessibility.js
node --check templates/menu.js
node --check reports/assets/menu.js
node --check reports/assets/access.js
node --check reports/assets/scoreboard.js
node --check reports/assets/snapshot.js
node --check reports/sw.js
python -m py_compile scripts/access_page.py scripts/bowl_projection.py
python scripts/access_page.py
git diff --exit-code -- reports/access.html
python scripts/menu_build.py
git diff --exit-code -- reports/assets/menu.js
```

**Important:** `menu_build.py` may regenerate navigation data from the current local report directory and can produce differences unrelated to Accessibility. Inspect any diff before changing files. `access_page.py` regenerates a committed page and the PR workflow checks its determinism. The PR workflow is `.github/workflows/pr-safety-tests.yml`: `pull_request` only, `contents: read`, checkout credentials not persisted, no push/deploy/secrets, and scoped paths. GitHub may not run a newly introduced workflow until it exists on the default branch; **do not modify main just to enable it**. Inspect existing workflows separately for PR-triggered side effects.

## 5. Independent reviewer checklist (all pending until verified)

- [ ] Run native Node tests and Python/JS syntax checks; resolve any failures.
- [ ] Regenerate access page and menu; inspect diffs, ensure deterministic artifacts.
- [ ] Compare Standard screenshots to main on mobile/desktop, light/automatic dark/explicit dark.
- [ ] Test every mode on actual pages (Games, standings, projections, postseason and historical reports); inspect foreground, soft, fill, and movement tokens.
- [ ] Check 4.5:1 contrast against **actual** panels; custom extremes, near-identical colours, and warning behavior.
- [ ] Verify No colour and stronger emphasis communicate outcomes without relying on hue (including charts, bars, status, favourite, Clinched/Out).
- [ ] Verify keyboard focus, screen readers, semantic labels, controls, responsive layout and tap targets.
- [ ] Verify Follow device/On/Off motion, animations and scroll behavior with OS reduced motion both enabled and disabled.
- [ ] Test storage denial, malformed JSON, settings persistence across pages, cross-tab updates and unrelated preference preservation.
- [ ] Test saved-image PNGs in each palette and confirm public/Discord images use Standard; ensure no text zoom is unexpectedly introduced.
- [ ] Test PWA offline navigation, caching, version upgrade and direct access.html URL.
- [ ] Inspect bowl generator output and remaining hard-coded outcome colours; retain brand and LIVE distinctions.
- [ ] Reconcile concurrent Selection Watch 5.6 and other PR changes; avoid overwriting other authors' edits.
- [ ] Audit workflow safety and branch protections, and determine why PR Actions runs are absent.
- [ ] Document defects with severity, reproduction, affected files, and fix recommendations; rerun checks after fixes.

## 6. Known gaps / potential blockers

1. **No native CI/browser verification.** This alone prevents merge approval.
2. **No-colour and stronger emphasis are partial.** Focus outlines and preview symbols exist, but site-wide chart/status/favourite cues have not been comprehensively adapted.
3. **Saved-image and public-image isolation not proven.** Snapshot style inheritance is a structural observation, not a PNG/Discord test.
4. **Remaining semantic colour audit.** `docs/color-tokens.md` lists further targets; `scripts/bowl_projection.py` changed but its generated pages are not rebuilt.
5. **Custom contrast assumes representative backgrounds**, not every page's real surface.
6. **Motion=Off semantics and CSS specificity** need browser verification. Text zoom was intentionally omitted.
7. **Concurrent work** may change shared `templates/menu.js`, `reports/assets/menu.js`, `tests/menu.test.js` and generated pages.

## 7. Decisions and guardrails

Reviewer may propose fixes and update this PR branch as authorized, but **must not merge PR #109, modify main, or deploy**. Keep it draft until the owner and independent auditor agree it meets acceptance criteria. Treat unverified work as unverified. Do not block unrelated fixes on unavailable CI, but record the limitation precisely. Prefer source changes followed by controlled generation, not direct edits to generated assets. The accessibility module is a source file, not a separate runtime asset. The reviewer should deliver a PASS / PASS WITH FIXES / BLOCKED decision with evidence and explicit remaining issues.

## 8. Project-manager decision: No colour mode is deferred, not cancelled (2026-11-18)

**Product direction:** NCAA 180 is currently a 180-manager dashboard with a predominantly male audience. The longer-term goal is to package the complete system as a reusable **super-league template**. Prioritize finishing the full dashboard and maintaining clean, responsibility-based modules over polishing a specialized mode unlikely to see substantial immediate use. This is a sequencing decision, **not** a decision that accessibility is unimportant or that no user could benefit.

**Current PR scope:** Retain the existing `none` / No colour preference and baseline monochrome palette; do not remove the mode or its stored-settings compatibility. Do **not** expand PR #109 into a site-wide monochrome redesign, pattern library, or component-by-component symbol retrofit. Treat current No colour as **basic/partial**, not fully supported or validated. This deferral is approved and should not by itself block PR #109; unrelated core accessibility defects and colour-only meaning in essential workflows still warrant review. Continue prioritizing red-green CVD, contrast, motion, emphasis, and stable shared settings.

**Future project backlog (project manager: copy into project plan):**
- **Feature:** Complete No colour / monochrome accessibility mode for the reusable super-league template.
- **Status:** Deferred / planned; **not cancelled**. Implement after core dashboard build-out and before claiming full accessibility readiness for the packaged template.
- **Scope:** Audit every dashboard page and generated graphic; distinguish positive/negative/neutral and game states without hue, using meaningful text, symbols, shape, border or pattern as appropriate. Ensure graphs, probability bars, standings, odds, live/final status, mobile views, saved images, light/dark themes and print remain interpretable.
- **Acceptance:** No critical distinction depends on colour alone; complete keyboard and screen-reader labels where visual markers are introduced; test grayscale/high-contrast/light/dark/mobile, saved PNG and public/Discord isolation; no regression to Standard, RG/BY or Custom modes.
- **Architecture:** Build semantic cues in the responsible components, with shared tokens/helpers only where multiple consumers need them. Avoid a monolithic global CSS workaround or adding modules with no clear ownership.
- **Reason for deferral:** Scope and opportunity cost, not an assumption that only people with achromatopsia could benefit. Achromatopsia prevalence is **not** a valid estimate of all users who might use No colour (including low vision, situational needs, or preference).

**Architecture direction for current PR:** Keep `templates/accessibility.js` responsible for settings, resolution, semantic palette, persistence and events; keep `templates/menu.js` responsible for navigation. Bundle the former synchronously for backward compatibility with static pages. Next consider (a) one canonical validation/normalization boundary for preferences, (b) explicit separation between saved motion preference and resolved effective motion behavior, and (c) a concise semantic token contract, without building a general-purpose settings framework. Add focused tests for these changes. Defer a new framework, TypeScript conversion, bundler, broad settings platform, or full No colour UI retrofit.

## 9. Development chronology (summary, not current status)

The work began with a light/dark `--up/--dn` bridge, then added local settings, presets, custom pickers, page generation, offline precache, colour migrations, motion, cross-tab events and expanded tests. Multiple defects were caught in smoke checks and fixed. The PR-only workflow was added but has not produced a confirmed run. This consolidated document replaces the earlier append-only notes, some of which described features as not yet implemented or the page as not using the shared site head; those descriptions are historical and no longer current.
