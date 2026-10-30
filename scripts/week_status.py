"""
week_status.py -- which NFL weeks are finished (imported by other scripts, not run).

Why: league_matchups.py sets Outcome as soon as a matchup has any points, so during a
live week (e.g. after Thursday night) many rows already say Win/Loss. "Every row has an
Outcome" therefore does NOT mean the week is over. The authority is Sleeper's NFL state:
during the regular season, weeks before state.week are complete.

completed_weeks(year)  -> sorted list of finished week numbers (1..18) for that season
current_week(year)     -> the week in progress / next to be played

Sleeper state is fetched once per job and cached in data/NFLState.json (not committed).
If Sleeper can't be reached, falls back to the cached file, then to the old rule
(every matchup row has an Outcome) with a warning.
"""
import json
import os

import pandas as pd
import requests
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

STATE_URL = lcfg.sleeper() + "/state/nfl"
CACHE = "data/NFLState.json"
MATCHUPS = "data/Matchups_Season.csv"
MAX_WEEK = 18
_state = None


def _get_state():
    global _state
    if _state is not None:
        return _state
    try:
        r = requests.get(STATE_URL, timeout=20, headers={"User-Agent": "NCAA180-Sleeper/1.0"})
        r.raise_for_status()
        _state = r.json()
        with open(CACHE, "w") as f:
            json.dump(_state, f)
    except Exception as e:
        print(f"WARNING: Sleeper NFL state unavailable ({e}); trying cache")
        try:
            with open(CACHE) as f:
                _state = json.load(f)
        except Exception:
            _state = {}
    return _state


def _fallback(year):
    print("WARNING: using fallback week detection (every matchup row has an Outcome or points)")
    m = pd.read_csv(MATCHUPS, dtype=str)
    m = m[m["Year"] == str(year)]
    # From the CCG week on, teams without a real game have no Outcome, so points count too.
    pts = pd.to_numeric(m["PointsFor"], errors="coerce").fillna(0)
    done = (m["Outcome"].notna() | (pts > 0)).groupby(m["Week"].astype(int)).all()
    return sorted(int(w) for w, ok in done.items() if ok)


def completed_weeks(year):
    st = _get_state()
    if not st or "week" not in st:
        return _fallback(year)
    season = int(st.get("season") or 0)
    stype = st.get("season_type")
    week = int(st.get("week") or 0)
    year = int(year)
    if season > year or (season == year and stype == "post"):
        return list(range(1, MAX_WEEK + 1))
    if season < year or stype in ("pre", "off"):
        return []
    return list(range(1, min(week, MAX_WEEK + 1)))


def current_week(year):
    done = completed_weeks(year)
    return min(max(done, default=0) + 1, MAX_WEEK)
