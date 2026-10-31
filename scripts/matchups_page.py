"""
matchups_page.py -- the week's pregame projections and win chance: data/MatchupProjections_Current.csv
and the frozen record in MatchupProjections_Historic.csv (the scoreboard's pregame odds read it).
The Matchups page itself is retired (Chris, 2026-10-30): reports/matchups.html now forwards to the
scoreboard, the one Games page all week.

PREGAME = the week's Tuesday BASELINE snapshot (the FIRST snapshot file for that week). A later
manual snapshot never changes the posted odds (Chris, 2026-10-14). Each week's rows are also
appended ONCE to data/MatchupProjections_Historic.csv, which is never rewritten; that file is
the record of pregame expectations for predictive measures. Game-time projections for awards and
manager stats live separately (gametime_projections.py).

Projected score = each roster's BEST projected lineup: every rostered player's Sleeper projection
(baseline snapshot in data/projections/<season>/ for that week, scored with that league's own
scoring_settings), placed into the league's lineup slots with max_points.best_lineup. It ignores
who is actually in the lineup, so it is the roster's ceiling-by-projection, not the manager's call.

Win chance = Normal CDF of (projected A - projected B) / (SPREAD * sqrt(2)): each team's actual
score lands within about +/-24 points of its kickoff projection (backtest 2021-2025, 4,949 games:
residual sd 24.4; picks the winner 72.9%, calibrated within ~2 pts per bucket). Shown with the
same floor as the weekly report: never 0% or 100%.

Also flags each team's CURRENT Sleeper lineup: starters projected 0 (empty slot, bye, out).
Regular season only (postseason Sleeper pairings are fictional). CWD must be repo root.

  python scripts/matchups_page.py              upcoming week: _Current + _Historic (+ redirect page)
  python scripts/matchups_page.py --week 5     past week: _Historic only (Rank left blank)
"""
import glob
import html
import json
import math
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from max_points import ELIGIBLE, POS_ALIAS, best_lineup  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

OUT = "reports/matchups.html"
OUT_CSV = "data/MatchupProjections_Current.csv"
OUT_HIST = "data/MatchupProjections_Historic.csv"
BAR_MIN_DIST = 120  # below this the two win-bar colors read as the same; switch one to Secondary
SPREAD = float(lcfg.cfg()["spread"])  # per-team sd around the projection (points); re-fit from history each season
LEAGUES = "data/LeagueIDs_AllYears.csv"
DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX", "K", "DEF"]
e = html.escape


def baseline_snapshot(season, wk=None):
    """(week, proj file, lineups file) for the week's FIRST snapshot (the Tuesday baseline).
    wk=None -> the newest week that has any snapshot. Timestamped names sort chronologically."""
    files = sorted(glob.glob(f"data/projections/{season}/wk*_proj.csv"))
    if not files:
        return None
    if wk is None:
        wk = max(int(re.search(r"wk(\d+)_", os.path.basename(f)).group(1)) for f in files)
    week_files = sorted(f for f in files if os.path.basename(f).startswith(f"wk{wk:02d}_"))
    if not week_files:
        return None
    proj = week_files[0]
    return wk, proj, proj.replace("_proj.csv", "_lineups.csv")


def append_historic(g):
    """Append this week's rows to the historic file unless that (Year, Week) is already there.
    Never rewrites existing rows: the first pregame odds recorded for a week are final."""
    if g.empty:
        return False
    yr, wk = int(g["Year"].iloc[0]), int(g["Week"].iloc[0])
    if os.path.exists(OUT_HIST):
        h = pd.read_csv(OUT_HIST, dtype=str)
        if ((h["Year"].astype(int) == yr) & (h["Week"].astype(int) == wk)).any():
            print(f"{OUT_HIST}: {yr} week {wk} already recorded; left unchanged")
            return False
        g.to_csv(OUT_HIST, mode="a", header=False, index=False, columns=list(h.columns))
    else:
        g.to_csv(OUT_HIST, index=False)
    print(f"{OUT_HIST}: appended {yr} week {wk} ({len(g)} games)")
    return True


def slots_by_league(season):
    lg = pd.read_csv(LEAGUES, dtype=str)
    lg = lg[lg["Year"] == str(season)]
    out = {}
    for r in lg.itertuples():
        rp = getattr(r, "RosterPositions", "")
        if isinstance(rp, str) and rp:
            out[r.LeagueID] = [s for s in rp.split(",") if s not in ("BN", "IR", "TAXI")]
    return out


