"""refresh_labels: frozen odds stay; rank/record labels follow the latest data (2026-11-04)."""
import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import matchups_page as mp  # noqa: E402

COLS = ["Year", "Week", "LeagueID", "RosterID", "OpponentRosterID", "Rank", "Rec", "OppRank", "OppRec",
        "WinPct", "EveryWeekLeader", "EveryWeek"]


class RefreshLabels(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False).name
        pd.DataFrame([["2026", "9", "L", "1", "2", "7", "6-0", "", "5-1", "60.0", "", "3-3"]], columns=COLS).to_csv(self.f, index=False)
        mp.OUT_HIST = self.f

    def tearDown(self):
        os.remove(self.f)

    def g(self):  # new run, opposite orientation
        return pd.DataFrame([["2026", "9", "L", "2", "1", "3", "6-1", "1", "7-0", "40.0", "A", "4-3"]], columns=COLS)

    def test_flip_and_odds_frozen(self):
        self.assertTrue(mp.refresh_labels(self.g(), True))
        r = pd.read_csv(self.f, dtype=str, keep_default_na=False).iloc[0]
        self.assertEqual((r.Rank, r.Rec, r.OppRank, r.OppRec, r.EveryWeek), ("1", "7-0", "3", "6-1", "4-3"))
        self.assertEqual(r.WinPct, "60.0")

    def test_stale_poll_keeps_ranks(self):
        mp.refresh_labels(self.g(), False)
        r = pd.read_csv(self.f, dtype=str, keep_default_na=False).iloc[0]
        self.assertEqual((r.Rank, r.Rec), ("7", "7-0"))


if __name__ == "__main__":
    unittest.main()
