"""Dwight Fight: fixed-seed, frozen-round knockout for league assistants.

The JSON bracket is the authority after lock. Entrants are Sleeper user IDs, not
mutable display names. Scheduled weekly execution is safe before the regular season.
"""
import argparse
import csv
import datetime as dt
import json
import math
import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _postseason_common as ps
import week_status

HISTORY = Path("data/Dwight_Historic.csv")
COLUMNS = ["Season", "Round", "RoundName", "Week", "TeamA", "SeedA",
           "TeamB", "SeedB", "ScoreA", "ScoreB", "Winner", "Notes", "Status"]
NAMES = {1: "First Round", 2: "Quarterfinal", 3: "Semifinal", 4: "Final"}


def names(value):
    """Normalized, deduplicated roster of requested Sleeper usernames."""
    return list(dict.fromkeys(x.strip().casefold() for x in str(value or "").split(",") if x.strip()))


def dimensions(count, last=17):
    if count > 32:
        raise ValueError("Dwight Fight supports at most 32 entrants")
    if count < 2:
        raise ValueError("Dwight Fight requires at least two entrants")
    size = 1 << (count - 1).bit_length()
    rounds = size.bit_length() - 1
    return size, last - rounds + 1


def slots(size):
    """Fixed NCAA-style bracket ordering: adjacent slots play each other."""
    result = [1, 2]
    while len(result) < size:
        n = len(result) * 2
        result = [x for seed in result for x in (seed, n + 1 - seed)]
    return result


def resolve(requested, owners, api, session=None, saved=None):
    """Resolve user handles with the Sleeper public API, then map IDs to current teams."""
    session = session or requests
    resolved, errors = [], []
    saved = saved or []
    saved_handles = {str(x.get("username", "")).casefold(): x for x in saved}
    for handle in requested:
        try:
            response = session.get(f"{api}/user/{handle}", timeout=20)
            response.raise_for_status()
            obj = response.json()
        except Exception as exc:
            # Sleeper may stop resolving a renamed handle. An initial bracket
            # supplies the immutable ID to recover the same person.
            old = saved_handles.get(handle)
            if not old:
                errors.append(f"{handle}: Sleeper lookup failed ({exc})")
                continue
            try:
                response = session.get(f"{api}/user/{old['user_id']}", timeout=20)
                response.raise_for_status()
                obj = response.json()
                if not obj or str(obj.get("user_id")) != str(old["user_id"]):
                    raise ValueError("saved Sleeper ID could not be verified")
                print(f"NOTE: renamed Sleeper account {handle} -> {obj.get('username')} (ID {old['user_id']})")
            except Exception as follow:
                errors.append(f"{handle}: saved ID lookup failed ({follow})")
                continue
        uid = str((obj or {}).get("user_id") or "")
        if not uid:
            errors.append(f"{handle}: Sleeper returned no user")
            continue
        team = owners.get(uid)
        if not team:
            errors.append(f"{handle}: user {uid} has no team this season")
            continue
        resolved.append({**team, "user_id": uid,
                         "username": str(obj.get("username") or handle),
                         "display_name": str(obj.get("display_name") or handle)})
    ids = [x["user_id"] for x in resolved]
    if len(set(ids)) != len(ids):
        errors.append("Two supplied usernames resolve to the same Sleeper user ID")
    return resolved, errors


