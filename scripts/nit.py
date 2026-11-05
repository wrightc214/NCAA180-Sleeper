"""
nit.py -- the NIT (rules: config/league.json -> postseason.nit; spec in the project's
pipeline-architecture doc, confirmed by the commissioner against 2024/2025).

Pool: every team not in the playoff field or a (published) bowl.
  Group Stage 1 (week 13): the pool split into 24 groups (A-X), sizes as even as possible
    (3s and 4s); top score in each group advances.
  Group Stage 2 (week 14): the 24 winners in 8 groups of 3 (A-H).
  Bracket: QF (wk 15) A/B, C/D, E/F, G/H winners; SF (wk 16) QF1-QF2, QF3-QF4; Final (wk 17).
Same-league avoidance is best effort: groups minimise same-league teams, and Group Stage 2
spreads a league's winners across bracket branches so they meet as late as possible.

REALIGNED FORMAT from postseason.nit.realigned_from (2026; Chris, 2026-11-04; project doc
nit-format-2026.md). Earlier seasons keep the format above (history replays).
  Round 1 (week 13): groups of 4 (some 3s), World Cup pots from the final bot poll, one team per
    pot per group, same-league spreading. Advance: group winners + "lucky dogs" (best scores among
    the rest) to a round-2 field of 28 (21 for small fields).
  Round 2 (week 14): 7 groups of 4; pots from the average of round-1 points rank and poll rank;
    never two teams from the same round-1 group. Advance: 7 winners + 1 lucky dog = 8.
  Quarterfinals (week 15): two halves of 4 (pots by combined group points), conflicts kept apart
    in priority order: same league > same round-2 group > same round-1 group; tossups prefer
    cross-league rivals meeting; then closest to straight seeding. Seeds are not shown.
  Ties (group wins, lucky dogs, pots, seeds): every-week head-to-head among the tied teams, then
    wins, then points.

Review step (Chris, 2026-10-27): each random draw (Group Stage 1, Group Stage 2) is written
as a DRAFT with its seed recorded; --publish locks it; --redraw makes a new draft. Results
and the bracket are refreshed every run. An exact tie for a group/game win is flagged.

  python scripts/nit.py [--year Y] [--publish | --redraw] [--from-history] [--data-dir DIR]
"""
import argparse
import os
import random
import string
import sys

import pandas as pd

import _postseason_common as ps
import team_names as tn

_NIT = ps.config()[1]["nit"]
# Display names (Chris, 2026-10-28): Opening Groups -> Qualifier Groups. History rows keep the names used then.
STAGE1, STAGE2 = _NIT["group_stage_1"]["name"], _NIT["group_stage_2"]["name"]
HISTORY_NAMES = {STAGE1: set(_NIT["group_stage_1"]["history_names"]) | {STAGE1},
                 STAGE2: set(_NIT["group_stage_2"]["history_names"]) | {STAGE2}}


def group_sizes(n, groups):
    base, extra = divmod(n, groups)
    return [base + 1] * extra + [base] * (groups - extra)


def assign_groups(teams, sizes, rng, branch_of=None, met=None):
    """Greedy best-effort same-league avoidance. Most-represented leagues placed first.
    branch_of(i) -> (pairing, half) for bracket spreading (Group Stage 2).
    met: franchise pairs that met in recent postseasons -- avoided too, but ranked below the
    league rules (Chris, 2026-10-28: soft rule)."""
    met = met or set()
    key = lambda t: (str(t["LeagueName"]).strip(), str(t["RosterID"]))  # noqa: E731
    groups = [[] for _ in sizes]
    by_lg = {}
    for t in teams:
        by_lg.setdefault(t["LeagueID"], []).append(t)
    leagues = list(by_lg)
    rng.shuffle(leagues)
    leagues.sort(key=lambda l: -len(by_lg[l]))
    for lg in leagues:
        members = by_lg[lg][:]
        rng.shuffle(members)
        for t in members:
            best, best_k = [], None
            for i, g in enumerate(groups):
                if len(g) >= sizes[i]:
                    continue
                same = sum(x["LeagueID"] == lg for x in g)
                rematch = sum(frozenset((key(t), key(x))) in met for x in g)
                k = (same, rematch, len(g))
                if branch_of:
                    p, h = branch_of(i)
                    same_p = sum(x["LeagueID"] == lg for j, gg in enumerate(groups) if branch_of(j)[0] == p for x in gg)
                    same_h = sum(x["LeagueID"] == lg for j, gg in enumerate(groups) if branch_of(j)[1] == h for x in gg)
                    k = (same, same_p, same_h, rematch, len(g))
                if best_k is None or k < best_k:
                    best, best_k = [i], k
                elif k == best_k:
                    best.append(i)
            groups[rng.choice(best)].append(t)
    return groups


