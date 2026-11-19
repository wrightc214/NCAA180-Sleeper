"""Generate Accessibility page with the shared site head, navigation and app assets.

Run from the repository root: python scripts/access_page.py
This does not fetch league data, deploy, or publish.
"""
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from site_common import page_head, menu_html

SOURCE = Path("templates/access.html")
TARGET = Path("reports/access.html")

def main():
    template = SOURCE.read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", template, re.S)
    main_block = re.search(r"<main>.*?</main>", template, re.S)
    if not css or not main_block:
        raise ValueError("Accessibility template requires a style block and main element")
    output = (page_head("Accessibility — NCAA 180", extra_css=css.group(1), totop=False)
              + menu_html("access")
              + "\n" + main_block.group(0)
              + '\n<script src="assets/access.js"></script></body></html>\n')
    TARGET.write_text(output, encoding="utf-8")

if __name__ == "__main__":
    main()
