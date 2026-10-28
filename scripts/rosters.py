import pandas as pd
from sleeper_wrapper import League
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

# --- Load league IDs ---
league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")

# --- Detect current year (or hardcode if needed) ---
current_year = lcfg.season()

# --- Filter to current year only ---
current_leagues = league_df[league_df['Year'] == current_year]

# --- Load player data for enrichment ---
players_df = pd.read_csv("data/Players.csv")

# Create lookup dictionary for quick reference
player_lookup = {
    str(row["player_id"]): {
        "FullName": f"{row.get('first_name', '')} {row.get('last_name', '')}".strip(),
        "Position": row.get("position", ""),
        "Team": row.get("team", "")
    }
    for _, row in players_df.iterrows()
}

all_players = []

# --- Loop through current leagues and fetch rosters ---
for idx, row in current_leagues.iterrows():
    league_id = row["LeagueID"]
    league_name = row["LeagueName"]

    print(f"Processing current roster for {league_name}")

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

        # Current players on this roster
        for player_id in r.get("players", []):
            player_info = player_lookup.get(str(player_id), {
                "FullName": "",
                "Position": "",
                "Team": ""
            })

            all_players.append({
                "Year": current_year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "RosterID": roster_id,
                "OwnerID": owner_id,
                "OwnerName": owner_name,
                "PlayerID": player_id,
                "FullName": player_info["FullName"],
                "Position": player_info["Position"],
                "Team": player_info["Team"]
            })

# --- Convert to DataFrame ---
df = pd.DataFrame(all_players)

# --- Save CSV ---
out_file = "data/Rosters_Current.csv"
df.to_csv(out_file, index=False)
print(f"✅ Saved {len(df)} player rows (with player details) to {out_file}")