def recent_met(year):
    """Franchise pairs that met in the last postseason.bowls.repeat_seasons postseasons."""
    import bowls
    return bowls.history(year, ps.config()[1]["bowls"])[0]


def conflicts(groups):
    return sum(len(g) - len({t["LeagueID"] for t in g}) for g in groups)


def stage_rows(year, stage, week, groups, seed):
    rows = []
    for i, g in enumerate(groups):
        letter = string.ascii_uppercase[i]
        rows += ps.game_rows(year, "NIT", week, f"{year}-NIT-{'GS1' if stage == STAGE1 else 'GS2'}-{letter}", g,
                             stage=stage, bowl=f"Group {letter}", draw=seed)
    return rows


def refresh(year, df, stage, team):
    rows = []
    for gid, g in df.groupby("GameID", sort=False):
        r0 = g.iloc[0]
        rows += ps.game_rows(year, "NIT", r0["Week"] or None, gid, [team[(r.LeagueID, str(r.RosterID))] for r in g.itertuples()],
                             stage=stage, bowl=r0["BowlName"], draw=r0["DrawSeed"])
    return rows


def stage_winners(rows):
    df = pd.DataFrame(rows)
    out, problems = [], []
    for gid, g in df.groupby("GameID", sort=False):
        if (g["Status"] != "Final").any():
            return None, problems
        w = g[g["Outcome"] == "Win"]
        if len(w) != 1:
            problems.append(f"{gid}: tie for first -- resolve manually")
            return None, problems
        out.append((g.iloc[0]["BowlName"], w.iloc[0]))
    return out, problems


