"""history_player_teams.py -- one-off: each player's NFL team per week, 2019-2025 (weeks 1-17),
for lineups whose stored label lacks the team (see claude/missing-data-postseason-history.md).

Source: Sleeper weekly stats, which carry the player's team that week. Players without a stat line
that week (bye, inactive) get no row; readers fall back to the nearest week of the same season.
Only players who appear in our rosters' weekly points are kept.
Writes data/backfill/PlayerTeams_History.csv.gz (Year, Week, PlayerID, Team). Needs Sleeper
access (GitHub runner); branch only.
"""
import sys
import time

import pandas as pd
import requests

import league_config as lcfg

S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})
URLS = [  # array form carries "team"; the /v1 dict form is a fallback
    "https://api.sleeper.com/stats/nfl/{y}/{w}?season_type=regular",
    lcfg.sleeper() + "/stats/nfl/regular/{y}/{w}",
]


def fetch(y, w):
    for u in URLS:
        for _ in range(3):
            try:
                r = S.get(u.format(y=y, w=w), timeout=60)
                if r.status_code == 200:
                    d = r.json()
                    out = {}
                    items = d if isinstance(d, list) else [dict(v or {}, player_id=k) for k, v in (d or {}).items()]
                    for p in items:
                        team = p.get("team") or (p.get("player") or {}).get("team")
                        if p.get("player_id") and team:
                            out[str(p["player_id"])] = team
                    if out:
                        return out
                break
            except Exception as e:
                print(y, w, u, e)
                time.sleep(3)
    return {}


def main():
    rows = []
    for y in range(2019, 2026):
        pp = pd.read_csv(f"data/backfill/PlayerPoints_{y}.csv.gz", dtype=str, usecols=["PlayerID"])
        wanted = set(pp["PlayerID"])
        for w in range(1, 18):
            teams = fetch(y, w)
            rows += [(y, w, pid, t) for pid, t in teams.items() if pid in wanted]
            print(y, w, f"{len(teams)} with team, {sum(1 for p in teams if p in wanted)} kept", flush=True)
            time.sleep(0.2)
    if not rows:
        sys.exit("No team data returned by any source; nothing written")
    df = pd.DataFrame(rows, columns=["Year", "Week", "PlayerID", "Team"])
    df.to_csv("data/backfill/PlayerTeams_History.csv.gz", index=False)
    print(len(df), "player-weeks;", df.groupby("Year").size().to_dict())


if __name__ == "__main__":
    main()
