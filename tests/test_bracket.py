"""Bracket component (task 5.13): model, desktop/phone markup and exports from the 2025 Playoff."""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bracket_fixture as F  # noqa: E402

import bracket as BK  # noqa: E402  (scripts/ on the path via bracket_fixture)


def desk(h):
    """The desktop board markup only (the page also carries the phone view and export templates)."""
    return h[h.index('<div class="bk-desk">'):h.index('<div class="bk-phone"')]


def games(h):
    """[(round, index, state, [(name, classes, score)...])] from desktop markup."""
    out = []
    for m in re.finditer(r'class="bk-g st-(\w+)" data-r="(\d+)" data-i="(\d+)"[^>]*>(.*?)</(?:a|div)>(?=<div class="bk-(?:g|ln|bowl|qh|cw|rh)|<a |$)', h, re.S):
        rows = re.findall(r'<div class="(bk-row[^"]*)"[^>]*>.*?<b>([^<]*)</b>.*?<span class="bk-pt">([^<]*)</span>', m.group(4), re.S)
        out.append((int(m.group(2)), int(m.group(3)), m.group(1), [(n, c, p) for c, n, p in rows]))
    return out


class Final2025(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = F.bracket("final")
        cls.d = desk(cls.h)
        cls.g = games(cls.d)

    def test_quads_named_for_elite8_bowls_in_bracket_order(self):
        qs = re.findall(r'class="bk-qh"[^>]*>(?:<img[^>]*>)?<span>([^<]*)', self.d)
        self.assertEqual(qs, ["Orange Quad", "Cotton Quad", "Peach Quad", "Fiesta Quad"])

    def test_champion_and_title_score(self):
        self.assertIn('<div class="bk-cn">Arizona State</div>', self.d)
        self.assertIn("168.32 – 112.08 over Montana", self.d)
        self.assertIn("13 seed · beat Furman, Columbia, Old Dominion, Washington State, Montana", self.d)
        self.assertIn("trophies/special/National%20Championship.png", self.d)
        self.assertNotIn("Playoffs/Trophy.png", self.h)

    def test_scores_two_decimals_and_wsu_elite8(self):
        e8 = [g for g in self.g if g[0] == 2]
        self.assertIn(("Washington State", "bk-row win", "206.80"), [r for g in e8 for r in g[3]])
        for g in self.g:
            for _, _, p in g[3]:
                self.assertRegex(p, r"^\d+\.\d\d$")

    def test_every_game_has_one_winner_and_one_dimmed_loser(self):
        self.assertEqual(len(self.g), 31)
        for g in self.g:
            cls = sorted(c for _, c, _ in g[3])
            self.assertEqual(cls, ["bk-row lose", "bk-row win"], g)

    def test_connectors_in_advancing_team_colour(self):
        # every final game draws three line pieces in its winner's row colour
        rows = re.findall(r'<div class="bk-row win" style="background:(#[0-9A-Fa-f]{6})', self.d)
        lines = re.findall(r'class="bk-ln"[^>]*background:([^"]+)"', self.d)
        self.assertNotIn("var(--line)", lines)  # nothing unplayed
        self.assertEqual(len(lines), 30 * 3 + 1)  # 30 games feed a next game; + title game -> champion
        for c in set(lines):
            self.assertIn(c, rows)

    def test_names_never_truncate(self):
        self.assertNotIn("ellipsis", BK.CSS)
        self.assertNotIn("North Carolina A&amp;T…", self.h)
        self.assertIn("<b>North Carolina A&amp;T</b>", self.d)

    def test_bowls_and_title_logo(self):
        for b in ("Orange Bowl", "Cotton Bowl", "Peach Bowl", "Fiesta Bowl", "Rose Bowl", "Sugar Bowl"):
            self.assertRegex(self.d, rf'class="bk-bowl"[^>]*><img src="[^"]*{b}\.png"[^>]*><span>{b}</span>')
        self.assertRegex(self.d, r'class="bk-bowl nc"[^>]*><img src="[^"]*National Championship\.png"[^>]*><span>National Championship</span>')

    def test_forced_logos_on_team_rows(self):
        """5.14 logos.force: a forced team's rows use its forced file in every view and export."""
        import json
        force = json.load(open(os.path.join(F.ROOT, "config", "league.json")))["logos"]["force"]
        self.assertIn("Clemson", force)
        rows = re.findall(r'<div class="bk-row[^"]*"[^>]*><span class="bk-sd">\d*</span><img src="([^"]*)"[^>]*><span class="bk-nm"><b>([^<]*)</b>', self.h)
        seen = {}
        for src, name in rows:
            if name in force:
                seen.setdefault(name, set()).add(src)
        self.assertEqual(seen.get("Clemson"), {"../assets/logos/teams/glow-dark/Clemson.png"})
        for name, srcs in seen.items():
            self.assertEqual(srcs, {"../assets/logos/teams/" + force[name].split("assets/logos/teams/")[-1]}, name)

    def test_past_season_games_have_no_scoreboard_link(self):
        self.assertNotIn('href="scoreboard.html', self.h)

    def test_exports_offered(self):
        keys = re.findall(r'<template class="bk-x" data-key="([^"]+)"[^>]*data-file="([^"]+)"', self.h)
        files = dict(keys)
        self.assertEqual(files["round-0"], "ncaa180-2025-playoff-first-round")
        self.assertEqual(files["quad-0"], "ncaa180-2025-playoff-orange-quad")
        self.assertEqual(files["quad-3"], "ncaa180-2025-playoff-fiesta-quad")
        self.assertEqual(files["e8"], "ncaa180-2025-playoff-elite-8-and-beyond")
        self.assertEqual(files["champ"], "ncaa180-2025-national-champion")
        self.assertIn('"full": "ncaa180-2025-playoff-bracket"', self.h.replace("&quot;", '"'))
        self.assertRegex(self.h, r'data-key="e8"[^>]*data-note=""')  # Elite 8 is set

    def test_export_losers_carry_precomputed_grey(self):
        m = re.search(r'class="bk-row lose" style="background:(#\w+);color:(#\w+)" data-xbg="(#\w+)" data-xfg="(#\w+)"', self.h)
        self.assertTrue(m)
        self.assertEqual(m.group(3), BK.gray_mix(m.group(1), 0.6))

    def test_elite8_beyond_has_no_quad_labels(self):
        t = re.search(r'data-key="e8".*?</template>', self.h, re.S).group(0)
        self.assertNotIn("Quad", t)
        for b in ("Orange Bowl", "Rose Bowl", "Sugar Bowl"):
            self.assertIn(f"<span>{b}</span>", t)


class MidTournament(unittest.TestCase):
    def test_sweet16_live_no_dimming_before_final(self):
        h = desk(F.bracket("s16-live"))
        g = games(h)
        s16 = [x for x in g if x[0] == 1]
        self.assertEqual(len(s16), 8)
        for x in s16:
            self.assertEqual(x[2], "live")
            self.assertEqual([c for _, c, _ in x[3]], ["bk-row", "bk-row"])  # full colour
        self.assertEqual(h.count('class="bk-live"'), 8)
        # Elite 8 on: neutral TBD slots and neutral connectors; quads named from the rotation
        self.assertEqual([x[2] for x in g if x[0] == 2], ["tbd"] * 4)
        self.assertIn("var(--line)", h)
        self.assertIn('<div class="bk-champ empty ">', h)
        qs = re.findall(r'class="bk-qh"[^>]*>(?:<img[^>]*>)?<span>([^<]*)', h)
        self.assertEqual(qs, ["Orange Quad", "Cotton Quad", "Peach Quad", "Fiesta Quad"])
        # first round is final: losers dimmed there
        self.assertEqual(sum(1 for x in g if x[0] == 0 for _, c, _ in x[3] if "lose" in c), 16)

    def test_elite8_live_and_upcoming(self):
        h = F.bracket("e8-live", ids=True)
        d = desk(h)
        g = games(d)
        self.assertEqual([x[2] for x in g if x[0] == 2], ["live", "live", "upcoming", "upcoming"])
        for x in g:
            if x[0] == 2:
                self.assertTrue(all("lose" not in c for _, c, _ in x[3]))
        self.assertRegex(h, r'data-key="e8"[^>]*data-live="1"')
        self.assertNotIn('data-key="champ"', h)  # Champion offered only once the final is final
        # every game links to its Scoreboard game view
        self.assertIn('href="scoreboard.html?season=2025&amp;week=15&amp;post=2025-P-', d)

    def test_elite8_beyond_greyed_until_set(self):
        h = F.bracket("s16-live")
        self.assertRegex(h, r'data-key="e8"[^>]*data-note="Available once the Elite 8 is set"')


class Config(unittest.TestCase):
    def test_settings_in_config(self):
        import _postseason_common as ps
        b = ps.config()[1]["display"]["bracket"]
        self.assertEqual((b["loser_opacity"], b["loser_grayscale"], b["quad_label"]), (0.35, 0.6, "{bowl} Quad"))
        self.assertIn("_note", b)

    def test_2026_quads_follow_rotation(self):
        import _postseason_common as ps
        self.assertEqual(ps.playoff_round_bowls(2026)["3"], ["Peach Bowl", "Fiesta Bowl", "Rose Bowl", "Sugar Bowl"])

    def test_quad_label_is_configurable(self):
        po = F.playoff_2025("final")
        R = BK.order_rounds([dict(g, round_key=(g["week"], g["round"])) for g in po], lambda t: int(t["Seed"]))
        B = BK.model(R, year=2025, title="t", eyebrow="e", round_names=["a"] * 5, weeks=[13, 14, 15, 16, 17],
                     side=lambda t: {"name": t["Team"], "seed": t["Seed"], "conf": "", "bg": "#000000", "fg": "#ffffff", "logo": ""},
                     quad_round=2, e8_round=2, quad_label="The {bowl} Region")
        self.assertEqual([q["name"] for q in B["quads"]], ["The Orange Region", "The Cotton Region", "The Peach Region", "The Fiesta Region"])

    def test_gray_mix_matches_css_grayscale(self):
        self.assertEqual(BK.gray_mix("#ff0000", 1), "#363636")
        self.assertEqual(BK.gray_mix("#ff0000", 0), "#ff0000")


class AllSeasons(unittest.TestCase):
    def test_every_season_with_a_knockout_renders(self):
        import postseason_page as pp
        from poll_page import colors
        col = colors()
        for y in range(2019, 2026):
            po = [g for g in pp.history_games(y) if g["event"] == "Playoff"]
            with self.subTest(year=y):
                self.assertIn('class="bk"', pp.bracket_html(po, col, y, None))

    def test_not_a_knockout_returns_empty(self):
        import postseason_page as pp
        po = F.playoff_2025("final")
        po = [g for g in po if not (g["round"] == 2 and g["teams"][0]["Team"] == "Baylor")]  # 7 Sweet 16 games
        self.assertEqual(pp.bracket_html(po, {}, 2025, None), "")


if __name__ == "__main__":
    unittest.main()


def test_playoff_round_order_is_stable_for_shared_week():
    """2020's title game and third-place game share a week and round; the page must not flip between runs."""
    import re
    from pathlib import Path
    page = (Path(__file__).resolve().parents[1] / "reports/postseason-2020.html").read_text(encoding="utf-8")
    heads = re.findall(r"<h3>([^<]*)</h3>", page)
    assert heads.index("National Championship") < heads.index("Third Place Game")
