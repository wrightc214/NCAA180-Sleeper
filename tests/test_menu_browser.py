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
                                       "as => as.map(a => [a.textContent.trim() || 'bell', a.hasAttribute('aria-current')])")

    def test_main_tabs_on_key_pages(self):
        for name, lit in (("scoreboard.html", "Games"), ("standings.html", "Standings"),
                          ("special.html", "Special Events"), ("week-05.html", "Awards")):
            with self.subTest(page=name):
                pg = self.page(name)
                t = self.tabs(pg)
                self.assertEqual([x[0] for x in t][:3], ["Awards", "Roster Map", "Standings"])
                self.assertEqual(t[-1][0], "bell")
                self.assertEqual([x[0] for x in t if x[1]], [lit])
                self.assertEqual([x[0] for x in t][-3:], ["Records", "About", "bell"])  # About public since #106
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
        self.assertIn("The Guillotine", pg.inner_text('nav.weeks.sub[data-row="special"]'))
        self.assertEqual(pg.locator('nav.weeks.sub img').count(), 1)
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


if __name__ == "__main__":
    unittest.main()
