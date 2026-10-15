"""
records_page.py -- reports/records.html: All-Time Records (v1) + data/Records_AllTime.csv.

Rules (Chris, 2026-10-14):
  - Single-game lists include the current season live (marked); SEASON lists (perfect seasons,
    most wins, Cinderella, best Lineup Skill season) stop at the last completed season -- the
    current season joins them through the end-of-season script.
  - Only real games: regular season + Postseason_Historic (Sleeper's fictional postseason pairings
    never count). Lowest score is regular season only (postseason teams without a real game may not
    set lineups).
  - Games with an orphaned (caretaker / vacant) side are left out of game records; orphan teams
    never hold a record.
  - Scores: one standard scoring system 2019-2025 (ScoresStandard_Historic; postseason file is
    already restated), official for the current season. Results stand as played; a game whose
    standard score would flip it carries a dagger (ScoringFlags_Historic).
  - Snapshot names/colors: each entry shows that season's team name.
  - Perfect season = 12-0: 11-0 regular season + CCG win. Most wins = regular season + CCG +
    postseason (head-to-head wins; advancing from a group = 1 win, going out in a group = 1 loss).
  - Highest score eliminated and Cinderella are per playoff round, on the Legend ladder
    (2022 "Second Round" relabelled Sweet 16 in the data). Cinderella needs seeds: 2022 on.
  - Milestones: first manager to each mark (wins, playoff appearances, titles, Legend points).
CWD must be repo root.
"""
import html
import json
import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import managers_page as mp  # noqa: E402
import manager_lineups as ml  # noqa: E402
import team_names as tn  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

OUT = "reports/records.html"
OUT_CSV = "data/Records_AllTime.csv"
FLAGS = "data/ScoringFlags_Historic.csv"
TOP = 10
e = html.escape
ROUND_NAME = {1: "First round / group stage", 2: "Sweet 16", 3: "Elite 8", 4: "Final Four", 5: "Title game"}
MILESTONES = {"Career wins": [25, 50, 75, 100], "Playoff appearances": [3, 5, 7], "National titles": [1, 2, 3],
              "Legend points": [100, 150, 200]}


_SHORT = {}


def lg_short(name):
    if not _SHORT:
        import poll_common as pc
        _SHORT.update(pc.league_short())
    return _SHORT.get(str(name).strip().upper(), str(name).replace("NCAA ", "").title())


def load():
    year = int(pd.read_csv(ml.LEAGUES, dtype=str)["Year"].astype(int).max())
    m = mp.regular_season(year)
    owner_last = m.sort_values("Week").groupby(["Year", "LeagueName", "RosterID"]).agg(
        OwnerID=("OwnerID", "last"), OwnerName=("OwnerName", "last"), Orphan=("Orphan", "last"))
    flags = set()
    if os.path.exists(FLAGS):
        f = pd.read_csv(FLAGS, dtype=str)
        f = f[f["Type"] == "Game"]
        flags = {(int(r.Year), r.LeagueName.strip(), int(r.Week), str(r.RosterID)) for r in f.itertuples()}
    return year, m, owner_last, flags


def name(year, league, rid):
    return tn.season_name(year, league, rid) or ""


def regular_games(m, flags):
    """One row per regular-season game (both sides known)."""
    a = m.rename(columns=lambda c: c)
    b = m[["Year", "LeagueID", "Week", "RosterID", "PF", "OwnerName", "Orphan"]].rename(
        columns={"RosterID": "OpponentRosterID", "PF": "PA2", "OwnerName": "OppOwner", "Orphan": "OppOrphan"})
    g = a.merge(b, on=["Year", "LeagueID", "Week", "OpponentRosterID"], how="inner")
    g = g[g["RosterID"].astype(int) < g["OpponentRosterID"].astype(int)].copy()
    rows = []
    for r in g.itertuples():
        win_home = r.Outcome == "Win"
        tie = r.Outcome == "Tie"
        W = (r.RosterID, r.PF, r.OwnerName, r.Orphan) if (win_home or tie) else (r.OpponentRosterID, r.PA2, r.OppOwner, r.OppOrphan)
        L = (r.OpponentRosterID, r.PA2, r.OppOwner, r.OppOrphan) if (win_home or tie) else (r.RosterID, r.PF, r.OwnerName, r.Orphan)
        dag = (r.Year, r.LeagueName, int(r.Week), str(r.RosterID)) in flags
        rows.append({"Year": r.Year, "Week": int(r.Week), "Stage": f"Week {int(r.Week)}", "League": r.LeagueName,
                     "WTeam": name(r.Year, r.LeagueName, W[0]), "WOwner": W[2], "WPts": round(W[1], 2), "WOrphan": W[3],
                     "LTeam": name(r.Year, r.LeagueName, L[0]), "LOwner": L[2], "LPts": round(L[1], 2), "LOrphan": L[3],
                     "Tie": tie, "Dagger": dag, "Post": False})
    return pd.DataFrame(rows)


