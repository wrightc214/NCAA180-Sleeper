import requests
import csv
import datetime as dt
from pathlib import Path
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

    # Keep immutable biographical facts for rostered and previously valued players.
    # Do not preserve current injury/availability here or infer identity from position.
    birth_path = Path("data/PlayerBirthDates.csv")
    biographies = {}
    if birth_path.exists():
        with birth_path.open(newline="", encoding="utf-8") as f:
            biographies = {r["SleeperID"]: r for r in csv.DictReader(f)}
    candidates = {r["player_id"] for r in filtered_players} | set(biographies)
    for path, field in (("data/Rosters_Current.csv", "PlayerID"), ("data/PlayerValues_Season.csv", "SleeperID")):
        if Path(path).exists():
            with open(path, newline="", encoding="utf-8-sig") as f:
                candidates.update(r[field] for r in csv.DictReader(f))
    for pid in candidates:
        row = player_data.get(pid, {})
        position, dob = row.get("position"), row.get("birth_date")
        if position not in positions_of_interest - {"DEF"} or not dob:
            continue
        try:
            dt.date.fromisoformat(dob)
        except (ValueError, TypeError):
            continue
        biographies[pid] = {"SleeperID": pid, "Position": position, "BirthDate": dob}
    with birth_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SleeperID", "Position", "BirthDate"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(biographies[pid] for pid in sorted(biographies))

    print("✅ Player data has been exported to data/players.csv")
else:
    print(f"❌ Error: Unable to fetch player data. Status code: {response.status_code}")
