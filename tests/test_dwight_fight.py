"""Dwight Fight bracket invariants: run with pytest -q tests/test_dwight_fight.py."""
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dwight_fight as df


def entrants(n):
    return [{"user_id": str(i), "username": f"user{i}",
             "display_name": f"user{i}", "team": f"Team{i}", "league": "Test",
             "league_id": "L", "roster_id": str(i)} for i in range(1, n + 1)]


@pytest.mark.parametrize("n,first,size", [(5,15,8),(8,15,8),(11,14,16),
                                         (16,14,16),(17,13,32),(32,13,32)])
def test_bracket_dimensions(n, first, size):
    assert df.dimensions(n) == (size, first)
    b = df.draw(entrants(n), entrants(n))
    assert b["start_week"] == first
    assert b["bracket_size"] == size
    assert len(b["rounds"]) == size.bit_length() - 1


def test_oversize_fails():
    with pytest.raises(ValueError, match="at most 32"):
        df.dimensions(33)


@pytest.mark.parametrize("n", [5,11,16,17])
def test_fixed_pairings_and_byes(n):
    b = df.draw(entrants(n), entrants(n))
    assert [g["a"]["seed"] for g in b["rounds"][0]] == df.slots(b["bracket_size"])[::2]
    assert [g["b"]["seed"] if g["b"] else None for g in b["rounds"][0]] == [
        x if x <= n else None for x in df.slots(b["bracket_size"])[1::2]]
    df.advance(b, {}, {}, set())
    assert sum(bool(g["winner"]) for g in b["rounds"][0]) == b["bracket_size"] - n


def test_exact_sixteen_order():
    assert df.slots(16) == [1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11]


def test_names_case_insensitive_deduplicated():
    assert df.names(" Alice, bob, ALICE , , BoB ") == ["alice", "bob"]


def test_same_people_vs_added_removed():
    b = df.draw(entrants(5), entrants(5))
    assert df.same_members(b, entrants(5))
    assert not df.same_members(b, entrants(6))
    assert not df.same_members(b, entrants(5)[1:])


def test_renamed_user_preserves_seed_and_pairing():
    b = df.draw(entrants(8), entrants(8))
    new = entrants(8)
    new[0]["username"] = "renamed"
    new[0]["display_name"] = "New Display"
    assert df.same_members(b, new)
    df.update_names(b, new)
    assert b["entrants"][0]["username"] == "renamed"
    assert b["rounds"][0][0]["a"]["display_name"] == "New Display"
    assert b["rounds"][0][0]["a"]["seed"] == 1


class FakeResponse:
    def __init__(self, data=None, error=False):
        self.data, self.error = data, error
    def raise_for_status(self):
        if self.error:
            raise ValueError("404")
    def json(self):
        return self.data


class FakeSession:
    def __init__(self, by):
        self.by = by
    def get(self, url, timeout=None):
        return self.by.get(url.split("/")[-1], FakeResponse(error=True))


def test_unresolved_does_not_resolve_and_renamed_user_id_recovers():
    owner = {"101":{"league_id":"L","roster_id":"1","team":"Team1"}}
    saved = [{"user_id":"101","username":"oldhandle"}]
    session = FakeSession({"101": FakeResponse({"user_id":"101","username":"newhandle","display_name":"New"})})
    fresh, errors = df.resolve(["oldhandle"], owner, "api", session=session, saved=saved)
    assert not errors
    assert fresh[0]["user_id"] == "101"
    assert fresh[0]["username"] == "newhandle"
    missing, errors = df.resolve(["unknown"], owner, "api", session=session, saved=saved)
    assert missing == [] and errors


def test_tie_breaks_standard_maxpf_then_seed():
    a,b = entrants(2)
    a["seed"],b["seed"]=1,2
    assert df.choose(a,b,101,100,0,1000) is a
    assert df.choose(a,b,100,100,130,140) is b
    assert df.choose(a,b,100,100,140,140) is a


def test_frozen_advancement_ignores_corrected_scores():
    b = df.draw(entrants(2), entrants(2))
    a, other = ("L","1"), ("L","2")
    df.advance(b, {17:{a:120,other:110}}, {17:{a:150,other:140}}, {17})
    assert b["champion"]["user_id"] == "1"
    df.advance(b, {17:{a:100,other:160}}, {17:{a:130,other:180}}, {17})
    assert b["champion"]["user_id"] == "1"
    assert b["rounds"][0][0]["score_b"] == 160
    assert b["rounds"][0][0]["snapshot_b"] == 110


def test_history_rows_recorded_and_preserve_prior_seasons(tmp_path):
    p = tmp_path / "dwight.csv"
    p.write_text("Season,Round,RoundName,Week,TeamA,SeedA,TeamB,SeedB,ScoreA,ScoreB,Winner,Notes,Status\n"
                 "2023,4,Final,18,A,1,B,2,1,0,A,,Confirmed\n")
    b = df.draw(entrants(2), entrants(2))
    df.advance(b, {17:{("L","1"):3,("L","2"):2}}, {}, {17})
    df.write_history(2026,b,p)
    text=p.read_text()
    assert "2023,4,Final" in text
    assert "2026,1,Final,17" in text
    assert "Recorded" in text


def test_2023_replay(tmp_path):
    b = df.replay_2023(tmp_path)
    assert b["champion"]["team"] == "Arizona State"
    assert (tmp_path / "dwight-2023-replay.json").exists()


def test_standings_tiebreaks_win_pct_pf_then_pa(monkeypatch):
    e = entrants(3)
    rows=[]
    for team,pf,pa in ((e[0],1000,1800),(e[1],1100,1900),(e[2],1100,2000)):
        rows.append({"LeagueID":team["league_id"],"RosterID":team["roster_id"],
                     "LeagueName":"Test","Team":team["team"],"Wins":5,
                     "Losses":5,"Ties":0,"PointsFor":pf,"PointsAgainst":pa})
    monkeypatch.setattr(df.ps,"standings",lambda year:pd.DataFrame(rows))
    monkeypatch.setattr(df.ps,"regular_games",lambda year:pd.DataFrame())
    ordered=df.rank_entrants(e,2026)
    assert [v["user_id"] for v in ordered] == ["3","2","1"]
