"""Archive results come from recorded games, not the live selection formula."""
import json
import sys
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
