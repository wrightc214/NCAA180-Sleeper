"""Opt-in browser acceptance for the unlisted Selection Watch page.
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest tests/test_selection_watch_browser.py
Uses only local static assets; 2025 and provisional 2026 previews make no Sleeper/ESPN requests.
"""
import json
import os
from pathlib import Path
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in browser tests")
class SelectionWatchBrowser(unittest.TestCase):
    def test_historical_and_provisional_board(self):
        from playwright.sync_api import sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                for preview, rows in (("2025", 6), ("provisional", None)):
                    for width in (1150, 390):
                        with self.subTest(preview=preview, width=width):
                            page = browser.new_page(viewport={"width": width, "height": 1100},
                                                    service_workers="block")
                            errors = []
                            page.on("pageerror", lambda ex: errors.append(str(ex)))
                            page.route("https://api.sleeper.app/**", lambda r: r.abort())
                            page.route("https://site.api.espn.com/**", lambda r: r.abort())
                            page.route("https://fonts.googleapis.com/**", lambda r: r.abort())
                            page.route("https://fonts.gstatic.com/**", lambda r: r.abort())
                            page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?preview={preview}")
                            page.wait_for_function(
                                "marker => document.getElementById('sw-updated').textContent.includes(marker)",
                                arg="Historical replay" if preview == "2025" else "Updated", timeout=60000,
                            )
                            self.assertEqual(errors, [])
                            self.assertIn("UNOFFICIAL", page.locator("#sw-status").inner_text().upper())
                            if preview == "provisional":
                                self.assertIn("PROVISIONAL", page.locator("#sw-status").inner_text().upper())
                                self.assertEqual(page.get_by_role("link", name="View game").count(), 0)
                            if rows:
                                self.assertEqual(page.locator(".sw-pair").count(), rows)
                                self.assertIn("2 steals", page.locator("#sw-status").inner_text())
                                self.assertEqual(page.locator(".sw-pair.cut").count(), 1)
                                self.assertGreater(page.locator(".sw-pair .sw-team.admitted").count(), 0)
                                self.assertNotIn("Updated", page.locator("#sw-status").inner_text())
                            for sort in ("chance", "margin"):
                                page.select_option("#sw-sort", sort)
                                layout = page.evaluate("""() => ({
                                    viewport: innerWidth,
                                    page: document.documentElement.scrollWidth,
                                    boardRight: Math.max(...[...document.querySelectorAll(
                                        '.sw-page header, #sw-status, .sw-head > :last-child, .sw-pair > :last-child'
                                    )].map(el => el.getBoundingClientRect().right))
                                })""")
                                self.assertLessEqual(layout["page"], layout["viewport"], layout)
                                self.assertLessEqual(layout["boardRight"], layout["viewport"], layout)
                            self.assertEqual(page.locator(".sw-pair.cut").count(), 1 if rows else page.locator(".sw-pair.cut").count())
                            self.assertTrue(page.locator("#sw-noimpact").count())
                            page.click("#sw-collapse")
                            self.assertEqual(page.evaluate("[...document.querySelectorAll('details.sw-section')].filter(d => d.open).length"), 0)
                            page.click("#sw-collapse")
                            self.assertEqual(page.evaluate("[...document.querySelectorAll('details.sw-section')].filter(d => d.open).length"), 5)
                            if preview == "2025" and width == 390:
                                self.assertTrue(page.locator("#sw-board button.sw-save").is_visible())
                            page.close()
                browser.close()
        finally:
            server.shutdown()

    def test_live_route_reuses_games_inputs(self):
        """Mock full Week 12 Games feeds to exercise all 15 CCGs without production requests."""
        from playwright.sync_api import sync_playwright
        import copy
        baseline = json.loads((ROOT / "data/scoreboard/2026/week-06.json").read_text())
        index = json.loads((ROOT / "data/scoreboard/index.json").read_text())
        fixture = json.loads((ROOT / "tests/fixtures/scoreboard-week06.json").read_text())
        preview = json.loads((ROOT / "reports/postseason/selection-watch-provisional-2026.json").read_text())
        preview.pop("provisional")
        preview["note"] = "Synthetic CCG browser test only · Unofficial"
        ix = {**index, "week": 12, "weeks": sorted(set(index["weeks"] + [12]))}
        odds = []
        for g in preview["ccg"]:
            lid, ra = g["a"].split("|")
            _, rb = g["b"].split("|")
            odds.append({"LeagueID": lid, "RosterID": ra, "OpponentRosterID": rb, "WinPct": "60",
                         "Proj": "125", "OppProj": "120"})
        base = {**baseline, "week": 12, "odds": odds}
        sample = fixture["rosters"]
        def matchup():
            out = []
            for rid in range(1, 13):
                r = copy.deepcopy(sample[(rid - 1) % len(sample)])
                r["roster_id"] = rid
                r["matchup_id"] = (rid + 1) // 2
                r["points"] = 0
                r["players_points"] = {str(k): 0 for k in (r.get("players") or [])}
                out.append(r)
            return out
        nflteams = {x["team"] for x in baseline.get("player_info", {}).values() if x.get("team")}
        espn = {"season": {"year": 2026}, "week": {"number": 12}, "events": [{
            "id": "mock", "date": "2026-11-27T01:15:00Z",
            "status": {"period": 0, "displayClock": "0:00",
                       "type": {"state": "pre", "completed": False}},
            "competitions": [{"competitors": [{"team": {"abbreviation": t}} for t in nflteams]}]}]}

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                page = browser.new_page(viewport={"width": 1000, "height": 1200}, service_workers="block")
                errors = []
                fetched = set()
                page.on("pageerror", lambda e: errors.append(str(e)))
                def sleeper(route):
                    u = route.request.url
                    if "/matchups/" in u:
                        fetched.add(u.split("/league/")[1].split("/")[0])
                        payload = matchup()
                    elif "/stats/" in u:
                        payload = fixture["stats"]
                    else:
                        payload = {"scoring_settings": fixture["scoring"]}
                    route.fulfill(content_type="application/json", body=json.dumps(payload))
                page.route("https://api.sleeper.app/**", sleeper)
                page.route("https://site.api.espn.com/**", lambda r: r.fulfill(content_type="application/json", body=json.dumps(espn)))
                page.route("https://fonts.googleapis.com/**", lambda r: r.abort())
                page.route("https://fonts.gstatic.com/**", lambda r: r.abort())
                page.route("**/postseason/selection-watch.json",
                           lambda r: r.fulfill(content_type="application/json", body=json.dumps(preview)))
                page.route("**/scoreboard/index.json",
                           lambda r: r.fulfill(content_type="application/json", body=json.dumps(ix)))
                # First load with no usable odds for one game. Then restore the valid
                # baseline and finally send a blank value, which Games coerces to zero.
                active_base = {**base, "odds": odds[1:]}
                page.route("**/2026/week-12.json",
                           lambda r: r.fulfill(content_type="application/json", body=json.dumps(active_base)))
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html")
                page.wait_for_function("document.getElementById('sw-error').textContent.includes('CCG win chance unavailable')")
                self.assertIn("no verified current probabilities", page.locator("#sw-error").inner_text())
                self.assertEqual(page.locator("#sw-board .sw-pair").count(), 0)
                page.select_option("#sw-sort", "margin")
                self.assertEqual(page.locator("#sw-board .sw-pair").count(), 0)
                self.assertTrue(page.locator("#sw-board button.sw-save").is_disabled())

                active_base = base
                page.click("#sw-refresh")
                page.wait_for_function("document.getElementById('sw-updated').textContent.startsWith('Updated')", timeout=90000)
                self.assertEqual(errors, [])
                self.assertEqual(len(fetched), 15)
                self.assertEqual(page.locator("#sw-board .sw-pair").count() > 0, True)
                self.assertIn("UNOFFICIAL", page.locator("#sw-status").inner_text().upper())
                self.assertNotIn("PROVISIONAL", page.locator("#sw-status").inner_text().upper())
                self.assertTrue(page.locator("#sw-board button.sw-save").is_enabled())
                verified = page.locator("#sw-board-rows").inner_html()
                verified_timestamp = page.locator("body").get_attribute("data-snap-time")

                active_base = {**base, "odds": [{**odds[0], "WinPct": ""}, *odds[1:]]}
                page.click("#sw-refresh")
                page.wait_for_function("document.getElementById('sw-error').textContent.includes('last verified data')")
                self.assertEqual(page.locator("#sw-board-rows").inner_html(), verified)
                self.assertEqual(page.locator("body").get_attribute("data-snap-time"), verified_timestamp)
                browser.close()
        finally:
            server.shutdown()
