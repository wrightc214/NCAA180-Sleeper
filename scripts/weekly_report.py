"""
weekly_report.py -- NCAA 180-wide weekly report pages for GitHub Pages.

Writes (repo root is the Pages site):
  reports/week-NN.html   one page per completed regular-season week (all rebuilt each run,
                         so late stat corrections flow through)
  reports/index.html     copy of the latest week
  reports/data/week-NN.json  the numbers behind each page (small; easy to inspect)

Template: templates/weekly_report.html ({{PLACEHOLDER}} substitution, no extra libraries).

Sections: header KPIs, 7 awards (owner shown), Playoff Rank top 32 (wins then points,
ties = 0.5 win, movement vs prior week), top 10 scores, conference average, top starter
per position.

Awards: High Score, Biggest Blowout, Closest Game, Bad Beat (highest score in a loss),
Lucky Win (lowest score in a win), Low Score, You Beat Yourself (losers only whose best
lineup beat the opponent's actual score; biggest MaxPoints - PointsFor; needs
data/MaxPoints_Season.csv, skipped with a warning if missing).

Logos: award cards use assets/logos/teams/<Team>.png when it exists, else the color bar.
Lists always use color bars (logos are unreadable at that size).

Weeks 12+ are skipped: Sleeper's postseason matchups are fictional.
CWD must be repo root. Run after matchups, scores, max_points.
"""
import html
import json
import os
from urllib.parse import quote
import sys
from datetime import datetime, timezone

import math

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import nav_html  # noqa: E402
from poll_common import ranks_for_week  # noqa: E402
from week_status import completed_weeks as finished_weeks  # noqa: E402

MATCHUPS = "data/Matchups_Season.csv"
SCORES = "data/Scores_Season.csv"
MAXPTS = "data/MaxPoints_Season.csv"
TEAMS = "data/Teams.csv"
COLORS = "data/Colors - Teams.csv"
PLAYERS = "data/Players.csv"
TEMPLATE = "templates/weekly_report.html"
OUT_DIR = "reports"
LOGO_DIR = "assets/logos/teams"
LAST_REGULAR_WEEK = 11
LEAGUE_COLORS = "data/Colors - Leagues.csv"
N_LEAGUES = 15
UPSET_FIRST_WEEK = 5  # earlier weeks have too few games for a meaningful pregame estimate
SIM_MIN_GAMES = 3  # below this, a team's own std dev is replaced by the league-wide one

LEAGUE_DISPLAY = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]
e = html.escape


# ---------------------------------------------------------------- data
def load():
    m = pd.read_csv(MATCHUPS, dtype=str)
    m["Week"] = m["Week"].astype(int)
    m["P"] = m["PointsFor"].astype(float)
    m["PA"] = m["PointsAgainst"].astype(float)
    t = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig").rename(
        columns={"League": "LeagueName", "Roster ID": "RosterID"})
    m = m.merge(t[["LeagueName", "RosterID", "Team"]], on=["LeagueName", "RosterID"], how="left")
    opp = m[["LeagueID", "Week", "RosterID", "Team"]].rename(
        columns={"RosterID": "OpponentRosterID", "Team": "OppTeam"})
    m = m.merge(opp, on=["LeagueID", "Week", "OpponentRosterID"], how="left")
    m["Lg"] = m["LeagueName"].map(LEAGUE_DISPLAY).fillna(m["LeagueName"])
    m["Team"] = m["Team"].fillna(m["OwnerName"])
    return m


def completed_weeks(m):
    have = set(m["Week"])
    return [w for w in finished_weeks(m["Year"].iloc[0]) if w <= LAST_REGULAR_WEEK and w in have]


def standings(m, upto):
    r = m[m["Week"] <= upto].copy()
    r["Wv"] = (r["Outcome"] == "Win") * 1.0 + (r["Outcome"] == "Tie") * 0.5
    # Expected wins: share of the other 179 teams outscored each week (ties = half)
    r["ExpW"] = r.groupby("Week")["P"].transform(lambda p: (p.rank(method="average") - 1) / (len(p) - 1))
    s = r.groupby(["LeagueName", "RosterID"], as_index=False).agg(
        Team=("Team", "last"), Lg=("Lg", "last"), Owner=("OwnerName", "last"),
        Wv=("Wv", "sum"), Pts=("P", "sum"), ExpW=("ExpW", "sum"),
        W=("Outcome", lambda x: int((x == "Win").sum())),
        L=("Outcome", lambda x: int((x == "Loss").sum())),
        T=("Outcome", lambda x: int((x == "Tie").sum())))
    s["Luck"] = s["Wv"] - s["ExpW"]
    s["key"] = list(zip(s["Wv"], s["Pts"].round(2)))
    s["Rank"] = s["key"].rank(method="min", ascending=False).astype(int)
    return s.sort_values("Rank")


