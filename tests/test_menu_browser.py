"""Shared site menu in a real browser (todo-header-rebuild.md, 2026-11-17). Opt-in like the other
browser suites: RUN_SCOREBOARD_BROWSER_TESTS=1. Serves the repo and checks that menu.js fills the
placeholders on Games, Standings, Special Events and a week page, plus Dev view and the About dev panel."""
import functools
import http.server
import os
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1"


@unittest.skipUnless(RUN, "browser test (set RUN_SCOREBOARD_BROWSER_TESTS=1)")
class MenuBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
        handler.log_message = lambda *a: None
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}/reports/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()

    def page(self, name):
        pg = self.browser.new_page()
        self.errors = []
        pg.on("pageerror", lambda e: self.errors.append(str(e)))
        pg.route("**/config/push.json", lambda r: r.fulfill(status=404, body=""))  # no push prompt in tests
        pg.goto(self.base + name, wait_until="domcontentloaded")
        return pg

    def tabs(self, pg):
        return pg.eval_on_selector_all('nav.weeks[aria-label="Pages"] a',
                                       "as => as.map(a => [a.getAttribute('aria-label') || a.textContent.trim(), a.hasAttribute('aria-current')])")

    def test_main_tabs_on_key_pages(self):
        for name, lit in (("scoreboard.html", "Games"), ("standings.html", "Standings"),
                          ("special.html", "Special Events"), ("week-05.html", "Awards")):
            with self.subTest(page=name):
                pg = self.page(name)
                t = self.tabs(pg)
                self.assertEqual([x[0] for x in t][:3], ["Awards", "Roster Map", "Standings"])
                self.assertEqual(t[-1][0], "Notification settings")
                self.assertEqual([x[0] for x in t if x[1]], [lit])
                self.assertEqual([x[0] for x in t][-4:], ["Records", "About", "Accessibility", "Notification settings"])  # About public since #106; Accessibility since 2026-11-22
                icons = pg.eval_on_selector_all('nav.weeks[aria-label="Pages"] a.n180-icon', "as => as.map(a => [a.getAttribute('aria-label'), a.textContent.trim(), !!a.querySelector('svg')])")
                self.assertEqual(icons, [["About", "", True], ["Accessibility", "", True], ["Notification settings", "", True]])  # icon-only tabs (Accessibility public since 2026-11-22)
                self.assertEqual(self.errors, [])
                pg.close()

    def test_sub_rows(self):
        pg = self.page("week-05.html")
        rows = pg.eval_on_selector_all("nav.weeks.sub:not([hidden])",
                                       "ns => ns.map(n => [n.getAttribute('aria-label'), n.querySelector('[aria-current]')?.textContent])")
        self.assertEqual(rows[0][0], "Seasons")
        self.assertEqual(rows[1], ["Weeks", "Wk 5"])
        pg.close()
        pg = self.page("special.html")
        special = pg.inner_text('nav.weeks.sub[data-row="special"]')
        self.assertIn("The Guillotine", special)
        self.assertIn("Dwight Fight", special)  # public since 889a0a0 (CW, Nov 24)
        self.assertEqual(pg.locator('nav.weeks.sub[data-row="special"] img').count(), 2)
        pg.close()

    def test_sub_rows_below_header(self):
        # CW, 2026-11-20: sub-rows display directly below the page header, in their original order.
        for name, labels in (("week-05.html", ["Seasons", "Weeks"]), ("standings.html", ["Seasons"]),
                             ("poll-how.html", ["Poll pages"]), ("special.html", ["Special events", "Seasons"]),  # Seasons = guillotine-seasons (hidden unless Dev)
                             ("ccg-race.html", ["Selection Watch pages"]), ("selection-watch.html", ["Selection Watch pages"])):
            with self.subTest(page=name):
                pg = self.page(name)
                got = pg.evaluate("""() => {
                  const h = document.querySelector('header'), out = [];
                  let n = h.nextElementSibling;
                  while (n && n.matches('nav.weeks.sub')) { out.push(n.getAttribute('aria-label')); n = n.nextElementSibling; }
                  return {after: out, before: document.querySelectorAll('nav.weeks.sub:not(.n180-below)').length,
                          waiting: document.querySelectorAll('nav.weeks.sub.n180-wait').length};
                }""")
                self.assertEqual(got, {"after": labels, "before": 0, "waiting": 0})
                self.assertEqual(self.errors, [])
                pg.close()

    def test_dev_view_and_about_panel(self):
        pg = self.page("about.html")
        self.assertTrue(pg.locator("#devpanel").is_hidden())
        for _ in range(5):
            pg.click("#about-title")
        self.assertTrue(pg.locator("#devpanel").is_visible())
        self.assertEqual(pg.locator(".n180-devbar").count(), 0)
        pg.check("#dev-view")
        self.assertEqual(pg.locator(".n180-devbar").count(), 0)  # About is public: no "not public" bar
        pg.evaluate("""() => { NCAA180.menu.data.tabs.splice(1, 0, {id: 'wip', label: 'WIP', href: 'wip.html', state: 'hidden-dev'});
                              NCAA180.menu.render(true); }""")
        # Count the injected tab by name: other real tabs may also be hidden-dev (e.g. Transactions).
        dev = pg.locator('nav.weeks[aria-label="Pages"] a.n180-dev', has_text="WIP")
        self.assertEqual(dev.count(), 1)
        self.assertIn("DEV", dev.inner_text())
        pg.uncheck("#dev-view")
        self.assertEqual(pg.locator(".n180-devbar").count(), 0)
        self.assertEqual(pg.locator('nav.weeks[aria-label="Pages"] a.n180-dev').count(), 0)
        pg.check("#dev-tester")
        pg.wait_for_function("() => document.getElementById('dev-st').textContent.startsWith('Tester mode on')")
        self.assertTrue(pg.evaluate("JSON.parse(localStorage.getItem('ncaa180.push')).test"))
        self.assertEqual(self.errors, [])
        pg.close()

    def test_guillotine_replay(self):
        # 2025 replay (CW, 2026-11-24): Dev-only page; public viewers never see the Seasons row.
        pg = self.page("special.html")
        self.assertTrue(pg.locator('nav.weeks.sub[data-row="guillotine-seasons"]').is_hidden())
        pg.evaluate("localStorage.setItem('ncaa180.dev','1')")
        pg.goto(self.base + "guillotine-2025.html", wait_until="domcontentloaded")
        row = pg.locator('nav.weeks.sub[data-row="guillotine-seasons"]')
        self.assertTrue(row.is_visible())
        self.assertIn("2025 replay", row.inner_text())
        self.assertEqual(pg.locator(".n180-devbar").count(), 1)
        self.assertIn("Replay, not an official result", pg.inner_text(".gl-replay"))
        pg.wait_for_selector(".gl-champ")
        self.assertIn("Georgetown", pg.inner_text(".gl-champ"))
        self.assertEqual(pg.locator(".gl-weeks a").count(), 5)
        self.assertEqual(pg.locator(".fz-t .gl-r").count(), 11)  # week 17 final field
        self.assertEqual(self.errors, [])
        pg.close()


if __name__ == "__main__":
    unittest.main()
