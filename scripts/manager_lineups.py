"""
manager_lineups.py -- start/sit stats per MANAGER (OwnerID), per season and career.

Two stats, both regular season only (weeks 1-11 with a final result), orphan weeks excluded:

LINEUP SKILL (2019 on) = sum(actual - worst) / sum(best - worst) over the manager's games.
  best  = best legal lineup in hindsight (actual points), the same as MaxPoints.
  worst = worst legal lineup from the same roster that week, built only from players who actually
          scored (nonzero points) plus anyone the manager started. A bye / inactive / IR player isn't
          a real alternative; letting zeros fill the worst lineup made every real lineup look good
          (range compressed to 0.61-0.87). This matches the 2026-10-07 prototype (Chris 0.788, #3).
  1.0 = perfect lineup every week, 0 = worst possible every week. Pooled sums, so weeks with
  little real choice (best ~ worst) barely count, and a thin roster can't score ~100% by default.
  Companions: points left on the bench per game (best - actual) and perfect-lineup weeks.

BEAT THE PROJECTION (2026 on; needs game-time projections from gametime_projections.py)
  = actual points of the lineup started - actual points of the AUTOPILOT lineup.
  autopilot = the best lineup by game-time (kickoff) projection: what Sleeper's numbers said to start.
  Positive = the manager's calls outscored the projections. Reported as total, per game and
  weeks won (beat the autopilot) / lost; weeks where the manager started the autopilot lineup
  exactly count as neither.

Players: every player on the roster that week (bench and IR, as in MaxPoints). 2019-2025 from
data/backfill/PlayerPoints_<year>.csv.gz, current season from data/Scores_Season.csv.
Owners: Matchups files (OwnerID "Orphan" = caretaker/vacant/deleted, excluded). league_matchups.py
stamps the CURRENT owner on every week of the season, so for the current season Orphans.csv
corrects mid-season changes: weeks before a roster was orphaned go to its previous owner; weeks
before an orphan was filled are excluded.

Writes:
  data/LineupWeeks_Historic.csv   per team-week 2019 to last season (built when missing or --history)
  data/LineupWeeks_Season.csv     per team-week, current season (every run)
  data/ManagerLineup_Season.csv   per manager per season
  data/ManagerLineup_Career.csv   per manager, all seasons; Qualified = at least CAREER_MIN_GAMES
CWD must be repo root.
"""
import glob
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from max_points import DEFAULT_SLOTS, ELIGIBLE, POS_ALIAS, lineup_pick  # noqa: E402
from week_status import completed_weeks  # noqa: E402

BACKFILL = "data/backfill"
LEAGUES = "data/LeagueIDs_AllYears.csv"
WEEKS_HIST = "data/LineupWeeks_Historic.csv"
WEEKS_SEASON = "data/LineupWeeks_Season.csv"
OUT_SEASON = "data/ManagerLineup_Season.csv"
OUT_CAREER = "data/ManagerLineup_Career.csv"
LAST_REGULAR_WEEK = 11
CAREER_MIN_GAMES = 22  # two full regular seasons
ALL_POS = set().union(*ELIGIBLE.values())


def is_orphan(oid, name):
    n = str(name)
    return str(oid) in ("Orphan", "0") or " Orphan #" in n or n.upper().startswith("DELETED") or n in ("Vacant", "Orphan")


def slots_for(year):
    frames = [pd.read_csv(LEAGUES, dtype=str)]
    if os.path.exists(f"{BACKFILL}/LeagueIDs_2019_2020.csv"):
        frames.append(pd.read_csv(f"{BACKFILL}/LeagueIDs_2019_2020.csv", dtype=str))
    out = {}
    for lg in frames:
        for r in lg[lg["Year"] == str(year)].itertuples():
            rp = getattr(r, "RosterPositions", "")
            if isinstance(rp, str) and rp:
                out[r.LeagueID] = [s for s in rp.split(",") if s not in ("BN", "IR", "TAXI")]
    return out


def pos_of(pid, table):
    if not str(pid).isdigit():
        return "DEF"  # team defenses use the team code as player id
    p = table.get(str(pid), "")
    p = p if isinstance(p, str) else ""
    return POS_ALIAS.get(p, p)


