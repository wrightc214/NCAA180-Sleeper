"""
dwight_page.py -- the Dwight Fight pages (Special Events -> Dwight Fight), drawn with the site's bracket
component (task 5.18; scripts/bracket.py, the same look as the Playoff bracket).

  reports/dwight-fight.html          this season: the bracket from data/scoreboard/<year>/dwight.json
                                     (dwight_fight.py), or before the draw the bracket shape from the
                                     current standings, marked "Projected"
  reports/dwight-fight-<year>.html   each past season from data/Dwight_Historic.csv

Season picker: the menu's "dwight-seasons" row (site_common.menu_rows), this season first.
Every team row: seed . logo . that season's name in that season's colours, then "username · role"
(league_roles.py + config postseason.dwight_fight roles / role_labels). Byes: a seed with a bye first
appears in round 2; the round-1 column holds only the games actually played.

Called by special_page.py (the weekly job runs it after dwight_fight.py). CWD = repo root.
"""
import csv
import html
import json
import os
import sys
import urllib.parse
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowl_projection as bp  # noqa: E402
import bracket as BK  # noqa: E402
import dwight_fight as dw  # noqa: E402
import league_config as lcfg  # noqa: E402
import league_roles as LR  # noqa: E402
import team_names as tn  # noqa: E402
import trophies as TR  # noqa: E402
from poll_page import colors  # noqa: E402
from site_common import logo_html, menu_html, page_head  # noqa: E402

e = html.escape
PAGE = "reports/dwight-fight.html"
SEASON_PAGE = "reports/dwight-fight-{}.html"
STANDINGS_HIST = "data/Standings_Historic.csv"
MATCHUPS_HIST = "data/Matchups_Historic.csv"
SCOREBOARD = "data/scoreboard"
NBSP = "\u00a0"
RECON_NOTE = "Reconstructed: field = that season's poll voters; the event was likely not held."


def conf():
    return lcfg.cfg()["postseason"].get("dwight_fight", {})


# ------------------------------------------------------------------ events (one shape for every season)
# event: {season, start_week, last_week, weeks: [per round], rounds: [[game]], entrants, status, note, warnings}
# game:  {a, b, score_a, score_b, winner, final, bye, game_id}; a / b / winner = entrant dict or None
# entrant: {seed, team, league, roster_id, username}

def _owner_lookup(year, week):
    """{(LeagueName, RosterID): Sleeper name} for a past season's event week (that week's manager), with the
    season's last regular-season owner as the fallback."""
    out = {}
    if os.path.exists(STANDINGS_HIST):
        h = pd.read_csv(STANDINGS_HIST, dtype=str, keep_default_na=False)
        for r in h[h["Year"] == str(year)].itertuples():
            out[(r.LeagueName.strip(), str(r.RosterID))] = r.OwnerName
    if os.path.exists(MATCHUPS_HIST):
        m = pd.read_csv(MATCHUPS_HIST, dtype=str, keep_default_na=False, usecols=["Year", "LeagueName", "Week", "RosterID", "OwnerName"])
        m = m[(m["Year"] == str(year)) & (m["Week"] == str(week))]
        for r in m.itertuples():
            if r.OwnerName and r.OwnerName != "Orphan":
                out[(r.LeagueName.strip(), str(r.RosterID))] = r.OwnerName
    return out


