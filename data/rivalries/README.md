# Rivalries data (draft, 2026-10-28)

Clean rivalry tables built from the research workbook (`notes/NCAA180_Rivalry_Fact_Tables.xlsx`) plus a validation pass against public lists. Keyed by **school name**, not league slot, so it works for any school (NCAA or NAIA), in the league or not.

## Files
| File | What |
|---|---|
| `football.csv` | One row per school pair (527). Name, trophy, multi-team series, first/last meeting, total meetings, certainty, sources, notes. |
| `series.csv` | Multi-team trophies and series (Commander-in-Chief's, Florida Cup, Sgt. York, Big Three, Beanpot…). Pair rows point here through the `series` column. |
| `other_sports.csv` | Supplemental non-football rivalries, for teams without a strong football rival (Chris's intent). |
| `school_names.csv` | League team name → school name where they differ (`FSU` → `Florida State`, `Miami` → `Miami (FL)`, `UCONN` → `UConn`…). |

## Columns (football)
- `team_a`, `team_b`: school names, alphabetical within the pair (one row per pair).
- `name`: the rivalry's actual name. **Blank when the series has none.** Plain "A–B" labels and descriptions ("former Big East rivalry") are not names.
- `trophy`: the head-to-head trophy only. Multi-team trophies go in `series`.
- `first_year`, `last_year`, `meetings`: real-life series history. `numbers_through` says how current they are.
- `certainty`: confidence that the pairing is a real rivalry (scale below). `status` restates it as a word.
- `sources`, `notes`: where each fact came from, and any conflicts.

## Certainty
| Value | Status | Rule |
|---|---|---|
| 5 | confirmed | Named rivalry or trophy on Wikipedia's rivalry list, or confirmed from school or press sources (searched 2026-10-28), or Chris's call. |
| 4 | established series | On Wikipedia's rivalry or most-played lists without a name, a recognised multi-team series pair, or a workbook row with official sources and a name. |
| 3 | probable | Workbook row whose series facts come from official sources, but no rivalry label was found. |
| 2 | possible | Workbook row with some series data but no evidence of a rivalry. |
| 1 | candidate | Workbook suggestion with no data. Research lead only. |

Suggested use: show rivalry names and trophies at 4+. Use 3+ for the bowl-draw rivalry preference.

## How the numbers were chosen
The sources are ranked, and the first one with data wins:
1. Wikipedia, *List of most-played college football series in NCAA Division I*. Current through 2026-10-24 (100 series).
2. Wikipedia, *List of NCAA college football rivalry games*. Current through the 2025 season (about 410 pairs).
3. The workbook, but only where its own row says the facts came from official sources.

The workbook's 2026 meetings are kept only when one of these confirms them. Many of them are late-November games that haven't been played yet: the Iron Bowl is the clearest case.

## What the validation found in the workbook
- **Unverified rows:** 244 of 313 football rows were still "initial candidate", but 235 of them were rated 4/5 for certainty. Those ratings have been re-scored with the rule above.
- **Filler text:** "Not established in the draft" and "None identified…" have been removed.
- **Wrong rivalry names:**
  - Arkansas State–Louisiana was named "Battle for the Belt", but The Belt is Troy–South Alabama.
  - New Mexico–UTEP was named "Battle of I-10", but that is UTEP–New Mexico State.
- **Out-of-date figures:**
  - Bayou Classic: the last meeting is 2025 (the 52nd classic), giving 77 meetings.
  - Michigan–Ohio State: 121 meetings.
  - Utah–Utah State: 114 meetings, last met 2026.
- **Future games listed as played:** the 2026 Iron Bowl and other late-season 2026 games were recorded as already played.
- **Duplicate school:** Houston Baptist and Houston Christian are the same school.
- **Multi-team trophies** (Commander-in-Chief's, Michigan MAC, Sgt. York) were attached to two-team pairs. They now live in `series.csv`.
- **Added:**
  - 212 rivalries from the Wikipedia lists, including FCS, Division II and Division III.
  - UConn–UCF "Civil ConFLiCT" and UConn–UMass (Chris's calls).
  - Charlotte–East Carolina.
  - Tulsa–Wichita State basketball, "Havoc in the Heartland".
- **Confirmed from school or press sources:** the Rail, Battle of the Border (Austin Peay–Murray State), the East/West and North-South BBQ Bowls, the Lowcountry Boil Bowl, the 1919 Cup, the Legacy Series, the Train Bell Trophy and Battle of the Blue.

## Known gaps / next steps
- League teams without a 4+ football rivalry: Belmont (no football), Wichita State (no football), Charlotte, Dayton, Kennesaw State, Mississippi Valley State, Monmouth, Northern Iowa and UT Martin. For these, `other_sports.csv` or Chris's own calls fill the gap.
- HBCU classics beyond the ones listed here have no complete public table to check against, so they need a manual pass.
- NAIA schools: none are listed yet. The structure is ready for them.
- Wikipedia's counts lag a game or two in places. Treat `meetings` as approximate until a game-by-game source is wired in.
