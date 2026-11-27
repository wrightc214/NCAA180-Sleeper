"""Verify league routing and Sleeper mentions for published matchups."""
from datetime import datetime as notifications_date
import json
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sleeper_postseason_matchups as notifications
from sleeper_postseason_matchups import matchup_posts


def test_postseason_matchups_route_only_pending_current_round_games():
    base = {
        "Year": "2026", "Week": "13", "Round": "Playoff", "Status": "Pending",
        "BowlName": "", "PlayoffRound": "First Round", "Stage": "First Round",
    }
    first = {"LeagueID": "100", "RosterID": "1", "Team": "Arizona State"}
    second = {"LeagueID": "200", "RosterID": "2", "Team": "Auburn"}
    rows = [
        {**base, **side, "GameID": game, **overrides}
        for game, overrides in [
            ("active", {}), ("final", {"Status": "Final"}), ("future", {"Week": "14"}),
            ("ccg", {"Round": "CCG"}),
        ]
        for side in (first, second)
    ]
    handles = {("100", "1"): "manager_one", ("200", "2"): "manager_two"}
    posts = list(matchup_posts(rows, "2026", "13", {"100", "200"},
                               lambda league, roster: handles[league, roster], {}))
    assert len(posts) == 2
    assert posts[0][1] == "100"
    assert "Arizona State & @manager_one vs. Auburn\n" in posts[0][2]
    assert posts[1][1] == "200"
    assert "Arizona State vs. Auburn & @manager_two\n" in posts[1][2]
    assert list(matchup_posts(rows, "2026", "13", {"100", "200"},
                              lambda league, roster: handles[league, roster],
                              {posts[0][0]: {"status": "pending"}})) == posts[1:]


def test_same_league_mentions_both_managers_once():
    base = {
        "Year": "2026", "Week": "13", "Round": "Bowl", "Status": "Pending",
        "BowlName": "Rose Bowl", "PlayoffRound": "", "Stage": "", "GameID": "bowl",
        "LeagueID": "100",
    }
    rows = [dict(base, RosterID="1", Team="Arizona State"), dict(base, RosterID="2", Team="Utah")]
    posts = list(matchup_posts(rows, "2026", "13", {"100"},
                               lambda league, roster: {"1": "one", "2": "two"}[roster], {}))
    assert len(posts) == 1
    assert "Arizona State & @one vs. Utah & @two\n" in posts[0][2]


def test_review_code_changes_on_scoring_correction_or_new_pairing(monkeypatch):
    game = {field: "" for field in (
        "GameID", "Round", "Stage", "BowlName", "PlayoffRound", "LeagueID",
        "RosterID", "Team", "Seed", "Status", "Outcome", "Points",
    )}
    game.update(Year="2026", Week="13", GameID="first", Team="Auburn", Status="Pending")
    roster = {"roster_id": 1, "points": 100.1, "players_points": {"sample": 10.1}}
    monkeypatch.setattr(notifications, "fetch_json", lambda url: [roster])
    args = ([game], "2026", 13, {"100"}, [("key", "100", "caption")])
    original = notifications.review_code(*args)
    assert notifications.review_code(*args) == original
    roster["points"] = 100.2
    assert notifications.review_code(*args) != original
    roster["points"] = 100.1
    game["Team"] = "Clemson"
    assert notifications.review_code(*args) != original


@pytest.mark.parametrize("approval", [None, "stale", "current"])
def test_wednesday_sends_only_the_approved_unchanged_slate(tmp_path, monkeypatch, approval):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SLEEPER_SESSION_TOKEN", "test-token")
    monkeypatch.setattr(sys, "argv", ["sleeper_postseason_matchups.py", "--scheduled"])
    monkeypatch.setattr(notifications.week_gate, "state", lambda: ("2026", 13, "regular"))
    monkeypatch.setattr(notifications.league_config, "cfg", lambda: {
        "schedule": {"postseason_start_week": 13, "postseason_end_week": 17},
    })
    class Wednesday:
        @staticmethod
        def now(zone):
            return notifications_date(2026, 12, 2)

    monkeypatch.setattr(notifications, "datetime", Wednesday)
    data = tmp_path / "data"
    data.mkdir()
    (data / "LeagueIDs_AllYears.csv").write_text("Year,LeagueID\n2026,100\n", encoding="utf-8")
    if approval:
        (tmp_path / notifications.APPROVALS).write_text(
            json.dumps({"2026/13": approval}), encoding="utf-8",
        )

    class PublishedSlate:
        def to_dict(self, orient):
            return []

    posts = [("2026/13/first/100", "100", "Auburn & @one vs. Clemson")]
    monkeypatch.setattr(notifications.postseason, "read_season", PublishedSlate)
    monkeypatch.setattr(notifications, "matchup_posts", lambda *args: iter(posts))
    monkeypatch.setattr(notifications, "review_code", lambda *args: "current")
    calls = []
    monkeypatch.setattr(notifications, "post_private_review", lambda *args: calls.append("review"))
    monkeypatch.setattr(notifications, "save_state", lambda records, message: calls.append(message))
    monkeypatch.setattr(notifications, "send_post", lambda *args: calls.append("send") or "123")
    if approval == "stale":
        with pytest.raises(SystemExit, match="changed after approval"):
            notifications.main()
        assert calls == ["review"]
    else:
        notifications.main()
        assert calls == ([
            "Reserve Sleeper matchup post 2026/13/first/100",
            "send",
            "Confirm Sleeper matchup post 2026/13/first/100",
        ] if approval else [])