def history_groups(year, stage, team):
    h = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
    h = h[(h["Season"] == str(year)) & (h["Event"] == "NIT") & h["RoundName"].isin(HISTORY_NAMES[stage])].sort_values("Bowl")
    lg = pd.read_csv(ps.LEAGUES, dtype=str)
    lid = dict(zip(lg[lg["Year"] == str(year)]["LeagueName"].str.strip(), lg[lg["Year"] == str(year)]["LeagueID"]))
    groups = []
    for r in h.itertuples():
        g = []
        for t in r.TeamA.split(" | "):
            sl = tn.slot(year, t)
            g.append(team[(lid[sl[0].strip()], str(sl[1]))])
        groups.append(g)
    return groups


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--from-history", action="store_true", help="replay: use that year's actual group draws")
    ap.add_argument("--data-dir")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, field_path, draft_dir = ps.paths(a)
    _, pcfg = ps.config()
    cfg = pcfg["nit"]
    st = ps.standings(year)
    team = {(r["LeagueID"], r["RosterID"]): r for r in st.to_dict("records")}
    season = ps.read_season(season_path)
    yr = season[season["Year"].astype(str) == str(year)]
    bowls = yr[yr["Round"] == "Bowl"]
    if bowls.empty:
        sys.exit("FATAL: bowls must be published before the NIT can be drawn")
    field = pd.read_csv(field_path, dtype=str)
    field = field[field["Year"].astype(str) == str(year)]
    taken = set(zip(field["LeagueID"], field["RosterID"])) | set(zip(bowls["LeagueID"], bowls["RosterID"].astype(str)))
    pool = [t for k, t in team.items() if k not in taken]
    nit = yr[yr["Round"] == "NIT"]
    problems = []

    def draft_or_publish(stage, make):
        path = os.path.join(draft_dir, f"NIT_{'GS1' if stage == STAGE1 else 'GS2'}_{year}.csv")
        if a.from_history:
            rows = make(None)
        elif a.publish:
            if not os.path.exists(path):
                sys.exit(f"FATAL: no {stage} draft to publish ({path})")
            rows = ps.read_season(path).to_dict("records")
        else:
            if os.path.exists(path) and not a.redraw:
                print(f"NIT {year}: {stage} draft awaiting review ({path}); --publish or --redraw")
                return False
            prev = ps.read_season(path)["DrawSeed"].iloc[0] if os.path.exists(path) else None
            seed = int(prev) + 1 if prev else ps.draw_seed(year, stage)
            rows = make(seed)
            os.makedirs(draft_dir, exist_ok=True)
            pd.DataFrame(rows, columns=ps.COLUMNS).to_csv(path, index=False)
            gs = pd.DataFrame(rows).groupby("GameID")
            conf = sum(len(g) - g["LeagueID"].nunique() for _, g in gs)
            print(f"NIT {year}: DRAFT {stage}: {len(gs)} groups, sizes {sorted(gs.size().value_counts().items())}, "
                  f"same-league pairs {conf}, seed {seed} -> {path}")
            if cfg.get("review_before_publish", True):
                return False
        ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] == stage), rows, season_path)
        print(f"NIT {year}: {stage} published ({len(rows)} team rows)")
        return True

    if year >= int(cfg.get("realigned_from", 9999)) and not a.from_history:
        return realigned(year, a, cfg, team, pool, nit, season_path, draft_or_publish, problems)

    # ---- Group Stage 1
    g1 = nit[nit["Stage"] == STAGE1]
    c1 = cfg["group_stage_1"]
    if g1.empty:
        def make1(seed):
            if seed is None:
                groups = history_groups(year, STAGE1, team)
            else:
                groups = assign_groups(pool, group_sizes(len(pool), c1["groups"]), random.Random(seed), met=recent_met(year))
                if min(len(g) for g in groups) < c1["min_size"]:
                    sys.exit(f"FATAL: pool of {len(pool)} is too small for {c1['groups']} groups of {c1['min_size']}+")
            return stage_rows(year, STAGE1, c1["week"], groups, seed or "history")
        if not draft_or_publish(STAGE1, make1):
            return
        if not a.from_history:
            return
        nit = ps.read_season(season_path)
        nit = nit[(nit["Year"].astype(str) == str(year)) & (nit["Round"] == "NIT")]
        g1 = nit[nit["Stage"] == STAGE1]
    rows1 = refresh(year, g1, STAGE1, team)
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] == STAGE1), rows1, season_path)
    w1, p = stage_winners(rows1)
    problems += p
    if w1 is None:
        print(f"NIT {year}: {STAGE1} in progress / pending")
        return finish(problems)

    # ---- Group Stage 2
    c2 = cfg["group_stage_2"]
    nit = ps.read_season(season_path)
    nit = nit[(nit["Year"].astype(str) == str(year)) & (nit["Round"] == "NIT")]
    g2 = nit[nit["Stage"] == STAGE2]
    winners1 = [team[(w["LeagueID"], str(w["RosterID"]))] for _, w in w1]
    if g2.empty:
        def make2(seed):
            if seed is None:
                groups = history_groups(year, STAGE2, team)
            else:
                ng = c2["groups"]
                branch = lambda i: (i // 2, i // (ng // 2))  # noqa: E731  (pairing A/B.., bracket half)
                groups = assign_groups(winners1, [c2["size"]] * ng, random.Random(seed), branch_of=branch, met=recent_met(year))
            return stage_rows(year, STAGE2, c2["week"], groups, seed or "history")
        if not draft_or_publish(STAGE2, make2):
            return finish(problems)
        nit = ps.read_season(season_path)
        nit = nit[(nit["Year"].astype(str) == str(year)) & (nit["Round"] == "NIT")]
        g2 = nit[nit["Stage"] == STAGE2]
    rows2 = refresh(year, g2, STAGE2, team)
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] == STAGE2), rows2, season_path)
    w2, p = stage_winners(rows2)
    problems += p
    if w2 is None:
        print(f"NIT {year}: {STAGE2} in progress / pending")
        return finish(problems)

    # ---- bracket (deterministic): A/B, C/D, E/F, G/H -> SF -> Final
    w2 = sorted(w2, key=lambda x: x[0])
    current = [[team[(w2[i][1]["LeagueID"], str(w2[i][1]["RosterID"]))], team[(w2[i + 1][1]["LeagueID"], str(w2[i + 1][1]["RosterID"]))]]
               for i in range(0, len(w2), 2)]
    bc = cfg["bracket"]
    rows = []
    for r_i, label in enumerate(bc["rounds"]):
        week = int(bc["first_week"]) + r_i
        nxt = []
        for g_i, pair in enumerate(current, 1):
            if pair is None:
                nxt.append(None)
                continue
            gid = f"{year}-NIT-{label[:2].upper()}{g_i}"
            gr = ps.game_rows(year, "NIT", week, gid, pair, stage=label, bowl=f"{label} {g_i}" if len(current) > 1 else label)
            rows += gr
            if any(r["Outcome"] == "Tie" for r in gr):
                problems.append(f"{gid}: exact tie -- resolve manually")
            w = [r for r in gr if r["Outcome"] == "Win"]
            nxt.append(team[(w[0]["LeagueID"], w[0]["RosterID"])] if w else None)
        if len(nxt) == 1:
            break
        current = [[nxt[i], nxt[i + 1]] if nxt[i] and nxt[i + 1] else None for i in range(0, len(nxt), 2)]
        if all(c is None for c in current):
            break
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] in bc["rounds"]), rows, season_path)
    print(f"NIT {year}: bracket {len(rows) // 2} games ({sum(r['Status'] == 'Final' for r in rows) // 2} final)")
    return finish(problems)


