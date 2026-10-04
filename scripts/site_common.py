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
# Use the team's own pair (Background + Font from "Colors - Teams.csv") when the Font
# color reads on the Background (WCAG contrast >= 4.5). Otherwise fall back to white or
# black text, and if the Background is a gray (low saturation) use the team's other color
# as the background instead -- e.g. Alabama: gray/crimson -> crimson with white text.

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


def team_colors(bg, fg, default=("#14213a", "#ffffff")):
    """(background, text) for a team block, applying the fallback rule above."""
    bg, fg = _hex(bg), _hex(fg)
    try:
        if not bg:
            return default
        if fg and contrast(bg, fg) >= 4.5:
            return bg, fg
        if fg and _sat(bg) < 0.35 and _sat(fg) >= 0.35:
            bg = fg  # gray background -> the team's real color
        text = "#ffffff" if contrast(bg, "#ffffff") >= contrast(bg, "#000000") else "#000000"
        return bg, text
    except Exception:
        return default
