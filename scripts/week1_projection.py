"""
week1_projection.py -- week-1 projected starter points per team, for the Professor prior.

Sleeper's projections feed keeps serving completed weeks, so this runs any time after
week-1 lineups lock (same method as history_projections.py, verified against the app:
starters x that league's scoring settings).

Writes/replaces the season's rows in data/TeamProjectionsWk1_Historic.csv:
  Year, LeagueID, LeagueName, Week, RosterID, ProjectedPts
Then rebuild the prior: python scripts/poll_prior.py
  python scripts/week1_projection.py [--year Y]     (default: current season)
CWD must be repo root.
"""
import argparse
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402

BASE = "https://api.sleeper.app/v1"
OUT = "data/TeamProjectionsWk1_Historic.csv"
S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})


def get(path):
    for i in range(3):
        try:
            r = S.get(BASE + path, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(0.1)
            return r.json()
        except Exception as e:  # noqa: BLE001
            if i == 2:
                raise SystemExit(f"ERROR {path}: {e}")
            time.sleep(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    a = ap.parse_args()
    year = a.year or max(pc.seasons())
    week = 1
    proj = get(f"/projections/nfl/regular/{year}/{week}") or {}
    if not proj:
        raise SystemExit(f"No projections for {year} week {week} yet.")
    lg = pc.leagues_all()
    lg = lg[lg["Year"] == str(year)]
    rows = []
    for r in lg.itertuples():
        sc = {k: float(v) for k, v in ((get(f"/league/{r.LeagueID}") or {}).get("scoring_settings") or {}).items()
              if isinstance(v, (int, float))}
        for m in get(f"/league/{r.LeagueID}/matchups/{week}") or []:
            tot = sum(round(sum(float((proj.get(str(p)) or {}).get(k, 0) or 0) * w for k, w in sc.items()), 2)
                      for p in (m.get("starters") or []))
            rows.append({"Year": year, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName, "Week": week,
                         "RosterID": m.get("roster_id"), "ProjectedPts": round(tot, 2)})
    new = pd.DataFrame(rows)
    old = pd.read_csv(OUT, dtype=str) if os.path.exists(OUT) else pd.DataFrame(columns=new.columns)
    old = old[old["Year"] != str(year)]
    pd.concat([old, new.astype(str)], ignore_index=True).to_csv(OUT, index=False)
    print(f"{OUT}: {year} week {week}, {len(new)} teams")


if __name__ == "__main__":
    main()
