# PR #109 — Accessibility 5.8 settings inventory

**Branch:** `feature/accessibility-5-8`. **Status:** Draft; independent review required; do not merge or deploy.

## Configuration architecture

The project owner approved `config/accessibility.json` as a dedicated exception to the default `config/league.json` settings location. All owner-facing accessibility presentation settings live in this file. Python reads through `scripts/league_config.py::accessibility()` and `scripts/accessibility_config.py`, which validates and supplies defaults. The menu build embeds the same validated settings into the browser bundle for synchronous use on historical static pages. No browser-local setting is written to the public configuration file.

Individual users' selected mode, colours, correction, motion and emphasis remain in `localStorage["ncaa180.access"]`. The owner can set their defaults under `defaults` below.

Missing config files, missing keys, malformed hex colours, invalid types and out-of-range ratios use safe code defaults. Every configurable key below is documented in its parent section's `_note`.

## New settings — file, key, default

| File | Key | Default |
|---|---|---|
| `config/accessibility.json` | `palettes.standard.light.positive` | `#1a7f37` |
| `config/accessibility.json` | `palettes.standard.light.negative` | `#b42318` |
| `config/accessibility.json` | `palettes.standard.light.neutral` | `#6b7484` |
| `config/accessibility.json` | `palettes.standard.dark.positive` | `#4fc785` |
| `config/accessibility.json` | `palettes.standard.dark.negative` | `#ff7b72` |
| `config/accessibility.json` | `palettes.standard.dark.neutral` | `#8a96ab` |
| `config/accessibility.json` | `palettes.rg.light.positive` | `#0758a8` |
| `config/accessibility.json` | `palettes.rg.light.negative` | `#a65300` |
| `config/accessibility.json` | `palettes.rg.dark.positive` | `#79b9ff` |
| `config/accessibility.json` | `palettes.rg.dark.negative` | `#ffb45d` |
| `config/accessibility.json` | `palettes.by.light.positive` | `#007b73` |
| `config/accessibility.json` | `palettes.by.light.negative` | `#b42318` |
| `config/accessibility.json` | `palettes.by.dark.positive` | `#65d4c6` |
| `config/accessibility.json` | `palettes.by.dark.negative` | `#ff7b72` |
| `config/accessibility.json` | `palettes.none.light.positive` | `#252525` |
| `config/accessibility.json` | `palettes.none.light.negative` | `#595959` |
| `config/accessibility.json` | `palettes.none.dark.positive` | `#f2f2f2` |
| `config/accessibility.json` | `palettes.none.dark.negative` | `#c5c5c5` |
| `config/accessibility.json` | `appearance.soft.light.positive` | `#e3f3e8` |
| `config/accessibility.json` | `appearance.soft.light.negative` | `#fbe4e1` |
| `config/accessibility.json` | `appearance.soft.dark.positive` | `#173a2a` |
| `config/accessibility.json` | `appearance.soft.dark.negative` | `#4a2024` |
| `config/accessibility.json` | `appearance.alternate_soft.light.positive` | `#e9eef2` |
| `config/accessibility.json` | `appearance.alternate_soft.light.negative` | `#f1edf0` |
| `config/accessibility.json` | `appearance.alternate_soft.dark.positive` | `#26313a` |
| `config/accessibility.json` | `appearance.alternate_soft.dark.negative` | `#342c32` |
| `config/accessibility.json` | `appearance.fill_text` | `#ffffff` |
| `config/accessibility.json` | `appearance.monochrome_fills.positive` | `#3c3c3c` |
| `config/accessibility.json` | `appearance.monochrome_fills.negative` | `#656565` |
| `config/accessibility.json` | `contrast.minimum_ratio` | `4.5` |
| `config/accessibility.json` | `contrast.distinguishability_ratio` | `1.5` |
| `config/accessibility.json` | `contrast.light_background` | `#ffffff` |
| `config/accessibility.json` | `contrast.dark_background` | `#171b22` |
| `config/accessibility.json` | `defaults.mode` | `standard` |
| `config/accessibility.json` | `defaults.motion` | `system` |
| `config/accessibility.json` | `defaults.emphasis` | `false` |
| `config/accessibility.json` | `defaults.auto_contrast` | `true` |
| `config/accessibility.json` | `labels.auto_contrast` | `Automatically improve contrast` |
| `config/accessibility.json` | `labels.low_light` | `Selected colours may be difficult to read on light backgrounds.` |
| `config/accessibility.json` | `labels.low_dark` | `Selected colours may be difficult to read on dark backgrounds.` |
| `config/accessibility.json` | `labels.low_fill` | `White text on solid fills may be difficult to read.` |
| `config/accessibility.json` | `labels.similar` | `Positive and negative colours may be difficult to distinguish; automatic contrast correction cannot guarantee distinguishability.` |

## Validation / reviewer checklist

- Run native Node tests, Python build, and inspect regenerated `reports/assets/menu.js` and `reports/access.html` for reproducibility.
- Verify missing or partial `config/accessibility.json` does not break page generation.
- Check light/dark contrast and alternate presets using custom owner settings, including the conditional user correction toggle.
- Verify user localStorage preferences do not overwrite owner settings and the public/Discord graphics remain isolated from user selections.
- Audit remaining hardcoded accessibility UI strings, browser thresholds, and fixed presentation values; distinguish owner-adjustable settings from implementation constants.
- Keep PR #109 draft and unmerged pending independent review.
