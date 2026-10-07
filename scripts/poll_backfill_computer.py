"""
poll_backfill_computer.py -- ONE-TIME: the computer ranking (wins, then points) for every
regular-season week of past seasons -> data/Poll_Historic.csv (PollType Computer), and for
the current season's finished weeks not yet in data/Poll_Season.csv.

Run once, verify, then delete (repo's run-once-then-delete convention). Human polls for
past seasons are added separately from the commissioner's sheets.

Team = the slot's current Teams.csv name (2021-2025 slot names that differed, e.g. a
renamed slot, still show today's name; identity is LeagueID + RosterID). 2019-2020 are
added once the history-backfill branch merges.

Usage: python scripts/poll_backfill_computer.py [--years 2021 2022 ...]
CWD must be repo root.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from poll_aggregate import frame  # noqa: E402


def year_rows(cfg, year, weeks):
    m = pc.matchups(year)
    teams = pc.teams(year)
    out, prev = [], {}
    for w in weeks:
        st = pc.standings_through(cfg, m, w)
        order = pc.computer_order(st)
        cr = {k: i + 1 for i, k in enumerate(order)}
        df = frame(year, w, "Computer", order, list(range(1, len(order) + 1)), ["Computer"] * len(order),
                   {}, {}, {}, 1, cr, st, teams, prev, "backfill")
        prev = cr
        out.append(df)
    return pd.concat(out, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int)
    args = ap.parse_args()
    cfg = pc.config()
    last = int(cfg.get("last_regular_week", 11))
    lg = pd.read_csv(pc.LEAGUE_IDS, dtype=str)
    current = int(lg["Year"].astype(int).max())
    years = args.years or sorted(int(y) for y in lg["Year"].unique())

    hist = []
    for y in years:
        if y == current:
            from week_status import completed_weeks
            done = [w for w in completed_weeks(y) if w <= last]
            have = set()
            if os.path.exists(pc.POLL_SEASON):
                s = pd.read_csv(pc.POLL_SEASON, dtype=str)
                have = set(s.loc[(s["Year"] == str(y)) & (s["PollType"] == "Computer"), "ThroughWeek"].astype(int))
            todo = [w for w in done if w not in have]
            if todo:
                df = year_rows(cfg, y, list(range(1, max(todo) + 1)))
                df = df[df["ThroughWeek"].isin(todo)]
                old = pd.read_csv(pc.POLL_SEASON, dtype=str) if os.path.exists(pc.POLL_SEASON) else pd.DataFrame(columns=pc.POLL_COLS)
                new = pd.concat([old, df.astype(str)], ignore_index=True)
                new = new.sort_values(["Year", "PollType", "ThroughWeek", "Rank"],
                                      key=lambda c: c.astype(int) if c.name in ("Year", "ThroughWeek", "Rank") else c)
                new.to_csv(pc.POLL_SEASON, index=False)
                print(f"{y}: computer ranking weeks {todo} -> {pc.POLL_SEASON}")
            continue
        df = year_rows(cfg, y, list(range(1, last + 1)))
        miss = (df["Team"] == "").sum()
        if miss:
            print(f"WARNING {y}: {miss} rows with no Teams.csv name")
        hist.append(df)
        print(f"{y}: {df['ThroughWeek'].nunique()} weeks, #1 final = {df[(df['ThroughWeek'] == last) & (df['Rank'] == 1)]['Team'].iloc[0]}")
    if hist:
        h = pd.concat(hist, ignore_index=True).astype(str)
        if os.path.exists(pc.POLL_HISTORIC):
            old = pd.read_csv(pc.POLL_HISTORIC, dtype=str)
            old = old[~((old["PollType"] == "Computer") & old["Year"].isin(h["Year"].unique()))]
            h = pd.concat([old, h], ignore_index=True)
        h.to_csv(pc.POLL_HISTORIC, index=False)
        print(f"Wrote {pc.POLL_HISTORIC}: {len(h)} rows")


if __name__ == "__main__":
    main()
