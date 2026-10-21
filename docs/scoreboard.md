# Live scoreboard

One static `reports/scoreboard.html` serves all games. Links select
`?season=2026&league=<Sleeper ID>&week=7&roster=<roster ID>` or `&game=<matchup ID>`.
No per-game or per-week HTML is generated. Saved baselines are data, not pages.

## Configuration

Edit `config/league.json`: schedule (`ccg_week`, `postseason_start_week`,
`last_regular_week`), player eligibility, uncertainty, refresh timing, contact,
API/data locations and standard scoring overrides. This is the shared-settings
starting point; existing standings/poll/postseason scripts have **not** migrated
and still use their current constants. Changing config alone does not change those
scripts yet. Never put credentials here: this file is public.

## Build and refresh

`python scripts/scoreboard_data.py` runs after the Tuesday baseline and Matchups
builder. It reads Sleeper season/week and full player metadata, including unsigned
and multi-position players. It exports the active-season index/player map and
immutable per-week projections + pregame odds. Existing frozen week files are never
overwritten. A missing baseline/completeness failure stops the builder and records
failure in the weekly job, preventing the processed-week marker.

`--offline` builds from repository sources for tests. It has older injury/team
metadata, so use the default online build before release. Each week file also keeps
snapshot NFL team information for past-week game clocks. Baseline odds remain the
original published expectations, even if a later scoring/settings decision changes.

At runtime the browser fetches one league's matchups, weekly player stats and ESPN
clocks on each refresh; league scoring, users and roster owners load once per
league/week selection. The browser never downloads Sleeper's full player feed:
`.github/workflows/scoreboard-players.yml` refreshes the saved player file
(`--players-only`, one server-side call) before each game window, and the page
re-reads that small file at most every 15 minutes. Live data requests never write
to GitHub or Discord. `--page-only` rewrites the static page shell.

Refresh: five minutes while starters are playing; 30 seconds only during Sunday-
night/Monday-night Q4 or OT. Hidden tabs pause/abort requests. HTTP errors back off;
failed refreshes retain the last good board with a STALE timestamp. No automatic
polling when no starters are live; manual Refresh remains available.

## Scoring and model

The standard is the majority saved whole-league scoring ruleset plus explicit
approved overrides (`yds_allow_550p=-7`, `xpmiss=0`). Each saved week freezes that
standard. Live scores retain Sleeper player/team adjustments and add the difference
between standard-rule and league-rule scoring from raw stats, following the existing
historical restatement method. Raw defense totals are converted to one-hot tiers.
A team-only adjustment is separately displayed. † appears only when this correction
changes a team total; Sleeper's total is displayed alongside.

A raw-stat/league-total discrepancy shows a warning rather than silently removing
commissioner adjustments or replacing the app score. A player with Sleeper points but
no stat line yet shows Sleeper's points without the correction, with a warning; the
rest of the board keeps updating. Player points use standard corrections;
manager records remain from the published standings and are labeled accordingly.
This feature does not restate season standings, poll results or draft orders.

Live expectation = actual + frozen player projection × regulation time remaining.
Remaining uncertainty = position SD × time remaining; variances add. Out/inactive
players have no remaining time; doubtful players remain eligible. OT is shown live,
but version A treats regulation remaining time/variance as zero. These are estimates,
not calibrated in-game probabilities. Frozen Tuesday matchup odds remain separate.

Pregame benches show available players by position; after kickoff show up to five
helpful/close-call players (within two projected points of a replaceable starter).
Zero/bye/out entries collapse. The validation banner asks users to ping @Wrightc214.

## Limits and release

This launch supports regular-season pairings only. At CCG week it refuses fictional
Sleeper postseason pairings; real cross-league postseason matchup input is a later
build. Available history starts at the first valid saved baseline (currently week 5).
The all-game Matchups listing remains prebuilt; game links load live on request.
Old weekly awards/archive pages are unchanged. Their migration to reusable static
shells is separate work.

Run checks:

```
node --test tests/scoreboard-core.test.js
python -m unittest discover -s tests -p 'test_scoreboard*.py'
```

Python checks compare JavaScript scoring to an independent Python sum across all
stored 2026 game-time projection stat lines and league scoring rules. A recorded
public week-six fixture also checks all 12 Big Sky scores. Model tests cover clocks,
OT, flex/multi-position eligibility, inactive/empty slots, ties and close-call benches.
Browser checks cover desktop/400px mobile, pregame/live/final, selection,
and HTTP 429/stale preservation. Hidden-tab pause is implemented but not automated
in those tests. Enable browser checks with `RUN_SCOREBOARD_BROWSER_TESTS=1` and
optionally `SCOREBOARD_BROWSER=/path/to/chromium`. No GitHub workflow or Discord
post is needed for local checks.

Merge/publishing requires Chris's approval. Rollback: revert the scoreboard commit;
existing data/poll/standings behavior is unchanged. Public Pages will serve the new
page after the branch is merged and deployed; a branch URL is source, not a live page.

## Conference overview

The bare `scoreboard.html` URL is now the conference overview: a responsive grid
of every league's matchups, using the repository's league colors and team identities.
Week and conference selectors update immediately. Clicking a matchup opens the same
static page with `game` in its URL, preserving the existing player-detail view and
Matchups links. The return link restores the overview's week/conference filter.
`--page-only` also writes `data/scoreboard/leagues.json` from the league palette file.
The shared navigation now includes Scoreboard on existing and future report pages.

The overview fetches NFL stats and ESPN clocks once per refresh, then processes
league matchup/scoring requests with at most four league workers. Scoring settings
are cached for the page session. No full Sleeper player feed is requested. It uses
the existing core player/team scoring and uncertainty calculations. Final cards show
frozen Tuesday odds for the exact roster pairing, not the final 100/0 probability;
unstarted games also show Tuesday odds. Started, unfinished games show live estimates.
Unknown statuses or incomplete live stat lines suppress the affected live estimate.
A dash means odds are unavailable. Scores marked † have the existing standard-rule
correction; open the game for the underlying Sleeper totals.

Overview refresh is five minutes until the selected matchups are final, including
between game windows. Hidden tabs abort and resume on visibility. Selection changes
abort obsolete requests. A failed league retains its prior scores with its own STALE
label/timestamp; a shared NFL-feed failure marks every visible conference stale.
Failures retry with bounded backoff. There are no new workflows or Discord messages.
Postseason pairing support remains separate work; this view serves supported regular
season weeks only. Revert the overview commit to restore the prior single-game entry.

Additional checks: `node --test tests/scoreboard*.test.js`; browser opt-in also runs
`test_scoreboard_overview_browser.py` for the full grid, shared-fetch counts, mobile,
league/week filters, final/live labels, partial failure and overview/game return links.
