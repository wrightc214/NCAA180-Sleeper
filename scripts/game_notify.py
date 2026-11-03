"""
game_notify.py -- game notifications for followed teams (todo-pwa.md, Chris 2026-11-01/03).

Each phone picks one frequency (Notifications page; stored as an event follow "freq:<x>"):
  windows  after each NFL window closes (Thu, Sun early, Sun late, Sun night, Mon)
  sunday   one update after Sunday's games, then each game when it's final
  final    each game when it's final (default)
  off      nothing (postseason result pushes still follow the phone's other follows)
A game is FINAL when both teams have 0 minutes left (every starter's NFL game over / out / bye).
Live lines show score, projection and win chance -- the same numbers as the scoreboard page
(live_model.py = Python twin of scoreboard-core.js).

Runs (workflow game-notify.yml) a little after each window's scheduled end. If any NFL game is
still live, it waits 15 minutes and checks again (up to WAIT_MAX), then stops; the next run or
the Tuesday settle catches anything left. Everything is sent once: data/push/GameNotify_Season.csv.

  python scripts/game_notify.py                 normal run (current Sleeper week)
  python scripts/game_notify.py --week 9 --test send to tester phones only, ignore + don't write the ledger
  python scripts/game_notify.py --week 9 --dry-run   print what each kind of phone would get
  python scripts/game_notify.py --settle        Tuesday: push a correction only where settled
                                                (standard) scores flip a game-night final
Pairings: weeks 1..last_regular_week from Sleeper's matchups; later weeks from
Postseason_Season.csv (CCG, playoff, bowls, NIT groups). CWD = repo root.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
import live_model as L  # noqa: E402
import notify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "push" / "GameNotify_Season.csv"
LEDGER_COLS = ["Year", "Week", "Key", "Kind", "At", "Data"]
ET = ZoneInfo("America/New_York")
WAIT_STEP = 15 * 60
WAIT_MAX = 2 * 3600
FREQS = ("windows", "sunday", "final", "off")
DEFAULT_FREQ = "final"
ALIASES = {"WSH": "WAS", "LA": "LAR", "JAC": "JAX"}


# ---------------- ledger ----------------

def ledger_rows():
    if not LEDGER.exists():
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ledger_add(rows):
    allrows = ledger_rows() + rows
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        w.writerows(allrows)


# ---------------- data ----------------

def get(url):
    for i in range(3):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == 2:
                raise
            time.sleep(3 * (i + 1))


def leagues(season):
    smap = notify.league_short_map()
    out = []
    with open(ROOT / "data" / "LeagueIDs_AllYears.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r["Year"] == str(season):
                out.append({"id": r["LeagueID"], "full": r["LeagueName"].strip(),
                            "short": smap.get(r["LeagueName"].strip(), r["LeagueName"].strip())})
    return out


def team_names():
    with open(ROOT / "data" / "Teams.csv", encoding="utf-8-sig") as f:
        return {(r["League"].strip(), str(int(float(r["Roster ID"])))): r["Team"].strip() for r in csv.DictReader(f)}


def nfl_games(season, week):
    """{team abbr: game}, plus the week's windows [(key, label, start ET, [game states])]."""
    data = get(f"{lcfg.espn()}?dates={season}&week={week}&seasontype=2")
    by_team, events = {}, []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        st = comp.get("status") or ev.get("status") or {}
        typ = st.get("type") or {}
        state = typ.get("state", "pre")
        if state == "post" and not typ.get("completed", True):
            state = "unknown"
        game = {"state": state, "period": st.get("period", 0), "clock": st.get("displayClock", "")}
        start = dt.datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(ET)
        events.append((start, game))
        for side in comp.get("competitors", []):
            ab = (side.get("team") or {}).get("abbreviation")
            if ab:
                by_team[ALIASES.get(ab, ab)] = game
    windows = {}
    for start, game in events:
        key, label = window_of(start)
        windows.setdefault(key, {"key": key, "label": label, "start": start, "games": []})["games"].append(game)
    return by_team, sorted(windows.values(), key=lambda w: w["start"])


