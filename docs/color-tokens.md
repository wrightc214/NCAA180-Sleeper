# Colour tokens (good / bad, win % scale)

Shared colours for anything that means good/bad (Project Manager 5.8). Defined once in
`templates/menu.js` (built into `reports/assets/menu.js`, already loaded synchronously on every page),
written into `<style id="n180-tokens">` before the menu draws. The Accessibility page (`reports/access.html`)
rewrites that style element per device: Standard, red/green-safe `rg`, blue/yellow `by`, Custom. Palettes live in
`config/accessibility.json`. "No colour" is shown disabled ("No colour: not yet available"); a stored `none`
paints exactly like Standard until its non-colour cues are built (the `none` palette and engine code are kept).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--good` / `--bad` | #1a7f37 / #b42318 | #4fc785 / #ff7b72 | text, lines, borders (≥ 4.5:1 on `--panel`) |
| `--neutral` | #6b7484 | #8a96ab | 50% point of the win % scale |
| `--good-soft` / `--bad-soft` | #e3f3e8 / #fbe4e1 | #173a2a / #4a2024 | background tints (rows, bubbles) |
| `--good-fill` / `--bad-fill` + `--on-fill` | #1a7f37 / #b42318 + #fff | same | solid badges with text on them |

## Rules
- **Meaning → tokens.** Any colour that means something (good/bad, up/down, win/loss, odds, clinched/out, cut
  lines, grades, above/below projection, more/less likely) uses `var(--good)` / `var(--bad)` / `var(--neutral)`
  (plus `-soft` / `-fill` + `--on-fill`) in CSS, or `NCAA180.colors.scale()` in JS. Never a red/green hex,
  `rgb()`, `hsl()` or named colour. A fallback is fine: `var(--good,#1a7f37)`.
- **Exempt:** team / brand / conference colours (incl. the site `--accent`), category colours (positions),
  status badges (LIVE / FINAL / upcoming, the Games lead/underdog tag; redesign pending). They don't change
  with the viewer's mode.
- **PNG renders stay Standard.** Images Python renders for Discord/posts (poll, bot-ballot, weekly, projection
  cards) have no viewer. They screenshot the pages in a fresh headless browser, so they get the Standard tokens;
  where a card needs its old look, the shoot step applies it (e.g. `poll_bot_cards.shade()` in `shoot()`).
- Legacy `--up` / `--dn` are aliases of `--good` / `--bad` (kept defined so archived pages follow the viewer's
  mode). Don't use them in new code.
- Pair colour with a non-colour cue where meaning matters (bold favourite, ✓/✗, label text).
- Win % (diverging scale, JS): `NCAA180.colors.scale(p)` → `rgb(...)` for `p` in 0..1 — bad → neutral grey → good,
  blended in OKLab. Colouring many cells: `const t = NCAA180.colors.tokens();` once, then `scale(p, t)`.
  Read tokens at draw time (they follow light/dark and, later, the viewer's setting).
- Saved images: `snapshot.js` copies `<style>` elements, so the viewer's colours carry over. Don't move the
  tokens to an inline `style` on `<html>`.

## Guard
`scripts/color_literal_check.py` (run by `tests/test_color_literals.py`) fails on red/green colour literals —
hex, `rgb()`, `hsl()`, computed `hsl(`/`rgb(` strings, named colours in CSS — in `scripts/`, `templates/` and
`reports/assets/` outside the token definitions. Its allowlist is explicit and commented (token definitions,
brand accent, position colours, status badges, PNG renderers); a stale entry fails too. The same test fails on
any `var(--up)` / `var(--dn)` use. Archived pages under `reports/*.html` aren't scanned.
