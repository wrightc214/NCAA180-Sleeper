"""Standard-scoring layer for history (Chris, 2026-10-08).

Every historical score is restated on ONE scoring system: each season's majority league
settings. Official Sleeper numbers are never overwritten; this script derives:

  data/ScoresStandard_Historic.csv  Year, LeagueID, LeagueName, Week, RosterID,
                                    PointsOfficial, PointsStandard, Delta  (every team-week)
  data/ScoringFlags_Historic.csv    footnotes: results that read differently under standard
                                    scoring (Type = Game | DivisionTitle | BowlLine)

Rules (Chris, 2026-10-08):
  - Scores and regular-season records shown on standard scoring; a flipped game is footnoted
    with its official result.
  - Division titles, CCG/playoff/bowl/NIT appearances and results stay as actually played,
    footnoted where standard standings disagree. Draft orders stay as they happened.
  - Prestige and bot rankings use the matches actually played (real participants) with
    standard scores.
  - Current season: official Sleeper scores; it is restated when it becomes history.

Re-scoring uses Sleeper weekly stat lines for only the settings that differ between leagues
(config/history.json -> restated_keys). A season whose leagues all match has Delta 0.
Run: python scripts/standard_scores.py   (rerun after any history rebuild / rollover)
"""
import collections
import json

import pandas as pd

CFG = json.load(open("config/history.json"))
OUT_SCORES = "data/ScoresStandard_Historic.csv"
OUT_FLAGS = "data/ScoringFlags_Historic.csv"


def rid(s):
    return str(s).replace(".0", "") if pd.notna(s) else ""


def settings_delta():
    s = pd.read_csv(CFG["scoring_settings"])
    out = {}
    for y, g in s.groupby("Year"):
        L = {str(r.LeagueID): json.loads(r.Settings) for r in g.itertuples()}
        keys = set().union(*L.values())
        maj = {k: collections.Counter(round(d.get(k, 0), 3) for d in L.values()).most_common(1)[0][0] for k in keys}
        for lid, d in L.items():
            dd = {k: maj[k] - round(d.get(k, 0), 3) for k in keys
                  if k.startswith(tuple(CFG["restated_keys"])) and round(d.get(k, 0), 3) != maj[k]}
            if dd:
                out[(int(y), lid)] = dd
    return out


def team_weeks(delta):
    st = pd.read_csv(CFG["scoring_stats"], dtype={"PlayerID": str})
    stat = {}
    for r in st.itertuples():
        stat.setdefault((int(r.Year), int(r.Week), r.PlayerID), {})[r.Stat] = r.Value
    base, dl = collections.defaultdict(float), collections.defaultdict(float)
    for f in CFG["starter_scores"]:
        sc = pd.read_csv(f, dtype=str)
        for r in sc.itertuples():
            y, w = int(r.LeagueYear), int(r.weekNum)
            k = (y, r.league_id, rid(r.roster_id), w)
            base[k] += float(r.starter_points or 0)
            dd = delta.get((y, r.league_id))
            if dd:
                s = stat.get((y, w, str(r.starter))) or {}
                dl[k] += sum(v * s.get(kk, 0) for kk, v in dd.items())
    have = {(y, w) for (y, w, _) in stat}
    gaps = sorted({(y, w) for (y, l, _, w) in base if (y, l) in delta} - have)
    if gaps:
        print(f"warning: restated seasons with no stat lines at all for {len(gaps)} weeks (e.g. {gaps[:3]})")
    return base, dl


