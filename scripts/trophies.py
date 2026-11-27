"""
trophies.py -- the trophy ledger and the shared trophy component (task 5.1).

One list of trophies, images drawn on demand (CW): every trophy ever won is ONE ROW; the picture is
the shared art (assets/trophies/..., config/trophies.json) with the plaque engraved from that row at
view time. Adding history or a new event adds rows, never image files.

Ledger (repo's usual _Historic / _Season split), same columns in both:
  data/Trophies_Historic.csv  finished seasons, FROZEN. Built once by --backfill; the weekly job never
                              writes it. Corrections = a hand edit in a reviewed PR.
  data/Trophies_Season.csv    the current season, rebuilt from source on every run (weekly job and right
                              after each postseason publish step).
Safety check: once a season row exists it may not disappear or change its winner on a later run unless
--allow-changes is passed. Otherwise the old file is kept, this step exits 1 listing the differences,
and the rest of the run carries on (the workflow records the failure). Additions always pass.

Component:
  trophy_html(event, winner, year, line2=None, ...)  -> <figure> with the art + HTML-text plaque
  engraving(row)                                     -> text, box and fitted sizes (JS twin: reports/assets/trophy.js)
  engrave_png(row) -> PIL.Image                      -> built in memory on request; never writes a file

CLI (CWD = repo root):
  python scripts/trophies.py                    rebuild data/Trophies_Season.csv (weekly + after publish steps)
  python scripts/trophies.py --allow-changes    same, accepting changed/dropped rows (after a reviewed correction)
  python scripts/trophies.py --backfill         one-time: write data/Trophies_Historic.csv (refuses to overwrite)
  python scripts/trophies.py --rollover YEAR    append YEAR's season rows to the historic file + clear the season
                                                file (for the year-end closing scripts; historic changes go via PR)
  python scripts/trophies.py --metrics          regenerate assets/fonts/barlow-trophy-metrics.json
  python scripts/trophies.py --check            every ledger row's art resolves (or falls back); counts
"""
import argparse
import html
import json
import math
import os
import re
import sys
import urllib.parse

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import team_names as tn  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = "config/trophies.json"
LEAGUE_CONFIG = "config/league.json"
METRICS = "assets/fonts/barlow-trophy-metrics.json"
FONTS = {"700": "assets/fonts/barlow-latin-700-normal.woff", "400": "assets/fonts/barlow-latin-400-normal.woff"}
HIST = "data/Trophies_Historic.csv"
SEASON = "data/Trophies_Season.csv"
POST_HIST = "data/Postseason_Historic.csv"
POST_SEASON = "data/Postseason_Season.csv"
DWIGHT_HIST = "data/Dwight_Historic.csv"
LEAGUES = ["data/LeagueIDs_AllYears.csv", "data/backfill/LeagueIDs_2019_2020.csv"]
MATCHUPS = ["data/Matchups_Historic.csv", "data/backfill/Matchups_2019_2020.csv", "data/Matchups_Season.csv"]
SHORTNAMES = "data/LeagueShortNames.csv"
SCOREBOARD = "data/scoreboard"

COLUMNS = ["Season", "EventType", "Event", "Round", "Team", "Conference", "LeagueID", "RosterID",
           "ManagerUserID", "ManagerName", "ArtKey", "Status", "Source"]
KEY = ["Season", "EventType", "Event", "Round"]          # one trophy (co-champions share a key)
WINNER = ["Team", "LeagueID", "RosterID"]                 # who holds it
ORDER = ["CCG", "Bowl", "PlayoffRound", "NationalTitle", "NIT", "Guillotine", "DwightFight"]
# Dwight Fight 2019: listed as champion on the Dwight Fight page (no bracket recorded; 2020 unknown).
DWIGHT_PRE_BRACKET = {2019: "Penn"}

LINE_HEIGHT = 1.15
LETTER_SPACING = -0.02  # em, the Dwight Fight engraving's tracking
SAFETY = 1.03           # widths are unkerned sums, then 3% more: always wider than the browser draws

e = html.escape
_cache = {}


