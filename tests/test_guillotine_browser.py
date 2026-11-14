"""Special Events -> The Guillotine page (2026-11-14). Opt-in like the other browser checks:
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m unittest tests/test_guillotine_browser.py
Screenshots go to $GUILLOTINE_SHOTS (a folder) when set."""
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest


def _gd(index, live=True):
    """Synthetic guillotine.json: every 2026 team; live = week 13 in progress, else week 13 frozen."""
    teams = []
    for lid, lg in index['leagues'].items():
        for rid, t in lg['teams'].items():
            teams.append({'l': lid, 'r': rid, 'team': t['name'], 'owner': f'mgr{rid}', 'league': lg['name'],
                          'status': 'alive', 'out': None, 'scores': {}, 'added': []})
    gd = {'season': 2026, 'name': 'The Guillotine', 'first_week': 13, 'last_week': 17, 'tiebreak_week': 18,
          'badge': 'assets/logos/badges/Guillotine.png', 'status': 'upcoming', 'next_week': 13,
          'entrants': len(teams), 'weeks': [], 'champions': [], 'teams': teams}
    if not live:
        for i, t in enumerate(teams):
            t['scores'] = {'13': 200 - i * 0.75}
            if i >= 90:
                t['status'], t['out'] = 'out', 13
        teams[100]['scores']['13'] = teams[89]['scores']['13']  # tied at the line -> survives (PGA)
        teams[100]['status'], teams[100]['out'] = 'alive', None
        teams[100]['added'] = [13]
        gd.update(status='live', next_week=14,
                  weeks=[{'week': 13, 'field': 180, 'advance': 90, 'advanced': 91, 'cutline': teams[89]['scores']['13'], 'added': 1, 'final': True}])
    return gd


