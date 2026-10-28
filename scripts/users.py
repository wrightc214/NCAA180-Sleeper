import pandas as pd
from sleeper_wrapper import League, User
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

user_id = int(lcfg.lookup_user_id())

CURRENT_YEAR = lcfg.season()  # Jan-Feb = last season (config season.rollover_month)

OBSERVER_IDS = lcfg.observer_ids()
LINKOFTIME_ID = "460518714907815936"
LINKOFTIME_REAL_LEAGUE = "NCAA BIG 10"

ORPHAN = "Orphan"

def resolve_owner(owner_id, league_name, user_map):
    """Returns (OwnerID, OwnerName). Every roster without a real, active coach is
    collapsed to ("Orphan", "Orphan") so coach-level stats lump them together:
      - no owner / observer account
      - linkoftime1 caretaker rosters (any league except his real Big Ten team)
      - deleted Sleeper accounts (display name starts with "DELETED")
    Team-level identity stays on LeagueID + RosterID, so orphan teams never merge."""
    if owner_id is None or str(owner_id) in OBSERVER_IDS:
        return ORPHAN, ORPHAN
    if str(owner_id) == LINKOFTIME_ID and league_name != LINKOFTIME_REAL_LEAGUE:
        return ORPHAN, ORPHAN
    name = user_map.get(owner_id, "Unknown")
    if str(name).upper().startswith("DELETED"):
        return ORPHAN, ORPHAN
    return owner_id, name

# -------------------------
# REGULAR-SEASON RECORD (weeks 1-11 only) FROM MATCHUPS DATA
# -------------------------
matchups_df = pd.read_csv("data/Matchups_Season.csv", dtype=str)
matchups_df["PointsFor"] = matchups_df["PointsFor"].astype(float)
matchups_df["PointsAgainst"] = matchups_df["PointsAgainst"].astype(float)

regular_season = matchups_df[matchups_df["IsRegularSeason"].astype(str) == "True"]

standings_agg = regular_season.groupby(["LeagueID", "RosterID"]).agg(
    Wins=("Outcome", lambda x: (x == "Win").sum()),
    Losses=("Outcome", lambda x: (x == "Loss").sum()),
    PointsFor=("PointsFor", "sum"),
    PointsAgainst=("PointsAgainst", "sum")
).reset_index()

# -------------------------
# ROSTER/DIVISION METADATA (not available from Matchups data)
# -------------------------
all_rosters = []
leagues = User(user_id).get_all_leagues("nfl", CURRENT_YEAR)
for league in leagues:
    league_id = str(league["league_id"])
    league_name = league.get("name")
    division1 = league.get("metadata", {}).get("division_1")
    division2 = league.get("metadata", {}).get("division_2")

    league_api = League(league_id)
    rosters = league_api.get_rosters()
    users = league_api.get_users()
    user_map = {u["user_id"]: u["display_name"] for u in users}

    for r in rosters:
        division_num = r.get("settings", {}).get("division")
        if division_num == 1:
            division_name = division1
        elif division_num == 2:
            division_name = division2
        else:
            division_name = None

        owner_id, owner_name = resolve_owner(r.get("owner_id"), league_name, user_map)
        all_rosters.append({
            "Year": CURRENT_YEAR,
            "LeagueID": league_id,
            "LeagueName": league_name,
            "RosterID": str(r["roster_id"]),
            "OwnerID": owner_id,
            "OwnerName": owner_name,
            "Division": division_num,
            "DivisionName": division_name
        })

meta_df = pd.DataFrame(all_rosters)

# -------------------------
# MERGE METADATA WITH REGULAR-SEASON RECORD
# -------------------------
merged = meta_df.merge(standings_agg, on=["LeagueID", "RosterID"], how="left")
merged[["Wins", "Losses"]] = merged[["Wins", "Losses"]].fillna(0).astype(int)
merged[["PointsFor", "PointsAgainst"]] = merged[["PointsFor", "PointsAgainst"]].fillna(0).round(2)

out_file = "data/Standings_Season.csv"
merged.to_csv(out_file, index=False)
print(f"Saved {len(merged)} roster rows (regular season, weeks 1-11) to {out_file}")