def game(r):
    return {"Team": r.Team, "Lg": r.Lg, "Owner": r.OwnerName, "P": round(r.P, 2),
            "Opp": r.OppTeam, "PA": round(r.PA, 2), "Margin": round(r.P - r.PA, 2)}


def upset(m, W):
    """Biggest Upset: the winner with the lowest pregame win probability.
    Pregame model (the commissioner's sim): each team's score ~ Normal(mean, sd) of its
    regular-season scores BEFORE week W; P(A beats B) = Phi((muA - muB) / sqrt(sdA^2 + sdB^2)).
    Teams with fewer than SIM_MIN_GAMES prior games use the league-wide sd. None for week 1."""
    if W < UPSET_FIRST_WEEK:
        return None
    prior = m[m["Week"].isin([w for w in finished_weeks(m["Year"].iloc[0]) if w < W])]
    if prior.empty:
        return None
    pooled = prior["P"].std()
    st = prior.groupby(["LeagueID", "RosterID"])["P"].agg(["mean", "std", "count"])
    st["sd"] = st["std"].where(st["count"] >= SIM_MIN_GAMES, pooled)
    w = m[(m["Week"] == W) & (m["Outcome"] == "Win")]
    best = None
    for r in w.itertuples():
        a = st.loc[(r.LeagueID, r.RosterID)] if (r.LeagueID, r.RosterID) in st.index else None
        b = st.loc[(r.LeagueID, r.OpponentRosterID)] if (r.LeagueID, r.OpponentRosterID) in st.index else None
        if a is None or b is None:
            continue
        z = (a["mean"] - b["mean"]) / math.sqrt(a["sd"] ** 2 + b["sd"] ** 2)
        p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
        if best is None or p < best[0]:
            best = (p, r)
    if best is None:
        return None
    p, r = best
    return {**game(r), "WinPct": round(p * 100, 1)}


def week_data(m, sc, mx, pos_map, W):
    w = m[m["Week"] == W].copy()
    d = {"week": W, "avg": round(w["P"].mean(), 2), "median": round(w["P"].median(), 2)}

    s = standings(m, W)
    d["unbeaten"] = int((s["L"] == 0).sum())
    d["winless"] = int((s["W"] == 0).sum())
    if W > 1:
        prev = standings(m, W - 1)[["LeagueName", "RosterID", "Rank"]].rename(columns={"Rank": "Prev"})
        s = s.merge(prev, on=["LeagueName", "RosterID"], how="left")
        s["Move"] = s["Prev"] - s["Rank"]
    else:
        s["Move"] = None
    top = s[s["Rank"] <= 32]
    d["top32"] = [{"Rank": int(r.Rank), "Team": r.Team, "Lg": r.Lg, "Owner": r.Owner,
                   "Rec": f"{r.W}-{r.L}" + (f"-{r.T}" if r.T else ""), "Pts": round(r.Pts, 2), "Luck": round(r.Luck, 2),
                   "Move": None if pd.isna(r.Move) else int(r.Move)} for r in top.itertuples()]

    d["top_scores"] = [game(r) for r in w.nlargest(10, "P").itertuples()]
    lg = w.groupby("Lg")["P"].mean().sort_values(ascending=False)
    d["leagues"] = [{"Lg": k, "Avg": round(v, 2)} for k, v in lg.items()]

    wins = w[w["Outcome"] == "Win"].copy()
    wins["Mg"] = wins["P"] - wins["PA"]
    losses = w[w["Outcome"] == "Loss"]
    aw = {
        "high": game(w.nlargest(1, "P").iloc[0]),
        "blowout": game(wins.nlargest(1, "Mg").iloc[0]),
        "closest": game(wins.nsmallest(1, "Mg").iloc[0]),
        "badbeat": game(losses.nlargest(1, "P").iloc[0]),
        "lucky": game(wins.nsmallest(1, "P").iloc[0]),
        "low": game(w.nsmallest(1, "P").iloc[0]),
    }
    if mx is not None:
        y = w.merge(mx[mx["Week"] == W][["LeagueID", "RosterID", "MaxPoints"]],
                    on=["LeagueID", "RosterID"], how="inner")
        y = y[(y["Outcome"] == "Loss") & (y["MaxPoints"] > y["PA"])].copy()
        if not y.empty:
            y["Left"] = y["MaxPoints"] - y["P"]
            r = y.nlargest(1, "Left").iloc[0]
            aw["ybs"] = {**game(r), "Max": round(r.MaxPoints, 2), "Left": round(r.Left, 2),
                         "Count": int(len(y))}
    if mx is not None:
        g2 = wins.merge(mx[mx["Week"] == W][["LeagueID", "RosterID", "MaxPoints"]],
                        on=["LeagueID", "RosterID"], how="inner")
        g2 = g2[g2["MaxPoints"] > 0].copy()
        if not g2.empty:
            g2["Eff"] = (g2["P"] / g2["MaxPoints"]).round(4)
            # Great Coaching: best lineup efficiency in a win; tie -> narrowest victory
            r = g2.sort_values(["Eff", "Mg"], ascending=[False, True]).iloc[0]
            aw["coach"] = {**game(r), "Max": round(r.MaxPoints, 2), "Eff": float(r.Eff)}
    up = upset(m, W)
    if up:
        aw["upset"] = up
    d["awards"] = aw

    st = sc[(sc["wk"] == W) & sc["st"]].copy()
    st["pos"] = st["player_id"].map(pos_map)
    best = st.sort_values("pts", ascending=False).drop_duplicates("player_id")
    d["players"] = []
    for p in POSITIONS:
        b = best[best["pos"] == p].head(1)
        if len(b):
            r = b.iloc[0]
            lab = str(r["label"]) if isinstance(r["label"], str) else str(r["player_id"])
            d["players"].append({"Pos": p, "Name": lab.split(",")[0],
                                 "NFL": lab.split("(")[-1].rstrip(")") if "(" in lab else "",
                                 "Pts": round(r["pts"], 2),
                                 "Started": int(st.loc[st["player_id"] == r["player_id"], "league_id"].nunique())})
    return d


