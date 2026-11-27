"""Verify league routing and Sleeper mentions for published matchups."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

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