def window_of(start):
    day = start.strftime("%a")
    if day == "Sun":
        if start.hour < 15:
            return "sun-early", "Sunday's early games"
        if start.hour < 19:
            return "sun-late", "Sunday's late games"
        return "sun-night", "Sunday night"
    names = {"Thu": "Thursday night", "Fri": "Friday's games", "Sat": "Saturday's games", "Mon": "Monday night",
             "Tue": "Tuesday's games", "Wed": "Wednesday's games"}
    return f"{day.lower()}-{start.date().isoformat()}", names.get(day, day)


def pairings(season, week, lgs):
    """[{id, label, members: [(league_id, roster_id)]}] for the week."""
    cfg = lcfg.cfg()
    by_id = {l["id"]: l for l in lgs}
    if week <= int(cfg["schedule"]["last_regular_week"]):
        out = []
        for l in lgs:
            groups = {}
            for m in get(f"{lcfg.sleeper()}/league/{l['id']}/matchups/{week}") or []:
                if m.get("matchup_id") is not None:
                    groups.setdefault(m["matchup_id"], []).append((l["id"], str(m["roster_id"])))
            out += [{"id": f"w{week}-{l['short']}-{k}", "label": "", "members": v} for k, v in groups.items()]
        return out
    path = ROOT / "data" / "Postseason_Season.csv"
    if not path.exists():
        return []
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["Year"] != str(season) or str(r["Week"]) != str(week) or r["LeagueID"] not in by_id:
                continue
            label = (by_id[r["LeagueID"]]["short"] + " championship" if r["Round"] == "CCG"
                     else r["BowlName"] if r["Round"] == "Bowl"
                     else f"NIT {r['BowlName'] or r['Stage']}" if r["Round"] == "NIT" else r["Stage"] or "Playoff")
            g = out.setdefault(r["GameID"], {"id": r["GameID"], "label": label, "members": []})
            g["members"].append((r["LeagueID"], str(r["RosterID"]).replace(".0", "")))
    return list(out.values())


def build_games(season, week):
    """Every game this week with live team models. Returns (games, windows, any_live)."""
    lgs = leagues(season)
    base = ROOT / "data" / "scoreboard" / str(season)
    baseline = json.loads((base / f"week-{week:02d}.json").read_text(encoding="utf-8"))
    meta = json.loads((base / "players.json").read_text(encoding="utf-8"))
    cfgj = lcfg.cfg()
    stats_feed = get(f"{lcfg.sleeper()}/stats/nfl/regular/{season}/{week}")
    stats = ({str(p["player_id"]): p.get("stats") or {} for p in stats_feed if p.get("player_id")}
             if isinstance(stats_feed, list) else {k: (v.get("stats") or v) for k, v in stats_feed.items()})
    by_team, windows = nfl_games(season, week)
    if any(g["state"] not in ("pre",) for w in windows for g in w["games"]) and len(stats) < 100:
        raise SystemExit("Statistics feed looks incomplete; not sending anything this run.")
    names = team_names()
    by_id = {l["id"]: l for l in lgs}
    rosters = {}
    for l in lgs:
        rules = (get(f"{lcfg.sleeper()}/league/{l['id']}") or {}).get("scoring_settings") or {}
        for m in get(f"{lcfg.sleeper()}/league/{l['id']}/matchups/{week}") or []:
            rosters[(l["id"], str(m["roster_id"]))] = (m, rules)
    past = False
    games = []
    for p in pairings(season, week, lgs):
        teams = []
        for lid, rid in p["members"]:
            if (lid, rid) not in rosters:
                continue
            roster, rules = rosters[(lid, rid)]
            cfg = {"position_sd": cfgj["position_sd"], "standard_scoring": baseline["scoring"], "official_scoring": rules}
            players = {}
            for pid in {str(x) for x in (roster.get("players") or []) + (roster.get("starters") or [])}:
                if pid == "0":
                    continue
                md = dict(meta.get(pid) or {}) or None
                if md is not None and not md.get("team") and (baseline.get("player_info") or {}).get(pid, {}).get("team"):
                    md["team"] = baseline["player_info"][pid]["team"]
                game = by_team.get(md["team"], {"state": "bye"}) if md and md.get("team") else None
                players[pid] = L.player_model(pid, md, stats.get(pid), baseline["projections"].get(pid), game,
                                              (roster.get("players_points") or {}).get(pid), cfg, past)
            model = L.team_model(roster, players)
            short = by_id[lid]["short"]
            teams.append({"league_id": lid, "roster_id": rid, "slot": notify.slot_key(short, rid),
                          "name": names.get((by_id[lid]["full"], rid), f"{short} #{rid}"), "model": model,
                          "done": L.is_done(model)})
        if len(teams) >= 2:
            games.append({"id": p["id"], "label": p["label"], "teams": teams, "done": all(t["done"] for t in teams)})
    any_live = any(g["state"] == "in" for w in windows for g in w["games"])
    return games, windows, any_live


