"""Dwight Fight browser checks (task 5.18): the bracket component renders on every season's page at phone
and desktop widths in both themes, the longest real "username · role" never clips, and a drawn, in-progress
bracket (33 Dwights, six rounds) carries the live labels. Opt-in like the other browser checks:
RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_dwight_browser.py"""
import itertools
import os
import sys
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dwight_fight as dw  # noqa: E402

PAGES = {2026: "dwight-fight.html", **{y: f"dwight-fight-{y}.html" for y in (2025, 2024, 2023, 2022, 2021)}}
FIXTURE = "_dwight-fixture-live.html"

# every second line that would overflow its row: [text, overflow px]; '' rows (TBD) have no second line
CLIP_JS = """(scope) => [...document.querySelectorAll(scope + ' .bk-row:not(.tbd)')].filter(r => r.getClientRects().length || scope === '.bk-phone')
  .flatMap(r => { const nm = r.querySelector('.bk-nm'), out = [];
    for (const el of nm.children) { const over = Math.max(el.scrollWidth - el.clientWidth, el.getBoundingClientRect().right - nm.getBoundingClientRect().right);
      if (over > 0.5) out.push([el.textContent, over]); }
    return out; })"""


def fixture_page():
    """A drawn, locked bracket mid-tournament (weeks 12-15 final, week 16 live), written into reports/."""
    os.chdir(ROOT)
    import dwight_page as D
    people = [{"user_id": str(i), "username": f"dwight{i}", "display_name": f"Dwight {i}",
               "team": f"University of Test School {i}", "league": "Sample", "league_id": "L", "roster_id": str(i)}
              for i in range(1, 34)]
    b = dw.draw(people, people, 17, 2026)
    b["locked"], b["status"] = True, "locked"
    scores = {w: {("L", str(i)): 110 + i + w / 100 for i in range(1, 34)} for w in range(12, 18)}
    dw.advance(b, scores, {}, set(range(12, 16)))
    ev = D._from_json(b, "drawn")
    (ROOT / "reports" / FIXTURE).write_text(D.build_page(2026, ev, [], [], current=True, n_req=33), encoding="utf-8")
    return ev


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in Playwright")
class DwightFightBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        cls.ev = fixture_page()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/reports/"
        cls.pw = sync_playwright().start()
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
        cls.browser = cls.pw.chromium.launch(**({"executable_path": exe} if exe else {}),
                                             args=["--no-sandbox", "--disable-dev-shm-usage"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        (ROOT / "reports" / FIXTURE).unlink(missing_ok=True)

    def open(self, name, width, theme="light"):
        page = self.browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme, service_workers="block")
        errors = []
        page.on("pageerror", lambda ex: errors.append(str(ex)))
        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
        page.goto(self.base + name)
        page.wait_for_function("document.querySelector('.bk')?.dataset.ready==='1'")
        page.wait_for_timeout(300)
        self.addCleanup(page.close)
        self.addCleanup(lambda: self.assertEqual(errors, []))
        return page

    def test_every_season_renders_at_phone_and_desktop(self):
        from playwright.sync_api import expect
        for (year, name), width, theme in itertools.product(PAGES.items(), (320, 390, 1280), ("light", "dark")):
            if theme == "dark" and width == 390:
                continue
            with self.subTest(year=year, width=width, theme=theme):
                p = self.open(name, width, theme)
                banner = p.locator("header h1").get_by_role("img", name="Dwight Fight")
                expect(banner).to_have_attribute("src", "../assets/logos/Dwight%20Fight/Dwight%20Fight%20Banner.png")
                self.assertGreater(banner.evaluate("(img) => img.naturalWidth"), 0)
                if width >= 720:
                    expect(p.locator(".bk-desk")).to_be_visible()
                    expect(p.locator(".bk-phone")).to_be_hidden()
                    self.assertGreater(p.locator(".bk-desk .bk-g").count(), 0)
                    self.assertEqual(p.locator(".bk-desk .bk-rh b").all_text_contents(),
                                     ["First Round", "Quarterfinal", "Semifinal", "Final"])
                else:
                    expect(p.locator(".bk-phone")).to_be_visible()
                    expect(p.locator(".bk-desk")).to_be_hidden()
                    on = p.locator('.bk-col[aria-hidden="false"] .bk-card:not(.bk-bye)')
                    self.assertGreater(on.count(), 0)
                    expect(on.first).to_be_visible()
                # names and "username · role" never clip, on the visible layout
                self.assertEqual(p.evaluate(CLIP_JS, ".bk-desk" if width >= 720 else ".bk-phone"), [])
                self.assertFalse(p.evaluate("document.documentElement.scrollWidth > innerWidth"))
                self.assertEqual(p.locator(".bk-row").filter(has_text="BYE").count(), 0)
                expect(p.locator("nav.weeks.sub[data-row='dwight-seasons'] a")).to_have_text(
                    ["2026", "2025", "2024", "2023", "2022", "2021"])

    def test_longest_second_line_fits_every_phone_column(self):
        """The phone shows one round at a time: put each round in focus and check every row in it."""
        for year, name in PAGES.items():
            for width in (320, 390):
                with self.subTest(year=year, width=width):
                    p = self.open(name, width)
                    longest = p.evaluate("Math.max(...[...document.querySelectorAll('.bk-phone .bk-nm small')].map(s=>s.textContent.length))")
                    self.assertGreaterEqual(longest, 20)
                    for r in range(p.locator(".bk-phone .bk-tab").count()):
                        p.locator(".bk-phone .bk-tab").nth(r).click()
                        p.wait_for_timeout(420)
                        self.assertEqual(p.evaluate(CLIP_JS.replace("scope + ' .bk-row", "scope + ' .bk-col[aria-hidden=\"false\"] .bk-row"),
                                                    ".bk-phone"), [])

    def test_2023_byes_and_past_season_labels(self):
        from playwright.sync_api import expect
        p = self.open(PAGES[2023], 1280)
        r0 = p.locator('.bk-desk .bk-g[data-r="0"]')
        expect(r0).to_have_count(3)
        self.assertEqual(sorted(int(x) for x in r0.locator(".bk-sd").all_text_contents()), list(range(6, 12)))
        qf_seeds = {int(x) for x in p.locator('.bk-desk .bk-g[data-r="1"] .bk-sd').all_text_contents()}
        self.assertTrue({1, 2, 3, 4, 5} <= qf_seeds)
        expect(p.locator(".bk-desk .bk-nm small").filter(has_text="wrightc214 · Data")).not_to_have_count(0)
        expect(p.locator("#dw-status")).to_have_text("Final · 11 Dwights · Weeks 15–18")
        expect(p.locator(".bk-desk .bk-champ")).to_contain_text("2023 Dwight Fight Champion")
        expect(p.locator(".bk-desk .bk-champ .trophy")).to_have_count(1)
        # the second line keeps the username's case (not uppercased like the Playoff's conference)
        self.assertEqual(p.locator(".bk-desk .bk-nm small").first.evaluate("e=>getComputedStyle(e).textTransform"), "none")
        for y in (2024, 2025):
            q = self.open(PAGES[y], 390)
            expect(q.locator("#dw-season-note")).to_have_text(
                "Reconstructed: field = that season's poll voters; the event was likely not held.")
            expect(q.locator(".dw-champs > div").filter(has_text=str(y))).to_have_text(
                {2024: "2024 New Mexico*", 2025: "2025 Arizona State*"}[y])
        expect(q.locator(".dw-totals > div").first).to_have_text("Arizona State 3 (2022, 2023, 2025*)")

    def test_live_bracket_labels_and_save_image_menu(self):
        from playwright.sync_api import expect
        p = self.open(FIXTURE, 1280)
        expect(p.locator("#dw-status")).to_have_text("Locked bracket · 33 Dwights · Weeks 12–17")
        expect(p.locator(".bk-desk .bk-rh b")).to_have_text(
            ["First Round", "Round 2", "Round 3", "Quarterfinal", "Semifinal", "Final"])
        expect(p.locator(".bk-desk .bk-st")).to_contain_text("Unofficial · Live · updated")
        expect(p.locator('.bk-desk .bk-g[data-r="0"]')).to_have_count(1)  # 33 Dwights: one play-in game
        expect(p.locator(".bk-desk .bk-g.st-final")).to_have_count(1 + 16 + 8 + 4)
        expect(p.locator(".bk-desk .bk-row.lose")).to_have_count(1 + 16 + 8 + 4)
        p.locator("#bracket .snap-btn").click()
        labels = p.locator(".bk-menu input[name=bk-what]")
        self.assertEqual([labels.nth(i).get_attribute("value") for i in range(labels.count())], ["round-4", "full"])  # This round = the round in play
        expect(p.locator(".bk-menu input[name=bk-size]")).to_have_count(2)
        expect(p.locator("#champions .snap-btn")).to_have_count(1)  # every collapsible section saves an image
        ph = self.open(FIXTURE, 390)
        self.assertEqual(int(ph.eval_on_selector(".bk-phone", "e=>e.dataset.focus")), 4)  # the semifinal is next


if __name__ == "__main__":
    unittest.main()
