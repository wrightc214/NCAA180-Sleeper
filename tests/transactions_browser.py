"""Read-only browser smoke test for generated Transactions page.

Called explicitly by PR CI after generating reports/transactions.html.
No network calls or production deployment.
"""
from csv import DictReader
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import struct
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def check_trade_exports(page):
    # Record the DOM that actually reaches the real renderer, not a stubbed export.
    vendor = (ROOT / "reports" / "assets" / "vendor" / "html2canvas-1.4.1.min.js").read_text()
    probe = r"""
    ;(() => {
      const draw = window.html2canvas;
      window.html2canvas = (root, options) => {
        const visible = [...root.querySelectorAll('.tx-card:not([hidden])')];
        const geometry = visible.map(c => {
          const rows = [...c.querySelectorAll('.tx-grade')];
          return rows.every((row, i) => i === 0 ||
            row.getBoundingClientRect().top >= rows[i - 1].getBoundingClientRect().bottom);
        });
        window.parent.__tradeExport = {
          titles: visible.map(c => c.dataset.snapCard),
          details: visible.map(c => [...c.querySelectorAll('.tx-fit details')].map(d => ({
            open: d.open, hasText: d.textContent.includes('Projected hold comparison:')
          }))),
          explainer: root.querySelector('.tx-explainer')?.textContent.includes('FantasyCalc') ?? null,
          buttons: root.querySelectorAll('.snap-btn').length,
          team: root.querySelector('#tx-team')?.value ?? null,
          geometry,
        };
        return draw(root, options);
      };
    })();
    """
    page.route("**/vendor/html2canvas-1.4.1.min.js", lambda route: route.fulfill(
        body=vendor + probe, content_type="application/javascript"))
    page.evaluate("Object.defineProperty(navigator, 'canShare', {value: () => false, configurable: true})")
    team = page.locator("#tx-team")
    team.select_option("Oregon")
    visible = page.locator(".tx-card:visible")
    assert visible.count() > 1
    card = visible.filter(has_text="1423799198175739904")
    details = card.locator(".tx-fit details")
    toggle = details.first.locator("summary")
    toggle.click()
    assert details.first.get_attribute("open") is not None
    assert details.last.get_attribute("open") is None

    def export(button):
        with page.expect_download(timeout=60000) as result:
            button.click()
        download = result.value
        assert download.suggested_filename.endswith(".png")
        assert download.failure() is None
        png = download.path().read_bytes()
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        assert min(struct.unpack(">II", png[16:24])) > 0
        data = page.evaluate("window.__tradeExport")
        assert data["buttons"] == 0
        assert all(data["geometry"]), "Exported grade rows overlap"
        return data

    single = export(card.get_by_role("button", name="Save image: Arizona State – Oregon · 2026-11-04"))
    assert single["titles"] == ["Arizona State – Oregon · 2026-11-04"]
    assert single["details"] == [[{"open": True, "hasText": True}, {"open": False, "hasText": False}]]
    assert single["team"] is None

    section = export(page.locator("section.fold").first.locator(":scope > .snap-btn"))
    assert section["titles"] == visible.evaluate_all("(cards) => cards.map(c => c.dataset.snapCard)")
    assert section["team"] == "Oregon"
    assert section["explainer"] is False
    assert section["details"][section["titles"].index(single["titles"][0])] == single["details"][0]
    assert details.first.get_attribute("open") is not None
    assert details.last.get_attribute("open") is None
    assert not page.locator(".tx-explainer .tx-note").is_visible()
    toggle.click()
    team.select_option("")


