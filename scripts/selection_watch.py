"""
selection_watch.py -- data for the Selection Watch page during CCG week (Chris, 2026-11-12).

Once the regular season is final the at-large order is fixed and only the 15 conference
championship games (CCGs) are left. This writes everything the page needs to work the playoff
field out live in the browser:
  order   every team, best first (full names; 'short' only when an approved Teams.csv ShortName
          exists -- the page falls back to it when space is tight), by the shared tiebreakers in REAL-TOSS mode (win % -> points
          for -> points against; a tie still standing stays tied unless a real coin toss has been
          recorded in config tiebreakers.coin_toss_results -- no hidden toss for the cut)
  ccg     the 15 CCG pairings (+ result when final)
  tie     groups of teams still exactly tied (only matter if they straddle the cut)
Field rule: the CCG winners (auto bids) + the top (field_size - #CCGs) of everyone else.

Steal Board (Chris's view): a THIEF is a CCG team that can only get in by winning = every CCG
team outside the natural top field_size. With k thieves winning, exactly the bottom k at-large
teams of the natural field are out. board() builds it; field() and odds() are the exact rule and
the full 2^15 enumeration -- the reference the page's JavaScript is tested against.

  python scripts/selection_watch.py [--year Y] [--check]   (--check: past season, compare to the
                                                            actual playoff field; writes nothing)
Writes reports/postseason/selection-watch.json (current season, once weeks 1..last regular are final).
"""
import argparse
import datetime as dt
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import league_config as lcfg  # noqa: E402
import team_names as tn  # noqa: E402

OUT = "reports/postseason/selection-watch.json"
HIST = "data/Postseason_Historic.csv"


def key(lid, rid):
    return f"{lid}|{rid}"


def ccg_pairs(year, st):
    """[(GameID, keyA, keyB, winnerKey or '', scoreA, scoreB)]: this season's file, else history."""
    by_name = {t: key(l, r) for t, l, r in zip(st["Team"], st["LeagueID"], st["RosterID"])}
    season = ps.read_season()
    s = season[(season["Year"].astype(str) == str(year)) & (season["Round"] == "CCG")]
    out = []
    if len(s):
        for gid, g in s.groupby("GameID", sort=True):
            g = g.to_dict("records")
            if len(g) != 2:
                continue
            a, b = g
            win = next((key(r["LeagueID"], r["RosterID"]) for r in g if r["Status"] == "Final" and r["Outcome"] == "Win"), "")
            pts = lambda r: float(r["Points"]) if str(r.get("Points", "")).strip() not in ("", "nan") else None  # noqa: E731
            out.append((gid, key(a["LeagueID"], a["RosterID"]), key(b["LeagueID"], b["RosterID"]), win, pts(a), pts(b)))
        return out
    if os.path.exists(HIST):
        h = pd.read_csv(HIST, dtype=str)
        h = h[(h["Season"] == str(year)) & (h["Event"] == "CCG")]
        for i, r in enumerate(h.itertuples()):
            a, b = by_name[r.TeamA.strip()], by_name[r.TeamB.strip()]
            w = by_name.get(str(r.Winner).strip(), "")
            out.append((f"{year}-CCG-{i}", a, b, w, float(r.ScoreA), float(r.ScoreB)))
    return out


