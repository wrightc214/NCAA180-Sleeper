"""Opt-in, network-free browser integration checks.
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m unittest discover -s tests -p 'test_scoreboard_browser.py'
Optional SCOREBOARD_BROWSER selects an existing Chromium executable.
"""
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import unittest


@unittest.skipUnless(os.environ.get('RUN_SCOREBOARD_BROWSER_TESTS') == '1', 'opt-in browser checks')
class BrowserTests(unittest.TestCase):
    def test_states_mobile_selection_and_failed_refresh(self):
        from playwright.sync_api import sync_playwright
        root=Path(__file__).resolve().parents[1]
        fixture=json.loads((root/'tests/fixtures/scoreboard-week06.json').read_text())
        metadata=json.loads((root/'data/scoreboard/2026/players.json').read_text())
        baseline=json.loads((root/'data/scoreboard/2026/week-06.json').read_text())
        players={pid:{'full_name':p['name'],'team':p['team'],'position':p['position'],'fantasy_positions':p['positions'],'status':'Active'} for pid,p in metadata.items()}
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as pw:
                kwargs={'headless':True,'args':['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']}
                if os.environ.get('SCOREBOARD_BROWSER'):kwargs['executable_path']=os.environ['SCOREBOARD_BROWSER']
                browser=pw.chromium.launch(**kwargs)
                for width in (1150,400):
                    for phase in ('pre','in','post'):
                        with self.subTest(width=width,phase=phase):
                            page=browser.new_page(viewport={'width':width,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                            state={'fail':False}
                            rosters=copy.deepcopy(fixture['rosters'])
                            if phase=='pre':
                                for r in rosters:
                                    r['points']=0;r['players_points']={p:0 for p in r['players']}
                            teams={p['team'] for p in metadata.values() if p['team']} | {p['team'] for p in baseline['player_info'].values() if p['team']}
                            espn={'season':{'year':2026},'week':{'number':6},'events':[{
                                'id':'night-game','date':'2026-10-20T00:15:00Z',
                                'status':{'period':4,'displayClock':'6:12','type':{'state':phase,'completed':phase=='post'}},
                                'competitions':[{'competitors':[{'team':{'abbreviation':t}} for t in teams]}]}]}
                            def route_api(route):
                                u=route.request.url
                                if '/matchups/' in u:
                                    if state['fail']:route.fulfill(status=429,headers={'Retry-After':'60'},body='{}');return
                                    d=rosters
                                elif '/stats/' in u:d={} if phase=='pre' else fixture['stats']
                                elif u.endswith('/players/nfl'):d=players
                                elif u.endswith('/users'):d=[{'user_id':'u'+str(r['roster_id']),'display_name':'Manager '+str(r['roster_id'])} for r in rosters]
                                elif u.endswith('/rosters'):d=[{'roster_id':r['roster_id'],'owner_id':'u'+str(r['roster_id'])} for r in rosters]
                                else:d={'scoring_settings':fixture['scoring']}
                                route.fulfill(content_type='application/json',body=json.dumps(d))
                            page.route('https://api.sleeper.app/**',route_api)
                            def route_espn(route):
                                from urllib.parse import urlparse, parse_qs
                                data=copy.deepcopy(espn)
                                data['week']['number']=int(parse_qs(urlparse(route.request.url).query)['week'][0])
                                route.fulfill(content_type='application/json',body=json.dumps(data))
                            page.route('https://site.api.espn.com/**',route_espn)
                            page.route('https://fonts.googleapis.com/**',lambda r:r.abort())
                            page.route('https://fonts.gstatic.com/**',lambda r:r.abort())
                            page.goto(f'http://127.0.0.1:{server.server_port}/reports/scoreboard.html?league=1316899756005412864&week=6&roster=6')
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated')")
                            self.assertEqual(page.locator('.big').count(),2)
                            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                            self.assertIn('VALIDATION PHASE',page.locator('.validation').inner_text())
                            if phase=='in':
                                self.assertIn('30 seconds',page.locator('#updated').inner_text())
                                self.assertGreater(page.locator('.ps.on').count(),0)
                            elif phase=='pre':self.assertIn('NEXT KICKOFF',page.locator('.mid').inner_text())
                            else:self.assertIn('FINAL',page.locator('.mid').inner_text())
                            old=page.locator('.big').all_text_contents();state['fail']=True;page.locator('#refresh').click()
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('STALE')")
                            self.assertEqual(page.locator('.big').all_text_contents(),old)
                            self.assertTrue(page.locator('#error').is_visible());state['fail']=False
                            options=page.locator('#game option').all_text_contents()
                            self.assertEqual(len(options),6)
                            page.select_option('#game',index=1)
                            page.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated')")
                            self.assertNotEqual(page.locator('.big').all_text_contents(),old) if phase!='pre' else None
                            # League and week changes reload the games without submitting a form.
                            page.select_option('#week', '5')
                            page.wait_for_function("document.getElementById('week').disabled === false && document.getElementById('game').options.length === 6")
                            self.assertEqual(page.locator('#game').input_value(), str(rosters[0]['matchup_id']))
                            other=page.locator('#league option').evaluate_all("els => els.map(e=>e.value).find(v=>v!=='1316899756005412864')")
                            page.select_option('#league', other)
                            page.wait_for_function("document.getElementById('league').disabled === false && document.getElementById('game').options.length === 6")
                            self.assertNotEqual(page.locator('#game option').all_text_contents(), options)
                            self.assertEqual(page.locator('a[aria-current="page"]').inner_text(), 'Scoreboard')
                            self.assertEqual(errors,[])
                            if os.environ.get('SCOREBOARD_SCREENSHOTS'):
                                dest=Path(os.environ['SCOREBOARD_SCREENSHOTS']);dest.mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(dest/f'{phase}-{width}.png'),full_page=True)
                            page.close()
                browser.close()
        finally:server.shutdown();server.server_close()