def post_owner(owner_last, year, team):
    s = tn.slot(year, team)
    if s is None:
        return "", "", True
    k = (year, s[0].strip(), str(s[1]))
    if k in owner_last.index:
        o = owner_last.loc[k]
        return s[0].strip(), ("Orphan" if o.Orphan else o.OwnerName), bool(o.Orphan)
    return s[0].strip(), "", False


def postseason(owner_last, year):
    """Head-to-head postseason games and per-team postseason results."""
    p = pd.read_csv(mp.POST, dtype=str)
    games, team_rows = [], []
    for r in p.itertuples():
        y = int(r.Season)
        if y >= year:
            continue
        ta, tb = mp.split(r.TeamA), mp.split(r.TeamB)
        winners = set(mp.split(r.Winner))
        step = mp.LADDER.get(r.RoundName) if r.Event == "Playoff" else None
        label = (r.Bowl if r.Event in ("Bowl", "CCG") and isinstance(r.Bowl, str) else r.RoundName) or r.Event
        stage = {"CCG": f"{label} CCG", "Bowl": label, "NIT": f"NIT {label}", "Playoff": label}.get(r.Event, label)
        if len(ta) == 1 and len(tb) == 1:
            try:
                sa, sb = float(r.ScoreA), float(r.ScoreB)
            except (TypeError, ValueError):
                continue  # no score recorded (e.g. a forfeit or unplayed pairing)
            for t, s, o, won in ((ta[0], sa, tb[0], ta[0] in winners), (tb[0], sb, ta[0], tb[0] in winners)):
                lg, own, orph = post_owner(owner_last, y, t)
                team_rows.append({"Year": y, "Team": t, "League": lg, "Owner": own, "Orphan": orph, "Event": r.Event,
                                  "Step": step, "Round": r.RoundName, "Pts": s, "Won": won,
                                  "Seed": r.SeedA if t == ta[0] else r.SeedB, "Stage": stage})
            w, l = (ta[0], tb[0]) if ta[0] in winners else (tb[0], ta[0])
            lw, ow, orw = post_owner(owner_last, y, w)
            ll, ol, orl = post_owner(owner_last, y, l)
            games.append({"Year": y, "Week": int(float(r.Week)) if isinstance(r.Week, str) and r.Week else 99,
                          "Stage": stage, "League": lw, "WTeam": w, "WOwner": ow, "WPts": sa if w == ta[0] else sb,
                          "WOrphan": orw, "LTeam": l, "LOwner": ol, "LPts": sb if w == ta[0] else sa, "LOrphan": orl,
                          "Tie": False, "Dagger": False, "Post": True})
        else:  # group: everyone listed in TeamA with scores in ScoreA
            sc = [float(x) if x else None for x in mp.split(r.ScoreA)] if isinstance(r.ScoreA, str) else []
            seeds = mp.split(r.SeedA)
            for i, t in enumerate(ta):
                lg, own, orph = post_owner(owner_last, y, t)
                team_rows.append({"Year": y, "Team": t, "League": lg, "Owner": own, "Orphan": orph, "Event": r.Event,
                                  "Step": step, "Round": r.RoundName, "Pts": sc[i] if i < len(sc) else None,
                                  "Won": t in winners, "Seed": seeds[i] if i < len(seeds) else "", "Stage": stage})
    return pd.DataFrame(games), pd.DataFrame(team_rows)


def entry(cat, rank, value, year, team, owner, league, detail, dagger=False, live=False):
    return {"Category": cat, "Rank": rank, "Value": value, "Year": year, "Team": team, "Owner": owner,
            "League": lg_short(league) if league else "", "Detail": detail, "Dagger": dagger, "Live": live}


