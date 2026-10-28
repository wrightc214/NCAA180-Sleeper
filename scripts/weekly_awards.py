import pandas as pd
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)
import standard_results  # noqa: E402 (standard-scoring scores/results)

# Combined cross-league weekly awards (NCAA180-wide superlatives).
# Each of the 15 individual leagues already gets its own recap via Sleeper,
# so this only needs to crown one winner per award across all 180 teams.
#
# Output accumulates across the season (like Matchups_Season.csv /
# Scores_Season.csv) rather than being overwritten each run, so the full
# season's award history builds up week over week. When previous seasons
# get backfilled later, that becomes WeeklyAwards_Historic.csv following
# the same Historic/Season/Week split as the rest of the pipeline.

CURRENT_YEAR = lcfg.season()  # Jan-Feb = last season (config season.rollover_month)

INPUT_PATH = "data/Matchups_Week.csv"
SCORES_PATH = "data/Scores_Week.csv"
OUTPUT_PATH = "data/WeeklyAwards_Season.csv"

df = standard_results.apply(pd.read_csv(INPUT_PATH, dtype=str))  # standard scores; 2026+ results on them
df["PointsFor"] = df["PointsFor"].astype(float)
df["PointsAgainst"] = df["PointsAgainst"].astype(float)
df["Week"] = df["Week"].astype(int)
# Matchups_*.csv's own BenchPoints column is structurally broken (always ~0 —
# see notes below) and unused here; drop it so it can't collide with the
# real bench total computed from Scores_Week.csv further down.
df = df.drop(columns=["BenchPoints"], errors="ignore")

week = int(df["Week"].iloc[0])

# Exclude unplayed rows and empty/vacant rosters from award eligibility.
played = df[(df["Outcome"] != "") & (df["OwnerName"] != "Vacant")].copy()

awards = []

def add_award(name, row, value, value_label):
    awards.append({
        "Year": CURRENT_YEAR,
        "Week": week,
        "Award": name,
        "Team": row["OwnerName"],
        "League": row["LeagueName"],
        "Opponent": row["OpponentName"],
        "Value": round(value, 2),
        "ValueLabel": value_label,
    })

if not played.empty:
    # Highest / lowest score
    top = played.loc[played["PointsFor"].idxmax()]
    add_award("HighestScore", top, top["PointsFor"], "points")

    bottom = played.loc[played["PointsFor"].idxmin()]
    add_award("LowestScore", bottom, bottom["PointsFor"], "points")

    # Closest game / biggest blowout — dedupe matchup pairs (each game has two rows)
    played["Margin"] = (played["PointsFor"] - played["PointsAgainst"]).abs()
    played["MatchupKey"] = played.apply(
        lambda r: (str(r["LeagueID"]), tuple(sorted([str(r["RosterID"]), str(r["OpponentRosterID"])]))),
        axis=1,
    )
    unique_games = played.drop_duplicates(subset="MatchupKey")

    closest = unique_games.loc[unique_games["Margin"].idxmin()]
    add_award("ClosestGame", closest, closest["Margin"], "point margin")

    blowout = unique_games.loc[unique_games["Margin"].idxmax()]
    add_award("BiggestBlowout", blowout, blowout["Margin"], "point margin")

    # Bad beat (highest score in a loss) / lucky win (lowest score in a win)
    losses = played[played["Outcome"] == "Loss"]
    if not losses.empty:
        bad_beat = losses.loc[losses["PointsFor"].idxmax()]
        add_award("BadBeat", bad_beat, bad_beat["PointsFor"], "points (lost anyway)")

    wins = played[played["Outcome"] == "Win"]
    if not wins.empty:
        lucky_win = wins.loc[wins["PointsFor"].idxmin()]
        add_award("LuckyWin", lucky_win, lucky_win["PointsFor"], "points (won anyway)")

    # Bench tragedy — most bench points left on the table.
    # Sourced from Scores_Week.csv (player-level, is_starter flag), not
    # Matchups_*.csv — Sleeper's matchup "points" field is starters-only,
    # so real bench totals only exist at the player-score level.
    try:
        scores = pd.read_csv(SCORES_PATH, dtype=str)
        if "is_starter" not in scores.columns:
            print(f"Skipping BenchTragedy: {SCORES_PATH} is on the old schema "
                  f"(no is_starter column) — rerun score_details.py to refresh it.")
            scores = pd.DataFrame()
    except FileNotFoundError:
        scores = pd.DataFrame()

    if not scores.empty:
        scores["points"] = pd.to_numeric(scores["points"], errors="coerce").fillna(0)
        scores["is_starter"] = scores["is_starter"].astype(str) == "True"
        bench_totals = (
            scores[~scores["is_starter"]]
            .groupby(["league_id", "roster_id"])["points"]
            .sum()
            .reset_index()
            .rename(columns={"points": "BenchPoints"})
        )
        enriched = played.merge(
            bench_totals,
            left_on=["LeagueID", "RosterID"],
            right_on=["league_id", "roster_id"],
            how="inner",
        )
        if not enriched.empty:
            tragedy = enriched.loc[enriched["BenchPoints"].idxmax()]
            add_award("BenchTragedy", tragedy, tragedy["BenchPoints"], "bench points left on the bench")

new_awards_df = pd.DataFrame(awards)

# Merge with existing season history instead of overwriting it. Keyed on
# (Year, Week, Award) so rerunning the same week (e.g. a late score
# correction from Sleeper) updates that week's row rather than duplicating it.
try:
    existing_df = pd.read_csv(OUTPUT_PATH)
except FileNotFoundError:
    existing_df = pd.DataFrame()

combined_df = pd.concat([existing_df, new_awards_df], ignore_index=True)
if not combined_df.empty:
    combined_df.drop_duplicates(subset=["Year", "Week", "Award"], keep="last", inplace=True)
    combined_df.sort_values(by=["Year", "Week", "Award"], inplace=True)

combined_df.to_csv(OUTPUT_PATH, index=False)
print(f"Week {week}: wrote/updated {len(new_awards_df)} awards. "
      f"{OUTPUT_PATH} now has {len(combined_df)} rows total across the season.")
print(new_awards_df.to_string(index=False))
