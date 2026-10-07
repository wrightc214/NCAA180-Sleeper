"""
poll_backtest.py -- how the bots and their BCS consensus compare with the real playoff
seeds (committee) and with each other. Report only; writes nothing to data/.

  python scripts/poll_backtest.py --years 2024 2025 [--out work/poll/backtest.md]

Needs data/Matchups_Historic.csv and data/Postseason_Historic.csv (Event=Playoff, Round 1
gives all 32 seeds). Ceiling/Market bots need the history-backfill files
(POLL_BACKFILL_DIR, default data/backfill); without them those bots sit out.
Seeds are matched to slots by school name via Teams.csv (current names); misses listed.
"""
import argparse
import itertools
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
import poll_bots as pb  # noqa: E402


def seeds(year, teams):
    p = pd.read_csv("data/Postseason_Historic.csv", dtype=str)
    r1 = p[(p["Season"] == str(year)) & (p["Event"] == "Playoff") & (p["Round"] == "1")]
    pairs = list(zip(r1["TeamA"], r1["SeedA"])) + list(zip(r1["TeamB"], r1["SeedB"]))
    by = {r.Key: (r.LeagueID, r.RosterID) for r in teams.itertuples()}
    out, miss = {}, []
    for name, sd in pairs:
        k = by.get(pc.norm(name))
        if k is None:
            miss.append(name)
        else:
            out[k] = int(sd)
    return out, miss


def spearman(a, b):
    a, b = pd.Series(list(a), dtype=float), pd.Series(list(b), dtype=float)  # positional, not index-aligned
    return a.rank().corr(b.rank())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="+", type=int, default=[2024, 2025])
    ap.add_argument("--out", default=os.path.join(pc.WORK, "backtest.md"))
    ap.add_argument("--bots", nargs="*", help="override the bot list (ids) for what-if runs")
    args = ap.parse_args()
    cfg = pc.config()
    if args.bots:
        cfg["bots"] = [{"id": b, "name": next((x["name"] for x in cfg["bots"] if x["id"] == b), b.title()), "enabled": True}
                       for b in args.bots]
    names = {b["id"]: b["name"] for b in cfg["bots"]}
    L = []
    pair_rho = {}
    pred = {}

    for y in args.years:
        m = pc.matchups(y)
        t = pc.teams(y)
        t["LeagueID"] = t["LeagueName"].str.upper().map(pc.league_ids(y))
        keys = sorted(set(zip(m["LeagueID"], m["RosterID"])))
        slots = pb.league_slots(y)
        sd, miss = seeds(y, t)
        L.append(f"\n## {y}\nSeeds matched to slots: {len(sd)}/32" + (f" (unmatched: {', '.join(miss)})" if miss else ""))

        # Seeds vs bots, through week 11 and with week-12 points
        for label, pts_thru in (("through week 11", None), ("plus week-12 points", 12)):
            extra = pb.history_extra(y, 11, slots)
            rk, used = pb.bot_ranks(cfg, m, 11, extra, keys, points_through=pts_thru)
            field = set(sd)
            cons = pb.consensus(cfg, rk, used, 32, field)
            cons["Seed"] = [sd[k] for k in zip(cons["LeagueID"], cons["RosterID"])]
            cons["Cons"] = range(1, len(cons) + 1)
            exact = int((cons["Cons"] == cons["Seed"]).sum())
            mad = (cons["Cons"] - cons["Seed"]).abs().mean()
            top4 = len(set(cons.nsmallest(4, "Cons")["Seed"]) & {1, 2, 3, 4})
            top8 = len(set(cons.nsmallest(8, "Cons")["Seed"]) & set(range(1, 9)))
            L.append(f"\n**Consensus vs seeds ({label}; bots used: {', '.join(names[b] for b in used)})** — "
                     f"Spearman {spearman(cons['Cons'], cons['Seed']):.3f} · mean miss {mad:.1f} seeds · "
                     f"exact {exact}/32 · top-4 {top4}/4 · top-8 {top8}/8")
            row = []
            for b in used:
                sub = rk[[k in field for k in zip(rk["LeagueID"], rk["RosterID"])]]
                s = [sd[k] for k in zip(sub["LeagueID"], sub["RosterID"])]
                row.append(f"{names[b]} {spearman(sub[b], s):.3f}")
            L.append("Each bot vs seeds (Spearman): " + " · ".join(row))
            if pts_thru is None:
                worst = cons.assign(d=(cons["Cons"] - cons["Seed"]).abs()).nlargest(5, "d")
                tn = {(r.LeagueID, r.RosterID): r.Team for r in t.itertuples()}
                L.append("Biggest disagreements: " + "; ".join(
                    f"{tn.get((r.LeagueID, r.RosterID))} seed {r.Seed} vs bots {r.Cons}" for r in worst.itertuples()))

        # Weekly: bot agreement and next-week prediction
        for w in range(2, 11):
            extra = pb.history_extra(y, w, slots)
            rk, used = pb.bot_ranks(cfg, m, w, extra, keys)
            for a, b in itertools.combinations(used, 2):
                pair_rho.setdefault((a, b), []).append(spearman(rk[a], rk[b]))
            nxt = pb.base(m, w + 1)
            nxt = nxt[nxt["Week"] == w + 1].set_index(["LeagueID", "RosterID"])["AP"]
            target = [nxt.get(k) for k in zip(rk["LeagueID"], rk["RosterID"])]
            cons = pb.consensus(cfg, rk, used, 25)
            cpos = {k: i for i, k in enumerate(zip(cons["LeagueID"], cons["RosterID"]))}
            pred.setdefault("BCS consensus", []).append(
                -spearman([cpos[k] for k in zip(rk["LeagueID"], rk["RosterID"])], target))
            for b in used:
                pred.setdefault(names[b], []).append(-spearman(rk[b], target))

    L.insert(0, f"# Poll bot backtest ({', '.join(map(str, args.years))})")
    L.append("\n## Bot agreement (Spearman, all 180, weeks 2–10, both seasons)")
    L.append("| | " + " | ".join(names[b] for b in names) + " |\n|---|" + "---|" * len(names))
    for a in names:
        cells = []
        for b in names:
            v = pair_rho.get((a, b)) or pair_rho.get((b, a))
            cells.append("—" if a == b else (f"{sum(v) / len(v):.2f}" if v else "n/a"))
        L.append(f"| {names[a]} | " + " | ".join(cells) + " |")
    L.append("\n## Predicting next week's all-play (Spearman, higher = better, avg weeks 2–10)")
    for k, v in sorted(pred.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        L.append(f"- {k}: {sum(v) / len(v):.3f}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
