"""Team pages (task 5.20): season matching (Python side; JS twin in tests/team-link.test.js, same cases),
settings defaults, and the built team files against the repo's own data.
Run from the repo root: python -m pytest tests/test_team_pages.py"""
import glob
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)

import pandas as pd  # noqa: E402

import team_pages as T  # noqa: E402

F = json.loads((ROOT / "tests" / "fixtures" / "team_link_cases.json").read_text(encoding="utf-8"))


class Matching(unittest.TestCase):
    def test_season_key(self):
        for (lg, r), want in F["season_key"]:
            self.assertEqual(T.season_key(lg, r), want)

    def test_current_team(self):
        for c in F["current_team"]:
            i = c["in"]
            got = T.current_team(F["index"], league_id=i.get("leagueId"), league_name=i.get("leagueName"), roster=i.get("roster"))
            self.assertEqual(list(got) if got else None, c["out"], c["_case"])

    def test_matching_seasons(self):
        kb = {int(y): set(v) for y, v in F["matching_seasons"]["keys_by_year"].items()}
        for (lg, r), want in F["matching_seasons"]["cases"]:
            self.assertEqual(T.matching_seasons(T.season_key(lg, r), kb), want)

    def test_file_names_survive_league_id_changes(self):
        self.assertEqual(T.team_file("NCAA PAC 12 ", "7"), "ncaa-pac-12-7.json")
        self.assertEqual(T.team_file("NCAA BIG EAST & CO.", 3), "ncaa-big-east-co-3.json")


