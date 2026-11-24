"""Shared site menu (todo-header-rebuild.md, 2026-11-17): config/nav.json -> reports/assets/menu.js,
placeholders on every page, data-driven rows, one-time page conversion."""
import glob
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
import site_common as sc  # noqa: E402
import menu_convert  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "config", "nav.json"), encoding="utf-8"))
KEYS = {t["id"] for t in CFG["tabs"]} | {a for t in CFG["tabs"] for a in t.get("aliases", [])}
STATES = {"visible", "hidden", "hidden-dev"}


def built_data():
    src = open(os.path.join(ROOT, "reports", "assets", "menu.js"), encoding="utf-8").read()
    return json.loads(re.search(r"var D = (\{.*?\});\n", src).group(1))


class Config(unittest.TestCase):
    def test_states_and_ids(self):
        ids = [t["id"] for t in CFG["tabs"]]
        self.assertEqual(len(ids), len(set(ids)))
        for t in CFG["tabs"]:
            self.assertIn(t.get("state", "visible"), STATES, t["id"])
        for row in CFG["rows"].values():
            for i in row["items"]:
                self.assertIn(i.get("state", "visible"), STATES)

    def test_live_menu_unchanged(self):
        """Every tab the site showed before the rebuild stays visible, in the same order."""
        vis = [t["label"] for t in CFG["tabs"] if t.get("state", "visible") == "visible"]
        self.assertEqual(vis, ["Awards", "Roster Map", "Standings", "Games", "Poll", "Postseason",
                               "Selection Watch", "Special Events", "Managers", "Transactions", "Records", "About",
                               "Accessibility", "Notification settings"])

    def test_selection_watch_ccg_public_playoffs_dev(self):
        """Chris, 2026-11-20: CCG public; Playoffs stays Dev-only until approved."""
        items = {i["label"]: i.get("state", "visible") for i in CFG["rows"]["selection-watch"]["items"]}
        self.assertEqual(items, {"CCG": "visible", "Playoffs": "visible"})


class Pages(unittest.TestCase):
    def test_every_page_has_placeholder_and_script(self):
        pages = [p for p in glob.glob("reports/*.html") if os.path.basename(p) not in ("matchups.html", "orphans.html")]
        self.assertGreater(len(pages), 90)
        for p in pages:
            doc = open(p, encoding="utf-8").read()
            m = re.search(r'<nav class="weeks" aria-label="Pages" data-current="([^"]*)"[^>]*></nav>', doc)
            self.assertTrue(m, f"{p}: no menu placeholder")
            self.assertIn(m.group(1), KEYS, f"{p}: unknown data-current {m.group(1)!r}")
            self.assertEqual(doc.count('<script src="assets/menu.js"></script>'), 1, p)
            # no baked tabs or sub-rows left behind
            self.assertNotRegex(doc, r'<nav class="weeks" aria-label="Pages"[^>]*>\s*<a ', p)
            self.assertNotRegex(doc, r'<nav class="weeks sub" aria-label="[^"]+">', p)
            for row in re.findall(r'data-row="([^"]+)"', doc):
                self.assertIn(row, built_data()["rows"], f"{p}: row {row} not in menu.js")

    def test_built_menu_matches_config(self):
        d = built_data()
        self.assertEqual([t["id"] for t in d["tabs"]],
                         [t["id"] for t in CFG["tabs"] if t.get("state", "visible") != "hidden"])
        self.assertTrue(re.fullmatch(r"week-\d{2}\.html", d["tabs"][0]["href"]))


