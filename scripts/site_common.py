"""
site_common.py -- pieces shared by every page under reports/ (imported, not run).

nav_html(current)   the tab bar: one tab per built week, then Roster Map and Standings.
                    `current` is an int week, "map", or "standings".
page_head(title)    <head> with the same fonts + stylesheet as the weekly report
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
    weeks = built_weeks() if weeks is None else weeks
    cur = ' aria-current="page"'
    links = [f'<a href="week-{w:02d}.html"{cur if current == w else ""}>Wk {w}</a>' for w in weeks]
    links.append(f'<a href="roster-map.html"{cur if current == "map" else ""}>Roster Map</a>')
    links.append(f'<a href="standings.html"{cur if current == "standings" else ""}>Standings</a>')
    return "".join(links)


def page_head(title, extra_css=""):
    tpl = open(TEMPLATE, encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    fonts = re.findall(r"<link [^>]*>", tpl)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n" + "\n".join(fonts) + "\n" + style +
            (f"\n<style>{extra_css}</style>" if extra_css else "") + "\n</head><body>")


# ---- Team colors: standing rule for every graphic -------------------------------------
# "Colors - Teams.csv" / "Colors - Leagues.csv": Primary, Secondary, Background, Text.
#   Primary / Secondary   the school's identity colors. Plain color blocks with no text
#                         (chips, award bars, map dots/rings) use these directly.
#   Background / Text     optional manual override for blocks that carry text. Leave blank
#                         and the pair is picked automatically by display_pair().
# "Colors - Palette.csv" lists every official color per school/league (Name, Order, Hex,
# ColorName, Role). display_pair() mixes and matches from it, with the background always
# the Primary or Secondary and text needing contrast >= MIN_CONTRAST (3.0, bold-text bar):
#   1. Primary + Secondary
#   2. Primary + another palette color, taken in the palette's official order (the brand's
#      own priority): the first one that reads comfortably (>= 4.5), else the first >= 3.0
#   3. Secondary + another palette color, same way
#   4. borderline pair (>= 2.5): the lighter of Primary/Secondary behind, the darker as text
#   5. last resort: Primary with white or black text

MIN_CONTRAST = 3.0

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
    """{name: [hex, ...]} in official order, from Colors - Palette.csv (empty if missing)."""
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
    return _palettes


def display_pair(primary, secondary, palette=()):
    """(background, text) chosen by the rule above."""
    p, s = _hex(primary), _hex(secondary)
    if s and contrast(p, s) >= MIN_CONTRAST:
        return p, s
    for bg in (p, s):
        if not bg:
            continue
        others = [c for c in palette if c not in (p.upper(), (s or "").upper())]
        pick = ([c for c in others if contrast(bg, c) >= 4.5]
                or [c for c in others if contrast(bg, c) >= MIN_CONTRAST])
        if pick:
            return bg, pick[0]
    if s and contrast(p, s) >= BORDERLINE:
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
        return display_pair(p, sc, palettes().get(name, []))
    except Exception:
        return default
