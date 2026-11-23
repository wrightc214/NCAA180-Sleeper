"""Points-for cap for the Clinched / Out proofs (task 5.15, Chris 2026-11-23).

Points for is the first tiebreak after record, so a proof that treats every tie on wins as unknown can
never clinch on a points gap. This module bounds what a chasing team can still score:

    cap = max(points_per_minute x player-minutes left, burst_per_player x starters still to play)

The other team's floor is its points so far minus max_drop while it still has a starter to play
(Chris, 2026-11-23: at most one big negative per team; 11.01 = a defense's floor under standard scoring,
-4 for 35+ points allowed and -7 for 550+ yards, plus a cent; the worst other starter on record is a QB
at -7.66). On a tie in wins, the points-for tiebreak is settled when one team's floor beats the other's
ceiling (points so far + cap).
Points against (the next tiebreak) is never capped.

Settings: config/league.json -> postseason.clinch (points_per_minute, burst_per_player). Both 0 or
missing = the old behaviour: every points-for tie stays unknown. The browser twin is
reports/assets/ccg-race-model.js (pointsCap / weekCap); both must give identical results.
"""
import os

import pandas as pd

import league_config as lcfg

BENCH = {"BN", "IR", "TAXI", "RES"}
MINUTES_PER_GAME = 60


def settings():
    """(rate, burst) from config; (0, 0) when the block or a key is missing."""
    c = (lcfg.cfg().get("postseason") or {}).get("clinch") or {}
    rate = float(c.get("points_per_minute") or 0)
    burst = float(c.get("burst_per_player") or 0)
    return max(rate, 0.0), max(burst, 0.0)


def max_drop():
    """Most one team can still lose (points) while it has starters to play; 0 when missing."""
    c = (lcfg.cfg().get("postseason") or {}).get("clinch") or {}
    return max(float(c.get("max_drop") or 0), 0.0)


def enabled(rate, burst):
    return rate > 0 or burst > 0


def points_cap(minutes_left, players_left, rate, burst):
    """Most a team can still score with `players_left` starters and `minutes_left` player-minutes to go."""
    if players_left <= 0 and minutes_left <= 0:
        return 0.0
    return max(rate * float(minutes_left), burst * float(players_left))


def week_cap(slots, rate, burst):
    """Cap for one full week still to play: every starter slot, 60 minutes each."""
    return points_cap(MINUTES_PER_GAME * slots, slots, rate, burst)


def starter_slots(year):
    """{league_id: number of starter slots} from data/LeagueIDs_AllYears.csv RosterPositions."""
    path = os.path.join(lcfg.ROOT, "data", "LeagueIDs_AllYears.csv")
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)
    df = df[df["Year"] == str(year)]
    out = {}
    for r in df.itertuples():
        pos = [p.strip().upper() for p in str(r.RosterPositions).split(",") if p.strip()]
        out[str(r.LeagueID)] = sum(p not in BENCH for p in pos)
    return out


def note():
    """One sentence for a page's method note ('' when the cap is off)."""
    rate, burst = settings()
    if not enabled(rate, burst):
        return ""
    fmt = lambda x: f"{x:g}"  # noqa: E731
    return (f"Points-for ties count as settled when the gap exceeds the most the chasing team could still score "
            f"({fmt(rate)} points per remaining player-minute, but never less than {fmt(burst)} per player still to play)"
            + (f", while the leader could still lose up to {fmt(max_drop())} if it has a starter still to play" if max_drop() else "")
            + ".")
