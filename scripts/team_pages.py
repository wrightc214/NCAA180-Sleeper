"""team_pages.py -- team pages, stage 1 (task 5.20).

A team is one ROSTER: its league + Sleeper roster_id. Not a manager, not a school.
  - The page's look (name, logo, colours) comes from the team's current identity.
  - Past seasons show the name the team had that season (data/TeamNames_Historic.csv).
  - Sleeper league IDs change every season, so seasons are matched by league NAME + RosterID
    (season_key below; JS twin: reports/assets/team-link.js). A season where that league/roster
    didn't exist simply has no block.

Writes (CWD = repo root, no network):
  data/teams/index.json              current leagues and teams, every season's league IDs -> name
  data/teams/<league slug>-<roster>.json   one file per current team (header, roster, trophies,
                                     seasons, drafts, transactions)
  reports/team.html                  the one template page; team.html?league=<current league id>&roster=<id>
                                     (no query: a team picker)
Settings: config/team_pages.json. Run after trophies.py, transactions_page.py and standings.py.
  python scripts/team_pages.py
"""
import ast
import csv
import datetime as dt
import glob
import html
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
import standard_results  # noqa: E402
import team_names as tn  # noqa: E402
from site_common import (SECTIONS_JS, fixed_bg_src, logo_info, menu_html, page_head,  # noqa: E402
                         team_colors)

CONFIG = "config/team_pages.json"
OUT_DIR = "data/teams"
PAGE = "reports/team.html"
LEAGUE_FILES = ["data/backfill/LeagueIDs_2019_2020.csv", "data/LeagueIDs_AllYears.csv"]
MATCHUP_FILES = ["data/backfill/Matchups_2019_2020.csv", "data/Matchups_Historic.csv", "data/Matchups_Season.csv"]
STANDING_FILES = ["data/backfill/Standings_2019_2020.csv", "data/Standings_Historic.csv", "data/Standings_Season.csv"]
OVERALL = "data/OverallStandings_Season.csv"
POSTSEASON_DIR = "data/postseason"
POSTSEASON_SEASON = "data/Postseason_Season.csv"
TROPHY_FILES = ["data/Trophies_Historic.csv", "data/Trophies_Season.csv"]
DRAFT_FILES = ["data/backfill/Drafts_2019_2020.csv", "data/Drafts_Historic.csv", "data/Drafts_Season.csv"]
PICK_FILES = ["data/backfill/DraftPicks_2019_2020.csv", "data/DraftPicks_Historic.csv", "data/DraftPicks_Season.csv"]
MANUAL_PICKS = "data/DraftPicksManual_Historic.csv"
TX_FILES = ["data/backfill/Transactions_2019_2020.csv", "data/Transactions_Historic.csv", "data/Transactions_Season.csv"]
ROSTERS = "data/Rosters_Current.csv"
PLAYERS = "data/Players.csv"
PLAYER_NAMES = "data/backfill/PlayerPositions_All.csv"

DEFAULTS = {"position_order": ["QB", "RB", "WR", "TE", "K", "DEF"], "transactions_shown": 25,
            "startup_draft_min_rounds": 6, "current_season_open": True}


def settings(path=CONFIG):
    """config/team_pages.json over safe defaults (bad or missing values fall back)."""
    out = dict(DEFAULTS)
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    for k, v in raw.items():
        if k.startswith("_") or k not in DEFAULTS:
            continue
        if isinstance(DEFAULTS[k], bool):
            out[k] = v if isinstance(v, bool) else DEFAULTS[k]
        elif isinstance(DEFAULTS[k], int):
            out[k] = v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else DEFAULTS[k]
        elif isinstance(DEFAULTS[k], list):
            out[k] = [str(x).upper() for x in v] if isinstance(v, list) and v else DEFAULTS[k]
    return out


# ---- Season matching (JS twin: reports/assets/team-link.js) ------------------------------------
def norm_league(name):
    """League names as one key: trimmed, single-spaced, upper case ('NCAA PAC 12 ' in 2019 = 'NCAA PAC 12')."""
    return " ".join(str(name or "").split()).upper()


def rid(v):
    """Roster ID as a plain string ('7', 7, '7.0' -> '7'); '' when blank."""
    s = str(v if v is not None else "").strip()
    if not s or s.lower() == "nan":
        return ""
    try:
        return str(int(float(s)))
    except ValueError:
        return s


def season_key(league_name, roster_id):
    """Identity of a team in any season: league name + roster ID."""
    return f"{norm_league(league_name)}|{rid(roster_id)}"


def slug(league_name):
    return re.sub(r"[^a-z0-9]+", "-", norm_league(league_name).lower()).strip("-")


def team_file(league_name, roster_id):
    return f"{slug(league_name)}-{rid(roster_id)}.json"


