"""
site_common.py -- pieces shared by every page under reports/ (imported, not run).

menu_html(current, rows)  the page's menu placeholders + assets/menu.js (the one shared menu;
                    config/nav.json, write_menu). `current` is an int week or a tab key.
page_head(title)    <head> with the same fonts + stylesheet as the weekly report, plus the app
                    tags (manifest, home-screen icon, assets/app.js) copied from the template
                    (style block lifted from templates/weekly_report.html, so every page
                    stays visually identical without a second copy of the CSS).
"""
import glob
import html
import os
import re
import urllib.parse
import json

TEMPLATE = "templates/weekly_report.html"
OUT_DIR = "reports"


def built_weeks():
    out = []
    for f in glob.glob(os.path.join(OUT_DIR, "data", "week-*.json")):
        m = re.search(r"week-(\d+)\.json$", f)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


# ---- Site menu (todo-header-rebuild.md, 2026-11-17) ------------------------------------
# One shared menu: config/nav.json -> reports/assets/menu.js (write_menu / scripts/menu_build.py).
# Pages carry only empty placeholders (menu_html), so a menu change never rebuilds a page.
NAV_CONFIG = "config/nav.json"
MENU_TEMPLATE = "templates/menu.js"
MENU_OUT = os.path.join(OUT_DIR, "assets", "menu.js")
# aria-labels of the sub-rows (kept from the per-page rows they replace)
ROW_ARIA = {"awards-seasons": "Seasons", "standings-seasons": "Seasons", "postseason-seasons": "Seasons",
            "projection-archive": "Projection archive", "poll": "Poll pages", "special": "Special events"}


