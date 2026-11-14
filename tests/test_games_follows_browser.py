"""Opt-in browser check: follows first on the Games overview (Chris, 2026-11-14).
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest tests/test_games_follows_browser.py
Every Sleeper league request is served the week-6 fixture rosters, so each conference shows the
same 6 pairings; enough to check section order and visibility."""
import json
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


@unittest.skipUnless(os.environ.get('RUN_SCOREBOARD_BROWSER_TESTS') == '1', 'opt-in browser checks')
class FollowsFirst(unittest.TestCase):
    def test_sections(self):
        from playwright.sync_api import sync_playwright
        root = Path(__file__).resolve().parents[1]
        fx = json.loads((root / 'tests/fixtures/scoreboard-week06.json').read_text())
        idx = json.loads((root / 'data/scoreboard/index.json').read_text())
        lid = '1316899756005412864'
        label = idx['leagues'][lid].get('label') or idx['leagues'][lid]['name']
        team = idx['leagues'][lid]['teams'][str(fx['rosters'][0]['roster_id'])]['name']

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(root)))
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        meta = json.loads((root / 'data/scoreboard/2026/players.json').read_text())
        base = json.loads((root / 'data/scoreboard/2026/week-06.json').read_text())
        teams = {x['team'] for x in meta.values() if x['team']} | {x['team'] for x in base['player_info'].values() if x['team']}
        espn = {'season': {'year': 2026}, 'week': {'number': 6}, 'events': [{
            'id': 'g', 'date': '2026-10-20T00:15:00Z', 'status': {'period': 4, 'displayClock': '0:00', 'type': {'state': 'post', 'completed': True}},
            'competitions': [{'competitors': [{'team': {'abbreviation': t}} for t in teams]}]}]}

        def api(route):
            u = route.request.url
            d = fx['rosters'] if '/matchups/' in u else (fx['stats'] if '/stats/' in u else {'scoring_settings': fx['scoring']})
            route.fulfill(content_type='application/json', body=json.dumps(d))

        def run(browser, follows, standalone=False, first=None):
            page = browser.new_page(viewport={'width': 1150, 'height': 1000}, service_workers='block')
            init = "try{sessionStorage.setItem('ncaa180.push.snooze','1');"
            if follows is not None:
                init += f"localStorage.setItem('ncaa180.push',{json.dumps(json.dumps({'follows': follows}))});"
            if first is not None:
                init += f"localStorage.setItem('sb-follows-first','{first}');"
            init += "}catch(e){}"
            if standalone:
                init += "window.matchMedia=(q=>({matches:/standalone/.test(q),addEventListener(){},removeEventListener(){}}));"
            page.add_init_script(init)
            errs = []
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.route('https://api.sleeper.app/**', api)
            page.route('https://site.api.espn.com/**', lambda r: r.fulfill(content_type='application/json', body=json.dumps(espn)))
            page.route('https://fonts.*/**', lambda r: r.abort())
            page.goto(f'http://127.0.0.1:{srv.server_port}/reports/scoreboard.html?week=6')
            page.wait_for_function("document.getElementById('updated')?.textContent.startsWith('Updated')", timeout=60000)
            out = page.evaluate("""()=>({ids:[...document.querySelectorAll('#board details.fsec')].map(d=>d.dataset.id),
              banner:!!document.querySelector('.fol-banner'),toggle:!!document.getElementById('fol-first'),
              teamCards:document.querySelectorAll('[data-id=fol-teams] .mini-match').length,
              yourConfs:document.querySelectorAll('[data-id=fol-leagues] details.conference').length,
              heads:[...document.querySelectorAll('#board h3.sec')].map(h=>h.textContent.trim().split(' ')[0])})""")
            page.close()
            self.assertEqual(errs, [])
            return out

        with sync_playwright() as pw:
            b = pw.chromium.launch(headless=True, args=['--no-sandbox'])
            # browser visitor, no follows: no follow sections at all
            o = run(b, None)
            self.assertNotIn('fol-teams', o['ids']); self.assertFalse(o['banner']); self.assertFalse(o['toggle'])
            # installed app, no follows: banner only
            o = run(b, [], standalone=True)
            self.assertTrue(o['banner']); self.assertNotIn('fol-teams', o['ids'])
            # follows a team and a conference: teams, conferences, featured, then the rest
            f = [{'kind': 'team', 'key': f'ncaa180|{label}:{fx["rosters"][0]["roster_id"]}'}, {'kind': 'league', 'key': f'ncaa180|{label}'}]
            o = run(b, f)
            self.assertEqual(o['ids'][:2], ['fol-teams', 'fol-leagues'])
            self.assertGreaterEqual(o['teamCards'], 1); self.assertEqual(o['yourConfs'], 1)
            self.assertIn('Other', o['heads']); self.assertTrue(o['toggle'])
            # plain order toggle off: no follow sections, toggle still there to turn it back on
            o = run(b, f, first='0')
            self.assertNotIn('fol-teams', o['ids']); self.assertTrue(o['toggle'])
            # follows a team that isn't playing: empty-state message, no league section
            o = run(b, [{'kind': 'team', 'key': 'ncaa180|Nowhere:99'}])
            self.assertIn('fol-teams', o['ids']); self.assertEqual(o['teamCards'], 0); self.assertNotIn('fol-leagues', o['ids'])
            b.close()
        srv.shutdown()
