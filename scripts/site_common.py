"""
site_common.py -- pieces shared by every page under reports/ (imported, not run).

nav_html(current)   the tab bar: Weekly Awards (latest week), Roster Map, Standings, Poll;
                    week_archive_html(week) lists every week on the awards page
                    (once reports/poll.html exists).
                    `current` is an int week, "map", "standings", or "poll".
page_head(title)    <head> with the same fonts + stylesheet as the weekly report, plus the app
                    tags (manifest, home-screen icon, assets/app.js) copied from the template
                    (style block lifted from templates/weekly_report.html, so every page
                    stays visually identical without a second copy of the CSS).
"""
import glob
import html
import os
import re

TEMPLATE = "templates/weekly_report.html"
OUT_DIR = "reports"


def built_weeks():
    out = []
    for f in glob.glob(os.path.join(OUT_DIR, "data", "week-*.json")):
        m = re.search(r"week-(\d+)\.json$", f)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def nav_html(current, weeks=None):
    """Main tabs: Weekly Awards (latest week; older weeks via week_archive_html on that page),
    Roster Map, Standings, Matchups, Poll, Managers. Poll sub-pages (how it works, bot ballots) highlight Poll."""
    weeks = built_weeks() if weeks is None else weeks
    cur = ' aria-current="page"'
    links = []
    if weeks:
        links.append(f'<a href="week-{max(weeks):02d}.html"{cur if isinstance(current, int) else ""}>Weekly Awards</a>')
    links.append(f'<a href="roster-map.html"{cur if current == "map" else ""}>Roster Map</a>')
    links.append(f'<a href="standings.html"{cur if current == "standings" else ""}>Standings</a>')
    if current == "matchups" or os.path.exists(os.path.join(OUT_DIR, "matchups.html")):
        links.append(f'<a href="matchups.html"{cur if current == "matchups" else ""}>Matchups</a>')
    if current == "scoreboard" or os.path.exists(os.path.join(OUT_DIR, "scoreboard.html")):
        links.append(f'<a href="scoreboard.html"{cur if current == "scoreboard" else ""}>Scoreboard</a>')
    if current in ("poll", "poll-how", "poll-bots") or os.path.exists(os.path.join(OUT_DIR, "poll.html")):
        links.append(f'<a href="poll.html"{cur if current in ("poll", "poll-how", "poll-bots") else ""}>Poll</a>')
    if current == "managers" or os.path.exists(os.path.join(OUT_DIR, "managers.html")):
        links.append(f'<a href="managers.html"{cur if current == "managers" else ""}>Managers</a>')
    if current == "records" or os.path.exists(os.path.join(OUT_DIR, "records.html")):
        links.append(f'<a href="records.html"{cur if current == "records" else ""}>Records</a>')
    if current == "app" or os.path.exists(os.path.join(OUT_DIR, "app.html")):
        links.append(f'<a href="app.html"{cur if current == "app" else ""}>Notifications</a>')
    return "".join(links)


def week_archive_html(current, weeks=None):
    """Second row on the weekly awards page: every built week, current one highlighted."""
    weeks = built_weeks() if weeks is None else weeks
    if len(weeks) < 2:
        return ""
    cur = ' aria-current="page"'
    links = "".join(f'<a href="week-{w:02d}.html"{cur if current == w else ""}>Wk {w}</a>' for w in weeks)
    return f'<nav class="weeks sub" aria-label="Weekly archive"><span>Archive</span>{links}</nav>'


# Back-to-top button (Chris, 2026-10-14): fixed bottom-right, appears only after scrolling about a screen,
# small so it doesn't sit over content for long; hidden when printing. Styles live in the template's <style>.
TOTOP = ('<a href="#" class="totop" aria-label="Back to top" hidden>&#8593;</a>'
         '<script>(function(){var b=document.currentScript.previousElementSibling;'
         'function f(){b.hidden=window.scrollY<window.innerHeight*0.9;}'
         'window.addEventListener("scroll",f,{passive:true});window.addEventListener("load",f);'
         'b.addEventListener("click",function(ev){ev.preventDefault();var r=window.matchMedia("(prefers-reduced-motion: reduce)").matches;'
         'window.scrollTo({top:0,behavior:r?"auto":"smooth"});});})();</script>')


