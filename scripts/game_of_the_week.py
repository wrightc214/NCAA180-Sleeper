"""
game_of_the_week.py -- pick the Game of the Week (Chris, 2026-11-04).

Every game of the week is scored:
  quality    the WORSE team's poll rank (so 1 v 90 doesn't score as a #1 game)
  closeness  pregame win odds near 50/50 + ranks close together (5 v 6 beats 1 v 9)
  stakes     a division-lead game between winning teams, or a team within bubble_width spots of
             the projected at-large cut line (bowl projection), or a top-seed race (both top 10);
             grows through the season
  rivalry    small bonus (data/rivalries, certainty 4+), only between good teams
  score = .55 * quality*(.5+.5*closeness) + .30 * stakes*gate + .15 * rivalry*gate
Premier rule (Chris): if any game has BOTH teams in the poll's top premier_max_rank (15), the pick
comes from those games -- skipping a top matchup would cost the feature its credibility.
A manual pick in data/scoreboard/<season>/game-of-the-week.json (a two-name list) always wins.

Writes the pick (+ a one-line reason anyone can check) into that file as
  "<week>": {"teams": [a, b], "reason": "...", "source": "auto"}
  python scripts/game_of_the_week.py [--year Y] [--week W] [--dry-run]
Settings: config/league.json -> game_of_the_week.
"""
import argparse
import json
import math
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import league_config as lcfg  # noqa: E402

DEFAULTS = {"weights": {"quality": 0.55, "stakes": 0.30, "rivalry": 0.15}, "premier_max_rank": 15,
            "quality_scale": 25, "rank_gap_scale": 12, "top_race_rank": 10, "bubble_width": 6}


def settings():
    c = dict(DEFAULTS)
    c.update(lcfg.cfg().get("game_of_the_week", {}))
    return c


def gotw_file(year):
    return os.path.join("data/scoreboard", str(year), "game-of-the-week.json")


def ranks(year, week):
    """Poll rank going into `week`: BotConsensus through week-1 (week 1: the preseason prior)."""
    if week <= 1:
        p = pd.read_csv("data/PollPrior_Season.csv", dtype=str)
        p = p[p["Year"] == str(year)].assign(s=lambda d: pd.to_numeric(d["Prior"])).sort_values("s", ascending=False)
        return {(str(r.LeagueID), str(r.RosterID)): i + 1 for i, r in enumerate(p.itertuples())}
    p = pd.read_csv("data/Poll_Season.csv", dtype=str)
    p = p[(p["Year"] == str(year)) & (p["PollType"] == "BotConsensus")]
    tw = pd.to_numeric(p["ThroughWeek"])
    p = p[tw == tw[tw <= week - 1].max()]  # latest poll on or before week-1
    return {(str(r.LeagueID), str(r.RosterID)): int(float(r.Rank)) for r in p.itertuples()}


def odds(year, week):
    f = os.path.join("data/scoreboard", str(year), f"week-{week:02d}.json")
    if not os.path.exists(f):
        return {}
    return {frozenset((str(o["LeagueID"]) + "|" + str(o["RosterID"]), str(o["LeagueID"]) + "|" + str(o["OpponentRosterID"]))):
            (str(o["RosterID"]), float(o["WinPct"])) for o in json.load(open(f))["odds"] if o.get("WinPct") not in (None, "")}


def rivalries():
    r = pd.read_csv("data/rivalries/football.csv", dtype=str)
    return {frozenset((a, b)) for a, b, c in zip(r["team_a"], r["team_b"], r["certainty"]) if str(c).isdigit() and int(c) >= 4}


