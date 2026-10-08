"""
history_projections.py -- backfill PREGAME projections for every past week (branch only).

Sleeper's projections feed still serves completed weeks, and team totals computed from it
(starters x that league's scoring settings) matched the app's pregame numbers exactly for
2026 wk1 and 2020 wk6 PAC 12 (data/backfill/ProjectionTest.txt, 2026-10-07).

Writes data/backfill/:
  ProjStarters_<year>.csv.gz : Year, LeagueID, LeagueName, Week, RosterID, Slot, PlayerID,
                               ProjPts (league scoring), ProjPPR (feed's own PPR number)
  TeamProjections_History.csv: Year, LeagueID, LeagueName, Week, RosterID, ProjectedPts
Seasons: earliest league season -> last completed season.
"""
import time

import pandas as pd
import requests

BASE = "https://api.sleeper.app/v1"
OUT = "data/backfill"
S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})


def get(url):
    for i in range(3):
        try:
            r = S.get(url if url.startswith("http") else BASE + url, timeout=60)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(0.1)
            return r.json()
        except Exception as e:
            if i == 2:
                print(f"ERROR {url}: {e}")
                return None
            time.sleep(3)


def main():
    a = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    b = pd.read_csv(f"{OUT}/LeagueIDs_2019_2020.csv", dtype=str)
    lg = pd.concat([b[a.columns.intersection(b.columns)], a], ignore_index=True)
    lg["LeagueName"] = lg["LeagueName"].str.strip()
    teams = []
    for year in range(int(lg["Year"].min()), int(lg["Year"].max())):
        ls = lg[lg["Year"] == str(year)]
        scoring = {r.LeagueID: (get(f"/league/{r.LeagueID}") or {}).get("scoring_settings") or {}
                   for r in ls.itertuples()}
        rows = []
        for week in range(1, 19):
            proj = get(f"/projections/nfl/regular/{year}/{week}") or {}
            if not proj:
                print(f"{year} wk{week}: no projections")
                continue
            for r in ls.itertuples():
                sc = {k: float(v) for k, v in scoring[r.LeagueID].items() if isinstance(v, (int, float))}
                for m in get(f"/league/{r.LeagueID}/matchups/{week}") or []:
                    tot = 0.0
                    for i, pid in enumerate(m.get("starters") or []):
                        st = proj.get(str(pid)) or {}
                        pts = round(sum(float(st.get(k, 0) or 0) * w for k, w in sc.items()), 2)
                        tot += pts
                        rows.append((year, r.LeagueID, r.LeagueName, week, m.get("roster_id"), i + 1,
                                     pid, pts, st.get("pts_ppr")))
                    teams.append({"Year": year, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                                  "Week": week, "RosterID": m.get("roster_id"), "ProjectedPts": round(tot, 2)})
            print(f"{year} wk{week}: {len(rows)} starter rows")
        pd.DataFrame(rows, columns=["Year", "LeagueID", "LeagueName", "Week", "RosterID", "Slot",
                                    "PlayerID", "ProjPts", "ProjPPR"]).to_csv(
            f"{OUT}/ProjStarters_{year}.csv.gz", index=False, compression="gzip")
    pd.DataFrame(teams).to_csv(f"{OUT}/TeamProjections_History.csv", index=False)
    print(f"TeamProjections_History: {len(teams)} rows")


if __name__ == "__main__":
    main()
