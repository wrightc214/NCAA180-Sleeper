"""
guillotine.py -- The Guillotine: every team, weeks first_week..last_week (12-16), about half cut each week.

Rules (config/league.json -> postseason.guillotine; Chris 2026-11-04 / 11-14, claude/todo-guillotine.md):
  - Each week counts only that week's score (standard scoring from 2026, like every postseason game).
  - Weeks first_week..last_week-1: half of the field entering the week, rounded down, advances.
    Everyone tied with the last advancing score advances too (PGA style), so a field can be bigger
    than half; the next week's cut is half of that bigger field.
  - last_week: the top score wins. An exact tie for first is decided by tiebreak_week's score among
    the tied teams; still tied -> co-champions. Until tiebreak_week is final the tied teams show "Tied".
  - Orphan teams play like everyone else.
  - Stat corrections: a week is frozen the first run it is final. A later run recomputes it with
    the current scores and only ADDS teams (AddedByCorrection = 1): a team advances if it now scores
    at or above the frozen CutLine; nobody who advanced is removed. The added teams join the next
    week's field (and play any later frozen week against that week's frozen line).
  - The champion (last_week) is recomputed each run, like the other postseason results; how late
    stat corrections should treat it is on hold (claude/todo-postseason-stat-corrections.md).

Writes
  data/Guillotine_Season.csv              one row per team per finished week (see COLUMNS)
  data/scoreboard/<season>/guillotine.json  the page's data (reports/special.html)

Usage: python scripts/guillotine.py [--year Y] [--out-dir DIR]
  --year Y      replay any season with scores (2019+); default = the current season.
                Seasons before from_season are only built with --out-dir (tests / replays).
  --out-dir     write both files under DIR instead of data/ (replays and tests).
CWD = repo root.
"""
import argparse
import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as psc  # noqa: E402
import team_names as tn  # noqa: E402

SEASON_FILE = "data/Guillotine_Season.csv"
COLUMNS = ["Year", "Week", "LeagueID", "LeagueName", "RosterID", "Team", "OwnerName", "Score",
           "Rank", "FieldSize", "Advance", "CutLine", "Status", "AddedByCorrection", "TiebreakScore", "FrozenAt"]
EPS = 1e-9


def settings():
    c, ps = psc.config()
    g = ps.get("guillotine")
    if not g:
        raise SystemExit("config postseason.guillotine missing")
    return g


def cut(scores, target):
    """Teams that advance: the top `target` scores plus everyone tied with the last of them.
    scores: {key: points}. Returns (advancing set, cut-line score)."""
    if target <= 0 or not scores:
        return set(), None
    order = sorted(scores.values(), reverse=True)
    line = order[min(target, len(order)) - 1]
    return {k for k, v in scores.items() if v >= line - EPS}, line


def champion(scores, tiebreak=None):
    """Last week: (champions, status per team). tiebreak = {key: week-18 score} or None if not final."""
    top = max(scores.values())
    tied = [k for k, v in scores.items() if v >= top - EPS]
    status = {k: "Eliminated" for k in scores}
    if len(tied) == 1:
        status[tied[0]] = "Champion"
        return tied, status
    if tiebreak is None:
        for k in tied:
            status[k] = "Tied"
        return [], status
    best = max(tiebreak.get(k, 0.0) for k in tied)
    winners = [k for k in tied if tiebreak.get(k, 0.0) >= best - EPS]
    for k in winners:
        status[k] = "Champion"  # still tied after the tiebreak week: co-champions
    return winners, status


