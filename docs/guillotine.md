# The Guillotine

Every team plays postseason weeks 13–17 on its own standard score. Settings and rules live in
`config/league.json → postseason.guillotine`. Spec: `claude/todo-guillotine.md` in the NCAA 180 project.

## Rules

- A week counts only that week's score.
- Weeks 13–16: half of the field entering the week advances, rounded down. Everyone tied with the last spot
  advances too (PGA style), and the next cut is half of that bigger field. No ties: 180 → 90 → 45 → 22 → 11.
- Week 17: the top score wins. An exact tie goes to the week 18 score among the tied teams, then co-champions.
- Orphan teams play like everyone else.
- Stat corrections: a week is frozen the first run it is final. A rerun only **adds** teams pushed over the
  line (`AddedByCorrection = 1`); nobody already through is removed and the frozen cut line stays.
- The champion is recomputed each run, like the other postseason results. Late stat corrections are an open
  question (`claude/todo-postseason-stat-corrections.md`).

## Pieces

| Piece | What it does |
|---|---|
| `scripts/guillotine.py` | Cuts each finished week → `data/Guillotine_Season.csv` + `data/scoreboard/<season>/guillotine.json`. Weekly job (`guillotine`). `--year 2025 --out-dir DIR` replays a past season. |
| `scripts/special_page.py` | `reports/special.html`, the **Special Events** tab. Sub-tabs come from `config/nav.json` → `rows.special` (add the Dwight Fight there; `python scripts/menu_build.py`). |
| `reports/assets/guillotine.js` + `guillotine-model.js` | The page: alive teams sorted by live projection (score, live projection, minutes left, % to survive), current and projected cut lines, eliminated teams with their week, and a week picker for frozen weeks. Same live model as the Games page. |
| `scripts/postseason_announce.py` | Pushes each week's cut (one line per team, only to that team's or league's followers; event followers get the summary) and the champion. A week's cut rides along with that week's postseason results push when both go out in the same run. |
| `config/push.json` | `guillotine` event. `auto_on_with`: a phone with every older event on gets it until it saves its picks again (`seen:guillotine` marker). |

**% to survive** is a fixed-seed simulation (4,000 draws). Each team's final is drawn from a normal
distribution centered on its live projection, with the Games page's position-based spread scaled by time left.
Ties at the line survive.

**Refresh:** automatic only while Monday Night Football is on (5 minutes, 30 seconds in Q4/OT). Otherwise it
uses the Refresh button. The page fetches only conferences that still have a team alive.

**Logos** (CW, 2026-11-14) live in `assets/logos/Guillotine/`, mapped in `postseason.guillotine.logos`:
- `Guillotine.png` (the wordmark) is the default, shown before week 13.
- `Round 1`–`Round 4` and `Final.png` show for weeks 13–17 on the page header. `Final.png` also heads the champion banner.
- `Guillotine G.png` is the Special Events sub-tab icon.

## Checks

```
python -m pytest tests/test_guillotine.py
node --test tests/guillotine-model.test.js
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m unittest tests/test_guillotine_browser.py
```
