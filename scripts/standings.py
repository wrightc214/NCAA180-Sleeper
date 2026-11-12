"""
standings.py -- NCAA 180 season-to-date standings across all 180 teams.

Writes data/OverallStandings_Season.csv (overwritten each run; also feeds columns A:K
of the poll Google Sheet):
  Playoff Rank, User ID, Team, League, Points, Wins, Losses, Ties,
  Exp Wins, Luck, Division Place

Points Rank, Last Week and the projection columns are formulas in the sheet,
so they are intentionally NOT produced here.

Rules:
  - Regular season only (weeks 1-11), completed weeks only (Outcome populated).
  - Ties count as 0.5 wins for all ranking (5-5-1 sits ahead of every 5-win team).
  - Ranking order: Wins + 0.5*Ties desc, then Points desc. No H2H.
  - Exp Wins: sum over weeks of (teams outscored that week / 179), all 180 teams.
    An exact points tie with another team counts as half a team beaten.
  - Luck = Wins + 0.5*Ties - Exp Wins.
  - Exact Wins+Points ties share a rank and the next rank is skipped (6,7,7,9).
  - Division Place is within League + Division (West/East names repeat across leagues).

CWD must be repo root, same as every other script.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import completed_weeks as finished_weeks  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)
import standard_results  # noqa: E402 (standard-scoring scores/results)

MATCHUPS_FILE = "data/Matchups_Season.csv"
TEAMS_FILE = "data/Teams.csv"
OUTPUT_FILE = "data/OverallStandings_Season.csv"
LAST_REGULAR_WEEK = lcfg.last_regular_week()

LEAGUE_DISPLAY = lcfg.league_display()  # friendly names: data/LeagueShortNames.csv


HISTORY_DIR = "data/standings"  # OverallStandings_<year>.csv, one per finished season (Chris, 2026-11-11)


def overall(reg, teams):
    """The standings table for one season's completed regular-season rows.
    teams: LeagueName, RosterID, Team, DivisionKey (that season's names and divisions)."""
    n_teams = reg.groupby("Week").size()
    if (n_teams != 180).any():
        print(f"WARNING: week team counts not all 180: {n_teams.to_dict()}")

    # All-play expected wins across the whole field.
    def week_exp(g):
        p = g["PointsFor"]
        below = p.apply(lambda x: (p < x).sum())
        equal = p.apply(lambda x: (p == x).sum() - 1)  # exclude self
        return (below + 0.5 * equal) / (len(g) - 1)

    reg = reg.copy()
    reg["ExpW"] = reg.groupby("Week", group_keys=False).apply(week_exp)
    reg["W"] = (reg["Outcome"] == "Win").astype(int)
    reg["L"] = (reg["Outcome"] == "Loss").astype(int)
    reg["T"] = (reg["Outcome"] == "Tie").astype(int)

    other = set(reg["Outcome"]) - {"Win", "Loss", "Tie"}
    if other:
        print(f"WARNING: unrecognized Outcome values ignored: {other}")

    s = reg.groupby(["LeagueName", "RosterID", "OwnerID", "OwnerName"], as_index=False).agg(
        Points=("PointsFor", "sum"), Wins=("W", "sum"), Losses=("L", "sum"),
        Ties=("T", "sum"), ExpWins=("ExpW", "sum"))

    s = s.merge(teams[["LeagueName", "RosterID", "Team", "DivisionKey"]],
                on=["LeagueName", "RosterID"], how="left")
    if s["Team"].isna().any():
        print("WARNING: no team name match for:")
        print(s[s["Team"].isna()][["LeagueName", "RosterID", "OwnerName"]].to_string(index=False))

    s["WinVal"] = s["Wins"] + 0.5 * s["Ties"]
    s = s.sort_values(["WinVal", "Points"], ascending=False).reset_index(drop=True)
    # Competition ranking: exact ties share a rank, next rank skipped (6,7,7,9).
    # Points rounded to 2dp first so float noise can't split a displayed tie.
    s["_key"] = list(zip(s["WinVal"], s["Points"].round(2)))
    s["Playoff Rank"] = s["_key"].rank(method="min", ascending=False).astype(int)
    s["Division Place"] = (s.groupby(["LeagueName", "DivisionKey"])["_key"]
                           .rank(method="min", ascending=False).astype(int))

    s["Points"] = s["Points"].round(2)
    s["Exp Wins"] = s["ExpWins"].round(2)
    s["Luck"] = (s["WinVal"] - s["ExpWins"]).round(2)
    s["League"] = s["LeagueName"].map(LEAGUE_DISPLAY).fillna(s["LeagueName"])
    s["User ID"] = s["OwnerName"]  # already "Orphan" for orphan rosters (league_matchups.py)

    return s[["Playoff Rank", "User ID", "Team", "League", "Points", "Wins", "Losses",
              "Ties", "Exp Wins", "Luck", "Division Place"]]


def main():
    if "--history" in sys.argv:
        return history()
    m = standard_results.apply(pd.read_csv(MATCHUPS_FILE, dtype=str))  # standard scores; 2026+ results on them
    m["Week"] = m["Week"].astype(int)
    m["PointsFor"] = m["PointsFor"].astype(float)

    # Completed regular-season weeks only: every row in the week has an Outcome.
    reg = m[m["Week"] <= LAST_REGULAR_WEEK]
    weeks = sorted(set(finished_weeks(m["Year"].iloc[0])) & set(reg["Week"]))
    if not weeks:
        raise SystemExit("No completed regular-season weeks yet.")
    reg = reg[reg["Week"].isin(weeks)].copy()

    t = pd.read_csv(TEAMS_FILE, dtype=str, encoding="utf-8-sig")
    t["DivisionKey"] = t["Division Name"].str.strip().str.upper()
    t = t.rename(columns={"League": "LeagueName", "Roster ID": "RosterID"})
    out = overall(reg, t)
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE}: {len(out)} teams, weeks {weeks[0]}-{weeks[-1]}")
    # a season that moved to Matchups_Historic gets its past-season file once
    done = {f[17:21] for f in os.listdir(HISTORY_DIR)} if os.path.isdir(HISTORY_DIR) else set()
    if set(pd.read_csv("data/Matchups_Historic.csv", usecols=["Year"])["Year"].astype(str)) - done:
        history()


