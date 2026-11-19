"""Approve historical Team Fit behavior independently of market pricing."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from trade_fit_store import FileArchive, FitLedger, publish_snapshot
from transactions_fit import (DEFAULTS, CONTEXT, PICKS, PICK_VALUES, PLAYER_VALUES, ROSTERS, TX,
                              TeamFit, age_factor, contender_weight, event_key, fit_grade)
from transactions_grades import load_config, read_rows
from transactions_page import PLAYERS, TEAMS, TRANSACTIONS, build_teams, render_fit, trade_assets


def test_rb_age_only_discounts_future_years_and_crosses_cliff_continuously():
    curve = DEFAULTS["age_curves"]["RB"]
    assert age_factor(24, 2, curve) == 1
    assert age_factor(28, 1, curve) == pytest.approx(.85)
    assert age_factor(31, 1, curve) == pytest.approx(.60)
    assert age_factor(30, 1, curve) == pytest.approx((.85 * .60) ** .5)
    assert age_factor(None, 2, curve) == 1


def test_poor_market_price_can_be_good_rebuild_fit_but_poor_hold_return_is_not():
    # A clear pre-deadline rebuilder doesn't pay for the lost current starts.
    score, _ = fit_grade(-5000, 2500, .10, 0, DEFAULTS)
    assert score == 60
    assert fit_grade(-5000, -2500, .10, 0, DEFAULTS)[0] == 40
    assert fit_grade(0, 0, .70, 1, DEFAULTS)[0] == 50


def test_bowl_makes_some_difference_but_less_than_playoff_race():
    standing = {"W": "4", "L": "5", "T": "0", "Contender": "0.2"}
    none = contender_weight(standing, {"Playoff": 0, "Bowl": 0}, DEFAULTS)
    bowl = contender_weight(standing, {"Playoff": 0, "Bowl": .5}, DEFAULTS)
    playoff = contender_weight(standing, {"Playoff": .5, "Bowl": 0}, DEFAULTS)
    assert none < bowl < playoff


def test_missing_fit_is_a_hyphen_not_even():
    assert render_fit(None) == '<strong aria-label="Team Fit unavailable">-</strong>'


@pytest.fixture(scope="module")
def trade_inputs():
    transactions = read_rows(TRANSACTIONS)
    players = {p["player_id"]: p for p in read_rows(PLAYERS)}
    teams = build_teams(read_rows(TEAMS))
    model = FitLedger()
    return transactions, players, teams, model


@pytest.mark.parametrize("tid,expected", [
    ("1412325964028899328", {"Brown": "A", "Bucknell": "B"}),
    ("1414580639092518912", {"Brown": "A", "Penn": "Even"}),
    ("1425957598431035392", {"Citadel": "Even", "UNC Charlotte": "A"}),
    ("1426656560473452544", {"Montana": "C", "Old Dominion": "B+"}),
    ("1423799198175739904", {"Arizona State": "B", "Oregon": "B+"}),
])
def test_verified_historical_team_fit(tid, expected, trade_inputs):
    transactions, players, teams, model = trade_inputs
    trade = next(r for r in transactions if r["TransactionID"] == tid)
    sides = trade_assets(trade, teams, players)
    out = model.evaluate(trade, sides)
    assert {teams[(trade["LeagueName"], k)]: v["letter"] for k, v in out.items()} == expected
    assert all(v["date"] <= "2026-11-10" and 0 <= v["score"] <= 100 for v in out.values())
    if tid == "1423799198175739904":
        oregon = next(k for k in out if teams[(trade["LeagueName"], k)] == "Oregon")
        assert out[oregon]["dynasty_after"] < out[oregon]["dynasty_before"]
        assert all(gain > 0 for _, gain, _ in out[oregon]["horizon_gaps"])


def test_frozen_grade_append_is_idempotent_and_audited(tmp_path):
    import json
    path = tmp_path / "grades.jsonl"
    key = ("2026", "1", "42", "1")
    item = {"key": key, "revision": 1, "fit": {"letter": "B", "score": 52}}
    FitLedger(path).append([item])
    original = path.read_bytes()
    with pytest.raises(ValueError, match="Cannot replace"):
        FitLedger(path).append([{**item, "fit": {"letter": "F"}}])
    FitLedger(path).append([])
    assert path.read_bytes() == original
    correction = {**item, "revision": 2, "fit": {"letter": "A", "score": 65}}
    path.write_bytes(original + (json.dumps(correction) + "\n").encode())
    with pytest.raises(ValueError, match="Invalid Team Fit revision"):
        FitLedger(path)
    correction["correction_reason"] = "Corrected source snapshot identification"
    path.write_bytes(original + (json.dumps(correction) + "\n").encode())
    row = {"Year": 2026, "LeagueID": "1", "TransactionID": "42"}
    assert FitLedger(path).evaluate(row, ["1"])["1"]["letter"] == "A"


def test_file_observations_grade_new_trades_without_later_market_inputs(tmp_path, monkeypatch):
    from transactions_page import trade_assets
    row = {"Year": "2026", "Week": "6", "LeagueID": "1", "LeagueName": "NCAA SEC",
           "TransactionID": "42", "RosterIDs": "[1,2]", "Created": "1500", "StatusUpdated": "2000",
           "Status": "complete", "Adds": "{'10': 2, '20': 1}", "Drops": "{'10': 1, '20': 2}", "Picks": "[]"}
    sides = trade_assets(row, {}, {})
    def tables(after):
        day, value = ("2026-10-12", "9000") if after else ("2026-10-05", "1000")
        return {
            ROSTERS: [{"LeagueID": "1", "PlayerID": pid, "RosterID": rid}
                      for pid, rid in zip(("10", "20"), ("2", "1") if after else ("1", "2"))],
            PICKS: [{"LeagueID": "1", "Season": "2027", "Round": "1",
                     "OriginalRosterID": rid, "OwnerRosterID": rid} for rid in ("1", "2")],
            TX: [{"TransactionID": "42", "Status": "complete"}] if after else
                [{"TransactionID": "41", "Status": "complete"}],
            CONTEXT: [{"Year": "2026", "Week": "5", "LeagueID": "1", "RosterID": rid,
                       "W": "3", "L": "2", "T": "0", "Contender": "0"} for rid in ("1", "2")],
            PLAYER_VALUES: [{"Date": day, "SleeperID": pid, "Position": "RB",
                             "DynastyValue": v, "RedraftValue": v} for pid, v in (("10", value), ("20", "3000"))],
            PICK_VALUES: [{"Date": day, "Season": "2027", "Round": "1", "Value": "100",
                           "Early": "100", "Mid": "100", "Late": "100"}],
        }
    def no_git(*args):
        raise AssertionError("Routine Team Fit must not invoke Git")
    monkeypatch.setattr("transactions_fit.git", no_git)
    assert event_key(row)[0] == 2000
    publish_snapshot(tmp_path, 1400, 1900, tables(False), {})
    archive = FileArchive(tmp_path)
    assert archive.pending(2000)
    assert TeamFit([row], {}, load_config(), archive).evaluate(row, sides) == {}

    # A capture that spans acceptance is not a reliable after snapshot.
    publish_snapshot(tmp_path, 1999, 2100, tables(True), {})
    archive = FileArchive(tmp_path)
    assert list(archive.after(2000)) == []
    assert TeamFit([row], {}, load_config(), archive).evaluate(row, sides) == {}

    publish_snapshot(tmp_path, 2200, 2300, tables(True), {})
    out = TeamFit([row], {}, load_config(), FileArchive(tmp_path)).evaluate(row, sides)
    assert set(out) == {"1", "2"}
    assert out["1"]["date"] == "2026-10-05"
    assert out["1"]["dynasty_before"] == 1100
    assert out["1"]["dynasty_after"] == 3100
    assert out["1"]["sources"]["market_published_ms"] == 1900
    assert out["1"]["sources"]["after_ms"] == 2200
