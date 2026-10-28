"""Postseason export display rules (Chris, 2026-10-28)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import postseason_export as pe  # noqa: E402


class Display(unittest.TestCase):
    def test_week_labels(self):
        self.assertEqual(pe.week_label(5), ("Week 5", "Wk 5"))
        self.assertEqual(pe.week_label(12), ("CCG Week", "CCG"))
        self.assertEqual(pe.week_label(13), ("Postseason Week 1", "Post 1"))
        self.assertEqual(pe.week_label(17), ("Postseason Week 5", "Post 5"))

    def test_bowl_tiers_count_back(self):
        self.assertEqual(pe.bowl_tiers({13, 14}), {14: "Prestige Bowls", 13: "Marquee Bowls"})
        self.assertEqual(pe.bowl_tiers({13, 14, 15, 16})[13], "Opening Bowls")

    def test_round_renames(self):
        self.assertEqual(pe.round_name("NIT", 2019, "Elite 8"), "Quarterfinal")
        self.assertEqual(pe.round_name("NIT", 2021, "Pod Stage"), "Opening Groups")
        self.assertEqual(pe.round_name("NIT", 2025, "Group Stage 2"), "Qualifier Groups")
        self.assertEqual(pe.round_name("Playoff", 2019, "Elite 8"), "Elite 8")
        self.assertEqual(pe.round_name("Playoff", 2020, "Third Place"), "Third Place Game")


if __name__ == "__main__":
    unittest.main()