# ---------------------------------------------------------------- render
def award_cols(n):
    """Desktop column count for n award cards: one row up to 7, else the 3-5 column
    grid that leaves the fewest empty slots (ties -> fewer columns, i.e. wider cards)."""
    if n <= 7:
        return n
    return min((3, 4, 5), key=lambda c: ((-n) % c, c))


def render(d, weeks, colors, tpl, updated, lcolors, ranks=None):
    W = d["week"]
    ranks = ranks or {}

    def rk(team):
        """Poll rank going into this week's games (the poll that applied to week W)."""
        n = ranks.get(team)
        return f'<span style="color:var(--mute);font-size:.85em">#{n}</span> ' if n else ""

    def chip(team):
        bg, fg = colors.get(team, ("#666666", "#ffffff"))
        return f'<span class="chip" style="background:{bg};color:{fg}" aria-hidden="true"></span>'

    def mark(team):
        f = os.path.join(LOGO_DIR, f"{team}.png")
        if os.path.exists(f):
            return f'<img class="logo" src="../{LOGO_DIR}/{quote(team)}.png" alt="">'
        return chip(team)

    def mv(x):
        if x is None:
            return '<span class="eq">–</span>'
        if x > 0:
            return f'<span class="up">▲{x}</span>'
        if x < 0:
            return f'<span class="dn">▼{-x}</span>'
        return '<span class="eq">–</span>'

    def card(label, g, val, unit, note):
        f = os.path.join(LOGO_DIR, f"{g['Team']}.png")
        has = os.path.exists(f)
        strip = (f'<div class="ls"><img src="../{LOGO_DIR}/{quote(g["Team"])}.png" alt="{e(g["Team"])} logo"></div>'
                 if has else "")
        return (f'<div class="aw"><div class="al">{label}</div>'
                f'<div class="av n">{val}<small>{unit}</small></div>'
                f'<div class="at">{"" if has else chip(g["Team"])}<b>{rk(g["Team"])}{e(g["Team"])}</b></div>'
                f'<div class="ao">{e(g["Owner"])} · {e(g["Lg"])}</div>'
                f'<div class="an">{note}</div>{strip}</div>')

    a = d["awards"]
    cards = [
        card("High score", a["high"], f'{a["high"]["P"]:.2f}', "pts", f'over {e(a["high"]["Opp"])}'),
        card("Biggest blowout", a["blowout"], f'+{a["blowout"]["Margin"]:.2f}', "margin",
             f'{a["blowout"]["P"]:.2f}–{a["blowout"]["PA"]:.2f} over {e(a["blowout"]["Opp"])}'),
        card("Closest game", a["closest"], f'{a["closest"]["Margin"]:.2f}', "margin",
             f'{a["closest"]["P"]:.2f}–{a["closest"]["PA"]:.2f} over {e(a["closest"]["Opp"])}'),
        card("Bad beat", a["badbeat"], f'{a["badbeat"]["P"]:.2f}', "pts in a loss",
             f'Lost to {e(a["badbeat"]["Opp"])}, {a["badbeat"]["PA"]:.2f}'),
        card("Lucky win", a["lucky"], f'{a["lucky"]["P"]:.2f}', "pts in a win",
             f'Beat {e(a["lucky"]["Opp"])}, {a["lucky"]["PA"]:.2f}'),
        card("Low score", a["low"], f'{a["low"]["P"]:.2f}', "pts", f'vs. {e(a["low"]["Opp"])}'),
    ]
    if "coach" in a:
        c = a["coach"]
        cards.append(card("Great coaching", c, f'{c["Eff"] * 100:.1f}%', "of max points",
                          f'{c["P"]:.2f} of a possible {c["Max"]:.2f}; beat {e(c["Opp"])} by {c["Margin"]:.2f}'))
    if "upset" in a:
        u = a["upset"]
        cards.append(card("Biggest upset", u, f'{u["WinPct"]:.0f}%', "pregame win chance",
                          f'Beat {e(u["Opp"])} {u["P"]:.2f}–{u["PA"]:.2f}'))
    if "ybs" in a:
        y = a["ybs"]
        cards.append(card("You beat yourself", y, f'{y["Left"]:.2f}', "pts left",
                          f'Scored {y["P"]:.2f}, best lineup {y["Max"]:.2f}, lost to '
                          f'{e(y["Opp"])} {y["PA"]:.2f}'))

    rows = "".join(
        f'<tr><td class="n">{r["Rank"]}</td><td class="mv">{mv(r["Move"])}</td>'
        f'<td class="tm">{chip(r["Team"])}<b>{rk(r["Team"])}{e(r["Team"])}</b><small>{e(r["Owner"])} · {e(r["Lg"])}</small></td>'
        f'<td class="n">{r["Rec"]}</td><td class="n">{r["Pts"]:.2f}</td>'
        f'<td class="n {"up" if r["Luck"] > 0.005 else "dn" if r["Luck"] < -0.005 else "eq"}">{r["Luck"]:+.2f}</td></tr>'
        for r in d["top32"])
    def result(g):
        """Top-score row result; a top score that LOST stands out in red with the winning score."""
        if g["Margin"] > 0:
            return f'def. {e(str(g["Opp"]))}'
        if g["Margin"] < 0:
            return f'<b class="dn">lost to {e(str(g["Opp"]))}, {g["PA"]:.2f}</b>'
        return f'tied {e(str(g["Opp"]))}'

    ts = "".join(
        f'<li><span class="n rk">{i + 1}</span>{chip(g["Team"])}<span class="nm"><b>{rk(g["Team"])}{e(g["Team"])}</b>'
        f'<small>{e(g["Owner"])} · {e(g["Lg"])} · {result(g)}</small></span>'
        f'<span class="n v">{g["P"]:.2f}</span></li>' for i, g in enumerate(d["top_scores"]))
    lo, hi = 115, max(l["Avg"] for l in d["leagues"])
    lo = min(lo, min(l["Avg"] for l in d["leagues"]) - 5)
    lg = "".join(
        f'<li><span class="ln">{e(l["Lg"])}</span><span class="bar"><i style="width:{(l["Avg"] - lo) / (hi - lo) * 100:.1f}%;background:{lcolors.get(l["Lg"], "var(--gold)")}"></i></span>'
        f'<span class="n">{l["Avg"]:.1f}</span></li>' for l in d["leagues"])
    pl = "".join(
        f'<li><span class="pos">{p["Pos"]}</span><span class="nm"><b>{e(p["Name"])}</b>'
        f'<small>{e(p["NFL"])} · started in {p["Started"]} of {N_LEAGUES} leagues</small></span>'
        f'<span class="n v">{p["Pts"]:.2f}</span></li>' for p in d["players"])
    cur = ' aria-current="page"'
    nav = nav_html(W, weeks)

    top32 = """<section><h2>Playoff Rank: Top 32 <small>Wins, then points</small></h2>
    <div class="tbl"><table><thead><tr><th class="r">#</th><th>{{PREVHDR}}</th><th>Team</th><th class="r">W-L</th><th class="r">PF</th><th class="r" title="Wins minus expected wins">Luck</th></tr></thead><tbody>{{ROWS}}</tbody></table></div>
    <p class="note">{{MOVENOTE}}Ranked across all 180 teams by wins, then total points. This is not the NCAA 180 poll.</p>
  </section>"""
    ranksec = top32
    try:  # the NCAA 180 Top 25 poll replaces the Playoff Rank table once a poll exists for this week
        import poll_page
        ps = poll_page.weekly_section(W)
        if ps:
            ranksec = f"<style>{ps[0]}</style>" + ps[1]
    except Exception as ex:  # fall back to Playoff Rank, never break the report
        print(f"Poll section unavailable ({ex}); using Playoff Rank.")
    out = tpl.replace("{{RANKSEC}}", ranksec)
    for k, v in {
        "WEEK": str(W), "PREVHDR": f"Wk {W - 1}" if W > 1 else "Wk",
        "MOVENOTE": (f"Movement is change in overall standings rank from Week {W - 1}. " if W > 1 else "")
        + "Luck is wins minus expected wins (share of all 179 other teams outscored each week). ",
        "UPDATED": updated, "NAV": nav,
        "AVG": f'{d["avg"]:.2f}', "MED": f'{d["median"]:.2f}',
        "UND": str(d["unbeaten"]), "WL": str(d["winless"]),
        "AW": "".join(cards), "AWCOLS": str(award_cols(len(cards))), "ROWS": rows, "TS": ts, "LG": lg, "PL": pl,
    }.items():
        out = out.replace("{{" + k + "}}", v)
    out = out.replace("Bars start at 115 points.", f"Bars start at {lo:.0f} points.")
    return out


