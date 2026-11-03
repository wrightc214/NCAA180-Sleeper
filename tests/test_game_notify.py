"""Game notifications (Chris, 2026-11-01/03): frequencies, finals at 0 minutes, windows, no repeats,
Tuesday flips. Offline: Sleeper/ESPN are replaced by the week-6 Big Sky fixture."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import game_notify as G  # noqa: E402
import notify  # noqa: E402

FIX = json.loads((ROOT / "tests" / "fixtures" / "scoreboard-week06.json").read_text())
META = json.loads((ROOT / "data" / "scoreboard" / "2026" / "players.json").read_text())
BIGSKY = {"id": "1316899756005412864", "full": "NCAA BIG SKY", "short": "Big Sky"}
WINDOWS = [("2026-10-16T00:15Z", "thu"), ("2026-10-18T17:00Z", "early"), ("2026-10-18T20:25Z", "late"),
           ("2026-10-19T00:20Z", "snf"), ("2026-10-20T00:15Z", "mnf")]


def nfl_teams():
    teams = set()
    for r in FIX["rosters"]:
        for p in r["players"]:
            t = (META.get(str(p)) or {}).get("team") or (p if not str(p).isdigit() else None)
            if t:
                teams.add(t)
    return sorted(teams)


def espn(states):
    """states: {window name: 'pre'|'in'|'post'}; teams spread over the five windows."""
    teams = nfl_teams()
    events = []
    for i in range(0, len(teams), 2):
        date, name = WINDOWS[(i // 2) % len(WINDOWS)]
        st = states.get(name, "pre")
        events.append({"date": date, "competitions": [{"status": {"type": {"state": st, "completed": st == "post"},
                                                                  "period": 4 if st != "pre" else 0,
                                                                  "displayClock": "5:00" if st == "in" else "0:00"},
                                                       "competitors": [{"team": {"abbreviation": t}} for t in teams[i:i + 2]]}]})
    return {"events": events}


def fake_get(states):
    def get(url):
        if "espn" in url:
            return espn(states)
        if "/stats/" in url:
            return FIX["stats"]
        if url.endswith("/matchups/6"):
            return FIX["rosters"]
        if "/league/" in url:
            return {"scoring_settings": FIX["scoring"]}
        raise AssertionError(url)
    return get


def device(i, freq, *rosters, test=False):
    f = [{"kind": "team", "key": f"ncaa180|Big Sky:{r}"} for r in rosters]
    if freq:
        f.append({"kind": "event", "key": f"ncaa180|freq:{freq}"})
    return {"id": f"d{i}", "is_test": test, "follows": f, "endpoint": "x", "p256dh": "x", "auth": "x"}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = [mock.patch.object(G, "LEDGER", Path(self.tmp.name) / "ledger.csv"),
                  mock.patch.object(G, "leagues", lambda season: [BIGSKY])]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def evaluate(self, states, devices):
        with mock.patch.object(G, "get", fake_get(states)):
            games, windows, live = G.build_games(2026, 6)
        sends, rows = G.plan(devices, games, windows, G.week_keys(2026, 6), 6)
        G.ledger_add([{"Year": 2026, "Week": 6, **r} for r in rows])
        return {d["id"]: p for d, p in sends}, games


class Frequencies(Base):
    DEVS = [device(1, "final", 1), device(2, "windows", 1), device(3, "sunday", 1), device(4, "off", 1),
            device(5, None, 1), device(6, "final")]

    def test_all_final(self):
        out, games = self.evaluate({w: "post" for _, w in WINDOWS}, self.DEVS)
        self.assertTrue(all(g["done"] for g in games))
        self.assertIn("Final", out["d1"]["title"])
        self.assertIn("· Final", out["d1"]["body"])
        self.assertIn("d2", out)       # a window closed
        self.assertEqual(out["d3"]["title"], "After Sunday's games")
        self.assertNotIn("d4", out)    # off
        self.assertIn("d5", out)       # no setting = final only
        self.assertNotIn("d6", out)    # no teams followed

    def test_no_repeats(self):
        self.evaluate({w: "post" for _, w in WINDOWS}, self.DEVS)
        out, _ = self.evaluate({w: "post" for _, w in WINDOWS}, self.DEVS)
        self.assertEqual(out, {})

    def test_early_window_only(self):
        out, games = self.evaluate({"thu": "post", "early": "post"}, self.DEVS)
        self.assertFalse(any(g["done"] for g in games))  # nobody is at 0 minutes yet
        self.assertNotIn("d1", out)
        self.assertEqual(out["d2"]["title"], "After Sunday's early games")
        self.assertIn("% to win", out["d2"]["body"])
        self.assertIn("proj", out["d2"]["body"])
        self.assertNotIn("d3", out)    # Sunday not over

    def test_sunday_then_monday(self):
        self.evaluate({"thu": "post", "early": "post", "late": "post", "snf": "post"}, self.DEVS)
        out, _ = self.evaluate({w: "post" for _, w in WINDOWS}, self.DEVS)
        # Sunday phones already had their summary: Monday brings only finals.
        if "d3" in out:
            self.assertIn("final", out["d3"]["title"].lower())


class Settle(Base):
    def test_flip_only(self):
        self.evaluate({w: "post" for _, w in WINDOWS}, [device(1, "final", 1)])
        rows = G.ledger_rows()
        d = json.loads(next(r for r in rows if r["Kind"] == "final" and '"Big Sky:1"' in r["Data"])["Data"])
        loser = next(t for t in d["teams"] if t["slot"] != d["winner"])
        std = Path(self.tmp.name) / "std.csv"
        lines = ["Year,LeagueID,Week,RosterID,PointsStandard"]
        for t in d["teams"]:
            lines.append(f"2026,{t['league_id']},6,{t['roster_id']},{200 if t is loser else 100}")
        std.write_text("\n".join(lines))
        sent = []
        with mock.patch.object(G, "ROOT", Path(self.tmp.name)), \
             mock.patch.object(notify, "fetch_devices", lambda: [device(1, "final", 1), device(2, "off", 1)]), \
             mock.patch.object(G, "deliver", lambda s, t=False: sent.extend(s) or (len(s), 0, 0)):
            (Path(self.tmp.name) / "data").mkdir()
            std.rename(Path(self.tmp.name) / "data" / "ScoresStandard_Season.csv")
            G.settle(2026)
        self.assertEqual([d["id"] for d, _ in sent], ["d1"])
        self.assertIn("after stat corrections", sent[0][1]["body"])
        flagged = [r for r in G.ledger_rows() if r["Kind"] == "settled"]
        self.assertTrue(any(json.loads(r["Data"])["flipped"] for r in flagged))


if __name__ == "__main__":
    unittest.main()