def _path(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


# ------------------------------------------------------------------ config
def cfg():
    if "cfg" not in _cache:
        c = json.load(open(_path(CONFIG), encoding="utf-8"))
        lg = json.load(open(_path(LEAGUE_CONFIG), encoding="utf-8"))
        hist = {k: v for k, v in lg["postseason"]["bowls"].get("history_names", {}).items() if not k.startswith("_")}
        c["_bowl_art"] = {**hist, **{k: v for k, v in c.get("bowl_art", {}).items() if not k.startswith("_")}}
        c["_approved"] = set(lg["postseason"]["bowls"].get("approved_logos", []))
        _cache["cfg"] = c
    return _cache["cfg"]


def metrics():
    if "m" not in _cache:
        _cache["m"] = json.load(open(_path(METRICS), encoding="utf-8"))
    return _cache["m"]


def build_metrics():
    """Advance widths (em) from the vendored woff files (PIL), for Python and the JS twin alike."""
    from PIL import ImageFont
    chars = [chr(c) for c in range(32, 127)] + list("·–—’‘“”éèáàíóúñüÉ")
    out = {"_note": "Advance widths (em) of the vendored Barlow woff files, generated by scripts/trophies.py --metrics. "
                    "Python and reports/assets/trophy.js size plaque text from this one table so they agree exactly; "
                    "kerning is ignored (always wider = never overflows).", "fallback": 0.88}
    for w, f in FONTS.items():
        font = ImageFont.truetype(_path(f), 1000)
        out[w] = {ch: round(font.getlength(ch) / 1000, 4) for ch in chars}
    with open(_path(METRICS), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=0)
    _cache.pop("m", None)
    return out


# ------------------------------------------------------------------ engraving model (mirrored in trophy.js)
def _fmt(tpl, d):
    return re.sub(r"\{(\w+)\}", lambda m: str(d.get(m.group(1), "")), tpl).strip()


def _row(event, winner=None, year=None):
    """Accept a ledger row, or an event dict/EventType string plus winner and year."""
    r = dict(event) if isinstance(event, dict) else {"EventType": str(event)}
    if winner is not None:
        r["Team"] = winner
    if year is not None:
        r["Season"] = year
    return r


def fields(row):
    """Placeholder values for a row: {year} {team} {conference} {round} {event} (engraved name) {art}."""
    c = cfg()
    ev = str(row.get("Event", "") or "")
    return {"year": str(row.get("Season", "") or ""), "team": str(row.get("Team", "") or ""),
            "conference": str(row.get("Conference", "") or ""), "round": str(row.get("Round", "") or ""),
            "event": c.get("bowl_labels", {}).get(ev, ev),
            "art": c["_bowl_art"].get(ev, ev)}


def event_cfg(row):
    ev = cfg()["events"].get(str(row.get("EventType", "")))
    if not ev or not isinstance(ev, dict):
        raise KeyError(f"No config/trophies.json events entry for EventType {row.get('EventType')!r}")
    return ev


def art_key(row):
    return _fmt(event_cfg(row)["art"], fields(row))


def generic_key(row):
    return _fmt(event_cfg(row).get("generic", ""), fields(row))


def resolved_art(row):
    """The file actually drawn: the event's own art, else its generic stand-in, else '' (fallback block)."""
    for p in (art_key(row), generic_key(row)):
        if p and os.path.exists(_path(p)):
            return p
    return ""


def geometry(art):
    """Plaque box for an art file: the default plaque with any per-file override."""
    c = cfg()
    g = {k: v for k, v in c["plaque"].items() if not k.startswith("_")}
    g.update({k: v for k, v in c.get("overrides", {}).get(art, {}).items() if not k.startswith("_")})
    return g


def text_em(text, weight):
    m = metrics()
    t = m[weight]
    fb = m["fallback"]
    n = len(text)
    return (sum(t.get(ch, fb) for ch in text) + LETTER_SPACING * max(n, 0)) * SAFETY


def _floor(x, nd=4):
    return math.floor(x * 10 ** nd) / 10 ** nd


FALLBACK_BOX = {"left": 0, "top": 0, "width": 100, "height": 25}  # missing art: a plain 4:1 plaque, full width


def engraving(event, winner=None, year=None, line2=None, fallback=False):
    """Everything both renderers need: lines, box (% of the art) and fitted font sizes
    (% of the art width, i.e. cqw). Font sizes only shrink from the box maxima; never truncated.
    fallback=True: sizes for the plain plaque block shown when the art file is missing."""
    row = _row(event, winner, year)
    f = fields(row)
    ev = event_cfg(row)
    art = art_key(row)
    g = geometry(art)
    S = float(g["size"])
    box = dict(FALLBACK_BOX) if fallback else {
        "left": _floor(g["x"] / S * 100, 2), "top": _floor(g["y"] / S * 100, 2),
        "width": _floor(g["w"] / S * 100, 2), "height": _floor(g["h"] / S * 100, 2)}
    l1 = f["team"]
    l2 = line2 if line2 is not None else _fmt(ev["line2"], f)
    shown2 = l2.upper() if g.get("uppercase_line2") else l2
    avail = box["width"] * (1 - 2 * float(g["padding"]))
    s1 = min(box["height"] * float(g["line1_max"]), avail / max(text_em(l1, "700"), 1e-6))
    s2 = min(box["height"] * float(g["line2_max"]), avail / max(text_em(shown2, "400"), 1e-6))
    return {"art": art, "fallback": fallback, "line1": l1, "line2": l2, "upper2": bool(g.get("uppercase_line2")), "box": box,
            "size1": _floor(s1, 3), "size2": _floor(s2, 3), "color": g["text_color"],
            "alt": _fmt(ev.get("alt", "{year} {event} trophy, won by {team}"), f),
            "name": _fmt(ev.get("name", "{event}"), f), "logo": _fmt(ev.get("logo", ""), f)}


def logo_for(en):
    """Fallback logo path or '' (bowl logos: CW's approved list only)."""
    p = en["logo"]
    if not p or not os.path.exists(_path(p)):
        return ""
    folder = os.path.basename(os.path.dirname(p))
    if folder in ("Bowls", "Playoffs") and os.path.splitext(os.path.basename(p))[0] not in cfg()["_approved"]:
        return ""
    return p


CSS = """
@font-face{font-family:"Barlow Trophy";font-weight:700;font-display:block;src:url("../assets/fonts/barlow-latin-700-normal.woff2") format("woff2"),url("../assets/fonts/barlow-latin-700-normal.woff") format("woff")}
@font-face{font-family:"Barlow Trophy";font-weight:400;font-display:block;src:url("../assets/fonts/barlow-latin-400-normal.woff2") format("woff2"),url("../assets/fonts/barlow-latin-400-normal.woff") format("woff")}
.trophy{margin:0;width:min(var(--tw,180px),100%);flex:none}
.trophy-art{position:relative;container-type:inline-size;line-height:0}
.trophy-art>img{display:block;width:100%;height:auto;aspect-ratio:1}
.trophy-plaque{position:absolute;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;overflow:hidden;font-family:"Barlow Trophy","Barlow",sans-serif;letter-spacing:-.02em;line-height:1.15;white-space:nowrap}
.trophy-plaque span{display:block;max-width:100%}
.trophy-plaque .tp-1{font-weight:700;color:inherit}.trophy-plaque .tp-2{font-weight:400;color:inherit}
.trophy-plaque .tp-up{text-transform:uppercase}
.trophy.fallback .trophy-art{aspect-ratio:auto;display:flex;flex-direction:column;align-items:center;gap:6%;padding:6% 4%;box-sizing:border-box;border:1px solid var(--line,#d5dbe5);border-radius:10px;background:var(--panel,#fff)}
.trophy.fallback .trophy-art>img{width:46%;aspect-ratio:1;object-fit:contain}
.trophy.fallback .trophy-plaque{position:relative;inset:auto;width:100%;aspect-ratio:4/1;background:#CFD4D8;border:2px solid #222934;border-radius:4px;box-sizing:border-box}
"""


def trophy_html(event, winner=None, year=None, line2=None, *, width=None, prefix="../", cls="", lazy=True, alt=None):
    """The shared trophy card. event: a ledger row, or an EventType/event dict plus winner + year.
    The plaque is HTML text over the art (percentages of the image), sized in cqw so it stays crisp at
    any width and in Save image. Missing art -> the event's logo + the same two lines on a plain plaque."""
    en = engraving(event, winner, year, line2)
    drawn = resolved_art(_row(event, winner, year))
    if not drawn:
        en = engraving(event, winner, year, line2, fallback=True)
    w = width or cfg()["display"]["list"]
    url = lambda p: e(prefix + urllib.parse.quote(p))  # noqa: E731
    t1 = f'<span class="tp-1" style="font-size:{en["size1"]}cqw">{e(en["line1"])}</span>'
    t2 = f'<span class="tp-2{" tp-up" if en["upper2"] else ""}" style="font-size:{en["size2"]}cqw">{e(en["line2"])}</span>'
    load = ' loading="lazy" decoding="async"' if lazy else ""
    a = e(alt or en["alt"])
    if drawn:  # own art or the generic stand-in (same shared base, same plaque)
        b = en["box"]
        pos = f'left:{b["left"]}%;top:{b["top"]}%;width:{b["width"]}%;height:{b["height"]}%;color:{en["color"]}'
        return (f'<figure class="trophy {cls}" style="--tw:{w}px" data-art="{e(en["art"])}">'
                f'<div class="trophy-art"><img src="{url(drawn)}" alt="{a}" width="{w}" height="{w}"{load}>'
                f'<div class="trophy-plaque" style="{pos}">{t1}{t2}</div></div></figure>')
    lg = logo_for(en)
    img = f'<img src="{url(lg)}" alt=""{load}>' if lg else ""
    return (f'<figure class="trophy fallback {cls}" style="--tw:{w}px" data-art="{e(en["art"])}" role="img" aria-label="{a}">'
            f'<div class="trophy-art">{img}<div class="trophy-plaque" style="color:{en["color"]}">'
            f'{t1}{t2}</div></div></figure>')


def engrave_png(row, width=None):
    """PIL image of the engraved trophy, built in memory from a ledger row (same geometry + fit rules).
    Never writes a file. Missing art -> a plain plaque-style image with the two lines."""
    from PIL import Image, ImageDraw, ImageFont
    en = engraving(row)
    drawn = resolved_art(row)
    if drawn:
        im = Image.open(_path(drawn)).convert("RGBA")
    else:  # same plain plaque as the page's fallback block
        en = engraving(row, fallback=True)
        im = Image.new("RGBA", (1200, 300), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, 1199, 299), 16, fill=(0xCF, 0xD4, 0xD8, 255), outline=(0x22, 0x29, 0x34, 255), width=6)
    W = im.size[0]
    b = en["box"]  # percentages of the width (and of the height for the art's own box)
    H = im.size[1] if not en.get("fallback") else W
    bx, by, bw, bh = b["left"] * W / 100, b["top"] * H / 100, b["width"] * W / 100, b["height"] * H / 100
    d = ImageDraw.Draw(im)
    lines = [(en["line1"], en["size1"] * W / 100, "700"),
             (en["line2"].upper() if en["upper2"] else en["line2"], en["size2"] * W / 100, "400")]
    total = sum(px * LINE_HEIGHT for _, px, _ in lines)
    y = by + (bh - total) / 2
    for text, px, wt in lines:
        font = ImageFont.truetype(_path(FONTS[wt]), max(1, int(px)))
        track = LETTER_SPACING * px
        tw = sum(font.getlength(ch) for ch in text) + track * len(text)
        x = bx + (bw - tw) / 2
        ty = y + (px * LINE_HEIGHT - px) / 2
        for ch in text:  # per character so the tracking matches the page
            d.text((x, ty), ch, font=font, fill=en["color"])
            x += font.getlength(ch) + track
        y += px * LINE_HEIGHT
    if width:
        im = im.resize((int(width), int(width * im.size[1] / W)), Image.LANCZOS)
    return im


