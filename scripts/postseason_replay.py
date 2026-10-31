"""
postseason_replay.py -- replay a finished postseason through the postseason scripts and check
them against Postseason_Historic.csv (Chris, 2026-10-27). Writes only to a scratch folder.

Exact checks (must match history): CCG pairings + winners; playoff field; bracket built from
that year's real seeds, every round's pairings + winners; bowl and NIT pools; NIT advancement
and bracket when fed the real group draws.
Rule checks (random draws can't match history): fresh bowl draws under the tiered rules and fresh NIT Group Stage 1
and 2 draws obey the rules (sizes, every team once, no same-league bowl games, state/region
exclusions, league spreading). Info: the bots' seeding vs the seeds actually used.

  python scripts/postseason_replay.py --year 2025 [--dir scratch/folder]
"""
import argparse
import os
import random
import shutil
import subprocess
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowls as B  # noqa: E402
import nit as N  # noqa: E402

FAIL = []


def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "Sleeper NFL state" not in l and "fallback week" not in l)
    return r.returncode, out


def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        FAIL.append(label)


def games(df):
    return {frozenset(g["Team"]): (g[g["Outcome"] == "Win"]["Team"].tolist() or ["?"])[0] for _, g in df.groupby("GameID")}


def hist_games(h):
    return {frozenset([r.TeamA, r.TeamB]): r.Winner for r in h.itertuples()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--dir")
    a = ap.parse_args()
    y = a.year
    d = a.dir or tempfile.mkdtemp(prefix=f"replay{y}_")
    shutil.rmtree(d, ignore_errors=True)
    h = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
    h = h[h["Season"] == str(y)]
    S = lambda: ps.read_season(os.path.join(d, "Postseason_Season.csv"))  # noqa: E731
    print(f"Postseason replay {y} -> {d}")

    print("CCG")
    code, out = run("scripts/conference_championships.py", "--year", str(y), "--data-dir", d)
    s = S()
    check("CCG pairings and winners match history", games(s[s["Round"] == "CCG"]) == hist_games(h[h["Event"] == "CCG"]), out)

    print("Playoff")
    code, out = run("scripts/playoff_field.py", "--year", str(y), "--data-dir", d)
    check("playoff field computed cleanly", code == 0, out)
    code, out = run("scripts/playoff_bracket.py", "--year", str(y), "--seeds", "history", "--data-dir", d)
    check("bracket built from real seeds (field == seeded teams)", code == 0, out)
    s = S()
    for r in range(1, 6):
        hh = h[(h["Event"] == "Playoff") & (h["Round"] == str(r))]
        if hh.empty:
            continue
        ours = games(s[(s["Round"] == "Playoff") & (s["PlayoffRound"].astype(str) == str(r))])
        check(f"round {r} ({hh.iloc[0]['RoundName']}): pairings + winners match", ours == hist_games(hh))

    print("Bowls")
    _, field_path, _ = ps.paths(argparse.Namespace(data_dir=d))
    _, cfg = ps.config()
    hb = h[h["Event"] == "Bowl"]
    bcfg = cfg["bowls"]
    pool32, notes = B.build_pool(y, field_path, bcfg)
    check(f"bowl pool ({len(pool32)} teams) matches history", len(pool32) == 2 * len(hb)
          and {t["Team"] for t in pool32} == set(hb["TeamA"]) | set(hb["TeamB"]))
    hist = B.history(y, bcfg)
    tiers = {t["name"]: t for t in bcfg["tiers"]}
    fixed = sum(len(t["bowls"]) for t in bcfg["tiers"] if t["fill"] != "random")
    ok_all, repeats = True, 0
    for k in range(200):
        gms, unfilled, left, _ = B.draw(y, pool32, bcfg, random.Random(k), hist)
        d0 = B.Draw(y, pool32, bcfg, random.Random(0), hist)
        placed = [t for _, x, z in gms for t in (x, z)]
        bad = []
        for b, x, z in gms:
            if x["LeagueID"] == z["LeagueID"]:
                bad.append(f"{b['name']}: same league")
            if b["tier"] == "Opening Bowls" or (b["tier"] == "Showcase Bowls" and not b.get("pool")):
                spots = [z] if b.get("lean") and d0.lg(x) == b["lean"] else [x, z]
                if any(not d0.allowed(b, t) for t in spots):
                    bad.append(f"{b['name']}: exclusion")
            if frozenset((B.slot(x), B.slot(z))) in hist[0]:
                if b["tier"] == "Marquee Bowls":
                    repeats += 1
                else:
                    bad.append(f"{b['name']}: repeat matchup")
        once = len(placed) == len({B.slot(t) for t in placed})
        showcase_all = {b["name"] for b, _, _ in gms if b["tier"] == "Showcase Bowls"} == {b["name"] for b in tiers["Showcase Bowls"]["bowls"]}
        if bad or not once or unfilled or left or not showcase_all or len(gms) != len(pool32) // 2:
            ok_all = False
            print(f"    draw {k}: {bad} unfilled {unfilled} unplaced {[t['Team'] for t in left]} showcase_all={showcase_all}")
    check(f"200 fresh bowl draws obey the new rules (tiers filled, all {fixed} fixed bowls played, no same-league, "
          "exclusions on random spots, no recent rematch outside Marquee, every team once)", ok_all)
    print(f"  info  Marquee rematches across 200 draws (penalised, allowed only if unavoidable): {repeats}")
    code, out = run("scripts/bowls.py", "--year", str(y), "--from-history", "--data-dir", d)

    print("NIT")
    code, out = run("scripts/nit.py", "--year", str(y), "--from-history", "--data-dir", d)
    s = S()
    n, hn = s[s["Round"] == "NIT"], h[h["Event"] == "NIT"]
    pool_h = {t for x in hn[hn["RoundName"].isin(N.HISTORY_NAMES[N.STAGE1])]["TeamA"] for t in x.split(" | ")}
    check("NIT pool matches history", pool_h == set(n[n["Stage"] == N.STAGE1]["Team"]))
    for st in (N.STAGE1, N.STAGE2):
        check(f"{st} winners match (real draw)", set(hn[hn["RoundName"].isin(N.HISTORY_NAMES.get(st, {st}))]["Winner"]) == set(n[(n["Stage"] == st) & (n["Outcome"] == "Win")]["Team"]))
    for st in cfg["nit"]["bracket"]["rounds"]:
        check(f"NIT {st}: pairings + winners match", games(n[n["Stage"] == st]) == hist_games(hn[hn["RoundName"].isin(N.HISTORY_NAMES.get(st, {st}))]))
    team = {(r["LeagueID"], r["RosterID"]): r for r in ps.standings(y).to_dict("records")}
    pool_t = [t for t in team.values() if t["Team"] in pool_h]
    w1 = [team[(r.LeagueID, str(r.RosterID))] for r in n[(n["Stage"] == N.STAGE1) & (n["Outcome"] == "Win")].itertuples()]
    c1, c2 = cfg["nit"]["group_stage_1"], cfg["nit"]["group_stage_2"]
    worst1 = worst2 = 0
    spread_ok = True
    for k in range(25):
        g1 = N.assign_groups(pool_t, N.group_sizes(len(pool_t), c1["groups"]), random.Random(k))
        sizes = sorted(len(g) for g in g1)
        if len(g1) != c1["groups"] or sizes[-1] - sizes[0] > 1 or sum(sizes) != len(pool_t):
            spread_ok = False
        worst1 = max(worst1, N.conflicts(g1))
        ng = c2["groups"]
        g2 = N.assign_groups(w1, [c2["size"]] * ng, random.Random(k), branch_of=lambda i: (i // 2, i // (ng // 2)))
        worst2 = max(worst2, N.conflicts(g2))
        for lg in {t["LeagueID"] for t in w1}:
            where = [i for i, g in enumerate(g2) for t in g if t["LeagueID"] == lg]
            if len(where) == 2 and len({i // (ng // 2) for i in where}) < 2:
                spread_ok = False
            if len(where) == 4 and len({i // 2 for i in where}) < 4:
                spread_ok = False
    check("25 fresh NIT draws: 24 groups, sizes differ by at most 1, every team once; leagues spread "
          "(2 winners -> opposite halves, 4 -> one per QF pairing)", spread_ok)
    print(f"  info  worst same-league pairs in a fresh draw: {N.STAGE1} {worst1}, {N.STAGE2} {worst2}")

    print("Seeding (info)")
    poll = "data/Poll_Season.csv" if y == ps.current_season() else "data/Poll_Historic.csv"
    p = pd.read_csv(poll, dtype=str)
    p = p[(p["Year"] == str(y)) & (p["PollType"] == "Seeding")]
    real = s[(s["Round"] == "Playoff") & (s["PlayoffRound"].astype(str) == "1")]
    rs = {(r.LeagueID, str(r.RosterID)): int(r.Seed) for r in real.itertuples() if str(r.Seed)}
    bs = {(r.LeagueID, r.RosterID): int(float(r.Rank)) for r in p.itertuples()}
    same = sum(1 for k, v in rs.items() if bs.get(k) == v)
    diff = sum(abs(bs.get(k, 99) - v) for k, v in rs.items()) / max(len(rs), 1)
    print(f"  info  bots' seeding vs seeds used: {same}/{len(rs)} identical, average gap {diff:.1f} seed lines")

    print(f"\n{'ALL EXACT CHECKS PASSED' if not FAIL else str(len(FAIL)) + ' CHECK(S) FAILED: ' + '; '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
