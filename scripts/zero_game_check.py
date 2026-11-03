"""zero_game_check.py -- block publishing when a finished week has a 0-0 game.

Why (Chris, 2026-11-03): on 2026-11-03 league_matchups.py crashed, week 8 stayed at 0.00 for
every team, and the run still posted a Top 25 and sent false standard-scoring alerts. A 0-0
game in a finished week means the Sleeper points never arrived (or Sleeper hasn't scored the
week yet), so nothing built from it should go out.

Checks every completed week of the current season (week_status.completed_weeks) in
data/Matchups_Season.csv. A game = a row with an opponent; it fails when both sides have 0
(blank counts as 0). Teams without a game that week (postseason, NIT groups) have no opponent
and are skipped.

Exit 1 + writes work/publish_blocked.txt when any game is 0-0. The weekly workflow then skips
the remaining scripts, the commits and the Discord posts, and does not mark the week processed,
so the next scheduled run tries again. ALLOW_ZERO_GAMES=true (workflow input) reports but passes.
"""
import os
import sys

import pandas as pd

import league_config as lcfg
from week_status import completed_weeks

OUT = "work/publish_blocked.txt"


def zero_games(year):
    m = pd.read_csv("data/Matchups_Season.csv", dtype=str)
    m = m[(m["Year"] == str(year)) & m["OpponentRosterID"].notna() & (m["OpponentRosterID"] != "")]
    done = set(completed_weeks(year))
    m = m[m["Week"].astype(int).isin(done)]
    pts = {(r.LeagueID, str(r.RosterID).replace(".0", ""), r.Week): float(r.PointsFor or 0)
           for r in m.fillna({"PointsFor": "0"}).itertuples()}
    seen, bad = set(), []
    for r in m.itertuples():
        a, b = str(r.RosterID).replace(".0", ""), str(r.OpponentRosterID).replace(".0", "")
        key = (r.LeagueID, r.Week, *sorted((a, b)))
        if key in seen:
            continue
        seen.add(key)
        olid = getattr(r, "OpponentLeagueID", "") or r.LeagueID
        if pts.get((r.LeagueID, a, r.Week), 0) == 0 and pts.get((str(olid), b, r.Week), 0) == 0:
            bad.append((r.LeagueName.strip(), r.Week, f"{r.OwnerName} vs {r.OpponentName}"))
    return sorted(done), bad, m["LeagueID"].nunique()


def summary(bad, n_leagues):
    """Short on purpose (Chris): a couple of games -> list them; one or two leagues -> name
    them; every league -> catastrophic, just say so."""
    leagues = pd.Series([b[0] for b in bad]).value_counts()
    weeks = "wk " + "/".join(sorted({str(b[1]) for b in bad}, key=int))
    if len(bad) <= 2:
        return f"{weeks}: " + "; ".join(f"{lg} – {g}" for lg, _, g in bad)
    if len(leagues) >= n_leagues:
        return f"CATASTROPHIC: every league is 0-0 in {weeks} ({len(bad)} games). Sleeper points never arrived."
    if len(leagues) <= 2:
        return f"{weeks}: " + "; ".join(f"{lg} ({n} games)" for lg, n in leagues.items())
    return f"{weeks}: {len(bad)} games in {len(leagues)} of {n_leagues} leagues"


def main():
    os.chdir(lcfg.ROOT)
    year = lcfg.season()
    weeks, bad, n_leagues = zero_games(year)
    if not bad:
        print(f"{year}: no 0-0 games in completed weeks {weeks[:1]}..{weeks[-1:]}")
        return 0
    msg = summary(bad, n_leagues)
    if os.environ.get("ALLOW_ZERO_GAMES", "").lower() == "true":
        print(f"::warning::{msg} (ALLOW_ZERO_GAMES=true: publishing anyway)")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(msg + "\n")
    print(f"::error::PUBLISHING BLOCKED (0-0 games): {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
