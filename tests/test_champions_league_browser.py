"""Special Events -> Champions League pages (2026-11-21). Opt-in like the other browser checks:
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m unittest tests/test_champions_league_browser.py
Uses the committed data (data/scoreboard/<season>/champions-league.json). Screenshots go to $CL_SHOTS
(a folder) when set. $PW_CHROME = a Chrome/Chromium binary when Playwright's own browser isn't installed."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "cl-standings": ["Standings", "Pts", "All-play"],
    "cl-schedule": ["Schedule", "Pod 1"],
    "cl-scoreboard": ["Pods", "Pod 11"],
    "cl-field": ["How the field was chosen", "Teams per conference", "Final Four"],
    "cl-selection": ["Projected field", "Projected"],
    "cl-rules": ["Pod points", "How the field is chosen", "Triad Cup"],
}


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in browser checks")
class ChampionsLeagueBrowserTests(unittest.TestCase):
    def test_pages_render(self):
        from playwright.sync_api import sync_playwright
        index = json.loads((ROOT / "data/scoreboard/index.json").read_text())
        data = json.loads((ROOT / f"data/scoreboard/{index['season']}/champions-league.json").read_text())
        shots = os.environ.get("CL_SHOTS")

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                kw = {"executable_path": os.environ["PW_CHROME"]} if os.environ.get("PW_CHROME") else {}
                b = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"], **kw)
                for width in (1300, 400, 390, 320):
                    for page, needles in PAGES.items():
                        with self.subTest(page=page, width=width):
                            ctx = b.new_context(viewport={"width": width, "height": 1000})
                            pg = ctx.new_page()
                            errors = []
                            pg.on("pageerror", lambda e: errors.append(str(e)))
                            pg.goto(f"http://127.0.0.1:{server.server_port}/reports/{page}.html")
                            pg.wait_for_timeout(800)
                            text = pg.inner_text("body")
                            self.assertEqual(errors, [])
                            # Site rule: no sideways page scroll; wide tables scroll inside their section.
                            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth - innerWidth"), 0)
                            self.assertFalse(pg.is_visible("#cl-error"), text[:300])
                            for n in needles:
                                self.assertIn(n.lower(), text.lower())
                            if page == "cl-standings":
                                rows = pg.locator("#cl-table tbody tr").count()
                                self.assertEqual(rows, len(data["teams"]))
                            if page == "cl-field":
                                self.assertEqual(pg.locator("#cl-field tbody tr").count(), len(data["teams"]))
                            if page != "cl-rules" and data.get("dev"):
                                self.assertTrue(pg.is_visible("#cl-banner"))
                            if shots:
                                os.makedirs(shots, exist_ok=True)
                                pg.screenshot(path=os.path.join(shots, f"{page}-{width}.png"), full_page=True)
                            ctx.close()
                b.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
