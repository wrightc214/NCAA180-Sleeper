# Guillotine 2025 replay (Dev only)

Chris (2026-11-24): preview what the Guillotine page looks like finished, using 2025's real week 13–17 scores.

- `data/replays/guillotine-2025.json`: `python scripts/guillotine.py --year 2025 --out-dir /tmp/g25`, json copied in.
  Weeks 12–16 (Chris 2026-11-24). Kept out of `data/scoreboard/` on purpose: `trophies.py` reads `data/scoreboard/<year>/guillotine.json`
  and would have logged a 2025 Guillotine trophy. `Guillotine_Season.csv` untouched.
- `special_page.py` writes `reports/guillotine-<year>.html` for every replay file, with a
  "Replay, not an official result" note. `guillotine.js` reads `data-src`, maps 2025 league IDs to this
  season's leagues by name (colors, logos, labels), keeps the 2025 team name, skips the live player feed.
- Menu: new `guillotine-seasons` row (2026 public, "2025 replay" hidden-dev, `min: 2` so the public sees no row).
- Fixes found while previewing, both affect the live page too: champion banner icon now uses the team row;
  Eliminated "Out" column 54 → 92 px so "Wk 17 · PS5" fits on one line.
- Tests: pytest 345 passed; browser guillotine + menu 8 OK (new `test_guillotine_replay`).

To remove the replay later: delete `data/replays/guillotine-2025.json`, `reports/guillotine-2025.html` and the nav row item.
