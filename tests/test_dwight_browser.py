"""Dwight Fight browser smoke: desktop + narrow mobile, both theme preferences."""
import itertools
import json
import os
import sys
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dwight_fight as dw


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in Playwright")
class DwightFightBrowser(unittest.TestCase):
    def test_bracket_and_archive_responsive(self):
        from playwright.sync_api import sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        people = [{"user_id": str(i), "username": f"dwight{i}",
                   "display_name": f"Dwight {i}", "team": f"University of Test School {i}",
                   "league": "Sample", "league_id": "L", "roster_id": str(i)}
                  for i in range(1, 12)]
        sample = dw.draw(people, people, 17, 2026)
        sample["locked"] = True
        sample["status"] = "locked"
        scores = {w: {("L", str(i)): 110 + i + w / 100 for i in range(1, 12)} for w in range(14, 18)}
        dw.advance(sample, scores, {}, set(range(14, 18)))
        self.assertTrue(sample["champion"])
        body = json.dumps(sample)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True,
                                                     args=["--no-sandbox", "--disable-dev-shm-usage"])
                for width, theme in itertools.product((320, 390, 1280), ("light", "dark")):
                    with self.subTest(width=width, theme=theme):
                        page = browser.new_page(viewport={"width": width, "height": 900},
                                                color_scheme=theme, service_workers="block")
                        errors = []
                        page.on("pageerror", lambda ex: errors.append(str(ex)))
                        page.route("**/data/scoreboard/2026/dwight.json",
                                   lambda route: route.fulfill(status=200,
                                                               content_type="application/json",
                                                               body=body))
                        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
                        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
                        page.goto(f"http://127.0.0.1:{server.server_port}/reports/dwight-fight.html")
                        page.wait_for_function("document.querySelector('.dw-bracket') !== null")
                        self.assertFalse(errors, errors)
                        self.assertIn("Locked bracket", page.locator("#dw-status").inner_text())
                        self.assertEqual(page.locator(".dw-round").count(), 4)
                        self.assertTrue(page.locator(".dw-champion").is_visible())
                        self.assertEqual(page.locator(".dw-history").count(), 3)
                        self.assertFalse(page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"))
                        page.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
