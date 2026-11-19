"""Cross-language parity and historical board acceptance for Selection Watch.
Python stage 1 is authoritative. Node stage 2 must reproduce it for *identical* inputs.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import selection_watch as sw  # noqa: E402

NODE = shutil.which("node")
CORE = ROOT / "reports/assets/selection-watch-core.js"
BRIDGE = """
const C=require(process.argv[1]),fs=require('fs');
const a=JSON.parse(fs.readFileSync(0,'utf8'));
const p=C.odds(a.d,a.p);
const b=C.board(a.d,a.leaders);
process.stdout.write(JSON.stringify({odds:p,board:b,locks:C.locks(a.d)}));
"""


def js(d, p, leaders):
    result = subprocess.run([NODE, "-e", BRIDGE, str(CORE)],
                            input=json.dumps({"d": d, "p": p, "leaders": leaders}),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=True, timeout=180, cwd=ROOT)
    return json.loads(result.stdout)


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
@pytest.mark.parametrize("year,expected_rows,expected_steals", [(2024, 5, 3), (2025, 6, 2)])
def test_js_equals_python_on_real_seasons(year, expected_rows, expected_steals):
    os.chdir(ROOT)
    d = sw.build(year)
    assert len(d["order"]) == 180 and len(d["ccg"]) == 15
    # Non-degenerate probabilities exercise every outcome of all 15 games, not only the actual finals.
    p = {g["id"]: .1 + .8 * ((i * 7) % 15) / 14 for i, g in enumerate(d["ccg"])}
    leaders = {g["id"]: g["winner"] for g in d["ccg"]}
    actual = js(d, p, leaders)
    expected = sw.odds(d, p)
    assert set(actual["odds"]) == set(expected)
    for k, share in expected.items():
        assert actual["odds"][k] == pytest.approx(share, abs=1e-9)
    pyrows, pyrisk, k = sw.board(d, leaders)
    board = actual["board"]
    assert len(board["thieves"]) == expected_rows == len(pyrows)
    assert board["k"] == expected_steals == k
    assert board["atRisk"] == pyrisk
    assert board["thieves"] == pyrows
    # Frozen final historical results still reproduce the *actual* field.
    frozen = {g["id"]: int(g["winner"] == g["a"]) for g in d["ccg"]}
    fixed = js(d, frozen, leaders)
    field = sw.field(d, [g["winner"] for g in d["ccg"]])
    for k in set(field) | set(fixed["odds"]):
        assert fixed["odds"].get(k, 0) == pytest.approx(field.get(k, 0), abs=1e-12)


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_js_equals_python_on_exact_coin_toss_at_cut():
    d = {"year": 2026, "field_size": 4, "ccg": [{"id": "g", "a": "t5", "b": "t4", "winner": ""}],
         "order": [{"k": f"t{i}", "rank": i + 1} for i in range(6)],
         "tie": [["t2", "t3"]]}
    p = {"g": .43}
    actual = js(d, p, {"g": "t5"})
    expected = sw.odds(d, p)
    for k in set(expected) | set(actual["odds"]):
        assert actual["odds"].get(k, 0) == pytest.approx(expected.get(k, 0), abs=1e-12)
    assert actual["odds"]["t2"] == pytest.approx(.5)
    assert actual["odds"]["t3"] == pytest.approx(.5)
