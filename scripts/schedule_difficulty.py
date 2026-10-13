"""
schedule_difficulty.py -- how hard each team's schedule played (team-page metric, NOT a poll input).

For every regular-season week: the all-team weekly median score (all 180 teams, every league) vs the
score your actual opponent put up that week. If the median beats your opponent, an average team
would have won that game. Summed over the season = the record an average team would have against
your schedule. Rank 1 = hardest schedule (fewest average-team wins); ties broken by how far your
opponents scored above the weekly median on average (more = harder).

Scores are PointsFor (one standardized scoring basis), so leagues and seasons compare directly.
Points faced are luck (no defense in fantasy), which is why this stays off the poll.

Writes data/ScheduleDifficulty_Season.csv (current season) and data/ScheduleDifficulty_Historic.csv.
CWD must be repo root. Usage: python scripts/schedule_difficulty.py [--years 2024 2025]
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402

OUT_SEASON = "data/ScheduleDifficulty_Season.csv"
OUT_HISTORIC = "data/ScheduleDifficulty_Historic.csv"
COLS = ["Year", "ThroughWeek", "Rank", "Tied", "Team", "LeagueID", "LeagueName", "League", "RosterID",
        "AvgTeamW", "AvgTeamL", "AvgTeamT", "AvgOppPts", "AvgOppVsMedian", "ActualW", "ActualL", "ActualT"]


def season(year, last_regular):
    m = pc.matchups(year)
    m = m[(m["Week"] <= last_regular) & m["Outcome"].isin(["Win", "Loss", "Tie"])].copy()
    if m.empty:
        return pd.DataFrame(columns=COLS)
    m["PointsFor"] = m["PointsFor"].astype(float)
    m["Median"] = m.groupby("Week")["PointsFor"].transform("median")
    opp = m[["LeagueID", "Week", "RosterID", "PointsFor"]].rename(
        columns={"RosterID": "OpponentRosterID", "PointsFor": "OppPts"})
    m = m.merge(opp, on=["LeagueID", "Week", "OpponentRosterID"], how="left")
    m["AW"] = (m["Median"] > m["OppPts"]).astype(int)
    m["AL"] = (m["Median"] < m["OppPts"]).astype(int)
    m["AT"] = (m["Median"] == m["OppPts"]).astype(int)
    m["Diff"] = m["OppPts"] - m["Median"]
    g = m.groupby(["LeagueID", "LeagueName", "RosterID"]).agg(
        AvgTeamW=("AW", "sum"), AvgTeamL=("AL", "sum"), AvgTeamT=("AT", "sum"),
        AvgOppPts=("OppPts", "mean"), AvgOppVsMedian=("Diff", "mean"),
        ActualW=("Outcome", lambda s: (s == "Win").sum()), ActualL=("Outcome", lambda s: (s == "Loss").sum()),
        ActualT=("Outcome", lambda s: (s == "Tie").sum())).reset_index()
    g["_w"] = g["AvgTeamW"] + 0.5 * g["AvgTeamT"]
    g = g.sort_values(["_w", "AvgOppVsMedian"], ascending=[True, False]).reset_index(drop=True)
    key = list(zip(g["_w"], g["AvgOppVsMedian"].round(6)))
    g["Rank"] = [key.index(k) + 1 for k in key]
    g["Tied"] = g["Rank"].duplicated(keep=False)
    names = {(r.LeagueID, r.RosterID): r.Team for r in pc.teams(year).itertuples()}
    short = pc.league_short()
    g["Team"] = [names.get(k, "") for k in zip(g["LeagueID"], g["RosterID"])]
    g["League"] = [short.get(str(n).strip().upper(), n) for n in g["LeagueName"]]
    g["Year"], g["ThroughWeek"] = year, int(m["Week"].max())
    g["AvgOppPts"] = g["AvgOppPts"].round(2)
    g["AvgOppVsMedian"] = g["AvgOppVsMedian"].round(2)
    return g[COLS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int)
    a = ap.parse_args()
    cfg = pc.config()
    last = int(cfg.get("last_regular_week", 11))
    years = a.years or pc.seasons()
    cur = max(pc.seasons())
    hist = [season(y, last) for y in years if y != cur]
    if cur in years:
        s = season(cur, last)
        s.to_csv(OUT_SEASON, index=False)
        print(f"Wrote {OUT_SEASON} ({len(s)} teams, through week {s['ThroughWeek'].max() if len(s) else '-'})")
    hist = [h for h in hist if len(h)]
    if hist:
        h = pd.concat(hist)
        if a.years and os.path.exists(OUT_HISTORIC):  # partial rerun: replace only those years
            old = pd.read_csv(OUT_HISTORIC, dtype={"LeagueID": str, "RosterID": str})
            h = pd.concat([old[~old["Year"].isin(a.years)], h])
        h.sort_values(["Year", "Rank"]).to_csv(OUT_HISTORIC, index=False)
        print(f"Wrote {OUT_HISTORIC} ({h['Year'].nunique()} seasons)")


if __name__ == "__main__":
    main()
