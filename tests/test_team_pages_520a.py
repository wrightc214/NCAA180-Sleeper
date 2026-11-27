import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TeamPageRegression(unittest.TestCase):
    def test_chart_patterns_and_markers(self):
        js = (ROOT / "reports/assets/team.js").read_text()
        css = (ROOT / "scripts/team_pages.py").read_text()
        for cls in ("s1", "s2", "s3", "s4"):
            self.assertIn("series-marker." + cls, css)
            self.assertIn("series-line." + cls, css)
        self.assertIn("hit.ownerSVGElement", js)
        self.assertIn("League average", js)

    def test_totals_and_export(self):
        js = (ROOT / "reports/assets/team.js").read_text()
        self.assertIn("<tfoot>", js)
        self.assertIn("gameTotals(s.games)", js)
        self.assertIn("efficiency(records)", js)
        self.assertIn("appearances", js)
        snap = (ROOT / "reports/assets/snapshot.js").read_text()
        self.assertIn("Share unavailable; downloading PNG", snap)
        self.assertIn("overflow:visible", snap)

if __name__ == "__main__":
    unittest.main()
