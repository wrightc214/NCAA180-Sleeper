import pandas as pd
import requests
import os
import sys
import time
import json
import argparse
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "data/Scores_Season.csv"
LEAGUE_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"

# Same source NFLgameStatus.py uses for live-refresh — the one authoritative
# "what NFL week is it" signal in this repo. score_details.py used to guess
# the current week from its own fetched player points (whichever week had
# any nonzero total); that heuristic silently broke whenever a handful of
# the 270 (15 leagues x 18 weeks) requests it fired every run got
# rate-limited or timed out, since a failed fetch just got skipped instead
# of retried, and one bad week could throw off the "current week" pick for
# every league at once.
ESPN_SCOREBOARD_URL = lcfg.espn()

# When live-refresh.yml runs, NFLgameStatus.py (an earlier step in the same
# job, same runner) already hit ESPN and wrote this. Reuse it instead of
# hitting ESPN a second time in the same job. update-leagues.yml never runs
# NFLgameStatus.py first, so this file won't exist there and we fall back
# to calling ESPN directly.
NFL_STATUS_FILE = "nfl_status.json"

# How many trailing weeks to (re)fetch, including the current one. The NFL
# issues stat corrections (reassigned fumbles/TDs, etc.) for up to a couple
# days after a game, so the current week alone isn't enough — but refetching
# the ENTIRE season to date every run (the old behavior) is pure waste once
# you're a few weeks in, and it's what turned 15 leagues into 270 requests
# a run. 2 covers "this week + last week" and is cheap to widen if a later
# correction window turns out to need it.
CORRECTION_WINDOW_WEEKS = 2

EXPECTED_COLUMNS = [
    "LeagueYear", "league_id", "weekNum", "roster_id", "lookupID",
    "player_id", "is_starter", "lineup_slot", "points", "label",
]

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

# -------------------------
# ARGUMENT PARSER
# -------------------------
parser = argparse.ArgumentParser(description="Fetch Sleeper league scores.")
parser.add_argument("--week", type=int, help="Specify NFL week number to fetch (1-18)")
args = parser.parse_args()

# -------------------------
# DETERMINE CURRENT NFL YEAR (adjust for Jan/Feb rollover)
# -------------------------
CURRENT_YEAR = lcfg.season()  # Jan-Feb = last season (config season.rollover_month)
print(f"Current NFL Year: {CURRENT_YEAR}")

# -------------------------
# DETERMINE CURRENT NFL WEEK (authoritative, from ESPN — not guessed)
# -------------------------
def get_current_nfl_week():
    if args.week:
        return args.week

    if os.path.exists(NFL_STATUS_FILE):
        try:
            with open(NFL_STATUS_FILE) as f:
                week = json.load(f).get("week_number")
            if week:
                print(f"Using week from {NFL_STATUS_FILE} (written earlier in this job) — skipping a redundant ESPN call")
                return int(week)
        except Exception as e:
            print(f"Could not read {NFL_STATUS_FILE} ({e}) — falling back to ESPN directly")

    try:
        resp = requests.get(ESPN_SCOREBOARD_URL, timeout=10)
        resp.raise_for_status()
        week = resp.json().get("week", {}).get("number")
        if not week:
            raise ValueError("ESPN response had no week.number")
        return int(week)
    except Exception as e:
        print(f"FATAL: could not determine current NFL week from ESPN: {e}")
        sys.exit(1)

CURRENT_WEEK = get_current_nfl_week()
FETCH_FROM_WEEK = max(1, CURRENT_WEEK - CORRECTION_WINDOW_WEEKS + 1)
print(f"Current NFL Week: {CURRENT_WEEK} (fetching weeks {FETCH_FROM_WEEK}-{CURRENT_WEEK}; "
      f"earlier weeks are assumed final and are left untouched)")

# -------------------------
# LOAD PLAYERS DATA
# -------------------------
if not os.path.exists(PLAYERS_FILE):
    raise FileNotFoundError(f"Missing Players file: {PLAYERS_FILE}")

