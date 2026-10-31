"""Push follow matching, ordering and privacy rules (Chris, 2026-10-30; todo-pwa.md)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import notify  # noqa: E402

CONF = {"prestige": ["Playoff", "Bowl", "NIT", "CCG"], "champions_to_team_followers": True}


def dev(*follows, test=False):
    return {"id": "d", "is_test": test, "follows": [{"kind": k, "key": "ncaa180|" + v} for k, v in follows]}


def item(text, tier, event, slots=(), leagues=(), order=0):
    return {"text": text, "tier": tier, "event": event, "slots": list(slots), "leagues": list(leagues), "order": order}


WEEK = {"id": "2026-w14-results", "event": "results", "title": "Week 14 postseason results",
        "summary": "Playoff Sweet 16 final; 2 bowls final; NIT Qualifier Groups final",
        "items": [
            item("NIT Group A: Tuskegee advances", "NIT", "nit_results", ["HBCU:3"], ["HBCU"]),
            item("Gator Bowl: Michigan 142 – 114 TCU", "Bowl", "bowl_results", ["Big Ten:5", "Big 12:2"], ["Big Ten", "Big 12"]),
            item("Sweet 16: (2) Clemson 153 – 128 (18) Murray State", "Playoff", "playoff_results",
                 ["ACC:1", "Ohio Valley:4"], ["ACC", "Ohio Valley"], order=2),
            item("Sweet 16: (1) Baylor 150 – 120 (17) Washington State", "Playoff", "playoff_results",
                 ["Big 12:7", "Pac-12:9"], ["Big 12", "Pac-12"], order=1),
            item("Sun Bowl: LSU 114 – 112 Army", "Bowl", "bowl_results", ["SEC:4", "Wild:2"], ["SEC", "Wild"]),
        ]}


class Matching(unittest.TestCase):
    def test_team_follow_matches_any_event_the_team_is_in(self):
        self.assertTrue(notify.matches(dev(("team", "HBCU:3")), WEEK, CONF))
        self.assertFalse(notify.matches(dev(("team", "HBCU:9")), WEEK, CONF))

    def test_league_follow(self):
        self.assertTrue(notify.matches(dev(("league", "SEC")), WEEK, CONF))
        self.assertFalse(notify.matches(dev(("league", "Ivy")), WEEK, CONF))

    def test_event_toggle(self):
        self.assertTrue(notify.matches(dev(("event", "bowl_results")), WEEK, CONF))
        self.assertFalse(notify.matches(dev(("event", "ccg_results")), WEEK, CONF))

    def test_playoff_team_never_sees_nit_unless_it_follows_it(self):
        body = notify.body_for(dev(("team", "ACC:1")), WEEK, CONF)
        self.assertIn("Clemson", body)
        self.assertNotIn("Tuskegee", body)
        self.assertNotIn("Gator", body)

    def test_lm_audience_never_pushes(self):
        ann = dict(WEEK, audience="lm")
        self.assertFalse(notify.matches(dev(("event", "bowl_results"), ("team", "HBCU:3")), ann, CONF))

    def test_test_sends_reach_testers_only(self):
        ann = dict(WEEK, test=True)
        self.assertFalse(notify.matches(dev(("team", "HBCU:3")), ann, CONF))
        self.assertTrue(notify.matches(dev(("team", "HBCU:3"), test=True), ann, CONF))


class Ordering(unittest.TestCase):
    def test_own_teams_first_then_prestige(self):
        d = dev(("team", "HBCU:3"), ("event", "playoff_results"), ("event", "bowl_results"), ("event", "nit_results"))
        lines = notify.body_for(d, WEEK, CONF).split("\n")
        self.assertTrue(lines[0].startswith("NIT Group A"))  # own team first, even though NIT
        self.assertTrue(lines[1].startswith("Sweet 16: (1) Baylor"))  # then playoff, by seed
        self.assertTrue(lines[2].startswith("Sweet 16: (2) Clemson"))
        self.assertEqual(lines[3], "+2 more")  # 2 bowls left, capped at MAX_LINES

    def test_one_push_per_device_even_with_several_matches(self):
        # team + league + event all match: still one payload (one announcement -> one push)
        d = dev(("team", "SEC:4"), ("league", "SEC"), ("event", "bowl_results"))
        self.assertTrue(notify.matches(d, WEEK, CONF))
        body = notify.body_for(d, WEEK, CONF)
        self.assertEqual(body.count("Sun Bowl"), 1)

    def test_event_only_device_gets_summary_line_first(self):
        lines = notify.body_for(dev(("event", "bowl_results")), WEEK, CONF).split("\n")
        self.assertEqual(lines[0], WEEK["summary"])
        self.assertTrue(all("Bowl" in x for x in lines[1:]))


class Champions(unittest.TestCase):
    CHAMP = {"id": "2026-champion", "event": "champions", "also_events": ["playoff_results"], "champion": True,
             "title": "National champion: Arizona State", "summary": "",
             "items": [item("National Championship: (13) Arizona State 168 – 112 (6) Montana", "Playoff",
                            "playoff_results", ["Pac-12:6", "Big Sky:2"], ["Pac-12", "Big Sky"])]}

    def test_any_team_follower_gets_champion(self):
        self.assertTrue(notify.matches(dev(("team", "Ivy:1")), self.CHAMP, CONF))
        self.assertIn("Arizona State", notify.body_for(dev(("team", "Ivy:1")), self.CHAMP, CONF))

    def test_league_only_follower_needs_the_toggle(self):
        self.assertFalse(notify.matches(dev(("league", "Ivy")), self.CHAMP, CONF))
        self.assertTrue(notify.matches(dev(("league", "Ivy"), ("event", "champions")), self.CHAMP, CONF))

    def test_round_followers_get_the_title_game(self):
        self.assertTrue(notify.matches(dev(("event", "playoff_results")), self.CHAMP, CONF))


class Groups(unittest.TestCase):
    def test_other_super_leagues_follows_are_ignored(self):
        d = {"follows": [{"kind": "team", "key": "otherleague|HBCU:3"}, {"kind": "event", "key": "otherleague|bowl_results"}]}
        self.assertFalse(notify.matches(d, WEEK, CONF))


class Keys(unittest.TestCase):
    def test_slot_key_uses_short_name_and_int_roster(self):
        self.assertEqual(notify.slot_key("Big Sky", "6"), "Big Sky:6")
        self.assertEqual(notify.slot_key("Pac-12", 6.0), "Pac-12:6")

    def test_short_map_covers_teams(self):
        m = notify.league_short_map()
        self.assertEqual(m["NCAA BIG 10"], "Big Ten")


if __name__ == "__main__":
    unittest.main()
