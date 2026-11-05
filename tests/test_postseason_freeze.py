"""Postseason weeks 13+: frozen per-team odds (matchups_page.write_post) -> scoreboard games (2026-11-04)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import matchups_page as mp  # noqa: E402
import scoreboard_data as sd  # noqa: E402


class PostseasonFreeze(unittest.TestCase):
    def test_bowl_playoff_and_group(self):
        f = os.path.join(tempfile.mkdtemp(), "post.csv")
        mp.OUT_POST = f
        row = lambda gid, rnd, l, r, seed="", bowl="": {"Round": rnd, "Stage": "", "GameID": gid, "BowlName": bowl,  # noqa: E731
                                                        "PlayoffRound": "1" if rnd == "Playoff" else "", "Seed": seed,
                                                        "LeagueID": l, "RosterID": r}
        post = {"P1": [row("P1", "Playoff", "A", "1", "32"), row("P1", "Playoff", "B", "2", "1")],
                "B1": [row("B1", "Bowl", "A", "3", bowl="Rose Bowl"), row("B1", "Bowl", "B", "4", bowl="Rose Bowl")],
                "N1": [row("N1", "NIT", "A", "5"), row("N1", "NIT", "B", "6"), row("N1", "NIT", "C", "7")]}
        rows = {(l, r): {"Best": 100 + int(r), "Current": 0, "ZeroStarters": 0, "League": l}
                for l, r in [("A", "1"), ("B", "2"), ("A", "3"), ("B", "4"), ("A", "5"), ("B", "6"), ("C", "7")]}
        self.assertTrue(mp.write_post(2026, 13, post, rows, {}, "snap"))
        self.assertTrue(mp.write_post(2026, 13, post, rows, {}, "snap"))  # second run: unchanged
        games = sd.post_games(2026, 13, f)
        self.assertEqual([g["round"] for g in games], ["Playoff", "Bowl", "NIT"])
        self.assertEqual([s["Seed"] for s in games[0]["sides"]], ["1", "32"])  # seed order
        self.assertEqual(len(games[2]["sides"]), 3)
        self.assertAlmostEqual(sum(s["WinPct"] for s in games[2]["sides"]), 100, delta=0.2)
        self.assertEqual(sum(1 for _ in open(f)), 8)  # header + 7 teams, written once


if __name__ == "__main__":
    unittest.main()
