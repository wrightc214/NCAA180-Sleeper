"""
poll_bots.py -- the computer voters ("bots"). Each bot ranks every team through a week
(imported, not run). Bot list, names and on/off live in config/poll.json -> bots.

Teams never play outside their league in the regular season, so head-to-head methods
(Colley, Massey, H2H Elo) can't compare leagues. Every bot is built from scores, which
compare across the whole field.

  record     wins (ties = half), then points for            -- the league's Playoff Rank
  allplay    expected wins vs all other teams each week (share outscored, ties half)
  points     total points for
  form       all-play, last 3 weeks weighted 3:2:1
  resume     0.6 x win% + 0.4 x opponents' all-play% (schedule strength that crosses leagues)
  ceiling    average best-possible lineup (MaxPoints) per game -- roster strength
  professor  blend that shifts with the season (config professor): a frozen preseason prior
             (starter value, week-1 projection, dynasty value, last season's final rank), quality (all-play, points per game,
             consistency) and resume (win %, quality wins, conference standing); every measure
             is a percentile across all teams; block weights interpolate between anchor weeks
  redraft    market view of the starting lineup: FantasyCalc redraft value of the best
             legal lineup (roster map LineupRedraft). History has no FantasyCalc data, so
             backtests use Sleeper's projected lineup for the next week as a stand-in.

Missing inputs are bridged (bridge(): straight line between the nearest weeks with data, or
the nearest week's value), flagged ValueSource in the bot file. A bot with no data at all for
the season sits out; the consensus uses whatever bots have data and records BotsUsed.
Points: PointsFor = standard scoring; PointsOfficial (game-time) for the Scoreboard and
standings tiebreaks and Monday Morning QB. Outcomes are always official.

Consensus (BCS computer component) within the pool (all teams, or the playoff field), per
config consensus: each team's best and worst bot rank are dropped and the rest averaged
(BotAvgRank); ComputerPct = (N - BotAvgRank) / (N - 1). method "points" instead gives
size..1 points per bot (classic BCS) and sums after dropping high/low. Order: ComputerPct,
BotAvgRank, then the Standings bot. TopVotes = counted bots ranking the team in the top size.
"""
import os

import pandas as pd

BOT_FUNCS = {}


def bot(name):
    def deco(f):
        BOT_FUNCS[name] = f
        return f
    return deco


# ---------------------------------------------------------------- base table
def base(m, through_week, last_regular=11):
    """Per team-week regular-season rows through the week, with all-play share."""
    upto = min(int(through_week), int(last_regular))
    r = m[(m["Week"] <= upto) & m["Outcome"].isin(["Win", "Loss", "Tie"])].copy()
    r["PointsFor"] = r["PointsFor"].astype(float)
    r["Wv"] = (r["Outcome"] == "Win") * 1.0 + (r["Outcome"] == "Tie") * 0.5
    r["AP"] = r.groupby("Week")["PointsFor"].transform(lambda p: (p.rank(method="average") - 1) / (len(p) - 1))
    return r


def key(df):
    return list(zip(df["LeagueID"], df["RosterID"]))


@bot("record")
def b_record(r, extra):
    g = r.groupby(["LeagueID", "RosterID"]).agg(W=("Wv", "sum"), PF=("PointsOfficial", "sum"))
    return g["W"] * 1e5 + g["PF"]  # wins first, official points break ties = the league's real playoff rank


@bot("allplay")
def b_allplay(r, extra):
    g = r.groupby(["LeagueID", "RosterID"]).agg(A=("AP", "sum"), PF=("PointsFor", "sum"))
    return g["A"] + g["PF"] * 1e-9


@bot("points")
def b_points(r, extra):
    return r.groupby(["LeagueID", "RosterID"])["PointsFor"].sum()


@bot("form")
def b_form(r, extra):
    last = r["Week"].max()
    w = r["Week"].map(lambda x: {0: 3, 1: 2, 2: 1}.get(last - x, 0))
    t = r.assign(x=r["AP"] * w, w=w).groupby(["LeagueID", "RosterID"]).agg(x=("x", "sum"), w=("w", "sum"), A=("AP", "sum"))
    return t["x"] / t["w"] + t["A"] * 1e-6


