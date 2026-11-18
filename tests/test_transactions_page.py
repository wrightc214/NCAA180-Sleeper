"""Transactions page/grades regression tests.

No API calls; fixtures are deliberately synthetic to isolate valuation logic.
"""
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from transactions_page import build_teams, day, movement, parse, summary, trade_assets, trade_card
from transactions_grades import (compare, consolidation, evaluate_trade, grade, load_config,
                                 historical, nearest_pick, pick_swap, read_rows)


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
    assert len(small) == 1 and small[0][1].startswith("2.")
    large = nearest_pick(5200, 2027, picks)
    assert len(large) == 2
    assert large[0][1] == "1.01"
    assert large[0][0] <= 5200
    assert [slot for _, slot, _ in nearest_pick(9200, 2027, picks)] == ["1.01", "1.02"]
    assert [slot for _, slot, _ in nearest_pick(4600, 2027, picks)] == ["1.02"]
    assert nearest_pick(9200, 2027, [{"Season": "2027", "Round": "1", "Value": "4600"}]) == [
        (4600, "R1", False)
    ]


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


def test_config_controls_both_thresholds_and_fallback_parameters():
    config = load_config()
    assert config["blockbuster_min_multiple"] == 1.4
    assert config["blockbuster_min_headliner_share"] == .60
    assert config["proxy_pick_slot"] == "4.12"
    assert config["consolidation"]["method"] == "ktc-style-fallback"
    assert config["grade_bands"][0] == [60, "A"]
    assert compare({"A": [4900], "B": [4900]}, 11000, config)["grade"]["A"] == "Even"


def test_zero_contender_value_never_receives_phantom_consolidation_credit():
    result = compare({"Win": [5000], "Picks": [0, 0]}, 11000)
    assert result["credit"] == {"Win": 0.0, "Picks": 0.0}
    assert result["grade"]["Win"] == "A"
    assert result["grade"]["Picks"] == "F"


def test_surplus_appears_in_winning_team_panel_only():
    sides = {"1": [{"kind": "player", "id": "100", "label": "Alpha Runner"}],
             "2": [{"kind": "player", "id": "200", "label": "Beta Receiver"}]}
    dyn = compare({"1": [7000], "2": [2000]}, 11000)
    dyn["surplus"] = {"team": "1", "value": 2000, "picks": [(1980, "2.07", True)]}
    result = {"dynasty": dyn, "contender": None, "status": "complete", "player_date": "2026-10-06"}
    row = {"LeagueName": "NCAA SEC", "Week": "5", "Created": "1791331200000", "TransactionID": "t1"}
    rendered = trade_card(row, sides, TEAMS, {}, result, {"NCAA SEC": "SEC"})
    assert rendered.count('class="tx-surplus"') == 1
    assert 'Experimental consolidation adjustment (KTC-style)' in rendered
    winner_panel, other = rendered.split('<div class="tx-center">', 1)
    assert "tx-surplus" in winner_panel
    assert "tx-surplus" not in other
    assert "Pick 2.07" in rendered
    assert "2027" not in rendered

@pytest.mark.parametrize("position", ["K", "DEF", "D/ST"])
def test_league_proxy_excluded_from_credit_but_counted_in_both_modes(position):
    pd = "2026-11-03"
    players = [
        {"Date": pd, "SleeperID": "1", "DynastyValue": "4000", "RedraftValue": "6000"},
        {"Date": pd, "SleeperID": "2", "DynastyValue": "2000", "RedraftValue": "3000"},
    ]
    picks = [{"Date": pd, "Season": "2027", "Round": "4", "Early": "861",
              "Mid": "784", "Late": "725", "Value": "773"}]
    sides = {"A": [{"kind": "player", "id": "1"}], "B": [{"kind": "player", "id": "2"}]}
    base = evaluate_trade(sides, pd, players, picks, 2026)
    sides["A"].append({"kind": "player", "id": "3", "position": position})
    got = evaluate_trade(sides, pd, players, picks, 2026)
    assert got["proxies"] == {"A": {"3": 725}, "B": {}}
    for mode in ("dynasty", "contender"):
        assert got[mode]["raw"]["A"] == base[mode]["raw"]["A"] + 725
        assert got[mode]["credit"] == base[mode]["credit"]
    assert got["blockbuster"] == base["blockbuster"] == {"points": 6000, "multiple": 1.5,
                                                            "headliner_points": 4000, "headliner_share": 1.0}
    assert "blockbuster" not in evaluate_trade(
        sides, pd, players, picks, 2026, {"blockbuster_min_multiple": 1.6})
    assert evaluate_trade(sides, pd, players, [], 2026)["dynasty"] is None


