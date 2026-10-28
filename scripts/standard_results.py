"""One place that puts matchup rows on standard (common-scheme) scoring.

Rules (Chris, 2026-10-08 / 2026-10-15):
  - Scores are SHOWN on standard scoring in every season (data/ScoresStandard_*.csv).
  - Results: from config postseason.standard_scoring_from (2026) W/L/T are decided on the
    standard scores. Earlier seasons keep Sleeper's official outcome (footnoted elsewhere).

apply(m) takes matchup rows (Year, LeagueID, Week, RosterID, OpponentRosterID, PointsFor,
PointsAgainst, Outcome; any dtype) and returns a copy where
  PointsFor / PointsAgainst = standard points (official where no standard score exists)
  Outcome                   = standard result for standard seasons (rows with an Outcome only)
  PointsOfficial, PointsAgainstOfficial, OutcomeOfficial = Sleeper's numbers, kept for notes.
Lineup-efficiency stats (max points, bench points) stay on Sleeper's player points.
"""
import os

import pandas as pd

import league_config as lcfg

FILES = ("data/ScoresStandard_Historic.csv", "data/ScoresStandard_Season.csv")
RESULTS = {"Win", "Loss", "Tie"}
_cache = {}


def standard_from():
    return int(lcfg.cfg()["postseason"]["standard_scoring_from"])


def _scores():
    key = tuple((f, os.path.getmtime(f)) for f in FILES if os.path.exists(f))
    if key not in _cache:
        out = {}
        for f, _ in key:
            s = pd.read_csv(f, dtype=str)
            for y, lid, w, r, p in zip(s["Year"], s["LeagueID"], s["Week"], s["RosterID"], s["PointsStandard"]):
                out[(int(y), str(lid), int(w), str(r).replace(".0", ""))] = float(p)
        _cache.clear()
        _cache[key] = out
    return _cache[key]


def _rid(v):
    return "" if pd.isna(v) else str(v).replace(".0", "")


def apply(m):
    a = m.copy()
    if a.empty:
        return a
    std = _scores()
    years = pd.to_numeric(a["Year"], errors="coerce").astype("Int64")
    weeks = pd.to_numeric(a["Week"], errors="coerce").astype("Int64")
    lids, rids, opps = a["LeagueID"].astype(str), a["RosterID"].map(_rid), a["OpponentRosterID"].map(_rid)
    pf = pd.to_numeric(a["PointsFor"], errors="coerce")
    pa = pd.to_numeric(a["PointsAgainst"], errors="coerce")
    a["PointsOfficial"], a["PointsAgainstOfficial"], a["OutcomeOfficial"] = pf, pa, a["Outcome"]

    def look(y, l, w, r, fallback):
        if pd.isna(y) or pd.isna(w):
            return fallback
        return std.get((int(y), l, int(w), r), fallback)

    a["PointsFor"] = [look(y, l, w, r, p) for y, l, w, r, p in zip(years, lids, weeks, rids, pf)]
    a["PointsAgainst"] = [look(y, l, w, o, p) if o else p for y, l, w, o, p in zip(years, lids, weeks, opps, pa)]

    first = standard_from()
    cur = (years >= first).fillna(False) & a["Outcome"].isin(RESULTS) & a["PointsFor"].notna() & a["PointsAgainst"].notna()
    if cur.any():
        missing = [(int(y), int(w)) for y, l, w, r, c in zip(years, lids, weeks, rids, cur)
                   if c and (int(y), l, int(w), r) not in std]
        if missing:
            print(f"WARNING: {len(missing)} {first}+ team-weeks have no standard score yet "
                  f"(e.g. {sorted(set(missing))[:3]}); Sleeper's result used for them. Run standard_scores_season.py.")
        f, ag = a.loc[cur, "PointsFor"].astype(float).round(2), a.loc[cur, "PointsAgainst"].astype(float).round(2)
        a.loc[cur, "Outcome"] = ["Win" if x > y else "Loss" if x < y else "Tie" for x, y in zip(f, ag)]
    return a
