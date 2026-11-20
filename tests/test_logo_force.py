"""logos.force (task 5.14): a configured logo wins on fixed team-colour backgrounds.

The forced file is used by site_common.logo_html(team, bg=<team colour>) and carried to the
front end as logo_forced (data/scoreboard/index.json). Theme-following logos (bg=None) and
white logo tiles are unchanged; a forced file that doesn't exist fails the build.
"""
import json
import os
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)
import site_common as sc  # noqa: E402

SIX = ["Tennessee", "Clemson", "Illinois", "North Carolina", "Purdue", "Oklahoma State"]


def colors():
    import csv
    with open("data/Colors - Teams.csv", encoding="utf-8-sig") as f:
        return {r["Team"]: sc.team_colors(r["Primary"], r["Secondary"], r["Background"], r["Text"], name=r["Team"])
                for r in csv.DictReader(f)}


def src(markup):
    return re.findall(r'src="([^"]*)"', markup)


class ForcedLogoTests(unittest.TestCase):
    def setUp(self):
        sc._FORCED = None  # re-read the real config for each test

    def tearDown(self):
        sc._FORCED = None

    def test_config_shape(self):
        cfg = json.loads((ROOT / "config/league.json").read_text(encoding="utf-8"))
        self.assertIn("_note", cfg["logos"])
        self.assertEqual(cfg["logos"]["force"], {t: f"glow-dark/{t}.png" for t in SIX})
        self.assertEqual(sc.forced_logos(), {t: f"glow-dark/{t}.png" for t in SIX})

    def test_forced_file_wins_on_fixed_team_colour(self):
        col = colors()
        for team in SIX:
            bg = col[team][0]
            with self.subTest(team=team, bg=bg):
                self.assertFalse(sc.is_dark(bg), "the six are mid-tone: the old rule gave the regular logo")
                self.assertEqual(src(sc.logo_html(team, bg=bg)),
                                 [f"../assets/logos/teams/glow-dark/{team.replace(' ', '%20')}.png"])
                # also on a dark fixed background and with another prefix
                self.assertEqual(src(sc.logo_html(team, prefix="", bg="#000000")),
                                 [f"assets/logos/teams/glow-dark/{team.replace(' ', '%20')}.png"])

    def test_white_tiles_and_theme_following_unchanged(self):
        for team in SIX:
            i = sc.logo_info(team)
            with self.subTest(team=team):
                self.assertEqual(src(sc.logo_html(team, bg="#ffffff")), [i["src"]])
                self.assertEqual(src(sc.logo_html(team, bg="#FAFAFA")), [i["src"]])
                theme = sc.logo_html(team, cls="logo")
                self.assertEqual(src(theme), [i["src"], i["dark"]])
                self.assertIn('class="logo tl-hd"', theme)
                self.assertIn('class="logo tl-d"', theme)

    def test_teams_without_override_unchanged(self):
        col = colors()
        teams = [t for t in col if t not in SIX and sc.logo_info(t)]
        self.assertGreater(len(teams), 100)
        for team in teams:
            i, bg = sc.logo_info(team), col[team][0]
            self.assertEqual(i["forced"], "")
            want = i["dark"] if sc.is_dark(bg) and i["dark"] else i["src"]
            self.assertEqual(src(sc.logo_html(team, bg=bg)), [want], team)

    def test_missing_forced_file_fails(self):
        cfg = {"logos": {"force": {"Clemson": "glow-dark/Nope.png"}}}
        with self.assertRaises(sc.LogoConfigError) as e:
            sc.forced_logos(cfg)
        self.assertIn("Clemson", str(e.exception))
        self.assertIn("glow-dark/Nope.png", str(e.exception))
        for bad in ("../teams/Clemson.png", "/etc/passwd", ""):
            with self.assertRaises(sc.LogoConfigError):
                sc.forced_logos({"logos": {"force": {"Clemson": bad}}})
        # and it fails the build: the first logo lookup raises
        sc._FORCED = None
        real = sc.forced_logos
        sc.forced_logos = lambda config=None: real(cfg)
        try:
            with self.assertRaises(sc.LogoConfigError):
                sc.logo_html("Tennessee", bg="#FF8200")
        finally:
            sc.forced_logos = real

    def test_unknown_team_warns(self):
        from contextlib import redirect_stderr
        import io
        buf = io.StringIO()
        with redirect_stderr(buf):
            out = sc.forced_logos({"logos": {"force": {"Not A School": "glow-dark/Clemson.png"}}})
        self.assertIn("unknown team 'Not A School'", buf.getvalue())
        self.assertIsNone(sc.logo_info("Not A School"))
        self.assertIn("Not A School", out)

    def test_scoreboard_json_carries_logo_forced(self):
        index = json.loads((ROOT / "data/scoreboard/index.json").read_text(encoding="utf-8"))
        teams = [t for lg in index["leagues"].values() for t in lg["teams"].values()]
        self.assertTrue(all("logo_forced" in t for t in teams))
        forced = {t["name"]: t["logo_forced"] for t in teams if t["logo_forced"]}
        self.assertEqual(forced, {t: f"../assets/logos/teams/glow-dark/{t.replace(' ', '%20')}.png" for t in SIX})
        for t in teams:  # same rule as the pages
            i = sc.logo_info(t["name"])
            self.assertEqual(t["logo_forced"], i["forced"] if i else "", t["name"])
        code = (ROOT / "scripts/scoreboard_data.py").read_text(encoding="utf-8")
        self.assertIn('"logo_forced": i["forced"]', code)

    def test_front_end_prefers_forced_on_team_colour_icons(self):
        for f in ("scoreboard-overview.js", "guillotine.js"):
            js = (ROOT / "reports/assets" / f).read_text(encoding="utf-8")
            self.assertRegex(js, r"logo_forced\|\|(dk&&|darkBg\()", f)


if __name__ == "__main__":
    unittest.main()