@bot("resume")
def b_resume(r, extra):
    ap = r.groupby(["LeagueID", "RosterID"])["AP"].mean()
    opp = r[["LeagueID", "OpponentRosterID"]].copy()
    opp["oap"] = [ap.get((a, b)) for a, b in zip(opp["LeagueID"], opp["OpponentRosterID"])]
    r = r.assign(oap=opp["oap"].astype(float))
    g = r.groupby(["LeagueID", "RosterID"]).agg(W=("Wv", "mean"), O=("oap", "mean"), PF=("PointsFor", "sum"))
    return 0.6 * g["W"] + 0.4 * g["O"] + g["PF"] * 1e-9


@bot("ceiling")
def b_ceiling(r, extra):
    mx = extra.get("maxpts")
    if mx is None or mx.empty:
        return None
    upto = r["Week"].max()
    mx = mx[mx["Week"].astype(int) <= upto]
    if mx.empty:
        return None
    return mx.groupby(["LeagueID", "RosterID"])["MaxPoints"].mean()


@bot("redraft")
def b_redraft(r, extra):
    v = extra.get("redraft")
    if v is None or len(v) == 0:
        return None
    return v


@bot("median")
def b_median(r, extra):
    g = r.groupby(["LeagueID", "RosterID"])
    return g["PointsFor"].median() + g["PointsFor"].sum() * 1e-9


@bot("margin")
def b_margin(r, extra):
    """Hammer (margin only, Chris 2026-10-08): per game, win = + margin percentile among that week's
    winning margins (biggest blowout +1, median win +0.5, a squeaker ~0); loss = - the same among
    that week's losing margins; tie = 0. Season value = mean. Margins on game-time (official) scores so they
    agree with the result that stands."""
    pts = "PointsOfficial" if "PointsOfficial" in r.columns else "PointsFor"
    t = r[["LeagueID", "RosterID", "OpponentRosterID", "Week", "Outcome", pts]].copy()
    t[pts] = t[pts].astype(float)
    opp = t.rename(columns={"RosterID": "OpponentRosterID", "OpponentRosterID": "RosterID", pts: "PA"})
    t = t.merge(opp[["LeagueID", "Week", "RosterID", "OpponentRosterID", "PA"]],
                on=["LeagueID", "Week", "RosterID", "OpponentRosterID"], how="left")
    t["M"] = (t[pts] - t["PA"]).abs()
    t["s"] = 0.0
    for res, sign in (("Win", 1), ("Loss", -1)):
        x = t["Outcome"] == res
        p = t[x].groupby("Week")["M"].rank(pct=True, method="average")
        t.loc[x, "s"] = sign * p
    g = t.groupby(["LeagueID", "RosterID"]).agg(S=("s", "mean"), PF=(pts, "sum"))
    return g["S"] + g["PF"] * 1e-9


@bot("efficiency")
def b_efficiency(r, extra):
    mx = extra.get("maxpts")
    if mx is None or mx.empty:
        return None
    mx = mx[mx["Week"].astype(int) <= r["Week"].max()]
    pf = r.groupby(["LeagueID", "RosterID"])["PointsOfficial"].sum()  # lineup calls were made under game-time scoring
    mp = mx.groupby(["LeagueID", "RosterID"])["MaxPoints"].sum()
    return (pf / mp).dropna()


@bot("elo")
def b_elo(r, extra, k=24.0, scale=400.0):
    """All-play Elo: each week every team 'plays' all others; rating moves by actual vs
    expected share outscored. Recent weeks count more because Elo forgets slowly."""
    rating = {}
    for wk, g in r.sort_values("Week").groupby("Week"):
        ks = list(zip(g["LeagueID"], g["RosterID"]))
        pts = g["PointsFor"].to_numpy()
        rt = pd.Series([rating.get(x, 1500.0) for x in ks]).to_numpy()
        exp = (1 / (1 + 10 ** ((rt[None, :] - rt[:, None]) / scale))).sum(axis=1) - 0.5
        act = (pts[:, None] > pts[None, :]).sum(axis=1) + 0.5 * ((pts[:, None] == pts[None, :]).sum(axis=1) - 1)
        n = len(ks) - 1
        for i, x in enumerate(ks):
            rating[x] = rt[i] + k * (act[i] - exp[i]) / n * 10
    return pd.Series(rating)


# ---------------------------------------------------------------- professor
def _pct(s):
    """Percentile rank 0..1 (1 = best) across all teams; ties share the average rank."""
    s = pd.Series(s, dtype=float)
    return ((s.rank(method="average") - 1) / max(len(s) - 1, 1)).fillna(0.0)


