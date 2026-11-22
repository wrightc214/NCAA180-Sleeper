"""5.12.2 guard: meaningful colours come from the shared tokens, never hard-coded red/green.

The scanner and its commented allowlist live in scripts/color_literal_check.py.
"""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import color_literal_check as clc  # noqa: E402


class ColorLiteralGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = clc.scan()

    def test_no_red_green_literals_outside_tokens(self):
        bad = clc.offenders(self.results)
        self.assertEqual(bad, [], "\n" + "\n".join(
            f"{p}:{ln}: {lit} ({k}) -> use var(--good)/var(--bad)/var(--neutral) or NCAA180.colors.scale()"
            for p, ln, lit, k, _ in bad))

    def test_allowlist_has_no_stale_entries(self):
        used = {r[4] for r in self.results}
        stale = [a for i, a in enumerate(clc.ALLOW) if i not in used]
        self.assertEqual(stale, [], "allowlist entries that no longer match anything: remove them")

    def test_detector_catches_each_literal_form(self):
        kinds = lambda s: [k for _, _, k in clc.literals(s)]  # noqa: E731
        self.assertEqual(kinds(".a{color:#1a7f37}"), ["green"])
        self.assertEqual(kinds(".a{color:#c00}"), ["red"])
        self.assertEqual(kinds(".a{background:rgb(180,35,24)}"), ["red"])
        self.assertEqual(kinds(".a{background:hsl(130,65%,76%)}"), ["green"])
        self.assertEqual(kinds('f"hsl({hue:.0f},65%,50%)"'), ["computed"])
        self.assertEqual(kinds("`hsl(${h},65%,50%)`"), ["computed"])
        self.assertEqual(kinds(".a{border:1px solid green}"), ["named"])
        # Not good/bad colours: greys, amber, blue, team navy, prose.
        self.assertEqual(kinds(".a{color:#6b7484;background:#b8860b;border-color:#0758a8;fill:#14213a}"), [])
        self.assertEqual(kinds("<p>green = best, red = worst</p>"), [])

    def test_token_fallbacks_are_allowed(self):
        lits = list(clc.literals(".a{color:var(--good,#1a7f37)}"))
        self.assertEqual(len(lits), 1)
        text = ".a{color:var(--good,#1a7f37)}"
        off = lits[0][0]
        self.assertTrue(clc.TOKEN_FALLBACK.search(text[max(0, off - 80):off]))

    def test_legacy_up_dn_only_as_aliases(self):
        """Every use moved to --good/--bad; --up/--dn stay defined (aliases) for archived pages."""
        uses = []
        for path in clc.files():
            if path in ("templates/accessibility.js", "reports/assets/menu.js"):
                continue
            text = open(os.path.join(ROOT, path), encoding="utf-8").read()
            for m in re.finditer(r"var\(--(up|dn)\b", text):
                uses.append(f"{path}:{text.count(chr(10), 0, m.start()) + 1}")
        self.assertEqual(uses, [])
        a11y = open(os.path.join(ROOT, "templates/accessibility.js"), encoding="utf-8").read()
        self.assertIn(":root{--up:var(--good);--dn:var(--bad)}", a11y)
        tpl = open(os.path.join(ROOT, "templates/weekly_report.html"), encoding="utf-8").read()
        self.assertIn("--up:var(--good,", tpl)
        self.assertIn("--dn:var(--bad,", tpl)


if __name__ == "__main__":
    unittest.main()