# ---------------- realigned format (2026+) ----------------
def key(t):
    return (str(t["LeagueID"]), str(t["RosterID"]).replace(".0", ""))


def weekly(year):
    """{team key: {week: points}} for the regular season (this season's scoring mode)."""
    out = {}
    for r in ps.regular_games(year).itertuples():
        out.setdefault((str(r.LeagueID), str(r.RosterID)), {})[int(r.Week)] = float(r.PF)
    return out


def tb_sort(teams, W):
    """Tied teams, best first: every-week head-to-head among them, then wins, then points."""
    def ew(t):
        mine = W.get(key(t), {})
        return sum(1 for u in teams if u is not t for w, v in mine.items() if v > W.get(key(u), {}).get(w, float("inf")))
    return sorted(teams, key=lambda t: (-ew(t), -float(t.get("Wins") or 0), -float(t.get("PointsFor") or 0)))


def rank(teams, metric, W):
    """Best first by metric (higher = better); exact ties broken by tb_sort."""
    by = {}
    for t in teams:
        by.setdefault(round(float(metric(t)), 2), []).append(t)
    return [t for v in sorted(by, reverse=True) for t in tb_sort(by[v], W)]


def poll_rank(year, before_week):
    """{team key: rank} from the latest BotConsensus poll before the NIT starts."""
    p = pd.read_csv("data/Poll_Season.csv", dtype=str) if year == ps.current_season() else pd.read_csv("data/Poll_Historic.csv", dtype=str)
    p = p[(p["Year"] == str(year)) & (p["PollType"] == "BotConsensus")]
    tw = pd.to_numeric(p["ThroughWeek"])
    p = p[tw == tw[tw < int(before_week)].max()]
    return {(str(r.LeagueID), str(r.RosterID)): int(float(r.Rank)) for r in p.itertuples()}