def professor_weights(pcfg, games):
    """(prior, quality, resume) shares for `games` played, linear between anchor weeks."""
    anchors = sorted((int(k), v) for k, v in pcfg["weights"].items())
    g = max(anchors[0][0], min(int(games), anchors[-1][0]))
    for (w0, a), (w1, b) in zip(anchors, anchors[1:]):
        if w0 <= g <= w1:
            f = (g - w0) / (w1 - w0) if w1 > w0 else 0
            return [(x + f * (y - x)) / 100 for x, y in zip(a, b)]
    return [x / 100 for x in anchors[-1][1]]


def _quality(r, q):
    t = r.assign(med=r.groupby("Week")["PointsFor"].transform("median"))
    t["above"] = (t["PointsFor"] > t["med"]).astype(float)
    g = t.groupby(["LeagueID", "RosterID"]).agg(ap=("AP", "mean"), ppg=("PointsFor", "mean"), cons=("above", "mean"))
    return q["allplay"] * _pct(g["ap"]) + q["ppg"] * _pct(g["ppg"]) + q["consistency"] * _pct(g["cons"])


@bot("professor")
def b_professor(r, extra):
    pcfg = extra.get("professor_cfg")
    if not pcfg or r.empty:
        return None
    q, rs = pcfg["quality"], pcfg["resume"]
    games = int(r["Week"].max())
    Q = _quality(r, q)
    # quality wins: wins over opponents in the top half of Quality that week (data through that week)
    qwins = pd.Series(0.0, index=Q.index)
    for w in sorted(r["Week"].unique()):
        qw = _quality(r[r["Week"] <= w], q)
        top = set(qw[qw >= qw.median()].index)
        wk = r[(r["Week"] == w) & (r["Wv"] == 1)]
        for a, b, o in zip(wk["LeagueID"], wk["RosterID"], wk["OpponentRosterID"]):
            if (a, o) in top and (a, b) in qwins.index:
                qwins[(a, b)] += 1
    g = r.groupby(["LeagueID", "RosterID"]).agg(W=("Wv", "mean"), PF=("PointsOfficial", "sum"))
    g["k"] = g["W"] * 1e5 + g["PF"]  # the real conference standing (official tiebreak)
    g["lr"] = g.groupby(level="LeagueID")["k"].rank(ascending=False, method="min")
    g["n"] = g.groupby(level="LeagueID")["W"].transform("size")
    g["stand"] = (g["n"] - g["lr"]) / (g["n"] - 1).clip(lower=1)
    R = rs["win_pct"] * _pct(g["W"]) + rs["quality_wins"] * _pct(qwins.reindex(g.index).fillna(0)) \
        + rs["standing"] * _pct(g["stand"])
    prior = extra.get("prior") or {}
    wp, wq, wr = professor_weights(pcfg, games)
    if prior:
        pr = pd.Series([prior.get(k) for k in g.index], index=g.index, dtype=float)
        P = _pct(pr.fillna(pr.median()))
    else:  # no frozen prior for this season: its share goes to the other blocks pro rata
        P = pd.Series(0.0, index=g.index)
        tot = max(wq + wr, 1e-9)
        wq, wr, wp = wq + wp * wq / tot, wr + wp * wr / tot, 0.0
    return wp * P + wq * Q.reindex(g.index) + wr * R


PRIOR_FILES = ("data/PollPrior_Season.csv", "data/PollPrior_Historic.csv")


def load_prior(year):
    """{(LeagueID, RosterID): Prior} for that year (Season file, else Historic), else {}."""
    for f in PRIOR_FILES:
        if os.path.exists(f):
            p = pd.read_csv(f, dtype=str)
            p = p[(p["Year"] == str(year)) & p["Prior"].notna()]
            if len(p):
                return {(a, b): float(v) for a, b, v in zip(p["LeagueID"], p["RosterID"], p["Prior"])}
    return {}


# ---------------------------------------------------------------- missing data (Chris 2026-10-08)
def bridge(by_week, week):
    """Fill a weekly input that is missing for `week` (or for some teams that week).
    by_week = {week: {key: value}}. Per team: actual if present; else straight line between
    the nearest weeks before and after; else the nearest week on either side (carried).
    A live run never has later weeks, so it carries the last known value forward; a rebuild
    of past weeks can carry the first known value back. Returns ({key: value}, {key: source})."""
    weeks = sorted(w for w, d in by_week.items() if d)
    if not weeks:
        return {}, {}
    keys = set().union(*(by_week[w].keys() for w in weeks))
    vals, src = {}, {}
    for k in keys:
        have = [w for w in weeks if by_week[w].get(k) is not None]
        if not have:
            continue
        if week in have:
            vals[k], src[k] = by_week[week][k], "actual"
            continue
        lo = [w for w in have if w < week]
        hi = [w for w in have if w > week]
        if lo and hi:
            a, b = lo[-1], hi[0]
            va, vb = by_week[a][k], by_week[b][k]
            vals[k], src[k] = va + (vb - va) * (week - a) / (b - a), "interpolated"
        else:
            w = lo[-1] if lo else hi[0]
            vals[k], src[k] = by_week[w][k], "carried"
    return vals, src