def history():
    """Final regular-season standings for every past season in Matchups_Historic.csv, same rules and
    columns, with that season's team names and divisions -> data/standings/OverallStandings_<year>.csv.
    Results are as recorded that season (official Sleeper scoring)."""
    import team_names as tn
    m = pd.read_csv("data/Matchups_Historic.csv", dtype=str)
    m = m[m["IsRegularSeason"].astype(str) == "True"].copy()
    m["Week"] = m["Week"].astype(int)
    m["PointsFor"] = m["PointsFor"].astype(float)
    sh = pd.read_csv("data/Standings_Historic.csv", dtype=str)
    os.makedirs(HISTORY_DIR, exist_ok=True)
    for year, reg in m.groupby("Year"):
        n = tn.names(year).copy()
        n["LeagueName"] = n["LeagueName"].str.strip()
        d = sh[sh["Year"] == year][["LeagueName", "RosterID", "DivisionName"]].copy()
        d["LeagueName"] = d["LeagueName"].str.strip()
        d["DivisionKey"] = d["DivisionName"].str.strip().str.upper()
        teams = n.merge(d[["LeagueName", "RosterID", "DivisionKey"]], on=["LeagueName", "RosterID"], how="left")
        reg = reg.assign(LeagueName=reg["LeagueName"].str.strip())
        out = overall(reg, teams)
        path = os.path.join(HISTORY_DIR, f"OverallStandings_{year}.csv")
        out.to_csv(path, index=False)
        print(f"Wrote {path}: {len(out)} teams, weeks {reg['Week'].min()}-{reg['Week'].max()}")


if __name__ == "__main__":
    main()
