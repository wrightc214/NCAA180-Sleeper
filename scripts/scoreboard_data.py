"""Build compact scoreboard inputs and page; never changes standings/polls or posts.

Run after the weekly baseline snapshot: python scripts/scoreboard_data.py
Default uses Sleeper's season/week and full player metadata. --offline uses the latest
saved baseline and repository position reference for repeatable builds/tests.
Frozen per-week files are created once. Live lineup/score/clock requests happen in-browser.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import html
import json
import os
from pathlib import Path

from site_common import page_head, nav_html, team_colors

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def normalized(settings):
    return {k: round(float(v), 6) for k, v in settings.items() if isinstance(v, (int, float)) and v}


def standard_settings(scoring, overrides):
    # A whole majority ruleset, not a synthetic per-key combination of incompatible rules.
    choices = collections.Counter(json.dumps(normalized(s), sort_keys=True) for s in scoring.values())
    key, count = choices.most_common(1)[0]
    if count <= len(scoring) / 2:
        raise ValueError("No majority scoring ruleset; review standard settings before building")
    return {**json.loads(key), **overrides}


def player_map(full=None):
    result = {}
    # All-player reference retains unsigned players and multi-position eligibility.
    for r in rows("data/backfill/PlayerPositions_All.csv"):
        result[r["PlayerID"]] = {"name": r["Name"], "position": r["Position"],
                                 "positions": (r.get("FantasyPositions") or r["Position"]).split("|"),
                                 "team": r.get("Team", ""), "status": ""}
    for r in rows("data/Players.csv"):
        old = result.get(r["player_id"], {})
        result[r["player_id"]] = {**old, "name": (r["first_name"] + " " + r["last_name"]).strip(),
                                  "position": r["position"], "positions": old.get("positions", [r["position"]]),
                                  "team": r.get("team", ""), "status": r.get("status", "")}
    for pid, p in (full or {}).items():
        positions = p.get("fantasy_positions") or [p.get("position", "")]
        if not any(s in {"QB", "RB", "FB", "WR", "TE", "K", "DEF"} for s in positions):
            continue
        result[str(pid)] = {"name": p.get("full_name") or " ".join(filter(None, [p.get("first_name"), p.get("last_name")])) or str(pid),
                            "position": p.get("position", ""), "positions": positions,
                            "team": p.get("team") or "", "status": p.get("injury_status") or p.get("status") or ""}
    return {k: v for k, v in result.items() if set(v["positions"]) & {"QB", "RB", "FB", "WR", "TE", "K", "DEF"}}


def build(offline=False):
    os.chdir(ROOT)
    cfg = json.loads(Path("config/league.json").read_text())
    full = None
    if offline:
        snapshots = sorted(glob.glob("data/projections/*/wk*_proj.csv"))
        year = max(int(Path(p).parent.name) for p in snapshots)
        week = max(int(Path(p).name[2:4]) for p in snapshots if int(Path(p).parent.name) == year)
    else:
        import requests
        def get(url):
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        state = get(cfg["api"]["sleeper"] + "/state/nfl")
        year, week = int(state["season"]), int(state["week"])
        full = get(cfg["api"]["sleeper"] + "/players/nfl")
        if not isinstance(full, dict) or len(full) < 100:
            raise ValueError("Incomplete player metadata; existing scoreboard data preserved")
    leagues = {r["LeagueID"]: {"name": r["LeagueName"].strip(),
                "slots": [s for s in r["RosterPositions"].split(",") if s not in ("BN", "IR", "TAXI")]}
               for r in rows("data/LeagueIDs_AllYears.csv") if int(r["Year"]) == year}
    if not leagues or any(not v["slots"] for v in leagues.values()):
        raise ValueError("Missing leagues or lineup slots")
    scoring = json.loads(Path(f"data/projections/{year}/scoring.json").read_text())
    if set(scoring) != set(leagues):
        raise ValueError("Scoring snapshot does not cover every league")
    standard = standard_settings(scoring, cfg["scoring"]["overrides"])
    colors = {r["Team"]: r for r in rows("data/Colors - Teams.csv")}
    teams = {}
    for r in rows("data/Teams.csv"):
        c = colors.get(r["Team"], {})
        bg, fg = team_colors(c.get("Primary"), c.get("Secondary"), c.get("Background"), c.get("Text"), name=r["Team"])
        teams.setdefault(r["League"].strip(), {})[r["Roster ID"]] = {
            "name": r["Team"], "primary": c.get("Primary") or bg, "secondary": c.get("Secondary") or fg,
            "background": bg, "text": fg,
            "logo": f"../assets/logos/teams/{r['Team']}.png" if Path(f"assets/logos/teams/{r['Team']}.png").exists() else ""}
    for lid, league in leagues.items():
        league["teams"] = teams.get(league["name"], {})
        if not league["teams"]:
            raise ValueError(f"No team identities for {league['name']}")
    players = player_map(full)
    base = Path(f"data/scoreboard/{year}")
    # Baselines never refresh once exported. New manual snapshots cannot replace them.
    available = []
    for wk in sorted({int(Path(p).name[2:4]) for p in glob.glob(f"data/projections/{year}/wk*_proj.csv")}):
        p = sorted(glob.glob(f"data/projections/{year}/wk{wk:02d}_*_proj.csv"))[0]
        projections = rows(p)
        if any(r.get("GameState") in ("in", "post") for r in projections):
            continue
        target = base / f"week-{wk:02d}.json"
        if not target.exists():
            baseline = {r["PlayerID"]: json.loads(r["Stats"] or "{}") for r in projections}
            odds = [r for r in rows("data/MatchupProjections_Historic.csv") if int(r["Year"]) == year and int(r["Week"]) == wk]
            if len(odds) != sum(len(l["teams"]) for l in leagues.values()) // 2:
                raise ValueError(f"Incomplete frozen matchup odds for week {wk}")
            dump(target, {"season": year, "week": wk, "snapshot": projections[0]["SnapshotUTC"],
                          "projections": baseline, "odds": odds, "scoring": standard,
                          "player_info": {r["PlayerID"]: {"team": r.get("NFLTeam", ""), "position": r.get("Position", "")} for r in projections}})
        available.append(wk)
    if week not in available:
        raise ValueError(f"No valid pregame baseline for {year} week {week}; existing index preserved")
    dump(base / "players.json", players)
    dump("data/scoreboard/index.json", {"season": year, "week": week, "weeks": available, "leagues": leagues,
         "standard_scoring": standard, "metadata_source": "repository reference" if offline else "Sleeper full player feed",
         "built_at": dt.datetime.now(dt.timezone.utc).isoformat()})
    css = Path("reports/assets/scoreboard.css").read_text()
    body = '''<div class="wrap gwrap">
<div class="validation" role="note"><strong>⚠ SCOREBOARD VALIDATION PHASE</strong>
<p>Questions or inaccuracies? <b>Ping @Wrightc214 on Discord</b> with the matchup and what looks wrong.</p></div>
<nav class="weeks" aria-label="Pages">''' + nav_html("scoreboard") + '''</nav>
<header><div><div class="eyebrow">NCAA 180 · standard scoring</div><h1>Live <em>scoreboard</em></h1></div></header>
<form id="chooser" class="tools"><label>League <select id="league"></select></label><label>Week <select id="week"></select></label>
<label>Game <select id="game"></select></label></form>
<div class="tools"><button id="refresh" type="button">↻ Refresh</button><span id="updated" role="status">Loading…</span></div>
<p id="error" role="alert" hidden></p><div id="board" aria-busy="true"></div>
<p class="note">Scores retain Sleeper points and apply the standard-rule correction. † appears only when a scoring-rule difference changes a team’s score.
Records currently follow the published standings. Live odds and minutes remaining are estimates, not official results.
Tuesday pregame expectations stay frozen. Live projection = points so far + player projection × share of game remaining.
Questions? Ping @Wrightc214 on Discord.</p></div>
<script src="assets/scoreboard-core.js"></script><script src="assets/scoreboard.js" defer></script></body></html>'''
    body = body.replace("@Wrightc214", "@" + html.escape(cfg["contact"]["username"]))
    Path("reports/scoreboard.html").write_text(page_head("NCAA 180 Scoreboard", css) + body, encoding="utf-8")
    print(f"Scoreboard: {len(leagues)} leagues, {len(players)} players, baselines {available}; default {year}/{week}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    build(parser.parse_args().offline)