def score_week(year, week, bubble=None, R=None, O=None):
    """[(score, info dict)] best first. bubble: {(LeagueID, RosterID): position vs the cut line}."""
    cfg = settings()
    W = cfg["weights"]
    R = R if R is not None else ranks(year, week)
    O = O if O is not None else odds(year, week)
    riv = rivalries()
    m = ps._matchups(year)
    reg = m[(m["Week"] < week) & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    rec = {}
    for r in reg.itertuples():
        k = (str(r.LeagueID), str(r.RosterID))
        w, l = rec.get(k, (0, 0))
        rec[k] = (w + (r.Outcome == "Win"), l + (r.Outcome == "Loss"))
    teams = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
    lid = dict(zip(m["LeagueName"].str.strip(), m["LeagueID"].astype(str)))
    name = {(lid.get(r["League"].strip(), ""), str(r["Roster ID"])): r["Team"] for _, r in teams.iterrows()}
    div = {(lid.get(r["League"].strip(), ""), str(r["Roster ID"])): str(r["Division Name"]).strip() for _, r in teams.iterrows()}
    # games behind the division leader (wins minus losses), before this week
    lead = {}
    for k, d in div.items():
        w, l = rec.get(k, (0, 0))
        lead[(k[0], d)] = max(lead.get((k[0], d), -99), w - l)
    short = {v: k for k, v in ps.league_short().items()}
    late = min(1.0, max(0.0, (week - 3) / 8))
    wk = m[m["Week"] == week]
    out, seen = [], set()
    for r in wk.itertuples():
        if pd.isna(r.OpponentRosterID) or str(r.OpponentRosterID) in ("", "nan", "<NA>"):
            continue
        a = (str(r.LeagueID), str(r.RosterID))
        b = (str(r.LeagueID), str(r.OpponentRosterID).replace(".0", ""))
        if frozenset((a, b)) in seen:
            continue
        seen.add(frozenset((a, b)))
        na, nb = name.get(a, "?"), name.get(b, "?")
        ra, rb = R.get(a, 999), R.get(b, 999)
        worse = max(ra, rb)
        q = math.exp(-(worse - 1) / cfg["quality_scale"])
        gap = math.exp(-abs(ra - rb) / cfg["rank_gap_scale"])
        od = O.get(frozenset((f"{a[0]}|{a[1]}", f"{b[0]}|{b[1]}")))
        pa = (od[1] if od[0] == a[1] else 100 - od[1]) if od else None
        c = 0.6 * (1 - abs(pa - 50) / 50) + 0.4 * gap if pa is not None else gap
        wa, wb = rec.get(a, (0, 0)), rec.get(b, (0, 0))
        winning = wa[0] > wa[1] and wb[0] > wb[1]
        stakes, why = 0.0, []
        if week >= 4 and winning and div.get(a) == div.get(b) and all(
                (lead[(k[0], div[k])] - (rec.get(k, (0, 0))[0] - rec.get(k, (0, 0))[1])) <= 2 for k in (a, b)):
            stakes = max(stakes, 1.0)
            why.append(f"{short.get(r.LeagueName.strip(), r.LeagueName.strip())} {div[a].title()} lead on the line")
        if ra <= cfg["top_race_rank"] and rb <= cfg["top_race_rank"]:
            stakes = max(stakes, 0.8)
            why.append("top-seed race")
        # bubble: closest-to-the-cut team in this game (0 = last team in, 1 = first team out)
        bt = [(abs(bubble[k] - 0.5), bubble[k], n) for k, n in ((a, na), (b, nb))
              if bubble and k in bubble and rec.get(k, (0, 0))[0] > rec.get(k, (0, 0))[1]]
        if bt:
            d, p_, n = min(bt)
            stakes = max(stakes, 0.9 * (1 - (d - 0.5) / cfg["bubble_width"]))
            pos = 1 - p_ if p_ <= 0 else p_
            nth = {1: "", 2: "2nd", 3: "3rd"}.get(pos, f"{pos}th")
            why.append(f"{n}: projected {nth + '-to-' if nth else ''}last team in the playoff" if p_ <= 0
                       else f"{n}: projected {nth or 'first'} team out of the playoff")
        stakes *= late
        rv = 1.0 if frozenset((na, nb)) in riv else 0.0
        if rv:
            why.append("rivalry")
        gate = min(1.0, 0.25 + 2 * q)
        score = W["quality"] * q * (0.5 + 0.5 * c) + W["stakes"] * stakes * gate + W["rivalry"] * rv * min(1.0, 2 * q)
        premier = ra <= cfg["premier_max_rank"] and rb <= cfg["premier_max_rank"]
        rk = lambda x: f"#{x} " if x <= 25 else ""  # noqa: E731  (poll shows a Top 25)
        head = f"{rk(ra)}{na} ({wa[0]}-{wa[1]}) vs {rk(rb)}{nb} ({wb[0]}-{wb[1]})"
        odds_txt = f"{pa:.0f}% / {100 - pa:.0f}%" if pa is not None else ""
        reason = " · ".join(x for x in [odds_txt] + why if x)
        out.append((score, dict(teams=[na, nb], keys=[list(a), list(b)], premier=premier, ranks=[ra, rb],
                                headline=head, reason=reason, league=short.get(r.LeagueName.strip(), r.LeagueName.strip()))))
    out.sort(key=lambda x: -x[0])
    prem = [x for x in out if x[1]["premier"]]
    if prem:  # premier rule: a both-top-15 game is always the pick
        out = prem + [x for x in out if not x[1]["premier"]]
    return out


def projection_bubble(week):
    """Bubble band saved by bowl_projection.py when its projection is current (after week-1)."""
    meta = "reports/postseason/meta.json"
    if not os.path.exists(meta):
        return {}
    m = json.load(open(meta))
    if int(m.get("after_week", -1)) != week - 1:
        return {}
    return {(str(l), str(r)): int(p) for l, r, p in m.get("bubble", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--week", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    year = a.year or ps.current_season()
    week = a.week or (max(ps.completed_weeks(year), default=0) + 1)
    if week > ps.last_regular_week():
        print(f"Game of the Week: week {week} is postseason (CCG week uses the championship games); skipped")
        return
    path = gotw_file(year)
    picks = json.load(open(path)) if os.path.exists(path) else {}
    if isinstance(picks.get(str(week)), list):
        print(f"Game of the Week {year} wk {week}: manual pick kept ({' vs '.join(picks[str(week)])})")
        return
    ranked = score_week(year, week, projection_bubble(week))
    if not ranked:
        print(f"Game of the Week {year} wk {week}: no games")
        return
    best = ranked[0][1]
    print(f"Game of the Week {year} wk {week}: {best['headline']} -- {best['reason']}")
    for s, g in ranked[1:4]:
        print(f"  next: {s:.3f} {g['headline']} -- {g['reason']}")
    if not a.dry_run:
        picks[str(week)] = {"teams": best["teams"], "reason": best["reason"], "source": "auto"}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(picks, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
