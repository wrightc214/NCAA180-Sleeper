"""Run: python -m unittest tests/test_ccg_race.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ccg_race import alive_members


class Contenders(unittest.TestCase):
    def run_case(self, wins, games, divisions=None):
        members = list(wins)
        return alive_members(members, divisions or [members], games, wins)

    def test_one_game_lead_with_tie_possible(self):
        got = self.run_case({"A": 8, "B": 7}, [("A", "C"), ("B", "D")],
                            [["A", "B"], ["C", "D"]])
        self.assertEqual(got[0], ["A", "B"])

    def test_two_game_lead_with_one_game_left(self):
        got = self.run_case({"A": 9, "B": 7}, [("A", "B")],
                            [["A", "B"]])
        self.assertEqual(got, [["A"]])

    def test_head_to_head_leader_and_second(self):
        got = self.run_case({"A": 9, "B": 8}, [("A", "B")])
        self.assertEqual(got, [["A", "B"]])

    def test_three_way_tie(self):
        got = self.run_case({"A": 8, "B": 8, "C": 8},
                            [("A", "B"), ("B", "C"), ("C", "A")])
        self.assertEqual(got, [["A", "B", "C"]])

    def test_more_than_twenty_game_fallback(self):
        members = list("ABCDEFGHIJKL")
        games = [(members[i % 12], members[(i + 1) % 12]) for i in range(21)]
        result = self.run_case({m: 5 for m in members}, games,
                               [members[:6], members[6:]])
        self.assertEqual(len(result), 2)
        self.assertEqual([len(x) for x in result], [6, 6])


if __name__ == "__main__":
    unittest.main()