def current_team(index, league_id=None, league_name=None, roster=None):
    """(page league id, roster id) for a team seen in any season, or None when it has no page.
    A team still in the league resolves to this season's league ID; a defunct team (retired league or
    roster) to the league ID of its last season (index entries marked "defunct").
    league_id: any season's Sleeper ID (resolved through index['ids']); league_name wins when given."""
    name = norm_league(league_name) if league_name else index.get("ids", {}).get(str(league_id or ""), "")
    r = rid(roster)
    if not name or not r:
        return None
    leagues = sorted(index.get("leagues", {}).items(), key=lambda kv: bool(kv[1].get("defunct")))
    for lid, lg in leagues:  # current leagues first, then defunct ones
        if norm_league(lg.get("name")) == name and r in index.get("teams", {}).get(lid, {}):
            return (lid, r)
    return None


def matching_seasons(key, keys_by_year):
    """Years (newest first) in which a season key exists. keys_by_year: {year: set of season keys}."""
    return sorted((y for y, ks in keys_by_year.items() if key in ks), reverse=True)


def team_links(year):
    """{team name that season: [page league id, roster]} for every team of that season. Pages pass this to
    NCAATeamLink.wrap(). A team still in the league -> this season's league ID; a defunct team -> its
    last season's league ID (the same rule as current_team)."""
    lids = league_ids()
    lid_of = {(y, name): lid for lid, (y, name) in lids.items()}
    last = {}
    for y in sorted({y for y, _ in lids.values()}):
        n = tn.names(y)
        for lg, r in zip(n["LeagueName"], n["RosterID"]):
            if (y, norm_league(lg)) in lid_of:
                last[(norm_league(lg), rid(r))] = y
    n = tn.names(year)
    out = {}
    for lg, r, team in zip(n["LeagueName"], n["RosterID"], n["Team"]):
        k = (norm_league(lg), rid(r))
        lid = lid_of.get((last.get(k), k[0]))
        if lid:
            out[str(team).strip()] = [lid, k[1]]
    return out


