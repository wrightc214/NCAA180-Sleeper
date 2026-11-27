"""Regression coverage for the 5.20a team generator and generated page."""
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import team_pages as T


class TeamPageRegression(unittest.TestCase):
    def test_efficiency_excludes_missing_official_pf_and_keeps_real_zero(self):
        def game(team, points):
            return dict(Y=2026, Key=team, Outcome="Win", PointsFor="95",
                        PointsAgainst="90", PointsOfficial=points, PointsAgainstOfficial="90")

        games = pd.DataFrame([
            game("zero", "0"), game("full", "100"),
            game("partial", "80"), game("partial", ""),
            game("missing_max", "100"),
        ])
        records = T.season_records(games, 2026)
        maxima = {(2026, "zero"): 25, (2026, "full"): 100, (2026, "partial"): 150}
        self.assertEqual(T.annual_efficiencies(records, maxima), {2026: 50.0})
        self.assertEqual(T.annual_efficiencies(records, {}), {})

    def test_committed_template_matches_generator(self):
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / "team.html"
            T.write_page(generated)
            self.assertEqual(generated.read_bytes(), (ROOT / "reports/team.html").read_bytes())

    def test_luck_total_signs_positive_values(self):
        js = (ROOT / "reports/assets/team.js").read_text(encoding="utf-8")
        self.assertIn("(ac.w+ac.t/2-ac.xw>=0?'+':'')+(ac.w+ac.t/2-ac.xw).toFixed(1)", js)


if __name__ == "__main__":
    unittest.main()