# ------------------------------------------------------------------ ledger: lookups
def _read(path):
    p = _path(path)
    if not os.path.exists(p) or os.path.getsize(p) < 5:
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def league_ids():
    if "lid" not in _cache:
        out = {}
        for f in LEAGUES:
            d = _read(f)
            for r in d.to_dict("records"):
                out[(str(r["Year"]), r["LeagueName"].strip())] = str(r["LeagueID"])
        _cache["lid"] = out
    return _cache["lid"]


def short_names():
    if "short" not in _cache:
        d = _read(SHORTNAMES)
        _cache["short"] = {r["Full Name"].strip(): r["Short Name"].strip() for r in d.to_dict("records")}
    return _cache["short"]


def owners():
    """{(year, league_id, roster_id): [(week, owner_id, owner_name)]} from the season's matchup data."""
    if "own" not in _cache:
        out = {}
        for f in MATCHUPS:
            d = _read(f)
            if d.empty:
                continue
            for y, lid, rid, wk, oid, on in zip(d["Year"], d["LeagueID"], d["RosterID"], d["Week"], d["OwnerID"], d["OwnerName"]):
                out.setdefault((str(y), str(lid), str(rid)), []).append((int(wk or 0), oid, on))
        for v in out.values():
            v.sort()
        _cache["own"] = out
    return _cache["own"]


