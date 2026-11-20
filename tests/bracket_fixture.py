"""Bracket fixtures (task 5.13): the 2025 Playoff as played, and mid-tournament states cut from it.
Not a test module; imported by test_bracket.py and test_bracket_browser.py."""
import copy
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def playoff_2025(state="final", ids=False):
    """2025 Playoff games (postseason_page.history_games). state:
    'final'    as played
    's16-live' First Round final; Sweet 16 in progress (points, not final); later rounds not drawn
    'e8-live'  through the Sweet 16 final; Elite 8 drawn with two games live and two not started
    ids=True gives every game a Scoreboard GameID (like a current-season game)."""
    os.chdir(ROOT)
    import postseason_page as pp
    po = [g for g in pp.history_games(2025) if g["event"] == "Playoff"]
    po = copy.deepcopy(po)
    if ids:
        for n, g in enumerate(po):
            g["id"] = f"2025-P-{n + 1}"
    if state == "s16-live":
        po = [g for g in po if g["round"] <= 2]
        for g in po:
            if g["round"] == 2:
                g["final"] = False
                for t in g["teams"]:
                    t["Win"] = False
                    t["Points"] = round((t["Points"] or 0) * 0.6, 2)
    elif state == "e8-live":
        po = [g for g in po if g["round"] <= 3]
        for k, g in enumerate([g for g in po if g["round"] == 3]):
            g["final"] = False
            for t in g["teams"]:
                t["Win"] = False
                t["Points"] = round(t["Points"] * 0.5, 2) if k < 2 else None
    return po


def bracket(state="final", ids=False, year=2025):
    """Mid-tournament states act as the current season (quads named from the bowl rotation)."""
    import _postseason_common as ps
    import postseason_page as pp
    from poll_page import colors
    short = {v: k for k, v in ps.league_short().items()}
    return pp.bracket_html(playoff_2025(state, ids), colors(), year, short, current=state != "final")


def write_page(state="final", ids=True, name=None):
    """A Postseason-like page holding only the fixture bracket, in reports/ (so asset paths work).
    Returns the file name; the caller deletes it."""
    import bowl_projection as bp
    import league_config as lcfg
    import postseason_page as pp
    from site_common import page_head
    name = name or f"_bracket-fixture-{state}.html"
    body = pp.section("Bracket", "", bracket(state, ids), "bracket")
    doc = (page_head("bracket fixture", pp.CSS) + f'<div class="wrap"><header><h1>{lcfg.brand()} <em>2025 Postseason</em></h1></header>'
           + body + bp.FOLD_JS + bp.snap_js(0, foot="fixture", tag="2025", projection=False) + "</div></body></html>")
    with open(os.path.join(ROOT, "reports", name), "w", encoding="utf-8") as f:
        f.write(doc)
    return name
