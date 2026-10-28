"""standard_results.apply: standard points everywhere; results decided on them from 2026 only."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import standard_results as sr  # noqa: E402


def rows(year):
    return pd.DataFrame([
        dict(Year=str(year), LeagueID="L", Week="3", RosterID="1", OpponentRosterID="2", PointsFor="100.0", PointsAgainst="101.0", Outcome="Loss"),
        dict(Year=str(year), LeagueID="L", Week="3", RosterID="2", OpponentRosterID="1", PointsFor="101.0", PointsAgainst="100.0", Outcome="Win"),
        dict(Year=str(year), LeagueID="L", Week="4", RosterID="1", OpponentRosterID="2", PointsFor="0", PointsAgainst="0", Outcome=None),
    ])


class Apply(unittest.TestCase):
    def setUp(self):
        self._orig = sr._scores
        std = {(y, "L", 3, "1"): 103.0 for y in (2025, 2026)}
        sr._scores = lambda: std

    def tearDown(self):
        sr._scores = self._orig

    def test_current_season_result_follows_standard(self):
        a = sr.apply(rows(2026))
        self.assertEqual(list(a["Outcome"][:2]), ["Win", "Loss"])
        self.assertEqual(list(a["PointsFor"][:2]), [103.0, 101.0])
        self.assertEqual(list(a["PointsAgainst"][:2]), [101.0, 103.0])
        self.assertEqual(list(a["OutcomeOfficial"][:2]), ["Loss", "Win"])
        self.assertTrue(pd.isna(a["Outcome"].iloc[2]))  # unplayed week untouched

    def test_history_shows_standard_points_but_keeps_result(self):
        a = sr.apply(rows(2025))
        self.assertEqual(list(a["Outcome"][:2]), ["Loss", "Win"])
        self.assertEqual(a["PointsFor"].iloc[0], 103.0)


if __name__ == "__main__":
    unittest.main()
