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


def test_hold_code_is_stable_per_week():
    code = notifications.hold_code("2026", 13)
    assert code == notifications.hold_code("2026", 13)
    assert code != notifications.hold_code("2026", 14)
    assert len(code) == 10


def _wednesday_setup(tmp_path, monkeypatch, week, argv):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SLEEPER_SESSION_TOKEN", "test-token")
    monkeypatch.setattr(sys, "argv", ["sleeper_postseason_matchups.py", *argv])
    monkeypatch.setattr(notifications.week_gate, "state", lambda: ("2026", week, "postseason"))
    monkeypatch.setattr(notifications.league_config, "cfg", lambda: {
        "schedule": {"postseason_start_week": 13, "postseason_end_week": 17},
        "postseason": {
            "playoff": {"first_week": 13}, "bowls": {"tiers": [{"week": 13}]},
            "nit": {"group_stage_1": {"week": 13}},
        },
    })
    monkeypatch.setattr(notifications.postseason, "league_short", lambda: {"SEC": "NCAA SEC"})

    class Wednesday:
        @staticmethod
        def now(zone):
            return notifications_date(2026, 12, 2)

    monkeypatch.setattr(notifications, "datetime", Wednesday)
    data = tmp_path / "data"
    data.mkdir()
    (data / "LeagueIDs_AllYears.csv").write_text("Year,LeagueID,LeagueName\n2026,100,NCAA SEC\n", encoding="utf-8")

    class PublishedSlate:
        def to_dict(self, orient):
            return []

    key = f"2026/{week}/first/100"
    posts = [(key, "100", "Auburn & @one vs. Clemson")]
    monkeypatch.setattr(notifications.postseason, "read_season", PublishedSlate)
    monkeypatch.setattr(notifications, "matchup_posts",
                        lambda *args, events, **kwargs: iter(posts if "Playoff" in events else []))
    calls = []
    monkeypatch.setattr(notifications, "post_private_review", lambda *args: calls.append("review"))
    monkeypatch.setattr(notifications, "save_state",
                        lambda records, message, path=None: calls.append(message))
    monkeypatch.setattr(notifications, "send_post", lambda *args: calls.append("send") or "123")
    return key, calls


@pytest.mark.parametrize("week, held", [(13, False), (13, True), (14, False)])
def test_wednesday_sends_unless_the_opening_week_is_held(tmp_path, monkeypatch, week, held):
    key, calls = _wednesday_setup(tmp_path, monkeypatch, week, ["--scheduled"])
    if held:
        (tmp_path / notifications.HOLDS).write_text(
            json.dumps({f"2026/{week}": {"held": True}}), encoding="utf-8",
        )
    notifications.main()
    assert calls == ([] if held else [
        f"Reserve Sleeper matchup post {key}",
        "send",
        f"Confirm Sleeper matchup post {key}",
    ])


def test_hold_code_records_hold_for_opening_week_only(tmp_path, monkeypatch):
    _, calls = _wednesday_setup(tmp_path, monkeypatch, 13, ["--hold", "wrong"])
    with pytest.raises(SystemExit, match="not for the current week"):
        notifications.main()
    monkeypatch.setattr(sys, "argv", ["x", "--hold", notifications.hold_code("2026", 13)])
    notifications.main()
    assert calls == ["Hold Sleeper opening matchups for 2026/13"]
    monkeypatch.setattr(notifications.week_gate, "state", lambda: ("2026", 14, "postseason"))
    monkeypatch.setattr(sys, "argv", ["x", "--hold", notifications.hold_code("2026", 14)])
    with pytest.raises(SystemExit, match="no opening posts to hold"):
        notifications.main()


def test_review_posts_hold_code_only_in_opening_week(tmp_path, monkeypatch):
    _, calls = _wednesday_setup(tmp_path, monkeypatch, 13, ["--review"])
    notifications.main()
    assert calls == ["review"]


@pytest.mark.parametrize("week,expected", [(13, True), (14, False)])
def test_cut_line_is_only_on_initial_playoff_posts(tmp_path, monkeypatch, capsys, week, expected):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["sleeper_postseason_matchups.py"])
    monkeypatch.setattr(notifications.week_gate, "state", lambda: ("2026", week, "postseason"))
    monkeypatch.setattr(notifications.league_config, "cfg", lambda: {
        "schedule": {"postseason_start_week": 13, "postseason_end_week": 17},
        "postseason": {
            "playoff": {"first_week": 13}, "bowls": {"tiers": [{"week": 13}]},
            "nit": {"group_stage_1": {"week": 13}},
        },
    })
    monkeypatch.setattr(notifications.postseason, "league_short", lambda: {"SEC": "NCAA SEC"})
    data = tmp_path / "data"
    data.mkdir()
    (data / "LeagueIDs_AllYears.csv").write_text("Year,LeagueID,LeagueName\n2026,100,NCAA SEC\n", encoding="utf-8")
    (tmp_path / notifications.postseason.FIELD_FILE).write_text(
        "Year,BidType,Wins,Losses,PointsFor\n2026,At-Large,9,3,1700\n"
        "2026,At-Large,8,4,1642.3\n2026,Auto,6,6,1510\n", encoding="utf-8",
    )
    game = dict(Year="2026", Week=str(week), Round="Playoff", GameID="game",
                Status="Pending", BowlName="", PlayoffRound="Round", Stage="", LeagueID="100")

    class PublishedSlate:
        def to_dict(self, orient):
            return [dict(game, Team="Auburn", RosterID="1"), dict(game, Team="Clemson", RosterID="2")]

    monkeypatch.setattr(notifications.postseason, "read_season", PublishedSlate)
    monkeypatch.setattr(notifications, "fetch_json", lambda url: [])
    notifications.main()
    output = capsys.readouterr().out
    assert "Auburn vs. Clemson" in output
    assert ("Last at-large in: 8–4, 1,642.3 pts. Think there's an error? Let us know." in output) == expected


def test_nit_opening_group_includes_all_managers_in_their_home_leagues():
    base = dict(Year="2026", Week="13", Round="NIT", Status="Pending", GameID="group-a",
                BowlName="Group A", PlayoffRound="", Stage="Opening Groups")
    roster_data = [("100", "1", "Auburn"), ("100", "2", "Clemson"), ("200", "3", "Utah")]
    rows = [dict(base, LeagueID=league, RosterID=roster, Team=team)
            for league, roster, team in roster_data]
    posts = list(matchup_posts(rows, "2026", "13", {"100", "200"},
                               lambda league, roster: f"manager_{roster}", {}))
    assert len(posts) == 2
    assert "Auburn & @manager_1 · Clemson & @manager_2 · Utah" in posts[0][2]
    assert "Auburn · Clemson · Utah & @manager_3" in posts[1][2]