@unittest.skipUnless(os.environ.get('RUN_SCOREBOARD_BROWSER_TESTS') == '1', 'opt-in browser checks')
class GuillotineBrowserTests(unittest.TestCase):
    def run_page(self, gd, week, espn_state, shots_name, check):
        from playwright.sync_api import sync_playwright
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'tests/fixtures/scoreboard-week06.json').read_text())
        base6 = json.loads((root / 'data/scoreboard/2026/week-06.json').read_text())
        index = json.loads((root / 'data/scoreboard/index.json').read_text())
        idx = {**index, 'week': week, 'weeks': index['weeks'] + [13, 14]}
        base = {**base6, 'week': week, 'odds': [], 'event': 'postseason', 'games': []}
        teams = sorted({p['team'] for p in base6['player_info'].values() if p['team']})
        shots = os.environ.get('GUILLOTINE_SHOTS')

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as pw:
                b = pw.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])
                for width in (1300, 400):
                    with self.subTest(width=width):
                        page = b.new_page(viewport={'width': width, 'height': 1400}, service_workers='block')
                        page.add_init_script("try{sessionStorage.setItem('ncaa180.push.snooze','1')}catch(e){}")
                        errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        fetched = []

                        def api(route):
                            u = route.request.url
                            if '/matchups/' in u:
                                fetched.append(u.split('/league/')[1].split('/')[0])
                                data = copy.deepcopy(fixture['rosters'])
                            elif '/stats/' in u:
                                data = fixture['stats']
                            else:
                                data = {'scoring_settings': fixture['scoring']}
                            route.fulfill(content_type='application/json', body=json.dumps(data))

                        def espn(route):
                            # Monday 2026-12-07 20:15 ET (Tue 01:15 UTC): MNF
                            ev = lambda i, t2: {'id': str(i), 'date': '2026-12-08T01:15:00Z', 'status': espn_state, 'competitions': [{'competitors': [{'team': {'abbreviation': x}} for x in t2]}]}  # noqa: E731
                            data = {'season': {'year': 2026}, 'week': {'number': week}, 'events': [ev(0, teams)]}
                            route.fulfill(content_type='application/json', body=json.dumps(data))
                        page.route('https://api.sleeper.app/**', api)
                        page.route('https://site.api.espn.com/**', espn)
                        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
                        page.route('https://fonts.gstatic.com/**', lambda r: r.abort())
                        page.route('**/scoreboard/index.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps(idx)))
                        page.route('**/2026/guillotine.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps(gd)))
                        page.route(f'**/week-{week:02d}.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps(base)))
                        page.goto(f'http://127.0.0.1:{server.server_port}/reports/special.html')
                        page.wait_for_function("document.getElementById('updated')?.textContent.length>0 && !document.getElementById('updated').textContent.startsWith('Loading')", timeout=30000)
                        page.wait_for_timeout(300)
                        check(page, fetched, gd, width)
                        self.assertEqual(errors, [])
                        if shots:
                            page.screenshot(path=os.path.join(shots, f'{shots_name}-{width}.png'), full_page=True)
                        page.close()
                b.close()
        finally:
            server.shutdown()

    def test_live_week(self):
        index = json.loads((Path(__file__).resolve().parents[1] / 'data/scoreboard/index.json').read_text())
        gd = _gd(index, live=True)
        live = {'period': 4, 'displayClock': '5:00', 'type': {'state': 'in', 'completed': False}}

        def check(page, fetched, gd, width):
            self.assertEqual(sorted(set(fetched)), sorted(index['leagues']))  # week 1: every conference
            self.assertEqual(page.locator('.live-t .gl-r').count(), 180)
            self.assertEqual(page.locator('.gl-cut').count(), 1)
            k = page.locator('.gl-k b').all_inner_texts()
            self.assertEqual(k[:2], ['180', '90'])
            odds = [t for t in page.locator('.live-t .gl-n.od').all_inner_texts()]
            self.assertTrue(all(o.endswith('%') for o in odds))
            # MNF Q4 -> automatic refresh every 30 seconds
            self.assertIn('every 30 seconds', page.locator('#updated').inner_text())
            self.assertEqual(page.locator('nav[aria-label="Special events"] a').inner_text(), 'The Guillotine')
            self.assertIn('Special Events', page.locator('nav.weeks[aria-label="Pages"]').inner_text())
        self.run_page(gd, 13, live, 'live', check)

    def test_not_mnf_manual_only(self):
        index = json.loads((Path(__file__).resolve().parents[1] / 'data/scoreboard/index.json').read_text())
        gd = _gd(index, live=True)
        pre = {'period': 0, 'displayClock': '0:00', 'type': {'state': 'pre', 'completed': False}}

        def check(page, fetched, gd, width):
            self.assertIn('tap Refresh', page.locator('#updated').inner_text())
            self.assertEqual(page.locator('.live-t .gl-r').count(), 180)
        self.run_page(gd, 13, pre, 'preview', check)

    def test_frozen_week_and_eliminated(self):
        index = json.loads((Path(__file__).resolve().parents[1] / 'data/scoreboard/index.json').read_text())
        gd = _gd(index, live=False)
        pre = {'period': 0, 'displayClock': '0:00', 'type': {'state': 'pre', 'completed': False}}

        def check(page, fetched, gd, width):
            # week 14 live view: only the 91 survivors, from their conferences only
            self.assertEqual(page.locator('.live-t .gl-r').count(), 91)
            self.assertEqual(page.locator('.out-t .gl-r').count(), 89)
            self.assertEqual(page.locator('.gl-weeks a').count(), 2)
            page.click('.gl-weeks a >> nth=0')
            page.wait_for_selector('.fz-t')
            self.assertEqual(page.locator('.fz-t .gl-r').count(), 180)
            self.assertEqual(page.locator('.fz-t .gl-r.gone').count(), 89)
            self.assertIn('added after stat corrections', page.locator('.fz-t').inner_text())
        self.run_page(gd, 14, pre, 'frozen', check)


if __name__ == '__main__':
    unittest.main()
