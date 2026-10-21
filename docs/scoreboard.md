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

At runtime the browser fetches one league's matchups, roster owners, users, scoring,
weekly player stats and ESPN clocks. Full player metadata refreshes at most once per
15 minutes per page session (the feed is large); it falls back visibly to the saved
map. Live data requests never write to GitHub or Discord.

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
commissioner adjustments or replacing the app score. Missing statistics for a player
with nonzero app points block that refresh. Player points use standard corrections;
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
