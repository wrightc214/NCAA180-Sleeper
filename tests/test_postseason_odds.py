"""postseason_odds: the fast selection rules must match the real engine (bowl_projection.project) on
the same results, and the simulation must respect the field sizes (2026-11-07)."""
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
import _postseason_common as ps  # noqa: E402
import bowl_projection as bp  # noqa: E402
import postseason_odds as po  # noqa: E402


def key(t):
    return (str(t["LeagueID"]), str(t["RosterID"]).replace(".0", ""))


class FastRulesMatchEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.year = ps.current_season()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.P = bp.project(cls.year)
            cls.F = po.deterministic(cls.year)

    def test_playoff_field(self):
        self.assertEqual(self.F["Playoff"], {key(t) for t in self.P["field"]})

    def test_auto_bids(self):
        self.assertEqual(self.F["aq"], {key(t) for t in self.P["field"] if str(t["BidType"]).startswith("Auto")})

    def test_bowl_pool(self):
        self.assertEqual(self.F["Bowl"], {key(t) for t in self.P["pool"]})

    def test_prestige_and_marquee(self):
        tier = {}
        for b, x, y in self.P["games"]:
            tier.setdefault(b["tier"], set()).update({key(x), key(y)})
        self.assertEqual(self.F["Prestige"], tier.get("Prestige Bowls", set()))
        self.assertEqual(self.F["Marquee"], tier.get("Marquee Bowls", set()))


class Simulation(unittest.TestCase):
    def test_sizes_and_totals(self):
        with contextlib.redirect_stdout(io.StringIO()):
            out = po.build(ps.current_season(), sims=300, seed=1, write=False)
        t = out["teams"]
        tot = lambda c: sum(x[c] for x in t)  # noqa: E731
        self.assertAlmostEqual(tot("Playoff"), 32, delta=0.01)
        self.assertAlmostEqual(tot("Natty"), 1, delta=0.01)
        self.assertAlmostEqual(tot("Prestige"), 10, delta=0.01)
        for x in t:  # every team lands in exactly one of Playoff / Bowl / NIT
            self.assertAlmostEqual(x["Playoff"] + x["Bowl"] + x["NIT"], 1, delta=0.001)
            self.assertLessEqual(x["Prestige"] + x["Marquee"], x["Bowl"] + 1e-9)
            for c, f in x["flags"].items():  # a proof never contradicts the runs
                self.assertEqual(x[c], 1.0 if f == "clinched" else 0.0, (x["Team"], c, f))


if __name__ == "__main__":
    unittest.main()