def page_head(title, extra_css="", totop=True):
    tpl = open(TEMPLATE, encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    fonts = re.findall(r"<link [^>]*>", tpl)  # fonts + the app's manifest / home-screen icon links
    app = re.findall(r'<meta name="(?:theme-color|apple-mobile-web-app-[a-z-]+)"[^>]*>|<script src="assets/app\.js"[^>]*></script>', tpl)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n" + "\n".join(fonts) + "\n" + "".join(app) + "\n" + style +
            (f"\n<style>{extra_css}</style>" if extra_css else "") + "\n</head><body>" + (TOTOP if totop else ""))


# ---- Team colors: standing rule for every graphic -------------------------------------
# "Colors - Teams.csv" / "Colors - Leagues.csv": Primary, Secondary, Background, Text.
#   Primary / Secondary   the school's identity colors. Plain color blocks with no text
#                         (chips, award bars, map dots/rings) use these directly.
#   Background / Text     optional manual override for blocks that carry text. Leave blank
#                         and the pair is picked automatically by display_pair().
# "Colors - Palette.csv" lists every official color per school/league (Name, Order, Hex,
# ColorName, Role). display_pair() mixes and matches from it, with the background always
# the Primary or Secondary and text needing contrast >= MIN_CONTRAST (3.0, bold-text bar):
#   1. Primary + Secondary, if readable (>= READABLE 4.5)
#   2. Primary background + the first readable school color as text: Secondary, then the
#      school's accents (tertiary) in official order, then its own neutrals
#   3. Secondary background, same way (Primary first)
#   4. borderline pair (>= MIN_CONTRAST 3.0): the lighter of Primary/Secondary behind, the darker as text
#   5. last resort: Primary with white or black text

MIN_CONTRAST = 3.0
READABLE = 4.5  # text on a team color block (small text included)

def _hex(c):
    if not isinstance(c, str) or not c.strip():
        return None
    c = c.strip()
    return c if c.startswith("#") else "#" + c


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _sat(h):
    import colorsys
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hsv(r, g, b)[1]


BORDERLINE = 2.5
PALETTE = "data/Colors - Palette.csv"
_palettes = None


def palettes():
    """{name: [hex, ...]} in official order, from Colors - Palette.csv (empty if missing).
    Also fills _roles: {name: {hex: role}} (Primary / Secondary / Accent / Neutral)."""
    global _palettes
    if _palettes is None:
        _palettes = {}
        if os.path.exists(PALETTE):
            import csv
            with open(PALETTE, encoding="utf-8-sig") as f:
                for r in sorted(csv.DictReader(f), key=lambda r: (r["Name"], int(r["Order"]))):
                    h = _hex(r["Hex"])
                    if h:
                        _palettes.setdefault(r["Name"], []).append(h.upper())
                        _roles.setdefault(r["Name"], {}).setdefault(h.upper(), (r.get("Role") or "").strip())
    return _palettes


_roles = {}


def _text_order(palette, exclude, name=None):
    """Palette colors usable as text, school accents (tertiary) before neutrals, official order kept."""
    roles = _roles.get(name, {})
    others = [c for c in palette if c not in exclude]
    return ([c for c in others if roles.get(c) != "Neutral"] +
            [c for c in others if roles.get(c) == "Neutral"])


def display_pair(primary, secondary, palette=(), name=None):
    """(background, text) chosen by the rule above."""
    p, s = _hex(primary), _hex(secondary)
    ex = {p.upper(), (s or "").upper()}
    if s and contrast(p, s) >= READABLE:
        return p, s
    for bg in (p, s):  # school colors as text: accents before neutrals
        if not bg:
            continue
        other = [s] if bg == p else [p]
        cands = [c for c in other if c] + _text_order(palette, ex, name)
        pick = [c for c in cands if contrast(bg, c) >= READABLE]
        if pick:
            return bg, pick[0]
    if s and contrast(p, s) >= MIN_CONTRAST:  # borderline: lighter behind, darker as text
        return (p, s) if _lum(p) >= _lum(s) else (s, p)
    return p, ("#ffffff" if contrast(p, "#ffffff") >= contrast(p, "#000000") else "#000000")


def team_colors(primary, secondary, background=None, text=None, name=None,
                default=("#14213a", "#ffffff")):
    """(background, text) for a block that carries text: the row's manual Background/Text
    if filled in, else display_pair() over the school's palette (looked up by `name`)."""
    p, sc, bg, tx = _hex(primary), _hex(secondary), _hex(background), _hex(text)
    try:
        if bg and tx:
            return bg, tx
        if not p:
            return default
        return display_pair(p, sc, palettes().get(name, []), name=name)
    except Exception:
        return default
