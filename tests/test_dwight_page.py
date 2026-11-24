"""Dwight Fight pages on the bracket component (task 5.18): every season draws a real bracket, byes start
in round 2, roles follow the agreed order, and the bracket component's new options leave the Playoff alone."""
import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)

import bracket as BK  # noqa: E402
import dwight_fight as dw  # noqa: E402
import dwight_page as D  # noqa: E402

ROWS = D.history_rows()
PAST = D.history_seasons(ROWS, 2026)


def played(ev, j):
    return [g for g in ev["rounds"][j] if g["a"] and g["b"]]


def seeds(games):
    return {x["seed"] for g in games for x in (g["a"], g["b"]) if x}


def test_every_past_season_is_listed_newest_first():
    assert PAST == [2025, 2024, 2023, 2022, 2021]


@pytest.mark.parametrize("year", [2021, 2022, 2023, 2024, 2025])
def test_every_recorded_game_lands_in_the_bracket(year):
    ev = D.history_event(year, ROWS)
    recorded = [r for r in ROWS if r["Season"] == str(year)]
    assert sum(len(played(ev, j)) for j in range(len(ev["rounds"]))) == len(recorded)
    final = ev["rounds"][-1][0]
    assert final["final"] and final["winner"]["team"] == next(r["Winner"] for r in recorded if r["RoundName"] == "Final")


@pytest.mark.parametrize("year", [2023, 2024, 2025])
def test_eleven_team_fields_byes_start_in_the_quarterfinal(year):
    ev = D.history_event(year, ROWS)
    assert len(ev["rounds"]) == 4
    assert len(played(ev, 0)) == 3                      # round 1: only the three games actually played
    assert seeds(played(ev, 0)) == set(range(6, 12))     # 8v9, 7v10, 6v11
    assert sum(g["bye"] for g in ev["rounds"][0]) == 5   # seeds 1-5 rest...
    assert {1, 2, 3, 4, 5} <= seeds(played(ev, 1))       # ...and appear first in the quarterfinal


def test_sixteen_team_fields_have_no_byes():
    for year in (2021, 2022):
        ev = D.history_event(year, ROWS)
        assert len(played(ev, 0)) == 8 and not any(g["bye"] for g in ev["rounds"][0])


def test_reconstructed_seasons_carry_the_note_and_stay_visible():
    for year in (2024, 2025):
        assert D.history_event(year, ROWS)["note"] == D.RECON_NOTE
    for year in (2021, 2022, 2023):
        assert D.history_event(year, ROWS)["note"] == ""


def test_a_game_that_does_not_fit_the_bracket_fails_loudly():
    bad = [dict(r) for r in ROWS if r["Season"] == "2023"]
    bad[3]["SeedB"] = "9"  # 1 v 9 in the quarterfinal: 9 lost in round 1
    with pytest.raises(ValueError):
        D.history_event(2023, bad)


def test_past_seasons_use_that_seasons_names_and_managers():
    ev = D.history_event(2023, ROWS)
    by = {x["team"]: x for x in ev["entrants"]}
    assert by["Arizona State"]["username"] == "wrightc214"
    assert by["Wake Forest"]["username"] == "WhiskyScientist"


# ------------------------------------------------------------------ roles
def test_roles_order_and_labels(monkeypatch):
    official = {"linkoftime1": ("league_manager", ""), "wrightc214": ("data_contact", ""),
                "codekhaos": ("assistant", "NCAA PAC 12")}
    short = {"NCAA PAC 12": "Pac-12"}
    cfg = D.conf()
    monkeypatch.setattr(D, "conf", lambda: {**cfg, "roles": {"WhiskyScientist": "Poll Chair", "LinkOfTime1": "Ignored"}})
    now, past = D.make_role(True, official, short), D.make_role(False, official, short)
    assert now("LinkOfTime1") == "Commissioner"          # official role beats the manual list
    assert now("wrightc214") == "Data Manager"
    assert now("CodeKhaos") == "Pac-12 Assistant"
    assert now("whiskyscientist") == "Poll Chair"         # manual list (any case)
    assert now("EthanH") == "Legacy Voter" and past("EthanH") == "Poll Voter"


def test_past_seasons_use_their_own_role_table(tmp_path):
    t = tmp_path / "roles.csv"
    t.write_text("Season,Username,Role,Note\n2021,CodeKhaos,Big East Assistant,\n2022,linkoftime1,Commissioner,\n", encoding="utf-8")
    r21 = D.make_role(False, table=D.season_roles(2021, t))
    assert r21("codekhaos") == "Big East Assistant"
    assert r21("linkoftime1") == "Poll Voter"  # no 2021 row: today's role does not leak into the past
    assert D.make_role(False, table=D.season_roles(2022, t))("LinkOfTime1") == "Commissioner"
    assert D.season_roles(2021, tmp_path / "missing.csv") == {}


def test_role_table_prefilled_for_active_role_holders():
    import csv
    rows = list(csv.DictReader(open(D.ROLES, encoding="utf-8-sig")))
    assert {(r["Season"], r["Username"], r["Role"]) for r in rows} >= {("2023", "wrightc214", "Data Manager"),
                                                                       ("2023", "linkoftime1", "Commissioner")}


