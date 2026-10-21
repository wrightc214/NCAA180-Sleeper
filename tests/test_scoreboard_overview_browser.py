"""Network-free overview integration checks; same opt-in as the detailed board."""
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
class OverviewBrowserTests(unittest.TestCase):
    def test_grid_states_filter_partial_failure_and_game_links(self):
        from playwright.sync_api import sync_playwright
        root=Path(__file__).resolve().parents[1]
        fixture=json.loads((root/'tests/fixtures/scoreboard-week06.json').read_text())
        metadata=json.loads((root/'data/scoreboard/2026/players.json').read_text())
        baseline=json.loads((root/'data/scoreboard/2026/week-06.json').read_text())
        index=json.loads((root/'data/scoreboard/index.json').read_text())
        teams={p['team'] for p in metadata.values() if p['team']}|{p['team'] for p in baseline['player_info'].values() if p['team']}
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                args={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']}
                if os.environ.get('SCOREBOARD_BROWSER'):args['executable_path']=os.environ['SCOREBOARD_BROWSER']
                browser=pw.chromium.launch(**args)
                for width in (1450,400):
                    for phase in ('pre','in','post'):
                        with self.subTest(width=width,phase=phase):
                            page=browser.new_page(viewport={'width':width,'height':1100})
                            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                            state={'fail':None,'stats':0,'espn':0,'players':0}
                            rs=copy.deepcopy(fixture['rosters'])
                            if phase=='pre':
                                for r in rs:r['points']=0;r['players_points']={p:0 for p in r['players']}
                            def api(route):
                                u=route.request.url
                                if '/matchups/' in u:
                                    lid=u.split('/league/')[1].split('/')[0]
                                    if lid==state['fail']:route.fulfill(status=429,body='{}');return
                                    data=rs
                                elif '/stats/' in u:state['stats']+=1;data={} if phase=='pre' else fixture['stats']
                                elif u.endswith('/players/nfl'):state['players']+=1;data={}
                                elif u.endswith('/users'):data=[]
                                elif u.endswith('/rosters'):data=[]
                                else:data={'scoring_settings':fixture['scoring']}
                                route.fulfill(content_type='application/json',body=json.dumps(data))
                            def espn(route):
                                state['espn']+=1
                                w=int(parse_qs(urlparse(route.request.url).query)['week'][0])
                                data={'season':{'year':2026},'week':{'number':w},'events':[{'id':'night','date':'2026-10-20T00:15:00Z','status':{'period':4,'displayClock':'6:12','type':{'state':phase,'completed':phase=='post'}},'competitions':[{'competitors':[{'team':{'abbreviation':t}} for t in teams]}]}]}
                                route.fulfill(content_type='application/json',body=json.dumps(data))
                            page.route('https://api.sleeper.app/**',api)
                            page.route('https://site.api.espn.com/**',espn)
                            page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
                            page.route('https://fonts.gstatic.com/**',lambda r:r.abort())
                            page.goto(f'http://127.0.0.1:{server.server_port}/reports/scoreboard.html?week=6')
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated')")
                            self.assertEqual(page.locator('.conference').count(),len(index['leagues']))
                            self.assertEqual(page.locator('.mini-match').count(),sum(len(l['teams']) for l in index['leagues'].values())//2)
                            self.assertEqual(state['stats'],1);self.assertEqual(state['espn'],1);self.assertEqual(state['players'],0)
                            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                            self.assertEqual(page.locator('a[aria-current="page"]').inner_text(),'Scoreboard')
                            statuses=page.locator('.match-status').all_text_contents()
                            self.assertTrue(all(('Final' if phase=='post' else 'Live' if phase=='in' else 'Upcoming') in s for s in statuses))
                            self.assertIn('PREGAME %' if phase!='in' else 'LIVE WIN %',page.locator('.match-meta').first.inner_text())
                            if os.environ.get('SCOREBOARD_SCREENSHOTS'):
                                dest=Path(os.environ['SCOREBOARD_SCREENSHOTS']);dest.mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(dest/f'overview-{phase}-{width}.png'),full_page=True)
                            lid=next(iter(index['leagues']));state['fail']=lid
                            old=page.locator('.score-row').all_text_contents()
                            page.get_by_role('button',name='↻ Refresh').click()
                            page.wait_for_function("document.getElementById('updated').textContent.includes('conferences refreshed')")
                            self.assertEqual(page.locator('.conference-error').count(),1)
                            self.assertIn('STALE',page.locator('.conference-error').inner_text())
                            self.assertEqual(page.locator('.score-row').all_text_contents(),old)
                            state['fail']=None
                            page.select_option('#league',lid)
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated') && document.querySelectorAll('.conference').length===1")
                            self.assertEqual(page.locator('.mini-match').count(),6)
                            page.select_option('#week','5')
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated') && location.search.includes('week=5')")
                            self.assertEqual(page.locator('.mini-match').count(),6)
                            page.select_option('#week','6')
                            page.select_option('#week','5')
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated') && location.search.includes('week=5') && document.querySelectorAll('.mini-match').length===6")
                            page.locator('.mini-match').first.click()
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated') && document.querySelectorAll('.big').length===2")
                            self.assertTrue(page.locator('#overview-back').is_visible())
                            page.locator('#overview-back').click()
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated') && document.querySelectorAll('.conference').length===1")
                            self.assertEqual(page.locator('#week').input_value(),'5')
                            self.assertEqual(page.locator('#league').input_value(),lid)
                            self.assertEqual(errors,[])
                            page.close()
                browser.close()
        finally:server.shutdown();server.server_close()