# ---------------------------------------------------------------- main
def main():
    m = load()
    weeks = completed_weeks(m)
    if not weeks:
        print("No completed regular-season weeks yet; nothing to build.")
        return
    only = int(sys.argv[1]) if len(sys.argv) > 1 else None

    sc = pd.read_csv(SCORES, dtype=str)
    sc = sc[sc["LeagueYear"] == m["Year"].iloc[0]].copy()
    sc["wk"] = sc["weekNum"].astype(int)
    sc["pts"] = sc["points"].astype(float)
    sc["st"] = sc["is_starter"].str.lower() == "true"
    pl = pd.read_csv(PLAYERS, dtype=str)
    pos_map = dict(zip(pl["player_id"], pl["position"].replace({"FB": "RB"})))
    lab_pos = sc["label"].str.extract(r", ([A-Z]+) \(", expand=False)
    for pid, p in zip(sc["player_id"], lab_pos):
        if pid not in pos_map and isinstance(p, str):
            pos_map[pid] = p

    mx = None
    if os.path.exists(MAXPTS):
        mx = pd.read_csv(MAXPTS, dtype=str)
        mx["Week"] = mx["Week"].astype(int)
        mx["MaxPoints"] = mx["MaxPoints"].astype(float)
    else:
        print(f"WARNING: {MAXPTS} missing; 'You Beat Yourself' award skipped")

    c = pd.read_csv(COLORS, dtype=str, encoding="utf-8-sig")
    colors = {r.Team: (r.Primary, r.Secondary) for r in c.itertuples()}
    lc = pd.read_csv(LEAGUE_COLORS, dtype=str, encoding="utf-8-sig")
    full_to_short = {k.upper(): v for k, v in LEAGUE_DISPLAY.items()}
    lcolors = {}
    for r in lc.itertuples():
        short = full_to_short.get(str(r.League).upper())
        bg = str(r.Primary).strip()
        if short and bg:
            lcolors[short] = bg if bg.startswith("#") else "#" + bg
    tpl = open(TEMPLATE, encoding="utf-8").read()
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    os.makedirs(os.path.join(OUT_DIR, "data"), exist_ok=True)
    for W in weeks:
        if only and W != only:
            continue
        d = week_data(m, sc, mx, pos_map, W)
        page = render(d, weeks, colors, tpl, updated, lcolors, ranks_for_week(m["Year"].iloc[0], W))
        with open(os.path.join(OUT_DIR, f"week-{W:02d}.html"), "w", encoding="utf-8") as f:
            f.write(page)
        with open(os.path.join(OUT_DIR, "data", f"week-{W:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
        if W == weeks[-1]:
            with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
                f.write(page)
        print(f"Week {W}: high {d['awards']['high']['Owner']} {d['awards']['high']['P']}, "
              f"YBS {d['awards'].get('ybs', {}).get('Owner', '-')}")
    print(f"Wrote {OUT_DIR}/ for weeks {weeks[0]}-{weeks[-1]} (index = week {weeks[-1]})")


if __name__ == "__main__":
    main()
