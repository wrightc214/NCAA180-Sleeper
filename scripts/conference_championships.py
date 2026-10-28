"""
conference_championships.py -- week-12 conference championship games (CCG).

Each league's division winners (weeks 1..last_regular_week; tiebreak Wins, then PointsFor,
no head-to-head) meet in the CCG week. Winner = higher points that week (standard scoring
from 2026). Writes Round="CCG" rows to Postseason_Season.csv; rerun refreshes scores.
A tie for a division title or in a CCG is flagged, never guessed (exit 1).

  python scripts/conference_championships.py [--year 2026] [--data-dir DIR]
"""
import argparse
import sys

import pandas as pd

import _postseason_common as ps


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--data-dir")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, _, _ = ps.paths(a)
    _, cfg = ps.config()
    week = ps.ccg_week()
    per = int(cfg["ccg"].get("divisions_per_league", 2))
    st = ps.standings(year).dropna(subset=["Division"])
    short = {v: k for k, v in ps.league_short().items()}
    rows, problems = [], []
    for (lid, lname), g in st.groupby(["LeagueID", "LeagueName"]):
        champs = []
        for div, d in g.groupby("Division"):
            r = ps.rank(d)
            tied = r[(r["Wins"] == r.iloc[0]["Wins"]) & (r["PointsFor"] == r.iloc[0]["PointsFor"])]
            if len(tied) > 1:
                problems.append(f"{lname} / {div}: division title tied ({', '.join(tied['Team'])})")
                continue
            champs.append(r.iloc[0].to_dict())
        if len(champs) != per:
            problems.append(f"{lname}: {len(champs)} division winner(s), expected {per} -- CCG not paired")
            continue
        champs = ps.rank(pd.DataFrame(champs)).to_dict("records")  # better record listed first
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
