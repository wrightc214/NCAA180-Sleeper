"""Transactions page/grades regression tests.

No API calls; fixtures are deliberately synthetic to isolate valuation logic.
"""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from transactions_page import build_teams, day, movement, parse, summary, trade_assets
from transactions_grades import (compare, consolidation, evaluate_trade, grade,
                                 historical, nearest_pick)


TEAMS = build_teams([
    {"League": "NCAA SEC", "Roster ID": "1", "Team": "Alabama"},
    {"League": "NCAA SEC", "Roster ID": "2", "Team": "Georgia"},
    {"League": "NCAA SEC", "Roster ID": "3", "Team": "Auburn"},
])
PLAYERS = {
    "100": {"first_name": "Alpha", "last_name": "Runner", "position": "RB"},
    "200": {"first_name": "Beta", "last_name": "Receiver", "position": "WR"},
    "300": {"first_name": "Gamma", "last_name": "Quarterback", "position": "QB"},
}


def tx(**kw):
    return {"LeagueName": "NCAA SEC", "RosterIDs": "[1, 2]",
            "Adds": "{'100': 2, '200': 1}", "Drops": "{'100': 1, '200': 2}",
            "Picks": "[{'season':'2027','round':2,'roster_id':3,'owner_id':1,'previous_owner_id':2}, "
                     "{'season':'2028','round':3,'roster_id':1,'owner_id':2,'previous_owner_id':1}]",
            **kw}


def test_parse_both_player_directions_and_pick_via_original_team():
    sides = trade_assets(tx(), TEAMS, PLAYERS)
    assert [a["label"] for a in sides["1"]] == ["Beta Receiver", "2027 R2 (via Auburn)"]
    assert [a["label"] for a in sides["2"]] == ["Alpha Runner", "2028 R3 (via Alabama)"]
    assert sides["1"][0]["id"] == "200"


def test_parse_three_for_one():
    r = tx()
    r["Adds"] = "{'100': 1, '200': 1, '300': 1, '400': 2}"
    sides = trade_assets(r, TEAMS, PLAYERS)
    assert len([p for p in sides["1"] if p["kind"] == "player"]) == 3
    assert len([p for p in sides["2"] if p["kind"] == "player"]) == 1


def test_movement_distinct_leagues_and_availability():
    base = {"Year": "2026", "Week": "5", "Status": "complete",
            "Type": "waiver", "LeagueName": "NCAA SEC", "Adds": "{'100': 1}", "Drops": "{'200': 1}"}
    rows = [base, dict(base, Adds="{'100': 2}", Drops=""),  # twice in SEC counts once
            dict(base, LeagueName="NCAA ACC"),
            dict(base, Type="trade", LeagueName="NCAA PAC 12"),
            dict(base, Status="pending", LeagueName="NCAA BIG 10")]
    rosters = [{"PlayerID": "100", "LeagueName": "NCAA SEC"},
               {"PlayerID": "100", "LeagueName": "NCAA ACC"},
               {"PlayerID": "200", "LeagueName": "NCAA PAC 12"}]
    m = movement(rows, rosters, PLAYERS, {"NCAA SEC", "NCAA ACC", "NCAA PAC 12"}, 5)
    assert m["adds"][0]["count"] == 2
    assert m["adds"][0]["owned"] == 2
    assert m["adds"][0]["available"] == ["NCAA PAC 12"]
    assert m["drops"][0]["count"] == 2
    assert m["drops"][0]["owned"] == 1


def test_historical_strict_on_or_before():
    d = [{"Date": "2026-10-02"}, {"Date": "2026-10-06"}]
    assert historical(d, "2026-10-01") is None
    assert historical(d, "2026-10-02") == "2026-10-02"
    assert historical(d, "2026-10-05") == "2026-10-02"
    assert historical(d, "2026-10-06") == "2026-10-06"


@pytest.mark.parametrize("share,label", [(0.60, "A"), (0.5999, "B+"), (0.55, "B+"),
    (0.5499, "B"), (0.52, "B"), (0.51999, "Even"), (0.48, "Even"),
    (0.4799, "C"), (0.45, "C"), (0.4499, "D"), (0.40, "D"), (0.3999, "F")])
def test_grade_boundaries(share, label):
    assert grade(share) == label


def test_consolidation_credit_inverse_and_no_phantom():
    sides = {"A": [6000], "B": [2200, 2000, 1800]}
    credit, raw = consolidation(sides, 11000)
    lo = min(raw, key=raw.get)
    assert credit[lo] > 0
    assert credit[max(raw, key=raw.get)] == 0
    assert consolidation({"A": [0], "B": [0]}, 10000)[0] == {"A": 0.0, "B": 0.0}
    x = compare({"A": [5000], "B": [5000]}, 11000)
    assert x["credit"] == {"A": 0, "B": 0}
    assert x["grade"] == {"A": "Even", "B": "Even"}


def test_nearest_pick_one_then_two_and_primary_highest_fitting():
    picks = [{"Season": "2027", "Round": "1", "Value": "2700", "Early": "4600",
              "Mid": "3000", "Late": "2300"},
             {"Season": "2027", "Round": "2", "Value": "1500", "Early": "1900",
              "Mid": "1600", "Late": "1350"},
             {"Season": "2027", "Round": "3", "Value": "1000", "Early": "1200",
              "Mid": "1000", "Late": "900"}]
    small = nearest_pick(1600, 2027, picks)
    assert len(small) == 1 and small[0][1].startswith("2027 Pick 2.")
    large = nearest_pick(5200, 2027, picks)
    assert len(large) == 2
    assert large[0][1].startswith("2027 Pick 1.")
    assert large[0][0] <= 5200


def test_no_future_valuation_no_grade_before_october():
    assets = {"A": [{"kind": "player", "id": "100"}], "B": [{"kind": "player", "id": "200"}]}
    p = [{"Date": "2026-10-02", "SleeperID": "100", "DynastyValue": "8000", "RedraftValue": "7000"},
         {"Date": "2026-10-02", "SleeperID": "200", "DynastyValue": "4000", "RedraftValue": "3000"}]
    k = [{"Date": "2026-10-02", "Season": "2027", "Round": "2", "Value": "1600"}]
    assert evaluate_trade(assets, "2026-09-30", p, k, 2026)["dynasty"] is None
    got = evaluate_trade(assets, "2026-10-02", p, k, 2026)
    assert got["dynasty"] and got["contender"]
    assert got["player_date"] == "2026-10-02"


def test_missing_historical_pick_withholds_dynasty_not_contender():
    assets = {"A": [{"kind": "pick", "season": 2027, "round": 1}],
              "B": [{"kind": "player", "id": "100"}]}
    p = [{"Date": "2026-10-02", "SleeperID": "100", "DynastyValue": "5000", "RedraftValue": "6000"}]
    out = evaluate_trade(assets, "2026-10-03", p, [], 2026)
    assert out["dynasty"] is None
    assert out["contender"] is not None


def test_complete_only_summaries():
    c, weeks = summary([{"LeagueName": "NCAA SEC", "Week": "5"},
                        {"LeagueName": "NCAA SEC", "Week": "6"}])
    assert c["NCAA SEC"] == 2 and weeks[5] == weeks[6] == 1


def test_epoch_is_utc():
    assert day(0) == "1970-01-01"
