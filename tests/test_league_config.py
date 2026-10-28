"""Shared settings migration guard: values the scripts used to hard-code must come back unchanged
from config/league.json (scripts that need Sleeper can't be run offline for a before/after diff)."""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import league_config as lcfg  # noqa: E402
import standard_scores_season as sss  # noqa: E402

DISPLAY = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac-12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big Ten",
    "NCAA BIG SKY": "Big Sky", "NCAA AMERICAN": "American", "NCAA SOUTHLAND": "Southland",
}


class SharedSettings(unittest.TestCase):
    def test_former_constants(self):
        self.assertEqual(lcfg.sleeper(), "https://api.sleeper.app/v1")
        self.assertEqual(lcfg.sleeper_root(), "https://api.sleeper.app")
        self.assertEqual(lcfg.espn(), "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
        self.assertEqual(lcfg.lookup_user_id(), "731808894699028480")
        self.assertEqual(lcfg.observer_ids(), {"731808894699028480"})
        self.assertEqual(lcfg.brand(), "NCAA 180")
        self.assertEqual(lcfg.last_regular_week(), 11)
        self.assertEqual(lcfg.cfg()["draft"]["pick_trade_window"], 4)
        self.assertEqual(lcfg.cfg()["managers"]["career_min_games"], 20)
        self.assertEqual(float(lcfg.cfg()["spread"]), 24.0)
        self.assertEqual(lcfg.cfg()["managers"]["legend_points"],
                         {"win": 1, "unbeaten": 5, "division": 3, "conference": 5, "bowl": 2, "nit_champ": 4, "nit_runner": 2,
                          "playoff": 5, "s16": 3, "e8": 4, "f4": 6, "final": 8, "title": 25})
        self.assertEqual(tuple(lcfg.cfg()["scoring"]["restated_keys"]), ("pass_int", "pts_allow", "yds_allow", "xpmiss"))
        self.assertEqual(lcfg.league_display(), DISPLAY)

    def test_every_league_has_a_friendly_name(self):
        # Pages show friendly names only; every league that ever existed needs one.
        import csv
        names = set()
        for f in ("data/backfill/LeagueIDs_2019_2020.csv", "data/LeagueIDs_AllYears.csv"):
            with open(lcfg.ROOT / f, encoding="utf-8-sig", newline="") as fh:
                names |= {r["LeagueName"].strip() for r in csv.DictReader(fh)}
        self.assertEqual(sorted(names - set(lcfg.league_display())), [])

    def test_season_rollover(self):
        self.assertEqual(lcfg.season(dt.date(2026, 10, 28)), 2026)
        self.assertEqual(lcfg.season(dt.date(2027, 1, 15)), 2026)  # playoffs/offseason still last season
        self.assertEqual(lcfg.season(dt.date(2027, 3, 1)), 2027)


class StandardSeason(unittest.TestCase):
    def test_tiers_from_totals(self):
        s = sss.normalized_stats({"yds_allow": 560, "pts_allow": 0})
        self.assertEqual((s["yds_allow_550p"], s["pts_allow_0"]), (1, 1))
        kept = sss.normalized_stats({"yds_allow": 560, "yds_allow_500_549": 1})  # explicit tiers win
        self.assertNotIn("yds_allow_550p", kept)

    def test_deltas_and_correction(self):
        base = {"rec": 1.0, "xpmiss": 0.0, "yds_allow_550p": -7.0}
        scoring = {"a": base, "b": dict(base), "e": dict(base), "c": {**base, "xpmiss": -1.0}, "d": {**base, "yds_allow_550p": -9.0}}
        d = sss.deltas(scoring)
        self.assertEqual(d, {"c": {"xpmiss": 1.0}, "d": {"yds_allow_550p": 2.0}})
        self.assertEqual(sss.correction({"xpmiss": 2}, d["c"]), 2.0)  # standard has no missed-XP penalty
        self.assertEqual(sss.correction({"yds_allow": 600}, d["d"]), 2.0)
        self.assertEqual(sss.correction({"yds_allow": 300}, d["d"]), 0.0)


if __name__ == "__main__":
    unittest.main()
