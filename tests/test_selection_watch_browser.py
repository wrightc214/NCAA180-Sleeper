"""Opt-in browser acceptance for the unlisted Selection Watch page.
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest tests/test_selection_watch_browser.py
Uses only local static assets; 2025 and provisional 2026 previews make no Sleeper/ESPN requests.
"""
import itertools
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
                    for width, theme in itertools.product((320, 390, 1280), ("light", "dark")):
                        with self.subTest(preview=preview, width=width, theme=theme):
                            page = browser.new_page(viewport={"width": width, "height": 1100},
                                                    service_workers="block", color_scheme=theme)
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
                            before = page.locator("#sw-board").evaluate("""board => [0,1].map(i =>
                                [...board.querySelectorAll('.sw-cut-row')].map(r => r.children[i].textContent))""")
                            page.locator("#sw-sort").click()
                            self.assertEqual(page.locator("#sw-sort").get_attribute("aria-pressed"), "true")
                            after = page.locator("#sw-board").evaluate("""board => [0,1].map(i =>
                                [...board.querySelectorAll('.sw-cut-row')].map(r => r.children[i].textContent))""")
                            self.assertEqual(after, [column[::-1] for column in before])
                            self.assertIn("UNOFFICIAL", page.locator("#sw-status").inner_text().upper())
                            if preview == "provisional":
                                self.assertIn("PROVISIONAL", page.locator("#sw-status").inner_text().upper())
                                self.assertEqual(page.get_by_role("link", name="View game").count(), 0)
                            if rows:
                                self.assertGreater(page.locator(".sw-cut-row").count(), 0)
                                self.assertIn("steals confirmed", page.locator("#sw-status").inner_text())
                                self.assertEqual(page.locator(".sw-cut-line").count(), 1)
                                self.assertGreater(page.locator(".sw-cut-row .sw-team.admitted").count(), 0)
                                self.assertTrue(page.evaluate("""() => [...document.querySelectorAll('#sw-board .sw-cut-row')]
                                    .every(row => row.querySelectorAll('.sw-team.admitted').length <= 1)"""))
                                self.assertNotIn("Updated", page.locator("#sw-status").inner_text())
                            layout = page.evaluate("""() => ({
                                viewport: innerWidth,
                                page: document.documentElement.scrollWidth,
                                boardRight: Math.max(...[...document.querySelectorAll(
                                    '.sw-page header, #sw-status, .sw-head > :last-child, .sw-cut-row > :last-child'
                                )].map(el => el.getBoundingClientRect().right))
                            })""")
                            self.assertLessEqual(layout["page"], layout["viewport"], layout)
                            self.assertLessEqual(layout["boardRight"], layout["viewport"], layout)
                            self.assertTrue(page.locator("#sw-noimpact").count())
                            page.click("#sw-collapse")
                            self.assertEqual(page.evaluate("[...document.querySelectorAll('#sw-content details.sw-section')].filter(d => !d.hidden && d.open).length"), 0)
                            page.click("#sw-collapse")
                            self.assertEqual(page.evaluate("[...document.querySelectorAll('#sw-content details.sw-section')].filter(d => !d.hidden && d.open).length"), (5 if preview == "2025" else 6) + int(page.locator("#sw-playins").is_visible()))
                            if preview == "provisional":
                                pick = page.locator("#sw-picks select").first
                                pick.select_option(index=1)
                                self.assertIn("WHAT-IF", page.locator("#sw-whatif-banner").inner_text())
                                page.locator("#sw-reset-picks").click()
                                self.assertFalse(page.locator("#sw-whatif-banner").is_visible())
                            if preview == "2025" and width == 390:
                                self.assertTrue(page.locator("#sw-board button.sw-save").is_visible())
                            if preview == "2025":
                                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?season=2025")
                                page.locator("#sw-final-playins").wait_for(state="visible")
                                self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))
                            page.close()
                page = browser.new_page(viewport={"width": 390, "height": 1100}, service_workers="block")
                page.route("https://fonts.googleapis.com/**", lambda r: r.abort())
                page.route("https://fonts.gstatic.com/**", lambda r: r.abort())
                requests = []
                page.on("request", lambda req: requests.append(req.url))
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html")
                page.select_option("#sw-season", "2020")
                page.get_by_role("button", name="View season").click()
                page.locator("#sw-final").wait_for(state="visible")
                self.assertTrue(page.url.endswith("?season=2020"))
                self.assertIn("FINAL RESULTS", page.locator("#sw-final-status").inner_text())
                self.assertIn("Campbell", page.locator("#sw-final-status").inner_text())
                self.assertEqual(page.locator("#sw-final-field li").count(), 32)
                self.assertEqual(page.locator("#sw-final-ccg tbody tr").count(), 15)
                self.assertFalse(page.locator("#sw-refresh").is_visible())
                archive = page.locator("#sw-final")
                open_sections = archive.locator("details[open]:not([hidden])")
                self.assertEqual(open_sections.count(), 3)
                archive.get_by_role("button", name="Collapse all").click()
                self.assertEqual(open_sections.count(), 0)
                archive.get_by_role("button", name="Expand all").click()
                self.assertEqual(open_sections.count(), 3)
                self.assertTrue(archive.get_by_role("button", name="Collapse all").is_visible())
                self.assertTrue(page.get_by_text("Conf.", exact=True).is_visible())
                big_sky = page.locator("#sw-final-ccg tbody tr").filter(has_text="Big Sky")
                self.assertIn("222.08†", big_sky.inner_text())
                self.assertIn("144.60†", big_sky.inner_text())
                self.assertIn("Standard scoring: 220.08", big_sky.inner_text())
                self.assertIn("Standard scoring: 146.60", big_sky.inner_text())
                for section_id in ("sw-final-ccg-section", "sw-final-field-section"):
                    section = page.locator("#" + section_id)
                    summary = section.locator("summary")
                    save = summary.get_by_role("button", name="Save image")
                    self.assertTrue(save.is_enabled())
                    summary.click(position={"x": 12, "y": 12})
                    self.assertIsNone(section.get_attribute("open"))
                    with page.expect_download(timeout=30000) as pending:
                        save.click()
                    download = pending.value
                    self.assertIn(f"2020-{section_id}", download.suggested_filename)
                    self.assertEqual(download.path().read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
                    self.assertIsNone(section.get_attribute("open"))
                    summary.click(position={"x": 12, "y": 12})
                    self.assertIsNotNone(section.get_attribute("open"))
                self.assertFalse(page.evaluate("document.documentElement.scrollWidth > innerWidth"))
                self.assertIn("No checkpoints recorded", page.locator("#sw-final-field").inner_text())
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?season=2025&timeline=sample")
                page.locator("#sw-final").wait_for(state="visible")
                self.assertIn("SAMPLE TIMELINE", page.locator("#sw-final-field").inner_text())
                self.assertIn("UNLV", page.locator(".sw-timeline").inner_text())
                board_text = page.locator("#sw-final-cut").inner_text()
                self.assertIn("BID THIEVES", board_text)
                self.assertIn("Last at-large bid: #29", board_text)
                self.assertIn("Cut starts at #31 · 1 play-in below", board_text)
                self.assertNotIn("Georgia Southern", board_text)
                self.assertNotIn("UTEP", board_text)
                playin = page.locator("#sw-final-playins")
                self.assertIn("Georgia Southern", playin.inner_text())
                self.assertIn("UTEP", playin.inner_text())
                self.assertIn("Play-in winner", playin.inner_text())
                self.assertTrue(playin.get_by_role("button", name="Save image").is_enabled())
                playin.locator("summary").click(position={"x": 12, "y": 12})
                self.assertIsNone(playin.get_attribute("open"))
                with page.expect_download(timeout=30000) as pending:
                    playin.get_by_role("button", name="Save image").click()
                self.assertIn("2025-sw-final-playins", pending.value.suggested_filename)
                self.assertIsNone(playin.get_attribute("open"))
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?season=2024")
                page.locator("#sw-final").wait_for(state="visible")
                self.assertIn("Last at-large bid: #27", page.locator("#sw-final-cut").inner_text())
                self.assertIn("Eastern Kentucky", page.locator("#sw-final-playins").inner_text())
                self.assertIn("Chattanooga", page.locator("#sw-final-playins").inner_text())
                self.assertNotIn("‡", page.locator("#sw-final").inner_text())
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?season=2022")
                page.locator("#sw-final").wait_for(state="visible")
                cut_text = page.locator("#sw-final-cut").inner_text()
                self.assertIn("left out by entry error", page.locator('#sw-final-cut [data-at-large="Texas Tech"]').inner_text())
                self.assertIn("in field by entry error", page.locator('#sw-final-cut [data-at-large="Central Michigan"]').inner_text())
                self.assertIn("‡ Bracket entry error", cut_text)
                self.assertIn("Last at-large bid: #25", cut_text)
                for ranking in (False, True):
                    if ranking:
                        page.locator("#sw-final-sort").click()
                    boundary = page.locator("#sw-final-cut .sw-cut-line").evaluate("""line =>
                        [line.previousElementSibling, line.nextElementSibling].map(
                            row => row.querySelector('[data-at-large]').dataset.atLarge)""")
                    self.assertEqual(boundary, ["Brown", "Central Michigan"] if ranking else ["Central Michigan", "Brown"])
                self.assertIn("Above cut", page.locator('#sw-final-cut [data-at-large="Brown"]').inner_text())
                self.assertIn("Central Michigan ‡", page.locator("#sw-final-field").inner_text())
                self.assertEqual(page.evaluate("document.documentElement.scrollWidth - innerWidth"), 0)
                self.assertTrue(page.evaluate("""() => document.querySelector('.sw-page nav').compareDocumentPosition(
                    document.querySelector('.sw-page header')) & Node.DOCUMENT_POSITION_FOLLOWING"""))
                self.assertFalse(page.locator("#sw-discord-draft").is_visible())
                self.assertFalse(any("api.sleeper.app" in url or "site.api.espn.com" in url for url in requests))
                page.close()
                page = browser.new_page(viewport={"width": 390, "height": 1100}, service_workers="block")
                page.route("https://fonts.googleapis.com/**", lambda r: r.abort())
                page.route("https://fonts.gstatic.com/**", lambda r: r.abort())
                replay = json.loads((ROOT / "reports/postseason/selection-watch-2025.json").read_text())
                play_id, = replay["play_ins"]
                play_game = next(g for g in replay["ccg"] if g["id"] == play_id)
                play_game["winner"] = ""
                ute = next(t["k"] for t in replay["order"] if t["team"] == "UTEP")
                page.route("**/postseason/selection-watch-2025.json",
                           lambda r: r.fulfill(content_type="application/json", body=json.dumps(replay)))
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/selection-watch.html?preview=2025")
                page.locator("#sw-playins").wait_for(state="visible")
                board_before = page.locator("#sw-board-rows").inner_html()
                page.locator("#sw-whatif summary").click(position={"x": 10, "y": 10})
                page.locator("#sw-picks select").select_option(ute)
                self.assertIn("UTEP wins", page.locator("#sw-whatif-banner").inner_text())
                self.assertIn("Play-in winner", page.locator("#sw-playin-rows").get_by_text("UTEP").locator("..").inner_text())
                self.assertIn("2 steals confirmed", page.locator("#sw-status").inner_text())
                self.assertEqual(board_before, page.locator("#sw-board-rows").inner_html())
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
                self.assertEqual(page.locator("#sw-board .sw-cut-row").count(), 0)
                self.assertTrue(page.locator("#sw-board button.sw-save").is_disabled())

                active_base = base
                page.click("#sw-refresh")
                page.wait_for_function("document.getElementById('sw-updated').textContent.startsWith('Updated')", timeout=90000)
                self.assertEqual(errors, [])
                self.assertEqual(len(fetched), 15)
                self.assertEqual(page.locator("#sw-board .sw-cut-row").count() > 0, True)
                self.assertIn("UNOFFICIAL", page.locator("#sw-status").inner_text().upper())
                self.assertNotIn("PROVISIONAL", page.locator("#sw-status").inner_text().upper())
                self.assertTrue(page.locator("#sw-board button.sw-save").is_enabled())
                draft = page.locator("#sw-discord-draft")
                self.assertFalse(draft.is_visible())
                for enabled in (True, False):
                    page.evaluate("""enabled => {
                        window.NCAA180.menu.setDev(enabled);
                        window.dispatchEvent(new StorageEvent('storage', {key: 'ncaa180.dev'}));
                    }""", enabled)
                    self.assertEqual(draft.is_visible(), enabled)
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
