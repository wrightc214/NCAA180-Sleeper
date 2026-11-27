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
                self.assertGreaterEqual(p.locator("#tm-over .tm-tile").count(), 8)
                self.assertGreaterEqual(p.locator("#tm-over-sec .snap-card-btn, #tm-over-sec .snap-btn").count(), 1, "overview Save image")
                self.assertTrue(p.is_visible("#tm-mgr table"))
                self.assertTrue(p.is_visible("#tm-picks li"))
                self.assertGreaterEqual(p.locator("#tm-season-charts .tm-chart").count(), 3)
                self.assertTrue(p.is_visible("#tm-h2h table"))
                self.assertGreaterEqual(p.locator("#tm-trophies figure.trophy").count(), 1)
                self.assertGreaterEqual(p.locator("#tm-trophies article .snap-card-btn").count(), 1, "trophy Save image")
                self.assertGreaterEqual(p.locator("#tm-seasons details.tm-season").count(), 8)
                self.assertEqual(p.locator("#tm-seasons details.tm-season[open]").count(), 1)
                self.assertEqual(p.get_attribute("#tm-seasons details.tm-season[open]", "data-year"), str(json.loads(
                    (ROOT / "data/teams/index.json").read_text())["season"]))
                self.assertIn("Fresno State", p.inner_text("#tm-seasons details.tm-season[data-year='2021'] summary"))
                self.assertTrue(p.is_visible(".tm-draft li"))
                self.assertTrue(p.is_visible("#tm-tx .tm-tx-item"))
                self.assertEqual(p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), 0,
                                 "no sideways scroll")
                p.click("#tm-tx-sec .tm-more")
                self.assertGreater(p.locator("#tm-tx .tm-tx-item:visible").count(), 25)
                for el in p.query_selector_all("#tm-trophies figure.trophy img"):
                    el.scroll_into_view_if_needed()
                p.wait_for_function("[...document.querySelectorAll('#tm-trophies figure.trophy:not(.fallback) img')].every(i=>i.complete&&i.naturalWidth>0)")
                if OUT:
                    os.makedirs(OUT, exist_ok=True)
                    p.screenshot(path=os.path.join(OUT, f"team-{tag}.png"), full_page=True)

    def test_color_modes_and_team_override(self):
        p = self.open(f"reports/team.html?league={league_id('NCAA PAC 12')}&roster=7", 390)
        self.assertIn("tm-c-full", p.get_attribute("body", "class"), "team colours by default")
        sec = "#tm-roster-sec"
        bg = lambda: p.evaluate(f"getComputedStyle(document.querySelector('{sec}')).backgroundColor")  # noqa: E731
        self.assertEqual(bg(), "rgb(140, 29, 64)", "Arizona State maroon")
        chip = p.evaluate("(()=>{const c=getComputedStyle(document.querySelector('.tm-chip'));return [c.backgroundColor,c.color]})()")
        self.assertEqual(chip, ["rgb(255, 198, 39)", "rgb(140, 29, 64)"], "season label inverted")
        head = p.evaluate("(()=>{const c=getComputedStyle(document.querySelector('.tm-head'));return [c.backgroundColor,c.color]})()")
        self.assertEqual(head, ["rgb(255, 198, 39)", "rgb(140, 29, 64)"], "header block inverted")
        switch = p.get_by_role("switch", name="This team only")
        switch.click()
        self.assertEqual(switch.get_attribute("aria-checked"), "true")
        p.get_by_role("radio", name="Team", exact=True).press("ArrowRight")
        self.assertEqual(p.get_by_role("radio", name="Inverted").get_attribute("aria-checked"), "true")
        self.assertEqual(bg(), "rgb(255, 198, 39)", "Inverted mode uses Arizona State gold")
        p.reload()
        p.wait_for_selector("body[data-ready]", state="attached")
        self.assertIn("tm-c-inverted", p.get_attribute("body", "class"))
        switch.click()
        self.assertEqual(switch.get_attribute("aria-checked"), "false")
        self.assertEqual(bg(), "rgb(140, 29, 64)", "switching off restores the global mode")
        p.click("#tm-colors [data-c=frame]")
        self.assertIn("tm-c-frame", p.get_attribute("body", "class"))
        self.assertEqual(p.evaluate("getComputedStyle(document.querySelector('.tm-head')).backgroundColor"), "rgb(140, 29, 64)",
                         "Accent mode keeps the team-coloured header")
        self.assertNotEqual(bg(), "rgb(140, 29, 64)")
        p.click("#tm-colors [data-c=site]")
        p.reload()
        p.wait_for_selector("body[data-ready]", state="attached")
        self.assertIn("tm-c-site", p.get_attribute("body", "class"), "remembered on this device")
        self.assertEqual(p.get_attribute("#tm-colors [data-c=site]", "aria-checked"), "true")
        self.assertEqual(p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), 0)
        p.evaluate("localStorage.removeItem('ncaa180.teamColors')")

    def test_overview_saves_a_png(self):
        mw = league_id("NCAA MOUNTAIN WEST")
        p = self.open(f"reports/team.html?league={mw}&roster=4")
        p.evaluate("navigator.canShare = () => false")
        save = p.locator("#tm-over-sec > button.snap-btn")
        with p.expect_download(timeout=60000) as pending:
            save.click()
        download = pending.value
        self.assertIn("Overview", download.suggested_filename)
        self.assertEqual(download.path().read_bytes()[:8], bytes((137, 80, 78, 71, 13, 10, 26, 10)))

    def test_head_to_head_separates_regular_and_postseason_records(self):
        pac = league_id("NCAA PAC 12")
        p = self.open(f"reports/team.html?league={pac}&roster=7", 390)
        row = p.locator("#tm-h2h-t tbody tr").filter(has_text="California")
        self.assertEqual(row.locator("td").nth(0).inner_text(), "California")
        self.assertEqual(row.locator("td").nth(1).inner_text(), "3-5 (0-2)")
        self.assertIn("postseason records in parentheses", p.locator("#tm-h2h-sec .note").inner_text())

    def test_postseason_section_shows_latest_appearance_and_history(self):
        pac = league_id("NCAA PAC 12")
        p = self.open(f"reports/team.html?league={pac}&roster=7", 390)
        section = p.locator("#tm-post-sec")
        heading = section.get_by_role("button", name="Postseason")
        self.assertEqual(heading.get_attribute("aria-expanded"), "true")
        heading.click()
        self.assertFalse(section.locator("#tm-post").is_visible())
        self.assertEqual(heading.get_attribute("aria-expanded"), "false")
        heading.press("Enter")
        self.assertTrue(section.locator("#tm-post").is_visible())
        self.assertEqual(heading.get_attribute("aria-expanded"), "true")
        self.assertEqual(section.locator("details[open]").count(), 1)
        years = section.locator("details").evaluate_all("items => items.map(item => Number(item.dataset.year))")
        self.assertEqual(years, sorted(years, reverse=True))
        self.assertEqual(section.locator("details[open]").get_attribute("data-year"), str(years[0]))
        self.assertIn("National champion", section.locator("details[data-year='2025'] summary").inner_text())
        self.assertGreater(section.locator("details[open] tbody tr.post").count(), 0)
        self.assertEqual(section.locator("tbody tr.reg").count(), 0)
        older = section.locator("details[data-year='2024']")
        older.locator("summary").click()
        self.assertIn("Tangerine Bowl", older.locator("tbody").inner_text())
        p.evaluate("navigator.canShare = () => false")
        with p.expect_download(timeout=60000) as pending:
            section.locator("button.snap-btn").click()
        self.assertIn("Postseason", pending.value.suggested_filename)
        self.assertEqual(pending.value.path().read_bytes()[:8], bytes((137, 80, 78, 71, 13, 10, 26, 10)))

    def test_chart_hover_tooltip(self):
        p = self.open(f"reports/team.html?league={league_id('NCAA PAC 12')}&roster=7")
        hit = p.locator("#tm-season-charts .tm-chart .hit").first
        hit.hover()
        tip = p.locator("#tm-season-charts .tm-chart .tm-tip").first
        self.assertTrue(tip.is_visible())
        self.assertRegex(tip.inner_text(), r"20\d\d")

    def test_picker_shows_my_team(self):
        p = self.open("reports/team.html")
        self.assertIn("Set your team", p.inner_text(".tm-mine"))
        p.evaluate("localStorage.setItem('ncaa180.push', JSON.stringify({myTeam: 'ncaa180|Pac-12:7'}))")
        p.reload()
        p.wait_for_selector("body[data-ready]", state="attached")
        self.assertIn("Arizona State", p.inner_text(".tm-mine"))
        self.assertIn("roster=7", p.get_attribute(".tm-mine a", "href"))
        p.evaluate("localStorage.removeItem('ncaa180.push')")

    def test_override_survives_historical_url(self):
        current = league_id("NCAA MOUNTAIN WEST")
        old = league_id("NCAA MOUNTAIN WEST", 2021)
        p = self.open(f"reports/team.html?league={current}&roster=4")
        p.get_by_role("switch", name="This team only").click()
        p.get_by_role("radio", name="Inverted").click()
        p.goto(self.base + f"reports/team.html?league={old}&roster=4")
        p.wait_for_selector("body[data-ready]", state="attached")
        self.assertEqual(p.text_content(".tm-head h1"), "Air Force")
        self.assertIn(f"league={current}", p.url)
        self.assertIn("tm-c-inverted", p.get_attribute("body", "class"))
        self.assertEqual(p.get_by_role("switch", name="This team only").get_attribute("aria-checked"), "true")

    def test_color_controls_and_neutral_tables_at_supported_widths(self):
        teams = (("NCAA SEC", 11, "Alabama"), ("NCAA BIG 10", 11, "Iowa"), ("NCAA BIG 10", 12, "Michigan"))
        for conference, roster, name in teams:
            for width in (320, 390, 1280):
                for theme in ("light", "dark"):
                    with self.subTest(team=name, width=width, theme=theme):
                        p = self.open(f"reports/team.html?league={league_id(conference)}&roster={roster}", width, theme)
                        self.assertEqual(p.text_content(".tm-head h1"), name)
                        radios = p.locator("#tm-colors [role=radio]")
                        self.assertEqual(radios.all_text_contents(), ["Team", "Inverted", "Accent", "Site"])
                        for radio in radios.all():
                            radio.click()
                            self.assertTrue(p.locator("#tm-colors").evaluate("el => el.scrollWidth <= el.clientWidth"))
                            if radio.get_attribute("data-c") in ("full", "inverted"):
                                self.assertTrue(p.locator("#tm-mgr table").evaluate("""el =>
                                    getComputedStyle(el).backgroundColor ===
                                    getComputedStyle(document.querySelector('.tm-chart')).backgroundColor
                                """))
                                contrast = p.locator("#tm-mgr-sec h2").evaluate(r"""el => {
                                    const luminance = rgb => rgb.match(/\d+/g).map(Number)
                                        .map(v => v / 255)
                                        .map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
                                        .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
                                    const a = luminance(getComputedStyle(el).color);
                                    const b = luminance(getComputedStyle(el.parentElement).backgroundColor);
                                    return (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
                                }""")
                                self.assertGreaterEqual(contrast, 4.5)
                                self.assertTrue(p.locator(".tm-head img").evaluate("""el =>
                                    el.getAttribute('src') === (document.body.classList.contains('tm-c-full')
                                        ? el.dataset.logoInv : el.dataset.logo)
                                """))
                                p.wait_for_function("document.querySelector('.tm-head img')?.naturalWidth > 0")
                        p.close()

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
        self.assertEqual(p.locator("#tm-pick li a").count(), 204)
        self.assertEqual(p.locator("#tm-pick .tm-defunct a").count(), 24)
        p = self.open(f"reports/team.html?league={league_id('NCAA AMERICAN', 2019)}&roster=13")
        self.assertTrue(p.is_visible("#tm-error"))
        self.assertTrue(p.is_visible("#tm-pick a"))

    def test_defunct_team_page(self):
        p = self.open(f"reports/team.html?league={league_id('NCAA AMERICAN', 2019)}&roster=5", 390)
        self.assertEqual(p.text_content(".tm-head h1"), "Ohio")
        self.assertIn("Defunct", p.inner_text(".tm-head"))
        self.assertEqual(p.locator("#tm-roster-sec").count(), 0, "no current-roster section")
        self.assertEqual(p.get_attribute("#tm-seasons details.tm-season[open]", "data-year"), "2019")
        self.assertGreaterEqual(p.locator("#tm-trophies figure.trophy").count(), 1)
        self.assertEqual(p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth"), 0)
        if OUT:
            p.screenshot(path=os.path.join(OUT, "team-defunct-mobile.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
