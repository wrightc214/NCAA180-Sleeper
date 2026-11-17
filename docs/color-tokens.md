# Colour tokens (good / bad, win % scale)

Shared colours for anything that means good/bad (Project Manager 5.8). Defined once in
`templates/menu.js` (built into `reports/assets/menu.js`, already loaded synchronously on every page),
written into `<style id="n180-tokens">` before the menu draws. **Hard-coded Standard (red/green) for now**;
the accessibility page will rewrite that style element per device (presets, custom pickers).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--good` / `--bad` | #1a7f37 / #b42318 | #4fc785 / #ff7b72 | text, lines, borders (≥ 4.5:1 on `--panel`) |
| `--neutral` | #6b7484 | #8a96ab | 50% point of the win % scale |
| `--good-soft` / `--bad-soft` | #e3f3e8 / #fbe4e1 | #173a2a / #4a2024 | background tints (rows, bubbles) |
| `--good-fill` / `--bad-fill` + `--on-fill` | #1a7f37 / #b42318 + #fff | same | solid badges with text on them |

## Rules
- Use `var(--good)` etc., never a red/green hex. A fallback is fine: `var(--good,#1a7f37)`.
- Pair colour with a non-colour cue where meaning matters (bold favourite, ✓/✗, label text).
- Win % (diverging scale, JS): `NCAA180.colors.scale(p)` → `rgb(...)` for `p` in 0..1 — bad → neutral grey → good,
  blended in OKLab. Colouring many cells: `const t = NCAA180.colors.tokens();` once, then `scale(p, t)`.
  Read tokens at draw time (they follow light/dark and, later, the viewer's setting).
- Saved images: `snapshot.js` copies `<style>` elements, so the viewer's colours carry over. Don't move the
  tokens to an inline `style` on `<html>`.

## Not yet on tokens (5.8 audit)
Page CSS `--up` / `--dn` (rank movement), `bowl_projection.py` (`#2e7d32` / `#c62828` / `#16743b` / `#b42318`),
live-status greens in `scoreboard-overview.css`, `snapshot.js` LIVE label, Selection Watch / Guillotine / standings
red/green. Moving them is part of the accessibility page build.
