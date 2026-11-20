"""Bracket component in a browser (task 5.13). Opt-in like the other browser checks:
RUN_SCOREBOARD_BROWSER_TESTS=1 python3 -m pytest -q tests/test_bracket_browser.py
Chromium from Playwright (CI installs it); set PLAYWRIGHT_CHROMIUM_EXECUTABLE to use another Chrome.
The WebKit test (1.5x full-bracket export, iOS Safari's engine) runs when Playwright's WebKit is
installed and skips otherwise."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import struct
import threading
import unittest
from urllib.parse import parse_qs, urlparse

import bracket_fixture as F

ROOT = Path(__file__).resolve().parents[1]
IOS_CANVAS = 16_777_216  # iOS Safari's maximum canvas area (pixels)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def png_size(data):
    return struct.unpack(">II", data[16:24])


@unittest.skipUnless(os.environ.get('RUN_SCOREBOARD_BROWSER_TESTS') == '1', 'opt-in browser checks')
class BracketBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pages = {s: F.write_page(s) for s in ("final", "s16-live", "e8-live")}
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}/reports/'
        cls.pw = sync_playwright().start()
        exe = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
        cls.browser = cls.pw.chromium.launch(**({'executable_path': exe} if exe else {}),
                                             args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        for n in cls.pages.values():
            (ROOT / 'reports' / n).unlink(missing_ok=True)

    def open(self, state, width, theme='dark', motion='no-preference', height=900):
        ctx = self.browser.new_context(viewport={'width': width, 'height': height}, color_scheme=theme,
                                       reduced_motion=motion, accept_downloads=True, service_workers='block')
        p = ctx.new_page()
        errors = []
        p.on('pageerror', lambda e: errors.append(str(e)))
        p.goto(self.base + self.pages[state])
        p.wait_for_function("document.querySelector('.bk')?.dataset.ready==='1'")
        p.wait_for_timeout(400)
        self.addCleanup(ctx.close)
        self.addCleanup(lambda: self.assertEqual(errors, []))
        return p

    def focus(self, p):
        return int(p.eval_on_selector('.bk-phone', 'e=>e.dataset.focus'))

    # ---------------------------------------------------------- phone navigation
    def test_phone_opens_on_round_in_play_and_swipes(self):
        p = self.open('e8-live', 390)
        self.assertEqual(self.focus(p), 2)  # Elite 8 is being played
        box = p.locator('.bk-view').bounding_box()
        y = box['y'] + 120

        x0 = box['x'] + 5 if box['x'] + 5 + 150 < box['x'] + box['width'] else box['x'] + box['width'] / 2

        def swipe(dx):  # from the left margin (a tap on a game opens it; a drag that starts on one still swipes)
            x = x0 if dx > 0 else box['x'] + box['width'] - 5
            p.mouse.move(x, y)
            p.mouse.down()
            p.mouse.move(x + dx, y + 5, steps=6)
            p.mouse.up()
            p.wait_for_timeout(450)
        swipe(-140)
        self.assertEqual(self.focus(p), 3)
        swipe(150)
        swipe(150)
        self.assertEqual(self.focus(p), 1)
        swipe(30)  # too short: not a swipe
        self.assertEqual(self.focus(p), 1)
        self.assertEqual(p.locator('.bk-tab[aria-current="true"]').get_attribute('data-r'), '1')

    def test_phone_tabs_are_buttons_and_reachable(self):
        p = self.open('final', 320, theme='light')
        self.assertEqual(self.focus(p), 4)  # all final: opens on the Championship (champion card)
        tabs = p.locator('.bk-tab')
        self.assertEqual(tabs.count(), 5)
        self.assertEqual(p.eval_on_selector_all('.bk-tab', 'e=>e.map(x=>x.tagName)'), ['BUTTON'] * 5)
        tabs.nth(0).click()  # the strip scrolls: the far tab is still reachable on a 320px phone
        p.wait_for_timeout(450)
        self.assertEqual(self.focus(p), 0)
        # quad headers inside the focused round
        self.assertEqual(p.eval_on_selector_all('.bk-pq', 'e=>e.filter(x=>getComputedStyle(x).visibility==="visible").length'), 4)
        tabs.nth(3).click()
        p.wait_for_timeout(450)
        self.assertEqual(self.focus(p), 3)
        self.assertEqual(p.eval_on_selector_all('.bk-pq', 'e=>e.filter(x=>getComputedStyle(x).visibility==="visible").length'), 0)

    def test_phone_keyboard_arrows(self):
        p = self.open('final', 390)
        p.focus('.bk-view')
        p.keyboard.press('ArrowLeft')
        p.keyboard.press('ArrowLeft')
        self.assertEqual(self.focus(p), 2)
        p.keyboard.press('ArrowRight')
        self.assertEqual(self.focus(p), 3)
        p.keyboard.press('ArrowRight')
        p.keyboard.press('ArrowRight')  # stops at the last round
        self.assertEqual(self.focus(p), 4)

    def test_phone_next_round_peeks_at_feeder_midpoints(self):
        p = self.open('final', 390)
        p.locator('.bk-tab').nth(1).click()
        p.wait_for_timeout(500)
        r = p.evaluate("""()=>{const c=r=>[...document.querySelectorAll(`.bk-col[data-r="${r}"]>.bk-card`)].map(x=>{const b=x.getBoundingClientRect();return [b.top+b.height/2,b.left]});
          const f=c(1),n=c(2),view=document.querySelector('.bk-view').getBoundingClientRect();return {f,n,right:view.right}}""")
        for i, (cy, _) in enumerate(r['n']):
            self.assertAlmostEqual(cy, (r['f'][2 * i][0] + r['f'][2 * i + 1][0]) / 2, delta=1.5)
        peek = r['right'] - r['n'][0][1]
        self.assertTrue(30 <= peek <= 80, peek)

    def test_reduced_motion_switches_instantly(self):
        p = self.open('final', 390, motion='reduce')
        self.assertEqual(p.eval_on_selector('.bk-track', 'e=>getComputedStyle(e).transitionDuration'), '0s')
        p2 = self.open('final', 390)
        self.assertEqual(p2.eval_on_selector('.bk-track', 'e=>getComputedStyle(e).transitionDuration'), '0.35s')

    # ---------------------------------------------------------- game link
    def test_game_opens_scoreboard_game_view(self):
        p = self.open('e8-live', 1280)
        a = p.locator('.bk-desk a.bk-g[data-r="2"][data-i="0"]')
        href = a.get_attribute('href')
        q = parse_qs(urlparse(href).query)
        self.assertEqual((q['season'], q['week']), (['2025'], ['15']))
        want = [g for g in F.playoff_2025('e8-live', ids=True) if g['round'] == 3 and g['bowl'] == 'Orange Bowl'][0]['id']
        self.assertEqual(q['post'], [want])
        with p.expect_navigation():
            a.click()
        self.assertTrue(p.url.endswith('/reports/' + href))
        # phone: a tap on the focused round opens the game; a tap on the peeking round moves to it
        m = self.open('e8-live', 390)
        peek = m.locator('.bk-col[data-r="3"] .bk-card').first
        peek.click(position={'x': 10, 'y': 20}, force=True)
        m.wait_for_timeout(450)
        self.assertEqual(self.focus(m), 3)
        self.assertTrue(m.url.endswith(self.pages['e8-live']))

    # ---------------------------------------------------------- layout, contrast, names
    def test_widths_themes_overflow_contrast_names(self):
        for width in (320, 390, 768, 1280):
            for theme in ('light', 'dark'):
                with self.subTest(width=width, theme=theme):
                    p = self.open('final', width, theme)
                    sw = p.evaluate('document.documentElement.scrollWidth')
                    self.assertLessEqual(sw, width, 'page scrolls sideways outside the bracket scroller')
                    view = '.bk-desk' if width >= 720 else '.bk-phone'
                    self.assertTrue(p.locator(view).is_visible())
                    bad = p.evaluate(f"""()=>{{
                      const lum=c=>{{const v=c.match(/\\d+(\\.\\d+)?/g).slice(0,3).map(Number).map(x=>x/255).map(x=>x<=.03928?x/12.92:((x+.055)/1.055)**2.4);return .2126*v[0]+.7152*v[1]+.0722*v[2]}};
                      const out=[];for(const r of document.querySelectorAll('{view} .bk-row.win')){{const s=getComputedStyle(r),a=lum(s.backgroundColor),b=lum(s.color);
                        const cr=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);if(cr<4.5)out.push(r.textContent.trim()+' '+cr.toFixed(2));}}
                      for(const b of document.querySelectorAll('{view} .bk-nm b')){{if(b.offsetParent&&b.scrollWidth>b.clientWidth+1)out.push('cut: '+b.textContent)}}
                      return out}}""")
                    self.assertEqual(bad, [])

    def test_desktop_rows_fit_longest_name_on_one_line(self):
        p = self.open('final', 1280)
        h = p.eval_on_selector_all('.bk-desk .bk-row', 'e=>[...new Set(e.map(x=>x.offsetHeight))]')
        self.assertEqual(h, [42])

    # ---------------------------------------------------------- exports
    def save(self, p, what, scale):
        with p.expect_download(timeout=120000) as d:
            p.evaluate(f"document.querySelector('.bk').bkSave('{what}', {scale})")
        path = d.value.path()
        return d.value.suggested_filename, png_size(Path(path).read_bytes())

    def test_export_menu_defaults(self):
        p = self.open('final', 1280)
        p.click('#bracket .snap-btn')
        self.assertEqual(p.eval_on_selector('.bk-menu input[name=bk-what]:checked', 'e=>e.value'), 'full')
        labels = p.locator('.bk-menu .bk-sz label')
        self.assertIn('Recommended for Android & desktop', labels.nth(0).inner_text())
        self.assertIn('Recommended for iPhone', labels.nth(1).inner_text())
        self.assertEqual(labels.nth(0).locator('svg').count(), 1)  # icon beside the text, not icon-only
        m = self.open('s16-live', 390)
        m.click('#bracket .snap-btn')
        self.assertEqual(m.eval_on_selector('.bk-menu input[name=bk-what]:checked', 'e=>e.value'), 'round-1')
        self.assertTrue(m.locator('.bk-menu input[value=e8]').is_disabled())
        self.assertIn('Available once the Elite 8 is set', m.locator('.bk-menu').inner_text())

    def test_full_bracket_sizes(self):
        p = self.open('final', 1280)
        name, (w, h) = self.save(p, 'full', 1.5)
        self.assertEqual(name, 'ncaa180-2025-playoff-bracket.png')
        self.assertLessEqual(w * h, IOS_CANVAS, (w, h))
        _, (w2, h2) = self.save(p, 'full', 2)
        self.assertAlmostEqual(w2 / w, 4 / 3, delta=0.01)
        self.assertGreater(w2 * h2, IOS_CANVAS)  # why iPhone gets 1.5x

    def test_full_bracket_15x_in_webkit(self):
        try:
            wk = self.pw.webkit.launch()
        except Exception as x:  # noqa: BLE001
            self.skipTest(f'WebKit not installed here: {str(x).splitlines()[0]}')
        self.addCleanup(wk.close)
        ctx = wk.new_context(viewport={'width': 1280, 'height': 900}, accept_downloads=True)
        p = ctx.new_page()
        p.goto(self.base + self.pages['final'])
        p.wait_for_function("document.querySelector('.bk')?.dataset.ready==='1'")
        name, (w, h) = self.save(p, 'full', 1.5)
        self.assertLessEqual(w * h, IOS_CANVAS)
        self.assertGreater(w, 3000)


if __name__ == '__main__':
    unittest.main()
