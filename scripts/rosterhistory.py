"""
rosterhistory.py -- every player on every roster, CURRENT SEASON ONLY.

Writes data/Rosters_Players_Season.csv. Past seasons are frozen in
data/Rosters_Players_Historic.csv (never rewritten; the offseason rollover moves the
finished season there). Current season = latest Year in LeagueIDs_AllYears.csv.
Rows are sorted so an unchanged roster produces a byte-identical file (no git churn).
"""
import pandas as pd
from sleeper_wrapper import League

league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")
league_df = league_df[league_df["Year"] == league_df["Year"].max()]

all_players = []

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

    # Map user_id -> display_name
    user_map = {u["user_id"]: u["display_name"] for u in users}

    for r in rosters:
        roster_id = r["roster_id"]
        owner_id = r.get("owner_id")
        owner_name = user_map.get(owner_id, "Unknown")

        # loop through all players on this roster
        for player_id in r.get("players", []):
            all_players.append({
                "Year": year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "RosterID": roster_id,
                "OwnerID": owner_id,
                "OwnerName": owner_name,
                "PlayerID": player_id
            })

df = pd.DataFrame(all_players)
if not df.empty:
    df = df.sort_values(["LeagueName", "RosterID", "PlayerID"], key=lambda c: c if c.dtype.kind in "iuf" else c.astype(str)).reset_index(drop=True)

out_file = "data/Rosters_Players_Season.csv"
df.to_csv(out_file, index=False)
print(f"Saved {len(df)} player rows to {out_file}")
