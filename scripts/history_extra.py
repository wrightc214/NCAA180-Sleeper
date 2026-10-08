"""
history_extra.py -- one-off pulls that feed record-book / award research (branch only).
Writes only to data/backfill/. Nothing existing is modified.

  python scripts/history_extra.py

1. PlayerPoints_<year>.csv.gz : every rostered player's points, every week, every team,
   2019 -> last completed season (bench included; Started flag). Enables Lineup Skill
   (worst/best legal lineup) and Difference Maker (wins added).
2. ScoringSettings_History.csv : each league's scoring settings per season (scoring-drift check).
3. Extra2021.txt : any 2021 "NCAA" league not in LeagueIDs_AllYears.csv ("NCAA 192" question).
4. ProjectionTest.txt : do Sleeper's projections endpoints still serve past weeks, and do
   computed team totals match the app's pregame numbers (Chris's 2026 wk1 / 2020 wk6 PAC 12
   screenshots)?
"""
import gzip
import io
import json
import time

import pandas as pd
import requests

BASE = "https://api.sleeper.app/v1"
OUT = "data/backfill"
S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})


def get(url, params=None):
    for i in range(3):
        try:
            r = S.get(url if url.startswith("http") else BASE + url, params=params, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(0.12)
            return r.json()
        except Exception as e:
            if i == 2:
                print(f"ERROR {url}: {e}")
                return None
            time.sleep(2)


def leagues():
    a = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    b = pd.read_csv(f"{OUT}/LeagueIDs_2019_2020.csv", dtype=str)
    d = pd.concat([b[a.columns.intersection(b.columns)], a], ignore_index=True)
    d["LeagueName"] = d["LeagueName"].str.strip()
    return d


def player_points(lg):
    last = int(lg["Year"].max()) - 1  # current season is handled by the weekly pipeline
    for year in range(int(lg["Year"].min()), last + 1):
        rows = []
        for r in lg[lg["Year"] == str(year)].itertuples():
            for week in range(1, 19):
                for m in get(f"/league/{r.LeagueID}/matchups/{week}") or []:
                    st = set(m.get("starters") or [])
                    for pid, pts in (m.get("players_points") or {}).items():
                        rows.append((year, r.LeagueID, r.LeagueName, week, m.get("roster_id"), pid,
                                     pts, int(pid in st)))
            print(f"{year} {r.LeagueName}: {len(rows)} rows so far")
        df = pd.DataFrame(rows, columns=["Year", "LeagueID", "LeagueName", "Week", "RosterID",
                                         "PlayerID", "Points", "Started"])
        df.to_csv(f"{OUT}/PlayerPoints_{year}.csv.gz", index=False, compression="gzip")
        print(f"PlayerPoints {year}: {len(df)} rows")


def scoring(lg):
    rows = []
    for r in lg.itertuples():
        s = (get(f"/league/{r.LeagueID}") or {}).get("scoring_settings") or {}
        rows.append({"Year": r.Year, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                     "Settings": json.dumps(s, sort_keys=True)})
    pd.DataFrame(rows).to_csv(f"{OUT}/ScoringSettings_History.csv", index=False)


def extra_2021(lg):
    known = set(lg["LeagueID"])
    members = set()
    for lid in lg[lg["Year"] == "2021"]["LeagueID"]:
        for u in get(f"/league/{lid}/users") or []:
            members.add(u["user_id"])
    found = {}
    for uid in sorted(members):
        for x in get(f"/user/{uid}/leagues/nfl/2021") or []:
            if str(x.get("name", "")).upper().startswith("NCAA") and x["league_id"] not in known:
                found[x["league_id"]] = (x.get("name"), x.get("total_rosters"), x.get("previous_league_id"))
    lines = [f"Searched {len(members)} members of the 15 known 2021 leagues."]
    lines += [f"EXTRA: {lid} {n} rosters={t} previous={p}" for lid, (n, t, p) in found.items()] or ["No extra 2021 NCAA leagues found."]
    open(f"{OUT}/Extra2021.txt", "w").write("\n".join(lines) + "\n")


def projection_test(lg):
    ref = {("2026", 1): {"Arizona State": 163.89, "Colorado": 141.05, "Arizona": 102.30, "Utah": 137.83,
                         "USC": 134.02, "UCLA": 151.88, "Oregon State": 123.90, "Washington": 126.36,
                         "Washington State": 153.64, "Stanford": 139.05},
           ("2020", 6): {"Arizona State": 107.91, "Oregon": 97.86, "Arizona": 129.78, "UCLA": 135.07,
                         "USC": 130.73, "Oregon State": 138.75, "Washington State": 137.85,
                         "Colorado": 134.05, "Stanford": 103.78, "Utah": 175.53}}
    teams = pd.read_csv("data/Teams.csv", encoding="utf-8-sig")
    slot = {int(r["Roster ID"]): r.Team for _, r in teams[teams.League == "NCAA PAC 12"].iterrows()}
    out = []
    for (season, week), want in ref.items():
        lid = lg[(lg["Year"] == season) & (lg["LeagueName"] == "NCAA PAC 12")]["LeagueID"].iloc[0]
        sc = (get(f"/league/{lid}") or {}).get("scoring_settings") or {}
        ms = get(f"/league/{lid}/matchups/{week}") or []
        feeds = {
            "new": lambda: {str(x.get("player_id")): x.get("stats") or {} for x in
                            (get(f"https://api.sleeper.app/projections/nfl/{season}/{week}",
                                 [("season_type", "regular")] + [("position[]", p) for p in
                                                                 ["QB", "RB", "WR", "TE", "K", "DEF"]]) or [])},
            "v1": lambda: {str(k): v or {} for k, v in
                           (get(f"/projections/nfl/regular/{season}/{week}") or {}).items()}}
        for fname, f in feeds.items():
            proj = f()
            out.append(f"{season} wk{week} feed={fname}: {len(proj)} players")
            if not proj:
                continue
            for m in sorted(ms, key=lambda m: m["roster_id"]):
                tot = round(sum(float((proj.get(str(p)) or {}).get(k, 0) or 0) * float(w)
                                for p in m.get("starters") or [] for k, w in sc.items()
                                if isinstance(w, (int, float))), 2)
                team = slot.get(m["roster_id"])
                exp = want.get(team)
                out.append(f"  {team:18s} computed {tot:7.2f}  app {exp if exp is not None else '-':>7}  "
                           f"diff {round(tot - exp, 2) if exp is not None else '-'}")
    open(f"{OUT}/ProjectionTest.txt", "w").write("\n".join(out) + "\n")


if __name__ == "__main__":
    lg = leagues()
    projection_test(lg)
    extra_2021(lg)
    scoring(lg)
    player_points(lg)
