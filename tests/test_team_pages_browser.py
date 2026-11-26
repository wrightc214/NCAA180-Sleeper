"""Team page in a real browser (task 5.20): loads a team, draws every section, no sideways scroll on a
phone, a past season's league ID lands on this season's page, no query = team picker.
Opt-in: RUN_SCOREBOARD_BROWSER_TESTS=1. Screenshots (PR evidence): TEAM_ARTIFACTS=<folder>."""
import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = os.environ.get("TEAM_ARTIFACTS")


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def league_id(name, year=None):
    idx = json.loads((ROOT / "data" / "teams" / "index.json").read_text(encoding="utf-8"))
    if year is None:
        return next(lid for lid, lg in idx["leagues"].items() if lg["name"] == name)
    import csv
    for f in ("data/backfill/LeagueIDs_2019_2020.csv", "data/LeagueIDs_AllYears.csv"):
        for r in csv.DictReader(open(ROOT / f, encoding="utf-8-sig")):
            if int(r["Year"]) == year and r["LeagueName"].strip() == name:
                return r["LeagueID"]
    raise KeyError((name, year))


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in Playwright")
class TeamPageBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()

    def open(self, path, width=1280, theme="light"):
        p = self.browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme, service_workers="block")
        self.addCleanup(p.close)
        errors = []
        p.on("pageerror", lambda ex: errors.append(str(ex)))
        self.addCleanup(lambda: self.assertEqual(errors, []))
        p.route("https://fonts.googleapis.com/**", lambda r: r.abort())
        p.route("https://fonts.gstatic.com/**", lambda r: r.abort())
        p.goto(self.base + path)
        p.wait_for_selector("body[data-ready]", state="attached", timeout=20000)
        return p

    def test_team_page_loads(self):
        mw = league_id("NCAA MOUNTAIN WEST")
        for width, theme, tag in ((1280, "light", "desktop"), (390, "dark", "mobile")):
            with self.subTest(tag):
                p = self.open(f"reports/team.html?league={mw}&roster=4", width, theme)
                self.assertEqual(p.text_content(".tm-head h1"), "Air Force")
                self.assertIn("Formerly Fresno State", p.inner_text(".tm-head"))
                self.assertTrue(p.is_visible("#tm-roster li"))
                self.assertGreaterEqual(p.locator("#tm-trophies figure.trophy").count(), 1)
                self.assertGreaterEqual(p.locator("#tm-trophies article .snap-card-btn").count(), 1, "trophy Save image")
                self.assertGreaterEqual(p.locator("details.tm-season").count(), 8)
                self.assertEqual(p.locator("details.tm-season[open]").count(), 1)
                self.assertEqual(p.get_attribute("details.tm-season[open]", "data-year"), str(json.loads(
                    (ROOT / "data/teams/index.json").read_text())["season"]))
                self.assertIn("Fresno State", p.inner_text("details.tm-season[data-year='2021'] summary"))
                self.assertTrue(p.is_visible(".tm-draft li"))
                self.assertTrue(p.is_visible("#tm-tx .tm-tx-item"))
                self.assertEqual(p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), 0,
                                 "no sideways scroll")
                p.click(".tm-more")
                self.assertGreater(p.locator("#tm-tx .tm-tx-item:visible").count(), 25)
                for el in p.query_selector_all("#tm-trophies figure.trophy img"):
                    el.scroll_into_view_if_needed()
                p.wait_for_function("[...document.querySelectorAll('#tm-trophies figure.trophy:not(.fallback) img')].every(i=>i.complete&&i.naturalWidth>0)")
                if OUT:
                    os.makedirs(OUT, exist_ok=True)
                    p.screenshot(path=os.path.join(OUT, f"team-{tag}.png"), full_page=True)

    def test_past_league_id_lands_on_this_season(self):
        old = league_id("NCAA MOUNTAIN WEST", 2021)
        p = self.open(f"reports/team.html?league={old}&roster=4")
        self.assertEqual(p.text_content(".tm-head h1"), "Air Force")
        self.assertIn(f"league={league_id('NCAA MOUNTAIN WEST')}", p.url)

    def test_standings_links_follow_dev_view(self):
        p = self.open_plain("reports/standings-2021.html")
        self.assertEqual(p.locator("a.team-link").count(), 0, "hidden-dev: no links for the public")
        p.evaluate("NCAA180.menu.setDev(true)")  # the About page's Dev view switch
        p.reload()
        p.wait_for_selector("a.team-link")
        link = p.locator("#t a.team-link", has_text="Fresno State").first
        link.click()
        p.wait_for_selector("body[data-ready]", state="attached")
        self.assertEqual(p.text_content(".tm-head h1"), "Air Force")
        p.evaluate("NCAA180.menu.setDev(false)")

    def open_plain(self, path):
        p = self.browser.new_page(service_workers="block")
        self.addCleanup(p.close)
        p.route("https://fonts.googleapis.com/**", lambda r: r.abort())
        p.route("https://fonts.gstatic.com/**", lambda r: r.abort())
        p.goto(self.base + path)
        p.wait_for_selector("#t tbody tr")
        return p

    def test_picker_and_unknown_team(self):
        p = self.open("reports/team.html")
        self.assertEqual(p.locator("#tm-pick a").count(), 180)
        p = self.open(f"reports/team.html?league={league_id('NCAA AMERICAN', 2019)}&roster=5")
        self.assertTrue(p.is_visible("#tm-error"))
        self.assertTrue(p.is_visible("#tm-pick a"))


if __name__ == "__main__":
    unittest.main()
