# PR_README — Task 5.13 Playoff bracket redesign (desktop + phone + export)

Delete this file and `pr-assets/5.13/` at merge.

## What changed

| File | Change |
|---|---|
| `scripts/bracket.py` (new) | Reusable bracket component: `order_rounds()` → `model()` → `desktop_html()` / `phone_html()` / `export_templates()`. Nothing in it is Playoff-specific except the optional quad / bowl / champion fields, so NIT/CCG can feed it later (not converted here). |
| `reports/assets/bracket.js` (new) | Phone layout and navigation (swipe, tabs, arrow keys, reduced motion) plus the Save image menu (NCAASnap). |
| `scripts/postseason_page.py` | `bracket_html(po, col, year, short, current=None)` now builds the model and calls the component. It still returns `""` when the playoff isn't a clean knockout. The old bracket CSS is removed and `bracket.CSS` added. Season rows carry their `GameID` (as `id`) for the Scoreboard link. |
| `config/league.json` | New `postseason.display.bracket`: `loser_opacity` 0.35, `loser_grayscale` 0.6, `quad_label` "{bowl} Quad", plus `_note`. |
| `reports/assets/snapshot.js` | `save({..., scale})` option, default 2 and backward compatible; the full bracket uses 1.5 for iPhone. |
| `scripts/bowl_projection.py` (`snap_js`) | The generic per-section image button skips a section that holds a bracket, which brings its own menu. |
| `reports/postseason-2019…2025.html` | Regenerated. `postseason.html` (2026) is still owned by `bowl_projection.py` until 2026 postseason rows are published, so it is unchanged. |
| `tests/test_bracket.py`, `tests/bracket_fixture.py`, `tests/test_bracket_browser.py` | Unit tests, fixtures (2025 as played, cut mid-Sweet 16, cut mid-Elite 8) and browser tests. |
| `.github/workflows/pr-check.yml` | Installs WebKit and runs the bracket browser tests. |

## Build notes

