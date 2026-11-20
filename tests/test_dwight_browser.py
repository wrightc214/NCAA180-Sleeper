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
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dwight_fight as dw


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in Playwright")
class DwightFightBrowser(unittest.TestCase):
    def test_bracket_and_archive_responsive(self):
        from playwright.sync_api import expect, sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        people = [{"user_id": str(i), "username": f"dwight{i}",
                   "display_name": f"Dwight {i}", "team": f"University of Test School {i}",
                   "league": "Sample", "league_id": "L", "roster_id": str(i)}
                  for i in range(1, 33)]
        sample = dw.draw(people, people, 17, 2026)
        sample["locked"] = True
        sample["status"] = "locked"
        scores = {w: {("L", str(i)): 110 + i + w / 100 for i in range(1, 33)} for w in range(13, 18)}
        dw.advance(sample, scores, {}, set(range(13, 17)))
        in_progress_body = json.dumps(sample)
        dw.advance(sample, scores, {}, set(range(13, 18)))
        self.assertTrue(sample["champion"])
        body = json.dumps(sample)
        with TemporaryDirectory() as work:
            history_path = Path(work) / "Dwight_Historic.csv"
            historic = (ROOT / "data/Dwight_Historic.csv").read_text(encoding="utf-8")
            # Out of order, absent from the original archive, with zero and missing scores.
            history_path.write_text(
                historic.rstrip("\n") + "\n2024,1,Final,17,Extra A,1,Extra B,2,0,,Extra A,,Recorded\n",
                encoding="utf-8",
            )
            dw.write_history(2026, sample, history_path)
            history_body = history_path.read_text(encoding="utf-8")
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
                        page.add_init_script("localStorage.setItem('ncaa180.dev', '1')")
                        page.route("**/data/scoreboard/index.json",
                                   lambda route: route.fulfill(json={"season": 2026}))
                        page.route("**/data/scoreboard/2026/dwight.json",
                                   lambda route: route.fulfill(content_type="application/json", body=body))
                        page.route("**/data/Dwight_Historic.csv",
                                   lambda route: route.fulfill(content_type="text/csv", body=history_body))
                        page.route("https://fonts.googleapis.com/**", lambda route: route.abort())
                        page.route("https://fonts.gstatic.com/**", lambda route: route.abort())
                        page.goto(f"http://127.0.0.1:{server.server_port}/reports/dwight-fight.html")
                        title = page.locator("header h1")
                        expect(title).to_have_count(1)
                        expect(title).to_have_text("")
                        banner = title.get_by_role("img", name="Dwight Fight")
                        expect(banner).to_have_attribute("src", "../assets/logos/Dwight%20Fight/Dwight%20Fight%20Banner.png")
                        self.assertGreater(banner.evaluate("(img) => img.naturalWidth"), 0)
                        expect(page.locator("#dw-status")).to_contain_text("Locked bracket")
                        rounds = page.locator(".dw-round h2")
                        names = ["First Round", "Round 2", "Quarterfinal", "Semifinal", "Final"]
                        expect(rounds).to_have_text([
                            f"{name} · Wk {i + 12} · PS{i}" for i, name in enumerate(names, 1)
                        ])
                        expect(page.locator(".dw-champion")).to_be_visible()
                        archive = page.locator(".dw-history")
                        summaries = archive.locator("summary")
                        expect(summaries).to_have_text([
                            "2026 · 31 games", "2024 · 1 game", "2023 · 10 games",
                            "2022 · 15 games", "2021 · 15 games",
                        ])
                        summaries.first.click()
                        expect(archive.first.locator("h3")).to_have_text([
                            f"{name} · Week {i + 12}" for i, name in enumerate(names, 1)
                        ])
                        summaries.nth(1).click()
                        expect(archive.nth(1).locator(".dw-hgame b")).to_have_text(["0.00", "—"])
                        summaries.last.click()
                        historic_scores = archive.last.locator(".dw-hgame b").all_text_contents()
                        self.assertIn("80.50", historic_scores)
                        self.assertIn("138.00", historic_scores)
                        self.assertFalse(page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"))
                        if width == 390 and theme == "light":
                            page.unroute("**/data/scoreboard/2026/dwight.json")
                            page.route("**/data/scoreboard/2026/dwight.json",
                                       lambda route: route.fulfill(content_type="application/json",
                                                                   body=in_progress_body))
                            page.reload()
                            expect(rounds.last).to_have_text("Final · Wk 17 · PS5")
                            expect(page.locator(".dw-champion")).to_have_count(0)
                            expect(summaries).to_have_text([
                                "2024 · 1 game", "2023 · 10 games", "2022 · 15 games", "2021 · 15 games",
                            ])
                        self.assertFalse(errors, errors)
                        page.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
