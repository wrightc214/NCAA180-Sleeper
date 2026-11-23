"""Trophy component in a real browser (task 5.1): art loads, engraving never overflows, Save image
captures the engraving, the JS fallback replaces missing art. Opt-in: RUN_SCOREBOARD_BROWSER_TESTS=1."""
import io
import itertools
import os
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = os.environ.get("TROPHY_ARTIFACTS")  # optional folder for the Save-image PNG (PR evidence)

CHECK = """()=>{
  const out=[];
  for(const f of document.querySelectorAll('figure.trophy')){
    const img=f.querySelector('.trophy-art>img');
    if(!f.classList.contains('fallback')&&(!img||!img.complete||img.naturalWidth===0))out.push('broken '+f.dataset.art);
    const p=f.querySelector('.trophy-plaque');if(!p||!p.offsetParent)continue;
    const pr=p.getBoundingClientRect();
    for(const s of p.children){const r=s.getBoundingClientRect();
      if(s.scrollWidth>s.clientWidth+0.5||r.left<pr.left-0.5||r.right>pr.right+0.5||r.top<pr.top-0.5||r.bottom>pr.bottom+0.5)
        out.push('overflow '+s.textContent);}
  }
  return out}"""


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(os.environ.get("RUN_SCOREBOARD_BROWSER_TESTS") == "1", "opt-in Playwright")
class TrophyBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=str(ROOT)))
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()

    def open(self, path, width=1280, theme="light"):
        p = self.browser.new_page(viewport={"width": width, "height": 900}, color_scheme=theme,
                                  service_workers="block", accept_downloads=True)
        self.addCleanup(p.close)
        errors = []
        p.on("pageerror", lambda ex: errors.append(str(ex)))
        self.addCleanup(lambda: self.assertEqual(errors, []))
        p.route("https://fonts.googleapis.com/**", lambda r: r.abort())
        p.route("https://fonts.gstatic.com/**", lambda r: r.abort())
        p.goto(self.base + path)
        p.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i=>i.loading='eager')")
        p.wait_for_load_state("networkidle")
        p.evaluate("document.fonts.ready")
        return p

    def test_postseason_trophies_load_and_fit(self):
        for width, theme in itertools.product((390, 1280), ("light", "dark")):
            with self.subTest(width=width, theme=theme):
                p = self.open("reports/postseason-2025.html", width, theme)
                self.assertGreaterEqual(p.locator("figure.trophy").count(), 52)
                self.assertEqual(p.evaluate(CHECK), [])
                self.assertLessEqual(p.evaluate("document.documentElement.scrollWidth"), width)
                # the engraving is real text, in the plaque, in the trophy font
                fig = p.locator("#ccg figure.trophy").first
                self.assertIn("Champion", fig.locator(".tp-2").inner_text().title())
                self.assertIn("Barlow Trophy", fig.locator(".trophy-plaque").evaluate("e=>getComputedStyle(e).fontFamily"))

    def test_every_season_page_has_no_broken_trophy(self):
        for f in sorted(ROOT.glob("reports/postseason-20*.html")):
            with self.subTest(page=f.name):
                p = self.open(f"reports/{f.name}", 1280)
                self.assertEqual(p.evaluate(CHECK), [])

    def test_save_image_of_champion_card_shows_the_engraving(self):
        from PIL import Image
        p = self.open("reports/postseason-2025.html", 1280)
        p.wait_for_function("document.querySelector('.bk')?.dataset.ready==='1'")
        with p.expect_download(timeout=120000) as d:
            p.evaluate("document.querySelector('.bk').bkSave('champ', 2)")
        data = Path(d.value.path()).read_bytes()
        if OUT:
            Path(OUT).mkdir(parents=True, exist_ok=True)
            (Path(OUT) / d.value.suggested_filename).write_bytes(data)
        im = Image.open(io.BytesIO(data)).convert("RGB")
        # find the plaque: the biggest run of #CFD4D8 rows, then look for ink inside it
        w, h = im.size
        px = im.load()
        rows = [y for y in range(h) if sum(1 for x in range(0, w, 2) if px[x, y] == (0xCF, 0xD4, 0xD8)) > 60]
        self.assertTrue(rows, "no plaque in the image")
        y0, y1 = rows[0], rows[-1]
        xs = [x for x in range(w) if px[x, (y0 + y1) // 2] == (0xCF, 0xD4, 0xD8)]
        ink = sum(1 for y in range(y0, y1) for x in range(xs[0], xs[-1]) if sum(px[x, y]) < 300)
        self.assertGreater(ink, 300, "plaque is blank in the saved image")

    def test_dwight_fight_and_js_fallback(self):
        p = self.open("reports/dwight-fight.html", 390)
        p.wait_for_function("window.NCAATrophy?.config")
        html = p.evaluate("""()=>{const d=document.createElement('div');document.body.append(d);
          d.innerHTML=NCAATrophy.html({EventType:'Bowl',Event:'No Such Bowl'},'Arizona State',2026,null,{lazy:false});
          return new Promise(r=>setTimeout(()=>r(d.innerHTML),1500))}""")
        self.assertIn('class="trophy fallback', html)
        self.assertIn("2026 No Such Bowl", html)
        self.assertNotIn("No%20Such%20Bowl.png", html.split("data-art")[0])


if __name__ == "__main__":
    unittest.main()