# ---------------------------------------------------------------- ranking
RESULT_BOTS = {"record", "resume", "professor", "margin"}  # use win/loss; never see weeks past the regular season


def bot_ranks(cfg, m, through_week, extra=None, keys=None, points_through=None):
    """DataFrame: LeagueID, RosterID, <bot>_val, <bot> (rank 1..n, ties min) for enabled bots
    that have data. `keys` = every (LeagueID, RosterID) to rank (missing values rank last).
    points_through: let score-only bots see later weeks (e.g. 12 = CCG week points); the
    record/resume bots always stop at the regular season (later opponents are fictional)."""
    extra = dict(extra or {})
    extra.setdefault("professor_cfg", cfg.get("professor"))
    last = int(cfg.get("last_regular_week", 11))
    full = base(m, points_through or through_week, max(last, int(points_through or 0)))
    r = full[full["Week"] <= min(int(through_week), last)]
    if r.empty:
        return pd.DataFrame(), []
    keys = keys or sorted(set(key(r)))
    out = pd.DataFrame(keys, columns=["LeagueID", "RosterID"])
    used = []
    for b in cfg["bots"]:
        if not b.get("enabled", True):
            continue
        s = BOT_FUNCS[b["id"]](r if b["id"] in RESULT_BOTS else full, extra)
        if s is None:
            continue
        s = pd.Series(s)
        vals = [s.get(k) for k in keys]
        out[b["id"] + "_val"] = vals
        out[b["id"]] = out[b["id"] + "_val"].astype(float).rank(ascending=False, method="min", na_option="bottom").astype(int)
        used.append(b["id"])
    return out, used


def consensus(cfg, ranks, used, size, pool=None):
    """BCS-style computer component over `pool` (set of keys) or everyone."""
    d = ranks.copy()
    if pool is not None:
        d = d[[k in pool for k in zip(d["LeagueID"], d["RosterID"])]].copy()
        for b in used:  # re-rank inside the pool
            d[b] = d[b + "_val"].astype(float).rank(ascending=False, method="min", na_option="bottom").astype(int)
    drop = bool(cfg.get("consensus", {}).get("drop_high_low", True)) and len(used) >= 3
    pts = d[used].apply(lambda c: (size + 1 - c).clip(lower=0))
    rk = d[used]
    if drop:
        keep_pts = pts.sum(axis=1) - pts.max(axis=1) - pts.min(axis=1)
        keep_rk = (rk.sum(axis=1) - rk.max(axis=1) - rk.min(axis=1)) / (len(used) - 2)
        n = len(used) - 2
    else:
        keep_pts, keep_rk, n = pts.sum(axis=1), rk.mean(axis=1), len(used)
    d["ComputerPct"] = (keep_pts / (n * size)).round(4)
    d["BotAvgRank"] = keep_rk.round(2)
    d["BotHigh"] = rk.min(axis=1)
    d["BotLow"] = rk.max(axis=1)
    d["BotFirst"] = (rk == 1).sum(axis=1)
    top = (rk <= size).sum(axis=1)
    if drop:  # votes from bots that count: drop the best and worst if they were top-`size`
        top = top - (rk.min(axis=1) <= size).astype(int) - ((rk.max(axis=1) <= size) & (top > 1)).astype(int)
    d["TopVotes"] = top.clip(lower=0)
    d["BotsUsed"] = len(used)
    method = cfg.get("consensus", {}).get("method", "points")
    if method == "zscore":
        # Magnitude: each bot's value standardized within the pool (gaps count, not just order).
        z = pd.DataFrame({b: (d[b + "_val"].astype(float) - d[b + "_val"].astype(float).mean())
                          / d[b + "_val"].astype(float).std(ddof=0) for b in used}, index=d.index).fillna(-3.0)
        z = z.clip(-3, 3)
        zs = (z.sum(axis=1) - z.max(axis=1) - z.min(axis=1)) / (len(used) - 2) if drop else z.mean(axis=1)
        d["ZScore"] = zs.round(4)
        d["ComputerPct"] = ((zs + 3) / 6).round(4)
    if method == "avg_rank":
        # Score from the trimmed average full rank: 1.0 for an average of 1, 0 at pool size.
        n_pool = len(d)
        d["ComputerPct"] = ((n_pool - d["BotAvgRank"]) / (n_pool - 1)).round(4)
    tie = d["record"] if "record" in used else 0
    d = d.assign(_t=tie).sort_values(["ComputerPct", "BotAvgRank", "_t"], ascending=[False, True, True]).drop(columns="_t")
    return d.reset_index(drop=True)