class NoRealNames(unittest.TestCase):
    """The site is public: team-page files never name a real person (league data role instead)."""

    def test_team_page_sources(self):
        for f in ("scripts/team_pages.py", "reports/assets/team.js", "reports/assets/team-link.js", "config/team_pages.json",
                  "tests/test_team_pages.py", "tests/test_team_pages_browser.py", "tests/team-link.test.js"):
            text = (ROOT / f).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\bChris(?!\s+(Godwin|Olave|Bell|Rodriguez))(?:'s)?\b", f)


class Settings(unittest.TestCase):
    def test_defaults_and_bad_values(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            Path(p).write_text(json.dumps({"_note": "x", "transactions_shown": -3, "position_order": "QB",
                                           "current_season_open": "yes", "unknown": 1}))
            self.assertEqual(T.settings(p), T.DEFAULTS)
            self.assertEqual(T.settings(os.path.join(d, "missing.json")), T.DEFAULTS)
            Path(p).write_text(json.dumps({"transactions_shown": 10, "position_order": ["qb", "rb"]}))
            s = T.settings(p)
            self.assertEqual((s["transactions_shown"], s["position_order"]), (10, ["QB", "RB"]))

    def test_repo_config_is_valid(self):
        raw = json.loads((ROOT / "config" / "team_pages.json").read_text(encoding="utf-8"))
        self.assertTrue(raw.get("_note"))
        self.assertEqual({k for k in raw if not k.startswith("_")}, set(T.DEFAULTS))


class RealData(unittest.TestCase):
    """The same three situations in the league's own history, through the full build."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.index = T.build(out_dir=cls.tmp.name, page=os.path.join(cls.tmp.name, "team.html"))
        cls.files = {os.path.basename(f): json.load(open(f, encoding="utf-8")) for f in glob.glob(os.path.join(cls.tmp.name, "ncaa-*.json"))}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def team(self, league, roster):
        return self.files[T.team_file(league, roster)]

    def test_every_current_team_has_a_file(self):
        teams = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
        current = [d for d in self.files.values() if not d.get("defunct")]
        self.assertEqual(len(current), len(teams))
        self.assertEqual(sum(1 for v in self.index["teams"].values() for t in v.values() if not t.get("defunct")), len(teams))

    def test_defunct_teams_get_pages(self):
        defunct = {d["key"]: d for d in self.files.values() if d.get("defunct")}
        self.assertEqual(len(defunct), 24)  # 2019 American + 2020 Southland
        ohio = self.team("NCAA AMERICAN", 5)
        self.assertEqual((ohio["name"], ohio["defunct"], ohio["roster_groups"]), ("Ohio", {"first": 2019, "last": 2019}, []))
        self.assertTrue(ohio["trophies"] and ohio["seasons"] and ohio["transactions"])
        lid = T.current_team(self.index, league_name="NCAA AMERICAN", roster=5)[0]
        self.assertEqual(T.league_ids()[lid], (2019, "NCAA AMERICAN"))
        self.assertTrue(self.index["leagues"][lid]["defunct"])
        self.assertEqual(self.team("NCAA SOUTHLAND", 8)["defunct"]["last"], 2020)
        all_trophies = len(pd.concat([pd.read_csv(f, dtype=str) for f in T.TROPHY_FILES]))
        self.assertEqual(sum(len(d["trophies"]) for d in self.files.values()), all_trophies, "every trophy is on a page")

    def test_history_links_cover_defunct_teams(self):
        links = T.team_links(2019)
        self.assertEqual(links["Ohio"], list(T.current_team(self.index, league_name="NCAA AMERICAN", roster=5)))
        self.assertEqual(links["Fresno State"], list(T.current_team(self.index, league_name="NCAA MOUNTAIN WEST", roster=4)))

    def test_renamed_school(self):
        d = self.team("NCAA MOUNTAIN WEST", 4)  # Fresno State 2019-2021, Air Force since 2022
        self.assertEqual(d["name"], "Air Force")
        names = {s["year"]: s["name"] for s in d["seasons"]}
        self.assertEqual((names[2021], names[2022]), ("Fresno State", "Air Force"))
        self.assertIn({"name": "Fresno State", "from": 2019, "to": 2021}, d["former"])
        self.assertEqual(next(s for s in d["seasons"] if s["year"] == 2021)["identity"]["name"], "Fresno State")
        self.assertTrue(any(t["Team"] == "Fresno State" for t in d["trophies"]), "a trophy won under the old name stays with the roster")

    def test_manager_change_same_roster(self):
        changed = [d for d in self.files.values() if len({s["manager"] for s in d["seasons"] if s["manager"]}) > 1]
        self.assertTrue(changed)
        d = self.team("NCAA MOUNTAIN WEST", 4)
        mgr = {s["year"]: s["manager"] for s in d["seasons"]}
        self.assertNotEqual(mgr[2019], mgr[2025])  # one roster, several managers: still one team
        self.assertEqual(len(d["seasons"]), len({s["year"] for s in d["seasons"]}))

    def test_pf_pa_are_standard_totals(self):
        d = self.team("NCAA MOUNTAIN WEST", 4)
        for s in d["seasons"]:
            reg = [g for g in s["games"] if g["kind"] == "reg" and "pf" in g]
            if s["record"]:
                self.assertAlmostEqual(s["record"]["pf"], sum(g["pf"] for g in reg), places=1)
                self.assertAlmostEqual(s["record"]["pa"], sum(g["pa"] for g in reg), places=1)

    def test_season_where_roster_did_not_exist(self):
        d = self.team("NCAA OHIO VALLEY", 1)  # league founded 2021
        years = [s["year"] for s in d["seasons"]]
        self.assertEqual(min(years), 2021)
        self.assertEqual(years, sorted(years, reverse=True))
        for lg in ("NCAA BIG SKY", "NCAA PIONEER"):  # founded 2020: no 2019 block
            self.assertNotIn(2019, [s["year"] for s in self.team(lg, 1)["seasons"]])

    def test_records_match_the_standings_pages(self):
        short = {v: k for k, v in T.lcfg.league_display().items()}
        seen = {(s["year"], d["league"], s["name"]): s for d in self.files.values() for s in d["seasons"]}
        files = sorted(glob.glob("data/standings/OverallStandings_*.csv"))
        checked = 0
        for f in files:
            y = int(os.path.basename(f)[17:21])
            for r in pd.read_csv(f).to_dict("records"):
                s = seen.get((y, short[r["League"]], r["Team"]))
                if s is None:
                    continue
                checked += 1
                rec = s["record"]
                self.assertEqual((rec["w"], rec["l"], rec["t"]), (r["Wins"], r["Losses"], r["Ties"]), (y, r["Team"]))
                # PF is shown on standard totals; the Standings files carry the points that season ranked on
                self.assertAlmostEqual(rec["pf"] if y >= T.standard_results.standard_from() else rec["pf_official"], r["Points"], places=1)
                self.assertEqual(s["place"][0], r["Division Place"], (y, r["Team"]))
        self.assertGreater(checked, 800)

    def test_sections_present_and_newest_first(self):
        d = self.team("NCAA MOUNTAIN WEST", 4)
        for k in ("roster_groups", "trophies", "seasons", "drafts", "transactions"):
            self.assertIn(k, d)
        self.assertTrue(all(a["t"] >= b["t"] for a, b in zip(d["transactions"], d["transactions"][1:])))
        self.assertTrue(all(int(a["Season"]) >= int(b["Season"]) for a, b in zip(d["trophies"], d["trophies"][1:])))
        trades = [t for t in d["transactions"] if "html" in t]
        self.assertTrue(trades and all('class="tx-card' in t["html"] for t in trades), "trades use the Transactions page card")

    def test_overview_roster_picks_charts(self):
        d = self.team("NCAA PAC 12", 7)
        o = d["overview"]
        for k in ("map", "poll", "bots", "odds", "trend"):
            self.assertIn(k, o)
        self.assertEqual(len(o["map"]["dyn"]), 3, "value, rank, last week's rank")
        first = d["first_value"]["value"]
        for g in d["roster_groups"]:
            vals = [p["value"] for p in g["players"]]
            self.assertEqual(vals, sorted(vals, reverse=True), g["pos"])
            for p in g["players"]:
                self.assertEqual(bool(p.get("star")), p["value"] > first, p["name"])
        self.assertTrue(d["picks"]["owned"] >= len(d["picks"]["picks"]))
        s25 = next(s for s in d["seasons"] if s["year"] == 2025)
        self.assertGreater(s25["record"]["max"], s25["record"]["pf"])
        self.assertEqual(sum(s25["record"]["ap"]), 11 * 11, "all-play: 11 weeks x 11 opponents")
        self.assertEqual(s25["poll"]["summary"]["cons"]["final"], s25["poll"]["cons"][-1][1])
        mg = d["managers"]
        self.assertEqual(sum(m["w"] for m in mg), sum(s["record"]["w"] for s in d["seasons"] if s["record"]))
        self.assertEqual(sum(len(m["years"]) for m in mg), len(d["seasons"]))
        h = d["h2h"]
        self.assertTrue(h and all(x["w"] + x["l"] + x["t"] > 0 for x in h))
        games = sum(1 for s in d["seasons"] for g in s["games"] if g.get("res") and g.get("opp_key"))
        self.assertEqual(sum(x["w"] + x["l"] + x["t"] for x in h), games)

    def test_defunct_has_no_current_data(self):
        d = self.team("NCAA AMERICAN", 5)
        for k in ("overview", "picks", "first_value"):
            self.assertNotIn(k, d)
        self.assertTrue(d["managers"] and d["h2h"])

    def test_manager_is_a_username(self):
        users = set(pd.read_csv("data/Rosters_Current.csv", dtype=str)["OwnerName"].dropna()) | {"Orphan"}
        for d in self.files.values():
            if not d.get("defunct"):
                self.assertIn(d["manager"], users)


if __name__ == "__main__":
    unittest.main()
