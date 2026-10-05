"""
projection_snapshot.py -- capture PREGAME expectations before kickoffs (raw data for the
Exceeding Expectations award, pregame projections, and later analysis). Past projections
cannot be fetched after the fact, so this runs on a schedule around kickoff windows.

Each run writes ONE new file (never rewritten, so git growth stays small):
  data/projections/<season>/wk<WW>_<YYYYMMDDTHHMM>Z.csv
One row per rostered player in every NCAA 180 league for the current week:
  SnapshotUTC, Season, Week, LeagueID, LeagueName, RosterID, PlayerID, Position, NFLTeam,
  Starter (1/0), Slot (starter position index, blank for bench), ProjPts (projected
  fantasy points under THAT league's scoring settings), ProjPPR (Sleeper's own pts_ppr),
  GameState (pre/in/post from ESPN), Kickoff (UTC ISO)
How to use later: a starter's pregame projection = his row from the latest snapshot taken
while his GameState was "pre". Lineups and projections both change until kickoff.

Skips (writes nothing) when no NFL game kicks off within the next WINDOW_HOURS, unless
FORCE=1 (manual runs). Sleeper projections come from Sleeper's public (unofficial, read-
only) projections feed; if it fails the run exits 1 so the workflow flags it.
CWD must be repo root.
"""
import datetime as dt
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

    snap = now.strftime("%Y%m%dT%H%MZ")
    rows = []
    for r in lg.itertuples():
        scoring = get(f"{SLEEPER}/league/{r.LeagueID}").get("scoring_settings") or {}
        for m in get(f"{SLEEPER}/league/{r.LeagueID}/matchups/{week}"):
            starters = [str(p) for p in (m.get("starters") or [])]
            for pid in [str(p) for p in (m.get("players") or [])]:
                st = proj.get(pid, {})
                team = players["team"].get(pid, "") if pid in players.index else pid  # DEF ids are team codes
                pos = players["position"].get(pid, "") if pid in players.index else "DEF"
                gs, kick = games.get(team if isinstance(team, str) else "", ("", ""))
                rows.append({"SnapshotUTC": snap, "Season": season, "Week": week,
                             "LeagueID": r.LeagueID, "LeagueName": r.LeagueName,
                             "RosterID": m.get("roster_id"), "PlayerID": pid,
                             "Position": pos, "NFLTeam": team,
                             "Starter": int(pid in starters),
                             "Slot": starters.index(pid) if pid in starters else "",
                             "ProjPts": score(st, scoring), "ProjPPR": st.get("pts_ppr", ""),
                             "GameState": gs, "Kickoff": kick})
    out_dir = os.path.join("data", "projections", season)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"wk{week:02d}_{snap}.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    pre = sum(1 for x in rows if x["GameState"] == "pre" and x["Starter"])
    note("notice", f"Projection snapshot {season} wk{week}: {len(rows)} rostered players, "
                   f"{pre} starters still pregame -> {path}")


if __name__ == "__main__":
    main()
