"""CCG Race desktop/mobile preview smoke. Uses only local fixture data.
RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest tests/test_ccg_race_browser.py
"""
import os
from pathlib import Path
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in browser tests")
class CCGRaceBrowser(unittest.TestCase):
    def test_preview_desktop_mobile_and_folds(self):
        from playwright.sync_api import sync_playwright

        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        shots = ROOT / "work" / "ccg-race-preview"
        shots.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                for width, theme, filename in [(1280, "light", "desktop.png"), (390, "dark", "mobile.png")]:
                    page = browser.new_page(viewport={"width": width, "height": 960},
                                            service_workers="block", color_scheme=theme)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for url in ("https://api.sleeper.app/**", "https://site.api.espn.com/**",
                                "https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**"):
                        page.route(url, lambda route: route.abort())
                    page.add_init_script("localStorage.setItem('ncaa180.dev','1')")
                    page.goto(f"http://127.0.0.1:{server.server_port}/reports/ccg-race.html?preview=midweek")
                    page.wait_for_function("""() => document.querySelectorAll('#conferences section').length === 15 &&
                        document.querySelectorAll('#conferences .race-team').length > 20 &&
                        document.querySelectorAll('#conferences .snap-btn').length === 15""", timeout=30000)
                    self.assertEqual(errors, [], f"JS errors at viewport {width}")
                    self.assertIn("PREVIEW", page.locator("#flag").inner_text())
                    self.assertEqual(page.locator("#conferences section").count(), 15)
                    self.assertIn("Clinched", page.locator("#ccg-1331775106527006720").inner_text())
                    self.assertGreaterEqual(page.locator("#ccg-1331775106527006720 .prob").filter(has_text="Out").count(), 2)
                    self.assertEqual(page.locator("nav[data-row='selection-watch'] a").count(), 2)
                    self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), width + 2)
                    # Each division highlights its clinched team or highest chance, and lists teams by chance.
                    bad = page.evaluate("""() => [...document.querySelectorAll('#conferences .division')].flatMap(d => {
                        const v = t => { const s = t.querySelector('.prob').textContent.trim();
                            return s === 'Clinched' ? 101 : s === 'Out' ? -1 : s.startsWith('>') ? 99.5 : s.startsWith('<') ? 0.5 : parseFloat(s); };
                        const rows = [...d.querySelectorAll('.race-team')], vals = rows.map(v);
                        const errs = [];
                        if (!rows[0].classList.contains('leader')) errs.push(d.querySelector('h3').textContent + ': first row not highlighted');
                        if (rows.slice(1).some(r => r.classList.contains('leader'))) errs.push(d.querySelector('h3').textContent + ': extra highlight');
                        if (vals.some((x, i) => i && x > vals[i - 1])) errs.push(d.querySelector('h3').textContent + ': ' + vals.join(','));
                        return errs; })""")
                    self.assertEqual(bad, [])
                    # Fill = odds (Chris, 2026-11-20): colour width matches the chance, none for <1% / Out,
                    # full for Clinched, and text on the fill reads at 4.5:1 or better against the team colour.
                    fills = page.evaluate("""() => {
                        const lum = c => { const m = c.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(x => +x / 255)
                            .map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4); return .2126*m[0] + .7152*m[1] + .0722*m[2]; };
                        const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
                        return [...document.querySelectorAll('#conferences .race-team')].map(t => {
                            const s = t.querySelector('.prob').textContent.trim(), f = t.querySelector('.rt-fill');
                            const want = s === 'Clinched' ? 100 : (s === 'Out' || s.startsWith('<')) ? 0 : s.startsWith('>') ? 99 : parseFloat(s);
                            const got = f ? f.getBoundingClientRect().width / t.getBoundingClientRect().width * 100 : 0;
                            const name = t.querySelector('strong').textContent;
                            const errs = [];
                            if (Math.abs(got - want) > 1.5) errs.push(name + ' fill ' + got.toFixed(1) + ' vs ' + s);
                            if (f) { const st = getComputedStyle(f), r = ratio(st.backgroundColor, getComputedStyle(f.querySelector('strong')).color);
                                if (r < 4.5) errs.push(name + ' contrast ' + r.toFixed(2)); }
                            return errs; }).flat(); }""")
                    self.assertEqual(fills, [])
                    page.screenshot(path=str(shots / filename), full_page=True)
                    page.locator(".fold-all").click()
                    self.assertEqual(page.locator("#conferences section.fold.closed").count(), 15)
                    page.locator(".fold-all").click()
                    self.assertEqual(page.locator("#conferences section.fold.closed").count(), 0)
                    page.close()
                browser.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
