# Rivalries data (draft, 2026-10-28)

Clean rivalry tables built from the research workbook (`notes/NCAA180_Rivalry_Fact_Tables.xlsx`) plus a validation pass against public lists. Teams are identified by name, not by league slot. League schools use **our team names, exactly as in `data/Teams.csv`** (`FSU`, `Miami`, `UCONN`, `Citadel`…), so the tables join directly. Schools outside the league use their common NCAA name. This works for any school, NCAA or NAIA, in the league or not.

## Files
| File | What |
|---|---|
| `football.csv` | One row per school pair (505). Name, trophy, multi-team series, first/last meeting, total meetings, certainty, sources, notes. |
| `series.csv` | Multi-team trophies and series (Commander-in-Chief's, Florida Cup, Sgt. York, Big Three, Beanpot…). Pair rows point here through the `series` column. |
| `other_sports.csv` | Supplemental non-football rivalries, for teams without a strong football rival (Chris's intent). |

## Columns (football)
- `team_a`, `team_b`: team names (our names for league schools), alphabetical within the pair (one row per pair).
- `name`: the rivalry's actual name. **Blank when the series has none.** Plain "A–B" labels and descriptions ("former Big East rivalry") are not names.
- `trophy`: the head-to-head trophy only. Multi-team trophies go in `series`.
- `first_year`, `last_year`, `meetings`: real-life series history, kept **only as evidence that the rivalry exists** (Chris: never displayed, accuracy not critical). `numbers_through` says how current they are.
- `peak_intensity` (1–10): how intense the rivalry was **at its peak**, even if that was 1931 (from the workbook; blank for rows the workbook didn't have). `current_relevance` (1–10): how much it matters today. Historical rivalries count; a low current relevance doesn't mean a pair should be removed.
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
  - UConn–UCF "Civil ConFLiCT" (UConn created it in 2014; trophy from 2015) and UConn–UMass (Southwick Jug trophy, 2024). Both were pushed by the schools themselves.
  - Kennesaw State's old FCS rivals: Jacksonville State, Monmouth and Samford at 3, Charleston Southern at 2.
  - Charlotte–East Carolina.
  - Tulsa–Wichita State basketball, "Havoc in the Heartland".
- **Confirmed from school or press sources:** the Rail, Battle of the Border (Austin Peay–Murray State), the East/West and North-South BBQ Bowls, the Lowcountry Boil Bowl, the 1919 Cup, the Legacy Series, the Train Bell Trophy and Battle of the Blue.

## Row-by-row review (2026-10-28)
Every workbook row that had no outside evidence (all of the 1s and 2s) was reviewed one at a time.
- **Dropped 25 pairs with no rivalry behind them.** These were conference-mates or one-off matchups the workbook guessed at:
  - Alabama–Florida State, Auburn–Florida State, Air Force–Wyoming, Arizona State–Utah, Boise State–TCU.
  - Chattanooga–Furman, Delaware–William & Mary, East Carolina–UCF, Eastern Washington–Montana State, Florida Atlantic–South Florida.
  - Georgia Southern–Troy, Hawaii–San Diego State, Houston–Texas A&M, Houston–Tulsa.
  - Houston Christian–Incarnate Word, Houston Christian–Prairie View A&M.
  - Iowa State–Oklahoma State, Kentucky–West Virginia, Louisiana–Tulane, Oklahoma–Texas Tech, Penn State–Texas Tech.
  - San Diego State–UNLV, Troy–UAB, Tulsa–Wichita State (football; the basketball row stays), USC–Washington.
- **Kept, and moved up to a confirmed rivalry or established series:**
  - Boise State–Idaho, which has its own Wikipedia page and returns in 2031.
  - Jacksonville State–Samford, which has its own Wikipedia page.
  - Mississippi State–Southern Miss, which is renewing in 2030–31.
  - Princeton–Rutgers, which played the first college football game.
- **Kept as probable or possible, with a reason in `notes`:** Boston College–Syracuse, BYU–Boise State, James Madison–Richmond, North Dakota State–Northern Iowa, Iowa State–Northern Iowa, NC State–South Carolina, North Carolina A&T–Winston-Salem State and a few weaker neighbor pairs.
- **Added:** the Battle of the Piney Woods (Sam Houston–Stephen F. Austin), which both public lists missed.
- No candidates (certainty 1) remain.

**Update (Chris, 2026-10-28):** rivalries that faded because the schools moved to different levels of play still count. 20 of the 25 dropped pairs were restored at certainty 2 with their peak-intensity scores. Alabama–FSU, Auburn–FSU, Oklahoma–Texas Tech, Penn State–Texas Tech and USC–Washington stay out.

## Known gaps / next steps
- **Weak football histories lean on other sports (Chris: over-index rather than under-index).** `other_sports.csv` adds basketball and other rivalries for:
  - Belmont: Lipscomb and Middle Tennessee.
  - Wichita State: Tulsa, Creighton and others.
  - Northern Iowa: Drake and the Iowa Big Four.
  - Kennesaw State: Georgia State and Jacksonville State.
  - Mississippi Valley State: Jackson State and Delta State.
  - UT Martin: Austin Peay.
  - Monmouth: Saint Peter's and Rider.
  - Charlotte: Davidson.
  - Dayton: Xavier.

  Rows scored 2 are unsourced leads.
- HBCU classics beyond the ones listed here have no complete public table to check against, so they need a manual pass.
- NAIA schools: none are listed yet. The structure is ready for them.
- Wikipedia's counts lag a game or two in places. Treat `meetings` as approximate until a game-by-game source is wired in.
