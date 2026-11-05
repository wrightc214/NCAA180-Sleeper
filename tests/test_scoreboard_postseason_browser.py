"""Postseason weeks 13+ on the Games page: cross-league games, NIT group card (2026-11-04). Opt-in like the others."""
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest
from urllib.parse import urlparse, parse_qs


@unittest.skipUnless(os.environ.get('RUN_SCOREBOARD_BROWSER_TESTS') == '1', 'opt-in browser checks')
class PostseasonBrowserTests(unittest.TestCase):
    def test_postseason_week(self):
        from playwright.sync_api import sync_playwright
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'tests/fixtures/scoreboard-week06.json').read_text())
        base6 = json.loads((root / 'data/scoreboard/2026/week-06.json').read_text())
        index = json.loads((root / 'data/scoreboard/index.json').read_text())
        L = list(index['leagues'])
        side = lambda l, r, seed='', pct=50: {'LeagueID': L[l], 'RosterID': str(r), 'Team': '', 'Seed': seed, 'Rec': '9-2', 'Proj': 120.0, 'WinPct': pct}  # noqa: E731
        games = [{'id': '2026-P-1', 'round': 'Playoff', 'stage': '', 'bowl': '', 'playoff_round': '1', 'sides': [side(0, 1, '1', 70), side(1, 2, '32', 30)]},
                 {'id': '2026-P-31', 'round': 'Playoff', 'stage': '', 'bowl': '', 'playoff_round': '5', 'sides': [side(2, 1, '2', 55), side(3, 2, '3', 45)]},
                 {'id': '2026-B-1', 'round': 'Bowl', 'stage': '', 'bowl': 'Rose Bowl', 'playoff_round': '', 'sides': [side(4, 3, '', 60), side(5, 4, '', 40)]},
                 {'id': '2026-N-A', 'round': 'NIT', 'stage': 'Opening Groups', 'bowl': '', 'playoff_round': '',
                  'sides': [side(6, 5, '', 40), side(7, 6, '', 30), side(8, 7, '', 20), side(9, 8, '', 10)]}]
        base = {**base6, 'week': 13, 'odds': [], 'event': 'postseason', 'games': games}
        idx = {**index, 'week': 13, 'weeks': index['weeks'] + [13]}
        teams = {p['team'] for p in base6['player_info'].values() if p['team']}

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
                for width in (1300, 400):
                    with self.subTest(width=width):
                        page = b.new_page(viewport={'width': width, 'height': 1200}, service_workers='block')
                        page.add_init_script("try{sessionStorage.setItem('ncaa180.push.snooze','1')}catch(e){}")
                        errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
                        fetched = []

                        def api(route):
                            u = route.request.url
                            if '/matchups/' in u:
                                fetched.append(u.split('/league/')[1].split('/')[0]); data = copy.deepcopy(fixture['rosters'])
                            elif '/stats/' in u: data = fixture['stats']
                            elif u.endswith('/users') or u.endswith('/rosters'): data = []
                            else: data = {'scoring_settings': fixture['scoring']}
                            route.fulfill(content_type='application/json', body=json.dumps(data))

                        def espn(route):
                            data = {'season': {'year': 2026}, 'week': {'number': 13}, 'events': [{'id': 'x', 'date': '2026-12-01T00:15:00Z', 'status': {'period': 4, 'displayClock': '0:00', 'type': {'state': 'post', 'completed': True}}, 'competitions': [{'competitors': [{'team': {'abbreviation': t}} for t in teams]}]}]}
                            route.fulfill(content_type='application/json', body=json.dumps(data))
                        page.route('https://api.sleeper.app/**', api)
                        page.route('https://site.api.espn.com/**', espn)
                        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
                        page.route('https://fonts.gstatic.com/**', lambda r: r.abort())
                        page.route('**/scoreboard/index.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps(idx)))
                        page.route('**/week-13.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps(base)))
                        page.goto(f'http://127.0.0.1:{server.server_port}/reports/scoreboard.html?week=13')
                        page.wait_for_function("document.getElementById('updated')?.textContent.startsWith('Updated')", timeout=30000)
                        secs = page.locator('h3.sec').all_inner_texts()
                        self.assertEqual([s.split()[0].upper() for s in secs], ['PLAYOFF', 'BOWLS', 'NIT'])
                        self.assertEqual(sorted(set(fetched)), sorted(L[:10]))  # only leagues in games
                        self.assertEqual(page.locator('.gotw .gotw-badge').count(), 1)  # National Championship
                        self.assertEqual(page.locator('.mini-match.grp .score-row').count() >= 4, True)
                        self.assertEqual(page.locator('.mini-match.grp .score-row.out').count(), 3)  # final: 3 can't advance
                        self.assertIn('POSTSEASON WEEK 1', page.locator('h1').inner_text().upper())
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                        if os.environ.get('SCOREBOARD_SCREENSHOTS'):
                            d = Path(os.environ['SCOREBOARD_SCREENSHOTS']); d.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(d / f'post-{width}.png'), full_page=True)
                        # single-game pages
                        for gid, n in (('2026-B-1', 2), ('2026-P-31', 2), ('2026-N-A', 4)):
                            page.goto(f'http://127.0.0.1:{server.server_port}/reports/scoreboard.html?week=13&post={gid}&overview=all')
                            page.wait_for_function("document.getElementById('updated')?.textContent.startsWith('Updated')", timeout=30000)
                            if n == 2:
                                self.assertEqual(page.locator('.big').count(), 2)
                            else:
                                self.assertEqual(page.locator('.gr').count(), 4)
                                self.assertEqual(page.locator('.gr.out').count(), 3)
                                self.assertEqual(page.locator('.gcols').is_visible(), width >= 1000)
                            alts = page.locator('.mid .gbadge').evaluate_all('e=>e.map(x=>x.alt)')
                            want = {'2026-B-1': ['Rose Bowl'], '2026-P-31': ['National Championship', 'Game of the Week'], '2026-N-A': ['NIT']}[gid]
                            self.assertEqual(alts, want)
                            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                            if os.environ.get('SCOREBOARD_SCREENSHOTS'):
                                page.screenshot(path=str(Path(os.environ['SCOREBOARD_SCREENSHOTS']) / f'game-{gid}-{width}.png'), full_page=True)
                        self.assertEqual(errors, [])
                        page.close()
                b.close()
        finally:
            server.shutdown(); server.server_close()


if __name__ == '__main__':
    unittest.main()
