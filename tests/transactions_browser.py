"""Read-only browser smoke test for generated Transactions page.

Called explicitly by PR CI after generating reports/transactions.html.
No network calls or production deployment.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, theme in ((1280, "light"), (390, "dark")):
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/reports/transactions.html")
                page.wait_for_selector(".tx-card")
                count = page.locator(".tx-card").count()
                assert count > 50, f"Too few cards: {count}"
                assert page.locator("section.fold").count() == 3
                assert page.locator("section.fold .snap-btn").count() == 3
                page.evaluate("(theme) => document.documentElement.setAttribute('data-theme', theme)", theme)
                assert page.locator("[data-score]").count() > 0
                # Reviewer-facing visual evidence, captured without altering the repository.
                shot = ROOT / "work" / "transactions-preview"
                shot.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot / f"transactions-{width}-{theme}.png"), full_page=False)
                # Filter to a team on the first trade. Revert filter.
                first = page.locator(".tx-card").first
                team = first.get_attribute("data-teams").split("|")[0]
                page.locator("#tx-team").select_option(label=team)
                assert 0 < page.locator(".tx-card:visible").count() <= count
                page.locator("#tx-team").select_option("")
                assert page.locator(".tx-card:visible").count() == count
                # Fold and restore without losing page state.
                sec = page.locator("section.fold").first
                sec.locator("h2").click()
                assert "closed" in (sec.get_attribute("class") or "")
                sec.locator("h2").click()
                assert "closed" not in (sec.get_attribute("class") or "")
                # Changes to week selector must refresh movement views.
                selector = page.locator("#tx-move-week")
                assert selector.locator("option").count() > 0
                values = selector.locator("option").evaluate_all("(es) => es.map(e => e.value)")
                if len(values) > 1:
                    selector.select_option(values[0])
                    assert page.locator("#tx-adds").count() == 1
                    selector.select_option(values[-1])
                overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
                assert overflow <= 8, f"Horizontal overflow at {width}px: {overflow}px"
                assert not errors, errors
                page.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)


if __name__ == "__main__":
    main()
