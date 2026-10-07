"""
history_backfill.py -- one-off pull of seasons that predate the NCAAranks account
(2019-2020; LeagueIDs_AllYears.csv starts at 2021 because league_ids.py only sees leagues
that account belongs to).

Writes ONLY to data/backfill/ (review first; merging into the _Historic files is a separate,
deliberate step). Nothing existing is modified.

  python scripts/history_backfill.py 2020 2019

1. Discover leagues: walk previous_league_id back from every league of the earliest year in
   LeagueIDs_AllYears.csv, then widen the net by searching every member of the found leagues
   for other leagues named "NCAA ..." in the same season (catches leagues that later folded).
2. Per league, same schemas as the existing _Historic files:
   LeagueIDs, Matchups, Scores (starters), Standings, Rosters_Players (final roster),
   Transactions, Drafts, DraftPicks.
3. data/backfill/Discovery.txt logs how each league was found, and anything odd.

Owner names use the same orphan rules as league_matchups.py, except the observer / caretaker
accounts are applied as-is (they may not have existed yet). IsRegularSeason = week <= 11,
matching the current definition; check against older schedules before relying on it.
"""
import os
import sys
import time
from collections import defaultdict

import pandas as pd
import requests

BASE = "https://api.sleeper.app/v1"
OUT = "data/backfill"
S = requests.Session()
S.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})
OBSERVER_IDS = {"731808894699028480"}
LINKOFTIME_ID = "460518714907815936"
LINKOFTIME_REAL_LEAGUE = "NCAA BIG 10"
log = []


