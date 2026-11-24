"""Current-season CCG division race snapshot. Live odds are computed by the browser.

Only runs during schedule.ccg_week - 1, and never overwrites the snapshot once
that regular-season week is final. Run from the repository root.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import _postseason_common as ps
from postseason_odds import _Conf, MAX_ENUM
import league_config as lcfg


def alive_members(members, divs, games, wins):
    """Exact existential contender test; ties on wins remain eligible.

    members: global roster keys; divs: lists of keys; games: remaining key pairs;
    wins: baseline wins by key. Use _Conf for the shared exhaustive enumeration.
    """
    at = {k: i for i, k in enumerate(members)}
    base = np.array([wins[k] for k in members], dtype=int)
    c = _Conf(list(range(len(members))),
              [[at[k] for k in d] for d in divs],
              [(at[a], at[b]) for a, b in games], base)
    out = []
    for d in divs:
        qualified = []
        for k in d:
            i = at[k]
            rivals = [at[x] for x in d if x != k]
            if not rivals:
                qualified.append(k)
            elif c.exact:
                if np.any(c.W[:, i] >= c.W[:, rivals].max(axis=1)):
                    qualified.append(k)
            elif base[i] + c.left[i] >= max(base[j] for j in rivals):
                qualified.append(k)
        out.append(qualified)
    return out


def build(year=None, write=True):
    os.chdir(lcfg.ROOT)
    cfg, _ = ps.config()
    year = int(year or ps.current_season())
    week = int(cfg["schedule"]["ccg_week"]) - 1
    last = ps.last_regular_week()
    if week != last:
        # Future seasons may support a longer window; do not expand it in 2026.
        raise ValueError("CCG race currently supports only the last regular-season week")
    if year != ps.current_season():
        return None
    completed = ps.completed_weeks(year)
    current = next((w for w in range(1, last + 1) if w not in completed), None)
    if current != week:
        return None

    st = ps.standings(year)
    if st.empty:
        raise ValueError("No completed regular-season standings")
    matchups = ps._matchups(year)
    remaining = matchups[matchups["Week"].between(week, last)]
    if remaining.empty:
        raise ValueError("Remaining-game schedule unavailable")

    divisions = pd.read_csv("data/Divisions.csv", dtype=str, encoding="utf-8-sig").fillna("")
    short = {full: short for short, full in ps.league_short().items()}
    confs = []
    for league, frame in st.groupby("LeagueID", sort=False):
        league = str(league)
        full = str(frame.iloc[0]["LeagueName"]).strip()
        spec = divisions[divisions["LeagueName"].str.strip() == full].sort_values(
            "Div Index", key=lambda v: pd.to_numeric(v, errors="coerce"))
        if len(spec) != 2:
            raise ValueError("Expected two configured divisions for " + full)
        entries = {}
        members = []
        divkeys = []
        for row in frame.to_dict("records"):
            k = str(row["RosterID"]).removesuffix(".0")
            members.append(k)
            entries[k] = {
                "roster_id": k, "team": str(row["Team"]),
                "owner": str(row["OwnerName"]), "wins": int(row["Wins"]),
                "losses": int(row["Losses"]), "ties": int(row["Ties"]),
                "points_for": float(row["PointsFor"]),
                "points_against": float(row["PointsAgainst"]),
                "remaining_games": []
            }
        for div in spec.itertuples(index=False):
            div_name = str(div[1]).strip().upper()
            subset = [str(r["RosterID"]).removesuffix(".0") for r in frame.to_dict("records")
                      if str(r["Division"]).upper() == div_name]
            if not subset:
                raise ValueError("No members for division " + full + "/" + div_name)
            divkeys.append((div_name, subset))

        games, seen = [], set()
        m = remaining[remaining["LeagueID"].astype(str) == league]
        for row in m.itertuples():
            a, b = str(row.RosterID).removesuffix(".0"), str(row.OpponentRosterID).removesuffix(".0")
            ident = (int(row.Week), tuple(sorted((a, b))))
            if ident in seen or a not in entries or b not in entries or a == b:
                continue
            seen.add(ident)
            games.append((a, b))
            entries[a]["remaining_games"].append({"week": int(row.Week), "opponent_roster_id": b})
            entries[b]["remaining_games"].append({"week": int(row.Week), "opponent_roster_id": a})
        if not games:
            raise ValueError("No remaining games for " + full)
        alive = alive_members(members, [v for _, v in divkeys], games,
                              {k: entries[k]["wins"] for k in members})
        if full not in short:
            raise ValueError("Missing friendly short conference name: " + full)
        confs.append({
            "league_id": league, "name": short[full],
            "divisions": [
                {"name": label, "clinched_before_week": len(ids) == 1,
                 "contenders": [entries[k] for k in ids]}
                for (label, _), ids in zip(divkeys, alive)
            ]
        })
    out = {
        "season": year, "week": week, "last_regular_week": last,
        "tiebreak_order": cfg["tiebreakers"]["order"],
        "coin_toss_results": cfg["tiebreakers"].get("coin_toss_results", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "conferences": confs
    }
    if write:
        os.makedirs("reports/postseason", exist_ok=True)
        with open("reports/postseason/ccg-race-{}.json".format(year), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    args = parser.parse_args()
    result = build(args.year)
    if result is None:
        print("CCG race inactive: not configured active week or already final")
    else:
        print("CCG race: {} conferences; {} live, {} clinched".format(
            len(result["conferences"]),
            sum(not d["clinched_before_week"] for c in result["conferences"] for d in c["divisions"]),
            sum(d["clinched_before_week"] for c in result["conferences"] for d in c["divisions"])))