- **Geometry is from the mockup.** Rows 292×42, a 2 px gap inside a game, 104 px first-round pitch, 52 px between rounds, 34 px quad header plus 40 px between quads. The board is about 2,026 px wide and scrolls inside the section. The champion card is centred on the title game.
- **Order.** When the First Round seeds are a full 1…2n, games use standard bracket position (1v32, 16v17, 8v25 …). That gives the right quad order (1-, 4-, 2-, 3-seed quads, as the `bowl_rotation` note defines) from the moment the bracket is drawn. If any later game doesn't sit on two adjacent feeders, the order falls back to the old results-based method. All seasons 2019–2025 render, and 2025's order is unchanged.
- **Inside a game:** in the First Round the higher seed is on top. In later rounds, the team from the upper feeder is on top, matching the mockup (Baylor over Washington State, Washington State over Arizona State in the Rose Bowl).
- **Quads.** Past seasons use the Elite 8 bowls as played. The current season uses the planned bowls from `ps.playoff_round_bowls(year)`, so quads are named from the draw. The label comes from config. Quad names are never hard-coded.
- **Logos.** Every team logo on a team-colour row comes from `site_common.logo_html(team, bg=row bg)`, so 5.14's `logos.force` applies with no bracket code. The phone view and every export clone the same `<img>` elements, so the image matches the screen; there is no separate JSON logo choice in the bracket JS.
  - Rebased on `main` @ `4c3be49` (5.14, #124).
  - `test_forced_logos_on_team_rows` checks that a forced team's rows use its forced file. Clemson is the only one of the six forced teams in the 2025 bracket (2 seed, Peach Quad, Final Four), and all 22 of its logos are `glow-dark/Clemson.png`.
  - Known limit from 5.14: the glow only outlines Illinois, Oklahoma State, Purdue and North Carolina. Fixing that is a config line per team once dark alts exist, with nothing in this PR to change.
- **Dimming.** On screen, a loser row uses opacity plus `grayscale()` from config, and only once its game is final. In exports, each loser row carries precomputed colours (`data-xbg` / `data-xfg`, the same matrix as CSS `grayscale()`), and its logo is greyed through a canvas, because html2canvas can't draw `filter`.
- **Fonts and colours.** Page chrome uses the site's tokens (`--bg`, `--panel`, `--ink`, `--mute`, `--line`; Big Shoulders / Barlow) rather than the mockup's Oswald / Inter, so the bracket follows light and dark themes. Only team blocks carry team colours.

## Decisions I made (please confirm or overrule)

1. **Advancing teams fill the next slot before that game is drawn.** They show at full colour with no score, and the connector is in their colour. "TBD" appears only where the team isn't known yet.
2. **Game links exist only for games with a Scoreboard GameID**, which means current-season games. Past seasons (2019–2025) have no Scoreboard postseason data and no GameIDs, so their games aren't links. The link format is `scoreboard.html?season=&week=&post=<GameID>`, as `scoreboard.js` builds it.
3. **Filename clash in the spec.** The spec gives `ncaa180-<year>-playoff-elite-8.png` both to Elite 8 & beyond and to "This round" on the Elite 8. I named them:
   - `…-elite-8-and-beyond.png` for Elite 8 & beyond;
   - `…-elite-8.png` for the round.
4. **The phone opens on the round in play**: the first round with a live or upcoming game. When everything is final, it opens on the Championship (champion card first).
5. **On the phone, tapping the peeking round moves to it** rather than opening a game, as in ESPN's app. A tap on the focused round opens the Scoreboard.
6. **The round tab strip is a native horizontal scroller.** It scrolls to centre the active tab rather than sliding a hidden track. In the mockup's sliding model, the far tabs on a 320 px phone sat outside the strip and couldn't be tapped. A test covers this.
7. **Narrow phones (under 360 px)** get a 10 px margin and a 40 px peek (spec: about 60), and slightly smaller seed, logo and score. Otherwise names like "Chattanooga" or "Georgetown" don't fit.
   - On phones, multi-word names wrap and the row grows, which the spec allows. Single words never break unless they physically can't fit.
   - On desktop every name fits on one line; a test checks every row is 42 px.
8. **The phone/desktop breakpoint is 720 px.** At 768 px (tablet portrait), you get the desktop board with horizontal scroll inside the section.
9. **The conference line stays at full text colour** (the mockup used 0.8 opacity), so the small text keeps the pair's contrast.
10. **Platform icons are generic glyphs**: a monitor for 2× and a phone for 1.5×, always beside the label text. I used no Apple or Android brand marks.
11. **Header state.** "Final" when the champion is decided; "Live · updated <ET>" when any game is live; otherwise "Updated <ET>". Each export computes its own state from the games it shows. Live images also carry the site's LIVE · UNOFFICIAL · as-of stamp.
12. **Reduced motion.** It honours the OS setting and the site's own Reduce motion setting (`access.js`), including the JS scrolling.
13. **I dropped "· standard scoring" from the mockup header.** The spec's header list doesn't include it. It's easy to add back.
14. **Edge seasons.**
    - 2020's group stage isn't a knockout, so its bracket starts at the Elite 8, with no quads.
    - 2021 has no Elite 8 bowls, so it has no quads and no quad exports.
    - 2019 (16 teams) gets quads of 4 teams.

## Open questions

- **iPhone share sheet.** The WebKit test runs in CI (Playwright WebKit can't be downloaded in my environment). A real-iPhone check of the share sheet with the 1.5× image is still worth one tap from you.
- **Past-season links.** OK that 2019–2025 games aren't clickable? The Scoreboard has nothing to show for them.
- **The filename call in decision 3.**

## Known drift in regenerated pages (not this PR's change)

Rebuilding `reports/postseason-2019…2025.html` also picks up generator changes from `main` that those committed pages never got:
- 5.14 forced logos on the six teams (72 swaps across the seasons);
- `.lo`/`.hi` colours becoming `var(--bad)`/`var(--good)`;
- a different order for some 2020 bracket images.

These are expected.

## Contrast

Every winner row on both views, at 320, 390, 768 and 1280 px in light and dark, was measured in the browser against its computed colours: **all ≥ 4.5:1** (checked by `test_widths_themes_overflow_contrast_names`). **Dimmed losers are exempt by design.** They use opacity 0.35 plus grayscale 0.6 so the winner reads at a glance, and the dim level is in config.

## Canvas sizes (full bracket)

| Size | Pixels | Area | iOS Safari limit 16.78 MP |
|---|---|---|---|
| 2× | 4100×4494 | 18.4 MP | over: Android & desktop only |
| 1.5× | 3075×3370 | 10.4 MP | fits |
