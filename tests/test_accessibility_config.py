"""Run with: python -m unittest discover -s tests -p 'test_accessibility_config.py'"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from accessibility_config import accessibility_config


class AccessibilityConfigTests(unittest.TestCase):
    def test_missing_file_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            config = accessibility_config(Path(d) / "missing.json")
            self.assertEqual(config["palettes"]["standard"]["light"]["positive"], "#1a7f37")
            self.assertTrue(config["defaults"]["auto_contrast"])

    def test_partial_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "accessibility.json"
            path.write_text(json.dumps({
                "palettes": {"standard": {"light": {"positive": "#123456", "negative": "oops"}}},
                "contrast": {"minimum_ratio": -2, "distinguishability_ratio": 2.1},
                "defaults": {"mode": "invalid", "auto_contrast": False},
            }), encoding="utf-8")
            config = accessibility_config(path)
            self.assertEqual(config["palettes"]["standard"]["light"]["positive"], "#123456")
            self.assertEqual(config["palettes"]["standard"]["light"]["negative"], "#b42318")
            self.assertEqual(config["contrast"]["minimum_ratio"], 4.5)
            self.assertEqual(config["contrast"]["distinguishability_ratio"], 2.1)
            self.assertEqual(config["defaults"]["mode"], "standard")
            self.assertFalse(config["defaults"]["auto_contrast"])


if __name__ == "__main__":
    unittest.main()
