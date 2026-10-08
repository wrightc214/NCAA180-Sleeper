"""
apply_orphan_overrides.py -- relabel specific historic team-seasons as orphans, from
data/OrphanOverrides_Historic.csv (Year, LeagueName, RosterID, OwnerID, OwnerName, Note).

Why: the "one team per owner" rule had two historic exceptions (a 2019 founder running
6 teams; a 2021 owner with 2). Chris's ruling: those extra teams are orphans, so career /
manager stats never merge them into one person. Same label as the live orphan rule:
OwnerID = OwnerName = "Orphan"; team identity stays LeagueID/LeagueName + RosterID.

Only rows where the listed owner holds the listed slot are changed (a later owner of the
same slot is untouched). Idempotent: rerun safely after any history rebuild.

Handles, by columns present:
  OwnerID/OwnerName + RosterID      Matchups, Standings, Rosters_Players, TeamNames
  OpponentRosterID + OpponentName   opponent side of Matchups
  RosterIDs + OwnerIDs (lists)      Transactions (the owner at that roster's position)
  Picked_By + RosterID              DraftPicks (Year from the LeagueIDs files)

Usage: python scripts/apply_orphan_overrides.py FILE [FILE ...]
CWD must be repo root.
"""
import ast
import glob
import sys

import pandas as pd

OVERRIDES = "data/OrphanOverrides_Historic.csv"
ORPHAN = "Orphan"


def norm(s):
    return str(s).strip().upper()


def league_years():
    """LeagueID -> Year from every LeagueIDs file present."""
    out = {}
    for f in glob.glob("data/LeagueIDs_AllYears.csv") + glob.glob("data/backfill/LeagueIDs_*.csv"):
        d = pd.read_csv(f, dtype=str)
        out.update(dict(zip(d["LeagueID"], d["Year"])))
    return out


def main(files):
    ov = pd.read_csv(OVERRIDES, dtype=str, encoding="utf-8-sig")
    keys = {(r.Year, norm(r.LeagueName), str(r.RosterID)): r.OwnerID for r in ov.itertuples()}
    years = league_years()
    for f in files:
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        yr = d["Year"] if "Year" in d.columns else d["LeagueID"].map(years).fillna("")
        lg = d["LeagueName"].map(norm)
        changed = 0
        if {"OwnerID", "RosterID"} <= set(d.columns):
            hit = [keys.get((y, l, r)) == o for y, l, r, o in zip(yr, lg, d["RosterID"], d["OwnerID"])]
            hit = pd.Series(hit, index=d.index)
            changed += int(hit.sum())
            d.loc[hit, "OwnerID"] = ORPHAN
            if "OwnerName" in d.columns:
                d.loc[hit, "OwnerName"] = ORPHAN
        if {"OpponentRosterID", "OpponentName"} <= set(d.columns):
            hit = pd.Series([(y, l, r) in keys and n != ORPHAN for y, l, r, n in
                             zip(yr, lg, d["OpponentRosterID"], d["OpponentName"])], index=d.index)
            # only where the opponent was the listed owner that season
            owner_names = dict(zip(ov["OwnerID"], ov["OwnerName"]))
            hit &= d["OpponentName"].isin(set(owner_names.values()))
            changed += int(hit.sum())
            d.loc[hit, "OpponentName"] = ORPHAN
        if {"RosterIDs", "OwnerIDs"} <= set(d.columns):
            def fix(row):
                try:
                    rids, oids = ast.literal_eval(row["RosterIDs"]), ast.literal_eval(row["OwnerIDs"])
                except (ValueError, SyntaxError):
                    return row["OwnerIDs"], 0
                n = 0
                for i, (rid, oid) in enumerate(zip(rids, oids)):
                    if keys.get((row["_y"], row["_l"], str(rid))) == str(oid):
                        oids[i] = ORPHAN
                        n += 1
                return (str(oids), n) if n else (row["OwnerIDs"], 0)
            tmp = d.assign(_y=yr, _l=lg)
            res = tmp.apply(fix, axis=1)
            d["OwnerIDs"] = [x[0] for x in res]
            changed += sum(x[1] for x in res)
        if {"Picked_By", "RosterID"} <= set(d.columns):
            hit = pd.Series([keys.get((y, l, r)) == p for y, l, r, p in zip(yr, lg, d["RosterID"], d["Picked_By"])],
                            index=d.index)
            changed += int(hit.sum())
            d.loc[hit, "Picked_By"] = ORPHAN
        d.to_csv(f, index=False)
        print(f"{f}: {changed} value(s) relabeled")


if __name__ == "__main__":
    main(sys.argv[1:])
