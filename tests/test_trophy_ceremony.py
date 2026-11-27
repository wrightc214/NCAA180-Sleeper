"""Coverage for Awards placement, historical rebuilds and Discord deduplication."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import trophy_ceremony as ceremony
from site_common import menu_data


def test_historical_ceremonies_and_awards_navigation(tmp_path, monkeypatch):
    monkeypatch.setattr(ceremony, "REPORTS", tmp_path)
    manifest = ceremony.build()
    assert {item["year"] for item in manifest} >= set(range(2019, 2026))
    ccg = next(item for item in manifest if item["year"] == 2025 and item["label"] == "CCG")
    assert ccg["week"] == 12
    page = (tmp_path / ccg["href"]).read_text(encoding="utf-8")
    assert "Conference Championships" in page
    assert 'id="trophy-ceremony"' in page
    past_final = (tmp_path / "ceremony-2022-18.html").read_text(encoding="utf-8")
    assert "Dwight Fight" in past_final
    rows = menu_data(str(tmp_path))["rows"]
    assert any(item["label"] == "2019" for item in rows["awards-seasons"]["items"])
    assert {"label": "CCG", "href": ccg["href"], "state": "hidden-dev"} in rows["awards-weeks-2025"]["items"]
    assert all(item["state"] == "hidden-dev" for item in rows["awards-seasons"]["items"])
    assert menu_data(str(tmp_path))["awards"] is None
    assert ceremony.build() == manifest


def test_unknown_bowl_goes_to_year_end_and_late_results_edit_same_post():
    bowl = dict(Season="2026", EventType="Bowl", Event="Test Bowl", Round="", Team="A", Conference="ACC")
    groups = ceremony.group_awards([bowl, bowl], [])
    assert groups == {(2026, None): [bowl]}
    assert ceremony.group_awards([bowl], [{**bowl, "Week": 15}]) == {(2026, 15): [bowl]}
    initial = dict(year=2026, week=15, key="2026-15", digest="first")
    posted = {"2026-15": dict(digest="first", destination="42", id="123")}
    assert ceremony.pending_posts([initial], posted, 2026, "42") == []
    revised = {**initial, "digest": "late-winner"}
    assert ceremony.pending_posts([revised], posted, 2026, "42") == [revised]
    assert ceremony.pending_posts([revised], posted, 2027, "42") == []