# ---------------------------------------------------------------- inputs
def current_extra(year, through_week):
    """Inputs for the live season: MaxPoints_Season.csv, RosterValues_Season.csv."""
    extra = {}
    if os.path.exists("data/MaxPoints_Season.csv"):
        mx = pd.read_csv("data/MaxPoints_Season.csv", dtype=str)
        mx = mx[mx["Year"] == str(year)].copy()
        mx["Week"] = mx["Week"].astype(int)
        mx["MaxPoints"] = mx["MaxPoints"].astype(float)
        extra["maxpts"] = mx
    if os.path.exists("data/RosterValues_Season.csv"):
        rv = pd.read_csv("data/RosterValues_Season.csv", dtype=str)
        rv = rv[(rv["Year"] == str(year)) & rv["LineupRedraft"].notna()]
        by_week = {int(w): {(a, b): float(v) for a, b, v in zip(g["LeagueID"], g["RosterID"], g["LineupRedraft"])}
                   for w, g in rv.groupby("Week")}
        vals, src = bridge(by_week, int(through_week))
        if vals:
            extra["redraft"], extra["redraft_src"] = vals, src
    extra["prior"] = load_prior(year)
    return extra


BACKFILL = os.environ.get("POLL_BACKFILL_DIR", "data/backfill")


def history_extra(year, through_week, slots=None):
    """Inputs for a past season, when the history-backfill files exist (else {}):
    ceiling from PlayerPoints_<year>.csv.gz (+ PlayerPositions_All.csv); redraft stand-in
    = projected starters' total for week through_week+1 from ProjStarters_<year>.csv.gz."""
    from max_points import best_lineup, DEFAULT_SLOTS, POS_ALIAS
    extra = {}
    pp = os.path.join(BACKFILL, f"PlayerPoints_{year}.csv.gz")
    pos_f = os.path.join(BACKFILL, "PlayerPositions_All.csv")
    if os.path.exists(pp) and os.path.exists(pos_f):
        cache = os.path.join("work", "poll", f"maxpts_{year}.csv")
        if os.path.exists(cache):
            mx = pd.read_csv(cache, dtype={"LeagueID": str, "RosterID": str})
        else:
            p = pd.read_csv(pp, dtype=str)
            pos = pd.read_csv(pos_f, dtype=str).set_index("PlayerID")["Position"].replace(POS_ALIAS)
            p["pos"] = p["PlayerID"].map(pos)
            p.loc[p["pos"].isna() & ~p["PlayerID"].str.isdigit(), "pos"] = "DEF"  # team IDs are defenses
            p["pts"] = p["Points"].astype(float)
            rows = []
            for (lid, wk, rid), g in p.groupby(["LeagueID", "Week", "RosterID"]):
                sl = (slots or {}).get(lid, DEFAULT_SLOTS + ["K", "DEF"])
                rows.append({"LeagueID": lid, "Week": int(wk), "RosterID": rid,
                             "MaxPoints": best_lineup(list(zip(g["pts"], g["pos"])), sl)})
            mx = pd.DataFrame(rows)
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            mx.to_csv(cache, index=False)
        extra["maxpts"] = mx
    ps = os.path.join(BACKFILL, f"ProjStarters_{year}.csv.gz")
    if os.path.exists(ps):
        if ("proj", year) not in _CACHE:
            p = pd.read_csv(ps, dtype=str)
            p["v"] = p["ProjPts"].astype(float)
            _CACHE[("proj", year)] = {int(w): g.groupby(["LeagueID", "RosterID"])["v"].sum().to_dict()
                                      for w, g in p.groupby("Week")}
        vals, src = bridge(_CACHE[("proj", year)], int(through_week) + 1)
        if vals:
            extra["redraft"], extra["redraft_src"] = vals, src
    extra["prior"] = load_prior(year)
    return extra


_CACHE = {}