def manager(year, lid, rid, week=None):
    """(user id, Sleeper username) owning the roster at that week ('' for an orphaned team)."""
    rows = owners().get((str(year), str(lid), str(rid)), [])
    if not rows:
        return "", ""
    pick = [r for r in rows if week is None or r[0] <= int(week)] or rows
    _, oid, on = pick[-1]
    if not oid or oid == "Orphan" or on == "Orphan":
        return "", ""
    return str(oid), on


def winner_row(year, etype, event, rnd, team, *, league="", rid="", lid="", week=None, status="Final", source="",
               user_id=None, username=None):
    """One ledger row; resolves the roster slot from the season's name when not given."""
    if not (league and rid):
        sl = tn.slot(year, team)
        if sl:
            league, rid = sl
    league = (league or "").strip()
    lid = lid or league_ids().get((str(year), league), "")
    uid, un = manager(year, lid, rid, week) if (lid and rid) else ("", "")
    if user_id is not None:  # the event's own record (Dwight Fight entrants)
        uid, un = str(user_id), username or un
    row = {"Season": str(year), "EventType": etype, "Event": event, "Round": rnd, "Team": team,
           "Conference": short_names().get(league, league), "LeagueID": lid, "RosterID": str(rid or ""),
           "ManagerUserID": uid, "ManagerName": un, "Status": status, "Source": source, "Week": week}
    row["ArtKey"] = art_key(row)
    return row