def run(year, frozen, points, done, ids, g, now=None):
    """Pure core (tests call this). Returns (rows, summary).
    frozen  : previous rows for this year (DataFrame, may be empty)
    points  : {week: {key: score}}, key = (LeagueID, RosterID)
    done    : set of completed weeks
    ids     : {key: {"LeagueName", "Team", "OwnerName"}} for every entrant
    """
    first, last = int(g["first_week"]), int(g["last_week"])
    tb = int(g.get("tiebreak_week", last + 1))
    now = now or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = {}
    if frozen is not None and len(frozen):
        for r in frozen.itertuples():
            prev.setdefault(int(r.Week), {})[(str(r.LeagueID), str(r.RosterID))] = r
    field = set(ids)
    rows, weeks, out_week, champs = [], [], {}, []
    for w in range(first, last + 1):
        if w not in done or not field:
            break
        sc = {k: round(float(points.get(w, {}).get(k, 0.0)), 2) for k in field}
        missing = [k for k in field if k not in points.get(w, {})]
        if missing:
            print(f"WARNING: week {w}: {len(missing)} team(s) have no score; counted as 0")
        rank = {k: i + 1 for i, k in enumerate(sorted(sc, key=lambda k: (-sc[k], ids[k]["Team"])))}
        old = prev.get(w, {})
        frozen_at = next((str(r.FrozenAt) for r in old.values() if str(r.FrozenAt)), now)
        if w < last:
            target = len(field) // 2
            adv, line = cut(sc, target)
            before = {k for k, r in old.items() if str(r.Status) == "Advanced"}
            added_before = {k for k, r in old.items() if str(r.AddedByCorrection) == "1"}
            if old:
                # A frozen week keeps its cut line AND its size: a team advances only by scoring at or
                # above that line. A field enlarged by an earlier week's correction must not re-cut a
                # week already played ("half" of the bigger field applies from the next unplayed week).
                r0 = next(iter(old.values()))
                line, target = float(r0.CutLine), int(r0.Advance)
                adv = {k for k, v in sc.items() if v >= line - EPS}
                new = adv - before
                if new:
                    print(f"Week {w}: stat corrections add {len(new)} team(s) to the next round")
                adv = adv | before
                added = (new | added_before) & adv
            else:
                added = set()
            status = {k: "Advanced" if k in adv else "Eliminated" for k in field}
            tbs = {}
            weeks.append({"week": w, "field": len(field), "advance": target, "advanced": len(adv),
                          "cutline": line, "added": len(added), "final": True})
        else:
            target = 1
            tie_scores = None
            top = max(sc.values())
            tied = [k for k, v in sc.items() if v >= top - EPS]
            if len(tied) > 1 and tb in done:
                tie_scores = {k: round(float(points.get(tb, {}).get(k, 0.0)), 2) for k in tied}
            champs, status = champion(sc, tie_scores)
            line, added = top, set()
            tbs = tie_scores or {}
            adv = set(champs)
            weeks.append({"week": w, "field": len(field), "advance": 1, "advanced": len(champs),
                          "cutline": top, "added": 0, "final": bool(champs),
                          "tied": len(tied) if len(tied) > 1 else 0, "tiebreak_week": tb if len(tied) > 1 else None})
        for k in sorted(field, key=lambda k: rank[k]):
            i = ids[k]
            rows.append({"Year": year, "Week": w, "LeagueID": k[0], "LeagueName": i["LeagueName"], "RosterID": k[1],
                         "Team": i["Team"], "OwnerName": i["OwnerName"], "Score": f"{sc[k]:.2f}", "Rank": rank[k],
                         "FieldSize": len(field), "Advance": target, "CutLine": f"{line:.2f}", "Status": status[k],
                         "AddedByCorrection": "1" if k in added else "", "TiebreakScore": f"{tbs[k]:.2f}" if k in tbs else "",
                         "FrozenAt": frozen_at})
            if status[k] == "Eliminated":
                out_week[k] = w
        field = adv if w < last else field
    finished = bool(champs)
    played = [x["week"] for x in weeks]
    next_week = None if finished else (max(played) + 1 if played else first)
    if next_week is not None and next_week > last:
        next_week = last  # last week final but tied, waiting on the tiebreak week
    if not weeks:
        alive = set(ids)
    elif finished:
        alive = set(champs)
    elif weeks[-1]["week"] == last:
        alive = {(str(r["LeagueID"]), str(r["RosterID"])) for r in rows if r["Week"] == last and r["Status"] == "Tied"}
    else:
        alive = set(field)
    return rows, {"weeks": weeks, "out_week": out_week, "champions": champs, "alive": alive,
                  "next_week": next_week, "finished": finished}