# ---------------- text ----------------

def fmt(x, d=1):
    return f"{x:.{d}f}"


def line(game, slot):
    """One line from the followed team's point of view."""
    teams = game["teams"]
    me = next((t for t in teams if t["slot"] == slot), teams[0])
    others = [t for t in teams if t is not me]
    pre = f"{game['label']}: " if game["label"] else ""
    if len(teams) == 2:
        o = others[0]
        a, b = me["model"], o["model"]
        if game["done"]:
            res = "W" if a["actual"] > b["actual"] else "L" if a["actual"] < b["actual"] else "T"
            return f"{pre}{me['name']} {res} {fmt(a['actual'], 2)}–{fmt(b['actual'], 2)} vs {o['name']} · Final"
        pct = round(L.probability(a, b))
        pct = max(1, min(99, pct)) if 0 < L.probability(a, b) < 100 else pct
        started = a["actual"] or b["actual"]
        score = f"{fmt(a['actual'])}–{fmt(b['actual'])}" if started else "vs"
        return (f"{pre}{me['name']} {score} {o['name']} · proj {fmt(a['projected'], 0)}–{fmt(b['projected'], 0)}"
                f" · {pct}% to win")
    key = "actual" if game["done"] else "projected"
    order = sorted(teams, key=lambda t: -t["model"][key])
    rank = order.index(me) + 1
    if game["done"]:
        return (f"{pre}{me['name']} {'wins' if rank == 1 else f'is {rank} of {len(teams)}'} ({fmt(me['model']['actual'], 2)})"
                + ("" if rank == 1 else f" · {order[0]['name']} advances"))
    return f"{pre}{me['name']} {fmt(me['model']['actual'])} · proj {fmt(me['model']['projected'], 0)} · {rank} of {len(teams)}"


def final_title(game, slot):
    t = next(t for t in game["teams"] if t["slot"] == slot)
    others = [x for x in game["teams"] if x is not t]
    best = max(x["model"]["actual"] for x in others)
    won = t["model"]["actual"] > best
    return f"Final: {t['name']} {'won' if won else 'tied' if t['model']['actual'] == best else 'lost'}"


# ---------------- who gets what ----------------

def freq_of(f):
    for k in f["event"]:
        if k.startswith("freq:") and k[5:] in FREQS:
            return k[5:]
    return DEFAULT_FREQ