# ------------------------------------------------------------------ ledger: builders
def from_postseason_history(path=POST_HIST):
    rounds = set(cfg()["events"]["PlayoffRound"]["rounds"])
    out = []
    for r in _read(path).to_dict("records"):
        y, ev, rn, bowl, win = r["Season"], r["Event"], r["RoundName"], r["Bowl"].strip(), r["Winner"].strip()
        if not win:
            continue
        src = os.path.basename(path)
        wk = r["Week"] or None
        if ev == "CCG":
            row = winner_row(y, "CCG", f"{bowl} Championship", "", win, week=wk, source=src)
            row["Conference"] = bowl  # the conference whose title it is
            row["ArtKey"] = art_key(row)
            out.append(row)
        elif ev == "Bowl":
            out.append(winner_row(y, "Bowl", bowl, "", win, week=wk, source=src))
        elif ev == "Playoff" and rn == "National Championship":
            out.append(winner_row(y, "NationalTitle", "National Championship", "", win, week=wk, source=src))
        elif ev == "Playoff" and rn in rounds and bowl:
            out.append(winner_row(y, "PlayoffRound", bowl, rn, win, week=wk, source=src))
        elif ev == "NIT" and rn == "Final":
            out.append(winner_row(y, "NIT", "NIT", "", win, week=wk, source=src))
    return out


def from_dwight_history(path=DWIGHT_HIST):
    out = []
    for y, team in DWIGHT_PRE_BRACKET.items():
        out.append(winner_row(y, "DwightFight", "Dwight Fight", "", team, status="Recorded",
                              source="Dwight Fight page past champions (no bracket recorded)"))
    for r in _read(path).to_dict("records"):
        if r["RoundName"] != "Final" or not r["Winner"].strip():
            continue
        st = "Reconstructed" if r["Status"].startswith("Reconstructed") else "Final"
        out.append(winner_row(r["Season"], "DwightFight", "Dwight Fight", "", r["Winner"].strip(), week=r["Week"] or None,
                              status=st, source=f"{os.path.basename(path)}: {r['Status']}"))
    return out