def top(df, cat, sort, asc, fn, n=TOP):
    out = []
    for i, r in enumerate(df.sort_values(sort, ascending=asc).head(n).itertuples(), 1):
        out.append(fn(cat, i, r))
    return out


def build():
    year, m, owner_last, flags = load()
    reg = regular_games(m, flags)
    pg, pt = postseason(owner_last, year)
    games = pd.concat([reg, pg], ignore_index=True)
    clean = games[~games["WOrphan"].astype(bool) & ~games["LOrphan"].astype(bool)].copy()
    clean["Margin"] = (clean["WPts"] - clean["LPts"]).abs().round(2)  # † games can be reversed on standard scores
    clean["Combined"] = (clean["WPts"] + clean["LPts"]).round(2)
    rec = []
    sections = []

    def game_detail(r, side="W"):
        if side == "W":
            return f"{'Tied' if r.Tie else 'Beat'} {r.LTeam} {r.WPts:.2f}–{r.LPts:.2f} · {r.Stage}"
        return f"Lost to {r.WTeam} {r.LPts:.2f}–{r.WPts:.2f} · {r.Stage}"

    # team-side scores for high/low
    sides = pd.concat([
        clean.assign(Team=clean.WTeam, Owner=clean.WOwner, Pts=clean.WPts, Side="W"),
        clean.assign(Team=clean.LTeam, Owner=clean.LOwner, Pts=clean.LPts, Side="L")], ignore_index=True)
    live = lambda r: r.Year == year  # noqa: E731
    sg = [
        ("Highest score", top(sides, "Highest score", ["Pts"], False, lambda c, i, r: entry(
            c, i, f"{r.Pts:.2f}", r.Year, r.Team, r.Owner, r.League, game_detail(r, r.Side), r.Dagger, live(r)))),
        ("Lowest score (regular season)", top(sides[~sides["Post"]], "Lowest score", ["Pts"], True, lambda c, i, r: entry(
            c, i, f"{r.Pts:.2f}", r.Year, r.Team, r.Owner, r.League, game_detail(r, r.Side), r.Dagger, live(r)))),
        ("Biggest blowout", top(clean, "Biggest blowout", ["Margin"], False, lambda c, i, r: entry(
            c, i, f"+{r.Margin:.2f}", r.Year, r.WTeam, r.WOwner, r.League, game_detail(r), r.Dagger, live(r)))),
        ("Closest games", top(clean, "Closest games", ["Margin", "Combined"], [True, False], lambda c, i, r: entry(
            c, i, "Tie" if r.Tie else f"{r.Margin:.2f}", r.Year, r.WTeam, r.WOwner, r.League, game_detail(r), r.Dagger, live(r)))),
        ("Highest losing score", top(clean[~clean["Tie"]], "Highest losing score", ["LPts"], False, lambda c, i, r: entry(
            c, i, f"{r.LPts:.2f}", r.Year, r.LTeam, r.LOwner, r.League, game_detail(r, "L"), r.Dagger, live(r)))),
        ("Lowest winning score", top(clean[~clean["Tie"]], "Lowest winning score", ["WPts"], True, lambda c, i, r: entry(
            c, i, f"{r.WPts:.2f}", r.Year, r.WTeam, r.WOwner, r.League, game_detail(r), r.Dagger, live(r)))),
        ("Highest combined score", top(clean, "Highest combined score", ["Combined"], False, lambda c, i, r: entry(
            c, i, f"{r.Combined:.2f}", r.Year, r.WTeam, r.WOwner, r.League, game_detail(r), r.Dagger, live(r)))),
    ]
    sections.append(("single", "Single game", sg))

    # ---- champions
    champs, finals = [], pt[(pt["Event"] == "Playoff") & (pt["Round"] == "National Championship")]
    for y, g in finals.groupby("Year"):
        w = g[g["Won"]].iloc[0]
        l = g[~g["Won"]].iloc[0]
        champs.append(entry("Champion", y, f"{w.Pts:.2f}–{l.Pts:.2f}", y, w.Team, w.Owner, w.League,
                            f"Runner-up {l.Team} ({l.Owner or 'Orphan'})"))
    champs.sort(key=lambda r: -r["Year"])
    mgr = pd.read_csv(mp.OUT_MGR, dtype={"OwnerID": str}) if os.path.exists(mp.OUT_MGR) else pd.DataFrame()
    title_mgr = []
    if len(mgr):
        t = mgr[mgr["Titles"] > 0].sort_values(["Titles", "Legend"], ascending=False)
        title_mgr = [entry("Titles by manager", i, int(r.Titles), "", r.Team, r.Manager, "", f"{int(r.FinalFours)} Final Fours · "
                           f"{int(r.Playoffs)} playoff trips") for i, r in enumerate(t.itertuples(), 1)]
    prog = defaultdict(list)
    for c in champs:
        s = tn.slot(c["Year"], c["Team"])
        cur = tn.current_name(*s) if s else c["Team"]
        prog[cur or c["Team"]].append(c["Year"])
    title_prog = [entry("Titles by program", i, len(v), "", k, "", "", ", ".join(str(x) for x in sorted(v)))
                  for i, (k, v) in enumerate(sorted(prog.items(), key=lambda kv: (-len(kv[1]), min(kv[1]))), 1)]
    sections.insert(0, ("champions", "Champions", [("National champions", champs), ("Titles by manager", title_mgr),
                                                     ("Titles by program (current name)", title_prog)]))

    # ---- seasons (completed seasons only)
    regs = m[(m["Year"] < year) & ~m["Orphan"]]
    sr = regs.groupby(["Year", "LeagueName", "RosterID"]).agg(
        W=("Outcome", lambda x: (x == "Win").sum()), L=("Outcome", lambda x: (x == "Loss").sum()),
        T=("Outcome", lambda x: (x == "Tie").sum()), G=("Outcome", "size"), PF=("PF", "sum")).reset_index()
    pt["Slot"] = [tn.slot(y, t) for y, t in zip(pt["Year"], pt["Team"])]
    pw = defaultdict(lambda: [0, 0, []])
    for r in pt.itertuples():
        if r.Slot is None:
            continue
        k = (r.Year, r.Slot[0].strip(), str(r.Slot[1]))
        pw[k][0 if r.Won else 1] += 1
        if r.Event == "CCG" and r.Won:
            pw[k][2].append("CCG")
        if r.Event == "Playoff" and r.Round == "National Championship" and r.Won:
            pw[k][2].append("Title")
    rows = []
    for r in sr.itertuples():
        k = (r.Year, r.LeagueName, r.RosterID)
        o = owner_last.loc[k]
        pwn, pls, tags = pw.get(k, [0, 0, []])
        rows.append({"Year": r.Year, "League": r.LeagueName, "Team": name(r.Year, r.LeagueName, r.RosterID),
                     "Owner": o.OwnerName, "RegW": r.W, "RegL": r.L, "RegT": r.T, "G": r.G, "PF": r.PF,
                     "PostW": pwn, "PostL": pls, "CCG": "CCG" in tags, "Title": "Title" in tags})
    sea = pd.DataFrame(rows)
    sea["TotW"], sea["TotL"] = sea["RegW"] + sea["PostW"], sea["RegL"] + sea["PostL"]
    perfect = sea[(sea["RegW"] == 11) & (sea["RegL"] == 0) & sea["CCG"]].sort_values(["TotW", "Year"], ascending=[False, True])
    per = [entry("Perfect season", i, f"{r.TotW}-{r.TotL}", r.Year, r.Team, r.Owner, r.League,
                 "11-0 + conference title" + (" · National champion" if r.Title else f" · finished {r.TotW}-{r.TotL}"))
           for i, r in enumerate(perfect.itertuples(), 1)]
    most = top(sea, "Most wins in a season", ["TotW", "TotL", "PF"], [False, True, False], lambda c, i, r: entry(
        c, i, f"{r.TotW}-{r.TotL}" + (f"-{r.RegT}" if r.RegT else ""), r.Year, r.Team, r.Owner, r.League,
        f"Regular season {r.RegW}-{r.RegL}" + (" · National champion" if r.Title else "")))
    sections.append(("seasons", f"Season (2019–{year - 1})", [("Perfect seasons (12-0)", per),
                                                                ("Most wins in a season", most)]))

    # ---- playoffs: highest score eliminated per round, Cinderella per round
    po = pt[(pt["Event"] == "Playoff") & pt["Step"].notna() & pt["Pts"].notna()].copy()
    po["Step"] = po["Step"].astype(int)
    elim = []
    for step in range(1, 6):
        d = po[(po["Step"] == step) & ~po["Won"] & ~po["Orphan"]]
        elim.append((f"Highest score eliminated · {ROUND_NAME[step]}", top(d, "Highest score eliminated", ["Pts"], False,
                    lambda c, i, r: entry(c, i, f"{r.Pts:.2f}", r.Year, r.Team, r.Owner, r.League, f"{r.Round}"), 3)))
    seeds = {}
    for r in po[po["Year"] >= 2022].itertuples():
        if str(r.Seed).strip().isdigit():
            seeds[(r.Year, r.Team)] = int(r.Seed)
    reach = po[po["Year"] >= 2022].groupby(["Year", "Team"]).agg(Step=("Step", "max"), Owner=("Owner", "last"),
                                                                    League=("League", "last")).reset_index()
    champs_set = {(c["Year"], c["Team"]) for c in champs}
    reach["Seed"] = [seeds.get((y, t)) for y, t in zip(reach["Year"], reach["Team"])]
    reach = reach[reach["Seed"].notna()]
    cin = []
    for step, label in ((3, "Reached the Elite 8"), (4, "Reached the Final Four"), (5, "Reached the title game"), (6, "Won it all")):
        d = reach[[((y, t) in champs_set) if step == 6 else s >= step for y, t, s in zip(reach.Year, reach.Team, reach.Step)]]
        cin.append((f"Cinderella · {label}", top(d, "Cinderella", ["Seed", "Year"], [False, True], lambda c, i, r: entry(
            c, i, f"#{int(r.Seed)} seed", r.Year, r.Team, r.Owner, r.League, label), 3)))
    sections.append(("playoffs", "Playoffs", elim + cin))

    # ---- milestones (first manager to each mark), from managers_page season data
    ms = pd.read_csv(mp.OUT_SEASONS, dtype={"OwnerID": str}) if os.path.exists(mp.OUT_SEASONS) else pd.DataFrame()
    miles = []
    if len(ms):
        ms = ms.sort_values("Year")
        ms["Playoff"] = ms["Finish"].fillna("").str.contains("Playoffs|Sweet 16|Elite 8|Final Four|Title game|National champion")
        ms["TitleN"] = ms["Finish"].fillna("").str.contains("National champion").astype(int)
        # wins by week (ties and in-season order matter for the first to reach a mark)
        wk = m[~m["Orphan"]].sort_values(["Year", "Week"])
        wk = wk.assign(Wn=(wk["Outcome"] == "Win").astype(int))
        wk["Cum"] = wk.groupby("OwnerID")["Wn"].cumsum()
        latest = wk.groupby("OwnerID")["OwnerName"].last()
        for mark in MILESTONES["Career wins"]:
            hit = wk[wk["Cum"] >= mark].groupby("OwnerID").head(1).sort_values(["Year", "Week"])
            if len(hit):
                first = hit.iloc[0]
                same = hit[(hit.Year == first.Year) & (hit.Week == first.Week)]
                who = " & ".join(latest[o] for o in same["OwnerID"])
                miles.append(entry("Milestone", f"{mark} wins", f"{mark} wins", int(first.Year), "", who, "",
                                   f"Week {int(first.Week)}, {int(first.Year)} · {len(hit)} manager(s) there now"))
            else:
                best = wk.groupby("OwnerID")["Cum"].max().sort_values(ascending=False)
                miles.append(entry("Milestone", f"{mark} wins", f"{mark} wins", "", "", latest[best.index[0]], "",
                                   f"Not reached yet · closest: {int(best.iloc[0])}", live=True))
        for label, col in (("Playoff appearances", "Playoff"), ("National titles", "TitleN"), ("Legend points", "Legend")):
            cum = ms.assign(V=ms[col].astype(float)).groupby("OwnerID")["V"].cumsum()
            ms["_c"] = cum
            for mark in MILESTONES[label]:
                hit = ms[ms["_c"] >= mark].groupby("OwnerID").head(1).sort_values("Year")
                unit = {"Playoff appearances": "playoff trips", "National titles": "titles" if mark > 1 else "title",
                        "Legend points": "Legend points"}[label]
                if len(hit):
                    y0 = hit["Year"].iloc[0]
                    who = " & ".join(sorted(hit[hit.Year == y0]["Manager"]))
                    miles.append(entry("Milestone", f"{mark} {unit}", f"{mark} {unit}", int(y0), "", who, "",
                                       f"{int(y0)} · {len(hit)} manager(s) there now"))
                else:
                    best = ms.groupby("OwnerID").agg(M=("Manager", "last"), V=("_c", "max")).sort_values("V", ascending=False).iloc[0]
                    miles.append(entry("Milestone", f"{mark} {unit}", f"{mark} {unit}", "", "", best.M, "",
                                       f"Not reached yet · closest: {best.V:g}", live=True))
    sections.append(("milestones", "First to the mark", [("Milestones", miles)]))

    # ---- lineups & streaks
    lw = pd.concat([pd.read_csv(ml.WEEKS_HIST, dtype={"LeagueID": str, "RosterID": str, "OwnerID": str}),
                    pd.read_csv(ml.WEEKS_SEASON, dtype={"LeagueID": str, "RosterID": str, "OwnerID": str})], ignore_index=True)
    lw = lw[lw["OwnerID"] != "Orphan"]
    out = m[["Year", "LeagueID", "Week", "RosterID", "Outcome", "PF", "PointsAgainst"]].copy()
    out["RosterID"] = out["RosterID"].astype(str)
    lw = lw.merge(out, on=["Year", "LeagueID", "Week", "RosterID"], how="left")
    lw["Left"] = (lw["Best"] - lw["Actual"]).round(2)
    loss = lw[lw["Outcome"] == "Loss"]
    left = top(loss, "Most points left on the bench in a loss", ["Left"], False, lambda c, i, r: entry(
        c, i, f"{r.Left:.2f}", r.Year, name(r.Year, r.LeagueName, r.RosterID), r.OwnerName, r.LeagueName,
        f"Week {r.Week}: started {r.Actual:.2f}, best possible {r.Best:.2f}", live=r.Year == year))
    lss = pd.read_csv(ml.OUT_SEASON, dtype={"OwnerID": str})
    lss = lss[(lss["Year"] < year) & (lss["Games"] >= 9) & (lss["OwnerID"] != "Orphan")]
    bestls = top(lss, "Best Lineup Skill season", ["LineupSkill"], False, lambda c, i, r: entry(
        c, i, f"{r.LineupSkill:.3f}".lstrip("0"), r.Year, "", r.OwnerName, "", f"{int(r.Games)} games · "
        f"{r.PtsLeftPerGame:.2f} left on bench per game"))
    # streaks: per manager, regular season in order, across seasons
    st = m[~m["Orphan"]].sort_values(["Year", "Week"])
    runs = []
    for oid, g in st.groupby("OwnerID"):
        cur_t, cur_n, start = None, 0, None
        res = list(zip(g["Outcome"], g["Year"], g["Week"]))
        for i, (o, y, w) in enumerate(res):
            if o == cur_t:
                cur_n += 1
            else:
                if cur_t in ("Win", "Loss"):
                    runs.append((oid, cur_t, cur_n, start, res[i - 1][1:], False))
                cur_t, cur_n, start = o, 1, (y, w)
        if cur_t in ("Win", "Loss"):
            runs.append((oid, cur_t, cur_n, start, res[-1][1:], (res[-1][1], res[-1][2]) == (year, int(st[st.Year == year]["Week"].max()))))
    rn = pd.DataFrame(runs, columns=["OwnerID", "Type", "N", "Start", "End", "Active"])
    names_latest = st.groupby("OwnerID")["OwnerName"].last()
    strk = []
    for t, label in (("Win", "Longest winning streak"), ("Loss", "Longest losing streak")):
        strk.append((label, top(rn[rn["Type"] == t], label, ["N"], False, lambda c, i, r: entry(
            c, i, f"{r.N} games", r.Start[0], "", names_latest[r.OwnerID], "",
            f"Week {r.Start[1]}, {r.Start[0]} → week {r.End[1]}, {r.End[0]}" + (" · active" if r.Active else ""),
            live=r.Active))))
    sections.append(("lineups", "Lineups & streaks", [("Best Lineup Skill season (9+ games)", bestls),
                                                      ("Most points left on the bench in a loss", left)] + strk))

    flat = [dict(r, Section=sec[1], List=lst) for sec in sections for lst, rows in sec[2] for r in rows]
    pd.DataFrame(flat).to_csv(OUT_CSV, index=False)
    write_page(sections, year)
    print(f"Wrote {OUT} and {OUT_CSV} ({len(flat)} entries)")
    return sections


