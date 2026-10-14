"""
max_points.py -- each team's best possible lineup score, every week.

Writes data/MaxPoints_Season.csv:
  Year, LeagueID, LeagueName, Week, RosterID, PointsFor, MaxPoints, Efficiency

Rules (confirmed by the commissioner):
  - Every player on the roster that week is eligible, including IR. A scoring
    IR player counts toward MaxPoints.
  - Lineup slots come from each league's roster_positions (saved by
    league_ids.py into LeagueIDs_AllYears.csv as RosterPositions). BN is ignored.
  - Filled greedily from most to least restrictive slot (QB/RB/WR/TE/K/DEF,
    then FLEX, then SUPER_FLEX). Optimal for nested slot types like these.
  - Positions from data/Players.csv; label text in Scores_Season.csv as fallback.
    FB counts as RB.
  - Only completed weeks (Matchups_Season Outcome populated) are written.

CWD must be repo root.
"""
import sys
import os
import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import completed_weeks as finished_weeks  # noqa: E402

SCORES_FILE = "data/Scores_Season.csv"
MATCHUPS_FILE = "data/Matchups_Season.csv"
LEAGUES_FILE = "data/LeagueIDs_AllYears.csv"
PLAYERS_FILE = "data/Players.csv"
OUTPUT_FILE = "data/MaxPoints_Season.csv"

YEAR = str(datetime.datetime.now().year)
DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX", "K", "DEF"]

ELIGIBLE = {
    "QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"}, "K": {"K"}, "DEF": {"DEF"},
    "FLEX": {"RB", "WR", "TE"},
    "WRRB_FLEX": {"RB", "WR"},
    "REC_FLEX": {"WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
}
POS_ALIAS = {"FB": "RB"}


def best_lineup(players, slots):
    """players: list of (points, pos). Returns max total for the slot list."""
    pool = sorted(players, key=lambda x: -x[0])
    used = [False] * len(pool)
    total = 0.0
    for slot in sorted(slots, key=lambda s: len(ELIGIBLE.get(s, ()))):
        ok = ELIGIBLE.get(slot)
        if ok is None:
            print(f"WARNING: unknown slot type {slot} ignored")
            continue
        for i, (pts, pos) in enumerate(pool):
            if not used[i] and pos in ok:
                used[i] = True
                total += pts
                break
    return round(total, 2)


def lineup_pick(values, positions, slots, worst=False):
    """Indices of the players filling `slots`: the highest total (worst=False) or the lowest
    (worst=True, the worst legal lineup). Same greedy order as best_lineup (most restrictive slot
    first), optimal for nested slot types like these. A slot no eligible player can fill stays empty."""
    order = sorted(range(len(values)), key=lambda i: values[i] if worst else -values[i])
    used, picked = set(), []
    for slot in sorted(slots, key=lambda s: len(ELIGIBLE.get(s, ()))):
        ok = ELIGIBLE.get(slot)
        if ok is None:
            continue
        for i in order:
            if i not in used and positions[i] in ok:
                used.add(i)
                picked.append(i)
                break
    return picked


def load_slots():
    slots = {}
    try:
        lg = pd.read_csv(LEAGUES_FILE, dtype=str)
        lg = lg[lg["Year"] == YEAR]
        if "RosterPositions" in lg.columns:
            for r in lg.itertuples():
                if isinstance(r.RosterPositions, str) and r.RosterPositions:
                    slots[r.LeagueID] = [s for s in r.RosterPositions.split(",") if s not in ("BN", "IR", "TAXI")]
    except FileNotFoundError:
        pass
    if not slots:
        print("WARNING: no RosterPositions found; using default slot list for every league")
    return slots


def main():
    sc = pd.read_csv(SCORES_FILE, dtype=str)
    sc = sc[sc["LeagueYear"] == YEAR].copy()
    sc["pts"] = sc["points"].astype(float)

    pl = pd.read_csv(PLAYERS_FILE, dtype=str)[["player_id", "position"]].drop_duplicates("player_id")
    sc = sc.merge(pl, on="player_id", how="left")
    sc["pos"] = sc["position"].fillna(sc["label"].str.extract(r", ([A-Z]+) \(", expand=False))
    sc["pos"] = sc["pos"].replace(POS_ALIAS)
    unknown = sc[sc["pos"].isna() & (sc["pts"] != 0)]
    if not unknown.empty:
        print(f"WARNING: {len(unknown)} scoring player-weeks with no position (excluded): "
              f"{sorted(unknown['player_id'].unique())[:20]}")

    m = pd.read_csv(MATCHUPS_FILE, dtype=str)
    m = m[m["Year"] == YEAR]
    done_weeks = {str(w) for w in finished_weeks(YEAR)} & set(m["Week"])

    slots = load_slots()
    rows = []
    for (lid, wk, rid), g in sc[sc["weekNum"].isin(done_weeks)].groupby(["league_id", "weekNum", "roster_id"]):
        players = list(zip(g["pts"], g["pos"]))
        rows.append({"LeagueID": lid, "Week": wk, "RosterID": rid,
                     "MaxPoints": best_lineup(players, slots.get(lid, DEFAULT_SLOTS))})
    mx = pd.DataFrame(rows)

    out = m[m["Week"].isin(done_weeks)][["Year", "LeagueID", "LeagueName", "Week", "RosterID", "PointsFor"]].merge(
        mx, on=["LeagueID", "Week", "RosterID"], how="left")
    out["PointsFor"] = out["PointsFor"].astype(float).round(2)
    missing = out["MaxPoints"].isna().sum()
    if missing:
        print(f"WARNING: {missing} team-weeks have no player scores; MaxPoints blank")
    bad = out[out["MaxPoints"] + 0.01 < out["PointsFor"]]
    if not bad.empty:
        print(f"WARNING: {len(bad)} team-weeks where MaxPoints < PointsFor (data gap):")
        print(bad.head(10).to_string(index=False))
    out["Efficiency"] = (out["PointsFor"] / out["MaxPoints"]).round(4)
    out["Week"] = out["Week"].astype(int)
    out = out.sort_values(["Week", "LeagueName", "RosterID"], key=lambda s: s.astype(int) if s.name == "RosterID" else s)
    out.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE}: {len(out)} team-weeks, weeks {sorted(int(w) for w in done_weeks)}")


if __name__ == "__main__":
    main()