def league_slots(year):
    import poll_common as pc
    lg = pc.leagues_all()
    lg = lg[lg["Year"] == str(year)]
    return {r.LeagueID: [s for s in r.RosterPositions.split(",") if s not in ("BN", "IR", "TAXI")]
            for r in lg.itertuples() if isinstance(r.RosterPositions, str)}


# ---------------------------------------------------------------- final poll (after the postseason)
# Postseason games = every game that needed a lineup: CCG, Playoff, Bowl, every NIT round.
# One lineup = one game. Result = share of rivals outscored (1/0 head-to-head; NIT groups 0..1).
# Normalized games table: LeagueID, RosterID, Week, Event (CCG/Playoff/Bowl/NIT), PlayoffRound
# (1..5 for Playoff, else 0), Res, PF, Opp (list of (LeagueID, RosterID)).

GAME_COLS = ["LeagueID", "RosterID", "Week", "Event", "PlayoffRound", "Res", "PF", "PFOff", "Group", "Opp"]
# Event PlayoffThird = a third-place game (2020): counts as a game; winner gets bump.PlayoffThird (= bowl).
# Group = more than two teams in the game (NIT groups, 2020 playoff round 1): result = share outscored.
ALIASES = "data/TeamAliases_Historic.csv"  # OldName, LeagueName, RosterID, FirstYear, LastYear
# Only years backed by evidence (score match). Idaho = MW roster 7 verified 2022-2025; Fresno State from 2026.


def name_lookup(year):
    """{normalized school name: (LeagueID, RosterID)} for a season, incl. historical aliases."""
    import poll_common as pc
    t = pc.teams(year)
    by = {r.Key: (r.LeagueID, r.RosterID) for r in t.itertuples()}
    by.update({pc.full_key(r.Team): (r.LeagueID, r.RosterID) for r in t.itertuples()})
    if os.path.exists(ALIASES):
        ids = pc.league_ids(year)
        a = pd.read_csv(ALIASES, dtype=str, encoding="utf-8-sig")
        for r in a.itertuples():
            if int(r.FirstYear) <= int(year) <= int(r.LastYear) and r.LeagueName.upper() in ids:
                by.setdefault(pc.norm(r.OldName), (ids[r.LeagueName.upper()], r.RosterID))
    return by


def postseason_historic(year):
    """Games from data/Postseason_Historic.csv (one row per game; NIT groups 'A | B | C').
    Missing scores are filled from each team's own PointsFor that week (real in Sleeper);
    a recorded winner that disagrees with those points is reported, not overridden."""
    import poll_common as pc
    p = pd.read_csv("data/Postseason_Historic.csv", dtype=str)
    p = p[p["Season"] == str(year)]
    by = name_lookup(year)
    m = pc.matchups(year)
    own_pts = {(a, b, int(w)): float(x) for a, b, w, x in zip(m["LeagueID"], m["RosterID"], m["Week"], m["PointsFor"])}
    own_off = {(a, b, int(w)): float(x) for a, b, w, x in zip(m["LeagueID"], m["RosterID"], m["Week"], m["PointsOfficial"])}
    rows, miss, unscored, mismatch = [], set(), [], []
    for r in p.itertuples():
        wk = int(r.Week) if isinstance(r.Week, str) and r.Week.strip() else 12 + int(r.Round)
        teams = [x.strip() for x in str(r.TeamA).split("|")]
        if isinstance(r.TeamB, str) and r.TeamB.strip():
            teams.append(r.TeamB.strip())
        if len(teams) < 2:
            continue  # single-team row (no game)
        keys = [pc.find(by, x) for x in teams]
        try:
            pts = [float(x) for x in str(r.ScoreA).split("|")]
            if isinstance(r.ScoreB, str) and r.ScoreB.strip():
                pts.append(float(r.ScoreB))
        except ValueError:
            pts = []
        # official (game-time) points where standard scoring restated them; else = standard
        off = list(pts)
        oa, ob = getattr(r, "OfficialScoreA", None), getattr(r, "OfficialScoreB", None)
        if isinstance(oa, str) and oa.strip():
            xs = [x.strip() for x in oa.split("|")]
            off[:len(xs)] = [float(x) if x else p for x, p in zip(xs, off)]
        if isinstance(ob, str) and ob.strip() and len(off) == len(teams):
            off[-1] = float(ob)
        if len(pts) != len(teams):
            # Scores not recorded: each team's own points that week are real in Sleeper.
            pts = [own_pts.get((k[0], k[1], wk)) if k else None for k in keys]
            off = [own_off.get((k[0], k[1], wk)) if k else None for k in keys]
            if any(x is None for x in pts):
                unscored.append(f"{r.Event} wk{wk} {' v '.join(teams)}")
                continue
            if isinstance(r.Winner, str) and r.Winner.strip() and len(teams) == 2:
                wi = [pc.norm(x) for x in teams].index(pc.norm(r.Winner)) if pc.norm(r.Winner) in [pc.norm(x) for x in teams] else None
                if wi is not None and pts[wi] < pts[1 - wi]:
                    mismatch.append(f"{r.Event} wk{wk} {r.Winner} (Sleeper points disagree)")
        miss |= {x for x, k in zip(teams, keys) if k is None}
        for i, k in enumerate(keys):
            if k is None:
                continue
            others = [j for j in range(len(teams)) if j != i]
            res = sum((pts[i] > pts[j]) + 0.5 * (pts[i] == pts[j]) for j in others) / len(others)
            third = r.Event == "Playoff" and "third" in str(r.RoundName).lower()
            rows.append({"LeagueID": k[0], "RosterID": k[1], "Week": wk,
                         "Event": "PlayoffThird" if third else r.Event,
                         "PlayoffRound": int(r.Round) if r.Event == "Playoff" and not third else 0,
                         "Res": res, "PF": pts[i], "PFOff": off[i] if off[i] is not None else pts[i],
                         "Group": len(teams) > 2, "Opp": [keys[j] for j in others if keys[j]]})
    if unscored:
        print(f"WARNING {year}: {len(unscored)} postseason game(s) with no score anywhere, skipped: {unscored[:5]}")
    if mismatch:
        print(f"WARNING {year}: recorded winner disagrees with Sleeper points: {mismatch}")
    return pd.DataFrame(rows, columns=GAME_COLS), miss