def plan(devices, games, windows, done_keys, week):
    """Payloads per device for this evaluation, plus the ledger rows to write."""
    newly_final = [g for g in games if g["done"] and f"final:{g['id']}" not in done_keys]
    complete = [w for w in windows if all(g["state"] == "post" for g in w["games"])]
    due_windows = [w for w in complete if f"window:{w['key']}" not in done_keys]
    sun = [w for w in windows if w["key"].startswith("sun-")]
    sunday_due = bool(sun) and all(w in complete for w in sun) and "sunday" not in done_keys
    sunday_sent_before = "sunday" in done_keys
    finals_since_window = {k[6:] for k in done_keys.get("_finals_since_window", set())}
    sends = []
    for d in devices:
        f = notify._follows(d)
        if not f["team"]:
            continue
        freq = freq_of(f)
        if freq == "off":
            continue
        mine = [(g, next(t["slot"] for t in g["teams"] if t["slot"] in f["team"]))
                for g in games if any(t["slot"] in f["team"] for t in g["teams"])]
        if not mine:
            continue
        title, lines = None, []
        fin = [(g, s) for g, s in mine if g in newly_final]
        if freq == "final" or (freq == "sunday" and sunday_sent_before):
            if fin:
                lines = [line(g, s) for g, s in fin]
                title = final_title(*fin[0]) if len(fin) == 1 else f"{len(fin)} of your games are final"
        elif freq == "sunday" and sunday_due:
            lines = [line(g, s) for g, s in mine]
            title = "After Sunday's games"
        elif freq == "windows" and due_windows:
            show = [(g, s) for g, s in mine if not g["done"] or g in newly_final or g["id"] in finals_since_window]
            lines = [line(g, s) for g, s in show]
            title = f"After {due_windows[-1]['label']}"
        if title and lines:
            if len(lines) > notify.MAX_LINES:
                lines = lines[:notify.MAX_LINES - 1] + [f"+{len(lines) - notify.MAX_LINES + 1} more"]
            sends.append((d, {"title": title, "body": "\n".join(lines), "url": "scoreboard.html",
                              "tag": f"games-w{week}-{len(done_keys)}"}))
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for g in newly_final:
        top = max(g["teams"], key=lambda t: t["model"]["actual"])
        rows.append({"Key": f"final:{g['id']}", "Kind": "final", "At": now, "Data": json.dumps({
            "teams": [{"league_id": t["league_id"], "roster_id": t["roster_id"], "slot": t["slot"], "name": t["name"],
                       "points": t["model"]["actual"]} for t in g["teams"]], "winner": top["slot"], "label": g["label"]})})
    rows += [{"Key": f"window:{w['key']}", "Kind": "window", "At": now, "Data": ""} for w in due_windows]
    if sunday_due:
        rows.append({"Key": "sunday", "Kind": "sunday", "At": now, "Data": ""})
    return sends, rows


def week_keys(season, week):
    """Ledger keys already used this week, and the finals recorded since the last window push."""
    keys, since = {}, set()
    for r in ledger_rows():
        if r["Year"] == str(season) and r["Week"] == str(week):
            keys[r["Key"]] = r
            if r["Kind"] == "window":
                since = set()
            elif r["Kind"] == "final":
                since.add(r["Key"])
    keys["_finals_since_window"] = since
    return keys


def deliver(sends, test=False):
    sent, gone, failed = 0, [], 0
    for d, payload in sends:
        if test and not d.get("is_test"):
            continue
        try:
            if notify._send_one(d, payload):
                sent += 1
            else:
                gone.append(d["id"])
        except Exception as e:
            failed += 1
            print(f"::warning::push to device {d.get('id', '?')[:8]} failed: {e}")
    if gone:
        notify._worker("/admin/prune", "POST", {"ids": gone})
    return sent, len(gone), failed


# ---------------- runs ----------------

