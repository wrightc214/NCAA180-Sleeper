"""
report_png.py -- save reports/latest.png, a full-page image of reports/index.html.

Needs Playwright + Chromium (installed by the workflow step that calls this).
Rendered at 1200px wide, 2x pixel density, light theme, after web fonts load.

Also saves one image per page section to reports/discord/NN-<name>.png for the Discord
post (Chris, 2026-10-06: the single full-page image was illegible on phones once Discord
compressed it). Sections render at a 600px phone-width viewport, 2x density. The HTML page
itself is not changed.
CWD must be repo root.
"""
import glob
import os
import re
from playwright.sync_api import sync_playwright

SRC = os.path.abspath("reports/index.html")
OUT = "reports/latest.png"
PARTS_DIR = "reports/discord"
PART_WIDTH = 600

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2, color_scheme="light")
    pg.goto("file://" + SRC, wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.screenshot(path=OUT, full_page=True)

    os.makedirs(PARTS_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(PARTS_DIR, "*.png")):
        os.remove(f)
    pg.set_viewport_size({"width": PART_WIDTH, "height": 900})
    pg.evaluate("document.fonts.ready")
    parts = []
    for i, sec in enumerate(pg.query_selector_all("main section, body > section, section")):
        h2 = sec.query_selector("h2")
        title = (h2.inner_text().split("\n")[0] if h2 else f"section {i + 1}").strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or f"section-{i + 1}"
        path = os.path.join(PARTS_DIR, f"{i + 1:02d}-{slug}.png")
        if path in parts:
            continue
        sec.screenshot(path=path)
        parts.append(path)
    b.close()
print(f"Wrote {OUT} and {len(parts)} section image(s) in {PARTS_DIR}/")