def entrants(year):
    """Every team that has a score this season: {(LeagueID, RosterID): {LeagueName, Team, OwnerName}}."""
    m = psc._matchups(year)
    m = m.sort_values("Week")
    out = {}
    for r in m.itertuples():
        k = (str(r.LeagueID), str(r.RosterID))
        out[k] = {"LeagueName": r.LeagueName, "OwnerName": r.OwnerName if isinstance(r.OwnerName, str) else "",
                  "Team": tn.season_name(int(year), r.LeagueName, r.RosterID) or f"{r.LeagueName} #{r.RosterID}"}
    return out


def page_json(year, g, rows, summary, ids):
    by = {}
    for r in rows:
        k = (str(r["LeagueID"]), str(r["RosterID"]))
        by.setdefault(k, {})[str(r["Week"])] = float(r["Score"])
    champs = set(summary["champions"])
    tied = {(str(r["LeagueID"]), str(r["RosterID"])) for r in rows if r["Status"] == "Tied"}
    teams = []
    for k, i in sorted(ids.items(), key=lambda kv: kv[1]["Team"]):
        st = "champion" if k in champs else "tied" if k in tied else "out" if k in summary["out_week"] else "alive"
        teams.append({"l": k[0], "r": k[1], "team": i["Team"], "owner": i["OwnerName"], "league": i["LeagueName"],
                      "status": st, "out": summary["out_week"].get(k), "scores": by.get(k, {}),
                      "added": sorted(int(r["Week"]) for r in rows if (str(r["LeagueID"]), str(r["RosterID"])) == k
                                      and r["AddedByCorrection"] == "1")})
    return {"season": int(year), "name": g.get("name", "The Guillotine"), "first_week": int(g["first_week"]),
            "last_week": int(g["last_week"]), "tiebreak_week": int(g.get("tiebreak_week", int(g["last_week"]) + 1)),
            "logos": g.get("logos", {}), "status": "final" if summary["finished"] else "live" if summary["weeks"] else "upcoming",
            "next_week": summary["next_week"], "entrants": len(ids), "weeks": summary["weeks"],
            "champions": [{"l": k[0], "r": k[1], "team": ids[k]["Team"]} for k in summary["champions"]],
            "teams": teams, "built_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    g = settings()
    year = a.year or psc.current_season()
    if year < int(g.get("from_season", 0)) and not a.out_dir:
        print(f"Guillotine starts in {g.get('from_season')}; {year} not built (use --out-dir for a replay).")
        return
    first, last, tb = int(g["first_week"]), int(g["last_week"]), int(g.get("tiebreak_week", int(g["last_week"]) + 1))
    season_file = os.path.join(a.out_dir, "Guillotine_Season.csv") if a.out_dir else SEASON_FILE
    json_file = (os.path.join(a.out_dir, "guillotine.json") if a.out_dir
                 else f"data/scoreboard/{year}/guillotine.json")
    ids = entrants(year)
    if not ids:
        print(f"Guillotine {year}: no teams yet.")
        return
    done = psc.completed_weeks(year)
    points = {w: {k: v[0] for k, v in psc.week_points(year, w).items()} for w in range(first, tb + 1) if w in done}
    old = pd.DataFrame(columns=COLUMNS)
    if os.path.exists(season_file) and os.path.getsize(season_file) > 10:
        old = pd.read_csv(season_file, dtype=str, keep_default_na=False)
    other = old[old["Year"].astype(str) != str(year)] if len(old) else old
    mine = old[old["Year"].astype(str) == str(year)] if len(old) else old
    rows, summary = run(year, mine, points, done, ids, g)
    out = pd.concat([other, pd.DataFrame(rows, columns=COLUMNS)], ignore_index=True)
    os.makedirs(os.path.dirname(season_file) or ".", exist_ok=True)
    out[COLUMNS].to_csv(season_file, index=False)
    os.makedirs(os.path.dirname(json_file) or ".", exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(page_json(year, g, rows, summary, ids), f, ensure_ascii=False, separators=(",", ":"))
    ws = summary["weeks"]
    trail = " → ".join([str(len(ids))] + [str(x["advanced"]) for x in ws])
    champ = ", ".join(ids[k]["Team"] for k in summary["champions"]) or "—"
    print(f"Guillotine {year}: {trail}; next week {summary['next_week']}; champion {champ}")


if __name__ == "__main__":
    main()