def score(stats, sc):
    return sum(float(v) * sc[k] for k, v in stats.items() if k in sc and isinstance(v, (int, float)))


def win_pct(a, b):
    p = 0.5 * (1 + math.erf((a - b) / (SPREAD * math.sqrt(2)) / math.sqrt(2)))
    return p * 100


def ccg_pairs(season, wk):
    """CCG week only: the conference championship games (written by conference_championships.py)
    as matchup-like rows; None for any other postseason week or when pairings are missing."""
    if wk != int(lcfg.cfg()["schedule"]["ccg_week"]) or not os.path.exists("data/Postseason_Season.csv"):
        return None
    ps = pd.read_csv("data/Postseason_Season.csv", dtype=str)
    ps = ps[(ps["Round"] == "CCG") & (ps["Year"] == str(season)) & (ps["Week"] == str(wk))]
    if ps.empty:
        print(f"Week {wk}: no CCG pairings yet (run conference_championships.py first).")
        return None
    return pd.DataFrame({"LeagueID": ps["LeagueID"], "RosterID": ps["RosterID"],
                         "OpponentRosterID": ps["OpponentRosterID"]})


def build(week=None):
    """week=None: upcoming week (page + _Current + _Historic). week=N: past week, _Historic only."""
    season = max(pc.seasons())
    snap = baseline_snapshot(season, week)
    if snap is None:
        print(f"No projection snapshot{f' for week {week}' if week else ''}; nothing to build.")
        return False
    wk, proj_f, line_f = snap
    ccg = None
    if wk > int(pc.config().get("last_regular_week", 11)):
        ccg = ccg_pairs(season, wk)
        if ccg is None:
            print(f"Week {wk} is postseason; matchups page skipped (pairings are fictional).")
            return False
    proj = pd.read_csv(proj_f, dtype={"PlayerID": str})
    stamp = str(proj["SnapshotUTC"].iloc[0]) if "SnapshotUTC" in proj.columns else ""
    started = proj["GameState"].isin(["in", "post"]).sum() if "GameState" in proj.columns else 0
    if started:  # not pregame (e.g. 2026 wk4's only snapshot was Sunday night): never record it
        print(f"Week {wk} snapshot {stamp} has {started} players whose games had started; not a pregame "
              f"baseline, nothing written.")
        return False
    stats = {r.PlayerID: json.loads(r.Stats) if isinstance(r.Stats, str) and r.Stats else {} for r in proj.itertuples()}
    pos = {r.PlayerID: POS_ALIAS.get(str(r.Position), str(r.Position)) for r in proj.itertuples()}
    scoring = json.load(open(f"data/projections/{season}/scoring.json"))
    scoring = {k: {s: float(v) for s, v in d.items() if isinstance(v, (int, float))} for k, d in scoring.items()}
    slots = slots_by_league(season)
    lines = pd.read_csv(line_f, dtype=str).fillna("")

    teams = {(r.LeagueID, r.RosterID): r.Team for r in pc.teams(season).itertuples()}
    short = pc.league_short()
    rows = {}
    for r in lines.itertuples():
        sc = scoring.get(r.LeagueID, {})
        pts = {p: score(stats.get(p, {}), sc) for p in r.Players.split("|") if p}
        best = best_lineup([(v, pos.get(p, "")) for p, v in pts.items() if pos.get(p) in set().union(*ELIGIBLE.values())],
                           slots.get(r.LeagueID, DEFAULT_SLOTS))
        starters = [p for p in r.Starters.split("|")]
        zero = sum(1 for p in starters if p in ("", "0") or pts.get(p, 0) <= 0)
        cur = round(sum(pts.get(p, 0) for p in starters if p not in ("", "0")), 2)
        rows[(r.LeagueID, r.RosterID)] = {"Best": best, "Current": cur, "ZeroStarters": zero,
                                          "League": short.get(r.LeagueName.strip().upper(), r.LeagueName)}

    rk = {}
    if week is None and os.path.exists(pc.RANKS_CURRENT):  # current poll only fits the upcoming week
        rr = pd.read_csv(pc.RANKS_CURRENT, dtype=str)
        rk = {(r.LeagueID, r.RosterID): int(r.Rank) for r in rr.itertuples()}
    st = standings(season, wk)
    ws = weekly_scores(season, wk)

    m = pc.matchups(season)
    m = m[m["Week"] == wk]
    if ccg is not None:  # CCG week: the real games from Postseason_Season.csv, not Sleeper's placeholders
        m = ccg
    games, done = [], set()
    for r in m.itertuples():
        a, b = (r.LeagueID, r.RosterID), (r.LeagueID, r.OpponentRosterID)
        if frozenset((a, b)) in done or a not in rows or b not in rows:
            continue
        done.add(frozenset((a, b)))
        if rows[b]["Best"] > rows[a]["Best"]:
            a, b = b, a  # projected favorite first
        p = win_pct(rows[a]["Best"], rows[b]["Best"])
        games.append({"Year": season, "Week": wk, "LeagueID": a[0], "League": rows[a]["League"],
                      "RosterID": a[1], "Team": teams.get(a, ""), "Rank": rk.get(a, ""), "Rec": st.get(a, ""),
                      "Proj": rows[a]["Best"], "CurLineup": rows[a]["Current"], "ZeroStarters": rows[a]["ZeroStarters"],
                      "OpponentRosterID": b[1], "OppTeam": teams.get(b, ""), "OppRank": rk.get(b, ""), "OppRec": st.get(b, ""),
                      "OppProj": rows[b]["Best"], "OppCurLineup": rows[b]["Current"], "OppZeroStarters": rows[b]["ZeroStarters"],
                      "WinPct": round(p, 1), "Snapshot": stamp,
                      **every_week_label(teams.get(a, ""), teams.get(b, ""), every_week(ws.get(a, {}), ws.get(b, {})))})
    g = pd.DataFrame(games)
    append_historic(g)
    if week is not None:
        return True
    g.to_csv(OUT_CSV, index=False)
    write_redirect()
    print(f"Wrote {OUT} and {OUT_CSV}: week {wk}, {len(g)} games (snapshot {stamp})")
    return True


