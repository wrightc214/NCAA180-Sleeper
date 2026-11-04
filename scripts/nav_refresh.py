"""nav_refresh.py -- rewrite the main tab row on every built page in reports/.

Why (Chris, 2026-11-03): a new tab (e.g. Postseason) only reached a page when that page's own
script rebuilt it, so the menu differed page to page. This swaps each page's
<nav class="weeks" aria-label="Pages"> block for site_common.nav_html(), keeping the page's
highlighted tab. Touches nothing else. Runs at the end of the weekly job; safe to run any time.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
from site_common import built_weeks, nav_html  # noqa: E402

NAV = re.compile(r'<nav class="weeks" aria-label="Pages">.*?</nav>', re.S)
CURRENT = {"roster-map.html": "map", "standings.html": "standings", "scoreboard.html": "scoreboard",
           "poll.html": "poll", "postseason.html": "postseason", "managers.html": "managers",
           "records.html": "records", "app.html": "app"}


def current_of(block):
    """The page's highlighted tab, read from its existing nav (aria-current link)."""
    m = re.search(r'<a href="([^"]+)"[^>]*aria-current="page"', block)
    if not m:
        return None
    href = m.group(1)
    w = re.match(r"week-(\d+)\.html$", href)
    return int(w.group(1)) if w else CURRENT.get(href)


def main():
    os.chdir(lcfg.ROOT)
    weeks = built_weeks()
    changed = 0
    for path in sorted(glob.glob("reports/*.html")):
        doc = open(path, encoding="utf-8").read()
        m = NAV.search(doc)
        if not m:
            continue
        new = f'<nav class="weeks" aria-label="Pages">{nav_html(current_of(m.group(0)), weeks)}</nav>'
        if new != m.group(0):
            with open(path, "w", encoding="utf-8") as f:
                f.write(doc[:m.start()] + new + doc[m.end():])
            changed += 1
    print(f"nav_refresh: {changed} page(s) updated")


if __name__ == "__main__":
    main()
