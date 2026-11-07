"""
postseason_odds.py -- postseason odds + the week's most impactful games (Chris, 2026-11-07).

Replaces "every team scores its average" with probabilities. The rest of the regular season, the
conference championships and the playoff are simulated SIMS times; every run goes through a fast
copy of the real selection rules (same config):
  division winners -> CCG (winner = auto bid) -> 17 at-large by the tiebreakers (win %, points for,
  points against) -> bowl pool (min_wins, one bump_wins team for an even count, bowl order = poll
  rank - poll_spots_per_win x wins, capped at the bowl count) -> Prestige (rank fill, pairs avoid same
  league / recent meetings) -> Marquee (one seat per league: best remaining division leader, then
  bowl order) -> Showcase/Opening = the rest of the pool; NIT = everyone else. Title odds: a 32-team
  bracket on projected seeds (latest consensus poll score + seed_per_win per remaining win -
  seed_per_loss per loss, as bowl_projection.py), 1v32 ... no reseeding.
The fast rules are checked against the real engine (bowl_projection.project) in
tests/test_postseason_odds.py.

Scoring model (standard scoring):
  upcoming week   each team's frozen Tuesday projection (MatchupProjections_Current) +- SPREAD
  later weeks     the team's weekly mean and spread so far, shrunk toward the league-wide values
                  (shrink_games pseudo-games), Normal.
Columns: CCG (berth), Playoff, Bowl (non-playoff bowl), Prestige, Marquee (both part of Bowl), NIT,
Natty (wins the National Championship). Playoff + Bowl + NIT = 100%.
Clinched / Out are PROVEN, never simulated (a 0-in-10,000 team isn't necessarily out):
  CCG     clinched: fewest possible wins > every division rival's most; out: most < a rival's fewest
  Playoff clinched: CCG clinched-and-... no -- at most 16 other teams can reach its fewest wins;
          out: CCG out and 32+ teams are sure to finish with more wins
  Bowl    out: playoff clinched, or most possible wins < bump_wins
  NIT     out: playoff clinched;  Natty out: playoff out
Leverage: for each team playing this week, P(outcome | win) - P(outcome | loss), read off the same
runs. Games ranked by the biggest swing for either team.

  python scripts/postseason_odds.py [--year Y] [--sims N] [--seed S]
Writes reports/postseason/odds.json (+ odds-wkNN.json). Settings: config postseason.odds.
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowls as B  # noqa: E402
import league_config as lcfg  # noqa: E402

OUT_DIR = "reports/postseason"
COLS = ["CCG", "Playoff", "Bowl", "Prestige", "Marquee", "NIT", "Natty"]
DEFAULTS = {"sims": 10000, "shrink_games": 4, "seed": 2026, "top_games": 8}


def settings():
    c = dict(DEFAULTS)
    c.update(lcfg.cfg()["postseason"].get("odds", {}))
    return c


def key(t):
    return (str(t["LeagueID"]), str(t["RosterID"]).replace(".0", ""))


# ------------------------------------------------------------------ inputs
def inputs(year):
    st = ps.standings(year).reset_index(drop=True)
    keys = [key(r) for r in st.to_dict("records")]
    idx = {k: i for i, k in enumerate(keys)}
    reg = ps.regular_games(year)
    done = sorted(ps.completed_weeks(year))
    after = max([w for w in done if w <= ps.last_regular_week()], default=0)
    m = ps._matchups(year)
    rem = m[m["Week"].between(after + 1, ps.last_regular_week())]
    games, seen = [], set()
    for r in rem.itertuples():
        a = (str(r.LeagueID), str(r.RosterID))
        b = (str(r.LeagueID), str(r.OpponentRosterID).replace(".0", ""))
        g = (int(r.Week), frozenset((a, b)))
        if g in seen or a not in idx or b not in idx:
            continue
        seen.add(g)
        games.append((int(r.Week), idx[a], idx[b]))
    return st, keys, idx, reg, after, games


def model(year, st, keys, idx, reg, after, shrink):
    """(mu, sd) per team for later weeks + {(week, i): mu} for the upcoming week's projections."""
    x = reg.assign(k=list(zip(reg["LeagueID"].astype(str), reg["RosterID"].astype(str))))
    g_mu = float(x["PF"].mean())
    within = x.groupby("k")["PF"].var(ddof=1)
    g_var = float(within.mean())
    mu, sd = np.full(len(keys), g_mu), np.full(len(keys), math.sqrt(g_var))
    for k, grp in x.groupby("k"):
        if k not in idx:
            continue
        n, mean, var = len(grp), float(grp["PF"].mean()), float(grp["PF"].var(ddof=1)) if len(grp) > 1 else g_var
        mu[idx[k]] = (n * mean + shrink * g_mu) / (n + shrink)
        sd[idx[k]] = math.sqrt((max(n - 1, 0) * var + shrink * g_var) / (max(n - 1, 0) + shrink))
    proj = {}
    f = "data/MatchupProjections_Current.csv"
    if os.path.exists(f):
        c = pd.read_csv(f, dtype=str, keep_default_na=False)
        c = c[(c["Year"] == str(year)) & (c["Week"] == str(after + 1))]
        for r in c.itertuples():
            k = (str(r.LeagueID), str(r.RosterID))
            if k in idx and r.Proj not in ("", "nan"):
                proj[(after + 1, idx[k])] = float(r.Proj)
    return mu, sd, proj


