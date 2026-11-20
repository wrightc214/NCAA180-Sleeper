"""Archive results come from recorded games, not the live selection formula."""
import json
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import selection_watch_history as history


def test_archive_matches_source_and_older_playoff_formats():
    data = history.build()
    assert data == json.loads(history.OUTPUT.read_text(encoding="utf-8"))
    assert set(data) >= {str(year) for year in range(2019, 2026)}
    for year in range(2019, 2026):
        season = data[str(year)]
        assert len(season["ccg"]) == (11 if year == 2019 else 15)
        assert len(season["field"]) == (16 if year == 2019 else 32)
        assert [row["seed"] for row in season["field"]] == list(range(1, len(season["field"]) + 1))
    assert data["2020"]["champion"] == "Campbell"
    assert any(row["team"] == "Dixie State" for row in data["2020"]["field"])


def test_rescored_ccgs_keep_as_played_scores_and_winners():
    games = [(year, game) for year, season in history.build().items() for game in season["ccg"]]
    rescored = [(year, g) for year, g in games if "standard_a" in g or "standard_b" in g]
    assert len(rescored) == 17
    big_sky = next(g for year, g in rescored if year == "2020" and g["conference"] == "Big Sky")
    assert (big_sky["score_a"], big_sky["score_b"], big_sky["winner"]) == (222.08, 144.60, "Villanova")
    assert (big_sky["standard_a"], big_sky["standard_b"]) == (220.08, 146.60)


def test_modern_final_steal_labels_are_verified_against_actual_field():
    data = history.build()
    assert {g["winner"] for g in data["2025"]["ccg"] if g.get("label") == "Stolen"} == {"Kansas State", "Nevada"}
    assert {g["winner"] for g in data["2024"]["ccg"] if g.get("label") == "Stolen"} == {"Jackson State", "UAB"}
    assert {g["winner"] for g in data["2025"]["ccg"] if g.get("label") == "Play-in winner"} == {"Georgia Southern"}
    assert {g["winner"] for g in data["2024"]["ccg"] if g.get("label") == "Play-in winner"} == {"Eastern Kentucky"}
    for year in ("2019", "2020"):
        assert not any(g.get("label") for g in data[year]["ccg"])
        assert "cut_board" not in data[year]


def test_owner_field_exception_restores_2022_board():
    data = history.build()
    board = data["2022"]["cut_board"]
    assert [(x["in"], x["out"]) for x in board["exceptions"]] == [("Central Michigan", "Texas Tech")]
    assert any(g.get("label") == "Stolen" for g in data["2022"]["ccg"])
    assert "Central Michigan" in {row["team"] for row in data["2022"]["field"]}
    assert "Texas Tech" not in {row["team"] for row in data["2022"]["field"]}
    for year in ("2021", "2023", "2024", "2025"):
        assert "exceptions" not in data[year]["cut_board"]


def _config(tmp_path, exceptions):
    path = tmp_path / "selection_watch.json"
    path.write_text(json.dumps({"field_exceptions": exceptions}), encoding="utf-8")
    return path


def test_without_the_exception_2022_has_no_board(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "CONFIG", _config(tmp_path, {}))
    data = history.build()
    assert "cut_board" not in data["2022"]
    assert not any(g.get("label") for g in data["2022"]["ccg"])
    assert "cut_board" in data["2025"]


@pytest.mark.parametrize("entry", [
    {"in": "Texas Tech", "out": "Central Michigan", "note": "reversed"},
    {"in": "Central Michigan", "out": "Brown", "note": "wrong team out"},
    {"in": "Central Michigan", "out": "Texas Tech", "note": ""},
])
def test_stale_or_incomplete_exceptions_fail_loudly(tmp_path, monkeypatch, entry):
    monkeypatch.setattr(history, "CONFIG", _config(tmp_path, {"2022": [entry]}))
    with pytest.raises(ValueError):
        history.build()