CSS = """
.jump{display:flex;flex-wrap:wrap;gap:6px;margin:4px 0 0}
.jump a{font:700 12px var(--num);letter-spacing:.04em;text-transform:uppercase;padding:4px 9px;border:1px solid var(--line);border-radius:3px;color:var(--ink);text-decoration:none;background:var(--panel)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:14px}
.card{border:1px solid var(--line);border-radius:6px;padding:10px 12px;background:var(--panel)}
.card h3{margin:0 0 6px;font:700 13px var(--num);letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
.card ol{list-style:none;margin:0;padding:0}
.card li{display:grid;grid-template-columns:22px 1fr auto;gap:2px 8px;padding:5px 0;border-top:1px solid var(--line);align-items:start}
.card li:first-child{border-top:0}
.card .k{font:700 13px var(--num);color:var(--mute)}
.card .v{font:700 15px var(--num);text-align:right;white-space:nowrap}
.card .w b{font-weight:700}
.card .w small{display:block;color:var(--mute);font-size:12px;margin-top:1px}
.pt{display:inline-block;padding:1px 7px;border-radius:3px;font-weight:700;font-size:12px;line-height:1.35;margin-right:4px}
.live{font:700 10px var(--num);letter-spacing:.06em;color:var(--accent);margin-left:4px}
.card li.m{grid-template-columns:110px 1fr}
.card li.m .v{text-align:left;font-size:13px}
"""


