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
    final_four = (tmp_path / "ceremony-2025-16.html").read_text(encoding="utf-8")
    assert "<small>Rose Bowl - Final Four</small>" in final_four
    championship = (tmp_path / "ceremony-2025-17.html").read_text(encoding="utf-8")
    assert "<small>Stagg Bowl - NIT Champ</small>" in championship
    past_final = (tmp_path / "ceremony-2022-18.html").read_text(encoding="utf-8")
    assert "Dwight Fight" in past_final
    menu = menu_data(str(tmp_path))
    rows = menu["rows"]
    assert any(item["label"] == "2019" for item in rows["awards-seasons"]["items"])
    assert {"label": "CCG", "href": ccg["href"]} in rows["awards-weeks-2025"]["items"]
    assert all(item.get("state", "visible") == "visible" for item in rows["awards-seasons"]["items"])
    assert menu["awards"] in {item["href"] for item in rows["awards-seasons"]["items"]}
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
