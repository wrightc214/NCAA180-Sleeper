"""history_stats.py -- one-off: weekly NFL stat lines for the scoring settings that differed
between leagues (INT thrown, DEF points/yards allowed, missed XP), 2020-2025. Lets us re-score
affected leagues on the majority system and see whether any result would change. Branch only.
Writes data/backfill/ScoringStats_2020_2025.csv.gz (PlayerID, Year, Week, Stat, Value)."""
import time

import pandas as pd
import requests

KEEP = ("pass_int", "pts_allow", "yds_allow", "xpmiss")
S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})
rows = []
for year in range(2020, 2026):
    for week in range(1, 19):
        d = None
        for i in range(3):
            try:
                d = S.get(f"https://api.sleeper.app/v1/stats/nfl/regular/{year}/{week}", timeout=60).json()
                break
            except Exception as e:
                print(year, week, e)
                time.sleep(3)
        for pid, st in (d or {}).items():
            for k, v in (st or {}).items():
                if k.startswith(KEEP) and isinstance(v, (int, float)) and v:
                    rows.append((pid, year, week, k, v))
        print(year, week, len(rows))
        time.sleep(0.2)
pd.DataFrame(rows, columns=["PlayerID", "Year", "Week", "Stat", "Value"]).to_csv(
    "data/backfill/ScoringStats_2020_2025.csv.gz", index=False, compression="gzip")