def rivals():
    try:
        r = pd.read_csv("data/rivalries/football.csv", dtype=str)
    except FileNotFoundError:
        return set()
    return {frozenset((a, b)) for a, b, c in zip(r["team_a"], r["team_b"], r["certainty"]) if str(c).isdigit() and int(c) >= 4}


def pot_draw(order, ngroups, rng, hard=lambda a, b: False, soft=lambda a, b: 0, tries=3000):
    """World Cup pots: order (best first) cut into pots of ngroups; one team per pot per group.
    hard conflicts never share a group; soft conflicts are minimised. Reproducible from rng."""
    pots = [order[i:i + ngroups] for i in range(0, len(order), ngroups)]
    best = None
    for _ in range(tries):
        groups, cost, ok = [[] for _ in range(ngroups)], 0, True
        for pot in pots:
            pot = pot[:]
            rng.shuffle(pot)
            free = list(range(ngroups))
            for t in pot:
                cand = [(sum(soft(t, u) for u in groups[g]), g) for g in free if not any(hard(t, u) for u in groups[g])]
                if not cand:
                    ok = False
                    break
                m = min(c for c, _ in cand)
                g = rng.choice([g for c, g in cand if c == m])
                groups[g].append(t)
                free.remove(g)
                cost += m
            if not ok:
                break
        if ok and (best is None or cost < best[0]):
            best = (cost, groups)
            if cost == 0:
                break
    return best[1] if best else None


def settle(rows, team, W):
    """All groups final -> (rows with Outcome fixed by the tiebreak, [(GameID, winner, points)], [(team, points, GameID)])
    for every team; None while any group is pending."""
    df = pd.DataFrame(rows)
    if df.empty or (df["Status"] != "Final").any():
        return None
    winners, everyone = [], []
    for gid, g in df.groupby("GameID", sort=False):
        ts = [(team[(r.LeagueID, str(r.RosterID))], float(r.Points)) for r in g.itertuples()]
        pts = {key(t): p for t, p in ts}
        order = rank([t for t, _ in ts], lambda t: pts[key(t)], W)
        winners.append((gid, order[0], pts[key(order[0])]))
        everyone += [(t, pts[key(t)], gid) for t in order]
        for r in rows:
            if r["GameID"] == gid:
                r["Outcome"] = "Win" if (r["LeagueID"], str(r["RosterID"])) == key(order[0]) else "Loss"
    return rows, winners, everyone


def qf_bracket(q, combined, gid1, gid2, W, riv, wts):
    """Two halves of 4 + QF pairings. Minimise, in order: weighted conflicts meeting in a QF,
    conflicts in the same half (= a SF meeting), then prefer cross-league rivals meeting, then
    closest to straight seeding (halves 1,4,5,8 / 2,3,6,7; 1v4, 2v3)."""
    from itertools import product
    order = rank(q, lambda t: combined[key(t)], W)
    pots = [order[i:i + 2] for i in range(0, 8, 2)]

    def w(a, b):
        return max([wts["league"] * (a["LeagueID"] == b["LeagueID"]), wts["round2"] * (gid2[key(a)] == gid2[key(b)]),
                    wts["round1"] * (gid1[key(a)] == gid1[key(b)])])

    def riv_pair(a, b):
        return a["LeagueID"] != b["LeagueID"] and frozenset((a["Team"], b["Team"])) in riv

    pairings = [((0, 3), (1, 2)), ((0, 2), (1, 3)), ((0, 1), (2, 3))]
    best = None
    for picks in product((0, 1), repeat=4):
        A = [p[i] for p, i in zip(pots, picks)]
        B = [p[1 - i] for p, i in zip(pots, picks)]
        halves = [sorted(h, key=order.index) for h in (A, B)]
        same_half = sum(w(a, b) for h in halves for i, a in enumerate(h) for b in h[i + 1:])
        for pa in pairings:
            for pb in pairings:
                games = [[halves[0][i] for i in pa[0]], [halves[0][i] for i in pa[1]],
                         [halves[1][i] for i in pb[0]], [halves[1][i] for i in pb[1]]]
                qf = sum(w(*g) for g in games)
                rv = sum(riv_pair(*g) for g in games)
                disp = sum(x != y for x, y in zip(picks, (0, 1, 0, 1))) + pairings.index(pa) + pairings.index(pb)
                k = (qf, same_half, -rv, disp)
                if best is None or k < best[0]:
                    best = (k, games)
    return best[1]


