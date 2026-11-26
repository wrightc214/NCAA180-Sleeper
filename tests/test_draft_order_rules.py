import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import draft_order_rules as r


class DraftOrderRules(unittest.TestCase):
    cfg = {"draft_order": {"default_basis": "max_pf", "record_through": {"A": 2026, "B": None}}}

    def test_default_is_max_pf(self):
        self.assertEqual(r.basis("B", 2026, self.cfg), "max_pf")
        self.assertEqual(r.basis("New league", 2030, self.cfg), "max_pf")  # added later, no entry needed

    def test_record_override_expires(self):
        self.assertEqual(r.basis("A", 2025, self.cfg), "record")
        self.assertEqual(r.basis("A", 2026, self.cfg), "record")
        self.assertEqual(r.basis("A", 2027, self.cfg), "max_pf")

    def test_live_config_loads(self):
        self.assertIn(r.basis("NCAA ACC", 2026), ("record", "max_pf"))


if __name__ == "__main__":
    unittest.main()