# ---- Loading ------------------------------------------------------------------------------------
def read(paths, **kw):
    frames = [pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig", **kw)
              for p in ([paths] if isinstance(paths, str) else paths) if os.path.exists(p)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def league_ids():
    """{lid: (year, normalized name)} for every season on file."""
    out = {}
    for r in read(LEAGUE_FILES).itertuples():
        out[str(r.LeagueID)] = (int(r.Year), norm_league(r.LeagueName))
    return out


def num(v, default=0.0):
    try:
        x = float(v)
        return default if x != x else x
    except (TypeError, ValueError):
        return default


def player_names():
    """{player id: (name, position, nfl team)}: the current player file over the full history list."""
    out = {}
    if os.path.exists(PLAYER_NAMES):
        for r in read(PLAYER_NAMES).itertuples():
            out[str(r.PlayerID)] = (r.Name, r.Position, r.Team)
    if os.path.exists(PLAYERS):
        for r in read(PLAYERS).itertuples():
            nm = " ".join(x for x in (r.first_name, r.last_name) if x).strip()
            if nm:
                out[str(r.player_id)] = (nm, r.position, r.team)
    return out


def player_label(pid, names):
    pid = str(pid)
    n = names.get(pid)
    if n and n[0]:
        return n[0], (n[1] or ""), (n[2] or "")
    if pid.isalpha():  # team defenses use the NFL abbreviation as their ID
        return f"{pid} D/ST", "DEF", pid
    return f"Player {pid}", "", ""


def ordinal(n):
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def identity(name):
    """{name, bg, ink, logo} for a school name: team colours (standing rule) and the logo for that background."""
    c = tn.colors_row(name) or {}
    bg, ink = team_colors(c.get("Primary"), c.get("Secondary"), c.get("Background"), c.get("Text"), name=name)
    info = logo_info(name, prefix="../")
    return {"name": name, "bg": bg, "ink": ink, "logo": fixed_bg_src(info, bg) if info else ""}


# ---- Seasons ------------------------------------------------------------------------------------
def matchup_rows(paths=MATCHUP_FILES):
    """All regular-season matchup rows, on standard scores (standard_results.apply) with Sleeper's kept."""
    m = read(paths)
    if m.empty:
        return m
    m = standard_results.apply(m)
    m["Y"] = m["Year"].astype(int)
    m["W"] = m["Week"].astype(int)
    m["Key"] = [season_key(a, b) for a, b in zip(m["LeagueName"], m["RosterID"])]
    return m[m["IsRegularSeason"].astype(str) == "True"].copy()


def season_records(m, std_from):
    """{(year, key): {w,l,t,pf,pa,pf_official,pa_official,games}}. W/L/T: Sleeper's official result before
    std_from (results are never flipped), standard scoring from std_from. PF/PA: standard totals in every
    season (Chris, 5.20 review); Sleeper's official totals kept alongside (division ties before std_from)."""
    out = {}
    for r in m.itertuples():
        if r.Outcome not in standard_results.RESULTS:
            continue
        d = out.setdefault((r.Y, r.Key), {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0,
                                          "pf_official": 0.0, "pa_official": 0.0, "games": 0})
        d[{"Win": "w", "Loss": "l", "Tie": "t"}[r.Outcome]] += 1
        d["pf"] += num(r.PointsFor)
        d["pa"] += num(r.PointsAgainst)
        d["pf_official"] += num(r.PointsOfficial)
        d["pa_official"] += num(r.PointsAgainstOfficial)
        d["games"] += 1
    for (y, _), d in out.items():
        for k in ("pf", "pa", "pf_official", "pa_official"):
            d[k] = round(d[k], 2)
        d["std"] = y >= std_from
    return out


def division_places(records, divisions):
    """{(year, key): (place, size)} within league + division: wins (ties = half) then points for, exact
    ties share a place -- the standings.py rule, on the points that season's standings used (official
    before standard_from), so places match the Standings pages."""
    groups = {}
    for (y, key), d in records.items():
        div = divisions.get((y, key), {}).get("division", "")
        pf = d["pf"] if d.get("std", True) else d.get("pf_official", d["pf"])  # the standings that season used
        groups.setdefault((y, key.split("|")[0], div), []).append((y, key, (d["w"] + 0.5 * d["t"], round(pf, 2))))
    out = {}
    for teams in groups.values():
        vals = sorted((v for *_, v in teams), reverse=True)
        for y, key, v in teams:
            out[(y, key)] = (vals.index(v) + 1, len(teams))
    return out


def standings_rows(paths=STANDING_FILES):
    """{(year, key): {division, manager, owner_id}} from the standings files (that season's division and manager)."""
    out = {}
    for r in read(paths).itertuples():
        out[(int(r.Year), season_key(r.LeagueName, r.RosterID))] = {
            "division": str(r.DivisionName or "").strip().title(), "manager": r.OwnerName, "owner_id": r.OwnerID}
    return out


def week_game(r, year, std_from, names):
    """One regular-season week for the schedule list."""
    lg = r.LeagueName.strip()
    opp = rid(r.OpponentRosterID)
    played = r.Outcome in standard_results.RESULTS
    g = {"w": int(r.W), "kind": "reg", "opp": (tn.season_name(year, lg, opp) or f"Roster {opp}") if opp else "Bye",
         "opp_key": season_key(lg, opp) if opp else ""}
    if not played:
        return g
    pf, pa = round(num(r.PointsFor), 2), round(num(r.PointsAgainst), 2)
    of, oa = round(num(r.PointsOfficial), 2), round(num(r.PointsAgainstOfficial), 2)
    g.update({"pf": pf, "pa": pa, "res": r.Outcome[0]})
    if abs(pf - of) > 0.005 or abs(pa - oa) > 0.005:
        g["official"] = [of, oa]
        std_res = "W" if pf > pa else "L" if pf < pa else "T"
        off_res = r.OutcomeOfficial[0] if r.OutcomeOfficial in standard_results.RESULTS else ""
        if year < std_from and std_res != g["res"]:
            g["note"] = "Standard scoring would flip this game; Sleeper's result stands."
        elif year >= std_from and off_res and off_res != g["res"]:
            g["note"] = "Sleeper shows a different result; decided on standard scoring."
    return g


# ---- Postseason ---------------------------------------------------------------------------------
def postseason_games(years, short):
    """{(year, key): [game]} from data/postseason/<year>.json (finished seasons) and
    Postseason_Season.csv (this season). game: {w, kind:'post', event, label, opp, res, pf, pa, status}."""
    out = {}
    for y in years:
        f = os.path.join(POSTSEASON_DIR, f"{y}.json")
        if not os.path.exists(f):
            continue
        for g in json.load(open(f, encoding="utf-8")).get("games", []):
            label = post_label(g["event"], g.get("round", ""), g.get("bowl", ""), g.get("conference", ""), g.get("group", ""))
            for s in g["sides"]:
                if not s.get("league_name") or not rid(s.get("roster_id")):
                    continue
                others = [o for o in g["sides"] if o is not s]
                row = {"w": int(g["week"]), "kind": "post", "event": g["event"], "round": g.get("round", ""),
                       "label": label, "status": "Final", "pf": s.get("points"),
                       "opp": " / ".join(f'{o["team"]} ({o["league"]})' if o.get("league") else o["team"] for o in others)}
                if g.get("format") == "group":
                    row["pa"] = None
                    pts = sorted((o.get("points") or 0 for o in g["sides"]), reverse=True)
                    row["res"] = "W" if s.get("won") else "L"
                    row["place"] = pts.index(s.get("points") or 0) + 1 if s.get("points") is not None else None
                    row["size"] = len(g["sides"])
                else:
                    row["pa"] = others[0].get("points") if others else None
                    row["res"] = "W" if s.get("won") else "L"
                out.setdefault((y, season_key(s["league_name"], s["roster_id"])), []).append(row)
    if os.path.exists(POSTSEASON_SEASON):
        p = read(POSTSEASON_SEASON)
        for r in p.itertuples():
            ev = r.Round
            label = post_label(ev, r.PlayoffRound or r.Stage, r.BowlName, short.get(r.LeagueName.strip(), r.LeagueName) if ev == "CCG" else "", r.Stage if ev == "NIT" else "")
            opp_teams, opp_lgs = r.OpponentTeam.split("|"), r.OpponentLeague.split("|")
            opp = " / ".join(f"{t.strip()} ({short.get(l.strip(), l.strip())})" if l.strip() else t.strip()
                             for t, l in zip(opp_teams, opp_lgs + [""] * len(opp_teams)) if t.strip())
            final = r.Status == "Final" or r.Outcome in ("Win", "Loss", "Tie")
            row = {"w": int(r.Week), "kind": "post", "event": ev, "round": r.PlayoffRound or r.Stage, "label": label,
                   "opp": opp, "status": "Final" if final else (r.Status or "Pending")}
            if final:
                row["pf"] = num(r.Points, None)
                op = [num(x, None) for x in r.OpponentPoints.split("|")]
                row["pa"] = op[0] if len(op) == 1 else None
                row["res"] = (r.Outcome or "")[:1]
            out.setdefault((int(r.Year), season_key(r.LeagueName, r.RosterID)), []).append(row)
    for v in out.values():
        v.sort(key=lambda g: g["w"])
    return out


def post_label(event, rnd, bowl, conference, group):
    if event == "CCG":
        return f"{conference} Championship".strip() if conference else "Conference Championship"
    if event == "Bowl":
        return bowl or "Bowl"
    if event == "NIT":
        return f"NIT {rnd}".strip() + (f" · {group}" if group else "")
    if event == "Playoff":
        return f"Playoff · {rnd}".strip(" ·") if rnd else "Playoff"
    return " ".join(x for x in (event, rnd) if x)


def postseason_summary(games):
    """One line per season: 'Won ACC Championship · Lost in the Elite 8'. '' when there were no games."""
    parts = []
    for ev in ("CCG", "Playoff", "Bowl", "NIT"):
        gs = [g for g in games if g["event"] == ev]
        if not gs:
            continue
        last = gs[-1]
        if last.get("status") != "Final":
            parts.append(f"{last['label']}: {last.get('status', 'Pending').lower()}")
        elif ev == "CCG":
            parts.append(("Won " if last["res"] == "W" else "Lost ") + last["label"])
        elif ev == "Playoff":
            rnd = last.get("round", "")
            if rnd == "National Championship":
                parts.append("National champion" if last["res"] == "W" else "National runner-up")
            elif last["res"] == "W":
                parts.append(f"Playoff: won {rnd}")
            else:
                parts.append(f"Playoff: lost in {rnd}" if rnd else "Playoff: lost")
        elif ev == "Bowl":
            parts.append(("Won " if last["res"] == "W" else "Lost ") + last["label"])
        else:
            rnd = last.get("round", "")
            if rnd == "Final":
                parts.append("NIT champion" if last["res"] == "W" else "NIT runner-up")
            else:
                parts.append(f"NIT: {'advanced from' if last['res'] == 'W' else 'out in'} {rnd}".strip())
    return " · ".join(parts)


# ---- Trophies, drafts, transactions ---------------------------------------------------------------
def trophies(lids):
    """{key: [ledger rows]} newest first, matched by that season's league (ID -> name) + roster."""
    out = {}
    t = read(TROPHY_FILES)
    for r in t.to_dict("records"):
        lg = lids.get(str(r.get("LeagueID", "")))
        name = lg[1] if lg else norm_league(r.get("Conference", ""))
        out.setdefault(season_key(name, r["RosterID"]), []).append(
            {k: r.get(k, "") for k in ("Season", "EventType", "Event", "Round", "Team", "Conference", "ManagerName", "Status")})
    order = {"NationalTitle": 0, "PlayoffRound": 1, "CCG": 2, "NIT": 3, "Bowl": 4, "Guillotine": 5, "DwightFight": 6}
    for v in out.values():
        v.sort(key=lambda r: (-int(r["Season"] or 0), order.get(r["EventType"], 9), r["Event"]))
    return out


def drafts(cfg, names):
    """{key: [{year, label, picks: [...]}]} newest first. Sleeper's picks, plus Chris's sheets
    (DraftPicksManual_Historic.csv) for drafts Sleeper has no picks for."""
    d = read(DRAFT_FILES)
    meta = {r.DraftID: (int(r.Season), int(r.Rounds or 0), int(r.Teams or 12), r.Status, r.Type) for r in d.itertuples()}
    picks = {}
    have = set()  # (year, league) drafts with Sleeper picks
    for r in read(PICK_FILES).itertuples():
        m = meta.get(r.DraftID)
        if not m:
            continue
        y, rounds, teams, _, _ = m
        kind = "Startup draft" if rounds > cfg["startup_draft_min_rounds"] else "Rookie draft"
        lg = norm_league(r.LeagueName)
        have.add((y, lg, kind))
        nm = " ".join(x for x in (r.FirstName, r.LastName) if x).strip() or player_label(r.PlayerID, names)[0]
        pno = int(num(r.Pick_No))
        picks.setdefault((season_key(lg, r.RosterID), y, kind), []).append(
            {"round": int(num(r.Round)), "pick": (pno - 1) % teams + 1 if teams else pno, "overall": pno,
             "player": nm, "pos": r.Position, "nfl": r.Team})
    if os.path.exists(MANUAL_PICKS):
        for r in read(MANUAL_PICKS).itertuples():
            y, lg = int(r.Year), norm_league(r.LeagueName)
            if (y, lg, "Rookie draft") in have:
                continue
            extra = r.PickType if r.PickType and r.PickType != "Regular" else ""
            picks.setdefault((season_key(lg, r.RosterID), y, "Rookie draft"), []).append(
                {"round": int(num(r.Round)), "pick": int(num(r.PickInRound)), "overall": int(num(r.OverallPick)),
                 "player": r.Player, "pos": r.Position, "nfl": "", "note": extra, "source": "sheet"})
    out = {}
    for (key, y, kind), ps in picks.items():
        ps.sort(key=lambda p: (p["overall"], p["round"], p["pick"]))
        out.setdefault(key, []).append({"year": y, "label": kind, "picks": ps,
                                        "source": "sheet" if any(p.get("source") for p in ps) else "sleeper"})
    for v in out.values():
        v.sort(key=lambda b: (-b["year"], b["label"] != "Rookie draft"))
    return out


def lit(v, fallback):
    s = str(v or "").strip()
    if not s or s in ("nan", "None"):
        return fallback
    try:
        x = ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return fallback
    return fallback if x is None else x


def transactions(lids, names):
    """{key: [entry]} newest first. Trades are drawn with the Transactions page's own card
    (transactions_page.trade_card + its grades); other moves are add/drop rows."""
    import transactions_page as tp
    from trade_fit_store import FileArchive, FitLedger
    from transactions_fit import event_key
    from transactions_grades import evaluate_trade, load_config, read_rows

    rows = [r for p in TX_FILES if os.path.exists(p) for r in read_rows(p) if r.get("Status") == "complete"]
    players = {pid: {"first_name": n, "last_name": "", "position": pos} for pid, (n, pos, _) in names.items()}
    grading = load_config()
    ph, pk = read_rows(tp.PLAYER_VALUES), read_rows(tp.PICK_VALUES)
    fit_model, fit_archive = FitLedger(), FileArchive()
    short = lcfg.league_display()
    colors = {}
    name_cache = {}

    def season_names(year):
        if year not in name_cache:
            n = tn.names(year)
            name_cache[year] = {(lg.strip(), rid(r)): t for lg, r, t in zip(n["LeagueName"], n["RosterID"], n["Team"])}
        return name_cache[year]

    out = {}
    for r in rows:
        y = int(r["Year"])
        lg = r["LeagueName"].strip()
        adds, drops = lit(r.get("Adds"), {}), lit(r.get("Drops"), {})
        rids = {rid(x) for x in lit(r.get("RosterIDs"), [])}
        rids |= {rid(x) for x in list(adds.values()) + list(drops.values())}
        base = {"t": int(num(r["Created"])), "y": y, "wk": int(num(r["Week"])), "type": r["Type"]}
        if r["Type"] == "trade":
            nm = season_names(y)
            for x in set(nm.values()):
                if x not in colors:
                    c = tn.colors_row(x)
                    colors[x] = dict(c) if c is not None else {}
            sides = tp.trade_assets(r, nm, players)
            card = ""
            if len(sides) == 2:
                res = evaluate_trade(sides, tp.day(r["Created"]), ph, pk, y, grading)
                fit = fit_model.evaluate(r, sides)
                pending = (len(fit) < len(sides) and str(r["TransactionID"]).isdigit()
                           and fit_archive.pending(event_key(r)[0]))
                card = tp.trade_card(r, sides, nm, colors, res, short, grading, fit, pending)
            for side in sides:
                gets = [a["label"] for a in sides[side]]
                gives = [a["label"] for o, assets in sides.items() if o != side for a in assets]
                partners = [nm.get((lg, o), f"Roster {o}") for o in sides if o != side]
                e = dict(base, html=card) if card else dict(base, partners=partners, gets=gets, gives=gives)
                out.setdefault(season_key(lg, side), []).append(e)
            continue
        for side in rids:
            a = [player_label(p, names) for p, to in adds.items() if rid(to) == side]
            d = [player_label(p, names) for p, frm in drops.items() if rid(frm) == side]
            if not a and not d:
                continue
            out.setdefault(season_key(lg, side), []).append(
                dict(base, adds=[[x[0], x[1]] for x in a], drops=[[x[0], x[1]] for x in d]))
    for v in out.values():
        v.sort(key=lambda e: -e["t"])
    return out


# ---- Build --------------------------------------------------------------------------------------
def current_roster(league_name, roster, rosters, names, order):
    rows = rosters[(rosters["LeagueName"].map(norm_league) == norm_league(league_name)) & (rosters["RosterID"].map(rid) == rid(roster))]
    groups = {}
    for r in rows.itertuples():
        if not str(r.PlayerID).strip():
            continue
        nm, pos, nfl = (r.FullName, r.Position, r.Team) if r.FullName else player_label(r.PlayerID, names)
        pos = (pos or "").upper()
        pos = {"DST": "DEF", "D/ST": "DEF", "PK": "K", "FB": "RB"}.get(pos, pos)
        groups.setdefault(pos if pos in order else "Other", []).append({"name": nm, "nfl": nfl or "FA", "id": str(r.PlayerID)})
    for v in groups.values():
        v.sort(key=lambda p: p["name"])
    return [{"pos": p, "players": groups[p]} for p in order + ["Other"] if p in groups]


def build(out_dir=OUT_DIR, page=PAGE):
    cfg = settings()
    std_from = standard_results.standard_from()
    lids = league_ids()
    cur = max(y for y, _ in lids.values())
    short = lcfg.league_display()
    short_n = {norm_league(k): v for k, v in short.items()}
    teams = read("data/Teams.csv").rename(columns={"League": "LeagueName", "Roster ID": "RosterID"})
    cur_lid = {name: lid for lid, (y, name) in lids.items() if y == cur}

    names = player_names()
    m = matchup_rows()
    records = season_records(m, std_from)
    divs = standings_rows()
    places = division_places(records, divs)
    keys_by_year = {}
    for (y, key) in set(records) | set(divs):
        keys_by_year.setdefault(y, set()).add(key)
    weeks = {}
    for r in m.sort_values(["Y", "W"]).itertuples():
        weeks.setdefault((r.Y, r.Key), []).append(week_game(r, r.Y, std_from, names))
    post = postseason_games(sorted(keys_by_year), short)
    for (y, key) in post:
        keys_by_year.setdefault(y, set()).add(key)
    trophy_rows = trophies(lids)
    draft_rows = drafts(cfg, names)
    tx = transactions(lids, names)
    rosters = read(ROSTERS)
    overall = read(OVERALL)
    rank = {(norm_league(next((k for k, v in short.items() if v == r["League"]), r["League"])), r["Team"]): r
            for r in overall.to_dict("records")} if not overall.empty else {}

    index = {"season": cur, "leagues": {}, "ids": {lid: name for lid, (_, name) in sorted(lids.items())}, "teams": {}}
    os.makedirs(out_dir, exist_ok=True)
    written = set()

    # Who gets a page: every current team, plus every defunct team -- a roster (league name + roster ID)
    # seen in any season that isn't in the league now (retired leagues: 2019 American, 2020 Southland).
    specs = []
    for t in teams.to_dict("records"):
        lg = norm_league(t["LeagueName"])
        if not cur_lid.get(lg):
            print(f"WARNING: no {cur} league ID for {t['LeagueName']}; {t['Team']} skipped")
            continue
        specs.append({"league": t["LeagueName"].strip(), "roster": rid(t["RosterID"]), "name": t["Team"].strip(),
                      "lid": cur_lid[lg], "division": str(t.get("Division Name", "")).strip().title(), "defunct": False})
    current_keys = {season_key(x["league"], x["roster"]) for x in specs}
    seen = set().union(*keys_by_year.values()) | set(trophy_rows)
    lid_of = {(y, name): lid for lid, (y, name) in lids.items()}
    for key in sorted(seen - current_keys):
        lg, r = key.split("|")
        years = matching_seasons(key, keys_by_year)
        if not years or not r:
            continue
        last = years[0]
        lid = lid_of.get((last, lg))
        if not lid:
            print(f"WARNING: no {last} league ID for {lg}; defunct roster {r} skipped")
            continue
        specs.append({"league": lg, "roster": r, "name": tn.season_name(last, lg, r) or f"{lg} roster {r}",
                      "lid": lid, "division": divs.get((last, key), {}).get("division", ""), "defunct": True,
                      "first": years[-1], "last": last})

    for t in specs:
        lg, r, lid, name = norm_league(t["league"]), t["roster"], t["lid"], t["name"]
        key = season_key(lg, r)
        ident = identity(name)
        seasons = []
        for y in matching_seasons(key, keys_by_year):
            nm = tn.season_name(y, t["league"], r) or name
            rec = records.get((y, key))
            sd = divs.get((y, key), {})
            pl = places.get((y, key))
            games = weeks.get((y, key), []) + post.get((y, key), [])
            s = {"year": y, "name": nm, "manager": sd.get("manager", ""), "division": sd.get("division", ""),
                 "record": rec, "place": list(pl) if pl and rec else None,
                 "post": postseason_summary(post.get((y, key), [])), "games": games}
            if nm != name:
                s["identity"] = identity(nm)
            if y >= std_from:
                s["standard"] = True
            seasons.append(s)
        if t["defunct"]:
            last = seasons[0] if seasons else {}
            mgr = last.get("manager") or ""
            data_now = {"record": None, "place": None, "rank": None, "of": None, "roster_groups": [],
                        "defunct": {"first": t["first"], "last": t["last"]}}
        else:
            now = next((s for s in seasons if s["year"] == cur), None) or {}
            o = rank.get((lg, name), {})
            mgr = now.get("manager") or ""
            owner_rows = rosters[(rosters["LeagueName"].map(norm_league) == lg) & (rosters["RosterID"].map(rid) == r)]
            if len(owner_rows):
                mgr = owner_rows["OwnerName"].iloc[0] or mgr
            data_now = {"record": now.get("record"), "place": now.get("place"),
                        "rank": int(o["Playoff Rank"]) if o.get("Playoff Rank") else None, "of": len(overall) or None,
                        "roster_groups": current_roster(lg, r, rosters, names, cfg["position_order"])}
        data = {
            "key": key, "league_id": lid, "league": t["league"], "short": short_n.get(lg, t["league"]),
            "roster": r, "season": cur, **ident, "manager": mgr or "Orphan",
            "division": (seasons[0].get("division") if t["defunct"] and seasons else
                         next((s["division"] for s in seasons if s["year"] == cur), "")) or t["division"],
            **data_now,
            "former": [{"name": n, "from": a, "to": b} for n, a, b in tn.former_names(t["league"], r) if n != name],
            "trophies": trophy_rows.get(key, []),
            "seasons": seasons,
            "drafts": draft_rows.get(key, []),
            "transactions": tx.get(key, []),
            "settings": {"transactions_shown": cfg["transactions_shown"], "current_season_open": cfg["current_season_open"]},
        }
        f = team_file(lg, r)
        _write_json(os.path.join(out_dir, f), data)
        written.add(f)
        lg_row = {"name": t["league"], "short": short_n.get(lg, t["league"]), "slug": slug(lg)}
        if t["defunct"]:
            lg_row.update(defunct=True, last=t["last"])
        index["leagues"].setdefault(lid, lg_row)
        team_row = {"name": name, "manager": mgr or "Orphan", "file": f}
        if t["defunct"]:
            team_row.update(defunct=True, last=t["last"])
        index["teams"].setdefault(lid, {})[r] = team_row
    for old in glob.glob(os.path.join(out_dir, "*.json")):
        if os.path.basename(old) not in written and os.path.basename(old) != "index.json":
            os.remove(old)  # nothing left to show (no season, trophy, draft or transaction on file)
    index["leagues"] = dict(sorted(index["leagues"].items(), key=lambda kv: (bool(kv[1].get("defunct")), kv[1]["short"])))
    index["teams"] = {lid: dict(sorted(v.items(), key=lambda kv: int(kv[0]))) for lid, v in index["teams"].items()}
    _write_json(os.path.join(out_dir, "index.json"), index)
    write_page(page)
    print(f"Wrote {len(written)} team files to {out_dir}/ + index.json; {page}")
    return index


def _write_json(path, data):
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"
    p = Path(path)
    if not p.exists() or p.read_text(encoding="utf-8") != text:  # unchanged files keep their git state
        p.write_text(text, encoding="utf-8")


# ---- Page ---------------------------------------------------------------------------------------
CSS = """
.tm-head{display:flex;justify-content:flex-start;text-align:left;border-bottom:0;align-items:center;gap:14px;padding:16px;border-radius:12px;background:var(--team-bg);color:var(--team-ink);margin:8px 0 14px}
.tm-head>div{text-align:left}
.tm-head img{width:72px;height:72px;object-fit:contain;flex:none}
.tm-head h1{margin:0;font-size:clamp(24px,7vw,38px);line-height:1.05;color:inherit}
.tm-head .eyebrow{color:inherit;opacity:.85}
.tm-meta{display:flex;flex-wrap:wrap;gap:4px 14px;margin-top:6px;font-weight:700;font-size:14px}
.tm-meta span{white-space:nowrap}
.tm-former{font-size:12px;opacity:.85;margin-top:4px}
.tm-pick{display:grid;gap:14px}
.tm-pick h3{margin:6px 0}
.tm-pick ul{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:6px}
.tm-pick a{display:block;padding:8px 10px;border:1px solid var(--line);border-radius:8px;color:var(--ink);text-decoration:none;font-weight:600}
.tm-pick a small{display:block;color:var(--mute);font-weight:500}
.tm-roster{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.tm-roster h3{margin:0 0 4px;font-size:13px;letter-spacing:.06em}
.tm-roster ul{list-style:none;margin:0;padding:0}
.tm-roster li{display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid var(--line);font-size:14px}
.tm-roster li small{color:var(--mute);font-variant-numeric:tabular-nums}
.tm-trophies{display:flex;flex-wrap:wrap;gap:12px}
.tm-trophies article{border:1px solid var(--line);border-radius:10px;background:var(--panel);overflow:hidden;width:min(200px,calc(50% - 6px))}
.tm-trophies article>header{margin:0;padding:6px 8px;font-size:11px;font-weight:700;color:var(--mute);border-bottom:1px solid var(--line)}
.tm-trophies .trophy{--tw:200px;width:100%}
.tm-season{border:1px solid var(--line);border-radius:10px;margin:0 0 10px;background:var(--panel)}
.tm-season>summary{display:flex;flex-wrap:wrap;align-items:center;gap:4px 12px;padding:10px 12px;cursor:pointer;font-weight:700}
.tm-season>summary::-webkit-details-marker{display:none}
.tm-season>summary::before{content:"\\25B8";font-size:12px;opacity:.7}
.tm-season[open]>summary::before{content:"\\25BE"}
.tm-season .yr{font:800 18px var(--num,sans-serif)}
.tm-chip{display:inline-block;padding:2px 8px;border-radius:4px;background:var(--chip-bg,var(--bg));color:var(--chip-ink,var(--ink));font-weight:800}
.tm-season .sum{flex-basis:100%;font-weight:600;font-size:13px;color:var(--mute)}
.tm-season .body{padding:0 12px 12px}
.tm-games{width:100%;min-width:0;table-layout:fixed;border-collapse:collapse;font-size:13px}
.tm-games col.c-wk{width:40px}.tm-games col.c-sc{width:92px}.tm-games col.c-r{width:22px}
.tm-games td{white-space:normal;overflow-wrap:break-word;padding:5px 4px;border-bottom:1px solid var(--line);vertical-align:top}
.tm-games td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tm-games tr td.wk{white-space:nowrap;color:var(--mute);font-weight:700}
.tm-games small{display:block;color:var(--mute);font-size:11px}
.tm-games tr.post td{background:color-mix(in srgb,var(--panel) 92%,var(--ink))}
.tm-res{display:inline-block;min-width:18px;text-align:center;font-weight:800}
.tm-res.W{color:var(--good)}.tm-res.L{color:var(--bad)}.tm-res.T{color:var(--neutral)}
.tm-draft{margin:0 0 14px}
.tm-draft h3{margin:0 0 4px;font-size:15px}
.tm-draft ol{list-style:none;margin:0;padding:0}
.tm-draft li{display:flex;gap:10px;padding:5px 0;border-bottom:1px solid var(--line);font-size:14px}
.tm-draft li b{font-variant-numeric:tabular-nums;min-width:42px}
.tm-draft li small{color:var(--mute)}
.tm-tx{display:grid;gap:12px}
.tm-move{display:flex;flex-wrap:wrap;gap:4px 12px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--panel);font-size:13px}
.tm-move .when{flex-basis:100%;font-size:11px;font-weight:700;color:var(--mute);letter-spacing:.04em}
.tm-move .add::before{content:"+ ";color:var(--good);font-weight:800}
.tm-move .drop::before{content:"− ";color:var(--bad);font-weight:800}
.tm-more{font:700 13px var(--sans,sans-serif);padding:8px 14px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:inherit;cursor:pointer;margin-top:10px}
.tm-empty{color:var(--mute)}
.tm-err{padding:14px;border:1px solid var(--bad);border-radius:8px}
@media(max-width:520px){.tm-head{padding:12px;gap:10px}.tm-head>div{text-align:left}
.tm-head img{width:52px;height:52px}.tm-trophies article{width:calc(50% - 6px)}}
"""


def write_page(path=PAGE):
    import transactions_page as tp
    import trophies as TR
    css = CSS + TR.CSS + tp.CSS + tp.position_badge_css(lcfg.cfg().get("position_colors"))
    body = f"""
<div class="wrap">
{menu_html("team")}
<div id="tm-top"><header><div><div class="eyebrow">{html.escape(lcfg.brand())}</div><h1>Team</h1></div></header></div>
<p class="tm-err" id="tm-error" hidden></p>
<div id="tm-sections" hidden>
<section id="tm-roster-sec"><h2>Current roster</h2><div id="tm-roster"></div></section>
<section id="tm-trophy-sec"><h2>Trophies</h2><div id="tm-trophies"></div></section>
<section id="tm-season-sec" data-nosnap><h2>Season by season</h2><div id="tm-seasons"></div>
<p class="note" id="tm-season-note"></p></section>
<section id="tm-draft-sec"><h2>Draft history</h2><div id="tm-drafts"></div></section>
<section id="tm-tx-sec" data-nosnap><h2>Transactions</h2><div class="tm-tx" id="tm-tx"></div></section>
</div>
<section id="tm-picker" hidden><h2>Pick a team</h2><div class="tm-pick" id="tm-pick"></div></section>
</div>
<script src="assets/trophy.js"></script><script src="assets/team-link.js"></script><script src="assets/team.js"></script>
"""
    out = page_head(f"Team · {lcfg.brand()}", css) + body + "</body></html>\n"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not Path(path).exists() or Path(path).read_text(encoding="utf-8") != out:
        Path(path).write_text(out, encoding="utf-8")
    return SECTIONS_JS  # team.js loads these after the page is built (so every card gets its Save image button)


if __name__ == "__main__":
    build()