def test_unlisted_skill_player_zero_unknown_id_ungraded_and_all_zero_not_even():
    pd = "2026-11-03"
    p = [{"Date": pd, "SleeperID": "sky", "DynastyValue": "100", "RedraftValue": "100"}]
    a = {"A": [{"kind": "player", "id": "1", "position": "RB"}],
         "B": [{"kind": "player", "id": "2", "position": "TE"}]}
    out = evaluate_trade(a, pd, p, [], 2026)
    assert out["dynasty"]["raw"] == {"A": 0, "B": 0}
    assert out["dynasty"]["grade"] == {"A": None, "B": None}
    assert "blockbuster" not in out
    a["B"][0].pop("position")
    assert evaluate_trade(a, pd, p, [], 2026)["dynasty"] is None


def test_small_surplus_uses_closest_meaningful_swap_and_not_future_round():
    p = [
        {"Season": "2027", "Round": "3", "Early": "1206", "Mid": "1066", "Late": "953"},
        {"Season": "2027", "Round": "4", "Early": "861", "Mid": "784", "Late": "725"},
        {"Season": "2029", "Round": "4", "Early": "400", "Mid": "300", "Late": "200"},
    ]
    assert pick_swap(372, 2027, p) == {"from": "4.12", "to": "3.05", "value": 376}
    assert pick_swap(372, 2027, p, {"surplus_swap_max_relative_error": .01}) is None
    assert pick_swap(7, 2027, p) is None
    assert pick_swap(725, 2027, p) is None


@pytest.mark.parametrize("trade_id,marked", [
    ("1414580639092518912", True), ("1412325964028899328", True),
    ("1426656560473452544", True), ("1425957598431035392", True),
    ("1426733052746272768", False),
    ("1423799198175739904", False),
])
def test_real_trade_results_and_blockbuster_rendering(trade_id, marked):
    from transactions_page import TRANSACTIONS, TEAMS as TEAM_FILE, PLAYERS as PLAYER_FILE
    row = next(r for r in read_rows(TRANSACTIONS) if r["TransactionID"] == trade_id)
    teams = build_teams(read_rows(TEAM_FILE))
    players = {p["player_id"]: p for p in read_rows(PLAYER_FILE)}
    sides = trade_assets(row, teams, players)
    out = evaluate_trade(sides, day(row["Created"]), read_rows("data/PlayerValues_Season.csv"),
                         read_rows("data/PickValues_Season.csv"), int(row["Year"]), load_config())
    rendered = trade_card(row, sides, teams, {}, out, {})
    assert ('>Blockbuster</span>' in rendered) is marked
    if trade_id == "1426656560473452544":
        assert "≈ Pick 1.01 + ≈ Pick 1.02" in rendered
    if trade_id == "1423799198175739904":
        assert out["dynasty"]["surplus"]["value"] == pytest.approx(372.294, abs=.001)
        assert "+725 pts (4.12 proxy)" in rendered
        assert "4.12 → 3.05" in rendered
        assert "2027" not in rendered.split('class="tx-surplus"', 1)[1]


@pytest.mark.parametrize("player_values,pick_value,marked", [
    ([1000, 750, 750], 0, False),     # third-for-two-fourths
    ([4000, 4000, 4000, 4500], 0, False),  # enough volume, no headliner
    ([6600, 4000], 4799, False),      # headliner exactly qualifies; one point short on volume
    ([6599, 4000], 4801, False),      # volume exactly qualifies; one point short on headliner
    ([6600, 4000], 4800, True),       # both thresholds qualify exactly; picks count for volume
    ([2000, 2000], 13000, False),     # a big pick cannot be the headliner
    ([], 17000, False),               # picks-only trade
])
def test_blockbuster_uses_two_snapshot_relative_raw_thresholds(player_values, pick_value, marked):
    day = "2026-11-03"
    players = [
        {"Date": day, "SleeperID": str(i), "DynastyValue": str(v), "RedraftValue": str(v)}
        for i, v in enumerate([11000, *player_values])  # benchmark player is not traded
    ]
    sides = {"A": [], "B": []}
    for i in range(1, len(players)):
        sides["A" if i % 2 else "B"].append({"kind": "player", "id": str(i)})
    picks = []
    if pick_value:
        sides["B"].append({"kind": "pick", "season": 2027, "round": 1})
        picks.append({"Date": day, "Season": "2027", "Round": "1", "Value": str(pick_value)})
    out = evaluate_trade(sides, day, players, picks, 2026)
    assert ("blockbuster" in out) is marked
    if marked:
        assert "blockbuster" not in evaluate_trade(
            sides, day, players, picks, 2026, {"blockbuster_min_headliner_share": .61})
        assert out["blockbuster"] == {"points": 15400, "multiple": 1.4,
                                     "headliner_points": 6600, "headliner_share": .60}


