"""Trophy ledger + shared trophy component (task 5.1)."""
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)
import _postseason_common as ps  # noqa: E402
import postseason_page as pp  # noqa: E402
import trophies as T  # noqa: E402

NODE = shutil.which("node")
PLAQUE_GREY = (0xCF, 0xD4, 0xD8, 255)

EXPECTED = {  # trophies per season and event type (PR_README lists these)
    "2019": {"Bowl": 27, "CCG": 11, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
    "2020": {"Bowl": 30, "CCG": 15, "DwightFight": 0, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
    "2021": {"Bowl": 28, "CCG": 15, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 0},
    "2022": {"Bowl": 26, "CCG": 15, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
    "2023": {"Bowl": 31, "CCG": 15, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
    "2024": {"Bowl": 30, "CCG": 15, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
    "2025": {"Bowl": 30, "CCG": 15, "DwightFight": 1, "NIT": 1, "NationalTitle": 1, "PlayoffRound": 6},
}


def hist():
    return pd.read_csv(ROOT / T.HIST, dtype=str, keep_default_na=False)


# ------------------------------------------------------------------ ledger
def test_historic_counts_by_season_and_type():
    h = hist()
    got = h.groupby(["Season", "EventType"]).size().unstack(fill_value=0).to_dict("index")
    assert {y: {k: v for k, v in d.items()} for y, d in got.items()} == EXPECTED
    assert list(h.columns) == T.COLUMNS


def test_historic_file_is_what_the_backfill_builds():
    # frozen file == one-time backfill output (until a reviewed hand edit says otherwise)
    assert T.build_historic().to_dict("records") == hist().to_dict("records")


def test_every_row_has_a_roster_slot():
    h = hist()
    assert (h["LeagueID"] != "").all() and (h["RosterID"] != "").all()


def test_every_row_maps_to_art_or_the_generic_stand_in():
    for r in T.ledger().to_dict("records"):
        assert r["ArtKey"] == T.art_key(r)
        drawn = T.resolved_art(r)
        assert drawn in (r["ArtKey"], T.generic_key(r)) and os.path.exists(drawn), r
        out = T.trophy_html(r)
        assert f'src="../{T.urllib.parse.quote(drawn)}"' in out and "fallback" not in out


def test_unmatched_bowls_and_conferences_use_the_generic_trophy():
    b = T.trophy_html({"EventType": "Bowl", "Event": "Belk Bowl"}, "Furman", 2020)
    assert "Generic%20Bowl.png" in b and "2020 Belk Bowl" in b
    c = T.trophy_html({"EventType": "CCG", "Conference": "Southland"}, "Dixie State", 2020)
    assert "Generic%20Conference.png" in c and "2020 Southland Champion" in c
    assert "Generic%20Bowl.png" in T.trophy_html({"EventType": "PlayoffRound", "Event": "New Bowl", "Round": "Elite 8"}, "X", 2030)


def test_spot_check_2025_against_postseason_history():
    h = hist()
    y = h[h["Season"] == "2025"]
    nt = y[y["EventType"] == "NationalTitle"]
    assert nt["Team"].tolist() == ["Arizona State"] and nt["Conference"].tolist() == ["Pac-12"]
    ph = pd.read_csv(ROOT / T.POST_HIST, dtype=str, keep_default_na=False)
    ccg = ph[(ph["Season"] == "2025") & (ph["Event"] == "CCG")]
    want = dict(zip(ccg["Bowl"], ccg["Winner"]))
    got = {r["Conference"]: r["Team"] for r in y[y["EventType"] == "CCG"].to_dict("records")}
    assert got == want and len(got) == 15
    pr = {(r["Event"], r["Round"]): r["Team"] for r in y[y["EventType"] == "PlayoffRound"].to_dict("records")}
    assert pr[("Rose Bowl", "Final Four")] == "Arizona State" and pr[("Sugar Bowl", "Final Four")] == "Montana"
    assert y[y["EventType"] == "NIT"]["Team"].tolist() == ["Tuskegee"]


def season_fixture(tmp_path):
    """A published 2026 season (Postseason_Season format) + final Guillotine and Dwight Fight files."""
    cols = ps.COLUMNS

    def game(rnd, stage, gid, bowl, winner, loser, week, pr=""):
        out = []
        for t, o in ((winner, "Win"), (loser, "Loss")):
            sl = T.tn.slot(2026, t)
            out.append({**{c: "" for c in cols}, "Year": "2026", "Round": rnd, "Stage": stage, "Week": str(week), "GameID": gid,
                        "BowlName": bowl, "PlayoffRound": pr, "LeagueName": sl[0], "RosterID": sl[1],
                        "LeagueID": T.league_ids()[("2026", sl[0].strip())], "Team": t, "Outcome": o, "Status": "Final",
                        "Points": "100" if o == "Win" else "90"})
        return out
    rows = (game("CCG", "Big Sky", "2026-CCG-1", "", "Montana State", "Montana", 12)
            + game("Bowl", "", "2026-BOWL-GatorBowl", "Gator Bowl", "Clemson", "Duke", 16)
            + game("Playoff", "Final Four", "2026-PO-R4-G01", "Orange Bowl", "Arizona State", "Baylor", 16, "4")
            + game("Playoff", "National Championship", "2026-PO-R5-G01", "", "Arizona State", "Clemson", 17, "5")
            + game("NIT", "Final", "2026-NIT-F", "Final", "Tuskegee", "Texas", 17))
    pending = game("Bowl", "", "2026-BOWL-SunBowl", "Sun Bowl", "Texas", "Utah", 16)
    for r in pending:
        r["Status"], r["Outcome"] = "Pending", "Pending"
    post = tmp_path / "Postseason_Season.csv"
    pd.DataFrame(rows + pending, columns=cols).to_csv(post, index=False)
    sb = tmp_path / "scoreboard" / "2026"
    sb.mkdir(parents=True)
    sl = T.tn.slot(2026, "Air Force")
    lid = T.league_ids()[("2026", sl[0].strip())]
    (sb / "guillotine.json").write_text(json.dumps({"season": 2026, "name": "The Guillotine", "status": "final", "last_week": 17,
                                                    "champions": [{"l": lid, "r": sl[1], "team": "Air Force"}],
                                                    "teams": [{"l": lid, "r": sl[1], "team": "Air Force", "league": sl[0]}]}))
    (sb / "dwight.json").write_text(json.dumps({"season": 2026, "last_week": 17, "champion": {
        "team": "Air Force", "league": sl[0], "league_id": lid, "roster_id": sl[1], "user_id": "42", "username": "dwight42"}}))
    return post, tmp_path / "scoreboard"


@pytest.fixture
def season_env(tmp_path, monkeypatch):
    post, sb = season_fixture(tmp_path)
    monkeypatch.setattr(T, "POST_SEASON", str(post))
    monkeypatch.setattr(T, "SCOREBOARD", str(sb))
    monkeypatch.setattr(T, "historic_seasons", lambda: set())
    # default args were bound at import: route through the patched globals
    monkeypatch.setattr(T, "build_season", lambda year: T.frame(T.from_postseason_season(year, str(post))
                                                                + T.from_special_events(year, str(sb))))
    return tmp_path / "Trophies_Season.csv"


def test_season_build_only_final_results(season_env):
    df = T.build_season(2026)
    got = sorted(zip(df["EventType"], df["Event"], df["Round"], df["Team"]))
    assert got == sorted([("CCG", "Big Sky Championship", "", "Montana State"), ("Bowl", "Gator Bowl", "", "Clemson"),
                          ("PlayoffRound", "Orange Bowl", "Final Four", "Arizona State"),
                          ("NationalTitle", "National Championship", "", "Arizona State"), ("NIT", "NIT", "", "Tuskegee"),
                          ("Guillotine", "The Guillotine", "", "Air Force"), ("DwightFight", "Dwight Fight", "", "Air Force")])
    dw = df[df["EventType"] == "DwightFight"].iloc[0]
    assert (dw["ManagerUserID"], dw["ManagerName"]) == ("42", "dwight42")


def test_rebuilding_the_season_file_twice_is_identical(season_env):
    assert T.update_season(2026, path=str(season_env)) == 0
    a = season_env.read_bytes()
    assert T.update_season(2026, path=str(season_env)) == 0
    assert season_env.read_bytes() == a


def test_weekly_run_never_touches_historic(season_env):
    before = hashlib.sha256((ROOT / T.HIST).read_bytes()).hexdigest()
    T.update_season(2026, path=str(season_env))
    assert hashlib.sha256((ROOT / T.HIST).read_bytes()).hexdigest() == before
    wf = (ROOT / ".github/workflows/update-leagues.yml").read_text()
    calls = re.findall(r"trophies\.py[^\n]*", wf)
    assert calls and all("--backfill" not in c and "--rollover" not in c for c in calls)


def test_safety_check_trips_on_changed_or_dropped_rows(season_env, capsys):
    assert T.update_season(2026, path=str(season_env)) == 0
    good = season_env.read_bytes()
    df = pd.read_csv(season_env, dtype=str, keep_default_na=False)
    changed = df.copy()
    changed.loc[changed["EventType"] == "Bowl", ["Team", "RosterID"]] = ["Somebody Else", "99"]
    changed.to_csv(season_env, index=False)
    bad = season_env.read_bytes()
    assert T.update_season(2026, path=str(season_env)) == 1
    assert season_env.read_bytes() == bad  # old file kept
    assert "CHANGED" in capsys.readouterr().out
    extra = pd.concat([df, df[df["EventType"] == "NIT"].assign(Event="Phantom Bowl", EventType="Bowl")])
    extra.to_csv(season_env, index=False)
    assert T.update_season(2026, path=str(season_env)) == 1
    assert "DROPPED" in capsys.readouterr().out
    assert T.update_season(2026, allow_changes=True, path=str(season_env)) == 0
    assert season_env.read_bytes() == good
    # additions always pass
    df[df["EventType"] != "NIT"].to_csv(season_env, index=False)
    assert T.update_season(2026, path=str(season_env)) == 0


# ------------------------------------------------------------------ config + art
def test_config_maps_every_event_type_to_existing_art():
    c = T.cfg()
    lg = json.load(open(ROOT / "config/league.json"))["postseason"]
    shorts = pd.read_csv(ROOT / "data/LeagueShortNames.csv", encoding="utf-8-sig")["Short Name"].str.strip()
    current = {T.short_names().get(n.strip(), n.strip()) for n in pd.read_csv(ROOT / "data/LeagueIDs_AllYears.csv", dtype=str)
               .query("Year == @T.current_season().__str__()")["LeagueName"]}
    assert current <= set(shorts)
    samples = [{"EventType": "CCG", "Conference": s} for s in current]
    samples += [{"EventType": "Bowl", "Event": b["name"]} for t in lg["bowls"]["tiers"] for b in t["bowls"]]
    samples += [{"EventType": "PlayoffRound", "Event": b, "Round": r} for pair in lg["playoff"]["bowl_rotation"] for b in pair
                for r in c["events"]["PlayoffRound"]["rounds"]]
    samples += [{"EventType": k} for k in ("NationalTitle", "NIT", "Guillotine", "DwightFight")]
    assert {s["EventType"] for s in samples} == {k for k in c["events"] if not k.startswith("_")}
    missing = [(s, T.art_key(s)) for s in samples if not os.path.exists(T.art_key(s))]
    assert missing == []


def test_every_key_has_a_note():
    def walk(d, path):
        if isinstance(d, dict):
            obj_keys = [k for k, v in d.items() if isinstance(v, dict) and not k.startswith("_")]
            if path in ("", "plaque", "overrides", "events", "bowl_art", "bowl_labels", "display") or path.startswith("events."):
                assert "_note" in d, path
            for k in obj_keys:
                walk(d[k], f"{path}.{k}".strip("."))
    walk(json.load(open(ROOT / T.CONFIG)), "")


def test_plaque_geometry_matches_every_1200_art_file():
    g = T.cfg()["plaque"]
    files = glob.glob(str(ROOT / "assets/trophies/**/*.png"), recursive=True)
    assert len(files) >= 61
    for f in files:
        im = Image.open(f).convert("RGBA")
        assert im.size == (g["size"], g["size"]), f
        box = im.crop((g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"]))
        assert [c for _, c in box.getcolors()] == [PLAQUE_GREY], f
        # and the box is the whole plaque: the pixel just outside each edge is not plaque grey
        for p in ((g["x"] - 1, g["y"] + 80), (g["x"] + g["w"], g["y"] + 80), (g["x"] + 320, g["y"] - 1), (g["x"] + 320, g["y"] + g["h"])):
            assert im.getpixel(p) != PLAQUE_GREY, (f, p)
    en = T.engraving({"EventType": "NIT"}, "Tuskegee", 2025)
    assert en["box"] == {"left": 23.33, "top": 76.16, "width": 53.33, "height": 13.33}


def test_dwight_fight_override_keeps_its_old_box():
    en = T.engraving({"EventType": "DwightFight"}, "Arizona State", 2025)
    assert (en["box"]["left"], en["box"]["top"], en["color"]) == (24.6, 82.5, "#4a260d")
    assert abs(en["box"]["width"] - 50.6) < 0.02 and abs(en["box"]["height"] - 11.1) < 0.02
    assert en["line2"] == "2025 Dwight Fight Champion" and en["upper2"]


# ------------------------------------------------------------------ text + fit
def test_plaque_text_two_lines():
    cases = [({"EventType": "CCG", "Conference": "Big Sky"}, "Montana State", 2026, "2026 Big Sky Champion"),
             ({"EventType": "Bowl", "Event": "Gator Bowl"}, "Clemson", 2026, "2026 Gator Bowl"),
             ({"EventType": "Bowl", "Event": "TaxSlayer Bowl"}, "Clemson", 2019, "2019 Gator Bowl"),  # no sponsors
             ({"EventType": "PlayoffRound", "Event": "Rose Bowl", "Round": "Final Four"}, "Arizona State", 2026, "2026 Rose Bowl · Final Four"),
             ({"EventType": "NationalTitle"}, "Arizona State", 2026, "2026 National Champion"),
             ({"EventType": "NIT"}, "Tuskegee", 2026, "2026 NIT Champion")]
    for ev, team, year, l2 in cases:
        en = T.engraving(ev, team, year)
        assert (en["line1"], en["line2"]) == (team, l2)
    en = T.engraving({"EventType": "CCG", "Conference": "Big Sky"}, "Montana State", 2026)
    assert en["alt"] == "2026 Big Sky Championship trophy, won by Montana State"
    assert T.engraving({"EventType": "Bowl", "Event": "Brooklyn Bowl"}, "X", 2019)["art"] == "assets/trophies/bowls/Gotham Bowl.png"


def longest():
    names = set(pd.read_csv(ROOT / "data/TeamNames_Historic.csv", dtype=str)["Team"]) | set(
        pd.read_csv(ROOT / "data/Teams.csv", dtype=str, encoding="utf-8-sig")["Team"])
    team = max(names, key=lambda n: T.text_em(n, "700"))
    rows = T.ledger().to_dict("records")
    label = max((T.engraving(r) for r in rows), key=lambda en: T.text_em(en["line2"].upper(), "400"))
    return team, label


def test_autofit_never_overflows_longest_real_names():
    team, worst = longest()
    fonts = {w: ImageFont.truetype(str(ROOT / f), 1000) for w, f in T.FONTS.items()}
    for row in T.ledger().drop_duplicates("ArtKey").to_dict("records"):  # every plaque geometry in use
        for fb in (False, True):
            en = T.engraving({**row, "Team": team}, line2=worst["line2"], fallback=fb)
            g = T.geometry(en["art"])
            avail = en["box"]["width"] * (1 - 2 * g["padding"])
            for text, size, w in ((en["line1"], en["size1"], "700"), (en["line2"].upper() if en["upper2"] else en["line2"], en["size2"], "400")):
                real = (fonts[w].getlength(text) / 1000 + T.LETTER_SPACING * len(text)) * size  # kerned, as drawn
                assert real <= avail + 1e-9, (text, en["art"])
                assert size > 0
            assert (en["size1"] + en["size2"]) * T.LINE_HEIGHT <= en["box"]["height"]


def test_engrave_png_in_memory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    row = hist()[lambda d: (d["Season"] == "2025") & (d["EventType"] == "NationalTitle")].iloc[0].to_dict()
    im = T.engrave_png(row)
    assert isinstance(im, Image.Image) and im.size == (1200, 1200)
    g = T.cfg()["plaque"]
    box = im.crop((g["x"], g["y"], g["x"] + g["w"], g["y"] + g["h"])).convert("RGB")
    ink = sum(n for n, p in box.getcolors(box.width * box.height) if sum(p) < 300)
    assert ink > 500  # the two lines are drawn
    assert list(tmp_path.iterdir()) == []  # nothing written
    assert T.engrave_png({**row, "EventType": "Bowl", "Event": "No Such Bowl"}).size == (1200, 1200)  # generic art
    monkeypatch.setattr(T, "resolved_art", lambda r: "")
    assert T.engrave_png({**row, "EventType": "Bowl", "Event": "No Such Bowl"}).size == (1200, 300)  # plain plaque


def test_fallback_when_art_missing(monkeypatch):
    real = T.os.path.exists
    monkeypatch.setattr(T.os.path, "exists", lambda p: False if "National Championship.png" in str(p) and "trophies" in str(p) else real(p))
    # (NationalTitle has no generic stand-in; a Bowl falls back only if its generic is missing too)
    out = T.trophy_html({"EventType": "NationalTitle"}, "Arizona State", 2025)
    assert 'class="trophy fallback' in out and "Arizona State" in out and "2025 National Champion" in out
    assert "assets/logos/Playoffs/National%20Championship.png" in out  # the event's logo
    assert 'aria-label="2025 National Championship trophy, won by Arizona State"' in out


# ------------------------------------------------------------------ Python == JS
BRIDGE = """
const T=require(process.argv[1]),fs=require('fs');
T.init({config:JSON.parse(fs.readFileSync('config/trophies.json')),league:JSON.parse(fs.readFileSync('config/league.json')),
  metrics:JSON.parse(fs.readFileSync('assets/fonts/barlow-trophy-metrics.json'))});
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(rows.map(r=>[T.engraving(r),T.engraving(r,null,null,null,true)])));
"""


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_python_and_js_produce_the_same_text_and_box():
    team, worst = longest()
    rows = T.ledger().to_dict("records")
    rows += [{**rows[0], "Team": team}, {"EventType": "Bowl", "Event": "Capital One Bowl", "Team": "É&’ test", "Season": "2019"},
             {"EventType": "DwightFight", "Team": "Arizona State", "Season": 2026}]
    py = [[T.engraving(r), T.engraving(r, fallback=True)] for r in rows]
    js = json.loads(subprocess.run([NODE, "-e", BRIDGE, str(ROOT / "reports/assets/trophy.js")], input=json.dumps(rows),
                                   text=True, capture_output=True, check=True, cwd=ROOT).stdout)
    assert py == js


def test_metrics_table_matches_the_vendored_fonts(tmp_path, monkeypatch):
    saved = (ROOT / T.METRICS).read_bytes()
    try:
        T.build_metrics()
        assert json.loads((ROOT / T.METRICS).read_text()) == json.loads(saved)
    finally:
        (ROOT / T.METRICS).write_bytes(saved)
        T._cache.pop("m", None)


# ------------------------------------------------------------------ pages
@pytest.mark.parametrize("year", sorted(EXPECTED))
def test_postseason_page_shows_each_postseason_trophy(year):
    doc = pp.build_season(int(year), [])
    L = hist()[lambda d: (d["Season"] == year) & d["EventType"].isin(["CCG", "Bowl", "PlayoffRound", "NIT", "NationalTitle"])]
    for r in L.to_dict("records"):
        alt = T.html.escape(T.engraving(r)["alt"])
        assert alt in doc, alt
    assert "Trophies_" not in doc  # rendered server-side, no CSV fetch


def test_no_per_trophy_image_files():
    imgs = glob.glob(str(ROOT / "assets/trophies/**/*.png"), recursive=True) + glob.glob(str(ROOT / "reports/**/*.png"), recursive=True)
    teams = {t for t in hist()["Team"]}
    # trophy art + generated images: nothing named after a winner or a season's trophy
    per = [p for p in imgs if Path(p).stem in teams or re.search(r"(19|20)\d\d.*(champ|trophy|bowl)", Path(p).stem, re.I)]
    assert per == [] and len(glob.glob(str(ROOT / "assets/trophies/**/*.png"), recursive=True)) == 63  # 61 + 2 generic placeholders