def run(season, week, test=False, dry=False, wait=True):
    waited = 0
    while True:
        games, windows, any_live = build_games(season, week)
        keys = {} if test else week_keys(season, week)
        if test:
            keys["_finals_since_window"] = set()
        if dry:
            devices = [{"id": f"sample-{fq}", "follows": [{"kind": "event", "key": f"{notify._group()}|freq:{fq}"}] +
                        [{"kind": "team", "key": f"{notify._group()}|{t['slot']}"} for g in games[:2] for t in g["teams"][:1]]}
                       for fq in FREQS]
        else:
            devices = notify.fetch_devices()
        sends, rows = plan(devices, games, windows, keys, week)
        print(f"week {week}: {len(games)} games, {sum(g['done'] for g in games)} final; "
              f"windows complete {[w['key'] for w in windows if all(x['state'] == 'post' for x in w['games'])]}; "
              f"{len(sends)} push(es) to send")
        if dry:
            for d, p in sends:
                print(f"  [{d['id']}] {p['title']}\n    " + p["body"].replace("\n", "\n    "))
        elif sends:
            sent, pruned, failed = deliver(sends, test)
            print(f"sent {sent}; pruned {pruned}; failed {failed}")
        if rows and not test and not dry:
            ledger_add([{"Year": season, "Week": week, **r} for r in rows])
        if not wait or not any_live or test or dry or waited >= WAIT_MAX:
            if any_live and waited >= WAIT_MAX:
                print("Games still live after the wait limit; the next run or Tuesday's settle will catch them.")
            return
        print(f"NFL games still live; checking again in {WAIT_STEP // 60} minutes.")
        time.sleep(WAIT_STEP)
        waited += WAIT_STEP


def settle(season, test=False, dry=False):
    """Tuesday: compare each game-night final with the settled standard scores. Push only flips."""
    std = {}
    path = ROOT / "data" / "ScoresStandard_Season.csv"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                std[(r["Year"], r["LeagueID"], str(r["Week"]), str(r["RosterID"]).replace(".0", ""))] = float(r["PointsStandard"])
    rows = [r for r in ledger_rows() if r["Year"] == str(season)]
    settled = {r["Key"][8:] for r in rows if r["Kind"] == "settled"}
    flips, out_rows = [], []
    for r in rows:
        if r["Kind"] != "final" or r["Key"][6:] in settled:
            continue
        d = json.loads(r["Data"])
        pts = [std.get((str(season), t["league_id"], r["Week"], t["roster_id"])) for t in d["teams"]]
        if any(p is None for p in pts):
            continue  # not settled yet
        top = max(range(len(pts)), key=lambda i: pts[i])
        new_winner = d["teams"][top]["slot"]
        out_rows.append({"Year": season, "Week": r["Week"], "Key": f"settled:{r['Key'][6:]}", "Kind": "settled",
                         "At": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "Data": json.dumps({"points": pts, "winner": new_winner, "flipped": new_winner != d["winner"]})})
        if new_winner != d["winner"]:
            w = d["teams"][top]
            others = " / ".join(f"{t['name']} {p:.2f}" for t, p in zip(d["teams"], pts) if t is not w)
            flips.append({"slots": {t["slot"] for t in d["teams"]},
                          "text": f"{(d['label'] + ': ') if d['label'] else ''}{w['name']} {pts[top]:.2f} beats {others} after stat corrections"})
    print(f"settle: {len(out_rows)} game(s) settled, {len(flips)} flipped")
    if flips and not dry:
        sends = []
        for dvc in notify.fetch_devices():
            f = notify._follows(dvc)
            if freq_of(f) == "off":
                continue
            mine = [x["text"] for x in flips if x["slots"] & f["team"]]
            if mine:
                sends.append((dvc, {"title": "Result changed after stat corrections", "body": "\n".join(mine),
                                    "url": "standings.html", "tag": "flip"}))
        print("sent %d; pruned %d; failed %d" % deliver(sends, test))
    elif flips:
        for x in flips:
            print("  [dry-run] " + x["text"])
    if out_rows and not test and not dry:
        ledger_add(out_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int)
    ap.add_argument("--test", action="store_true", help="tester phones only; ledger untouched")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--settle", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()
    season = lcfg.season()
    if not a.dry_run and not notify.push_ready():
        print("Push not configured (worker_url / secrets); nothing to do.")
        return
    if a.settle:
        settle(season, a.test, a.dry_run)
        return
    week = a.week or int(get(f"{lcfg.sleeper()}/state/nfl").get("week") or 0)
    if not (ROOT / "data" / "scoreboard" / str(season) / f"week-{week:02d}.json").exists():
        print(f"No scoreboard baseline for week {week} yet; nothing to do.")
        return
    run(season, week, a.test, a.dry_run, wait=not a.no_wait)


if __name__ == "__main__":
    main()
