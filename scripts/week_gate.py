"""
week_gate.py -- run the weekly update once per NFL week, right after Sleeper advances.

Sleeper flips its NFL week on Tuesday, but the time varies by hours, so the workflow
wakes every 2 hours Tue-Wed and asks this script whether to do the full run.

  python scripts/week_gate.py check   -> writes run=true/false to $GITHUB_OUTPUT
  python scripts/week_gate.py mark    -> records the current Sleeper season/week as done

data/LastProcessedWeek.csv (Season, Week, ProcessedAt) holds the last Sleeper week a
full, successful scheduled run covered. Scheduled runs go ahead only when Sleeper's
(season, week) differs from it and the NFL season is active. Manual runs always go.
If Sleeper can't be reached, a scheduled run is skipped (the next wake-up retries).

Readiness (added 2026-10-06): Sleeper flips the shared NFL week at once, but finishes each
league's end-of-week processing over roughly an hour (Chris's leagues: 11:12-12:05 ET). So a
scheduled run also waits until EVERY league for the season reports settings.last_scored_leg >=
the week just finished. Leagues without that field count as ready (warning). Safety valve: after
READY_DEADLINE (Wed 12:00 UTC) it runs anyway with a warning, so a stuck league can't block the
week. Manual runs skip the check.
"""
import datetime
import os
import sys

import pandas as pd
import requests

STATE_URL = "https://api.sleeper.app/v1/state/nfl"
FILE = "data/LastProcessedWeek.csv"
LEAGUES = "data/LeagueIDs_AllYears.csv"
LEAGUE_URL = "https://api.sleeper.app/v1/league/{}"
READY_DEADLINE = (2, 12)  # (weekday Mon=0, UTC hour): from Wed 12:00 UTC run even if not all ready


def not_ready(season, done_week):
    """League names whose last scored week is still behind done_week; (list, warnings)."""
    lg = pd.read_csv(LEAGUES, dtype=str)
    lg = lg[lg["Year"] == season]
    behind, warn = [], []
    for r in lg.itertuples():
        s = requests.get(LEAGUE_URL.format(r.LeagueID), timeout=20,
                         headers={"User-Agent": "NCAA180-Sleeper/1.0"}).json() or {}
        leg = (s.get("settings") or {}).get("last_scored_leg")
        if leg is None:
            warn.append(r.LeagueName)
        elif int(leg) < done_week:
            behind.append(f"{r.LeagueName} (scored through wk {leg})")
    return behind, warn


def past_deadline():
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now.weekday(), now.hour) >= READY_DEADLINE and now.weekday() <= 3


def state():
    r = requests.get(STATE_URL, timeout=20, headers={"User-Agent": "NCAA180-Sleeper/1.0"})
    r.raise_for_status()
    s = r.json()
    return str(s.get("season")), int(s.get("week") or 0), s.get("season_type")


def last():
    try:
        d = pd.read_csv(FILE, dtype=str)
        return d["Season"].iloc[-1], int(d["Week"].iloc[-1])
    except Exception:
        return None, None


def out(run, why):
    print(f"run={run}: {why}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"run={'true' if run else 'false'}\n")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "check":
        if os.environ.get("GITHUB_EVENT_NAME", "schedule") != "schedule":
            return out(True, "manual run")
        try:
            season, week, stype = state()
        except Exception as e:
            return out(False, f"Sleeper state unavailable ({e}); next wake-up retries")
        if stype not in ("regular", "post"):
            return out(False, f"season_type={stype}; weekly run only in season")
        ls, lw = last()
        if (ls, lw) == (season, week):
            return out(False, f"Sleeper week {season}/{week} already processed")
        if week > 1:
            try:
                behind, warn = not_ready(season, week - 1)
            except Exception as e:
                return out(False, f"League readiness check failed ({e}); next wake-up retries")
            if warn:
                print(f"::warning::No last_scored_leg for: {', '.join(warn)} (treated as ready)")
            if behind:
                if past_deadline():
                    print(f"::warning::Running anyway (past deadline); not finished: {'; '.join(behind)}")
                else:
                    return out(False, f"{len(behind)} league(s) still finishing week {week - 1}: "
                                      f"{'; '.join(behind)}; next wake-up retries")
        return out(True, f"Sleeper advanced to {season}/{week} (last processed {ls}/{lw}); all leagues ready")
    if mode == "mark":
        season, week, _ = state()
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        pd.DataFrame([{"Season": season, "Week": week, "ProcessedAt": now}]).to_csv(FILE, index=False)
        print(f"Marked {season}/{week} processed at {now}")


if __name__ == "__main__":
    main()
