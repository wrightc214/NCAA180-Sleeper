"""menu_convert.py -- one-time switch of already-built pages to the shared menu (todo-header-rebuild.md).

Replaces each page's baked tab row (<nav class="weeks" aria-label="Pages">…</nav>) and the sub-rows
right after it (Seasons, Weeks, Poll pages, Projection archive, Special events) with
site_common.menu_html() placeholders; reports/assets/menu.js fills them in the browser. Keeps each
page's highlighted tab. Idempotent (converted pages are skipped). Page generators already emit the
placeholders, so this is only for pages that aren't rebuilt (archives) and for the switch-over itself.
  python scripts/menu_convert.py
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
from site_common import _current_season, menu_html  # noqa: E402

MAIN = re.compile(r'<nav class="weeks" aria-label="Pages">(.*?)</nav>', re.S)
SUB = re.compile(r'\s*(?:<!--projection-archive-->|<nav class="weeks sub" aria-label="([^"]+)">.*?</nav>)', re.S)
CURRENT = {"roster-map.html": "map", "standings.html": "standings", "scoreboard.html": "scoreboard",
           "poll.html": "poll", "poll-how.html": "poll-how", "poll-bots.html": "poll-bots",
           "postseason.html": "postseason", "managers.html": "managers", "records.html": "records",
           "app.html": "app", "special.html": "special", "about.html": "about"}


def current_of(block):
    """The page's highlighted tab, read from its baked nav (aria-current link)."""
    m = re.search(r'<a href="([^"]+)"[^>]*aria-current="page"', block)
    if not m:
        return None
    href = m.group(1)
    return "awards" if re.match(r"week-\d+\.html$", href) else CURRENT.get(href)


def by_name(name):
    """Fallback when a page has no highlighted tab (e.g. About)."""
    if re.match(r"(week-|index\.html)", name):
        return "awards"
    for prefix, key in (("standings", "standings"), ("postseason", "postseason"), ("poll", "poll")):
        if name.startswith(prefix):
            return key
    return CURRENT.get(name)


def rows_for(name, labels, arch, current, season):
    rows = []
    for lab in labels:
        if lab == "Seasons":
            key = ("awards-seasons" if name.startswith(("week-", "index")) else
                   "standings-seasons" if name.startswith("standings") else "postseason-seasons")
        elif lab == "Weeks":
            m = re.match(r"week-(\d{4})-\d{2}\.html$", name)
            key = f"awards-weeks-{m.group(1) if m else season}"
        else:
            key = {"Projection archive": "projection-archive", "Poll pages": "poll", "Special events": "special"}[lab]
        if key not in rows:
            rows.append(key)
    if arch and "projection-archive" not in rows:
        rows.append("projection-archive")
    if current in ("poll", "poll-how", "poll-bots") and "poll" not in rows:
        rows.append("poll")  # How the poll works had no row; all poll pages now share one
    return rows


def convert(doc, name, season):
    m = MAIN.search(doc)
    if not m:
        return None
    current = current_of(m.group(0)) or by_name(name)
    end, labels, arch = m.end(), [], False
    while True:
        s = SUB.match(doc, end)
        if not s:
            break
        if s.group(1):
            labels.append(s.group(1))
        else:
            arch = True
        end = s.end()
    # rows baked elsewhere on the page (the poll pages had theirs under the header) move up with the rest
    rest = doc[end:]
    for lab in ("Poll pages", "Seasons", "Weeks", "Projection archive", "Special events"):
        pat = re.compile(r'<nav class="weeks sub" aria-label="%s">.*?</nav>' % lab, re.S)
        if pat.search(rest):
            labels.append(lab)
            rest = pat.sub("", rest)
    rest = rest.replace("<!--projection-archive-->", "")
    new = menu_html(current, rows_for(name, labels, arch, current, season))
    return doc[:m.start()] + new + rest


def main(paths=None):
    os.chdir(lcfg.ROOT)
    season = _current_season()
    changed = 0
    for path in paths or sorted(glob.glob("reports/*.html")):
        doc = open(path, encoding="utf-8").read()
        if 'data-current="' in doc:
            continue
        new = convert(doc, os.path.basename(path), season)
        if new and new != doc:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            changed += 1
    print(f"menu_convert: {changed} page(s) converted")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