def write_page(sections, year):
    def pill(team, y):
        if not team:
            return ""
        bg, fg = mp.chip(team)
        return f'<span class="pt" style="background:{bg};color:{fg}">{e(team)}</span>'

    def li(r):
        tag = f'<span class="live">{year}</span>' if r["Live"] and r["Year"] == year else ""
        dag = " †" if r["Dagger"] else ""
        if r["Category"] == "Milestone":
            who = e(r["Owner"]) if r["Owner"] else "–"
            return (f'<li class="m"><span class="v">{e(str(r["Value"]))}</span><span class="w"><b>{who}</b>'
                    f'<small>{e(r["Detail"])}</small></span></li>')
        yr = f'{r["Year"]} · ' if r["Year"] != "" and r["Category"] not in ("Champion",) else ""
        lg = f' · {e(r["League"])}' if r["League"] else ""
        k = r["Rank"] if r["Category"] != "Champion" else ""
        head = f'{pill(r["Team"], r["Year"])}<b>{e(r["Owner"] or "")}</b>{tag}' if r["Team"] else f'<b>{e(r["Owner"])}</b>{tag}'
        if r["Category"] == "Champion":
            head = f'<span class="k">{r["Year"]}</span> ' + head
        return (f'<li><span class="k">{k}</span><span class="w">{head}<small>{yr}{e(r["Detail"])}{lg}</small></span>'
                f'<span class="v">{e(str(r["Value"]))}{dag}</span></li>')

    jump = "".join(f'<a href="#{sid}">{e(t)}</a>' for sid, t, _ in sections)
    secs = []
    for sid, title, lists in sections:
        cards = "".join(f'<div class="card"><h3>{e(lt)}</h3><ol>{"".join(li(r) for r in rows) or "<li>–</li>"}</ol></div>'
                        for lt, rows in lists)
        secs.append(f'<section id="{sid}"><h2>{e(title)}</h2><div class="grid">{cards}</div></section>')
    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("records")}</nav>
<header><div><div class="eyebrow">NCAA 180 · 2019–{year}</div><h1>All-Time <em>Records</em></h1></div></header>
<nav class="jump" aria-label="Sections">{jump}</nav>
{"".join(secs)}
<section><p class="note">Real games only: regular season plus the postseason (conference championships, bowls, NIT,
playoffs); Sleeper's placeholder postseason pairings never count. Lowest score is regular season only. Games with an
orphaned (caretaker or vacant) team are left out. 2019–{year - 1} scores use one standard scoring system; results stand
as played, and † marks a game whose standard score would have flipped it. Single-game records include {year} so far
(marked); season records cover completed seasons. Perfect season = 11-0 plus the conference title. Season win totals
count head-to-head postseason wins, with advancing from a group as one win. Cinderella uses seeds, recorded from 2022
on. Streaks run across seasons, regular season only. Team names are as of that season.
<a href="../{OUT_CSV}">Raw CSV</a></p></section>
</div>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page_head("NCAA 180 All-Time Records", CSS) + body)


if __name__ == "__main__":
    build()