def history_rows(path=dw.HISTORY):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def history_event(year, rows):
    """A past season from Dwight_Historic.csv, laid into the event's fixed bracket (dwight_fight.slots).
    Raises ValueError when a recorded game doesn't fit the bracket (bad data must not draw a wrong bracket)."""
    rows = [r for r in rows if str(r["Season"]) == str(year)]
    seeds = {}
    for r in rows:
        for sd in "AB":
            seeds[int(r["Seed" + sd])] = r["Team" + sd].strip()
    if not rows:
        raise ValueError(f"no Dwight Fight games for {year}")
    size, _ = dw.dimensions(len(seeds))
    nr = size.bit_length() - 1
    week_of = {}
    for r in rows:
        week_of.setdefault(int(r["Round"]), int(r["Week"]))
    first = min(week_of.values()) - (min(week_of) - 1)
    weeks = [week_of.get(j + 1, first + j) for j in range(nr)]
    owners = _owner_lookup(year, weeks[0])
    ents = {}
    for s_, team in seeds.items():
        sl = tn.slot(year, team) or (None, None)
        lg = (sl[0] or "").strip()
        ents[s_] = {"seed": s_, "team": team, "league": lg, "roster_id": str(sl[1] or ""),
                    "username": owners.get((lg, str(sl[1] or "")), "")}
    left = {(int(r["Round"]), frozenset((int(r["SeedA"]), int(r["SeedB"])))): r for r in rows}

    def play(j, a, b):
        if a and b:
            r = left.pop((j + 1, frozenset((a["seed"], b["seed"]))), None)
            if r is None:
                raise ValueError(f"{year} round {j + 1}: no recorded game for seeds {a['seed']} v {b['seed']}")
            by = {int(r["SeedA"]): r["ScoreA"], int(r["SeedB"]): r["ScoreB"]}
            w = next((x for x in (a, b) if x["team"] == r["Winner"].strip()), None)
            num = lambda v: float(v) if str(v).strip() not in ("", "nan") else None  # noqa: E731
            return {"a": a, "b": b, "score_a": num(by[a["seed"]]), "score_b": num(by[b["seed"]]), "winner": w,
                    "final": w is not None, "bye": False}
        x = a or b
        return {"a": a, "b": b, "score_a": None, "score_b": None, "winner": x, "final": x is not None,
                "bye": j == 0 and x is not None}
    order = dw.slots(size)
    rounds = [[play(0, ents.get(order[2 * i]), ents.get(order[2 * i + 1])) for i in range(size // 2)]]
    for j in range(1, nr):
        prev = rounds[-1]
        rounds.append([play(j, prev[2 * i]["winner"], prev[2 * i + 1]["winner"]) if (prev[2 * i]["winner"] and prev[2 * i + 1]["winner"])
                       else {"a": prev[2 * i]["winner"], "b": prev[2 * i + 1]["winner"], "score_a": None, "score_b": None,
                             "winner": None, "final": False, "bye": False}
                       for i in range(len(prev) // 2)])
    if left:
        raise ValueError(f"{year}: recorded games that don't fit the bracket: {sorted((k[0], sorted(k[1])) for k in left)}")
    status = next((r["Status"] for r in rows if r.get("Status")), "")
    return {"season": int(year), "start_week": weeks[0], "last_week": weeks[-1], "weeks": weeks, "rounds": rounds,
            "entrants": list(ents.values()), "mode": "past", "warnings": [],
            "note": RECON_NOTE if status.startswith("Reconstructed") else ""}


def _from_json(b, mode):
    """An event from dwight_fight.py's JSON (initial / locked bracket)."""
    ent = lambda x: x and {"seed": int(x["seed"]), "team": x.get("team", ""), "league": str(x.get("league", "")).strip(),  # noqa: E731
                           "roster_id": str(x.get("roster_id", "")), "username": x.get("username", "")}
    rounds = []
    for j, rnd in enumerate(b["rounds"]):
        out = []
        for g in rnd:
            a, b_ = ent(g.get("a")), ent(g.get("b"))
            w = g.get("winner")
            win = next((x for x in (a, b_) if x and w and str(w.get("seed")) == str(x["seed"])), None)
            bye = j == 0 and bool(a) != bool(b_)
            out.append({"a": a, "b": b_, "score_a": g.get("score_a"), "score_b": g.get("score_b"),
                        "winner": win if (g.get("frozen") or bye) else None, "final": bool(g.get("frozen")) or bye,
                        "bye": bye, "game_id": g.get("game_id") or ""})
        rounds.append(out)
    weeks = [int(b["start_week"]) + j for j in range(len(rounds))]
    return {"season": int(b["season"]), "start_week": int(b["start_week"]), "last_week": int(b["last_week"]), "weeks": weeks,
            "rounds": rounds, "entrants": [ent(x) for x in b.get("entrants", [])], "mode": mode,
            "warnings": list(b.get("warnings") or []), "note": "", "locked": bool(b.get("locked"))}


def projected_event(year, requested=None):
    """Before the draw: this season's Dwights (config dwights, matched to their teams through the season
    standings, case-insensitive) seeded by today's standings with dwight_fight.py's own rules.
    Returns (event or None, [warnings])."""
    requested = dw.names(conf().get("dwights", "")) if requested is None else requested
    if len(requested) < 2:
        return None, []
    s = pd.read_csv("data/Standings_Season.csv", dtype=str, keep_default_na=False)
    s = s[(s["Year"] == str(year)) & (s["OwnerID"] != "Orphan")]
    people, missing = [], []
    for h in requested:
        m = s[s["OwnerName"].str.casefold() == h]
        if not len(m):
            missing.append(h)
            continue
        r = m.iloc[0]
        lg = r["LeagueName"].strip()
        people.append({"user_id": r["OwnerID"], "username": r["OwnerName"], "display_name": r["OwnerName"],
                       "league_id": r["LeagueID"], "roster_id": str(r["RosterID"]), "league": lg,
                       "team": tn.season_name(year, lg, r["RosterID"]) or lg})
    warn = [f"Not matched to a team yet: {', '.join(missing)}"] if missing else []
    if len(people) < 2:
        return None, warn
    b = dw.draw(people, dw.rank_entrants(people, year), last=int(conf().get("last_week", dw.FINAL_WEEK)), season=year)
    ev = _from_json(b, "projected")
    ev["warnings"] = warn
    return ev, warn


def current_event(year, root=SCOREBOARD):
    """(event or None, warnings) for this season: the drawn bracket when dwight.json has one, else the
    projection from the standings (also shown, with the resolution warnings, while the draw is pending)."""
    p = Path(root) / str(year) / "dwight.json"
    b = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    if b and b.get("rounds"):
        return _from_json(b, "drawn"), list(b.get("warnings") or [])
    ev, warn = projected_event(year)
    extra = list((b or {}).get("warnings") or [])
    if ev:
        ev["warnings"] = extra + warn
    return ev, extra + warn


# ------------------------------------------------------------------ roles (second line)
def role_labels():
    d = {"league_manager": "Commissioner", "data_contact": "Data Manager", "assistant": "{conference} Assistant",
         "default_current": "Legacy Voter", "default_past": "Poll Voter", "orphan": "Orphan"}
    d.update({k: v for k, v in (conf().get("role_labels") or {}).items() if not k.startswith("_")})
    return d


def make_role(current, R=None, short=None):
    """role(username) -> label: official role (league_roles.py, highest wins), then config roles, then
    the season default (default_current this season, default_past before)."""
    R = LR.roles() if R is None else R
    short = {v: k for k, v in ps.league_short().items()} if short is None else short
    L = role_labels()
    manual = {str(k).strip().casefold(): v for k, v in (conf().get("roles") or {}).items() if not str(k).startswith("_")}

    def role(username):
        k = str(username or "").strip().casefold()
        if k in R:
            r, lg = R[k]
            return L[r].replace("{conference}", short.get(lg, lg))
        if k in manual:
            return manual[k]
        return L["default_current" if current else "default_past"]
    return role


def second_line(ent, role):
    u = str(ent.get("username") or "").strip()
    if not u or u == "Orphan" or "orphan #" in u.casefold():  # an orphaned roster has no manager to name
        return role_labels()["orphan"]
    return f"{u} · {role(u).replace(' ', NBSP)}"  # a narrow phone row wraps after the "·", never inside the role


# ------------------------------------------------------------------ bracket
def _rel(p):
    return "../" + urllib.parse.quote(p) if p else ""


def bracket_model(ev, current, col=None, role=None, now_label=None):
    """bracket.py model for an event."""
    c = conf()
    col = colors() if col is None else col
    role = role or make_role(current)
    names = {}
    for x in ev["entrants"]:
        if x:
            names[x["team"]] = x

    def T(x, score, win):
        return {"Team": x["team"], "Seed": x["seed"], "Points": score, "Win": win}
    R = []
    for j, rnd in enumerate(ev["rounds"]):
        out = []
        for g in rnd:
            a, b = g["a"], g["b"]
            if g["bye"]:
                out.append({"bye": True, "final": True, "teams": [T(a or b, None, True)]})
            elif a and b:
                w = g["winner"]
                out.append({"teams": [T(a, g["score_a"], bool(w and w["seed"] == a["seed"])),
                                      T(b, g["score_b"], bool(w and w["seed"] == b["seed"]))],
                            "final": bool(g["final"] and w), "id": g.get("game_id") or "", "year": ev["season"],
                            "week": ev["weeks"][j]})
            else:
                out.append(None)
        R.append(out)

    def side(t):
        x = names.get(t["Team"], {"username": ""})
        bg, fg = col.get(t["Team"], ("#14213a", "#ffffff"))
        return {"name": t["Team"], "seed": t.get("Seed", ""), "conf": second_line(x, role), "sub_cls": "bk-case",
                "bg": bg, "fg": fg, "logo": logo_html(t["Team"], bg=bg)}

    def href(g):  # same Scoreboard game view as the Playoff, only when the game has a GameID
        return f"scoreboard.html?season={g['year']}&week={g['week']}&post={g['id']}" if g.get("id") else None
    total = len(R)
    label = {"projected": c.get("projected_label", "Projected: draws after the regular season"),
             "drawn": c.get("live_label", "Unofficial")}.get(ev["mode"], "")
    if now_label is not None:
        label = now_label
    y = ev["season"]
    B = BK.model(R, year=y, title=c.get("name", "Dwight Fight"),
                 eyebrow=f"{lcfg.brand()} · Special Events · {y} · Weeks {ev['weeks'][0]}–{ev['weeks'][-1]}",
                 round_names=[dw.round_name(j, total) for j in range(total)], weeks=ev["weeks"], side=side, href=href,
                 champion_title=f"{y} {c.get('name', 'Dwight Fight')} Champion", slug_name="dwight-fight",
                 row_width=int(c.get("row_width", 340)), logo=_rel((c.get("logos") or {}).get("mark", "")),
                 status_label=label, export_name=c.get("name", "Dwight Fight"), champ_file="dwight-fight-champion",
                 final_label="")
    if B["champion"]:  # engraved Dwight Fight trophy (task 5.1): the ledger row, else this file's final
        L = TR.ledger()
        rows = L[(L["EventType"] == "DwightFight") & (L["Season"].astype(str) == str(y))].to_dict("records")
        row = next((r for r in rows if r["Team"] == B["champion"]["name"]), None) or \
            {"EventType": "DwightFight", "Event": "Dwight Fight", "Round": "", "Team": B["champion"]["name"], "Season": y}
        d = TR.cfg()["display"]
        B["champion"]["trophy_html"] = TR.trophy_html(row, width=d["champion"], lazy=False)
        B["champion"]["trophy_html_big"] = TR.trophy_html(row, width=d["export"], lazy=False)
    return B


def dim():
    d = lcfg.cfg()["postseason"]["display"].get("bracket", {})
    return float(d.get("loser_opacity", 0.35)), float(d.get("loser_grayscale", 0.6))


# ------------------------------------------------------------------ page
CSS = bp.CSS + BK.CSS + BK.CSS_EXT + TR.CSS + """
.dw-wrap{max-width:1200px;min-width:0}
.dw-hdr{display:block;padding-bottom:10px;border-bottom:3px solid var(--accent);margin-bottom:6px}
.dw-title{margin:8px 0 0;line-height:0}.dw-title img{display:block;width:100%;max-width:640px;height:auto}
#dw-status{margin:4px 0 0;font:600 14px var(--body)}
.dw-note{font-size:13px;color:var(--mute);margin:2px 0 0}
.dw-warn{border:1px solid var(--bad);border-radius:6px;padding:10px;color:var(--bad)}
.dw-champs,.dw-totals{display:flex;flex-wrap:wrap;gap:6px}
.dw-champs>div,.dw-totals>div{padding:7px 10px;border:1px solid var(--line);border-radius:5px;background:var(--panel);font-size:13px}
.dw-reconstructed{color:var(--accent);font-weight:800;margin-left:1px}
.bk-champ .trophy{width:min(var(--tw),100%)}
"""


def champions_card(hist_events, cur=None):
    """Past champions + title totals (2019 / 2020 from the old Dwight Fight page; reconstructed seasons marked)."""
    wins = [{"year": y, "team": t, "recon": False} for y, t in sorted(TR.DWIGHT_PRE_BRACKET.items())]
    wins.append({"year": 2020, "display": "Finalist: Penn · champion unknown"})
    for ev in sorted(hist_events, key=lambda x: x["season"]):
        w = ev["rounds"][-1][0]["winner"]
        if w:
            wins.append({"year": ev["season"], "team": w["team"], "recon": bool(ev["note"])})
    if cur and cur["rounds"][-1][0]["winner"] and cur["rounds"][-1][0]["final"]:
        wins.append({"year": cur["season"], "team": cur["rounds"][-1][0]["winner"]["team"], "recon": False})
    wins.sort(key=lambda w: w["year"])
    mark = lambda w: '<sup class="dw-reconstructed" aria-label="reconstructed">*</sup>' if w.get("recon") else ""  # noqa: E731
    tot = {}
    for w in wins:
        if w.get("team"):
            tot.setdefault(w["team"], []).append(w)
    h = '<div class="dw-champs">' + "".join(f'<div><b>{w["year"]}</b> {e(w.get("team") or w.get("display", ""))}{mark(w)}</div>' for w in wins) + "</div>"
    h += '<h3>Title totals</h3><div class="dw-totals">' + "".join(
        f'<div><b>{e(t)} {len(ws)}</b> ({", ".join(str(w["year"]) + mark(w) for w in ws)})</div>'
        for t, ws in sorted(tot.items(), key=lambda kv: (-len(kv[1]), kv[0]))) + "</div>"
    if any(w.get("recon") for w in wins):
        h += '<p class="dw-note">* Reconstructed bracket; managers may not have set lineups for this event.</p>'
    return f'<section class="card" id="champions"><h2>Past champions</h2>{h}</section>'


def status_line(ev, n_req=0):
    if ev is None:
        return "Bracket pending · " + ("first draw follows the final regular-season week" if n_req >= 2 else
                                      "the field hasn't been set yet")
    n = len([x for x in ev["entrants"] if x])
    head = {"projected": conf().get("projected_label", "Projected: draws after the regular season"),
            "past": "Final" if ev["rounds"][-1][0]["final"] else f"{ev['season']}"}.get(
        ev["mode"], "Locked bracket" if ev.get("locked") else "Initial bracket")
    return f"{head} · {n} Dwights · Weeks {ev['weeks'][0]}–{ev['weeks'][-1]}"


def build_page(year, ev, warnings, hist_events, current, n_req=0):
    c = conf()
    brand = lcfg.brand()
    name = c.get("name", "Dwight Fight")
    banner = (c.get("logos") or {}).get("banner", "")
    title = (f'<img id="dw-banner" src="{e(_rel(banner))}" alt="{e(name)}">' if banner else e(name))
    secs = []
    if warnings:
        secs.append('<aside class="dw-warn" role="note"><strong>Resolution warning — bracket not locked.</strong><p>'
                    + "<br>".join(e(w) for w in warnings) + "</p></aside>")
    if ev:
        B = bracket_model(ev, current)
        secs.append(f'<section class="card" id="bracket"><h2>Bracket <small>{e(str(year))}</small></h2>{BK.html_(B, dim())}</section>')
    else:
        secs.append(f'<section class="card" id="bracket"><h2>Bracket <small>{e(str(year))}</small></h2>'
                    f'<p class="dw-note">{"The field needs at least two Dwights before a bracket can be drawn." if n_req < 2 else "The bracket appears once the Dwights are matched to their teams."}</p></section>')
    secs.append(champions_card(hist_events, ev if (current and ev and ev["mode"] == "drawn") else None))
    note = f'<p class="dw-note" id="dw-season-note">{e(ev["note"])}</p>' if (ev and ev.get("note")) else ""
    foot = f"{brand} · {year} {name}"
    return (page_head(f"{brand} {name} {year}", CSS)
            + f'<div class="wrap dw-wrap">{menu_html("special", ["special", "dwight-seasons"])}'
            + f'<header class="sbh dw-hdr"><div class="eyebrow">{e(brand)} · special events · {year} season</div>'
            + f'<h1 class="dw-title">{title}</h1><p id="dw-status" role="status">{e(status_line(ev, n_req))}</p>{note}</header>'
            + "".join(secs)
            + bp.FOLD_JS + bp.snap_js(0, foot=foot, tag=str(year), projection=False)
            + '<script src="assets/trophy.js"></script><script>window.NCAATrophy&&NCAATrophy.load("../").catch(()=>{})</script>'
            + "</div></body></html>")


def history_seasons(rows, current):
    return sorted({int(r["Season"]) for r in rows if str(r["Season"]).isdigit() and int(r["Season"]) < current}, reverse=True)


def main():
    os.chdir(lcfg.ROOT)
    cur = ps.current_season()
    rows = history_rows()
    hist = [history_event(y, rows) for y in history_seasons(rows, cur)]
    for ev in hist:
        with open(SEASON_PAGE.format(ev["season"]), "w", encoding="utf-8") as f:
            f.write(build_page(ev["season"], ev, [], hist, current=False))
    ev, warn = current_event(cur)
    n_req = len(dw.names(conf().get("dwights", "")))
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(build_page(cur, ev, warn, hist, current=True, n_req=n_req))
    print(f"wrote {PAGE} ({cur}) + {', '.join(SEASON_PAGE.format(e_['season']) for e_ in hist)}")


if __name__ == "__main__":
    main()
