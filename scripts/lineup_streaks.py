"""
lineup_streaks.py -- spot abandoned teams.

Writes data/LineupStreaks_Season.csv, one row per roster, sorted most-suspicious first:
  Team, League, LeagueName, RosterID, OwnerID, OwnerName,
  SameLineupWeeks   consecutive weeks (ending at the latest week in Scores_Season)
                    with the identical set of starters
  SinceWeek, ThroughWeek
  SameRosterWeeks   consecutive weeks with the identical full roster (no adds/drops/trades)
  ZeroStarters      starters who scored 0.0 in the latest COMPLETED week
                    (bye, injury, or cut player left in the lineup -- a strong tell)

The latest week in Scores_Season can be the upcoming one; its lineup is whatever is set
right now, so a streak through that week means the coach hasn't touched it yet this week.

Orphans (OwnerName "Orphan") are included so they're easy to filter in or out.
CWD must be repo root. Reads only pipeline files; run after `scores` and `matchups`.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import completed_weeks as finished_weeks  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

SCORES = "data/Scores_Season.csv"
MATCHUPS = "data/Matchups_Season.csv"
TEAMS = "data/Teams.csv"
OUT = "data/LineupStreaks_Season.csv"
YEAR = str(lcfg.season())

LEAGUE_DISPLAY = lcfg.league_display()  # data/LeagueShortNames.csv + config display overrides


def trailing_streak(sets_by_week):
    """sets_by_week: list of (week, frozenset) ascending. Returns (length, since_week)."""
    if not sets_by_week:
        return 0, None
    n, since = 1, sets_by_week[-1][0]
    for (w, s), (_, nxt) in zip(reversed(sets_by_week[:-1]), reversed(sets_by_week[1:])):
        if s != nxt:
            break
        n, since = n + 1, w
    return n, since


def main():
    sc = pd.read_csv(SCORES, dtype=str)
    sc = sc[sc["LeagueYear"] == YEAR].copy()
    sc["wk"] = sc["weekNum"].astype(int)
    sc["pts"] = sc["points"].astype(float)
    sc["st"] = sc["is_starter"].str.lower() == "true"

    m = pd.read_csv(MATCHUPS, dtype=str)
    m = m[m["Year"] == YEAR]
    last_done = max(finished_weeks(YEAR), default=None)
    owners = m.drop_duplicates(["LeagueID", "RosterID"])[["LeagueID", "LeagueName", "RosterID", "OwnerID", "OwnerName"]]

    t = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig").rename(
        columns={"League": "LeagueName", "Roster ID": "RosterID"})[["LeagueName", "RosterID", "Team"]]

    latest = sc["wk"].max()
    rows = []
    for (lid, rid), g in sc.groupby(["league_id", "roster_id"]):
        weeks = sorted(g["wk"].unique())
        starters = [(w, frozenset(g[(g.wk == w) & g.st]["player_id"])) for w in weeks]
        roster = [(w, frozenset(g[g.wk == w]["player_id"])) for w in weeks]
        n, since = trailing_streak(starters)
        nr, _ = trailing_streak(roster)
        zero = None
        if last_done is not None:
            z = g[(g.wk == last_done) & g.st]
            zero = int((z["pts"] == 0).sum()) if len(z) else None
        rows.append({"LeagueID": lid, "RosterID": rid, "SameLineupWeeks": n,
                     "SinceWeek": since, "ThroughWeek": weeks[-1],
                     "SameRosterWeeks": nr, "ZeroStarters": zero})
    df = pd.DataFrame(rows).merge(owners, on=["LeagueID", "RosterID"], how="left").merge(
        t, on=["LeagueName", "RosterID"], how="left")
    df["League"] = df["LeagueName"].map(LEAGUE_DISPLAY).fillna(df["LeagueName"])
    stale = df["ThroughWeek"] < latest
    if stale.any():
        print(f"WARNING: {stale.sum()} rosters have no rows for week {latest}")
    df = df.sort_values(["SameLineupWeeks", "ZeroStarters", "SameRosterWeeks"], ascending=False)
    cols = ["Team", "League", "LeagueName", "RosterID", "OwnerID", "OwnerName", "SameLineupWeeks",
            "SinceWeek", "ThroughWeek", "SameRosterWeeks", "ZeroStarters"]
    df[cols].to_csv(OUT, index=False)
    flagged = df[df["SameLineupWeeks"] >= 3]
    print(f"Wrote {OUT}: {len(df)} rosters, weeks through {latest} "
          f"(last completed {last_done}). Same lineup 3+ weeks: {len(flagged)}")
    print(flagged[cols[:2] + ["OwnerName", "SameLineupWeeks", "SameRosterWeeks", "ZeroStarters"]]
          .head(25).to_string(index=False))


if __name__ == "__main__":
    main()
