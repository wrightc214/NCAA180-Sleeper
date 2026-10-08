"""
poll_png.py -- phone-width images of reports/poll.html for the Discord post:
reports/discord-poll/01-poll.png (the poll + others receiving votes) and, when there are
any, 02-ranked-games.png. 600px wide, 2x density, light theme (same as report_png.py).
Needs Playwright + Chromium. CWD must be repo root.
"""
import glob
import os

from playwright.sync_api import sync_playwright

SRC = os.path.abspath("reports/poll.html")
OUT = "reports/discord-poll"
WIDTH = 600

os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, "*.png")):
    os.remove(f)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": WIDTH, "height": 900}, device_scale_factor=2, color_scheme="light")
    pg.goto("file://" + SRC, wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    made = []
    sec = pg.query_selector("section#poll")
    if sec:
        sec.screenshot(path=os.path.join(OUT, "01-poll.png"))
        made.append("01-poll.png")
    for s in pg.query_selector_all("section"):
        h2 = s.query_selector("h2")
        if h2 and h2.inner_text().lower().startswith("ranked games"):
            s.screenshot(path=os.path.join(OUT, "02-ranked-games.png"))
            made.append("02-ranked-games.png")
            break
    b.close()
print(f"Wrote {', '.join(made) or 'nothing'} in {OUT}/")