players_df = pd.read_csv(PLAYERS_FILE, dtype=str)
players_df["label"] = (
    players_df["first_name"].fillna("") + " " +
    players_df["last_name"].fillna("") + ", " +
    players_df["position"].fillna("") + " (" +
    players_df["team"].fillna("") + ")"
)
player_label_map = pd.Series(players_df.label.values, index=players_df.player_id).to_dict()

# -------------------------
# LOAD LEAGUE IDs
# -------------------------
if not os.path.exists(LEAGUE_FILE):
    raise FileNotFoundError(f"Missing LeagueID file: {LEAGUE_FILE}")

league_df = pd.read_csv(LEAGUE_FILE, dtype=str)

# -------------------------
# LOAD EXISTING SCORES
# -------------------------
if os.path.exists(CSV_PATH):
    try:
        existing_df = pd.read_csv(CSV_PATH, dtype=str)
        print(f"Loaded existing data: {len(existing_df)} rows")
        if list(existing_df.columns) != EXPECTED_COLUMNS:
            print("Existing file uses an old schema (pre bench-points fix) — discarding it. "
                  "Scores_Season.csv is fully refetched from the API every run, so nothing is lost.")
            existing_df = pd.DataFrame()
        else:
            # Loaded with dtype=str for safe key handling below, but "points"
            # needs to be numeric before it's concatenated with new_df's
            # numeric column — otherwise a mixed str/float object column
            # makes any later groupby().sum() on it silently do string
            # concatenation instead of addition.
            existing_df["points"] = pd.to_numeric(existing_df["points"], errors="coerce").fillna(0)
    except pd.errors.EmptyDataError:
        print(f"{CSV_PATH} exists but is empty. Starting fresh.")
        existing_df = pd.DataFrame()
else:
    existing_df = pd.DataFrame()

