"""Real coin toss (Chris, 2026-11-12): no hidden toss for division titles or the playoff cut.

A tie that survives win %, points for and points against stays tied in real-toss mode until a
real toss is recorded in config tiebreakers.coin_toss_results; lower-stakes orders keep the
simulated (reproducible) toss and report it."""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import league_config as lcfg  # noqa: E402
import tiebreak  # noqa: E402


def teams():
    return pd.DataFrame([
        {"Team": "Alpha", "LeagueID": "1", "RosterID": "1", "Wins": 8, "Losses": 3, "Ties": 0, "PointsFor": 1500.0, "PointsAgainst": 1400.0},
        {"Team": "Bravo", "LeagueID": "1", "RosterID": "2", "Wins": 8, "Losses": 3, "Ties": 0, "PointsFor": 1450.5, "PointsAgainst": 1300.0},
        {"Team": "Charlie", "LeagueID": "2", "RosterID": "1", "Wins": 8, "Losses": 3, "Ties": 0, "PointsFor": 1450.5, "PointsAgainst": 1300.0},
        {"Team": "Delta", "LeagueID": "2", "RosterID": "2", "Wins": 7, "Losses": 4, "Ties": 0, "PointsFor": 1600.0, "PointsAgainst": 1200.0},
    ])


def with_cfg(monkeypatch, order, results):
    c = dict(lcfg.cfg())
    c["tiebreakers"] = {"order": order, "coin_toss_results": results}
    monkeypatch.setattr(lcfg, "cfg", lambda: c)


ORDER = ["win_pct", "points_for", "points_against", "coin_toss"]


def test_real_toss_mode_leaves_exact_tie_unresolved(monkeypatch):
    with_cfg(monkeypatch, ORDER, [])
    out, tied, tosses = tiebreak.order(teams(), label="2026", real_toss=True)
    assert list(out["Team"])[0] == "Alpha" and list(out["Team"])[3] == "Delta"
    assert tied == [["Bravo", "Charlie"]] and tosses == []


def test_recorded_real_toss_is_applied(monkeypatch):
    with_cfg(monkeypatch, ORDER, [{"year": 2026, "teams": ["Bravo", "Charlie"], "order": ["Charlie", "Bravo"]}])
    out, tied, _ = tiebreak.order(teams(), label="2026", real_toss=True)
    assert list(out["Team"]) == ["Alpha", "Charlie", "Bravo", "Delta"] and tied == []


def test_recorded_toss_only_for_its_season(monkeypatch):
    with_cfg(monkeypatch, ORDER, [{"year": 2025, "teams": ["Bravo", "Charlie"], "order": ["Charlie", "Bravo"]}])
    _, tied, _ = tiebreak.order(teams(), label="2026", real_toss=True)
    assert tied == [["Bravo", "Charlie"]]


def test_simulated_toss_still_used_and_reported_elsewhere(monkeypatch):
    with_cfg(monkeypatch, ORDER, [])
    out, tied, tosses = tiebreak.order(teams(), label="2026")
    assert tied == [] and tosses == [["Bravo", "Charlie"]]
    again, _, _ = tiebreak.order(teams(), label="2026")
    assert list(out["Team"]) == list(again["Team"])  # reproducible
