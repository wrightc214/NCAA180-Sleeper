"""
poll_prior.py -- the Professor bot's frozen preseason prior (run once per season, before week 1).

  Prior = 80% Preseason Starter Value (PSV) percentile + 20% last season's final-rank percentile
  PSV = FantasyCalc redraft value of each roster's best legal starting lineup (roster_map's
        best_lineup, same slots), from the last value snapshot before week 1.
  Last season's final rank = the final poll's full order (BotConsensus, last week of that season);
        teams with no poll that season fall back to the league standings (wins, then points).
  Percentiles are across every team in the season (all 180).

The prior is FROZEN: never refreshed in-season. Weights live in config/poll.json
-> professor.prior.

Writes data/PollPrior_Season.csv: Year, LeagueID, LeagueName, RosterID, PSV, PSVPct,
LastFinalRank, LastFinalPct, Prior, Basis.

  python scripts/poll_prior.py                        # current rosters + current values
  python scripts/poll_prior.py --rosters R.csv --values V.csv --basis "note"
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from roster_map import DEFAULT_SLOTS, best_lineup  # noqa: E402

OUT = "data/PollPrior_Season.csv"


def pct(s):
    """Percentile rank 0..1 (1 = best) across the series; ties share the average rank."""
    s = pd.Series(s, dtype=float)
    return ((s.rank(method="average") - 1) / (len(s) - 1)).fillna(0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rosters", default="data/Rosters_Current.csv")
    ap.add_argument("--values", default="data/PlayerValues_Current.csv")
    ap.add_argument("--basis", default="")
    a = ap.parse_args()
    cfg = json.load(open("config/poll.json"))["professor"]["prior"]

    ro = pd.read_csv(a.rosters, dtype=str)
    year = ro["Year"].max()
    ro = ro[ro["Year"] == year]
    pv = pd.read_csv(a.values, dtype={"SleeperID": str})
    snap = pv["Date"].max() if "Date" in pv.columns else "?"
    ro = ro.merge(pv[["SleeperID", "RedraftValue", "Position"]].rename(
        columns={"SleeperID": "PlayerID", "Position": "VPos"}), on="PlayerID", how="left")
    ro["Pos"] = ro["VPos"].fillna(ro["Position"]).replace({"FB": "RB"})
    ro["RedraftValue"] = ro["RedraftValue"].fillna(0)

    slots = {}
    lg = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    for r in lg[lg["Year"] == year].itertuples():
        if isinstance(r.RosterPositions, str):
            slots[r.LeagueID] = [x for x in r.RosterPositions.split(",") if x not in ("BN", "IR", "TAXI", "K", "DEF")]
    rows = [{"Year": year, "LeagueID": lid, "LeagueName": lname.strip(), "RosterID": rid,
             "PSV": round(best_lineup(list(zip(g["RedraftValue"], g["Pos"])), slots.get(lid, DEFAULT_SLOTS)))}
            for (lid, lname, rid), g in ro.groupby(["LeagueID", "LeagueName", "RosterID"])]
    t = pd.DataFrame(rows)

    # last season's final order, by slot (league name + roster id)
    prev = str(int(year) - 1)
    final = {}
    if os.path.exists("data/Poll_Historic.csv"):
        p = pd.read_csv("data/Poll_Historic.csv", dtype=str)
        p = p[(p["Year"] == prev) & (p["PollType"] == "BotConsensus")]
        if len(p):
            p = p[p["AppliesToWeek"].astype(int) == p["AppliesToWeek"].astype(int).max()]
            final = {(r.LeagueName.strip(), r.RosterID): int(r.Rank) for r in p.itertuples()}
    if not final and os.path.exists("data/Standings_Historic.csv"):  # no poll that season
        s = pd.read_csv("data/Standings_Historic.csv", dtype=str)
        s = s[s["Year"] == prev].assign(W=lambda d: d["Wins"].astype(float), PF=lambda d: d["PointsFor"].astype(float))
        s = s.sort_values(["W", "PF"], ascending=False).reset_index(drop=True)
        final = {(r.LeagueName.strip(), r.RosterID): i + 1 for i, r in s.iterrows()}
    t["LastFinalRank"] = [final.get((a_, b)) for a_, b in zip(t["LeagueName"], t["RosterID"])]

    t["PSVPct"] = pct(t["PSV"]).round(4)
    t["LastFinalPct"] = pct(-t["LastFinalRank"].astype(float).fillna(t["LastFinalRank"].max() or 0)).round(4)
    t["Prior"] = (cfg["psv"] * t["PSVPct"] + cfg["last_final"] * t["LastFinalPct"]).round(4)
    t["Basis"] = a.basis or f"rosters {os.path.basename(a.rosters)}; values snapshot {snap}; final order {prev}"
    t.sort_values("Prior", ascending=False).to_csv(OUT, index=False)
    print(f"{OUT}: {len(t)} teams, year {year}, values {snap}, last-season ranks for {t['LastFinalRank'].notna().sum()}")


if __name__ == "__main__":
    main()
