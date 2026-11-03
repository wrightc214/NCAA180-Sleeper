"""live_model.py must give exactly the scoreboard's numbers (reports/assets/scoreboard-core.js).

Builds random players / games / stat lines, runs them through both, compares every field.
Needs node on PATH (skipped otherwise).
"""
import json
import random
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import live_model as L  # noqa: E402

CORE = ROOT / "reports" / "assets" / "scoreboard-core.js"
CFG = json.loads((ROOT / "config" / "league.json").read_text())

RULES = {"pass_yd": 0.04, "pass_td": 4, "pass_int": -1, "rush_yd": 0.1, "rush_td": 6, "rec": 1, "rec_yd": 0.1,
         "rec_td": 6, "fgm_40_49": 4, "xpm": 1, "xpmiss": -1, "pts_allow_0": 10, "pts_allow_14_20": 1,
         "pts_allow_35p": -4, "yds_allow_550p": -7, "yds_allow_0_100": 5, "def_td": 6, "sack": 1}
OFFICIAL = dict(RULES, yds_allow_550p=-9, xpmiss=0)


def rand_stats(r):
    if r.random() < 0.1:
        return None
    s = {k: round(r.uniform(0, 3 if k.endswith("td") else 120), 2) for k in r.sample(list(RULES), 6)}
    if r.random() < 0.5:
        s["pts_allow"] = r.randint(0, 45)
        s["yds_allow"] = r.randint(50, 620)
    return s


def rand_game(r):
    st = r.choice(["pre", "in", "post", "bye", None])
    if st is None:
        return None
    g = {"state": st, "period": r.randint(1, 5), "clock": f"{r.randint(0, 14)}:{r.randint(0, 59):02d}"}
    return g


def cases(n=300, seed=7):
    r = random.Random(seed)
    out = []
    for i in range(n):
        pos = r.choice(["QB", "RB", "WR", "TE", "K", "DEF"])
        meta = None if r.random() < 0.05 else {"name": f"P{i}", "position": pos, "positions": [pos],
                                               "team": "BUF", "status": r.choice(["", "", "Questionable", "Out"])}
        out.append({"id": str(i), "meta": meta, "raw": rand_stats(r), "proj": rand_stats(r), "game": rand_game(r),
                    "official": round(r.uniform(-2, 35), 2), "past": r.random() < 0.1})
    return out


JS = """
const C=require(process.argv[1]); const inp=JSON.parse(require('fs').readFileSync(0,'utf8'));
const cfg={...inp.cfg}; const players={}; const out={players:{}};
for (const c of inp.cases) { const p=C.playerModel(c.id,c.meta,c.raw||undefined,c.proj||undefined,c.game||undefined,c.official,cfg,c.past);
  players[c.id]=p; out.players[c.id]={actual:p.actual,projected:p.projected,variance:p.variance,minutes:p.minutes,phase:p.phase,baseline:p.baseline}; }
const ids=Object.keys(players); const tA={starters:ids.slice(0,9),points:120.5}, tB={starters:ids.slice(9,18).concat(['0']),points:98.25};
const a=C.teamModel(tA,players), b=C.teamModel(tB,players);
out.teams=[a,b].map(t=>({actual:t.actual,projected:t.projected,variance:t.variance,minutes:t.minutes,pregame:t.pregame}));
out.prob=C.probability(a,b);
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(shutil.which("node"), "node not installed")
class Parity(unittest.TestCase):
    def test_same_numbers_as_scoreboard(self):
        cs = cases()
        cfg = {"position_sd": CFG["position_sd"], "eligibility": CFG["eligibility"],
               "standard_scoring": RULES, "official_scoring": OFFICIAL}
        res = subprocess.run(["node", "-e", JS, str(CORE)], input=json.dumps({"cfg": cfg, "cases": cs}),
                             capture_output=True, text=True, check=True)
        js = json.loads(res.stdout)
        players = {}
        for c in cs:
            p = L.player_model(c["id"], c["meta"], c["raw"], c["proj"], c["game"], c["official"], cfg, c["past"])
            players[c["id"]] = p
            want = js["players"][c["id"]]
            for k in ("actual", "projected", "baseline", "minutes", "variance"):
                self.assertAlmostEqual(p[k], want[k], places=9, msg=f"{k} for case {c['id']}")
            self.assertEqual(p["phase"], want["phase"])
        ids = list(players)
        a = L.team_model({"starters": ids[:9], "points": 120.5}, players)
        b = L.team_model({"starters": ids[9:18] + ["0"], "points": 98.25}, players)
        for t, w in zip((a, b), js["teams"]):
            for k in ("actual", "projected", "variance", "minutes", "pregame"):
                self.assertAlmostEqual(t[k], w[k], places=9, msg=k)
        self.assertAlmostEqual(L.probability(a, b), js["prob"], places=9)


class Basics(unittest.TestCase):
    def test_remaining(self):
        self.assertEqual(L.remaining({"state": "pre"}), 1)
        self.assertEqual(L.remaining({"state": "post"}), 0)
        self.assertAlmostEqual(L.remaining({"state": "in", "period": 3, "clock": "7:30"}), (900 + 450) / 3600)

    def test_done(self):
        t = {"starters": [{"phase": "post", "minutes": 0}, {"phase": "bye", "minutes": 0}], "minutes": 0}
        self.assertTrue(L.is_done(t))
        t["starters"].append({"phase": "in", "minutes": 3})
        t["minutes"] = 3
        self.assertFalse(L.is_done(t))


if __name__ == "__main__":
    unittest.main()