def postseason_season(year):
    """Games from data/Postseason_Season.csv, the live per-team format (one row per team per
    game, Status = Final). Contract for every postseason script (CCG and bowls follow it; NIT
    and the playoff bracket must too):
      Year, Round (CCG / Bowl / NIT / Playoff), Week, LeagueID, RosterID, Points, Status,
      OpponentRosterID + OpponentLeague (name; blank = same league) + OpponentPoints --
      for a group game, '|'-separated lists of every group rival --
      and PlayoffRound (1..5) on Playoff rows.
    """
    import poll_common as pc
    path = "data/Postseason_Season.csv"
    cols = GAME_COLS
    if not os.path.exists(path) or os.path.getsize(path) < 10:
        return pd.DataFrame(columns=cols)
    p = pd.read_csv(path, dtype=str).fillna("")
    p = p[(p["Year"] == str(year)) & (p["Status"] == "Final")]
    ids = pc.league_ids(year)
    rows = []
    for r in p.itertuples():
        opp_r = [x.strip() for x in str(r.OpponentRosterID).split("|")]
        opp_l = [x.strip() for x in str(getattr(r, "OpponentLeague", "")).split("|")]
        opp_p = [float(x) for x in str(r.OpponentPoints).split("|") if x.strip()]
        opp_l += [""] * (len(opp_r) - len(opp_l))
        keys = [(ids.get(lg.upper(), r.LeagueID) if lg else r.LeagueID, rid) for rid, lg in zip(opp_r, opp_l)]
        me = float(r.Points)
        res = sum((me > o) + 0.5 * (me == o) for o in opp_p) / len(opp_p) if opp_p else None
        if res is None:
            continue
        rows.append({"LeagueID": r.LeagueID, "RosterID": r.RosterID, "Week": int(r.Week), "Event": r.Round,
                     "PlayoffRound": int(getattr(r, "PlayoffRound", 0) or 0) if r.Round == "Playoff" else 0,
                     "Res": res, "PF": me, "PFOff": me, "Group": len(opp_p) > 1, "Opp": keys})
    return pd.DataFrame(rows, columns=cols)