def test_highest_official_role_wins():
    import league_roles as LR
    import pandas as pd
    s = {"league_manager": "boss", "data_contact": "data", "special": {},
         "owners": pd.DataFrame({"LeagueName": ["NCAA IVY", "NCAA ACC"], "DisplayName": ["boss", "helper"]}), "staff": None}
    assert LR.roles(s) == {"boss": ("league_manager", ""), "data": ("data_contact", ""), "helper": ("assistant", "NCAA ACC")}


def test_second_line_keeps_username_case_and_never_breaks_inside_a_role():
    role = D.make_role(True, {"wrightc214": ("data_contact", "")}, {})
    assert D.second_line({"username": "wrightc214"}, role) == "wrightc214 · Data Manager"
    assert D.second_line({"username": "NCAA WILD Orphan #12"}, role) == "Orphan"


# ------------------------------------------------------------------ pages
def sample_event(n=11, start=14):
    people = [{"user_id": str(i), "username": f"Dwight{i}", "display_name": f"Dwight {i}", "team": f"Test School {i}",
               "league": "Sample", "league_id": "L", "roster_id": str(i)} for i in range(1, n + 1)]
    return D._from_json(dw.draw(people, people, 17, 2026), "drawn")


def desktop_games(html):
    desk = html.split('<div class="bk-desk">', 1)[1].split('<div class="bk-phone"', 1)[0]
    return re.findall(r'class="bk-g st-(\w+)" data-r="(\d+)" data-i="(\d+)"', desk)


def test_sample_draw_renders_a_bracket():
    ev = sample_event()
    html = D.build_page(2026, ev, [], [D.history_event(y, ROWS) for y in PAST], current=True, n_req=11)
    g = desktop_games(html)
    assert [r for _, r, _ in g].count("0") == 3 and [r for _, r, _ in g].count("1") == 4
    assert "BYE" not in html.upper().replace("BK-BYE", "").replace("ST-BYE", "")
    assert "Unofficial · " in html and "Locked bracket" not in html  # initial draw, live label


@pytest.mark.parametrize("year", [2021, 2022, 2023, 2024, 2025])
def test_every_past_page_has_a_bracket(year):
    ev = D.history_event(year, ROWS)
    html = D.build_page(year, ev, [], [D.history_event(y, ROWS) for y in PAST], current=False)
    games = desktop_games(html)
    assert len(games) == sum(len(played(ev, j)) for j in range(len(ev["rounds"])))
    assert all(st == "final" for st, _, _ in games)
    assert 'class="bk-champ ' in html and "Dwight Fight Champion" in html and 'class="trophy' in html
    assert ("dw-season-note" in html) == (year in (2024, 2025))
    assert "Unofficial" not in html and "National Championship" not in html


def test_byes_leave_no_rows_and_feed_round_two():
    ev = D.history_event(2023, ROWS)
    B = D.bracket_model(ev, False, col={}, role=lambda u: "Poll Voter")
    r0, r1 = B["rounds"][0]["games"], B["rounds"][1]["games"]
    assert [g["state"] for g in r0].count("bye") == 5
    top = {g["sides"][0]["seed"] for g in r1}
    assert {1, 2, 3, 4} <= top            # the bye seed sits in its quarterfinal from the start
    desk = BK.desktop_html(B, (0.35, 0.6))
    assert desk.count('class="bk-row') == 2 * (3 + 4 + 2 + 1)  # only played games are drawn
    phone = BK.phone_html(B, (0.35, 0.6))
    assert phone.count('class="bk-card bk-bye st-bye"') == 5 and phone.count('class="bk-row') == 2 * 10


def test_row_width_option():
    ev = D.history_event(2023, ROWS)
    B = D.bracket_model(ev, False, col={}, role=lambda u: "Poll Voter")
    assert B["rw"] == 340 and 'style="width:340px;left:' in BK.desktop_html(B, (0.35, 0.6))


# ------------------------------------------------------------------ Playoff unchanged
def test_playoff_bracket_identical_with_explicit_defaults():
    import bracket_fixture as F
    import postseason_page as pp
    from poll_page import colors
    import _postseason_common as ps
    po = F.playoff_2025("final")
    short = {v: k for k, v in ps.league_short().items()}
    base = pp.bracket_html(po, colors(), 2025, short, current=False)
    real = BK.model
    try:
        BK.model = lambda R, **k: real(R, **{**dict(row_width=292, logo="", status_label="", export_name=None,
                                                    champ_file="national-champion", final_label="National Championship"), **k})
        again = pp.bracket_html(po, colors(), 2025, short, current=False)
    finally:
        BK.model = real
    assert base == again
    assert "bk-case" not in base and "bk-bye" not in base and "width:292px;" not in base


def test_component_css_unchanged_for_the_playoff():
    import postseason_page as pp
    assert BK.CSS_EXT not in pp.CSS and ".bk-bye" not in BK.CSS


def test_config_dwights_list_untouched():
    c = json.loads((ROOT / "config/league.json").read_text(encoding="utf-8"))["postseason"]["dwight_fight"]
    assert c["dwights"] == ("linkoftime1, LanceBoneau, wrightc214, laxbro000, EthanH, Romantryert, Mrhawke19, "
                            "Elestial, WhiskyScientist, agrakush, BroncoZzz")
