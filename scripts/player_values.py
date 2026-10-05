"""
player_values.py -- dynasty + redraft player values from FantasyCalc (free public API).

One request returns every valued player with both numbers, keyed to Sleeper player IDs.
Settings match NCAA 180: 1 QB, 12 teams, full PPR. Kickers/DEF are not valued.

Writes:
  data/PlayerValues_Current.csv  overwritten each run
  data/PlayerValues_Season.csv   value history labeled by Date: the scheduled weekly run
                                 (Tuesday, after the week advances) adds a snapshot for its
                                 date; manual runs only fill a week with no snapshot. Trades
                                 are valued against the latest snapshot on/before their date.
                                 Past values cannot be fetched later.
Columns: Date, Week, SleeperID, Name, Position, NFLTeam, DynastyValue, RedraftValue
  data/PickValues_Current.csv    future rookie-pick values: Season, Round, Value, Early, Mid,
                                 Late. Value is FantasyCalc's plain round entry ("2027 1st");
                                 the tiered entries ("2027 1st (Early)") fill Early/Mid/Late.

On a failed request, existing files are left untouched (exit 1 so the run flags it).
CWD must be repo root.
"""
import datetime
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import current_week as cw  # noqa: E402
import requests

URL = "https://api.fantasycalc.com/values/current"
PARAMS = {"isDynasty": "true", "numQbs": 1, "numTeams": 12, "ppr": 1}
CURRENT = "data/PlayerValues_Current.csv"
SEASON = "data/PlayerValues_Season.csv"
PICKS = "data/PickValues_Current.csv"
ROUND_WORD = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5}
MATCHUPS = "data/Matchups_Season.csv"


def current_week():
    """First week without final results = the week in progress / about to start."""
    m = pd.read_csv(MATCHUPS, dtype=str)
    return cw(m["Year"].iloc[0])


def main():
    try:
        r = requests.get(URL, params=PARAMS, timeout=30,
                         headers={"User-Agent": "NCAA180-Sleeper/1.0"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"ERROR fetching FantasyCalc values: {e}")
        sys.exit(1)

    today = datetime.date.today().isoformat()
    week = current_week()
    rows, picks = [], []
    for d in data:
        p = d.get("player") or {}
        sid = p.get("sleeperId")
        name = p.get("name", "") or ""
        if str(p.get("position", "")).upper() == "PICK" or (not sid and re.match(r"^\d{4} ", name)):
            m1 = re.match(r"^(\d{4})\s+(?:Round\s+)?(1st|2nd|3rd|4th|5th)\s*(?:\((Early|Mid|Late)\))?\s*$", name)
            m2 = re.match(r"^(\d{4})\s+Pick\s+(\d+)\.(\d+)", name)
            if m1:
                tier = m1.group(3) or ""
                picks.append({"Season": int(m1.group(1)), "Round": ROUND_WORD[m1.group(2)], "Tier": tier,
                              "Value": d.get("value", 0) or 0, "Name": name, "Generic": 0 if tier else 1})
            elif m2:
                picks.append({"Season": int(m2.group(1)), "Round": int(m2.group(2)), "Tier": "",
                              "Value": d.get("value", 0) or 0, "Name": name, "Generic": 0})
            continue
        if not sid:
            continue
        rows.append({"Date": today, "Week": week, "SleeperID": str(sid),
                     "Name": p.get("name", ""), "Position": p.get("position", ""),
                     "NFLTeam": p.get("maybeTeam") or "",
                     "DynastyValue": d.get("value", 0) or 0,
                     "RedraftValue": d.get("redraftValue", 0) or 0})
    if len(rows) < 100:
        print(f"ERROR: only {len(rows)} valued players returned; not overwriting files")
        sys.exit(1)
    if picks:
        pk = pd.DataFrame(picks)
        # Round value: the plain "2027 1st" entry. Only if a season has no plain entry,
        # fall back to the average of its Early/Mid/Late or slot entries.
        gen = pk[pk["Generic"] == 1].groupby(["Season", "Round"])["Value"].mean()
        other = pk[pk["Generic"] == 0].groupby(["Season", "Round"])["Value"].mean()
        val = gen.combine_first(other) if not gen.empty else other
        out = val.round().astype(int).reset_index()
        # Early/Mid/Late kept as extra columns (blank when FantasyCalc doesn't tier
        # that season) for a later early/late-pick adjustment.
        tiers = pk[pk["Tier"] != ""].pivot_table(index=["Season", "Round"], columns="Tier",
                                                  values="Value", aggfunc="mean")
        for t in ("Early", "Mid", "Late"):
            out[t] = [round(tiers[t].get((a, b))) if t in tiers and pd.notna(tiers[t].get((a, b)))
                      else "" for a, b in zip(out["Season"], out["Round"])]
        out.to_csv(PICKS, index=False)
        print(f"Wrote {PICKS}: {len(out)} season/round values from {len(pk)} pick entries")
    else:
        print(f"WARNING: no draft-pick values in the FantasyCalc response; {PICKS} not updated")
    cur = pd.DataFrame(rows)
    cur.to_csv(CURRENT, index=False)
    print(f"Wrote {CURRENT}: {len(cur)} players (week {week})")

    # History is labeled by DATE (Sleeper's week counter flips mid-week). The scheduled
    # weekly run (Tuesday, right after the week advances) always records a snapshot for its
    # date; a manual run only fills in a week that has no snapshot yet. One row-set per date.
    scheduled = os.environ.get("GITHUB_EVENT_NAME") == "schedule"
    if os.path.exists(SEASON):
        hist = pd.read_csv(SEASON, dtype={"SleeperID": str})
        if (hist["Date"] == today).any():
            print(f"Snapshot for {today} already saved; {SEASON} unchanged")
            return
        if not scheduled and (hist["Week"].astype(int) == week).any():
            print(f"Week {week} already has a snapshot and this is a manual run; {SEASON} unchanged")
            return
        hist = pd.concat([hist, cur], ignore_index=True)
    else:
        hist = cur
    hist.to_csv(SEASON, index=False)
    print(f"Saved week {week} snapshot to {SEASON}")


if __name__ == "__main__":
    main()
