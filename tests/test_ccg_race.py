"""Run: python -m unittest tests/test_ccg_race.py"""
import os
import sys
import json
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ccg_race import alive_members, build
import clinch_cap  # noqa: E402


class Contenders(unittest.TestCase):
    def run_case(self, wins, games, divisions=None):
        members = list(wins)
        return alive_members(members, divisions or [members], games, wins)

    def test_one_game_lead_with_tie_possible(self):
        got = self.run_case({"A": 8, "B": 7, "C": 0, "D": 0}, [("A", "C"), ("B", "D")],
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

    def test_current_week_2026_matches_published_snapshot(self):
        """Integration check on the real scoring inputs, skipped after Week 11 closes."""
        # The published snapshot predates the 5.15 points-for cap: compare with the cap off.
        with mock.patch.object(clinch_cap, "settings", return_value=(0.0, 0.0)):
            current = build(2026, write=False)
        if current is None:
            self.skipTest("2026 Week 11 no longer active")
        with open("reports/postseason/ccg-race-2026.json", encoding="utf-8") as source:
            published = json.load(source)
        def flat(data):
            return {
                (c["league_id"], d["name"]): {
                    x["roster_id"]: (x["team"], x["wins"], x["losses"],
                                     round(x["points_for"], 2), round(x["points_against"], 2))
                    for x in d["contenders"]
                }
                for c in data["conferences"] for d in c["divisions"]
            }
        self.assertEqual(flat(current), flat(published))
        divisions = [d for c in current["conferences"] for d in c["divisions"]]
        self.assertEqual(sum(d["clinched_before_week"] for d in divisions), 12)
        self.assertEqual(sum(not d["clinched_before_week"] for d in divisions), 18)
        pac = next(c for c in current["conferences"] if c["name"] == "Pac-12")
        south = next(d for d in pac["divisions"] if d["name"] == "SOUTH")
        self.assertEqual({t["team"]: (t["wins"], t["losses"]) for t in south["contenders"]},
                         {"Colorado": (9, 1), "UCLA": (8, 2), "Arizona State": (8, 2)})

    def test_current_week_2026_with_points_cap(self):
        """5.15 replay at 0.45 / 18 (one week left = 297): only gaps over 297 change."""
        current = build(2026, write=False)
        if current is None:
            self.skipTest("2026 Week 11 no longer active")
        div = {(c["name"], d["name"]): {t["team"] for t in d["contenders"]}
               for c in current["conferences"] for d in c["divisions"]}
        self.assertEqual(div[("Wild", "PLAINS")], {"Montana"})          # Wichita State 371, South Dakota 324 back
        self.assertEqual(div[("HBCU", "HURRICANE")], {"North Carolina A&T", "Delaware State"})  # Howard 311 back
        self.assertEqual(div[("Pac-12", "SOUTH")], {"Colorado", "UCLA", "Arizona State"})       # UCLA 189 < 297
        divisions = [d for c in current["conferences"] for d in c["divisions"]]
        self.assertEqual(sum(d["clinched_before_week"] for d in divisions), 13)

    def test_more_than_twenty_game_fallback(self):
        members = list("ABCDEFGHIJKL")
        games = [(members[i % 12], members[(i + 1) % 12]) for i in range(21)]
        result = self.run_case({m: 5 for m in members}, games,
                               [members[:6], members[6:]])
        self.assertEqual(len(result), 2)
        self.assertEqual([len(x) for x in result], [6, 6])


if __name__ == "__main__":
    unittest.main()


class SelectionWatchSubRow(unittest.TestCase):
    def test_playoffs_page_generator_emits_the_sub_row(self):
        """The Playoffs page is generated; the CCG / Playoffs row must come from the generator, not a hand edit."""
        from pathlib import Path
        import site_common
        src = (Path(__file__).resolve().parents[1] / "scripts" / "selection_watch_page.py").read_text(encoding="utf-8")
        self.assertIn('menu_html("selection-watch", rows=("selection-watch",))', src)
        self.assertIn('data-row="selection-watch"', site_common.menu_html("selection-watch", rows=("selection-watch",)))
