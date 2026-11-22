"""Champions League engine (scripts/champions_league.py; Chris, 2026-11-21)."""
import json
import os
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)
import champions_league as cl  # noqa: E402


class Schedule(unittest.TestCase):
    def test_fixed_schedule_is_a_full_round_robin(self):
        c = cl.settings()
        s = cl.load_schedule(c["schedule_file"])
        self.assertEqual(sorted(s), list(range(c["pod_weeks"][0], c["pod_weeks"][1] + 1)))
        self.assertTrue(cl.validate_schedule(s, c["field_size"]))

    def test_validation_catches_a_repeat(self):
        s = cl.load_schedule(cl.settings()["schedule_file"])
        a, b = s[1][0], s[1][1]
        s[1][0], s[1][1] = (a[0], b[1], a[2]), (b[0], a[1], b[2])
        with self.assertRaises(ValueError):
            cl.validate_schedule(s)


class PodPoints(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(cl.pod_points({"a": 120, "b": 100, "c": 90}), {"a": 3, "b": 1, "c": 0})

    def test_ties_split_and_total_four(self):
        self.assertEqual(cl.pod_points({"a": 100, "b": 100, "c": 90}), {"a": 2, "b": 2, "c": 0})
        self.assertEqual(cl.pod_points({"a": 110, "b": 90, "c": 90}), {"a": 3, "b": 0.5, "c": 0.5})
        three = cl.pod_points({"a": 90, "b": 90, "c": 90})
        self.assertAlmostEqual(sum(three.values()), 4)
        self.assertAlmostEqual(three["a"], 4 / 3)

    def test_allplay_counts_ties_half(self):
        self.assertEqual(cl.allplay_wins({"a": 10, "b": 10, "c": 5}), {"a": 1.5, "b": 1.5, "c": 0.0})


class Tiebreaks(unittest.TestCase):
    def ties(self, metrics, weekly=None):
        teams = list(next(iter(metrics.values())))
        return cl.Ties(2025, metrics, weekly or {}, 11, {t: t for t in teams})

    def test_unique_best_wins_then_restart(self):
        t = self.ties({"rank_sum": {"a": 5, "b": 5, "c": 5}, "best_worst_rank": {"a": 9, "b": 4, "c": 6}})
        self.assertEqual(t.order(["a", "b", "c"], ["rank_sum", "best_worst_rank"]), ["b", "c", "a"])

    def test_drop_worst_before_next_step(self):
        # a and b tie on step 2 at the top; c loses to both -> drops; a/b restart and go to step 3
        t = self.ties({"rank_sum": {"a": 5, "b": 5, "c": 5}, "best_worst_rank": {"a": 4, "b": 4, "c": 9},
                       "bestball_total": {"a": -100, "b": -120, "c": -200}})
        self.assertEqual(t.order(["a", "b", "c"], ["rank_sum", "best_worst_rank", "bestball_total"]), ["b", "a", "c"])

    def test_h2h_windows_then_coin(self):
        weekly = {1: {"a": 10, "b": 5}, 2: {"a": 5, "b": 10}, 3: {"a": 1, "b": 9}}
        t = self.ties({"rank_sum": {"a": 1, "b": 1}}, weekly)
        t.h2h_last = 3
        # weeks 1-3: b 2-1 -> b wins
        self.assertEqual(t.order(["a", "b"], ["rank_sum", "h2h", "coin_toss"]), ["b", "a"])

    def test_cycle_moves_on(self):
        weekly = {1: {"a": 3, "b": 2, "c": 1}, 2: {"a": 1, "b": 3, "c": 2}, 3: {"a": 2, "b": 1, "c": 3}}
        t = self.ties({"rank_sum": {"a": 1, "b": 1, "c": 1}, "bestball_total": {"a": -1, "b": -3, "c": -2}}, weekly)
        t.h2h_last = 3
        # weeks 1-3: a>b, b>c, c>a (a cycle) -> weeks 2-3: no one beats/loses to all -> week 3 only: c beats both.
        # a and b restart: weeks 1-3, a beats b 2-1.
        self.assertEqual(t.order(["a", "b", "c"], ["rank_sum", "h2h", "bestball_total"]), ["c", "a", "b"])

    def test_rank_order_only_breaks_ties_inside_groups(self):
        t = self.ties({"rank_sum": {"a": 1, "b": 3, "c": 3, "d": 9}, "best_worst_rank": {"a": 50, "b": 7, "c": 5, "d": 1}})
        self.assertEqual(t.rank_order(["d", "c", "b", "a"], ["rank_sum", "best_worst_rank"]), ["a", "c", "b", "d"])

    def test_recorded_coin_toss(self):
        t = cl.Ties(2025, {"x": {"a": 1, "b": 1}}, {}, 11, {"a": "Alpha", "b": "Beta"},
                    [{"season": 2025, "teams": ["Alpha", "Beta"], "order": ["Beta", "Alpha"]}])
        self.assertEqual(t.coin(["a", "b"]), ["b", "a"])


class Standings(unittest.TestCase):
    def test_cup_and_head_start(self):
        c = {**cl.settings(), "pod_weeks": [1, 1], "cup_weeks": [2, 3], "cup_size": 3}
        sched = {1: [(1, 2, 3)]}
        field = {1: "a", 2: "b", 3: "c"}
        weekly = {1: {"a": 100, "b": 90, "c": 80}}
        table, weeks, cup = cl.standings(field, sched, weekly, c, {}, 2026)
        self.assertEqual([r["pts"] for r in table], [3, 1, 0])
        self.assertEqual(cup, ["a", "b", "c"])
        res = cl.cup_result(cup, {2: {"a": 50, "b": 55, "c": 60}, 3: {"a": 50, "b": 50, "c": 50}}, c)
        # totals: a 10+100=110, b 5+105=110, c 0+110=110 -> tie -> higher seed
        self.assertTrue(res["final"])
        self.assertEqual(res["champion"], "a")


class Golden(unittest.TestCase):
    """The committed 2026 dev field (from 2025) is what the engine builds."""

    def test_field_2026_reproduces(self):
        f = cl.read_field(2026)
        self.assertIsNotNone(f)
        res = cl.select(2025)
        got = [(r["Seed"], r["Team"], r["Route"]) for r in res["rows"]]
        want = [(int(r.Seed), r.Team, r.Route) for r in f.itertuples()]
        self.assertEqual(got, want)
        self.assertEqual(len(want), 33)
        self.assertEqual(len({r.LeagueName for r in f.itertuples()}), res["leagues"])  # league guarantee held

    def test_season_json_points_add_up(self):
        p = ROOT / "data/scoreboard/2026/champions-league.json"
        d = json.loads(p.read_text())
        played = len(d["weeks"])
        self.assertAlmostEqual(sum(r["pts"] for r in d["standings"]), 11 * 4 * played)
        self.assertEqual(len(d["teams"]), 33)


if __name__ == "__main__":
    unittest.main()