def final_ranks(cfg, m, extra, keys, games):
    """Bots for the final poll. Vegas, Bandwagon, Headliner, Bagman, Professor: frozen at the
    regular season. Scoreboard, Bracketologist, Monday Morning QB: regular season + postseason games."""
    last = int(cfg.get("last_regular_week", 11))
    rk, used = bot_ranks(cfg, m, last, extra, keys)
    reg = base(m, last, last)
    ap = reg.groupby(["LeagueID", "RosterID"])["AP"].mean()
    rr = reg.groupby(["LeagueID", "RosterID"]).agg(W=("Wv", "sum"), N=("Wv", "size"), PF=("PointsFor", "sum"),
                                                   PFO=("PointsOfficial", "sum"))
    ro = reg.assign(o=[ap.get((a, b)) for a, b in zip(reg["LeagueID"], reg["OpponentRosterID"])]) \
        .groupby(["LeagueID", "RosterID"])["o"].agg(["sum", "count"])
    g = games.copy()
    gp = g.groupby(["LeagueID", "RosterID"]).agg(W=("Res", "sum"), N=("Res", "size"), PF=("PF", "sum"), PFO=("PFOff", "sum"))
    g["o"] = g["Opp"].map(lambda ks: sum(ap.get(k, 0.5) for k in ks) / len(ks) if ks else None)
    go = g.dropna(subset=["o"]).groupby(["LeagueID", "RosterID"])["o"].agg(["sum", "count"])
    mx = extra.get("maxpts", pd.DataFrame(columns=["LeagueID", "RosterID", "Week", "MaxPoints"]))
    mx = mx.assign(Week=mx["Week"].astype(int))
    mx_reg = mx[mx["Week"] <= last].groupby(["LeagueID", "RosterID"])["MaxPoints"].sum()
    played = set(zip(g["LeagueID"], g["RosterID"], g["Week"].astype(int)))
    mx_post = mx[[(a, b, w) in played for a, b, w in zip(mx["LeagueID"], mx["RosterID"], mx["Week"])]] \
        .groupby(["LeagueID", "RosterID"])["MaxPoints"].sum()

    def get(df, k, c):
        return df.loc[k, c] if k in df.index else 0

    vals = {}
    for k in zip(rk["LeagueID"], rk["RosterID"]):
        if k not in rr.index:
            continue
        W, N = rr.loc[k, "W"] + get(gp, k, "W"), rr.loc[k, "N"] + get(gp, k, "N")
        PF = rr.loc[k, "PF"] + get(gp, k, "PF")
        PFO = rr.loc[k, "PFO"] + get(gp, k, "PFO")
        osum, ocnt = ro.loc[k, "sum"] + get(go, k, "sum"), ro.loc[k, "count"] + get(go, k, "count")
        mxt = mx_reg.get(k, 0) + mx_post.get(k, 0)
        vals[k] = {"record": W / N + PFO * 1e-9, "resume": 0.6 * W / N + 0.4 * osum / ocnt + PF * 1e-12,
                   "efficiency": PFO / mxt if mxt else None}
    for b in ("record", "resume", "efficiency"):
        if b in used:
            rk[b + "_val"] = [vals.get(k, {}).get(b) for k in zip(rk["LeagueID"], rk["RosterID"])]
            rk[b] = rk[b + "_val"].astype(float).rank(ascending=False, method="min", na_option="bottom").astype(int)
    return rk, used


def final_bumps(cfg, games):
    """{key: bump} on the standardized scale: per postseason win, by event (x share for groups);
    playoff wins escalate by round."""
    fc = cfg["polls"]["Final"]
    bump = fc.get("bump", {})
    sched = bump.get("Playoff", [])
    # Rounds count back from the final, so a shorter bracket (2019: 4 rounds) gives the title
    # game the title bump and drops the earliest rounds' bumps (config bump.align = "final").
    top = int(games.loc[games["Event"] == "Playoff", "PlayoffRound"].max() or 0) if len(games) else 0
    shift = len(sched) - top if bump.get("align", "final") == "final" else 0
    out = {}
    for r in games.itertuples():
        k = (r.LeagueID, r.RosterID)
        if r.Event == "Playoff":
            i = r.PlayoffRound + shift
            b = sched[i - 1] if 0 < i <= len(sched) else 0.0
            b = b * float(r.Res) if r.Group else (b if r.Res == 1.0 else 0.0)  # groups: x share outscored
        else:
            b = float(bump.get(r.Event, 0.0)) * float(r.Res)
        out[k] = out.get(k, 0.0) + b
    return out


def final_four(order, games):
    """Backstop: a semifinal or final winner sits directly above the team it beat (winner raised)."""
    pl = games[games["Event"] == "Playoff"]
    if pl.empty:
        return order
    top = int(pl["PlayoffRound"].max())
    order = list(order)
    for rnd in (top - 1, top):
        for r in pl[(pl["PlayoffRound"] == rnd) & (pl["Res"] == 1.0)].itertuples():
            w = (r.LeagueID, r.RosterID)
            for lo in r.Opp:
                if w in order and lo in order and order.index(w) > order.index(lo):
                    order.remove(w)
                    order.insert(order.index(lo), w)
    return order
