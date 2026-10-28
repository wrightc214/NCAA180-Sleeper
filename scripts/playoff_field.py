"""
playoff_field.py -- the playoff field: auto bids + at-large.

Settings (config/league.json -> postseason.playoff):
  field_size            total teams (32)
  auto_bids_per_league  whole number; filled in auto_bid_order (ccg_winner, then ccg_loser, ...)
  auto_bid_leagues      "all" (only option for now)
At-large spots = field_size - auto bids (calculated, never typed). At-large ranking = regular
season only (weeks 1..last_regular_week), Wins then PointsFor; a tie across the last spot is
flagged, never guessed (exit 1). Needs every CCG final.

  python scripts/playoff_field.py [--year 2026] [--data-dir DIR]
"""
import argparse
import os
import sys

import pandas as pd

import _postseason_common as ps


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--data-dir")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, field_path, _ = ps.paths(a)
    _, cfg = ps.config()
    pc = cfg["playoff"]
    if pc.get("auto_bid_leagues", "all") != "all":
        sys.exit("FATAL: only auto_bid_leagues = 'all' is supported so far")
    n_auto = int(pc["auto_bids_per_league"])
    order = pc["auto_bid_order"][:n_auto]
    if len(order) < n_auto:
        sys.exit(f"FATAL: auto_bids_per_league={n_auto} but auto_bid_order defines only {len(pc['auto_bid_order'])} sources")

    df = ps.read_season(season_path)
    ccg = df[(df["Year"].astype(str) == str(year)) & (df["Round"] == "CCG")]
    if ccg.empty or (ccg["Status"] != "Final").any() or (ccg["Outcome"] == "Tie").any():
        sys.exit(f"FATAL: every CCG must be final (and not tied) before the field can be set ({season_path})")
    st = ps.standings(year)
    auto = []
    for gid, g in ccg.groupby("GameID"):
        src = {"ccg_winner": g[g["Outcome"] == "Win"], "ccg_loser": g[g["Outcome"] == "Loss"]}
        for o in order:
            for _, r in src[o].iterrows():
                auto.append((r["LeagueID"], str(r["RosterID"]), {"ccg_winner": "Auto (CCG winner)", "ccg_loser": "Auto (CCG loser)"}.get(o, f"Auto ({o})")))
    keys = {(l, r) for l, r, _ in auto}
    n_at = int(pc["field_size"]) - len(keys)
    if n_at < 0:
        sys.exit(f"FATAL: {len(keys)} auto bids exceed field size {pc['field_size']}")
    pool = ps.rank(st[[(l, r) not in keys for l, r in zip(st["LeagueID"], st["RosterID"])]])
    rows, complete = [], True
    for l, r, bid in auto:
        t = st[(st["LeagueID"] == l) & (st["RosterID"] == r)].iloc[0]
        rows.append({**t.to_dict(), "BidType": bid})
    if n_at:
        cut = pool.iloc[n_at - 1]
        same = pool[(pool["Wins"] == cut["Wins"]) & (pool["PointsFor"] == cut["PointsFor"])]
        above = pool[(pool["Wins"] > cut["Wins"]) | ((pool["Wins"] == cut["Wins"]) & (pool["PointsFor"] > cut["PointsFor"]))]
        if len(above) + len(same) > n_at:
            complete = False
            print(f"WARNING: {len(same)} teams tied at {cut['Wins']} wins / {cut['PointsFor']} for the last "
                  f"{n_at - len(above)} at-large spot(s): {', '.join(same['Team'])} -- resolve manually")
            rows += [{**t, "BidType": "At-Large"} for t in above.to_dict("records")]
            rows += [{**t, "BidType": "Tied - Unresolved"} for t in same.to_dict("records")]
        else:
            rows += [{**t, "BidType": "At-Large"} for t in pool.head(n_at).to_dict("records")]
    out = pd.DataFrame(rows)
    out.insert(0, "Year", year)
    cols = ["Year", "LeagueID", "LeagueName", "RosterID", "Team", "OwnerName", "Division", "BidType", "Wins", "Losses", "PointsFor"]
    old = pd.read_csv(field_path, dtype=str) if os.path.exists(field_path) else pd.DataFrame(columns=cols)
    old = old[old["Year"].astype(str) != str(year)] if len(old) else old
    pd.concat([old, out[cols]], ignore_index=True).to_csv(field_path, index=False)
    print(f"Playoff field {year}: {len(keys)} auto + {n_at} at-large = {pc['field_size']} -> {field_path}")
    sys.exit(0 if complete else 1)


if __name__ == "__main__":
    main()
