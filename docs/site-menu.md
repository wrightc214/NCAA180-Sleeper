# Site menu (shared header)

One menu for every page (header rebuild, 2026-11-17). Before this, the tab row was baked into ~100
pages and `nav_refresh.py` rewrote them all each week.

| Piece | Role |
|---|---|
| `config/nav.json` | The menu: tabs (order, label, page, highlight aliases, state, icon) and fixed sub-rows (Poll pages, Special events). **Edit here.** |
| `templates/menu.js` | The renderer (template). |
| `scripts/menu_build.py` → `site_common.write_menu()` | Writes `reports/assets/menu.js` = config + data-driven rows read from `reports/` (Season / Week rows, projection archive, latest awards week). Runs at the end of the weekly job. |
| `site_common.menu_html(current, rows)` | What a page generator writes: empty placeholders + `<script src="assets/menu.js">`. |
| `scripts/menu_convert.py` | One-time switch of already-built pages (idempotent). Generators already emit placeholders. |

## Change the menu
1. Edit `config/nav.json`.
2. `python scripts/menu_build.py`, commit `reports/assets/menu.js`. No page is rebuilt.

## States
- `visible`: everyone.
- `hidden-dev`: shown only with **Dev view** on (amber, dashed, "DEV" tag). Listed in the public `menu.js`.
- `hidden`: left out of `menu.js`; direct link only. The page bakes `data-state="hidden"` for the DEV bar.

Neither hidden state is secret: the repo and every built page are public.

## Dev view
Per device (`localStorage["ncaa180.dev"] = "1"`). Switched in the About page's dev menu: tap the
page title 5 times within 3 seconds. With it on, `hidden-dev` items show and a "DEV — not public" bar
sits above the menu on any non-public page. The same panel has **Tester notifications**: the push
`test` flag (`app.js` `NCAA180.setTester`), the same flag as the notifications page's own title-tap trick.

## Page markup
```html
<nav class="weeks" aria-label="Pages" data-current="standings"></nav>
<nav class="weeks sub" aria-label="Seasons" data-row="standings-seasons"></nav>
<script src="assets/menu.js"></script><noscript><a href="index.html">Home</a></noscript>
```
Rows: `awards-seasons`, `awards-weeks-<year>`, `standings-seasons`, `postseason-seasons`,
`projection-archive`, `poll`, `special`. Sub-row items are highlighted by the page's file name.
The script is synchronous on purpose (small, cached): the menu is drawn before first paint.