# -------------------------
# HELPER: Normalize Key Columns
# -------------------------
def normalize_keys(df):
    if df.empty:
        return df
    for col in ["LeagueYear", "league_id", "roster_id", "weekNum"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    return df

# -------------------------
# FUNCTION TO FETCH SCORES
# Captures the FULL roster (starters + bench) so bench points are actually
# recoverable. Sleeper's matchup "points" field is starters-only, so bench
# points can never be derived from Matchups_*.csv — they only exist here,
# per player, from players_points.
# -------------------------
def fetch_matchups(league_id, week_num):
    url = f"{lcfg.sleeper()}/league/{league_id}/matchups/{week_num}"
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp.json() or []
        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    print(f"  FAILED league {league_id}, week {week_num} after {MAX_RETRIES} attempts: {last_err}")
    return None  # distinguish "failed" from "fetched, genuinely empty"

def get_weekly_scores(league_id, league_year, from_week, up_to_week):
    results = []
    failures = []

    for week_num in range(from_week, up_to_week + 1):
        matchups = fetch_matchups(league_id, week_num)
        if matchups is None:
            failures.append(week_num)
            continue

        print(f"  Week {week_num}: {len(matchups)} matchups")

        for matchup in matchups:
            roster_id = matchup.get("roster_id", "")
            starters = matchup.get("starters", []) or []
            player_points = matchup.get("players_points", {}) or {}
            lookup_id = f"{league_id}{roster_id}"

            starter_slot = {str(pid): idx + 1 for idx, pid in enumerate(starters)}

            for player_id, points in player_points.items():
                pid = str(player_id)
                points = float(points) if points not in (None, "", "null") else 0.0
                results.append({
                    "LeagueYear": league_year,
                    "league_id": league_id,
                    "weekNum": week_num,
                    "roster_id": roster_id,
                    "lookupID": lookup_id,
                    "player_id": pid,
                    "is_starter": pid in starter_slot,
                    "lineup_slot": starter_slot.get(pid),
                    "points": points,
                    "label": player_label_map.get(pid, ""),
                })
    return results, failures

# -------------------------
# FETCH DATA FOR CURRENT YEAR ONLY
# -------------------------
current_leagues = league_df.loc[league_df["Year"].astype(int) == CURRENT_YEAR, "LeagueID"].tolist()
if not current_leagues:
    raise ValueError(f"No leagues found for {CURRENT_YEAR} in {LEAGUE_FILE}")

all_data = []
all_failures = {}  # league_id -> [week_num, ...]
for league_id in current_leagues:
    print(f"Fetching scores for league {league_id}")
    league_scores, failures = get_weekly_scores(
        league_id, league_year=CURRENT_YEAR, from_week=FETCH_FROM_WEEK, up_to_week=CURRENT_WEEK
    )
    print(f"   -> {len(league_scores)} rows fetched")
    all_data.extend(league_scores)
    if failures:
        all_failures[league_id] = failures

if all_failures:
    print("\nWARNING: the following league/week fetches failed even after retries "
          "and were skipped this run (existing data for them, if any, is left as-is "
          "rather than being overwritten with zeros):")
    for lid, weeks in all_failures.items():
        print(f"  league {lid}: weeks {weeks}")

if not all_data:
    print("No new data fetched. Exiting without changes.")
    exit()

new_df = pd.DataFrame(all_data)
new_df["points"] = pd.to_numeric(new_df["points"], errors="coerce").fillna(0)

# -------------------------
# NORMALIZE BEFORE MERGE
# -------------------------
new_df = normalize_keys(new_df)
if not existing_df.empty:
    existing_df = normalize_keys(existing_df)

# -------------------------
# MERGE & DEDUPLICATE BY KEY
# Concat order matters: existing_df first, new_df second, keep="last" so a
# freshly fetched row always wins over a stale one for the same key. Rows
# that failed to fetch this run (see all_failures above) simply have no
# corresponding new_df entry, so their existing_df row survives untouched
# instead of being dropped or zeroed.
# -------------------------
combined_df = pd.concat([existing_df, new_df], ignore_index=True)
combined_df.drop_duplicates(
    subset=["league_id", "roster_id", "weekNum", "player_id"],
    keep="last",
    inplace=True
)

# -------------------------
# FINAL CLEANUP — remove exact full-row duplicates
# -------------------------
before = len(combined_df)
combined_df = combined_df.drop_duplicates(keep="last").reset_index(drop=True)
after = len(combined_df)
print(f"Final cleanup removed {before - after:,} exact duplicates")

# -------------------------
# DROP UNPLAYED FUTURE WEEKS before saving Scores_Season.csv.
# These are pre-generated zero-point placeholder rows for weeks that
# haven't happened yet — pure bloat with no player-level content, unlike
# Matchups_Season.csv which intentionally keeps them for the schedule view.
# CURRENT_WEEK now comes from ESPN (see top of file), not a heuristic over
# this same data, so this drop is no longer self-referential. Note this
# ceiling is independent of FETCH_FROM_WEEK above: weeks older than the
# fetch window are simply never re-fetched, and existing_df rows for them
# pass through this filter untouched since they're still <= CURRENT_WEEK.
# -------------------------
combined_df["weekNum"] = combined_df["weekNum"].astype(int)
dropped = combined_df[combined_df["weekNum"] > CURRENT_WEEK]
if len(dropped):
    print(f"Dropping {len(dropped):,} unplayed future-week rows (weeks > {CURRENT_WEEK})")
combined_df = combined_df[combined_df["weekNum"] <= CURRENT_WEEK].copy()

# -------------------------
# SORT & SAVE
# -------------------------
combined_df.sort_values(
    by=["LeagueYear", "league_id", "roster_id", "weekNum", "is_starter", "lineup_slot"],
    ascending=[True, True, True, True, False, True],
    inplace=True
)
combined_df.to_csv(CSV_PATH, index=False)

print(f"\nScores_Season.csv updated for {CURRENT_YEAR}")
print(f"Total rows after update: {len(combined_df)}")

# -------------------------
# WEEK SIDECAR
# -------------------------
this_week_df = combined_df[combined_df["weekNum"] == CURRENT_WEEK]
this_week_df.to_csv("data/Scores_Week.csv", index=False)
print(f"Saved {len(this_week_df)} rows for week {CURRENT_WEEK} to data/Scores_Week.csv")
