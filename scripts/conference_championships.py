"""
conference_championships.py -- week-12 conference championship games (CCG).

Each league's division winners (weeks 1..last_regular_week) meet in the CCG week.
Division order (Chris, 2026-10-30, Sleeper default): win percentage (ties count half),
then points for, then head-to-head among teams still exactly tied. A tie that survives all
three is flagged, never guessed (exit 1). Results and points use standard scoring from 2026.
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


def division_order(d, games):
    """Rows of one division, best first: win %, points for, then head-to-head among exact ties.
    Returns (ordered rows, tied_at_top) -- tied_at_top lists teams still tied for first."""
    d = d.copy()
    gp = d["Wins"] + d["Losses"] + d["Ties"]
    d["Pct"] = ((d["Wins"] + 0.5 * d["Ties"]) / gp.where(gp > 0, 1)).round(6)
    d = d.sort_values(["Pct", "PointsFor"], ascending=False, kind="mergesort").reset_index(drop=True)
    top = d[(d["Pct"] == d.iloc[0]["Pct"]) & (d["PointsFor"] == d.iloc[0]["PointsFor"])]
    if len(top) < 2:
        return d, []
    ids = set(top["RosterID"].astype(str))
    lid = top.iloc[0]["LeagueID"]
    h = games[(games["LeagueID"] == lid) & games["RosterID"].astype(str).isin(ids)
              & games["OpponentRosterID"].astype(str).isin(ids)]
    pts = {r: (h[h["RosterID"].astype(str) == r]["Res"] == "Win").sum()
           + 0.5 * (h[h["RosterID"].astype(str) == r]["Res"] == "Tie").sum() for r in ids}
    best = max(pts.values())
    leaders = [r for r, v in pts.items() if v == best]
    if len(leaders) > 1:
        return d, list(top[top["RosterID"].astype(str).isin(leaders)]["Team"])
    first = d[d["RosterID"].astype(str) == leaders[0]]
    return pd.concat([first, d.drop(first.index)]).reset_index(drop=True), []


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
            r, tied = division_order(d, games)
            if tied:
                problems.append(f"{lname} / {div}: division title tied after head-to-head ({', '.join(tied)})")
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