def matchups(year, current):
    if current:
        m = pd.read_csv("data/Matchups_Season.csv", dtype=str)
    elif year <= 2020:
        m = pd.read_csv(f"{BACKFILL}/Matchups_2019_2020.csv", dtype=str)
    else:
        m = pd.read_csv("data/Matchups_Historic.csv", dtype=str)
    m = m[m["Year"] == str(year)].copy()
    m["Week"] = m["Week"].astype(int)
    m = m[(m["IsRegularSeason"].astype(str).str.lower() == "true") & (m["Week"] <= LAST_REGULAR_WEEK)
          & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    if current:
        m = m[m["Week"].isin(completed_weeks(year))]
        m = owner_fixes(m, year)
    m["Orphan"] = [is_orphan(o, n) for o, n in zip(m["OwnerID"], m["OwnerName"])]
    return m


def owner_fixes(m, year):
    """Current season: undo the retroactive owner stamp using the orphan registry."""
    if not os.path.exists("data/Orphans.csv"):
        return m
    o = pd.read_csv("data/Orphans.csv", dtype=str).fillna("")
    for r in o.itertuples():
        key = (m["LeagueName"].str.strip() == r.LeagueName.strip()) & (m["RosterID"] == r.RosterID)
        if r.OrphanedYear == str(year) and r.OrphanedWeek.isdigit() and r.PreviousOwnerID:
            before = key & (m["Week"] < int(r.OrphanedWeek))
            m.loc[before, ["OwnerID", "OwnerName"]] = [r.PreviousOwnerID, r.PreviousOwnerName]
        if r.Status == "Filled" and r.FilledYear == str(year) and r.FilledWeek.isdigit():
            m.loc[key & (m["Week"] < int(r.FilledWeek)), ["OwnerID", "OwnerName"]] = "Orphan"
    return m


def player_points(year, current):
    """DataFrame: LeagueID, Week, RosterID, PlayerID, Points, Started (bool), Pos."""
    if current:
        s = pd.read_csv("data/Scores_Season.csv", dtype=str)
        s = s[s["LeagueYear"] == str(year)]
        p = pd.DataFrame({"LeagueID": s["league_id"], "Week": s["weekNum"].astype(int), "RosterID": s["roster_id"],
                          "PlayerID": s["player_id"], "Points": s["points"].astype(float),
                          "Started": s["is_starter"].str.lower() == "true"})
        pl = pd.read_csv("data/Players.csv", dtype=str)
        table = dict(zip(pl["player_id"], pl["position"]))
        # same fallback as max_points.py: position from the score label ("Name, QB (NYG)")
        for pid, lab in zip(s["player_id"], s["label"]):
            if not isinstance(table.get(pid), str) and isinstance(lab, str):
                hit = pd.Series([lab]).str.extract(r", ([A-Z]+) \(", expand=False).iloc[0]
                if isinstance(hit, str):
                    table[pid] = hit
    else:
        s = pd.read_csv(f"{BACKFILL}/PlayerPoints_{year}.csv.gz", dtype=str)
        p = pd.DataFrame({"LeagueID": s["LeagueID"], "Week": s["Week"].astype(int), "RosterID": s["RosterID"],
                          "PlayerID": s["PlayerID"], "Points": s["Points"].astype(float),
                          "Started": s["Started"].isin(["1", "True", "true"])})
        pl = pd.read_csv(f"{BACKFILL}/PlayerPositions_All.csv", dtype=str)
        table = dict(zip(pl["PlayerID"], pl["Position"]))
    p["Pos"] = [pos_of(x, table) for x in p["PlayerID"]]
    return p


def gametime(year):
    """{week: (proj stats by player, lineups by (LeagueID, RosterID) -> players)} plus scoring."""
    base = f"data/projections/{year}"
    out = {}
    for f in sorted(glob.glob(f"{base}/gametime/wk*_proj.csv")):
        wk = int(os.path.basename(f)[2:4])
        pr = pd.read_csv(f, dtype={"PlayerID": str})
        stats = {r.PlayerID: json.loads(r.Stats) if isinstance(r.Stats, str) and r.Stats else {} for r in pr.itertuples()}
        ln = pd.read_csv(f.replace("_proj.csv", "_lineups.csv"), dtype=str).fillna("")
        out[wk] = (stats, {(r.LeagueID, r.RosterID): [x for x in r.Players.split("|") if x] for r in ln.itertuples()})
    sc = {}
    if out and os.path.exists(f"{base}/scoring.json"):
        sc = {k: {s: float(v) for s, v in d.items() if isinstance(v, (int, float))}
              for k, d in json.load(open(f"{base}/scoring.json")).items()}
    return out, sc


def season_weeks(year, current):
    m = matchups(year, current)
    pts = player_points(year, current)
    slots = slots_for(year)
    gt, scoring = gametime(year) if current else ({}, {})
    if current:
        pl = pd.read_csv("data/Players.csv", dtype=str)
        cur_pos = dict(zip(pl["player_id"], pl["position"]))
    groups = {k: g for k, g in pts.groupby(["LeagueID", "Week", "RosterID"])}
    rows, gaps = [], 0
    for r in m.itertuples():
        g = groups.get((r.LeagueID, r.Week, r.RosterID))
        if g is None:
            gaps += 1
            continue
        actual = round(g.loc[g["Started"], "Points"].sum(), 2)  # every starter, before position filter
        g = g[g["Pos"].isin(ALL_POS)]
        vals, poss = g["Points"].tolist(), g["Pos"].tolist()
        sl = slots.get(r.LeagueID, DEFAULT_SLOTS)
        best = round(sum(vals[i] for i in lineup_pick(vals, poss, sl)), 2)
        real = g[(g["Points"] != 0) | g["Started"]]
        worst = round(sum(real["Points"].iloc[i] for i in lineup_pick(real["Points"].tolist(), real["Pos"].tolist(),
                                                                       sl, worst=True)), 2)
        if actual > best + 0.01:
            gaps += 1  # roster data incomplete (a scoring starter missing a position); skip the week
            continue
        row = {"Year": year, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName.strip(), "Week": r.Week,
               "RosterID": r.RosterID, "OwnerID": "Orphan" if r.Orphan else r.OwnerID,
               "OwnerName": "Orphan" if r.Orphan else r.OwnerName,
               "Actual": actual, "Best": best, "Worst": worst, "Autopilot": "", "BeatProj": ""}
        if r.Week in gt and r.LeagueID in scoring:
            stats, lineups = gt[r.Week]
            roster = lineups.get((r.LeagueID, r.RosterID))
            if roster:
                sc = scoring[r.LeagueID]
                actual_by = dict(zip(g["PlayerID"], g["Points"]))
                ap_pos = [pos_of(p, cur_pos) for p in roster]
                keep = [i for i, ps in enumerate(ap_pos) if ps in ALL_POS]
                proj = [sum(float(stats.get(roster[i], {}).get(k, 0) or 0) * w for k, w in sc.items()) for i in keep]
                pick = lineup_pick(proj, [ap_pos[i] for i in keep], sl)
                auto = round(sum(actual_by.get(roster[keep[i]], 0.0) for i in pick), 2)
                row["Autopilot"], row["BeatProj"] = auto, round(actual - auto, 2)
        rows.append(row)
    if gaps:
        print(f"{year}: {gaps} team-weeks skipped (no player data or incomplete roster data)")
    return pd.DataFrame(rows)


def summarize(w, by):
    w = w[w["OwnerID"] != "Orphan"].copy()
    w["Perfect"] = (w["Best"] - w["Actual"] < 0.005) & (w["Best"] - w["Worst"] > 0.005)
    bp = pd.to_numeric(w["BeatProj"], errors="coerce")
    w["BP"], w["BPW"], w["BPL"] = bp, (bp > 0.005).astype(int), (bp < -0.005).astype(int)
    w["BPG"] = bp.notna().astype(int)
    g = w.sort_values(["Year", "Week"]).groupby(by)
    s = g.agg(OwnerName=("OwnerName", "last"), Seasons=("Year", "nunique"), Games=("Week", "size"),
              Actual=("Actual", "sum"), Best=("Best", "sum"), Worst=("Worst", "sum"),
              PerfectWeeks=("Perfect", "sum"), BeatProjGames=("BPG", "sum"), BeatProjTotal=("BP", "sum"),
              BeatProjWins=("BPW", "sum"), BeatProjLosses=("BPL", "sum"),
              LastTeam=("LeagueName", "last")).reset_index()
    span = s["Best"] - s["Worst"]
    s["LineupSkill"] = ((s["Actual"] - s["Worst"]) / span.where(span > 0)).round(3)
    s["PtsLeftPerGame"] = ((s["Best"] - s["Actual"]) / s["Games"]).round(2)
    s["BeatProjPerGame"] = (s["BeatProjTotal"] / s["BeatProjGames"].where(s["BeatProjGames"] > 0)).round(2)
    s.loc[s["BeatProjGames"] == 0, "BeatProjTotal"] = float("nan")
    s["BeatProjTotal"] = s["BeatProjTotal"].round(2)
    for c in ("Actual", "Best", "Worst"):
        s[c] = s[c].round(2)
    s = s.drop(columns=["LastTeam"])
    return s.sort_values("LineupSkill", ascending=False)


def main():
    year = int(pd.read_csv(LEAGUES, dtype=str)["Year"].astype(int).max())
    if "--history" in sys.argv or not os.path.exists(WEEKS_HIST):
        hist = pd.concat([season_weeks(y, False) for y in range(2019, year)
                          if os.path.exists(f"{BACKFILL}/PlayerPoints_{y}.csv.gz")], ignore_index=True)
        hist.to_csv(WEEKS_HIST, index=False)
        print(f"Wrote {WEEKS_HIST}: {len(hist)} team-weeks")
    hist = pd.read_csv(WEEKS_HIST, dtype={"LeagueID": str, "RosterID": str, "OwnerID": str})
    cur = season_weeks(year, True)
    cur.to_csv(WEEKS_SEASON, index=False)
    print(f"Wrote {WEEKS_SEASON}: {len(cur)} team-weeks "
          f"({cur['BeatProj'].astype(str).ne('').sum()} with game-time projections)")
    allw = pd.concat([hist, cur], ignore_index=True)
    allw["OwnerID"] = allw["OwnerID"].astype(str)

    season = summarize(allw, ["Year", "OwnerID"])
    season.drop(columns=["Seasons"]).sort_values(["Year", "LineupSkill"], ascending=[False, False]).to_csv(OUT_SEASON, index=False)
    career = summarize(allw, ["OwnerID"])
    career["Qualified"] = career["Games"] >= CAREER_MIN_GAMES
    career.to_csv(OUT_CAREER, index=False)
    print(f"Wrote {OUT_SEASON} ({len(season)} rows) and {OUT_CAREER} "
          f"({len(career)} managers, {int(career['Qualified'].sum())} qualified)")


if __name__ == "__main__":
    main()