def test_task_511_settings_have_safe_defaults_when_sections_are_missing(monkeypatch):
    import league_config as lcfg
    from player_values import fantasycalc_request

    monkeypatch.setattr(lcfg, "cfg", lambda: {})
    settings = load_config()
    assert (settings["blockbuster_min_multiple"], settings["blockbuster_min_headliner_share"]) == (1.4, .6)
    assert settings["labels"]["blockbuster"] == "Blockbuster"
    assert settings["draft_slots_per_round"] == 12
    assert grade(.50) == "Even"
    assert fantasycalc_request()[1] == {"isDynasty": "true", "numQbs": 1, "numTeams": 12, "ppr": 1}


def test_task_511_partial_owner_settings_change_only_selected_behavior(monkeypatch):
    import league_config as lcfg
    from player_values import fantasycalc_request
    from transactions_grades import pick_slot_values

    monkeypatch.setattr(lcfg, "cfg", lambda: {
        "transactions": {
            "draft_slots_per_round": 10, "proxy_pick_slot": "4.10",
            "consolidation": {"method": "none"},
            "labels": {"blockbuster": "Big <trade>"}, "movement_types": ["waiver", "trade"],
        },
        "fantasycalc": {"num_teams": 10},
    })
    settings = load_config()
    assert settings["consolidation"]["exponent_low"] == 1.04
    assert settings["labels"]["rebuild"] == "Rebuild"
    assert settings["proxy_pick_slot"] == "4.10"
    assert fantasycalc_request()[1]["numTeams"] == 10
    assert compare({"1": [7000], "2": [3000]}, 11000)["credit"] == {"1": 0, "2": 0}
    slots = pick_slot_values([{"Season": "2027", "Round": "4", "Early": 900, "Mid": 800, "Late": 700}], 2027)
    assert list(slots)[-1] == (700, "4.10", True)
    row = tx(Week="1", Status="complete", Created="1794000000000", TransactionID="1", Type="trade")
    sides = {"1": [], "2": []}
    result = {"blockbuster": {"points": 20000, "multiple": 2, "headliner_points": 9000, "headliner_share": .9}}
    assert "Big &lt;trade&gt;" in trade_card(row, sides, TEAMS, {}, result, {})
    assert movement([row, {**row, "Type": "free_agent"}], [], PLAYERS, {"NCAA SEC"}, 1)["adds"] == []


def test_task_511_missing_transactions_nav_settings_remain_preview_only(monkeypatch):
    import site_common

    monkeypatch.setattr(site_common, "nav_config", lambda: {"tabs": [{"id": "transactions"}]})
    assert site_common.page_state("transactions") == "hidden-dev"
    assert site_common.menu_data()["tabs"] == [
        {"id": "transactions", "label": "Transactions", "href": "transactions.html", "state": "hidden-dev"},
    ]


def test_ccg_week_uses_shared_labels_in_card_selectors_and_summary(monkeypatch, tmp_path):
    import re
    import transactions_page as page

    ccg_week = str(page.lcfg.cfg()["schedule"]["ccg_week"])
    assert page.lcfg.week_label(ccg_week) == "CCG Week"
    row = tx(Week=ccg_week, Year=str(page.lcfg.season()), Status="complete",
             Created="1794000000000", TransactionID="ccg-trade", Type="trade")
    sources = {page.TRANSACTIONS: [row], page.PLAYERS: [
        {"player_id": pid, **player} for pid, player in PLAYERS.items()
    ]}
    report = tmp_path / "transactions.html"
    monkeypatch.setattr(page, "read_rows", lambda path: sources.get(path, []))
    monkeypatch.setattr(page, "OUT", str(report))
    page.main()
    rendered = report.read_text(encoding="utf-8")
    assert f'data-week="{ccg_week}"' in rendered
    assert re.search(r'<div class="tx-head">[^<]* · CCG Week · ', rendered)
    for selector in ("tx-week", "tx-move-week"):
        options = re.search(fr'<select id="{selector}">(.*?)</select>', rendered, re.S).group(1)
        assert re.search(fr'<option value="{ccg_week}"(?: selected)?>CCG Week</option>', options)
    assert '<h3>Trades by week</h3><div class="tx-bar"><span>CCG Week</span>' in rendered
