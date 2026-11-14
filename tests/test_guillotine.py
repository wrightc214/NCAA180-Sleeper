"""The Guillotine (scripts/guillotine.py, Chris 2026-11-14): cut rules, PGA ties, add-only stat
corrections, the last-week tiebreak, and its pushes (postseason_announce + notify)."""
import os
import sys
import unittest

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
os.chdir(ROOT)
import guillotine as gl  # noqa: E402
import notify  # noqa: E402
import postseason_announce as pa  # noqa: E402

G = {"first_week": 13, "last_week": 17, "tiebreak_week": 18}


def field(n):
    ids = {("L", str(i)): {"LeagueName": "NCAA BIG SKY", "Team": f"T{i:03d}", "OwnerName": f"m{i}"} for i in range(n)}
    return ids


def scores(ids, week, fn):
    return {k: fn(int(k[1])) for k in ids}


class CutTests(unittest.TestCase):
    def test_half_rounded_down_no_ties(self):
        ids = field(180)
        pts = {w: scores(ids, w, lambda i, w=w: 1000 - i - w * 0.001 * i) for w in range(13, 19)}
        rows, s = gl.run(2026, None, pts, set(range(1, 19)), ids, G, now="t")
        self.assertEqual([x["advanced"] for x in s["weeks"]], [90, 45, 22, 11, 1])
        self.assertEqual(s["champions"], [("L", "0")])
        self.assertTrue(s["finished"])
        self.assertIsNone(s["next_week"])

    def test_ties_at_line_all_advance_and_next_cut_is_half_of_bigger_field(self):
        ids = field(180)
        wk13 = scores(ids, 13, lambda i: 500 - i)
        for i in (89, 90, 91):  # three teams tied at the 90th score
            wk13[("L", str(i))] = 410.0
        pts = {13: wk13, 14: scores(ids, 14, lambda i: 500 - i)}
        rows, s = gl.run(2026, None, pts, {13, 14}, ids, G, now="t")
        self.assertEqual(s["weeks"][0]["advanced"], 92)
        self.assertEqual(s["weeks"][1]["field"], 92)
        self.assertEqual(s["weeks"][1]["advance"], 46)
        self.assertEqual(s["next_week"], 15)

    def test_unfinished_week_not_cut(self):
        ids = field(20)
        rows, s = gl.run(2026, None, {13: scores(ids, 13, lambda i: i)}, {12}, ids, G, now="t")
        self.assertEqual(rows, [])
        self.assertEqual(s["next_week"], 13)
        self.assertEqual(len(s["alive"]), 20)

    def test_stat_correction_only_adds(self):
        ids = field(20)
        pts = {13: scores(ids, 13, lambda i: 100 - i)}
        rows, s = gl.run(2026, None, pts, {13}, ids, G, now="t0")
        frozen = pd.DataFrame(rows, columns=gl.COLUMNS).astype(str)
        before = {(r.LeagueID, r.RosterID) for r in frozen.itertuples() if r.Status == "Advanced"}
        self.assertEqual(len(before), 10)
        # correction: #12 jumps above the line, #9 (last one through) drops below it
        pts[13][("L", "12")] = 99.5
        pts[13][("L", "9")] = 50.0
        rows2, s2 = gl.run(2026, frozen, pts, {13}, ids, G, now="t1")
        adv = {(r["LeagueID"], r["RosterID"]) for r in rows2 if r["Status"] == "Advanced"}
        self.assertTrue(before <= adv)            # nobody removed
        self.assertIn(("L", "12"), adv)            # pushed over the line: added
        added = {(r["LeagueID"], r["RosterID"]) for r in rows2 if r["AddedByCorrection"] == "1"}
        self.assertIn(("L", "12"), added)
        self.assertEqual({r["CutLine"] for r in rows2}, {f"{91:.2f}"})  # frozen cut line kept
        self.assertEqual({r["FrozenAt"] for r in rows2}, {"t0"})

    def test_last_week_tie_goes_to_tiebreak_week_then_co_champions(self):
        ids = field(4)
        g = {**G, "first_week": 17}
        pts = {17: {k: 100.0 for k in ids}}
        pts[17][("L", "3")] = 90.0
        rows, s = gl.run(2026, None, pts, {17}, ids, g, now="t")
        self.assertEqual(s["champions"], [])
        self.assertFalse(s["finished"])
        self.assertEqual(s["next_week"], 17)
        self.assertEqual({r["Status"] for r in rows if r["RosterID"] != "3"}, {"Tied"})
        self.assertEqual(len(s["alive"]), 3)
        pts[18] = {("L", "0"): 80.0, ("L", "1"): 120.0, ("L", "2"): 70.0}
        rows, s = gl.run(2026, None, pts, {17, 18}, ids, g, now="t")
        self.assertEqual(s["champions"], [("L", "1")])
        pts[18][("L", "0")] = 120.0
        rows, s = gl.run(2026, None, pts, {17, 18}, ids, g, now="t")
        self.assertEqual(sorted(s["champions"]), [("L", "0"), ("L", "1")])  # still tied: co-champions

    def test_missing_score_counts_zero(self):
        ids = field(4)
        rows, s = gl.run(2026, None, {13: {("L", "0"): 10.0, ("L", "1"): 9.0, ("L", "2"): 8.0}}, {13}, ids, G, now="t")
        r3 = [r for r in rows if r["RosterID"] == "3"][0]
        self.assertEqual((r3["Score"], r3["Status"]), ("0.00", "Eliminated"))

    def test_replay_2025(self):
        """Real 2025 weeks 13-17 (official scores): 180 -> 90 -> 45 -> 22 -> 11 -> 1."""
        ids = gl.entrants(2025)
        self.assertEqual(len(ids), 180)
        pts = {w: {k: v[0] for k, v in gl.psc.week_points(2025, w).items()} for w in range(13, 19)}
        rows, s = gl.run(2025, None, pts, set(range(1, 19)), ids, G, now="t")
        self.assertEqual([x["advanced"] for x in s["weeks"]], [90, 45, 22, 11, 1])
        self.assertEqual(len(s["champions"]), 1)


