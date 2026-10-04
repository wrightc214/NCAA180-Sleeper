"""
tank_check.py -- flag lineups that bench clearly better players (imported by
inactivity_report.py; can also be run alone to print the table).

League rule: no tanking by benching your best lineup. For a COMPLETED week, compare each
team's starters to the best legal lineup it could have set, valuing players by
FantasyCalc redraft value (a pre-game, rest-of-season quality measure -- not hindsight
points, so a fluke bench game doesn't count against anyone).

Bench players only count as "available" if they actually played that week (scored
non-zero points): injured / bye / inactive players can't be started, and we have no
as-of-week injury feed. Starters always count as chosen.

Per team: StartValue, BestValue, Ratio = Start/Best, Gap = Best - Start, plus the
better players benched and the weak starters they should have replaced.
Tiers: 🚨 Tank alert  Ratio < 0.60 and Gap >= 4000
       ⚠️ Lineup check Ratio < 0.75 and Gap >= 2500
CWD must be repo root.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX"]
ELIGIBLE = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"},
            "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
            "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
ALERT = (0.60, 4000)
CHECK = (0.75, 2500)


def best(pool, slots):
    """Greedy fill, most restrictive slot first. pool: list of (value, pos, name). Returns chosen."""
    pool = sorted(pool, key=lambda x: -x[0])
    used, chosen = [False] * len(pool), []
    for slot in sorted(slots, key=lambda s: len(ELIGIBLE.get(s, ()))):
        ok = ELIGIBLE.get(slot)
        if not ok:
            continue
        for i, p in enumerate(pool):
            if not used[i] and p[1] in ok:
                used[i] = True
                chosen.append(p)
                break
    return chosen


def league_slots(year):
    out = {}
    try:
        lg = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
        for r in lg[lg["Year"] == str(year)].itertuples():
            if isinstance(getattr(r, "RosterPositions", None), str):
                out[r.LeagueID] = [x for x in r.RosterPositions.split(",")
                                   if x not in ("BN", "IR", "TAXI", "K", "DEF")]
    except Exception:
        pass
    return out


def check_week(week, year):
    s = pd.read_csv("data/Scores_Season.csv", dtype={"player_id": str, "league_id": str})
    s = s[s["weekNum"] == week]
    pv = pd.read_csv("data/PlayerValues_Current.csv", dtype={"SleeperID": str})
    s = s.merge(pv[["SleeperID", "Name", "Position", "RedraftValue"]],
                left_on="player_id", right_on="SleeperID", how="left")
    s["RedraftValue"] = s["RedraftValue"].fillna(0)
    s["Pos"] = s["Position"].fillna(s["label"].str.extract(r", (\w+) \(")[0]).replace({"FB": "RB"})
    s["Name"] = s["Name"].fillna(s["label"].str.split(",").str[0])
    slots = league_slots(year)
    m = pd.read_csv("data/Matchups_Season.csv", dtype=str)
    m = m[m["Week"] == str(week)]
    t = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
    team = {(r.League, str(r._3)): r.Team for r in t.itertuples()}
    rows = []
    for (lid, rid), g in s.groupby(["league_id", "roster_id"]):
        sl = slots.get(lid, DEFAULT_SLOTS)
        st = g[g["is_starter"] == True]  # noqa: E712
        avail = g[(g["is_starter"] == True) | (g["points"] != 0)]  # noqa: E712
        pool = [(v, p, n) for v, p, n in zip(avail["RedraftValue"], avail["Pos"], avail["Name"])]
        opt = best(pool, sl)
        start_val = st[st["Pos"].isin({"QB", "RB", "WR", "TE"})]["RedraftValue"].sum()
        best_val = sum(p[0] for p in opt)
        if best_val <= 0:
            continue
        opt_names = {p[2] for p in opt}
        st_names = set(st["Name"])
        benched = [p for p in sorted(opt, key=lambda x: -x[0]) if p[2] not in st_names and p[0] > 0]
        weak = st[(~st["Name"].isin(opt_names)) & st["Pos"].isin({"QB", "RB", "WR", "TE"})]
        weak = weak.sort_values("RedraftValue")
        mr = m[(m["LeagueID"] == lid) & (m["RosterID"] == str(rid))]
        lname = mr["LeagueName"].iloc[0] if len(mr) else ""
        rows.append({"Week": week, "LeagueID": lid, "LeagueName": lname, "RosterID": rid,
                     "Team": team.get((lname, str(rid)), f"{lname} #{rid}"),
                     "OwnerName": mr["OwnerName"].iloc[0] if len(mr) else "",
                     "StartValue": int(start_val), "BestValue": int(best_val),
                     "Ratio": round(start_val / best_val, 2), "Gap": int(best_val - start_val),
                     "Benched": ", ".join(p[2] for p in benched),
                     "Started": ", ".join(weak["Name"])})
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    d = d[d["OwnerName"].astype(str) != "Orphan"].copy()
    d["Tier"] = ""
    d.loc[(d["Ratio"] < CHECK[0]) & (d["Gap"] >= CHECK[1]), "Tier"] = "Lineup check"
    d.loc[(d["Ratio"] < ALERT[0]) & (d["Gap"] >= ALERT[1]), "Tier"] = "Tank alert"
    return d.sort_values("Ratio")


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    d = check_week(w, sys.argv[2] if len(sys.argv) > 2 else "2026")
    print(d.head(25)[["Team", "OwnerName", "Ratio", "Gap", "Tier", "Benched", "Started"]].to_string())
    print(d["Tier"].value_counts())
