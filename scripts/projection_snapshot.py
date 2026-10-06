"""
projection_snapshot.py -- capture PREGAME expectations before kickoffs (raw data for the
Exceeding Expectations award, pregame projections, and later analysis). Past projections
cannot be fetched after the fact, so this runs on a schedule around kickoff windows.

Each run writes two NEW files (never rewritten, so git growth stays small):
  data/projections/<season>/wk<WW>_<stamp>Z_lineups.csv  one row per roster (180):
      LeagueID, LeagueName, RosterID, Starters (ordered, "|"-joined), Players ("|")
  data/projections/<season>/wk<WW>_<stamp>Z_proj.csv     one row per player rostered in
      any league: PlayerID, Position, NFLTeam, GameState (ESPN pre/in/post), Kickoff,
      ProjPPR, Stats (raw projected stat line, JSON)
  data/projections/<season>/scoring.json  each league's scoring_settings (only when changed)
Projected points for any league = sum(stat x that league's scoring weight).
How to use later: a starter's pregame projection = the latest snapshot taken while his
GameState was "pre"; his lineup status from the lineups file of that same snapshot.
Baseline: the weekly update runs this with FORCE=1 right after the week advances, so each
week has a snapshot even if every game-day run failed.

Skips (writes nothing) when no NFL game kicks off within the next WINDOW_HOURS, unless
FORCE=1 (manual runs). Sleeper projections come from Sleeper's public (unofficial, read-
only) projections feed; if it fails the run exits 1 so the workflow flags it.
CWD must be repo root.
"""
import datetime as dt
import json
import os
import sys

import pandas as pd
import requests

UA = {"User-Agent": "NCAA180-Sleeper/1.0"}
SLEEPER = "https://api.sleeper.app/v1"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
POS = ["QB", "RB", "WR", "TE", "K", "DEF"]
WINDOW_HOURS = 8
ESPN_ALIAS = {"WSH": "WAS", "LA": "LAR", "JAC": "JAX"}  # ESPN abbr -> Sleeper abbr


def note(kind, text):
    print(f"::{kind}::{text}")


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=30, **kw)
    r.raise_for_status()
    return r.json()


def nfl_games():
    """NFL team -> (state, kickoff UTC) for the current scoreboard week."""
    out = {}
    d = get(ESPN)
    for ev in d.get("events", []):
        state = ev.get("status", {}).get("type", {}).get("state", "")
        kick = ev.get("date", "")
        for comp in ev.get("competitions", []):
            for c in comp.get("competitors", []):
                ab = c.get("team", {}).get("abbreviation", "")
                out[ESPN_ALIAS.get(ab, ab)] = (state, kick)
    return out


def projections(season, week):
    """player_id -> stats dict. Tries the current feed, then the older v1 path."""
    try:
        params = [("season_type", "regular")] + [("position[]", p) for p in POS]
        d = get(f"https://api.sleeper.app/projections/nfl/{season}/{week}", params=params)
        out = {str(x.get("player_id")): (x.get("stats") or {}) for x in d if x.get("player_id")}
        if out:
            return out
    except Exception as e:
        print(f"primary projections feed failed: {e}")
    d = get(f"{SLEEPER}/projections/nfl/regular/{season}/{week}")
    return {str(k): (v or {}) for k, v in d.items()}


def score(stats, scoring):
    return round(sum(float(stats.get(k, 0) or 0) * float(w) for k, w in scoring.items()
                     if isinstance(w, (int, float))), 2)


def main():
    now = dt.datetime.now(dt.timezone.utc)
    state = get(f"{SLEEPER}/state/nfl")
    season, week = str(state.get("season")), int(state.get("week") or 0)
    if state.get("season_type") not in ("regular", "post") or week < 1:
        note("notice", f"Projection snapshot skipped: season_type={state.get('season_type')}")
        return

    games = nfl_games()
    soon = [k for s, k in games.values() if s == "pre" and k and
            0 <= (dt.datetime.fromisoformat(k.replace("Z", "+00:00")) - now).total_seconds() <= WINDOW_HOURS * 3600]
    if not soon and os.environ.get("FORCE") != "1":
        note("notice", f"Projection snapshot skipped: no kickoff in the next {WINDOW_HOURS}h")
        return

    proj = projections(season, week)
    if len(proj) < 100:
        note("error", f"Only {len(proj)} projections returned for {season} wk{week}; nothing written")
        sys.exit(1)

    players = pd.read_csv("data/Players.csv", dtype=str).set_index("player_id")
    lg = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    lg = lg[lg["Year"] == season]
    if lg.empty:
        note("error", f"No leagues for season {season} in LeagueIDs_AllYears.csv")
        sys.exit(1)

    out_dir = os.path.join("data", "projections", season)
    os.makedirs(out_dir, exist_ok=True)
    snap = now.strftime("%Y%m%dT%H%MZ")

    # 1) Lineups: one row per roster (starters change until kickoff; must be per roster).
    lineups, rostered, scoring_all = [], set(), {}
    for r in lg.itertuples():
        scoring_all[r.LeagueID] = get(f"{SLEEPER}/league/{r.LeagueID}").get("scoring_settings") or {}
        for m in get(f"{SLEEPER}/league/{r.LeagueID}/matchups/{week}"):
            starters = [str(p) for p in (m.get("starters") or [])]
            plist = [str(p) for p in (m.get("players") or [])]
            rostered.update(plist)
            lineups.append({"SnapshotUTC": snap, "Season": season, "Week": week,
                            "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                            "RosterID": m.get("roster_id"),
                            "Starters": "|".join(starters), "Players": "|".join(plist)})

    # 2) Projections: ONE row per player (rostered anywhere in NCAA 180), raw projected stats
    #    kept so any league's scoring can be applied later.
    prow = []
    for pid in sorted(rostered):
        team = players["team"].get(pid, "") if pid in players.index else pid  # DEF ids are team codes
        team = team if isinstance(team, str) else ""
        pos = players["position"].get(pid, "") if pid in players.index else "DEF"
        gs, kick = games.get(team, ("", ""))
        st = proj.get(pid, {})
        prow.append({"SnapshotUTC": snap, "Season": season, "Week": week, "PlayerID": pid,
                     "Position": pos if isinstance(pos, str) else "", "NFLTeam": team,
                     "GameState": gs, "Kickoff": kick, "ProjPPR": st.get("pts_ppr", ""),
                     "Stats": json.dumps({k: v for k, v in st.items() if isinstance(v, (int, float)) and v},
                                         separators=(",", ":"), sort_keys=True)})

    pd.DataFrame(lineups).to_csv(os.path.join(out_dir, f"wk{week:02d}_{snap}_lineups.csv"), index=False)
    pd.DataFrame(prow).to_csv(os.path.join(out_dir, f"wk{week:02d}_{snap}_proj.csv"), index=False)
    # League scoring rules: rewritten only when they change (they rarely do).
    sc_path = os.path.join(out_dir, "scoring.json")
    old = json.load(open(sc_path)) if os.path.exists(sc_path) else None
    if old != scoring_all:
        json.dump(scoring_all, open(sc_path, "w"), indent=0, sort_keys=True)
    pre = sum(1 for x in prow if x["GameState"] == "pre")
    note("notice", f"Projection snapshot {season} wk{week}: {len(lineups)} lineups, {len(prow)} players "
                   f"({pre} still pregame)")

if __name__ == "__main__":
    main()