def weekly_scores(season, wk):
    """{(LeagueID, RosterID): {week: points}} for regular-season weeks before `wk`."""
    m = pc.matchups(season)
    m = m[(m["Week"] < wk) & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    out = {}
    for r in m.itertuples():
        out.setdefault((r.LeagueID, r.RosterID), {})[int(r.Week)] = float(r.PointsFor)
    return out


def every_week(a, b):
    """A's record vs B if they had played every week so far: compare the two scores week by week."""
    w = l = t = 0
    for k in sorted(set(a) & set(b)):
        if a[k] > b[k]:
            w += 1
        elif a[k] < b[k]:
            l += 1
        else:
            t += 1
    return w, l, t


def every_week_label(ta, tb, rec):
    """Listed from the side of the team with more weekly wins; even records say 'split'."""
    w, l, t = rec
    if w + l + t == 0:
        return {"EveryWeekLeader": "", "EveryWeek": ""}
    tail = f"-{t}" if t else ""
    if w == l:
        return {"EveryWeekLeader": "", "EveryWeek": f"split {w}-{l}{tail}"}
    return {"EveryWeekLeader": ta if w > l else tb, "EveryWeek": f"{max(w, l)}-{min(w, l)}{tail}"}


def standings(season, wk):
    m = pc.matchups(season)
    m = m[(m["Week"] < wk) & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    out = {}
    for k, gg in m.groupby(["LeagueID", "RosterID"]):
        w, l, t = (gg["Outcome"] == "Win").sum(), (gg["Outcome"] == "Loss").sum(), (gg["Outcome"] == "Tie").sum()
        out[k] = f"{w}-{l}" + (f"-{t}" if t else "")
    return out


def write_redirect():
    """The Matchups page is retired (Chris, 2026-10-30): the scoreboard is the one Games page all
    week (projections before kickoff, live scores after). Old links land there."""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="0; url=scoreboard.html"><title>Games</title></head>'
                '<body><p>Matchups moved to the <a href="scoreboard.html">Games page</a>.</p></body></html>\n')


if __name__ == "__main__":
    if "--week" in sys.argv:
        build(int(sys.argv[sys.argv.index("--week") + 1]))
    else:
        build()