def get(path, tries=3):
    for i in range(tries):
        try:
            r = S.get(BASE + path, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            time.sleep(0.15)
            return r.json()
        except Exception as e:
            if i == tries - 1:
                log.append(f"ERROR {path}: {e}")
                return None
            time.sleep(2)


def note(msg):
    print(msg)
    log.append(msg)


def discover(years):
    ids = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    first = str(min(int(y) for y in ids["Year"]))
    frontier = list(ids[ids["Year"] == first]["LeagueID"])
    found = {}  # league_id -> league json
    how = {}
    # 1) walk previous_league_id
    for lid in frontier:
        cur = get(f"/league/{lid}")
        while cur and cur.get("previous_league_id") not in (None, "", "0"):
            prev = get(f"/league/{cur['previous_league_id']}")
            if not prev:
                break
            if prev["season"] in years and prev["league_id"] not in found:
                found[prev["league_id"]] = prev
                how[prev["league_id"]] = f"previous_league_id of {cur['name']} {cur['season']}"
            cur = prev
    # 2) widen via members' other NCAA leagues in the same season
    for season in years:
        members = set()
        for lid, lg in list(found.items()):
            if lg["season"] != season:
                continue
            for u in get(f"/league/{lid}/users") or []:
                members.add(u["user_id"])
        note(f"{season}: {sum(1 for l in found.values() if l['season'] == season)} leagues by chain; "
             f"searching {len(members)} members for others")
        for uid in sorted(members):
            for lg in get(f"/user/{uid}/leagues/nfl/{season}") or []:
                if str(lg.get("name", "")).upper().startswith("NCAA") and lg["league_id"] not in found:
                    found[lg["league_id"]] = lg
                    how[lg["league_id"]] = f"member search (user {uid})"
    rows = []
    for lid, lg in found.items():
        md = lg.get("metadata") or {}
        rows.append({"Year": int(lg["season"]), "LeagueID": lid, "LeagueName": lg.get("name"),
                     "Division1": md.get("division_1"), "Division2": md.get("division_2"),
                     "RosterPositions": ",".join(lg.get("roster_positions") or []),
                     "PreviousLeagueID": lg.get("previous_league_id"), "TotalRosters":
                     (lg.get("total_rosters")), "Status": lg.get("status"), "FoundBy": how[lid]})
    df = pd.DataFrame(rows).sort_values(["Year", "LeagueName"])
    for y, g in df.groupby("Year"):
        note(f"{y}: {len(g)} leagues, {int(g['TotalRosters'].fillna(0).sum())} rosters")
    return df


def resolve(owner_id, league_name, users):
    if owner_id is None or str(owner_id) in OBSERVER_IDS:
        return "Orphan", "Orphan"
    if str(owner_id) == LINKOFTIME_ID and league_name != LINKOFTIME_REAL_LEAGUE:
        return "Orphan", "Orphan"
    name = users.get(owner_id, "Unknown")
    if str(name).upper().startswith("DELETED"):
        return "Orphan", "Orphan"
    return owner_id, name


def pull_league(r, labels, out):
    lid, year, name = r.LeagueID, int(r.Year), r.LeagueName
    print(f"Pulling {name} {year}")
    rosters = get(f"/league/{lid}/rosters") or []
    users = {u["user_id"]: u.get("display_name") for u in (get(f"/league/{lid}/users") or [])}
    owner = {x["roster_id"]: x.get("owner_id") for x in rosters}
    divnames = {1: r.Division1, 2: r.Division2}

    for x in rosters:
        oid, oname = resolve(x.get("owner_id"), name, users)
        st = x.get("settings") or {}
        out["Standings"].append({
            "Year": year, "LeagueID": lid, "LeagueName": name, "RosterID": x["roster_id"],
            "OwnerID": oid, "OwnerName": oname, "Division": st.get("division"),
            "DivisionName": divnames.get(st.get("division")), "Wins": st.get("wins"),
            "Losses": st.get("losses"),
            "PointsFor": round((st.get("fpts") or 0) + (st.get("fpts_decimal") or 0) / 100, 2),
            "PointsAgainst": round((st.get("fpts_against") or 0) + (st.get("fpts_against_decimal") or 0) / 100, 2)})
        for p in x.get("players") or []:
            out["Rosters_Players"].append({"Year": year, "LeagueID": lid, "LeagueName": name,
                                           "RosterID": x["roster_id"], "OwnerID": oid,
                                           "OwnerName": oname, "PlayerID": p})

    for week in range(1, 19):
        ms = get(f"/league/{lid}/matchups/{week}") or []
        if not ms:
            continue
        by = defaultdict(list)
        for m in ms:
            by[m.get("matchup_id")].append(m)
            starters, sp = m.get("starters") or [], m.get("starters_points") or []
            pp = m.get("players_points") or {}
            for i, pid in enumerate(starters):
                pts = pp.get(str(pid))
                if pts is None and i < len(sp):
                    pts = sp[i]
                out["Scores"].append({"LeagueYear": year, "league_id": lid, "weekNum": week,
                                      "roster_id": m.get("roster_id"), "lookupID": f"{lid}{m.get('roster_id')}",
                                      "starter": str(pid), "starter_points": float(pts or 0),
                                      "array_index": i + 1, "label": labels.get(str(pid), "")})
        for mid, teams in by.items():
            if mid is None:  # no matchup that week: one row per roster, no opponent
                pairs = [(t, {}) for t in teams]
            else:
                if len(teams) != 2:
                    teams = teams + [{"roster_id": None, "points": 0}]
                pairs = [(teams[0], teams[1]), (teams[1], teams[0])]
            for t, o in pairs:
                oid, oname = resolve(owner.get(t["roster_id"]), name, users)
                _, opname = resolve(owner.get(o.get("roster_id")), name, users) if o else (None, "")
                pf, pa = t.get("points", 0) or 0, o.get("points", 0) or 0
                outcome = "" if (pf == 0 and pa == 0) or not o else (
                    "Win" if pf > pa else "Loss" if pf < pa else "Tie")
                sp = t.get("starters_points") or []
                out["Matchups"].append({
                    "Year": year, "LeagueID": lid, "LeagueName": name, "Week": week,
                    "RosterID": t["roster_id"], "OwnerID": oid, "OwnerName": oname,
                    "OpponentRosterID": o.get("roster_id"), "OpponentName": opname,
                    "PointsFor": pf, "PointsAgainst": pa, "Outcome": outcome,
                    "IsRegularSeason": week <= 11,
                    "StarterPoints": round(sum(sp), 2) if sp else None,
                    "BenchPoints": round(pf - sum(sp), 2) if sp else None})
        for tx in get(f"/league/{lid}/transactions/{week}") or []:
            out["Transactions"].append({
                "Year": year, "LeagueID": lid, "LeagueName": name, "Week": week,
                "TransactionID": tx.get("transaction_id"), "Type": tx.get("type"),
                "RosterIDs": tx.get("roster_ids"), "OwnerIDs": [owner.get(x) for x in tx.get("roster_ids") or []],
                "Picks": tx.get("draft_picks"), "Adds": tx.get("adds"), "Drops": tx.get("drops"),
                "Status": tx.get("status"), "Created": tx.get("created")})

    for d in get(f"/league/{lid}/drafts") or []:
        st = d.get("settings") or {}
        out["Drafts"].append({"LeagueID": lid, "LeagueName": name, "DraftID": d.get("draft_id"),
                              "Status": d.get("status"), "Type": d.get("type"), "Season": d.get("season"),
                              "Rounds": st.get("rounds"), "Teams": st.get("teams")})
        for p in get(f"/draft/{d.get('draft_id')}/picks") or []:
            md = p.get("metadata") or {}
            out["DraftPicks"].append({
                "LeagueID": lid, "LeagueName": name, "DraftID": d.get("draft_id"), "Round": p.get("round"),
                "Pick_No": p.get("draft_slot"), "OverallPick": p.get("pick_no"), "Picked_By": p.get("picked_by"),
                "RosterID": p.get("roster_id"), "PlayerID": p.get("player_id"),
                "FirstName": md.get("first_name"), "LastName": md.get("last_name"), "Team": md.get("team"),
                "Position": md.get("position"), "Status": md.get("status"), "YearsExp": md.get("years_exp")})


def main():
    years = [str(y) for y in (sys.argv[1:] or ["2020", "2019"])]
    os.makedirs(OUT, exist_ok=True)
    pl = pd.read_csv("data/Players.csv", dtype=str)
    labels = dict(zip(pl["player_id"], pl["first_name"].fillna("") + " " + pl["last_name"].fillna("") + ", "
                      + pl["position"].fillna("") + " (" + pl["team"].fillna("") + ")"))
    leagues = discover(years)
    tag = "_".join(sorted(years))
    leagues.to_csv(f"{OUT}/LeagueIDs_{tag}.csv", index=False)
    out = defaultdict(list)
    for r in leagues.itertuples():
        pull_league(r, labels, out)
    for k, rows in out.items():
        pd.DataFrame(rows).to_csv(f"{OUT}/{k}_{tag}.csv", index=False)
        note(f"{k}: {len(rows)} rows")
    m = pd.DataFrame(out["Matchups"])
    if not m.empty:
        for (y, w), g in m.groupby(["Year", "Week"]):
            if w in (1, 11, 12, 13, 16, 17, 18):
                note(f"{y} wk{w}: {len(g)} rosters, {int((g['PointsFor'] > 0).sum())} scored, "
                     f"{int(g['OpponentRosterID'].notna().sum())} with an opponent")
    open(f"{OUT}/Discovery_{tag}.txt", "w").write("\n".join(log) + "\n")


if __name__ == "__main__":
    main()
