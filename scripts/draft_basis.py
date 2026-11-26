"""
draft_basis.py -- freeze each team's regular-season record, points and max PF for draft orders.

Chris (2026-11-26): some leagues may already order their rookie draft by max PF, so every team's
record, points for/against and max PF through the regular season (weeks 1-11) is captured once,
before postseason weeks are added to the season files.

Writes data/DraftBasis_<year>.csv (frozen: not run by any workflow; rerun only on purpose):
  Year, LeagueID, LeagueName, RosterID, TeamName, OwnerName, DivisionName,
  Wins, Losses, Ties, PointsFor, PointsAgainst, MaxPF, Efficiency, ThroughWeek
Scores are as played in each league (Sleeper points), from data/Matchups_Season.csv and
data/MaxPoints_Season.csv. Fails if any team is missing a week or the totals disagree with
data/Standings_Season.csv.

Usage (repo root): python scripts/draft_basis.py --year 2026 --through 11
"""
import argparse, json
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--year", type=int, required=True)
ap.add_argument("--through", type=int, default=11)
a = ap.parse_args()

m = pd.read_csv("data/Matchups_Season.csv")
m = m[(m.Year == a.year) & (m.Week <= a.through)]
x = pd.read_csv("data/MaxPoints_Season.csv")
x = x[(x.Year == a.year) & (x.Week <= a.through)]
g = m.groupby(["LeagueID", "LeagueName", "RosterID"]).agg(
    OwnerName=("OwnerName", "last"),
    Wins=("Outcome", lambda s: int((s == "Win").sum())),
    Losses=("Outcome", lambda s: int((s == "Loss").sum())),
    Ties=("Outcome", lambda s: int((s == "Tie").sum())),
    PointsFor=("PointsFor", "sum"), PointsAgainst=("PointsAgainst", "sum"),
    Weeks=("Week", "nunique")).reset_index()
mp = x.groupby(["LeagueID", "RosterID"]).agg(MaxPF=("MaxPoints", "sum"), MaxWeeks=("Week", "nunique")).reset_index()
g = g.merge(mp, on=["LeagueID", "RosterID"], how="left")
if not ((g.Weeks == a.through) & (g.MaxWeeks == a.through)).all():
    raise SystemExit("A team is missing a week of results or max points")

st = pd.read_csv("data/Standings_Season.csv")
st = st[st.Year == a.year][["LeagueID", "RosterID", "DivisionName", "Wins", "Losses", "PointsFor"]]
g = g.merge(st.rename(columns={"Wins": "sW", "Losses": "sL", "PointsFor": "sPF"}), on=["LeagueID", "RosterID"], how="left")
off = g[(g.Wins != g.sW) | (g.Losses != g.sL) | ((g.PointsFor - g.sPF).abs() > 0.05)]
if len(off):
    raise SystemExit(f"{len(off)} teams disagree with Standings_Season.csv")

idx = json.load(open("data/scoreboard/index.json"))
g["TeamName"] = [idx["leagues"].get(str(l), {}).get("teams", {}).get(str(r), {}).get("name", "")
                 for l, r in zip(g.LeagueID, g.RosterID)]
g["Year"], g["ThroughWeek"] = a.year, a.through
g["PointsFor"], g["PointsAgainst"], g["MaxPF"] = g.PointsFor.round(2), g.PointsAgainst.round(2), g.MaxPF.round(2)
g["Efficiency"] = (g.PointsFor / g.MaxPF).round(4)
cols = ["Year", "LeagueID", "LeagueName", "RosterID", "TeamName", "OwnerName", "DivisionName", "Wins", "Losses",
        "Ties", "PointsFor", "PointsAgainst", "MaxPF", "Efficiency", "ThroughWeek"]
out = f"data/DraftBasis_{a.year}.csv"
g.sort_values(["LeagueName", "RosterID"])[cols].to_csv(out, index=False)
print(f"wrote {out}: {len(g)} teams through week {a.through}")
