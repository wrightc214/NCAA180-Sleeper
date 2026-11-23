"""Task 5.15: points-for cap for Clinched / Out. Run: python -m pytest tests/test_clinch_cap.py

The shared fixture tests/fixtures/clinch-cap-cases.json is also run by tests/clinch-cap.test.js, so
Python (postseason_odds._Conf) and the browser (ccg-race-model.js) must agree case by case.
"""
import json
import os
import sys
import unittest
from unittest import mock

import numpy as np

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import clinch_cap  # noqa: E402
from postseason_odds import _Conf  # noqa: E402
import ccg_race  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "clinch-cap-cases.json")


def run_case(fx, case):
    """Division D result {clinched, out} from the Python proof for one fixture case."""
    teams = {k: dict(v, **case.get("teams", {}).get(k, {})) for k, v in fx["teams"].items()}
    games = case.get("games", fx["games"])
    live = case.get("live", {})
    rate, burst, slots = case["rate"], case["burst"], fx["slots"]
    ids = list(teams)
    W0 = {k: teams[k]["wins"] for k in ids}
    PF0 = {k: float(teams[k]["pf"]) for k in ids}
    cap = {k: 0.0 for k in ids}
    open_games = []
    for a, b in games:
        la, lb = live.get(a, {}), live.get(b, {})
        if la.get("final") and lb.get("final"):
            sa, sb = la["actual"], lb["actual"]
            W0[a if sa > sb else b] += 1
            PF0[a] += sa
            PF0[b] += sb
            continue
        open_games.append((a, b))
        for k, lk in ((a, la), (b, lb)):
            PF0[k] += lk.get("actual", 0)
            if not lk.get("final"):
                cap[k] += clinch_cap.points_cap(lk.get("minutes", 60 * slots), lk.get("players", slots), rate, burst)
    on = clinch_cap.enabled(rate, burst)
    at = {k: i for i, k in enumerate(ids)}
    divs = [[at[k] for k in ids if teams[k]["div"] == d] for d in ("D", "E")]
    c = _Conf(list(range(len(ids))), divs, [(at[a], at[b]) for a, b in open_games],
              np.array([W0[k] for k in ids]),
              np.array([PF0[k] for k in ids]) if on else None, np.array([cap[k] for k in ids]) if on else None)
    flags = {k: c.ccg(at[k]) for k in ids if teams[k]["div"] == "D"}
    clinched = next((k for k, f in flags.items() if f == "clinched"), None)
    return {"clinched": clinched, "out": sorted(k for k, f in flags.items() if f == "out")}


class CapCurve(unittest.TestCase):
    def test_examples(self):
        r, b = 0.45, 18
        self.assertAlmostEqual(clinch_cap.points_cap(660, 11, r, b), 297)
        self.assertAlmostEqual(clinch_cap.points_cap(20, 2, r, b), 36)   # 2 starters, 10 minutes each
        self.assertAlmostEqual(clinch_cap.points_cap(1, 1, r, b), 18)
        self.assertEqual(clinch_cap.points_cap(0, 0, r, b), 0)
        self.assertAlmostEqual(clinch_cap.week_cap(11, r, b), 297)

    def test_config(self):
        rate, burst = clinch_cap.settings()
        self.assertEqual((rate, burst), (0.45, 18.0))
        self.assertIn("0.45 points per remaining player-minute", clinch_cap.note())

    def test_off_when_missing(self):
        with mock.patch.object(clinch_cap.lcfg, "cfg", return_value={"postseason": {}}):
            self.assertEqual(clinch_cap.settings(), (0.0, 0.0))
            self.assertEqual(clinch_cap.note(), "")

    def test_starter_slots_2026(self):
        slots = clinch_cap.starter_slots(2026)
        self.assertEqual(len(slots), 15)
        self.assertEqual(set(slots.values()), {11})


class SharedFixture(unittest.TestCase):
    def test_cases(self):
        fx = json.load(open(FIXTURE, encoding="utf-8"))
        for case in fx["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(run_case(fx, case), case["expect"])


class PostseasonProofs(unittest.TestCase):
    """Replay of postseason_odds proofs on the repo's current data (2026 after week 10)."""

    @classmethod
    def setUpClass(cls):
        import postseason_odds as po
        cls.po = po
        os.chdir(os.path.join(HERE, ".."))
        cls.S = po.simulate(2026, sims=50, seed=1)

    def test_off_is_old_rule(self):
        old = self.po.proofs(dict(self.S, PF0=None))
        self.assertEqual(self.po.proofs(self.S, rate=0, burst=0), old)

    def test_replay_changes(self):
        if self.S["after"] != 10:
            self.skipTest("replay pinned to 2026 after week 10")
        new, old = self.po.proofs(self.S), self.po.proofs(dict(self.S, PF0=None))
        team = list(self.S["st"]["Team"])
        changed = sorted((c, team[i], old[c][i], new[c][i]) for c in new for i in range(len(team)) if new[c][i] != old[c][i])
        self.assertEqual(changed, sorted([
            ("CCG", "Montana", "", "clinched"),
            ("CCG", "South Dakota", "", "out"), ("CCG", "Wichita State", "", "out"), ("CCG", "Howard", "", "out"),
            ("Playoff", "South Dakota", "", "out"), ("Playoff", "Wichita State", "", "out"), ("Playoff", "Howard", "", "out"),
            ("Natty", "South Dakota", "", "out"), ("Natty", "Wichita State", "", "out"), ("Natty", "Howard", "", "out"),
        ]))


class ContendersWithCap(unittest.TestCase):
    def test_tie_outside_cap_drops_contender(self):
        got = ccg_race.alive_members(["A", "B", "C", "D"], [["A", "B"], ["C", "D"]], [("A", "C"), ("B", "D")],
                                     {"A": 8, "B": 7, "C": 0, "D": 0},
                                     {"A": 1500, "B": 1100, "C": 0, "D": 0}, {k: 297 for k in "ABCD"})
        self.assertEqual(got[0], ["A"])

    def test_tie_inside_cap_keeps_contender(self):
        got = ccg_race.alive_members(["A", "B", "C", "D"], [["A", "B"], ["C", "D"]], [("A", "C"), ("B", "D")],
                                     {"A": 8, "B": 7, "C": 0, "D": 0},
                                     {"A": 1500, "B": 1300, "C": 0, "D": 0}, {k: 297 for k in "ABCD"})
        self.assertEqual(got[0], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
