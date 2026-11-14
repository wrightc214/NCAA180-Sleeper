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
            if u.endswith('/users'):  # the embedded game page (My team) also loads managers
                d = [{'user_id': f'u{r["roster_id"]}', 'display_name': f'Manager {r["roster_id"]}'} for r in fx['rosters']]
            elif u.endswith('/rosters'):
                d = [{'roster_id': r['roster_id'], 'owner_id': f'u{r["roster_id"]}'} for r in fx['rosters']]
            route.fulfill(content_type='application/json', body=json.dumps(d))

        def run(browser, follows, standalone=False, first=None, mine=None):
            page = browser.new_page(viewport={'width': 1150, 'height': 1000}, service_workers='block')
            init = "if(window.top===window)try{sessionStorage.setItem('ncaa180.push.snooze','1');"
            if follows is not None:
                st = {'follows': follows}
                if mine: st['myTeam'] = mine
                init += f"localStorage.setItem('ncaa180.push',{json.dumps(json.dumps(st))});"
            if first is not None:
                init += f"localStorage.setItem('sb-follows-first','{first}');"
            init += "}catch(e){}"  # top page only: the My team iframe must not reset storage
            if standalone:
                init += "window.matchMedia=(q=>({matches:/standalone/.test(q),addEventListener(){},removeEventListener(){}}));"
            page.add_init_script(init)
            errs = []
            page.on('pageerror', lambda e: errs.append(str(e)))
            page.route('https://api.sleeper.app/**', api)
            page.route('https://site.api.espn.com/**', lambda r: r.fulfill(content_type='application/json', body=json.dumps(espn)))
            page.route('https://fonts.*/**', lambda r: r.abort())
            page.route('**/game-of-the-week.json', lambda r: r.fulfill(content_type='application/json', body=json.dumps({'6': {'teams': ['Montana State', 'Stony Brook'], 'reason': 'x', 'source': 'auto'}})))
            page.goto(f'http://127.0.0.1:{srv.server_port}/reports/scoreboard.html?week=6')
            page.wait_for_function("document.getElementById('updated')?.textContent.startsWith('Updated')", timeout=60000)
            out = page.evaluate("""()=>({ids:[...document.querySelectorAll('#board details.fsec')].map(d=>d.dataset.id),
              banner:!!document.querySelector('.fol-banner'),toggle:!!document.getElementById('fol-first'),
              teamCards:document.querySelectorAll('[data-id=fol-teams] .mini-match').length,
              yourConfs:document.querySelectorAll('[data-id=fol-leagues] details.conference').length,
              heads:[...document.querySelectorAll('#board h3.sec')].map(h=>h.textContent.trim().split(' ')[0]),
              myBoard:!!document.getElementById('my-board')&&!document.getElementById('my-board').hidden,
              mySrc:document.querySelector('#my-board iframe')?.getAttribute('src')||'',
              slotFirst:!!document.getElementById('gotw-slot')&&!!(document.getElementById('gotw-slot').compareDocumentPosition(document.getElementById('my-board')||document.getElementById('board'))&Node.DOCUMENT_POSITION_FOLLOWING),
              myTeam:JSON.parse(localStorage.getItem('ncaa180.push')||'{}').myTeam||''})""")
            if out['myBoard']:  # the embedded game page loads without chrome and sizes its frame
                fr = page.frame_locator('#my-board iframe')
                fr.locator('.big').first.wait_for(timeout=60000)
                out['embedBigs'] = fr.locator('.big').count()
                out['embedNav'] = fr.locator('nav.weeks').is_visible()
                page.wait_for_function("parseInt(document.querySelector('#my-board iframe').style.height)>200", timeout=30000)
                if os.environ.get('SCOREBOARD_SCREENSHOTS'):
                    page.set_viewport_size({'width': 400, 'height': 1000}); page.wait_for_timeout(1500)
                    page.screenshot(path=os.path.join(os.environ['SCOREBOARD_SCREENSHOTS'], f'my-team-{len(follows)}.png'), full_page=True)
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
            rid = fx["rosters"][0]["roster_id"]
            me = f'ncaa180|{label}:{rid}'
            # follows a team and a conference: that team becomes My team automatically (existing users,
            # 2026-11-14) and gets the full board; its game is not repeated as a card
            f = [{'kind': 'team', 'key': me}, {'kind': 'league', 'key': f'ncaa180|{label}'}]
            o = run(b, f)
            self.assertEqual(o['myTeam'], me); self.assertTrue(o['myBoard'])
            self.assertIn('embed=1', o['mySrc']); self.assertEqual(o['embedBigs'], 2); self.assertFalse(o['embedNav'])
            self.assertEqual(o['ids'][:1], ['fol-leagues']); self.assertNotIn('fol-teams', o['ids'])
            self.assertEqual(o['yourConfs'], 1); self.assertIn('Other', o['heads']); self.assertTrue(o['toggle'])
            # My team plus every team in the conference: the other games stay compact cards
            many = [{'kind': 'team', 'key': f'ncaa180|{label}:{r["roster_id"]}'} for r in fx['rosters']]
            o = run(b, many, mine=me)
            self.assertTrue(o['myBoard']); self.assertEqual(o['ids'][:1], ['fol-teams'])
            self.assertTrue(o['slotFirst'])  # Game of the Week above My team (2026-11-14)
            self.assertEqual(o['teamCards'], len(fx['rosters']) // 2 - 1)
            # plain order toggle off: no follow sections or board, toggle still there to turn it back on
            o = run(b, f, first='0')
            self.assertNotIn('fol-teams', o['ids']); self.assertFalse(o['myBoard']); self.assertTrue(o['toggle'])
            # My team not playing and no other team follows: empty-state message, no board
            o = run(b, [{'kind': 'team', 'key': 'ncaa180|Nowhere:99'}])
            self.assertFalse(o['myBoard']); self.assertIn('fol-teams', o['ids']); self.assertEqual(o['teamCards'], 0)
            b.close()
        srv.shutdown()