def poll(year):
    """(rank array for the bowl order, consensus score array for seeds) from the latest poll."""
    ranks, _ = B.poll_ranks(year, lcfg.cfg()["postseason"]["bowls"].get("rank", {}).get("poll_type", "BotConsensus"))
    import bowl_projection as bp
    sc, _ = bp.poll_scores(year)
    return ranks, sc


def bracket_order(n):
    order = [1, 2]
    while len(order) < n:
        size = len(order) * 2
        order = [x for s in order for x in (s, size + 1 - s)]
    return order


# ------------------------------------------------------------------ the rules (one run)
class Rules:
    """Fast copy of the selection rules for one set of final regular-season results."""

    def __init__(self, year, st, keys):
        _, cfg = ps.config()
        self.cfg, self.bc, self.pc = cfg, cfg["bowls"], cfg["playoff"]
        self.keys = keys
        self.n = len(keys)
        self.league = np.array([str(x) for x in st["LeagueID"]])
        self.lname = [str(x).strip() for x in st["LeagueName"]]
        self.div = {}
        for i, (l, d) in enumerate(zip(st["LeagueID"], st["Division"])):
            self.div.setdefault((str(l), str(d)), []).append(i)
        self.leagues = {}
        for (l, d), ix in self.div.items():
            self.leagues.setdefault(l, []).append(np.array(ix))
        ranks, sc = poll(year)
        worst = max(ranks.values()) + 1 if ranks else 999
        self.prank = np.array([ranks.get(k, worst) for k in keys], dtype=float)
        self.pscore = np.array([sc.get(k, (-99, 999))[0] for k in keys])
        self.prk2 = np.array([sc.get(k, (-99, 999))[1] for k in keys])
        met, _, _ = B.history(year, self.bc)
        self.met = met
        self.slot = [(self.lname[i], keys[i][1]) for i in range(self.n)]
        self.n_bowls = len(B.bowl_list(self.bc))
        tiers = {t["fill"]: t for t in self.bc["tiers"]}
        self.n_prestige = len(tiers["rank"]["bowls"]) if "rank" in tiers else 0
        self.n_marquee = len(tiers["marquee"]["bowls"]) if "marquee" in tiers else 0
        self.field = int(self.pc["field_size"])

    def order(self, W, PF, PA, among):
        """Indices in `among`, best first: win % (equal games -> wins), points for, points against."""
        among = np.asarray(among)
        return among[np.lexsort((-PA[among], -PF[among], -W[among]))]

    def run(self, W, PF, PA, ccg_score, rem_w, rem_l):
        """Outcome sets for one run. ccg_score: score each team would post in CCG week."""
        n = self.n
        ccg, aq, divrank = set(), set(), np.zeros(n, dtype=int)
        for l, divs in self.leagues.items():
            champs = []
            for ix in divs:
                o = self.order(W, PF, PA, ix)
                divrank[o] = np.arange(1, len(o) + 1)
                champs.append(int(o[0]))
            ccg.update(champs)
            if len(champs) == 2:
                a, b = champs
                win = a if ccg_score[a] > ccg_score[b] else b if ccg_score[b] > ccg_score[a] else a
                aq.add(win)
                if win == a:
                    rem_w[a] += 1; rem_l[b] += 1  # noqa: E702
                else:
                    rem_w[b] += 1; rem_l[a] += 1  # noqa: E702
        rest = [i for i in range(n) if i not in aq]
        at = self.order(W, PF, PA, rest)[: self.field - len(aq)]
        playoff = aq | set(int(x) for x in at)
        non = [i for i in range(n) if i not in playoff]
        rec = self.order(W, PF, PA, non)  # record order
        pool = [int(i) for i in rec if W[i] >= self.bc["min_wins"]]
        if len(pool) % 2:
            bump = [int(i) for i in rec if W[i] == self.bc["bump_wins"]][: int(self.bc.get("max_bumps", 1))]
            pos = {int(i): p for p, i in enumerate(rec)}
            pool = sorted(pool + bump, key=lambda i: pos[i])
        x = float(self.bc.get("rank", {}).get("poll_spots_per_win", 25))
        pos = {i: p for p, i in enumerate(pool)}
        if self.bc.get("rank", {}).get("method", "record") == "poll_per_win":
            pool.sort(key=lambda i: (self.prank[i] - x * W[i], pos[i]))
        pool = pool[: 2 * self.n_bowls]
        if len(pool) % 2:
            pool = pool[:-1]
        left = list(pool)
        prestige = set()
        for _ in range(min(self.n_prestige, len(left) // 2)):
            s0 = left[0]
            mate = next((y for y in left[1:] if self.league[y] != self.league[s0]
                         and frozenset((self.slot[s0], self.slot[y])) not in self.met), None)
            if mate is None:
                continue
            prestige.update((s0, mate))
            left = [t for t in left if t not in (s0, mate)]
        top = {}
        for t in left:
            k = (self.league[t], self._div_of(t))
            top[k] = min(top.get(k, 99), divrank[t])
        order_ix = {t: p for p, t in enumerate(left)}
        seat_order = sorted(left, key=lambda t: (divrank[t] != top[(self.league[t], self._div_of(t))], order_ix[t]))
        nm = 2 * self.n_marquee
        picks, seen = [], set()
        for t in seat_order:
            if self.league[t] not in seen:
                picks.append(t)
                seen.add(self.league[t])
        picks = picks[:nm]
        for t in left:
            if len(picks) >= nm:
                break
            if t not in picks:
                picks.append(t)
        if len(picks) % 2:
            picks = picks[:-1]
        bowl = set(pool)
        nit = set(range(n)) - playoff - bowl
        return dict(CCG=ccg, Playoff=playoff, Bowl=bowl, Prestige=prestige, Marquee=set(picks), NIT=nit, aq=aq)

    def _div_of(self, t):
        if not hasattr(self, "_dv"):
            self._dv = {}
            for (l, d), ix in self.div.items():
                for i in ix:
                    self._dv[i] = d
        return self._dv[t]

    def seeds(self, playoff, rem_w, rem_l):
        pc = lcfg.cfg()["postseason"]["bowls"].get("projection", {})
        pw, pl = float(pc.get("seed_per_win", 0.1)), float(pc.get("seed_per_loss", 0.1))
        f = sorted(playoff, key=lambda i: (-(self.pscore[i] + pw * rem_w[i] - pl * rem_l[i]), self.prk2[i]))
        return f  # seed 1 first


# ------------------------------------------------------------------ simulation
def simulate(year, sims=None, seed=None):
    c = settings()
    sims = int(sims or c["sims"])
    rng = np.random.default_rng(int(seed if seed is not None else c["seed"]))
    st, keys, idx, reg, after, games = inputs(year)
    mu, sd, proj = model(year, st, keys, idx, reg, after, float(c["shrink_games"]))
    import matchups_page as mp
    spread = float(getattr(mp, "SPREAD", 24.0))
    R = Rules(year, st, keys)
    n = len(keys)
    W0 = st["Wins"].to_numpy(float)
    L0 = st["Losses"].to_numpy(float)
    PF0 = st["PointsFor"].to_numpy(float)
    PA0 = st["PointsAgainst"].to_numpy(float)
    G = len(games)
    gw = np.array([g[0] for g in games])
    ga = np.array([g[1] for g in games])
    gb = np.array([g[2] for g in games])
    mua = np.array([proj.get((w, a), mu[a]) for w, a, b in games])
    mub = np.array([proj.get((w, b), mu[b]) for w, a, b in games])
    sda = np.array([spread if (w, a) in proj else sd[a] for w, a, b in games])
    sdb = np.array([spread if (w, b) in proj else sd[b] for w, a, b in games])
    t0 = time.time()
    counts = {c_: np.zeros(n) for c_ in COLS}
    upcoming = [gi for gi in range(G) if gw[gi] == after + 1]
    # conditional tallies for leverage: per upcoming game, per side, per outcome: [wins_count, outcome|win, outcome|loss]
    lev = {gi: {"a_win": 0, "n": 0, **{f"{s}_{o}_{r}": 0 for s in "ab" for o in COLS + ["Postseason"] for r in ("w", "l")}}
           for gi in upcoming}
    order32 = bracket_order(R.field)
    for s in range(sims):
        sa = rng.normal(mua, sda)
        sb = rng.normal(mub, sdb)
        W, PF, PA = W0.copy(), PF0.copy(), PA0.copy()
        rem_w, rem_l = np.zeros(n), np.zeros(n)
        aw = sa > sb
        np.add.at(W, ga[aw], 1)
        np.add.at(W, gb[~aw], 1)
        np.add.at(rem_w, ga[aw], 1)
        np.add.at(rem_w, gb[~aw], 1)
        np.add.at(rem_l, gb[aw], 1)
        np.add.at(rem_l, ga[~aw], 1)
        np.add.at(PF, ga, sa)
        np.add.at(PF, gb, sb)
        np.add.at(PA, ga, sb)
        np.add.at(PA, gb, sa)
        ccg_score = rng.normal(mu, sd)
        out = R.run(W, PF, PA, ccg_score, rem_w, rem_l)
        # title: fixed bracket on projected seeds, one score per team per round
        seeds = R.seeds(out["Playoff"], rem_w, rem_l)
        alive = [seeds[i - 1] for i in order32]
        while len(alive) > 1:
            sc = rng.normal(mu[alive], sd[alive])
            alive = [alive[i] if sc[i] >= sc[i + 1] else alive[i + 1] for i in range(0, len(alive), 2)]
        out["Natty"] = {alive[0]}
        out["Postseason"] = out["Playoff"] | out["Bowl"]  # leverage only: "go bowling" = a bowl or the playoff
        for c_ in COLS:
            counts[c_][list(out[c_])] += 1
        for gi in upcoming:
            L_ = lev[gi]
            L_["n"] += 1
            a_won = bool(aw[gi])
            L_["a_win"] += a_won
            for o in COLS + ["Postseason"]:
                S = out[o]
                L_[f"a_{o}_{'w' if a_won else 'l'}"] += ga[gi] in S
                L_[f"b_{o}_{'l' if a_won else 'w'}"] += gb[gi] in S
    took = time.time() - t0
    odds = {c_: counts[c_] / sims for c_ in COLS}
    return dict(year=year, after=after, sims=sims, took=took, st=st, keys=keys, idx=idx, odds=odds, games=games,
                lev=lev, mu=mu, sd=sd, W0=W0, L0=L0, rules=R, upcoming=upcoming)


def deterministic(year):
    """The projection's own results (each team scores its season average; bowl_projection.project)
    run through the fast rules -- for the check against the real engine."""
    st, keys, idx, reg, after, games = inputs(year)
    x = reg.assign(k=list(zip(reg["LeagueID"].astype(str), reg["RosterID"].astype(str))))
    avg = x.groupby("k")["PF"].mean().round(2).to_dict()
    n = len(keys)
    a_ = np.array([avg.get(k, 0.0) for k in keys])
    W, PF, PA = (st[c].to_numpy(float, copy=True) for c in ("Wins", "PointsFor", "PointsAgainst"))
    rem_w, rem_l = np.zeros(n), np.zeros(n)
    for _, a, b in games:
        PF[a] += a_[a]; PF[b] += a_[b]; PA[a] += a_[b]; PA[b] += a_[a]  # noqa: E702
        if a_[a] > a_[b]:
            W[a] += 1; rem_w[a] += 1; rem_l[b] += 1  # noqa: E702
        elif a_[b] > a_[a]:
            W[b] += 1; rem_w[b] += 1; rem_l[a] += 1  # noqa: E702
    R = Rules(year, st, keys)
    out = R.run(W, PF, PA, a_, rem_w, rem_l)
    return {k_: {keys[i] for i in v} for k_, v in out.items()}


# ------------------------------------------------------------------ proofs (Clinched / Out)
def proofs(S):
    st, keys, games = S["st"], S["keys"], S["games"]
    n = len(keys)
    left = np.zeros(n)
    for _, a, b in games:
        left[a] += 1
        left[b] += 1
    wmin, wmax = S["W0"], S["W0"] + left
    R = S["rules"]
    flag = {c_: [""] * n for c_ in COLS}
    for (l, d), ix in R.div.items():
        for i in ix:
            rivals = [j for j in ix if j != i]
            if rivals and wmin[i] > max(wmax[j] for j in rivals):
                flag["CCG"][i] = "clinched"
            elif any(wmax[i] < wmin[j] for j in rivals):
                flag["CCG"][i] = "out"
    for i in range(n):
        others = np.delete(np.arange(n), i)
        if (wmax[others] >= wmin[i]).sum() <= R.field - len(R.leagues) - 1:
            flag["Playoff"][i] = "clinched"
        elif flag["CCG"][i] == "out" and (wmin[others] > wmax[i]).sum() >= R.field:
            flag["Playoff"][i] = "out"
        if flag["Playoff"][i] == "clinched":
            flag["Bowl"][i] = flag["NIT"][i] = flag["Prestige"][i] = flag["Marquee"][i] = "out"
        elif wmax[i] < R.bc["bump_wins"]:
            flag["Bowl"][i] = flag["Prestige"][i] = flag["Marquee"][i] = "out"
        if flag["Playoff"][i] == "out":
            flag["Natty"][i] = "out"
    return flag


# ------------------------------------------------------------------ output
def build(year, sims=None, seed=None, write=True):
    S = simulate(year, sims, seed)
    st, keys, odds = S["st"], S["keys"], S["odds"]
    flags = proofs(S)
    short = {v: k for k, v in ps.league_short().items()}
    teams = []
    for i, r in enumerate(st.to_dict("records")):
        teams.append({"LeagueID": keys[i][0], "RosterID": keys[i][1], "Team": r["Team"],
                      "League": short.get(str(r["LeagueName"]).strip(), str(r["LeagueName"]).strip()),
                      "Division": r["Division"], "Rec": f"{int(r['Wins'])}-{int(r['Losses'])}",
                      **{c_: round(float(odds[c_][i]), 4) for c_ in COLS},
                      "flags": {c_: flags[c_][i] for c_ in COLS if flags[c_][i]}})
    top = []
    labels = {"CCG": "reach the CCG", "Playoff": "make the playoff", "Prestige": "make a Prestige Bowl",
              "Marquee": "make a Marquee Bowl", "Postseason": "go bowling", "NIT": "land in the NIT", "Natty": "win the title"}
    for gi in S["upcoming"]:
        L_, (w, a, b) = S["lev"][gi], S["games"][gi]
        na, nb = L_["a_win"], L_["n"] - L_["a_win"]
        best = None
        for side, i, nw, nl in (("a", a, na, nb), ("b", b, nb, na)):
            if nw < 50 or nl < 50:  # too few runs on one side to say
                continue
            for o in ("CCG", "Playoff", "Prestige", "Marquee", "Postseason", "Natty"):
                pw_, pl_ = L_[f"{side}_{o}_w"] / nw, L_[f"{side}_{o}_l"] / nl
                d = pw_ - pl_
                if best is None or d > best["swing"]:
                    best = {"swing": round(d, 4), "team": teams[i]["Team"], "outcome": o, "label": labels[o],
                            "with_win": round(pw_, 4), "with_loss": round(pl_, 4), "LeagueID": keys[i][0], "RosterID": keys[i][1]}
        if best:
            top.append({"week": int(w), "a": teams[a]["Team"], "b": teams[b]["Team"], "league": teams[a]["League"],
                        "pwin_a": round(na / max(L_["n"], 1), 4), **best})
    top.sort(key=lambda x: -x["swing"])
    # Page + Discord (Chris, 2026-11-07): one row per TEAM, split into a playoff and a bowl list,
    # each ranked by swing (with-win minus with-loss); swings under min_swing are left out.
    n_top, floor = int(settings()["top_games"]), float(settings().get("min_swing", 0.10))
    by = {"Playoff": [], "Postseason": []}
    for gi in S["upcoming"]:
        L_, (w, a, b) = S["lev"][gi], S["games"][gi]
        na, nb = L_["a_win"], L_["n"] - L_["a_win"]
        for side, i, j, nw, nl in (("a", a, b, na, nb), ("b", b, a, nb, na)):
            if nw < 50 or nl < 50:
                continue
            for o in by:
                pw_, pl_ = L_[f"{side}_{o}_w"] / nw, L_[f"{side}_{o}_l"] / nl
                if pw_ - pl_ >= floor:
                    by[o].append({"team": teams[i]["Team"], "opp": teams[j]["Team"], "league": teams[i]["League"],
                                  "LeagueID": keys[i][0], "RosterID": keys[i][1], "with_win": round(pw_, 4),
                                  "with_loss": round(pl_, 4), "swing": round(pw_ - pl_, 4), "pwin": round(nw / max(L_["n"], 1), 4)})
    for o in by:
        by[o].sort(key=lambda x: -x["swing"])
    out = {"year": int(year), "after_week": int(S["after"]), "sims": S["sims"], "seconds": round(S["took"], 1),
           "columns": COLS, "teams": teams, "impact": top[:n_top], "impact_all": top,
           # no row cap yet (Chris, 2026-11-07): every swing >= min_swing; review counts after a week, cap later
           "impact_playoff": by["Playoff"], "impact_bowl": by["Postseason"]}
    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        for p in (os.path.join(OUT_DIR, "odds.json"), os.path.join(OUT_DIR, f"odds-wk{S['after']:02d}.json")):
            with open(p, "w") as f:
                json.dump(out, f, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--sims", type=int)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    year = a.year or ps.current_season()
    out = build(year, a.sims, a.seed)
    t = out["teams"]
    s = {c_: round(sum(x[c_] for x in t), 1) for c_ in COLS}
    print(f"Odds {year} after week {out['after_week']}: {out['sims']} runs in {out['seconds']}s; column totals {s}")
    for lbl, k_ in (("playoff", "impact_playoff"), ("bowl", "impact_bowl")):
        for g in out[k_]:
            print(f"  {lbl}: {g['team']} (vs {g['opp']}) {g['with_loss']:.0%} -> {g['with_win']:.0%} with a win")


if __name__ == "__main__":
    main()
