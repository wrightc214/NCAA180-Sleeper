"""Static Selection Watch build contract; does not require the live API."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "reports/selection-watch.html"


def test_page_is_generated_and_menu_wired():
    """The tab is public for CCG (Chris, 2026-11-20); the Playoffs page went public 2026-11-24 (Chris) through its
    sub-row item (config/nav.json rows.selection-watch), which also drives the DEV bar."""
    src = (ROOT / "scripts/selection_watch_page.py").read_text(encoding="utf-8")
    html = PAGE.read_text(encoding="utf-8")
    assert 'data-current="selection-watch"' in html and 'data-row="selection-watch"' in html
    nav = json.loads((ROOT / "config/nav.json").read_text(encoding="utf-8"))
    playoffs = [i for i in nav["rows"]["selection-watch"]["items"] if i["href"] == "selection-watch.html"]
    assert playoffs and playoffs[0]["state"] == "visible"
    for name in ("sw-status-section", "sw-board", "sw-playins", "sw-final-playins", "sw-bubble", "sw-locks", "sw-noimpact"):
        assert f'id="{name}"' in html
        assert f'data-save="{name}"' in html
    assert 'selection-watch-core.js' in html
    assert 'selection-watch.js' in html
    assert 'scoreboard-overview-model.js' in html
    assert "page_head(" in src and "menu_html(" in src


def test_previews_do_not_replace_live_file():
    folder = ROOT / "reports/postseason"
    historical = json.loads((folder / "selection-watch-2025.json").read_text())
    provisional = json.loads((folder / "selection-watch-provisional-2026.json").read_text())
    assert historical["year"] == 2025 and historical.get("provisional") is not True
    assert provisional["year"] == 2026 and provisional["provisional"] is True
    assert len(historical["ccg"]) == len(provisional["ccg"]) == 15
    assert len(historical["play_ins"]) == 1
    assert isinstance(provisional["play_ins"], list)
    assert len(historical["order"]) == len(provisional["order"]) == 180
    assert not (folder / "selection-watch.json").exists() or (
        "provisional" not in json.loads((folder / "selection-watch.json").read_text()))


def test_generator_uses_safe_defaults_and_escapes_owner_labels(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import selection_watch_page as generator

    output = tmp_path / "selection-watch.html"
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(generator, "PAGE", str(output))
    monkeypatch.setattr(generator.lcfg, "cfg", lambda: {})
    monkeypatch.setattr(generator.lcfg, "selection_watch", lambda: {})
    generator.main()
    html = output.read_text(encoding="utf-8")
    assert "<title>Selection Watch | NCAA 180</title>" in html
    assert '<summary>Steal Board <button' in html

    monkeypatch.setattr(generator.lcfg, "cfg", lambda: {
        "brand": "Example & Co.",
    })
    monkeypatch.setattr(generator.lcfg, "selection_watch", lambda: {
        "labels": {"title": "Playoffs <Now>", "steal_board": "Ignored old override"},
    })
    generator.main()
    html = output.read_text(encoding="utf-8")
    assert "<title>Playoffs &lt;Now&gt; | Example &amp; Co.</title>" in html
    assert 'data-sw-label="title">Playoffs &lt;Now&gt;<' in html
    assert '<summary>Steal Board <button' in html
    assert '<summary>Bubble odds <button' in html


def test_hidden_nav_state_hides_only_selection_watch(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import site_common

    monkeypatch.chdir(ROOT)
    config = site_common.nav_config()
    selection = next(tab for tab in config["tabs"] if tab["id"] == "selection-watch")
    monkeypatch.setattr(site_common, "nav_config", lambda: config)
    for state in ("hidden-dev", "hidden"):
        selection["state"] = state
        tabs = {t["id"]: t.get("state") for t in site_common.menu_data()["tabs"]}
        assert tabs["transactions"] is None
        if state == "hidden":
            assert "selection-watch" not in tabs
            assert site_common.page_state("selection-watch") == "hidden"
        else:
            assert tabs["selection-watch"] == "hidden-dev"


def test_disabled_publisher_leaves_existing_data_and_keeps_private_alerts(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import selection_watch

    monkeypatch.chdir(ROOT)
    live = tmp_path / "live.json"
    live.write_text("existing", encoding="utf-8")
    preview = tmp_path / "preview.json"
    alerts = []
    monkeypatch.setattr(selection_watch, "OUT", str(live))
    import site_common

    cfg = site_common.nav_config()
    next(tab for tab in cfg["tabs"] if tab["id"] == "selection-watch")["state"] = "hidden"
    monkeypatch.setattr(site_common, "nav_config", lambda: cfg)
    monkeypatch.setattr(selection_watch.ps, "last_regular_week", lambda: 11)
    monkeypatch.setattr(selection_watch.ps, "completed_weeks", lambda year: list(range(1, 12)))
    monkeypatch.setattr(selection_watch, "build", lambda year, **kwargs: {"ccg": [{"id": 1}]})
    monkeypatch.setattr(selection_watch, "toss_risks", lambda year, data: ["test"])
    monkeypatch.setattr(selection_watch, "toss_alert", lambda year, risks: alerts.append((year, risks)))
    monkeypatch.setattr(sys, "argv", ["selection_watch.py", "--year", "2026"])
    selection_watch.main()
    assert live.read_text(encoding="utf-8") == "existing"
    assert alerts == [(2026, ["test"])]
    monkeypatch.setattr(sys, "argv", ["selection_watch.py", "--year", "2026", "--provisional", "--output", str(preview)])
    selection_watch.main()
    assert not preview.exists()
