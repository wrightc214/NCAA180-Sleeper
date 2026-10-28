"""history_players.py -- one-off: every Sleeper NFL player's id, name and positions
(data/Players.csv only covers currently rostered players). Branch only.
Writes data/backfill/PlayerPositions_All.csv. Hand-kept rows in data/backfill/PlayerPositions_Manual.csv
(empty slot "0", retired DEF ids like OAK, the UNKNOWN default) are merged in and win over Sleeper's."""
import pandas as pd
import requests
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

d = requests.get(lcfg.sleeper() + "/players/nfl", timeout=120,
                 headers={"User-Agent": "NCAA180-Sleeper/1.0"}).json()
rows = [{"PlayerID": k, "Name": v.get("full_name") or f"{v.get('first_name', '')} {v.get('last_name', '')}".strip(),
         "Position": v.get("position"), "FantasyPositions": "|".join(v.get("fantasy_positions") or []),
         "Team": v.get("team")} for k, v in d.items()]
manual = pd.read_csv("data/backfill/PlayerPositions_Manual.csv", dtype=str).drop(columns="Note")
out = pd.concat([manual, pd.DataFrame(rows)], ignore_index=True).drop_duplicates("PlayerID", keep="first")
out.sort_values("PlayerID").to_csv("data/backfill/PlayerPositions_All.csv", index=False)
print(len(rows), "players")