def main():
    delta = settings_delta()
    base, dl = team_weeks(delta)
    m = pd.concat([pd.read_csv(f, dtype=str) for f in CFG["matchups"]])
    m["LeagueName"] = m["LeagueName"].str.strip()
    m["RosterID"] = m["RosterID"].map(rid)
    m["OpponentRosterID"] = m["OpponentRosterID"].map(rid)
    names = m.drop_duplicates(["Year", "LeagueID"]).set_index(["Year", "LeagueID"])["LeagueName"].to_dict()
    rows = []
    for (y, lid, r_, w), pts in base.items():
        rows.append((y, lid, names.get((str(y), lid), ""), w, r_, round(pts, 2), round(pts + dl.get((y, lid, r_, w), 0), 2),
                     round(dl.get((y, lid, r_, w), 0), 2)))
    sc = pd.DataFrame(rows, columns=["Year", "LeagueID", "LeagueName", "Week", "RosterID",
                                     "PointsOfficial", "PointsStandard", "Delta"]).sort_values(["Year", "LeagueName", "Week", "RosterID"])
    sc.to_csv(OUT_SCORES, index=False)

    # games: official vs standard result
    std = {(str(r.Year), r.LeagueID, str(r.Week), r.RosterID): r.PointsStandard for r in sc.itertuples()}
    m = m[m["OpponentRosterID"] != ""].copy()
    m["PS"] = [std.get((r.Year, r.LeagueID, r.Week, r.RosterID)) for r in m.itertuples()]
    m["PAS"] = [std.get((r.Year, r.LeagueID, r.Week, r.OpponentRosterID)) for r in m.itertuples()]
    m = m.dropna(subset=["PS", "PAS"])
    res = lambda a, b: "W" if a > b else ("L" if a < b else "T")
    m["ResO"] = [res(float(a), float(b)) for a, b in zip(m.PointsFor, m.PointsAgainst)]
    m["ResS"] = [res(a, b) for a, b in zip(m.PS, m.PAS)]
    flags = []
    import team_names as tn
    nm = lambda y, lg, r_: tn.season_name(int(y), lg, r_) or f"{lg} r{r_}"
    lr = CFG["last_regular_week"]
    for r in m[(m.ResO != m.ResS) & (m.Week.astype(int) <= lr)].itertuples():
        flags.append(dict(Year=r.Year, LeagueName=r.LeagueName, Week=r.Week, RosterID=r.RosterID, Team=nm(r.Year, r.LeagueName, r.RosterID),
                          Opponent=nm(r.Year, r.LeagueName, r.OpponentRosterID), Type="Game",
                          Official=f"{r.ResO} {float(r.PointsFor):.2f}-{float(r.PointsAgainst):.2f}",
                          Standard=f"{r.ResS} {r.PS:.2f}-{r.PAS:.2f}",
                          Note=f"Result differs under standard scoring; official result {r.ResO} {float(r.PointsFor):.2f}-{float(r.PointsAgainst):.2f}"))

    # division titles (regular season) and the .500 bowl line
    reg = m[m.Week.astype(int) <= lr]
    agg = reg.assign(WO=(reg.ResO == "W") + 0.5 * (reg.ResO == "T"), WS=(reg.ResS == "W") + 0.5 * (reg.ResS == "T"),
                     PFO=reg.PointsFor.astype(float), PFS=reg.PS.astype(float), G=1) \
        .groupby(["Year", "LeagueID", "LeagueName", "RosterID"]).agg(WO=("WO", "sum"), WS=("WS", "sum"), PFO=("PFO", "sum"),
                                                                     PFS=("PFS", "sum"), G=("G", "sum")).reset_index()
    stn = pd.concat([pd.read_csv(f, dtype=str) for f in CFG["standings"]])
    stn["RosterID"] = stn["RosterID"].map(rid)
    div = stn.drop_duplicates(["Year", "LeagueID", "RosterID"]).set_index(["Year", "LeagueID", "RosterID"])["Division"].to_dict()
    agg["Division"] = [div.get((r.Year, r.LeagueID, r.RosterID)) for r in agg.itertuples()]
    post = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
    played = set()  # (Year, LeagueName, RosterID) that actually played a CCG
    for r in post[post.Event == "CCG"].itertuples():
        for t in (r.TeamA, r.TeamB):
            sl = tn.slot(int(r.Season), t) if t else None
            if sl:
                played.add((r.Season, sl[0], sl[1]))
    for (y, lid, d), g in agg.dropna(subset=["Division"]).groupby(["Year", "LeagueID", "Division"]):
        real = g[[(y, r.LeagueName, r.RosterID) in played for r in g.itertuples()]]
        o = real.iloc[0] if len(real) == 1 else g.sort_values(["WO", "PFO"], ascending=False).iloc[0]
        s = g.sort_values(["WS", "PFS"], ascending=False).iloc[0]
        if o.RosterID != s.RosterID:
            flags.append(dict(Year=y, LeagueName=o.LeagueName, Week="", RosterID=o.RosterID, Team=nm(y, o.LeagueName, o.RosterID),
                              Opponent=nm(y, o.LeagueName, s.RosterID), Type="DivisionTitle",
                              Official=f"{o.WO:g}-{o.G - o.WO:g} won the division", Standard=f"{s.WS:g}-{s.G - s.WS:g} ({nm(y, o.LeagueName, s.RosterID)}) leads on standard scoring",
                              Note="Division title stands as played; standard-scoring standings would favor the team named in Opponent"))
    for r in agg[(agg.WO >= agg.G / 2) != (agg.WS >= agg.G / 2)].itertuples():
        flags.append(dict(Year=r.Year, LeagueName=r.LeagueName, Week="", RosterID=r.RosterID, Team=nm(r.Year, r.LeagueName, r.RosterID),
                          Opponent="", Type="BowlLine", Official=f"{r.WO:g}-{r.G - r.WO:g}", Standard=f"{r.WS:g}-{r.G - r.WS:g}",
                          Note="Regular-season record crosses .500 under standard scoring; postseason placement stands as played"))
    f = pd.DataFrame(flags).sort_values(["Year", "LeagueName", "Type", "Week"])
    f.to_csv(OUT_FLAGS, index=False)
    print(f"{len(sc)} team-weeks ({(sc.Delta != 0).sum()} restated); flags: {f.Type.value_counts().to_dict()}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "scripts")
    main()
