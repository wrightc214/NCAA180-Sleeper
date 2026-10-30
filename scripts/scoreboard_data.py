"""Build compact scoreboard inputs and page; never changes standings/polls or posts.

Run after the weekly baseline snapshot: python scripts/scoreboard_data.py
Default uses Sleeper's season/week and full player metadata. --offline uses the latest
saved baseline and repository position reference for repeatable builds/tests.
Frozen per-week files are created once. Live lineup/score/clock requests happen in-browser.
"""
import argparse
import csv
import datetime as dt
import glob
import html
import json
import os
from pathlib import Path

from site_common import page_head, nav_html, team_colors
from league_config import league_display, normalized, standard_settings  # noqa: F401 (normalized re-exported for tests)

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


def ccg_pairs(year, wk, odds, leagues):
    """CCG week: exactly one game per league, and it must be the game conference_championships.py
    wrote to Postseason_Season.csv. Otherwise nothing is frozen (frozen files never change)."""
    games = {}
    path = "data/Postseason_Season.csv"
    for r in (rows(path) if Path(path).exists() else []):
        if r["Round"] == "CCG" and str(r["Year"]) == str(year) and str(r["Week"]) == str(wk):
            games.setdefault(r["LeagueID"], set()).add(r["RosterID"])
    if len(games) != len(leagues) or any(len(g) != 2 for g in games.values()):
        raise ValueError(f"CCG pairings incomplete ({len(games)} of {len(leagues)} leagues); "
                         f"run conference_championships.py before freezing week {wk}")
    pairs = []
    for r in odds:
        if {r["RosterID"], r["OpponentRosterID"]} != games.get(r["LeagueID"]):
            raise ValueError(f"Week {wk} odds row {r['Team']} vs {r['OppTeam']} is not a CCG game")
        pairs.append({"game": "ccg", "LeagueID": r["LeagueID"], "rosters": [r["RosterID"], r["OpponentRosterID"]],
                      "label": "Conference Championship"})
    if len(pairs) != len(leagues):
        raise ValueError(f"Week {wk}: {len(pairs)} CCG odds rows for {len(leagues)} leagues")
    return pairs


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
    short = league_display()
    leagues = {r["LeagueID"]: {"name": r["LeagueName"].strip(), "label": short.get(r["LeagueName"].strip(), r["LeagueName"].strip()),
                "slots": [s for s in r["RosterPositions"].split(",") if s not in ("BN", "IR", "TAXI")]}
               for r in rows("data/LeagueIDs_AllYears.csv") if int(r["Year"]) == year}
    if not leagues or any(not v["slots"] for v in leagues.values()):
        raise ValueError("Missing leagues or lineup slots")
    scoring = json.loads(Path(f"data/projections/{year}/scoring.json").read_text())
    if set(scoring) != set(leagues):
        raise ValueError("Scoring snapshot does not cover every league")
    standard = standard_settings(scoring)
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
            extra = {}
            if wk >= cfg["schedule"]["ccg_week"]:
                # Sleeper's postseason pairings are placeholders; the matchups page pairs the real
                # CCG games (from Postseason_Season.csv), so its frozen odds are the real games.
                if wk != cfg["schedule"]["ccg_week"]:
                    print(f"Week {wk}: postseason weeks after the CCG are not supported yet; not frozen")
                    continue
                extra = {"event": "CCG", "pairs": ccg_pairs(year, wk, odds, leagues)}
            elif len(odds) != sum(len(l["teams"]) for l in leagues.values()) // 2:
                raise ValueError(f"Incomplete frozen matchup odds for week {wk}")
            dump(target, {"season": year, "week": wk, "snapshot": projections[0]["SnapshotUTC"],
                          "projections": baseline, "odds": odds, "scoring": standard, **extra,
                          "player_info": {r["PlayerID"]: {"team": r.get("NFLTeam", ""), "position": r.get("Position", "")} for r in projections}})
        available.append(wk)
    if week not in available and week > cfg["schedule"]["ccg_week"] and available:
        print(f"Week {week} is past the CCG (not supported yet); scoreboard defaults to week {max(available)}")
        week = max(available)
    if week not in available:
        raise ValueError(f"No valid pregame baseline for {year} week {week}; existing index preserved")
    dump(base / "players.json", players)
    dump("data/scoreboard/index.json", {"season": year, "week": week, "weeks": available, "leagues": leagues,
         "standard_scoring": standard, "metadata_source": "repository reference" if offline else "Sleeper full player feed",
         "built_at": dt.datetime.now(dt.timezone.utc).isoformat()})
    write_page(cfg)
    print(f"Scoreboard: {len(leagues)} leagues, {len(players)} players, baselines {available}; default {year}/{week}")


