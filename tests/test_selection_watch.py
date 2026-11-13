"""Selection Watch (stage 1): the data, the field rule, the Steal Board and the odds.

Validated against the real 2024 and 2025 seasons (Chris, 2026-11-12): the board built from the
final standings + actual CCG results gives exactly the actual playoff field."""
import os
import random
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import selection_watch as sw  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
EXPECT = {  # thieves that won (steals) / at-large teams pushed out, from the real seasons
    2024: ({"Jackson State", "UAB", "Eastern Kentucky"}, {"Memphis", "Arizona State", "UTEP"}),
    2025: ({"Kansas State", "Nevada"}, {"UNLV", "Youngstown State"}),
}


@pytest.fixture(scope="module", params=[2024, 2025])
def season(request):
    os.chdir(ROOT)
    if not os.path.exists(sw.HIST):
        pytest.skip("no postseason history")
    ok, d = sw.check(request.param)
    return request.param, ok, d


def test_rule_reproduces_actual_field(season):
    year, ok, d = season
    assert ok, f"{year}: field by rule differs from the actual playoff field"
    assert len(d["ccg"]) == 15 and len(d["order"]) == 180


def test_board_matches_real_season(season):
    year, _, d = season
    name = {t["k"]: t["team"] for t in d["order"]}
    leaders = {g["id"]: g["winner"] for g in d["ccg"]}
    thieves, at_risk, k = sw.board(d, leaders)
    stole = {name[t["team"]] for t in thieves if t["leading"]}
    pushed = {name[x] for x in at_risk[:k]}
    assert (stole, pushed) == EXPECT[year]


def test_board_count_rule_equals_field_rule(season):
    """Any CCG results: the bottom-k-out board agrees with the full field rule."""
    _, _, d = season
    rng = random.Random(7)
    for _ in range(300):
        win = [g[rng.choice("ab")] for g in d["ccg"]]
        f = {k for k, s in sw.field(d, win).items() if s == 1}
        thieves, at_risk, k = sw.board(d, {g["id"]: w for g, w in zip(d["ccg"], win)})
        out = set(at_risk[:k])
        inside = {t["k"] for t in d["order"][:d["field_size"]]}
        assert out == inside - f  # exactly the natural-field teams that miss
        assert all((t["team"] in f) == t["leading"] for t in thieves)  # a thief is in iff it leads


def test_odds_final_results_are_certain(season):
    _, _, d = season
    p = {g["id"]: 1.0 if g["winner"] == g["a"] else 0.0 for g in d["ccg"]}
    o = sw.odds(d, p)
    f = sw.field(d, [g["winner"] for g in d["ccg"]])
    assert {k for k, v in o.items() if v > 0.999} == {k for k, s in f.items() if s == 1}
    assert abs(sum(o.values()) - d["field_size"]) < 1e-9


def test_odds_coin_flip_slate_sums_to_field():
    os.chdir(ROOT)
    d = sw.build(2025)
    d["ccg"] = d["ccg"][:10]  # keep the test fast: 2^10 outcome sets
    d["field_size"] = 32 - 5  # the 5 dropped CCGs' auto bids
    o = sw.odds(d, {g["id"]: 0.5 for g in d["ccg"]})
    assert abs(sum(o.values()) - d["field_size"]) < 1e-9
    locks = [k for k, v in o.items() if v > 1 - 1e-12]
    assert d["order"][0]["k"] in locks


def test_tie_across_the_cut_splits_evenly():
    """A tie still standing at the last spot = a real coin toss: each tied team gets half."""
    order = [{"k": f"t{i}", "rank": i + 1} for i in range(6)]
    d = {"field_size": 4, "order": order, "tie": [["t2", "t3"]],
         "ccg": [{"id": "g", "a": "t5", "b": "t4"}]}  # both outside the top 4
    f = sw.field(d, ["t5"])
    assert f["t0"] == f["t1"] == 1 and f["t2"] == f["t3"] == 0.5 and f["t5"] == 1
    assert "t4" not in f or f["t4"] == 0