def build(year):
    st = ps.standings(year)
    order, tied, _ = ps.rank_ties(st, real_toss=True)
    lg = {v.strip(): k for k, v in ps.league_short().items()}  # league name -> short name
    teams = []
    for i, r in enumerate(order.itertuples()):
        teams.append({"k": key(r.LeagueID, r.RosterID), "team": r.Team, "short": tn.short_name(r.Team),
                      "conf": lg.get(r.LeagueName.strip(), r.LeagueName), "div": r.Division or "",
                      "w": int(r.Wins), "l": int(r.Losses), "t": int(r.Ties), "pf": float(r.PointsFor),
                      "pa": float(r.PointsAgainst), "rank": i + 1})
    name_key = {t["team"]: t["k"] for t in teams}
    ties = [[name_key[n] for n in g] for g in tied]
    pc = ps.cfg_postseason()["playoff"]
    games = [{"id": g, "a": a, "b": b, "winner": w, "pa": sa, "pb": sb} for g, a, b, w, sa, sb in ccg_pairs(year, order)]
    return {"year": int(year), "field_size": int(pc["field_size"]), "ccg_week": ps.ccg_week(),
            "order": teams, "ccg": games, "tie": ties,
            "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "note": "Unofficial. Field = CCG winners + top (field_size - #CCGs) of everyone else, by win %, "
                    "points for, points against; a tie that decides the last spot goes to a real coin toss."}


# ---------- the rule, the board and the odds (reference for the page) ----------

def _tie_of(d):
    return {k: i for i, g in enumerate(d["tie"]) for k in g}


def field(d, winners):
    """{key: share in the field} for one set of CCG winners. 1 = in; a tie group straddling the
    cut splits its remaining spots evenly (a real coin toss decides it)."""
    win = set(winners)
    n_at = d["field_size"] - len(d["ccg"])
    tie = _tie_of(d)
    res = {k: 1.0 for k in win}
    left, i, order = n_at, 0, [t["k"] for t in d["order"] if t["k"] not in win]
    while left > 0 and i < len(order):
        g = [order[i]]
        if order[i] in tie:  # whole tie group (consecutive in the order)
            while i + len(g) < len(order) and tie.get(order[i + len(g)]) == tie[order[i]]:
                g.append(order[i + len(g)])
        share = min(1.0, left / len(g))
        for k in g:
            res[k] = share
        left -= min(left, len(g))
        i += len(g)
    return res


def board(d, leaders):
    """Steal Board for one moment. leaders: {game id: key currently ahead / winner}.
    Returns (thief rows sorted by the caller's order, at-risk list (first out first), k)."""
    nat = {t["k"]: t["rank"] for t in d["order"]}
    N = d["field_size"]
    thieves, protected = [], set()
    for g in d["ccg"]:
        a_out, b_out = nat[g["a"]] > N, nat[g["b"]] > N
        lead = leaders.get(g["id"])
        if a_out and b_out:  # one steal certain: one row, whoever leads
            thieves.append({"game": g["id"], "team": lead or g["a"], "both_out": True, "leading": True})
        elif a_out or b_out:
            th = g["a"] if a_out else g["b"]
            thieves.append({"game": g["id"], "team": th, "both_out": False, "leading": lead == th})
        if lead and nat[lead] <= N:
            protected.add(lead)
    k = sum(t["leading"] for t in thieves)
    inside = [t["k"] for t in d["order"][:N] if t["k"] not in protected]
    at_risk = list(reversed(inside))[:len(thieves)]  # first out first
    return thieves, at_risk, k


def odds(d, p):
    """Exact chance of making the field for every team: all 2^n CCG outcome sets.
    p: {game id: chance team a wins} (final games: 1 or 0). Returns {key: chance}."""
    games = d["ccg"]
    chance = {}
    for bits in itertools.product((0, 1), repeat=len(games)):
        w, pr = [], 1.0
        for g, b in zip(games, bits):
            q = p.get(g["id"], 0.5)
            pr *= q if b else 1 - q
            w.append(g["a"] if b else g["b"])
        if pr == 0:
            continue
        for k, s in field(d, w).items():
            chance[k] = chance.get(k, 0.0) + pr * s
    return chance


# ---------- coin-toss alert (Chris, 2026-11-13) ----------
# After the regular season, any tie that could go to a REAL coin toss is reported to the league
# manager feed (lm-private-data): a division title tied after every tiebreaker (decided now), or an
# exact tie that would straddle the last playoff spot in at least one set of CCG results.
TOSS_STATE = "data/CoinTossAlert.json"  # last alert sent (so each situation is posted once)


def toss_risks(year, d):
    """[(kind, teams, detail)] for every possible real coin toss this season."""
    return division_toss_risks(year) + playoff_toss_risks(d)


def division_toss_risks(year):
    out = []
    st = ps.standings(year)
    for (lname, div), grp in st.groupby(["LeagueName", "Division"]):
        r, ties, _ = ps.rank_ties(grp, real_toss=True)
        top = next((t for t in ties if r.iloc[0]["Team"] in t), None)
        if top:
            out.append(("Division title", top, f"{lname.strip()} / {div}: tied for the division title"))
    return out


def playoff_toss_risks(d):
    """Exact ties that straddle the last playoff spot in at least one set of CCG results."""
    out = []
    if d["tie"] and d["ccg"]:
        tm = {t["k"]: t for t in d["order"]}
        for g in d["tie"]:
            hit, n = 0, 0
            for bits in itertools.product((0, 1), repeat=len(d["ccg"])):
                f = field(d, [c["a"] if b else c["b"] for c, b in zip(d["ccg"], bits)])
                n += 1
                hit += any(0 < f.get(k, 0) < 1 for k in g)
            if hit:
                names = [tm[k]["team"] for k in g]
                t0 = tm[g[0]]
                out.append(("Last playoff spot", names,
                            f"tied at {t0['w']}-{t0['l']}{'-' + str(t0['t']) if t0['t'] else ''}, {t0['pf']:.2f} PF, "
                            f"{t0['pa']:.2f} PA (#{t0['rank']}); decides the last spot in {hit:,} of {n:,} CCG outcome sets"))
    return out


def toss_alert(year, risks):
    """Post the coin-toss alert to lm-private-data once per situation (needs the webhook secret)."""
    text = ""
    if risks:
        lines = [f"🪙 **Possible real coin toss — {year}** (regular season final)"]
        for kind, teams, detail in risks:
            lines.append(f"• **{kind}:** {' vs '.join(teams)} — {detail}")
        lines.append("No hidden toss: if it decides the outcome, hold a real toss with both managers present and "
                     "record it in config/league.json → tiebreakers.coin_toss_results "
                     '({"year", "teams", "order": [winner, loser]}).')
        text = "\n".join(lines)
    old = json.load(open(TOSS_STATE)).get(str(year), "") if os.path.exists(TOSS_STATE) else ""
    if not text or text == old:
        return text
    print(text)
    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    if not hook:
        print("Coin-toss alert NOT posted: DISCORD_WEBHOOK_LM_PRIVATE_DATA not set")
        return text
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    import requests
    r = requests.post(hook, json={"content": text + (f" <@{contact}>" if contact else ""),
                                  "allowed_mentions": {"users": [contact] if contact else []}}, timeout=30)
    if r.status_code >= 300:
        print(f"Coin-toss alert post failed: HTTP {r.status_code}")
        return text
    state = json.load(open(TOSS_STATE)) if os.path.exists(TOSS_STATE) else {}
    state[str(year)] = text
    json.dump(state, open(TOSS_STATE, "w"), indent=1)
    return text


def check(year):
    """Past season: rebuild the board from the real CCG results and compare to the real field."""
    d = build(year)
    winners = [g["winner"] for g in d["ccg"]]
    f = {k for k, s in field(d, winners).items() if s == 1}
    h = pd.read_csv(HIST, dtype=str)
    po = h[(h["Season"] == str(year)) & (h["Event"] == "Playoff") & (h["RoundName"] == "First Round")]
    name = {t["team"]: t["k"] for t in d["order"]}
    actual = {name[t.strip()] for c in ("TeamA", "TeamB") for t in po[c]}
    leaders = {g["id"]: g["winner"] for g in d["ccg"]}
    margin = {g["id"]: abs((g["pa"] or 0) - (g["pb"] or 0)) * (1 if g["winner"] else 0) for g in d["ccg"]}
    thieves, at_risk, k = board(d, leaders)
    thieves.sort(key=lambda t: (not t["leading"], -margin[t["game"]] if t["leading"] else margin[t["game"]]))
    tm = {t["k"]: t for t in d["order"]}
    print(f"{year}: field by rule {len(f)} / actual {len(actual)} -- {'MATCH' if f == actual else 'DIFFERENT'}")
    for i, t in enumerate(thieves):
        if i == k:
            print("  " + "-" * 30 + " cut " + "-" * 30)
        ar = tm[at_risk[i]] if i < len(at_risk) else None
        th = tm[t["team"]]
        print(f"  {'IN ' if t['leading'] else 'out'} {(th['short'] or th['team']):<18} #{th['rank']:<3} | "
              f"{((ar['short'] or ar['team']) + ' #' + str(ar['rank'])) if ar else '':<22} {'out' if t['leading'] else 'IN'}")
    return f == actual, d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    year = a.year or ps.current_season()
    if a.check:
        ok, _ = check(year)
        sys.exit(0 if ok else 1)
    missing = sorted(set(range(1, ps.last_regular_week() + 1)) - set(ps.completed_weeks(year)))
    if missing:
        print(f"Selection Watch {year}: regular season not finished (weeks {missing[0]}-{missing[-1]} to go); nothing written")
        return
    d = build(year)
    toss_alert(year, toss_risks(year, d))  # before the CCG check: a division-title tie blocks pairing
    if len(d["ccg"]) == 0:
        print(f"Selection Watch {year}: no CCG pairings yet (conference_championships.py); nothing written")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if {k: v for k, v in old.items() if k != "generated"} == {k: v for k, v in d.items() if k != "generated"}:
        print(f"Selection Watch {year}: unchanged")
        return
    json.dump(d, open(OUT, "w"), indent=1)
    print(f"Selection Watch {year}: {len(d['order'])} teams, {len(d['ccg'])} CCGs, {len(d['tie'])} exact tie group(s) -> {OUT}")


if __name__ == "__main__":
    main()
