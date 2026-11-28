"""Guillotine survivor delivery uses only the complete, frozen cut."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sleeper_guillotine_survivors import survivor_posts


def test_survivor_posts_tag_local_managers_and_skip_recorded_deliveries():
    base = {"Year": "2026", "Week": "12", "FieldSize": "4", "FrozenAt": "timestamp"}
    rows = [
        dict(base, LeagueID="100", RosterID="1", Team="Arizona State", Status="Advanced"),
        dict(base, LeagueID="100", RosterID="2", Team="Utah", Status="Advanced"),
        dict(base, LeagueID="200", RosterID="1", Team="Clemson", Status="Eliminated"),
        dict(base, LeagueID="200", RosterID="2", Team="Auburn", Status="Eliminated"),
    ]
    def handle(league, roster):
        assert league == "100"
        return "wrightc214" if roster == "1" else ""

    args = (rows, "2026", 12, {"100", "200"})
    posts = list(survivor_posts(*args, {}, handle))
    assert len(posts) == 1
    key, league, text = posts[0]
    assert league == "100"
    assert "Arizona State & @wrightc214\nUtah\n" in text
    assert "Week 13" in text
    assert list(survivor_posts(*args, {key: {"status": "pending"}}, handle)) == []
    assert list(survivor_posts(*args, {key: {"status": "sent"}}, handle)) == []
    assert list(survivor_posts(rows[:-1], *args[1:], {}, handle)) == []
