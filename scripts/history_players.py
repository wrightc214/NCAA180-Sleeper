"""history_players.py -- one-off: every Sleeper NFL player's id, name and positions
(data/Players.csv only covers currently rostered players). Branch only.
Writes data/backfill/PlayerPositions_All.csv."""
import pandas as pd
import requests

d = requests.get("https://api.sleeper.app/v1/players/nfl", timeout=120,
                 headers={"User-Agent": "NCAA180-Sleeper/1.0"}).json()
rows = [{"PlayerID": k, "Name": v.get("full_name") or f"{v.get('first_name', '')} {v.get('last_name', '')}".strip(),
         "Position": v.get("position"), "FantasyPositions": "|".join(v.get("fantasy_positions") or []),
         "Team": v.get("team")} for k, v in d.items()]
pd.DataFrame(rows).sort_values("PlayerID").to_csv("data/backfill/PlayerPositions_All.csv", index=False)
print(len(rows), "players")