def main():
    with (ROOT / "data" / "Teams.csv").open(encoding="utf-8-sig", newline="") as file:
        pac_teams = sorted({r["Team"].strip() for r in DictReader(file) if r["League"].strip() == "NCAA PAC 12"})
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
                nav = page.locator('nav[data-current="transactions"]')
                nav.locator("a").first.wait_for()
                tx_link = nav.locator('a[href$="/transactions.html"]')
                assert tx_link.count() == 0, "Transactions leaked into normal navigation"
                page.evaluate("localStorage.setItem('ncaa180.dev', '1')")
                page.reload()
                tx_link.wait_for(state="visible")
                assert tx_link.count() == 1
                page.evaluate("localStorage.removeItem('ncaa180.dev')")
                page.reload()
                nav.locator("a").first.wait_for()
                assert tx_link.count() == 0
                count = page.locator(".tx-card").count()
                assert count > 50, f"Too few cards: {count}"
                assert page.locator("section.fold").count() == 3
                assert page.locator("section.fold > .snap-btn").count() == 3
                assert page.locator(".tx-card .snap-card-btn").count() == count
                page.evaluate("(theme) => document.documentElement.setAttribute('data-theme', theme)", theme)
                explainer = page.locator("details.tx-explainer")
                toggle = explainer.get_by_text("How trade grades work", exact=True)
                explanation = explainer.locator(".tx-note")
                assert toggle.is_visible()
                assert explainer.get_attribute("open") is None
                assert not explanation.is_visible()
                if width == 390:
                    toggle.click()
                else:
                    toggle.focus()
                    page.keyboard.press("Enter")
                assert explanation.is_visible()
                assert "FantasyCalc" in explanation.inner_text()
                toggle.click()
                assert not explanation.is_visible()
                assert page.locator("[data-score]").count() > 0
                assert page.locator('.tx-fit strong[aria-label="Team Fit unavailable"]').first.text_content() == "-"
                fit_card = page.locator(".tx-card").filter(has_text="1425957598431035392")
                fits = fit_card.locator(".tx-fit")
                assert fits.locator("strong").all_text_contents() == ["Even", "A"]
                assert fits.locator(".tx-side-value > small").count() == 0
                disclosure = fits.get_by_text("Fit details", exact=True).first
                disclosure.click()
                assert fits.get_by_text("Projected hold comparison:", exact=False).first.is_visible()
                disclosure.click()
                # Reviewer-facing visual evidence, captured without altering the repository.
                shot = ROOT / "work" / "transactions-preview"
                shot.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot / f"transactions-{width}-{theme}.png"), full_page=False)
                featured = page.locator(".tx-card.tx-blockbuster")
                assert featured.count() == 4
                for trade_id in ("1414580639092518912", "1412325964028899328", "1426656560473452544",
                                 "1425957598431035392"):
                    assert featured.filter(has_text=trade_id).get_by_text("Blockbuster", exact=True).count() == 1
                assert featured.filter(has_text="1426733052746272768").count() == 0
                assert page.get_by_text("Dynasty concentration edge", exact=False).count() > 0
                tech = page.locator(".tx-card").filter(has_text="1426087744886558720")
                assert tech.get_by_text("Georgia Tech by 583 points", exact=False).count() == 1
                assert tech.locator(".tx-fit strong").all_text_contents() == ["A", "F"]
                montana_od = page.locator(".tx-card").filter(has_text="1426656560473452544")
                assert "≈ Pick 3.12" in montana_od.locator(".tx-surplus").inner_text()
                oregon = page.locator(".tx-card").filter(has_text="1423799198175739904")
                assert oregon.get_by_text("4.12 → 2.10", exact=False).count() == 1
                assert "2027" not in oregon.locator(".tx-surplus").inner_text()
                assert oregon.get_by_text("+725 pts (4.12 proxy)", exact=False).count() == 1
                wisconsin = page.locator(".tx-card").filter(has_text="1427749292088516608")
                rebuild = wisconsin.locator(".tx-grade").filter(has_text="Rebuild value")
                assert set(rebuild.locator("strong").all_text_contents()) == {"B", "D"}
                assert set(rebuild.locator("small").all_text_contents()) == {"1,557 pts", "777 pts"}
                assert rebuild.locator('[title*="Grade capped from A"]').count() == 1
                boston_miami = page.locator(".tx-card").filter(has_text="1426089963417534464")
                contender = boston_miami.locator(".tx-grade").filter(has_text="Contender value")
                assert contender.locator("strong").all_text_contents() == ["C-", "C+"]
                assert contender.locator("small").all_text_contents() == ["0 pts", "128 pts"]
                assert oregon.locator(".tx-pos").all_text_contents() == ["RB", "K", "RB", "WR"]
                assert oregon.locator(".tx-pos-k").evaluate("el => getComputedStyle(el).backgroundColor") == "rgb(201, 184, 242)"
                assert oregon.locator(".tx-pick .tx-pos").count() == 0
                asu_oregon_fit = oregon.locator(".tx-fit strong")
                market = oregon.locator(".tx-grade").filter(has_text="Contender value").locator("strong")
                assert asu_oregon_fit.all_text_contents() == ["B", "B+"]
                assert float(market.last.get_attribute("data-score")) == 0
                assert float(market.last.get_attribute("data-color-score")) > 45
                assert market.last.evaluate(
                    "el => getComputedStyle(el).color === "
                    "NCAA180.colors.scale(Number(el.dataset.colorScore) / 100).replaceAll(',', ', ')"
                )
                assert asu_oregon_fit.last.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") > (
                    1.8 * market.last.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
                )
                # Filter to a team on the first trade. Revert filter.
                first = page.locator(".tx-card").first
                team = first.get_attribute("data-teams").split("|")[0]
                page.locator("#tx-team").select_option(label=team)
                assert 0 < page.locator(".tx-card:visible").count() <= count
                page.locator("#tx-team").select_option("")
                assert page.locator(".tx-card:visible").count() == count
                conference_filter = page.locator("#tx-conference")
                team_filter = page.locator("#tx-team")
                all_teams = team_filter.locator("option").evaluate_all("(os) => os.map(o => o.value)")
                team_filter.select_option("Oregon")
                conference_filter.select_option("NCAA PAC 12")
                assert team_filter.locator("option").evaluate_all("(os) => os.map(o => o.value)") == ["", *pac_teams]
                assert team_filter.input_value() == "Oregon"  # Still a valid selection.
                filtered = page.locator(".tx-card:visible")
                assert filtered.count() > 0
                assert all("Oregon" in names.split("|") for names in
                           filtered.evaluate_all("(cards) => cards.map(c => c.dataset.teams)"))
                conference_filter.select_option("NCAA BIG 10")
                assert team_filter.input_value() == ""  # Oregon is no longer valid.
                assert team_filter.locator("option[value=Oregon]").count() == 0
                assert filtered.count() > 0
                assert set(filtered.evaluate_all("(cards) => cards.map(c => c.dataset.conference)")) == {"NCAA BIG 10"}
                conference_filter.select_option("")
                assert team_filter.locator("option").evaluate_all("(os) => os.map(o => o.value)") == all_teams
                assert filtered.count() == count
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
                if width == 390:
                    check_trade_exports(page)
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
