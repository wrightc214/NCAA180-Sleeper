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


def finish(problems):
    for p in problems:
        print("WARNING:", p)
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