def from_postseason_season(year, path=POST_SEASON):
    """Published current-season games that are Final (drafts never reach this file)."""
    d = _read(path)
    if d.empty:
        return []
    d = d[(d["Year"].astype(str) == str(year)) & (d["Status"] == "Final") & (d["Outcome"] == "Win")]
    lg = json.load(open(_path(LEAGUE_CONFIG), encoding="utf-8"))["postseason"]
    rounds_cfg = lg["playoff"]["rounds"]
    nit_final = lg["nit"]["bracket"]["rounds"][-1]
    pr = set(cfg()["events"]["PlayoffRound"]["rounds"])
    src = os.path.basename(path)
    out = []
    for r in d.to_dict("records"):
        kw = dict(league=r["LeagueName"], rid=r["RosterID"], lid=r["LeagueID"], week=r["Week"] or None, source=src)
        if r["Round"] == "CCG":
            row = winner_row(year, "CCG", f"{r['Stage']} Championship", "", r["Team"], **kw)
            row["Conference"] = r["Stage"] or row["Conference"]
            row["ArtKey"] = art_key(row)
            out.append(row)
        elif r["Round"] == "Bowl":
            out.append(winner_row(year, "Bowl", r["BowlName"], "", r["Team"], **kw))
        elif r["Round"] == "Playoff":
            rn = r["Stage"]
            if rn == rounds_cfg[-1]:
                out.append(winner_row(year, "NationalTitle", "National Championship", "", r["Team"], **kw))
            elif rn in pr and r["BowlName"]:
                out.append(winner_row(year, "PlayoffRound", r["BowlName"], rn, r["Team"], **kw))
        elif r["Round"] == "NIT" and r["Stage"] == nit_final:
            out.append(winner_row(year, "NIT", "NIT", "", r["Team"], **kw))
    return out


def from_special_events(year, root=SCOREBOARD):
    out = []
    g = os.path.join(_path(root), str(year), "guillotine.json")
    if os.path.exists(g):
        d = json.load(open(g, encoding="utf-8"))
        if d.get("status") == "final":
            teams = {(t["l"], t["r"]): t for t in d.get("teams", [])}
            for c in d.get("champions", []):
                t = teams.get((c["l"], c["r"]), {})
                out.append(winner_row(year, "Guillotine", d.get("name", "The Guillotine"), "", c["team"],
                                      league=t.get("league", ""), rid=c["r"], lid=c["l"], week=d.get("last_week"),
                                      source="guillotine.json"))
    w = os.path.join(_path(root), str(year), "dwight.json")
    if os.path.exists(w):
        d = json.load(open(w, encoding="utf-8"))
        c = d.get("champion")
        if c:
            out.append(winner_row(year, "DwightFight", "Dwight Fight", "", c.get("team", ""), league=c.get("league", ""),
                                  rid=c.get("roster_id", ""), lid=c.get("league_id", ""), week=d.get("last_week"),
                                  source="dwight.json", user_id=c.get("user_id", ""), username=c.get("username", "")))
    return out


def trophy_display_points():
    """Weights for trophy wins. A playoff round win earns the next advancement bonus."""
    points = json.load(open(_path(LEAGUE_CONFIG), encoding="utf-8"))["managers"]["legend_points"]
    event_keys = {"CCG": "conference", "NIT": "nit_champ", "Bowl": "bowl",
                  "DwightFight": "dwight_fight", "Guillotine": "guillotine"}
    round_keys = {"Sweet 16": "e8", "Second Round": "e8", "Elite 8": "f4", "Final Four": "final"}
    return {**{event: points.get(key, 0) for event, key in event_keys.items()},
            "PlayoffRound": {round_name: points.get(key, 0) for round_name, key in round_keys.items()}}


def frame(rows):
    df = pd.DataFrame(rows, columns=COLUMNS).fillna("")
    if df.empty:
        return df
    df["_o"] = df["EventType"].map({k: i for i, k in enumerate(ORDER)}).fillna(99)
    df["_y"] = df["Season"].astype(int)
    df = df.sort_values(["_y", "_o", "Event", "Round", "Team"], kind="stable").drop(columns=["_o", "_y"])
    return df.reset_index(drop=True)


def write(df, path):
    os.makedirs(os.path.dirname(_path(path)), exist_ok=True)
    df[COLUMNS].to_csv(_path(path), index=False, lineterminator="\n")


def historic_seasons():
    h = _read(HIST)
    return set(h["Season"]) if len(h) else set()


def build_historic():
    return frame(from_postseason_history() + from_dwight_history())


def build_season(year):
    if str(year) in historic_seasons():  # rolled over: the frozen file owns it
        return frame([])
    return frame(from_postseason_season(year) + from_special_events(year))