def realigned(year, a, cfg, team, pool, nit, season_path, draft_or_publish, problems):
    c1, c2, cq = cfg["group_stage_1"], cfg["group_stage_2"], cfg["realigned"]
    W = weekly(year)
    pr = poll_rank(year, c1["week"])
    order0 = rank(pool, lambda t: -pr.get(key(t), 999), W)  # poll order, best first
    met = recent_met(year)
    mk = lambda t: (str(t["LeagueName"]).strip(), str(t["RosterID"]))  # noqa: E731
    soft = lambda x, y: cq["weights"]["league"] * (x["LeagueID"] == y["LeagueID"]) + (frozenset((mk(x), mk(y))) in met)  # noqa: E731

    # ---- Round 1
    g1 = nit[nit["Stage"] == STAGE1]
    if g1.empty:
        def make1(seed):
            n = len(pool)
            ng = -(-n // int(cq["group_size"]))
            groups = pot_draw(order0, ng, random.Random(seed), soft=soft)
            if groups is None:
                sys.exit("FATAL: no valid NIT round-1 draw")
            return stage_rows(year, STAGE1, c1["week"], groups, seed)
        if not draft_or_publish(STAGE1, make1):
            return
        g1 = ps.read_season(season_path)
        g1 = g1[(g1["Year"].astype(str) == str(year)) & (g1["Round"] == "NIT") & (g1["Stage"] == STAGE1)]
    rows1 = refresh(year, g1, STAGE1, team)
    s1 = settle(rows1, team, W)
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] == STAGE1), s1[0] if s1 else rows1, season_path)
    if s1 is None:
        print(f"NIT {year}: {STAGE1} in progress / pending")
        return finish(problems)
    _, win1, all1 = s1
    gid1 = {key(t): g for t, _, g in all1}
    pts1 = {key(t): p for t, p, _ in all1}
    field2 = int(cq["round2_field"] if len(pool) >= int(cq["small_field_below"]) else cq["round2_field_small"])
    wk = {key(t) for _, t, _ in win1}
    rest = rank([t for t, _, _ in all1 if key(t) not in wk], lambda t: pts1[key(t)], W)
    dogs1 = rest[:max(field2 - len(win1), 0)]
    adv1 = [t for _, t, _ in win1] + dogs1
    print(f"NIT {year}: {STAGE1} final -> {len(win1)} group winners + {len(dogs1)} lucky dogs: "
          + ", ".join(f"{t['Team']} {pts1[key(t)]:.2f}" for t in dogs1))

    # ---- Round 2
    nit = ps.read_season(season_path)
    g2 = nit[(nit["Year"].astype(str) == str(year)) & (nit["Round"] == "NIT") & (nit["Stage"] == STAGE2)]
    if g2.empty:
        def make2(seed):
            ng = 8 - int(cq.get("round2_lucky_dogs", 1))  # 7 groups: 28 -> 7x4, 21 -> 7x3
            by_pts = {key(t): i for i, t in enumerate(rank(adv1, lambda t: pts1[key(t)], W))}
            by_poll = {key(t): i for i, t in enumerate(rank(adv1, lambda t: -pr.get(key(t), 999), W))}
            order2 = sorted(adv1, key=lambda t: ((by_pts[key(t)] + by_poll[key(t)]) / 2, by_pts[key(t)]))
            # Hard (Chris, 2026-11-04): no round-1 group-mates and no regular-season rematch. Leagues play a
            # full round robin, so a regular-season rematch = same league.
            same_g1 = lambda x, y: gid1[key(x)] == gid1[key(y)]  # noqa: E731
            groups = pot_draw(order2, ng, random.Random(seed), hard=lambda x, y: same_g1(x, y) or x["LeagueID"] == y["LeagueID"], soft=soft)
            if groups is None:  # only if one league floods round 2; keep it as a strong preference and say so
                print("WARNING: round-2 draw could not avoid every regular-season rematch; minimised instead")
                groups = pot_draw(order2, ng, random.Random(seed), hard=same_g1, soft=soft)
            if groups is None:
                sys.exit("FATAL: no valid NIT round-2 draw")
            return stage_rows(year, STAGE2, c2["week"], groups, seed)
        if not draft_or_publish(STAGE2, make2):
            return finish(problems)
        nit = ps.read_season(season_path)
        g2 = nit[(nit["Year"].astype(str) == str(year)) & (nit["Round"] == "NIT") & (nit["Stage"] == STAGE2)]
    rows2 = refresh(year, g2, STAGE2, team)
    s2 = settle(rows2, team, W)
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] == STAGE2), s2[0] if s2 else rows2, season_path)
    if s2 is None:
        print(f"NIT {year}: {STAGE2} in progress / pending")
        return finish(problems)
    _, win2, all2 = s2
    gid2 = {key(t): g for t, _, g in all2}
    pts2 = {key(t): p for t, p, _ in all2}
    wk2 = {key(t) for _, t, _ in win2}
    rest2 = rank([t for t, _, _ in all2 if key(t) not in wk2], lambda t: pts2[key(t)], W)
    q = [t for _, t, _ in win2] + rest2[:max(8 - len(win2), 0)]
    print(f"NIT {year}: {STAGE2} final -> {len(win2)} winners + lucky dog(s): " + ", ".join(t["Team"] for t in q[len(win2):]))

    # ---- Quarterfinal halves (deterministic) -> SF -> Final
    combined = {key(t): pts1[key(t)] + pts2[key(t)] for t in q}
    current = qf_bracket(q, combined, gid1, gid2, W, rivals(), cq["weights"])
    bc = cfg["bracket"]
    rows = []
    for r_i, label in enumerate(bc["rounds"]):
        week = int(bc["first_week"]) + r_i
        nxt = []
        for g_i, pair in enumerate(current, 1):
            if pair is None:
                nxt.append(None)
                continue
            gid = f"{year}-NIT-{label[:2].upper()}{g_i}"
            gr = ps.game_rows(year, "NIT", week, gid, pair, stage=label, bowl=f"{label} {g_i}" if len(current) > 1 else label)
            st = settle(gr, team, W)
            if st:
                gr = st[0]
            rows += gr
            w = [r for r in gr if r["Outcome"] == "Win"]
            nxt.append(team[(w[0]["LeagueID"], w[0]["RosterID"])] if w else None)
        if len(nxt) == 1:
            break
        current = [[nxt[i], nxt[i + 1]] if nxt[i] and nxt[i + 1] else None for i in range(0, len(nxt), 2)]
        if all(c is None for c in current):
            break
    ps.replace_rows(year, lambda r: not (r["Round"] == "NIT" and r["Stage"] in bc["rounds"]), rows, season_path)
    print(f"NIT {year}: bracket {len({r['GameID'] for r in rows})} games")
    return finish(problems)


def finish(problems):
    for p in problems:
        print("WARNING:", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
