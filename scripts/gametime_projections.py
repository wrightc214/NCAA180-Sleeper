"""
gametime_projections.py -- GAME-TIME projections for COMPLETED weeks (awards + manager stats).

Two projection sets, kept apart on purpose (Chris, 2026-10-14):
  PREGAME   = Tuesday baseline snapshot of the UPCOMING week (projection_snapshot.py), used for
              predictive measures (matchups page win chance, MatchupProjections_Historic.csv).
              Never overwritten or changed by anything here.
  GAME-TIME = this script. After a week ends, Sleeper's projections feed still serves each
              player's kickoff-time projection for that week (matched the app's pregame team
              numbers to the cent, research 2026-10-07). Used for awards and manager stats
              (beat-the-projection, lineup decisions), with the lineups managers actually started.

For every completed week of the current season that has no game-time file yet, writes:
  data/projections/<season>/gametime/wk<WW>_proj.csv     one row per rostered player:
      PlayerID, Position, NFLTeam, ProjPPR, Stats (raw projected stat line, JSON)
  data/projections/<season>/gametime/wk<WW>_lineups.csv  one row per roster:
      LeagueID, LeagueName, RosterID, Starters (ordered, "|"), Players ("|")
  data/TeamProjectionsGametime_Season.csv (appended):
      Year, Week, LeagueID, LeagueName, RosterID, ProjStarters (game-time projection of the
      lineup actually started), ProjBest (best possible lineup by game-time projection),
      ZeroStarters (started slots projected <= 0: empty, bye, out), PulledUTC
Existing weeks are skipped, never rewritten. To redo a week, delete its files and rows by hand.
The gametime/ subfolder keeps these out of matchups_page.py's baseline glob.
CWD must be repo root.
"""
import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from max_points import DEFAULT_SLOTS, ELIGIBLE, POS_ALIAS, best_lineup  # noqa: E402
from projection_snapshot import SLEEPER, get, note, projections  # noqa: E402
from week_status import completed_weeks  # noqa: E402

TEAM_FILE = "data/TeamProjectionsGametime_Season.csv"
LEAGUES = "data/LeagueIDs_AllYears.csv"
MIN_PLAYERS = 100  # fewer projections than this = feed problem; write nothing for that week
ALL_POS = set().union(*ELIGIBLE.values())


def score(stats, sc):
    return round(sum(float(stats.get(k, 0) or 0) * w for k, w in sc.items()), 2)


def main():
    state = get(f"{SLEEPER}/state/nfl")
    season = str(state.get("season"))
    weeks = completed_weeks(season)
    if not weeks:
        note("notice", f"Game-time projections: no completed weeks in {season}")
        return

    lg = pd.read_csv(LEAGUES, dtype=str)
    lg = lg[lg["Year"] == season]
    if lg.empty:
        note("error", f"No leagues for season {season} in {LEAGUES}")
        sys.exit(1)
    slots = {r.LeagueID: [s for s in str(r.RosterPositions).split(",") if s not in ("BN", "IR", "TAXI")]
             for r in lg.itertuples() if isinstance(r.RosterPositions, str) and r.RosterPositions}

    out_dir = os.path.join("data", "projections", season, "gametime")
    os.makedirs(out_dir, exist_ok=True)
    done = set()
    if os.path.exists(TEAM_FILE):
        t = pd.read_csv(TEAM_FILE, dtype=str)
        done = set(t.loc[t["Year"] == season, "Week"].astype(int))
    todo = [w for w in weeks if w not in done and not os.path.exists(os.path.join(out_dir, f"wk{w:02d}_proj.csv"))]
    if not todo:
        print(f"Game-time projections: {season} weeks {weeks[0]}-{weeks[-1]} already recorded")
        return

    players = pd.read_csv("data/Players.csv", dtype=str).set_index("player_id")
    scoring = {r.LeagueID: {k: float(v) for k, v in (get(f"{SLEEPER}/league/{r.LeagueID}").get("scoring_settings")
                                                     or {}).items() if isinstance(v, (int, float))}
               for r in lg.itertuples()}
    pulled = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%MZ")
    team_rows, failed = [], []
    for wk in todo:
        proj = projections(season, wk)
        if len(proj) < MIN_PLAYERS:
            failed.append(wk)
            note("error", f"Game-time projections {season} wk{wk}: only {len(proj)} players; week skipped")
            continue
        lineups, rostered, wk_rows = [], set(), []
        for r in lg.itertuples():
            sc = scoring[r.LeagueID]
            for m in get(f"{SLEEPER}/league/{r.LeagueID}/matchups/{wk}") or []:
                starters = [str(p) for p in (m.get("starters") or [])]
                plist = [str(p) for p in (m.get("players") or [])]
                rostered.update(plist)
                lineups.append({"Season": season, "Week": wk, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                                "RosterID": m.get("roster_id"), "Starters": "|".join(starters),
                                "Players": "|".join(plist)})
                pts = {p: score(proj.get(p, {}), sc) for p in plist}
                pos = {p: POS_ALIAS.get(str(players["position"].get(p, "")), str(players["position"].get(p, "")))
                       if p in players.index else "DEF" for p in plist}  # DEF ids are team codes
                st_pts = [score(proj.get(p, {}), sc) for p in starters if p not in ("", "0")]
                wk_rows.append({"Year": season, "Week": wk, "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                                "RosterID": m.get("roster_id"),
                                "ProjStarters": round(sum(st_pts), 2),
                                "ProjBest": best_lineup([(v, pos[p]) for p, v in pts.items() if pos[p] in ALL_POS],
                                                        slots.get(r.LeagueID, DEFAULT_SLOTS)),
                                "ZeroStarters": sum(1 for p in starters if p in ("", "0") or score(proj.get(p, {}), sc) <= 0),
                                "PulledUTC": pulled})
        prow = []
        for pid in sorted(rostered):
            team = players["team"].get(pid, "") if pid in players.index else pid
            pos = players["position"].get(pid, "") if pid in players.index else "DEF"
            st = proj.get(pid, {})
            prow.append({"Season": season, "Week": wk, "PlayerID": pid,
                         "Position": pos if isinstance(pos, str) else "",
                         "NFLTeam": team if isinstance(team, str) else "", "ProjPPR": st.get("pts_ppr", ""),
                         "Stats": json.dumps({k: v for k, v in st.items() if isinstance(v, (int, float)) and v},
                                             separators=(",", ":"), sort_keys=True)})
        pd.DataFrame(lineups).to_csv(os.path.join(out_dir, f"wk{wk:02d}_lineups.csv"), index=False)
        pd.DataFrame(prow).to_csv(os.path.join(out_dir, f"wk{wk:02d}_proj.csv"), index=False)
        team_rows += wk_rows
        print(f"{season} wk{wk}: {len(lineups)} lineups, {len(prow)} players")

    if team_rows:
        new = pd.DataFrame(team_rows)
        new.to_csv(TEAM_FILE, mode="a", header=not os.path.exists(TEAM_FILE), index=False)
        note("notice", f"Game-time projections {season}: added weeks "
                       f"{sorted(new['Week'].unique().tolist())} ({len(new)} team-weeks)")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
