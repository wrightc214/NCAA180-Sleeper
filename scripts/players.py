import requests
import csv
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

# Define the URL for fetching NFL player data
url = lcfg.sleeper() + "/players/nfl"

# Send a GET request to the API
response = requests.get(url)

if response.status_code == 200:
    # Parse the response JSON to get the list of players
    player_data = response.json()

    # Define the positions you're interested in
    positions_of_interest = {'QB', 'RB', 'WR', 'TE', 'K', 'DEF', 'FB'}

    # Create a list to store filtered player data
    filtered_players = []

    for player_id, player_info in player_data.items():
        if (
            'team' in player_info and player_info['team'] is not None
            and 'position' in player_info
            and player_info['position'] in positions_of_interest
        ):
            player_entry = {
                'player_id': player_id,
                'first_name': player_info.get('first_name', ''),
                'last_name': player_info.get('last_name', ''),
                'position': player_info.get('position', ''),
                'status': player_info.get('status', ''),  # Player status (e.g., Active, Injured)
                'team': player_info.get('team', '')
            }
            filtered_players.append(player_entry)

    # Always overwrite the same file in the repo
    with open("data/Players.csv", "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.DictWriter(
            csv_file,
            fieldnames=['player_id', 'first_name', 'last_name', 'position', 'status', 'team']
        )
        csv_writer.writeheader()
        csv_writer.writerows(filtered_players)

    print("✅ Player data has been exported to data/players.csv")
else:
    print(f"❌ Error: Unable to fetch player data. Status code: {response.status_code}")
