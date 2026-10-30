"""
conference_championships.py -- week-12 conference championship games (CCG).

Each league's division winners (weeks 1..last_regular_week) meet in the CCG week.
Division order = the shared tiebreakers in config/league.json (tiebreakers.order; Sleeper
default per Chris 2026-10-30: win %, points for, head-to-head). A title still tied after the
last tiebreaker is flagged, never guessed (exit 1). Results and points use standard scoring from 2026.
Winner = higher points that CCG week. Writes Round="CCG" rows to Postseason_Season.csv;
reruns refresh scores.

Runs in the weekly job: it does nothing until every regular-season week is complete, then
writes the pairings (the Tuesday after the last regular week) and refreshes them after.

  python scripts/conference_championships.py [--year 2026] [--data-dir DIR] [--force]
"""
import argparse
import sys

import pandas as pd

import _postseason_common as ps


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--data-dir")
    ap.add_argument("--force", action="store_true", help="pair even if the regular season is unfinished (tests)")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, _, _ = ps.paths(a)
    _, cfg = ps.config()
    week = ps.ccg_week()
    lr = ps.last_regular_week()
    if not a.force and year == ps.current_season():
        missing = sorted(set(range(1, lr + 1)) - set(ps.completed_weeks(year)))
        if missing:
            print(f"CCG {year}: regular season not finished (weeks {missing[0]}-{missing[-1]} to go); nothing written")
            return
    per = int(cfg["ccg"].get("divisions_per_league", 2))
    games = ps.regular_games(year)
    st = ps.standings(year).dropna(subset=["Division"])
    short = {v: k for k, v in ps.league_short().items()}
    rows, problems = [], []
    for (lid, lname), g in st.groupby(["LeagueID", "LeagueName"]):
        champs = []
        for div, d in g.groupby("Division"):
            r, ties = ps.rank_ties(d, games)
            tied = next((t for t in ties if r.iloc[0]["Team"] in t), [])
            if tied:
                problems.append(f"{lname} / {div}: division title still tied after every tiebreaker ({', '.join(tied)})")
                continue
            champs.append(r.iloc[0].to_dict())
        if len(champs) != per:
            problems.append(f"{lname}: {len(champs)} division winner(s), expected {per} -- CCG not paired")
            continue
        champs = ps.rank(pd.DataFrame(champs), games).to_dict("records")  # better record listed first
        game = ps.game_rows(year, "CCG", week, f"{year}-CCG-{lid}", champs, stage=short.get(lname, lname))
        if any(r["Outcome"] == "Tie" for r in game):
            problems.append(f"{lname}: CCG ended in an exact tie -- resolve manually")
        rows += game
    ps.replace_rows(year, lambda r: r["Round"] != "CCG", rows, season_path)
    fin = sum(1 for r in rows if r["Status"] == "Final") // 2
    print(f"CCG {year}: {len(rows) // 2} games ({fin} final) -> {season_path}")
    for p in problems:
        print("WARNING:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
