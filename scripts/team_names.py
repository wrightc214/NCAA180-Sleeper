"""Team names over time. Identity = roster slot (LeagueName + RosterID); names are labels.

Sources (no year hardcoded):
  data/TeamNames_Historic.csv  Year, LeagueName, RosterID, Team, Basis  (completed seasons)
  data/Teams.csv               current names (used for any year not in the historic file)
  data/Colors - Teams.csv      colors keyed by school name (current AND former names)

Display rules (Chris, 2026-10-07):
  - Snapshot views (one season: a bracket, bowl results, a past poll) and record-book entries
    (one moment: highest score, game of the year): that season's name AND that season's colors.
  - Multi-year views (team page, all-time tables): current name and current colors;
    the team page lists former names with their years.
  - Colors for a former name with no palette row fall back to the slot's current colors;
    retired slots with no current team (e.g. 2019 American, 2020 Southland) use `default`.

No duplicate names (Chris, 2026-10-08): a school name may appear on only one slot per season.
A rename that would duplicate another slot's name is rejected and the slot keeps its previous name.

Fixing a name: edit one row in TeamNames_Historic.csv (or Teams.csv for the current season).
Rollover: append the finished season's Teams.csv names to TeamNames_Historic.csv.
Check: python scripts/team_names.py --check
"""
import os
import re
import sys

import pandas as pd

HIST = "data/TeamNames_Historic.csv"
CURRENT = "data/Teams.csv"
COLORS = "data/Colors - Teams.csv"

_cache = {}


def norm(s):
    return re.sub(r"[^a-z0-9&]", "", str(s).lower())


def _hist():
    if "h" not in _cache:
        h = pd.read_csv(HIST, dtype=str, encoding="utf-8-sig") if os.path.exists(HIST) else pd.DataFrame(
            columns=["Year", "LeagueName", "RosterID", "Team", "Basis"])
        h["LeagueName"] = h["LeagueName"].str.strip()
        _cache["h"] = h
    return _cache["h"]


def _current():
    if "c" not in _cache:
        c = pd.read_csv(CURRENT, dtype=str, encoding="utf-8-sig").rename(
            columns={"League": "LeagueName", "Roster ID": "RosterID"})
        c["LeagueName"] = c["LeagueName"].str.strip()
        _cache["c"] = c[["Team", "LeagueName", "RosterID"]]
    return _cache["c"]


def names(year):
    """DataFrame LeagueName, RosterID, Team for a season (current names if not historic)."""
    h = _hist()
    y = h[h["Year"] == str(year)]
    if len(y):
        return y[["LeagueName", "RosterID", "Team"]].reset_index(drop=True)
    return _current().copy()


def season_name(year, league, roster_id):
    n = names(year)
    r = n[(n["LeagueName"] == str(league).strip()) & (n["RosterID"] == str(roster_id))]
    return r["Team"].iloc[0] if len(r) else None


def current_name(league, roster_id):
    c = _current()
    r = c[(c["LeagueName"] == str(league).strip()) & (c["RosterID"] == str(roster_id))]
    return r["Team"].iloc[0] if len(r) else None


def slot(year, name):
    """(LeagueName, RosterID) a school name belonged to in that season, or None."""
    n = names(year)
    r = n[n["Team"].map(norm) == norm(name)]
    return (r["LeagueName"].iloc[0], r["RosterID"].iloc[0]) if len(r) == 1 else None


def former_names(league, roster_id):
    """[(name, first_year, last_year)] for a slot, oldest first, current name excluded."""
    h = _hist()
    x = h[(h["LeagueName"] == str(league).strip()) & (h["RosterID"] == str(roster_id))].copy()
    cur = current_name(league, roster_id)
    x["Y"] = x["Year"].astype(int)
    out = []
    for name, g in x.sort_values("Y").groupby((x.sort_values("Y")["Team"] != x.sort_values("Y")["Team"].shift()).cumsum()):
        t = g["Team"].iloc[0]
        if norm(t) != norm(cur):
            out.append((t, int(g["Y"].min()), int(g["Y"].max())))
    return out


def colors_row(name):
    """Colors - Teams.csv row (dict) for a school name, or None."""
    if "col" not in _cache:
        c = pd.read_csv(COLORS, dtype=str, encoding="utf-8-sig").fillna("")
        _cache["col"] = {norm(r["Team"]): r for r in c.to_dict("records")}
    return _cache["col"].get(norm(name))


def display(year, league, roster_id, snapshot=True):
    """(name, colors_row) to show. snapshot=True: that season's name/colors; False: current."""
    cur = current_name(league, roster_id)
    if not snapshot:
        return cur, colors_row(cur) if cur else None
    nm = season_name(year, league, roster_id) or cur
    return nm, colors_row(nm) or (colors_row(cur) if cur else None)


def check():
    h = _hist()
    problems = 0
    for y, g in h.groupby("Year"):
        d = g[g.duplicated(["LeagueName", "RosterID"], keep=False)]
        if len(d):
            problems += 1
            print(f"{y}: duplicate slots {d[['LeagueName','RosterID']].values.tolist()}")
        d = g[g["Team"].map(norm).duplicated(keep=False)]
        if len(d):
            problems += 1
            print(f"{y}: same name on two slots {d['Team'].tolist()}")
    c = _current()
    d = c[c["Team"].map(norm).duplicated(keep=False)]
    if len(d):
        problems += 1
        print(f"current (Teams.csv): same name on two slots {d['Team'].tolist()}")
    nocol = sorted({t for t in h["Team"] if not colors_row(t)})
    print(f"{len(nocol)} names with no colors (backlog): {', '.join(nocol)}")
    return problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(1 if check() else 0)
    print(__doc__)
