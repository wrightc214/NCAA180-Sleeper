"""Realigned NIT (2026 format, Chris 2026-11-04): tiebreak, pot draw rules, quarterfinal halves."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))
import nit as N  # noqa: E402

WTS = {"league": 100, "round2": 10, "round1": 1}


def T(lg, r, wins=8, pf=1000, team=None):
    return {"LeagueID": lg, "RosterID": str(r), "Wins": wins, "PointsFor": pf, "Team": team or f"{lg}{r}", "LeagueName": lg}


class Realigned(unittest.TestCase):
    def test_tiebreak_every_week_then_wins_then_points(self):
        a, b, c = T("A", 1, 7, 900), T("B", 1, 9, 900), T("C", 1, 9, 1100)
        W = {("A", "1"): {1: 150, 2: 150, 3: 150}, ("B", "1"): {1: 100, 2: 100, 3: 100}, ("C", "1"): {1: 100, 2: 100, 3: 100}}
        self.assertEqual([t["LeagueID"] for t in N.tb_sort([b, c, a], W)], ["A", "C", "B"])  # every-week, then points

    def test_pot_draw_hard_rule_and_one_per_pot(self):
        teams = [T(f"L{i % 15}", i) for i in range(28)]
        gid1 = {N.key(t): i // 4 for i, t in enumerate(teams)}
        groups = N.pot_draw(teams, 7, random.Random(3), hard=lambda x, y: gid1[N.key(x)] == gid1[N.key(y)])
        self.assertEqual([len(g) for g in groups], [4] * 7)
        for g in groups:
            self.assertEqual(len({gid1[N.key(t)] for t in g}), 4)
            self.assertEqual(sorted(teams.index(t) // 7 for t in g), [0, 1, 2, 3])  # one per pot

    def test_qf_league_first_then_seeding(self):
        q = [T(f"L{i}", i) for i in range(8)]
        q[7]["LeagueID"] = "L0"  # 1 & 8 same league
        comb = {N.key(t): 1000 - i for i, t in enumerate(q)}
        g1 = {N.key(t): f"g1-{i}" for i, t in enumerate(q)}
        g2 = {N.key(t): f"g2-{i}" for i, t in enumerate(q)}
        g2[N.key(q[6])] = g2[N.key(q[0])]  # 1 & 7 shared round 2 group
        games = N.qf_bracket(q, comb, g1, g2, {}, set(), WTS)
        flat = [(q.index(a), q.index(b)) for a, b in games]
        same_half = lambda x, y: any({x, y} <= set(h) for h in ({*flat[0], *flat[1]}, {*flat[2], *flat[3]}))  # noqa: E731
        self.assertFalse(same_half(0, 7))  # league: opposite halves (Final only)
        # 7 and 8 share pot 4, so one of them must join seed 1's half: league wins, and the round-2
        # rematch (1 & 7) is pushed to a possible semifinal, never a quarterfinal
        self.assertNotIn((0, 6), flat)
        self.assertEqual(len({t for g in flat for t in g}), 8)

    def test_qf_straight_seeding_without_conflicts(self):
        q = [T(f"L{i}", i) for i in range(8)]
        comb = {N.key(t): 1000 - i for i, t in enumerate(q)}
        ids = {N.key(t): str(i) for i, t in enumerate(q)}
        games = N.qf_bracket(q, comb, ids, dict(ids), {}, set(), WTS)
        self.assertEqual([(q.index(a), q.index(b)) for a, b in games], [(0, 7), (3, 4), (1, 6), (2, 5)])


if __name__ == "__main__":
    unittest.main()
