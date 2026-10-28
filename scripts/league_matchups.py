import pandas as pd
import time
from collections import defaultdict
from sleeper_wrapper import League
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

# -------------------------
# CURRENT YEAR (season rollover: Jan/Feb still counts as prior season)
# -------------------------
CURRENT_YEAR = lcfg.season()  # Jan-Feb = last season (config season.rollover_month)

# Load league IDs, restricted to current year only
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")
league_df = league_df[league_df["Year"] == CURRENT_YEAR]

season_matchups = []

OBSERVER_IDS = lcfg.observer_ids()  # observer accounts never count as owners
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

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    print(f"Processing {league_name} ({year})")

    league_api = League(league_id)

    try:
        rosters = league_api.get_rosters()
        users = league_api.get_users()
    except Exception as e:
        print(f"  ERROR fetching rosters/users for {league_id}: {e}")
        continue

    roster_map = {r['roster_id']: r.get('owner_id') for r in rosters}
    user_map = {u['user_id']: u['display_name'] for u in users if u['user_id'] in roster_map.values()}

    for week in range(1, 19):
        try:
            weekly_matchups = league_api.get_matchups(week)
        except Exception as e:
            print(f"  Warning: missing data for week {week} - {e}")
            continue

        if not weekly_matchups:
            continue

        matchups_by_id = defaultdict(list)
        for m in weekly_matchups:
            matchups_by_id[m['matchup_id']].append(m)

        for matchup_id, teams in matchups_by_id.items():
            if len(teams) != 2:
                teams.append({'roster_id': None, 'points': 0, 'starters': [], 'starters_points': [], 'players_points': {}})

            team1, team2 = teams

            for t, opp in [(team1, team2), (team2, team1)]:
                r_id = t['roster_id']
                owner_id = roster_map.get(r_id)
                owner_id, owner_name = resolve_owner(owner_id, league_name, user_map)

                opp_rid = opp.get('roster_id')
                opp_owner_id = roster_map.get(opp_rid)
                _, opp_name = resolve_owner(opp_owner_id, league_name, user_map)

                points_for = t.get('points', 0)
                points_against = opp.get('points', 0)

                if points_for == 0 and points_against == 0:
                    outcome = ""
                else:
                    outcome = "Win" if points_for > points_against else ("Loss" if points_for < points_against else "Tie")

                season_matchups.append({
                    "Year": year,
                    "LeagueID": league_id,
                    "LeagueName": league_name,
                    "Week": week,
                    "RosterID": r_id,
                    "OwnerID": owner_id,
                    "OwnerName": owner_name,
                    "OpponentRosterID": opp_rid,
                    "OpponentName": opp_name,
                    "PointsFor": points_for,
                    "PointsAgainst": points_against,
                    "Outcome": outcome,
                    "IsRegularSeason": week <= 11,
                    "StarterPoints": round(sum(t.get('starters_points', [])), 2) if t.get('starters_points') else None,
                    "BenchPoints": round(points_for - sum(t.get('starters_points', [])), 2) if t.get('starters_points') else None
                })

        time.sleep(0.5)

season_df = pd.DataFrame(season_matchups)
season_df.to_csv("data/Matchups_Season.csv", index=False)
print(f"Saved {len(season_df)} matchup rows to data/Matchups_Season.csv")

completed_weeks = [m["Week"] for m in season_matchups if m["Outcome"] != ""]
if completed_weeks:
    current_week = max(completed_weeks)
    week_df = season_df[season_df["Week"] == current_week]
    week_df.to_csv("data/Matchups_Week.csv", index=False)
    print(f"Saved {len(week_df)} rows for week {current_week} to data/Matchups_Week.csv")
else:
    print("No completed weeks yet — skipping Matchups_Week.csv")