def write_page(cfg):
    """Static shell only. Everything game-specific is fetched by the page."""
    brand = html.escape(cfg.get("brand", ""))
    contact = "@" + html.escape(cfg["contact"]["username"])
    css = Path("reports/assets/scoreboard.css").read_text() + Path("reports/assets/scoreboard-overview.css").read_text()
    league_colors = {r["League"].strip().upper(): r for r in rows("data/Colors - Leagues.csv")}
    index = json.loads(Path("data/scoreboard/index.json").read_text())
    themes = {}
    logos = {Path(f).stem.lower(): Path(f).name for f in glob.glob("assets/logos/Leagues/*.png")}
    for lid, league in index["leagues"].items():
        name = league["name"]
        c = league_colors.get(name.upper(), {})
        bg, fg = team_colors(c.get("Primary"), c.get("Secondary"), c.get("Background"), c.get("Text"), name=c.get("League", name))
        label = league_display().get(name.strip(), name.removeprefix("NCAA ")).upper()  # short name (LeagueShortNames.csv)
        logo = logos.get(label.lower(), "")
        themes[lid] = {"background": bg, "text": fg, "label": label,
                       "logo": f"../assets/logos/Leagues/{logo}" if logo else ""}
    dump("data/scoreboard/leagues.json", themes)
    # Header matches the rest of the site: nav, eyebrow, big two-tone title, accent rule; banner below it.
    body = f'''<div class="wrap gwrap">
<nav class="weeks" aria-label="Pages">''' + nav_html("scoreboard") + f'''</nav>
<header class="sbh"><div><div class="eyebrow">{len(index["leagues"])} conferences · live scores · standard scoring</div><h1>{brand} <em>Scoreboard</em></h1></div></header>
<div class="validation" role="note"><strong>⚠ Validation phase</strong> Questions or inaccuracies? <b>Ping {contact} on Discord</b> with the matchup.</div>
<a id="overview-back" class="overview-back" href="scoreboard.html" hidden>← All games</a>
<form id="chooser" class="tools pick"><select id="league" aria-label="League"></select><select id="week" aria-label="Week"></select>
<select id="game" aria-label="Game"></select></form>
<div class="tools"><button id="refresh" type="button">↻ Refresh</button><span id="updated" role="status">Loading…</span></div>
<p id="overview-help" class="note" hidden>Select a game for player details. Final games show Tuesday’s pregame win chance; live games show an estimate. — means odds unavailable.</p>
<p id="error" role="alert" hidden></p><div id="board" aria-busy="true"></div>
<p class="note">Scores retain Sleeper points and apply the standard-rule correction. † appears only when a scoring-rule difference changes a team’s score.
Records currently follow the published standings. Live odds and minutes remaining are estimates, not official results.
Tuesday pregame expectations stay frozen. Live projection = points so far + player projection × share of game remaining.
Questions? Ping {contact} on Discord.</p></div>
<script src="assets/scoreboard-core.js"></script><script src="assets/scoreboard-overview-model.js"></script><script src="assets/scoreboard-overview.js" defer></script><script src="assets/scoreboard.js" defer></script></body></html>'''
    Path("reports/scoreboard.html").write_text(page_head(f"{brand} Scoreboard", css) + body, encoding="utf-8")


def refresh_players():
    """Game-day refresh: one Sleeper player call server-side, so browsers never download it."""
    os.chdir(ROOT)
    import requests
    cfg = json.loads(Path("config/league.json").read_text())
    season = json.loads(Path("data/scoreboard/index.json").read_text())["season"]
    r = requests.get(cfg["api"]["sleeper"] + "/players/nfl", timeout=60)
    r.raise_for_status()
    full = r.json()
    if not isinstance(full, dict) or len(full) < 100:
        raise ValueError("Incomplete player metadata; existing players.json preserved")
    dump(f"data/scoreboard/{season}/players.json", player_map(full))
    print(f"Scoreboard players refreshed for {season}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--players-only", action="store_true", help="refresh player statuses only (game days)")
    parser.add_argument("--page-only", action="store_true", help="rewrite reports/scoreboard.html only")
    a = parser.parse_args()
    if a.players_only:
        refresh_players()
    elif a.page_only:
        os.chdir(ROOT)
        write_page(json.loads(Path("config/league.json").read_text()))
    else:
        build(a.offline)
