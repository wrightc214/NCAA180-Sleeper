"""menu_build.py -- write reports/assets/menu.js, the one shared site menu (todo-header-rebuild.md).

Reads config/nav.json (tabs, states, fixed sub-rows) and the pages in reports/ (season / week /
projection-archive rows, latest awards week). Runs at the end of the weekly job; safe to run any time.
  python scripts/menu_build.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
from site_common import write_menu  # noqa: E402


def main():
    os.chdir(lcfg.ROOT)
    d = write_menu()
    print(f"menu_build: {len(d['tabs'])} tabs, {len(d['rows'])} rows, awards -> {d['awards']}")


if __name__ == "__main__":
    main()