def nav_config():
    with open(NAV_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def _row_aria(key):
    return ROW_ARIA.get(key) or ("Weeks" if key.startswith("awards-weeks") else key)


def page_state(current):
    """menu state of the page whose tab key is `current` (visible when not in the menu list)."""
    for t in nav_config()["tabs"]:
        if t["id"] == current or current in t.get("aliases", []):
            return t.get("state", "visible")
    return "visible"


def menu_html(current, rows=()):
    """The page's menu block: main-tab placeholder, sub-row placeholders, the shared menu script.
    current: tab key (int week -> "awards"; see config/nav.json ids/aliases). rows: sub-row keys
    (awards-seasons, awards-weeks-<year>, standings-seasons, postseason-seasons, projection-archive,
    poll, special). Written once per page; reports/assets/menu.js fills it in the browser."""
    key = "awards" if isinstance(current, int) else (current or "")
    state = page_state(key) if key else "visible"
    st = f' data-state="{state}"' if state != "visible" else ""
    out = f'<nav class="weeks" aria-label="Pages" data-current="{html.escape(key)}"{st}></nav>'
    out += "".join(f'<nav class="weeks sub" aria-label="{html.escape(_row_aria(r))}" data-row="{html.escape(r)}"></nav>' for r in rows)
    return out + '<script src="assets/menu.js"></script><noscript><a href="index.html">Home</a></noscript>'


def _files(pattern):
    return sorted(os.path.basename(f) for f in glob.glob(os.path.join(OUT_DIR, pattern)))


def _current_season():
    try:
        import _postseason_common as ps
        return ps.current_season()
    except Exception:
        import league_config as lcfg
        return lcfg.season()


def menu_rows(out_dir=None):
    """Data-driven sub-rows, read from the pages that exist in reports/."""
    global OUT_DIR
    keep, OUT_DIR = OUT_DIR, out_dir or OUT_DIR
    try:
        cur = _current_season()
        rows = {}
        weeks = built_weeks() or sorted(int(m.group(1)) for f in _files("week-*.html") if (m := re.fullmatch(r"week-(\d{2})\.html", f)))
        past = {}
        for f in _files("week-*.html"):
            m = re.fullmatch(r"week-(\d{4})-(\d{2})\.html", f)
            if m:
                past.setdefault(int(m.group(1)), []).append(int(m.group(2)))
        # Awards: season row (past seasons open on their last week) + a week row per season
        if past and weeks:
            items = [{"label": str(y), "href": f"week-{y}-{max(w):02d}.html", "match": f"^week-{y}-\\d+\\.html$"} for y, w in sorted(past.items())]
            items.append({"label": str(cur), "href": f"week-{max(weeks):02d}.html", "match": "^week-\\d{2}\\.html$"})
            rows["awards-seasons"] = {"label": "Season", "aria": "Seasons", "items": items}
        for y, w in sorted(past.items()):
            rows[f"awards-weeks-{y}"] = {"label": "Week", "aria": "Weeks", "min": 2,
                                         "items": [{"label": f"Wk {x}", "href": f"week-{y}-{x:02d}.html"} for x in sorted(w)]}
        if weeks:
            rows[f"awards-weeks-{cur}"] = {"label": "Week", "aria": "Weeks", "min": 2,
                                           "items": [{"label": f"Wk {x}", "href": f"week-{x:02d}.html"} for x in weeks]}
        # Standings: past seasons + this season (standings.html)
        sy = [int(m.group(1)) for f in _files("standings-*.html") if (m := re.fullmatch(r"standings-(\d{4})\.html", f))]
        rows["standings-seasons"] = {"label": "Season", "aria": "Seasons",
                                     "items": [{"label": str(y), "href": f"standings-{y}.html"} for y in sorted(sy) if y != cur]
                                     + [{"label": str(cur), "href": "standings.html", "match": f"^standings(-{cur})?\\.html$"}]}
        # Postseason: each season's page; this season = postseason.html (projection, then the real page)
        py = [int(m.group(1)) for f in _files("postseason-*.html") if (m := re.fullmatch(r"postseason-(\d{4})\.html", f))]
        rows["postseason-seasons"] = {"label": "Season", "aria": "Seasons",
                                      "items": [{"label": str(y), "href": f"postseason-{y}.html"} for y in sorted(py) if y != cur]
                                      + [{"label": str(cur), "href": "postseason.html", "match": f"^postseason(-{cur}|-proj-wk\\d+)?\\.html$"}]}
        # Projection archive: one link per saved projection week; the newest is also postseason.html
        pw = sorted(int(m.group(1)) for f in _files("postseason-proj-wk*.html") if (m := re.fullmatch(r"postseason-proj-wk(\d+)\.html", f)))
        rows["projection-archive"] = {"label": "Projection", "aria": "Projection archive", "min": 2,
                                      "items": [{"label": f"After wk {w}", "href": f"postseason-proj-wk{w:02d}.html",
                                                 **({"match": f"^postseason(-proj-wk{w:02d})?\\.html$"} if w == pw[-1] else {})} for w in pw]}
        return rows, (f"week-{max(weeks):02d}.html" if weeks else None)
    finally:
        OUT_DIR = keep


def menu_data(out_dir=None):
    """What menu.js carries: tabs (hidden ones left out), fixed + data-driven rows, latest awards page."""
    cfg = nav_config()
    rows, awards = menu_rows(out_dir)
    tabs = []
    for t in cfg["tabs"]:
        if t.get("state", "visible") == "hidden":
            continue
        t = {k: v for k, v in t.items() if not (k == "state" and v == "visible")}
        if t["href"] == "@awards":
            if not awards:
                continue
            t["href"] = awards
        tabs.append(t)
    for key, row in cfg.get("rows", {}).items():
        items = [{k: v for k, v in i.items() if not (k == "state" and v == "visible")}
                 for i in row["items"] if i.get("state", "visible") != "hidden"]
        rows[key] = {**{k: v for k, v in row.items() if k != "items"}, "aria": _row_aria(key), "items": items}
    return {"tabs": tabs, "rows": rows, "awards": awards}


def write_menu(out_dir=None):
    data = menu_data(out_dir)
    tpl = open(MENU_TEMPLATE, encoding="utf-8").read()
    # Bundle the standalone accessibility source into the synchronous menu entrypoint.
    # Existing static reports only reference assets/menu.js; do not introduce a flash
    # or require rebuilding historical HTML just to load an additional script.
    with open("templates/accessibility.js", encoding="utf-8") as a11y_file:
        accessibility_source = a11y_file.read()
    if "/*__ACCESSIBILITY__*/" not in tpl:
        raise ValueError("menu template missing accessibility bundle placeholder")
    js = tpl.replace("/*__ACCESSIBILITY__*/", accessibility_source).replace(
        "/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = os.path.join(out_dir or OUT_DIR, "assets", "menu.js")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(js)
    return data


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


# Standard section treatment (Chris, 2026-11-08): fold + Collapse all + save image on every section.
SECTIONS_JS = '<script src="assets/snapshot.js"></script><script src="assets/sections.js"></script>'


# ---- Team logos by background (Chris, 2026-11-12) -------------------------------------
# Dark backgrounds only: Chris's dark alt (assets/logos/teams/alt-dark/<Team>.png) if there is one,
# else the glow version (glow-dark/<Team>.png, logo_glow.py), else the normal logo. Light
# backgrounds use the normal logo. Theme-following pages emit both images and CSS picks
# (.tl-hd / .tl-d in the shared stylesheet); blocks with a fixed color (team-color chips) decide here.
LOGO_DIR = "assets/logos/teams"


def logo_info(team, prefix="../"):
    """{'src', 'dark'} for a team ('dark' = alt or glow file, '' if neither), or None without a logo."""
    if not team or not os.path.exists(os.path.join(LOGO_DIR, f"{team}.png")):
        return None
    q = urllib.parse.quote(team)
    dark = next((f"{prefix}{LOGO_DIR}/{d}/{q}.png" for d in ("alt-dark", "glow-dark")
                 if os.path.exists(os.path.join(LOGO_DIR, d, f"{team}.png"))), "")
    return {"src": f"{prefix}{LOGO_DIR}/{q}.png", "dark": dark}


def is_dark(hexcolor):
    try:
        h = hexcolor.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except (AttributeError, ValueError):
        return False
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) < 0.18


def logo_html(team, prefix="../", cls="", alt="", bg=None, attrs=""):
    """<img> markup for a team logo ('' without one). bg=None follows the page theme;
    bg='#hex' is a fixed background (decided now)."""
    i = logo_info(team, prefix)
    if not i:
        return ""
    a = f' alt="{html.escape(alt)}"{attrs}'
    c = lambda extra: f' class="{(cls + " " + extra).strip()}"' if (cls or extra) else ""  # noqa: E731
    if bg is not None:
        return f'<img{c("")} src="{i["dark"] if is_dark(bg) and i["dark"] else i["src"]}"{a}>'
    if i["dark"]:
        return f'<img{c("tl-hd")} src="{i["src"]}"{a}><img{c("tl-d")} src="{i["dark"]}" alt="">'
    return f'<img{c("")} src="{i["src"]}"{a}>'