def ledger():
    """Both files, for every display."""
    return pd.concat([_read(HIST), _read(SEASON)], ignore_index=True).reindex(columns=COLUMNS).fillna("")


def safety_diff(old, new):
    """Rows that disappeared or changed winner (additions always pass)."""
    if old is None or old.empty:
        return []
    g = lambda df: {tuple(k): sorted(tuple(x) for x in grp[WINNER].values.tolist())  # noqa: E731
                    for k, grp in df.groupby(KEY, sort=False)}
    o, n = g(old), g(new)
    diffs = []
    for k, w in o.items():
        label = " / ".join(x for x in k if x)
        if k not in n:
            diffs.append(f"DROPPED {label}: was {', '.join(t for t, _, _ in w)}")
        elif not set(w) <= set(n[k]):
            diffs.append(f"CHANGED {label}: {', '.join(t for t, _, _ in w)} -> {', '.join(t for t, _, _ in n[k])}")
    return diffs


def current_season():
    lid = _read("data/LeagueIDs_AllYears.csv")
    return int(lid["Year"].astype(int).max())


def update_season(year=None, allow_changes=False, path=SEASON):
    """The weekly / post-publish step. Returns 0 (written or unchanged) or 1 (safety check tripped)."""
    year = year or current_season()
    new = build_season(year)
    old = _read(path)
    old = old.reindex(columns=COLUMNS).fillna("") if len(old) else old
    diffs = safety_diff(old, new)
    if diffs and not allow_changes:
        print(f"::error::trophies.py: {len(diffs)} existing trophy row(s) would change; kept {path}. "
              "Check the source data; if the change is right, rerun with --allow-changes (script_to_run: trophies_allow_changes).")
        for d in diffs:
            print("  " + d)
        stale = sorted(set(old["Season"].astype(str)) - {str(year)})
        if stale:
            print(f"  {path} still holds {', '.join(stale)}: roll it over first (Trophy ledger rollover workflow / --rollover).")
        return 1
    for d in diffs:
        print("ALLOWED " + d)
    write(new, path)
    print(f"{path}: {len(new)} trophies for {year}" + (f" ({len(diffs)} allowed change(s))" if diffs else ""))
    return 0


def rollover(year):
    s = _read(SEASON)
    s = s[s["Season"].astype(str) == str(year)] if len(s) else s
    if s.empty:
        sys.exit(f"No {year} rows in {SEASON}; nothing to roll over.")
    h = _read(HIST).reindex(columns=COLUMNS).fillna("")
    if str(year) in set(h["Season"]):
        sys.exit(f"{HIST} already has {year}; fix by hand in a PR.")
    write(frame(pd.concat([h, s.reindex(columns=COLUMNS)], ignore_index=True).to_dict("records")), HIST)
    write(frame([]), SEASON)
    print(f"Rolled {len(s)} {year} trophies into {HIST}; {SEASON} cleared.")


def check():
    L = ledger()
    bad = 0
    for r in L.to_dict("records"):
        drawn = resolved_art(r)
        if drawn != (r["ArtKey"] or art_key(r)):
            print(f"{'generic' if drawn else 'fallback'}: {r['Season']} {r['EventType']} {r['Event']} ({drawn or 'no art'})")
            bad += 1
    print(L.groupby(["Season", "EventType"]).size().unstack(fill_value=0).to_string())
    print(f"{len(L)} trophies; {bad} without their own art file")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-changes", action="store_true")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--force", action="store_true", help="with --backfill: overwrite (review the diff!)")
    ap.add_argument("--rollover", type=int)
    ap.add_argument("--metrics", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--year", type=int)
    a = ap.parse_args()
    os.chdir(ROOT)
    if a.metrics:
        build_metrics()
        print(f"wrote {METRICS}")
    elif a.backfill:
        if os.path.exists(HIST) and not a.force:
            sys.exit(f"{HIST} exists; it is frozen (hand edits via PR). --force to rebuild.")
        df = build_historic()
        write(df, HIST)
        print(f"wrote {HIST}: {len(df)} rows")
    elif a.rollover:
        rollover(a.rollover)
    elif a.check:
        check()
    else:
        sys.exit(update_season(a.year, a.allow_changes))


if __name__ == "__main__":
    main()