class Rows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.tmp.name
        os.makedirs(os.path.join(r, "data"))
        for w in (1, 2, 3):
            open(os.path.join(r, "data", f"week-{w:02d}.json"), "w").write("{}")
            open(os.path.join(r, f"week-{w:02d}.html"), "w").write("")
        for f in ("week-2024-01.html", "week-2024-11.html", "week-2025-01.html", "week-2025-11.html",
                  "standings-2025.html", "standings.html", "postseason-2024.html", "postseason-2025.html",
                  "postseason.html", "postseason-proj-wk08.html", "postseason-proj-wk09.html"):
            open(os.path.join(r, f), "w").write("")
        self._cs, sc._current_season = sc._current_season, lambda: 2026
        self._od = sc.OUT_DIR

    def tearDown(self):
        sc._current_season = self._cs
        sc.OUT_DIR = self._od
        self.tmp.cleanup()

    def test_rows_from_pages(self):
        d = sc.write_menu(self.tmp.name)
        self.assertEqual(sc.OUT_DIR, self._od)  # restored
        self.assertEqual(d["awards"], "week-03.html")
        rows = d["rows"]
        self.assertEqual([i["label"] for i in rows["awards-seasons"]["items"]], ["2024", "2025", "2026"])
        self.assertEqual(rows["awards-seasons"]["items"][0]["href"], "week-2024-11.html")
        self.assertEqual([i["href"] for i in rows["awards-weeks-2026"]["items"]], ["week-01.html", "week-02.html", "week-03.html"])
        self.assertEqual([i["label"] for i in rows["standings-seasons"]["items"]], ["2025", "2026"])
        self.assertEqual(rows["standings-seasons"]["items"][-1]["href"], "standings.html")
        self.assertEqual([i["href"] for i in rows["postseason-seasons"]["items"]],
                         ["postseason-2024.html", "postseason-2025.html", "postseason.html"])
        self.assertTrue(re.match(rows["postseason-seasons"]["items"][-1]["match"], "postseason-proj-wk08.html"))
        self.assertEqual([i["label"] for i in rows["projection-archive"]["items"]], ["After wk 8", "After wk 9"])
        self.assertTrue(re.match(rows["projection-archive"]["items"][-1]["match"], "postseason.html"))
        self.assertIn("special", rows)
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "assets", "menu.js")))

    def test_hidden_left_out(self):
        cfg = sc.nav_config()
        cfg["tabs"].append({"id": "wip", "label": "WIP", "href": "wip.html", "state": "hidden"})
        with mock.patch.object(sc, "nav_config", return_value=cfg):
            d = sc.menu_data(self.tmp.name)
        ids = [t["id"] for t in d["tabs"]]
        self.assertNotIn("wip", ids)
        self.assertIn("about", ids)  # public since 2026-11-17


class Markup(unittest.TestCase):
    def test_menu_html(self):
        h = sc.menu_html(7, ["awards-seasons", "awards-weeks-2026"])
        self.assertIn('data-current="awards"', h)
        self.assertIn('aria-label="Seasons" data-row="awards-seasons"', h)
        self.assertIn('aria-label="Weeks" data-row="awards-weeks-2026"', h)
        self.assertTrue(h.index("data-row") < h.index("assets/menu.js"))  # rows exist before the script runs
        cfg = sc.nav_config()
        cfg["tabs"].append({"id": "wip", "label": "WIP", "href": "wip.html", "state": "hidden"})
        with mock.patch.object(sc, "nav_config", return_value=cfg):
            self.assertIn('data-state="hidden"', sc.menu_html("wip"))
        self.assertNotIn("data-state", sc.menu_html("about"))
        self.assertNotIn("data-state", sc.menu_html("standings"))

    def test_convert_baked_page(self):
        doc = ('<div class="wrap"><nav class="weeks" aria-label="Pages"><a href="week-10.html">Awards</a>'
               '<a href="postseason.html" aria-current="page">Postseason</a></nav>'
               '<nav class="weeks sub" aria-label="Seasons"><span>Season</span><a href="postseason-2025.html">2025</a></nav>'
               '<!--projection-archive--><nav class="weeks sub" aria-label="Projection archive"><a href="x">After wk 8</a></nav>'
               '<header>x</header>')
        out = menu_convert.convert(doc, "postseason-proj-wk08.html", 2026)
        self.assertIn('data-current="postseason"', out)
        self.assertIn('data-row="postseason-seasons"', out)
        self.assertIn('data-row="projection-archive"', out)
        self.assertNotIn("<a href", out.split("<header>")[0].split("<noscript>")[0])
        self.assertTrue(out.endswith("<header>x</header>"))
        wk = ('<nav class="weeks" aria-label="Pages"><a href="week-10.html" aria-current="page">Awards</a></nav>\n'
              '<nav class="weeks sub" aria-label="Seasons"></nav><nav class="weeks sub" aria-label="Weeks"></nav>')
        self.assertIn('data-row="awards-weeks-2023"', menu_convert.convert(wk, "week-2023-04.html", 2026))
        self.assertIn('data-row="awards-weeks-2026"', menu_convert.convert(wk, "week-04.html", 2026))
        how = '<nav class="weeks" aria-label="Pages"><a href="poll.html" aria-current="page">Poll</a></nav>'
        self.assertIn('data-row="poll"', menu_convert.convert(how, "poll-how.html", 2026))


if __name__ == "__main__":
    unittest.main()