class PushTests(unittest.TestCase):
    def gdf(self):
        ids = field(6)
        rows, _ = gl.run(2026, None, {13: scores(ids, 13, lambda i: 100 - i)}, {13}, ids, G, now="t")
        return pd.DataFrame(rows, columns=gl.COLUMNS).astype(str)

    def ann(self):
        lc = gl.psc.config()[0]
        smap = {"NCAA BIG SKY": "Big Sky"}
        return pa.guillotine_announcements(self.gdf(), 2026, smap, lc)[0]

    def test_team_follower_gets_own_line_only(self):
        a = self.ann()
        dev = {"follows": [{"kind": "team", "key": "ncaa180|Big Sky:5"}]}
        self.assertTrue(notify.matches(dev, a))
        self.assertEqual(notify.payload_for(dev, a)["body"], "The Guillotine: T005 eliminated (95.00; cut 98.00)")

    def test_event_follower_gets_summary_not_every_team(self):
        a = self.ann()
        dev = {"follows": [{"kind": "event", "key": "ncaa180|guillotine"}]}
        self.assertTrue(notify.matches(dev, a))
        self.assertEqual(notify.payload_for(dev, a)["body"], "3 of 6 survive · cut line 98.00")

    def test_all_events_device_auto_on_until_it_saves(self):
        a = self.ann()
        allev = [e["key"] for e in notify.cfg()["events"] if e["key"] != "guillotine"]
        dev = {"follows": [{"kind": "event", "key": f"ncaa180|{k}"} for k in allev]}
        self.assertTrue(notify.matches(dev, a))
        dev["follows"].append({"kind": "event", "key": "ncaa180|seen:guillotine"})  # saved on app.html, unticked
        self.assertFalse(notify.matches(dev, a))
        some = {"follows": [{"kind": "event", "key": f"ncaa180|{k}"} for k in allev[1:]]}
        self.assertFalse(notify.matches(some, a))

    def test_folds_into_week_results_push(self):
        g = self.ann()
        host = {"id": "2026-w13-results", "event": "results", "title": "Week 13 postseason results",
                "summary": "2 bowls final", "items": [{"text": "Rose Bowl: A 1 – 0 B", "tier": "Bowl", "slots": ["Big Sky:0"], "leagues": ["Big Sky"]}]}
        out = pa.fold([host], [g], sent=lambda i: False)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["also_ids"], ["2026-w13-guillotine"])
        dev = {"follows": [{"kind": "team", "key": "ncaa180|Big Sky:0"}]}
        body = notify.payload_for(dev, out[0])["body"].split("\n")
        self.assertEqual(body, ["Rose Bowl: A 1 – 0 B", "The Guillotine: T000 survives (100.00; cut 98.00)"])
        # results already sent -> the cut goes on its own
        out = pa.fold([host], [g], sent=lambda i: i == "2026-w13-results")
        self.assertEqual([x["id"] for x in out], ["2026-w13-results", "2026-w13-guillotine"])


if __name__ == "__main__":
    unittest.main()
