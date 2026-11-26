import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import draft_order_rules as r


class DraftOrderRules(unittest.TestCase):
    def test_league_and_default(self):
        cfg = {"draft_order": {"default_max_pf_from": 2027, "max_pf_from": {"A": 2025, "B": None}}}
        self.assertEqual(r.basis("A", 2024, cfg), "record")
        self.assertEqual(r.basis("A", 2025, cfg), "max_pf")
        self.assertEqual(r.basis("B", 2026, cfg), "record")
        self.assertEqual(r.basis("B", 2027, cfg), "max_pf")
        self.assertEqual(r.basis("New league", 2027, cfg), "max_pf")  # added later, no entry needed

    def test_nothing_set(self):
        cfg = {"draft_order": {"default_max_pf_from": None, "max_pf_from": {}}}
        self.assertEqual(r.basis("A", 2030, cfg), "record")

    def test_live_config_loads(self):
        self.assertIn(r.basis("NCAA ACC", 2026), ("record", "max_pf"))


if __name__ == "__main__":
    unittest.main()
