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
  redraft    market view of the starting lineup: FantasyCalc redraft value of the best
             legal lineup (roster map LineupRedraft). History has no FantasyCalc data, so
             backtests use Sleeper's projected lineup for the next week as a stand-in.

A bot with no input for that week (e.g. ceiling before bench points exist) sits out;
the consensus uses whatever bots have data and records BotsUsed.

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
    g = r.groupby(["LeagueID", "RosterID"]).agg(W=("Wv", "sum"), PF=("PointsFor", "sum"))
    return g["W"] * 1e5 + g["PF"]  # wins first, points break ties (PF < 1e5)


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


@bot("efficiency")
def b_efficiency(r, extra):
    mx = extra.get("maxpts")
    if mx is None or mx.empty:
        return None
    mx = mx[mx["Week"].astype(int) <= r["Week"].max()]
    pf = r.groupby(["LeagueID", "RosterID"])["PointsFor"].sum()
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


# ---------------------------------------------------------------- ranking
RESULT_BOTS = {"record", "resume"}  # use win/loss; never see weeks past the regular season


def bot_ranks(cfg, m, through_week, extra=None, keys=None, points_through=None):
    """DataFrame: LeagueID, RosterID, <bot>_val, <bot> (rank 1..n, ties min) for enabled bots
    that have data. `keys` = every (LeagueID, RosterID) to rank (missing values rank last).
    points_through: let score-only bots see later weeks (e.g. 12 = CCG week points); the
    record/resume bots always stop at the regular season (later opponents are fictional)."""
    extra = extra or {}
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
    if cfg.get("consensus", {}).get("method", "points") == "avg_rank":
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
        rv = rv[(rv["Year"] == str(year)) & (rv["Week"].astype(int) <= int(through_week))]
        if len(rv):
            rv = rv[rv["Week"].astype(int) == rv["Week"].astype(int).max()]
            extra["redraft"] = {(a, b): float(v) for a, b, v in zip(rv["LeagueID"], rv["RosterID"], rv["LineupRedraft"])}
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
        p = pd.read_csv(ps, dtype=str)
        p = p[p["Week"].astype(int) == int(through_week) + 1]
        if len(p):
            s = p.assign(v=p["ProjPts"].astype(float)).groupby(["LeagueID", "RosterID"])["v"].sum()
            extra["redraft"] = s.to_dict()
    return extra


def league_slots(year):
    lg = pd.read_csv("data/LeagueIDs_AllYears.csv", dtype=str)
    lg = lg[lg["Year"] == str(year)]
    return {r.LeagueID: [s for s in r.RosterPositions.split(",") if s not in ("BN", "IR", "TAXI")]
            for r in lg.itertuples() if isinstance(r.RosterPositions, str)}
