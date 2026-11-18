"""Approve historical Team Fit behavior independently of market pricing."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from transactions_fit import DEFAULTS, TeamFit, age_factor, contender_weight, fit_grade
from transactions_grades import load_config, read_rows
from transactions_page import PICK_VALUES, PLAYER_VALUES, PLAYERS, TEAMS, TRANSACTIONS, build_teams, render_fit, trade_assets


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
    model = TeamFit(transactions, players, read_rows(PLAYER_VALUES), read_rows(PICK_VALUES), load_config())
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
