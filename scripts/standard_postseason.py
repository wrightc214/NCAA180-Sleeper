"""Restate Postseason_Historic scores on standard scoring (Chris, 2026-10-08).
ScoreA/ScoreB = standard points; OfficialScoreA/OfficialScoreB = Sleeper's official points,
filled only where they differ. Winners are never changed (results stand as played); a
winner that would differ is reported. Needs data/ScoresStandard_Historic.csv (standard_scores.py).
Run after standard_scores.py; rerun is safe (reads official from the Official columns first)."""
import sys

import pandas as pd

sys.path.insert(0, "scripts")
import team_names as tn

P = "data/Postseason_Historic.csv"
s = pd.read_csv("data/ScoresStandard_Historic.csv", dtype=str)
S = {(r.Year, r.LeagueName, r.RosterID, r.Week): (float(r.PointsOfficial), float(r.PointsStandard)) for r in s.itertuples()}
p = pd.read_csv(P, dtype=str, keep_default_na=False)
for c in ("OfficialScoreA", "OfficialScoreB"):
    if c not in p.columns:
        p[c] = ""
fmt = lambda v: repr(round(v, 2)).rstrip("0").rstrip(".")
changed, odd, flips = 0, [], []
for i, r in p.iterrows():
    if not r.Week or not r.ScoreA:
        continue
    for side in ("A", "B"):
        teams = r["Team" + side].split(" | ") if r["Team" + side] else []
        cur = (r["OfficialScore" + side] or r["Score" + side]).split(" | ")
        if not teams or len(cur) != len(teams):
            continue
        std, off, diff = [], [], False
        for t, v in zip(teams, cur):
            sl = tn.slot(int(r.Season), t)
            o, st = S.get((r.Season, sl[0], sl[1], r.Week), (None, None)) if sl else (None, None)
            if o is None or not v:
                std.append(v); off.append(v); continue
            v = float(v)
            if abs(v - o) > 0.015 and abs(v - st) > 0.015:
                odd.append((r.Season, r.Event, r.Bowl, t, v, o, st))
            std.append(fmt(st)); off.append(fmt(o)); diff |= abs(o - st) > 0.005
        p.at[i, "Score" + side] = " | ".join(std)
        p.at[i, "OfficialScore" + side] = " | ".join(off) if diff else ""
        changed += diff
    # winner check (two-team rows)
    if r.TeamB and p.at[i, "ScoreA"] and p.at[i, "ScoreB"]:
        a, b = float(p.at[i, "ScoreA"]), float(p.at[i, "ScoreB"])
        if (a > b) != (r.Winner == r.TeamA):
            flips.append((r.Season, r.Event, r.Bowl, r.TeamA, a, r.TeamB, b, r.Winner))
p.to_csv(P, index=False, lineterminator="\r\n")
print(f"{changed} sides restated; {len(odd)} stored scores matched neither basis (kept standard): {odd[:5]}")
print("winner would differ (results stand):", flips)