def draw(entrants, ranked, last=17, season=2026):
    size, start = dimensions(len(entrants), last)
    ordered = [dict(x, seed=i + 1) for i, x in enumerate(ranked)]
    byseed = {x["seed"]: x for x in ordered}
    first = [{"a": byseed.get(se), "b": byseed.get(order_b), "winner": None,
              "frozen": False, "score_a": None, "score_b": None,
              "snapshot_a": None, "snapshot_b": None}
             for se, order_b in zip(slots(size)[::2], slots(size)[1::2])]
    # Explicit placeholders preserve the exact path. Byes are auto-advanced in progress().
    rounds = [first]
    for r in range(1, size.bit_length() - 1):
        rounds.append([{"a": None, "b": None, "winner": None, "frozen": False,
                        "score_a": None, "score_b": None,
                        "snapshot_a": None, "snapshot_b": None}
                       for _ in range(len(rounds[-1]) // 2)])
    return {"season": season, "start_week": start, "last_week": last,
            "bracket_size": size, "locked": False, "status": "initial",
            "members": [x["user_id"] for x in ordered],
            "entrants": ordered, "rounds": rounds, "warnings": []}


def rank_entrants(entrants, year):
    frame = ps.standings(year)
    selected = frame.merge(pd.DataFrame([{"LeagueID": str(x["league_id"]),
                                          "RosterID": str(x["roster_id"])}
                                         for x in entrants]), on=["LeagueID", "RosterID"])
    if len(selected) != len(entrants):
        raise ValueError("A Dwight roster is missing from regular-season standings")
    ordered, _, tosses = ps.rank_ties(selected, ps.regular_games(year))
    for toss in tosses:
        print("DWIGHT simulated coin toss:", ", ".join(toss))
    bykey = {(str(x["league_id"]), str(x["roster_id"])): x for x in entrants}
    return [bykey[(str(r.LeagueID), str(r.RosterID))] for r in ordered.itertuples()]


def team_map():
    """Standings_Season is created by users.py before this script runs."""
    frame = pd.read_csv("data/Standings_Season.csv", dtype=str).fillna("")
    out = {}
    for r in frame.to_dict("records"):
        uid = r.get("OwnerID", "")
        if not uid or uid == "Orphan":
            continue
        team = {"league_id": str(r["LeagueID"]), "roster_id": str(r["RosterID"]),
                "league": r.get("LeagueName", ""),
                "team": ""}
        # Name from shared historical/team naming map, not Sleeper's display name.
        import team_names as tn
        team["team"] = tn.season_name(ps.current_season(), team["league"], team["roster_id"]) or team["league"]
        if uid in out:
            print(f"WARNING: Sleeper ID {uid} owns multiple NCAA rosters; first roster used")
            continue
        out[uid] = team
    return out


def same_members(old, fresh):
    return set(old.get("members", [])) == {x["user_id"] for x in fresh}


def update_names(old, fresh):
    by_id = {x["user_id"]: x for x in fresh}
    for x in old["entrants"]:
        new = by_id.get(x["user_id"])
        if new:
            x["username"] = new["username"]
            x["display_name"] = new["display_name"]
    # Match names in every bracket reference, including frozen rounds.
    for rnd in old["rounds"]:
        for game in rnd:
            for side in ("a", "b"):
                x = game[side]
                if x and x["user_id"] in by_id:
                    x["username"] = by_id[x["user_id"]]["username"]
                    x["display_name"] = by_id[x["user_id"]]["display_name"]


def choose(a, b, pa, pb, ma, mb):
    """Score, then official-scoring max PF, then seed."""
    if pa != pb:
        return a if pa > pb else b
    if ma != mb:
        return a if ma > mb else b
    return a if a["seed"] < b["seed"] else b


def advance(bracket, scores, max_points, completed):
    """Only freeze a result once. A frozen winner is never recomputed."""
    rounds = bracket["rounds"]
    for ri, round_games in enumerate(rounds):
        week = bracket["start_week"] + ri
        for gi, g in enumerate(round_games):
            if ri:
                left, right = rounds[ri - 1][2 * gi], rounds[ri - 1][2 * gi + 1]
                g["a"], g["b"] = left["winner"], right["winner"]
            a, b = g["a"], g["b"]
            if a is None and b is None:
                continue
            if (a is None or b is None) and ri == 0:
                g["winner"] = a or b
                g["frozen"] = True  # seed's first-round bye, independent of game scores
                continue
            if not a or not b:
                continue
            ka = (str(a["league_id"]), str(a["roster_id"]))
            kb = (str(b["league_id"]), str(b["roster_id"]))
            pa, pb = scores.get(week, {}).get(ka), scores.get(week, {}).get(kb)
            g["score_a"], g["score_b"] = pa, pb
            if g["frozen"]:
                # Score correction is shown without reopening advancement.
                continue
            if week not in completed or pa is None or pb is None:
                continue
            ma, mb = max_points.get(week, {}).get(ka), max_points.get(week, {}).get(kb)
            if ma is None or mb is None:
                if pa == pb:
                    print(f"WARNING: week {week} tied without MaxPoints; cannot freeze")
                    continue
                ma = ma if ma is not None else -1
                mb = mb if mb is not None else -1
            g["snapshot_a"], g["snapshot_b"] = pa, pb
            g["winner"] = choose(a, b, pa, pb, ma, mb)
            g["frozen"] = True
    final = rounds[-1][0]
    bracket["champion"] = final["winner"] if final["frozen"] and final["a"] and final["b"] else None
    return bracket


def points_for(year, weeks):
    return {w: {tuple(map(str, k)): float(p[0]) for k, p in ps.week_points(year, w).items()}
            for w in weeks}


def max_for(year, path="data/MaxPoints_Season.csv"):
    if not os.path.exists(path):
        return {}
    out = {}
    for r in pd.read_csv(path, dtype=str).fillna("").to_dict("records"):
        if str(r.get("Year")) != str(year) or not r.get("MaxPoints"):
            continue
        w = int(r["Week"])
        out.setdefault(w, {})[(r["LeagueID"], r["RosterID"])] = float(r["MaxPoints"])
    return out


def write_history(year, bracket, path=HISTORY):
    old = []
    if Path(path).exists():
        with open(path, newline="", encoding="utf-8-sig") as f:
            old = [r for r in csv.DictReader(f) if str(r.get("Season")) != str(year)]
    mine = []
    for ri, rnd in enumerate(bracket["rounds"]):
        for g in rnd:
            a, b = g["a"], g["b"]
            if not a or not b:
                continue  # bye is not a played game
            diff = g["frozen"] and (g["score_a"] != g["snapshot_a"] or g["score_b"] != g["snapshot_b"])
            mine.append({"Season": year, "Round": ri + 1,
                         "RoundName": NAMES.get(ri + 1, f"Round {ri + 1}"),
                         "Week": bracket["start_week"] + ri,
                         "TeamA": a["team"], "SeedA": a["seed"],
                         "TeamB": b["team"], "SeedB": b["seed"],
                         "ScoreA": g["score_a"] if g["score_a"] is not None else "",
                         "ScoreB": g["score_b"] if g["score_b"] is not None else "",
                         "Winner": (g["winner"] or {}).get("team", ""),
                         "Notes": "Sleeper differs (frozen advancement)" if diff else "",
                         "Status": "Recorded"})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(old + mine)


def replay_2023(out_dir):
    """Rebuild the archived 11-entrant bracket and assert every recorded matchup.

    Historical fixtures establish team-week points; the independent bracket engine
    must recreate every pairing, bye, advancement and seed from those fixtures.
    """
    if not out_dir:
        raise ValueError("--replay-2023 requires --out-dir to protect production data")
    with open(HISTORY, newline="", encoding="utf-8-sig") as stream:
        old = [x for x in csv.DictReader(stream) if x["Season"] == "2023"]
    seeds = {}
    for r in old:
        for side in "AB":
            seeds[int(r["Seed" + side])] = r["Team" + side]
    if len(seeds) != 11 or set(seeds) != set(range(1, 12)):
        raise AssertionError("2023 archive is missing expected seeds 1–11")
    entrants = [{"seed": k, "user_id": f"historic-{k}",
                 "username": name, "display_name": name, "team": name,
                 "league_id": "historic", "roster_id": str(k), "league": "Historic"}
                for k, name in sorted(seeds.items())]
    bracket = draw(entrants, entrants, 18, 2023)
    scores = {}
    for r in old:
        w = int(r["Week"])
        for side in "AB":
            k = (r["Team" + side], float(r["Score" + side]))
            seed = int(r["Seed" + side])
            scores.setdefault(w, {})[("historic", str(seed))] = k[1]
    advance(bracket, scores, {}, set(range(15, 19)))
    seen = {}
    for ri, rnd in enumerate(bracket["rounds"], 1):
        for g in rnd:
            a, b = g["a"], g["b"]
            if not a or not b:
                continue
            key = (ri, int(a["seed"]), int(b["seed"]))
            seen[key] = g
    for r in old:
        key = (int(r["Round"]), int(r["SeedA"]), int(r["SeedB"]))
        g = seen.pop(key, None)
        if not g:
            raise AssertionError(f"2023 replay missing recorded matchup {key}")
        if (g["winner"] or {}).get("team") != r["Winner"]:
            raise AssertionError(f"2023 replay winner mismatch {key}: {g['winner']} vs {r['Winner']}")
        if round(float(g["score_a"]), 2) != round(float(r["ScoreA"]), 2) or round(float(g["score_b"]), 2) != round(float(r["ScoreB"]), 2):
            raise AssertionError(f"2023 replay score mismatch {key}")
    if seen:
        raise AssertionError(f"2023 replay has unexpected matchups: {sorted(seen)}")
    if bracket["champion"]["team"] != "Arizona State":
        raise AssertionError("2023 champion differs from Arizona State")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "dwight-2023-replay.json").write_text(
        json.dumps(bracket, indent=2) + "\n", encoding="utf-8")
    print(f"Dwight Fight 2023 replay: verified {len(old)} games and Arizona State over Minnesota in the final")
    return bracket


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--out-dir", help="isolate replay/dry-run outputs")
    ap.add_argument("--replay-2023", action="store_true", help="historical weeks 15-18, not a production draw")
    args = ap.parse_args()
    os.chdir(Path(__file__).resolve().parent.parent)
    cfg, postseason = ps.config()
    conf = postseason.get("dwight_fight", {})
    year = 2023 if args.replay_2023 else args.year or ps.current_season()
    if args.replay_2023:
        replay_2023(args.out_dir)
        return
    if year < int(conf.get("from_season", 2026)) and not args.replay_2023:
        print(f"Dwight Fight: {year} precedes from_season; no-op")
        return
    requested = names(conf.get("dwights", ""))
    directory = Path(args.out_dir) if args.out_dir else Path(f"data/scoreboard/{year}")
    output = directory / "dwight.json"
    old = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    if not (old and old.get("locked")):
        if not requested:
            print("Dwight Fight: empty dwights configuration; no-op")
            return
        if len(requested) > 32:
            raise SystemExit("Dwight Fight: at most 32 usernames allowed")
    done = set(ps.completed_weeks(year))
    lr = ps.last_regular_week()
    if not set(range(1, lr + 1)).issubset(done):
        print(f"Dwight Fight {year}: regular season not final; no-op")
        return
    if old and old.get("locked"):
        bracket = old
        print("Dwight Fight: locked bracket retained; configuration edits ignored")
    else:
        fresh, errors = resolve(requested, team_map(), cfg["api"]["sleeper"], saved=old["entrants"] if old else [])
        if errors:
            for err in errors:
                print("WARNING: Dwight Fight:", err)
            pending = old or {"season": year, "status": "pending", "locked": False,
                              "entrants": [], "rounds": [], "start_week": None,
                              "last_week": int(conf.get("last_week", 17))}
            pending["warnings"] = errors
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
            return  # Never lock an invalid field.
        if len(fresh) < 2:
            print("Dwight Fight: fewer than two valid entrants; no-op")
            return
        last = int(conf.get("last_week", 17))
        size, start = dimensions(len(fresh), last)
        current = week_status.current_week(year)
        if old and same_members(old, fresh):
            bracket = old
            update_names(bracket, fresh)
        else:
            bracket = draw(fresh, rank_entrants(fresh, year), last, year)
            print(f"Dwight Fight: initial bracket drawn ({len(fresh)} teams, {size} slots, week {start})")
        bracket["warnings"] = []
        if current >= start:
            bracket["locked"] = True
            bracket["status"] = "locked"
            bracket["locked_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
            print(f"Dwight Fight: bracket locked at Sleeper week {current}")
        else:
            bracket["status"] = "initial"
            print(f"Dwight Fight: initial bracket only; Sleeper week {current}, starts {start}")
    weeks = range(bracket["start_week"], bracket["last_week"] + 1)
    advance(bracket, points_for(year, weeks), max_for(year), done)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bracket, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_history(year, bracket, Path(args.out_dir) / "Dwight_Historic.csv" if args.out_dir else HISTORY)
    print(f"Dwight Fight: wrote {output}")


if __name__ == "__main__":
    main()
