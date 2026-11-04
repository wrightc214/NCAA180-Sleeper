"""
playoff_bracket.py -- fixed-seed single-elimination playoff (Chris, 2026-10-27: 1v32, 2v31...,
no reseeding, no byes). Round r is played in week playoff.first_week + r - 1.

Seeds come from postseason.playoff.seeding:
  "bots"    -> the poll's Seeding ballot (Poll_Season.csv / Poll_Historic.csv, PollType=Seeding)
  "manual"  -> playoff.manual_seeds_file (Year, Seed, LeagueName, RosterID) e.g. a manager panel
  --seeds history  -> the seeds actually used that year (Postseason_Historic; replays only)
Rebuilt deterministically every run from seeds + finished results (nothing random to lock).
A tie in a game is flagged and stops that branch (exit 1).
Review step (Chris, 2026-11-03; postseason.playoff.review_before_publish): until the bracket is
published, a run writes a DRAFT (data/postseason_drafts/Playoff_<year>.csv: seeds + first-round
pairings), from the live field or, if that isn't published yet, the field draft. --publish needs
the published field, checks the pairings still match the draft, then writes the live bracket.
After that every run refreshes results as before. --data-dir runs skip the review.
--auto (weekly job): drafts only when a field (draft or live) and the seeding ballot exist and the
bracket isn't published; writes + flags for the LM preview only when the draft is new or changed.

  python scripts/playoff_bracket.py [--year 2026] [--seeds bots|manual|history] [--data-dir DIR]
"""
import argparse
import os
import sys

import pandas as pd

import _postseason_common as ps
import team_names as tn


def bracket_order(n):
    order = [1, 2]
    while len(order) < n:
        size = len(order) * 2
        order = [x for s in order for x in (s, size + 1 - s)]
    return order


def load_seeds(year, source, field_teams):
    _, cfg = ps.config()
    if source == "bots":
        path = "data/Poll_Season.csv" if year == ps.current_season() else "data/Poll_Historic.csv"
        p = pd.read_csv(path, dtype=str)
        p = p[(p["Year"] == str(year)) & (p["PollType"] == "Seeding")]
        seeds = {(r.LeagueID, r.RosterID): int(float(r.Rank)) for r in p.itertuples()}
    elif source == "manual":
        f = cfg["playoff"]["manual_seeds_file"]
        if not os.path.exists(f):
            sys.exit(f"FATAL: manual seeding selected but {f} doesn't exist")
        p = pd.read_csv(f, dtype=str)
        p = p[p["Year"] == str(year)]
        ids = {(r.LeagueName.strip(), r.RosterID): r.LeagueID for r in field_teams.itertuples()} if len(field_teams) else {}
        seeds = {(ids.get((r.LeagueName.strip(), r.RosterID), ""), r.RosterID): int(r.Seed) for r in p.itertuples()}
    elif source == "history":
        h = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
        h = h[(h["Season"] == str(year)) & (h["Event"] == "Playoff") & (h["Round"] == "1")]
        lg = pd.read_csv(ps.LEAGUES, dtype=str)
        lg = lg[lg["Year"] == str(year)]
        lid = dict(zip(lg["LeagueName"].str.strip(), lg["LeagueID"]))
        seeds = {}
        for r in h.itertuples():
            for t, s in ((r.TeamA, r.SeedA), (r.TeamB, r.SeedB)):
                sl = tn.slot(year, t)
                if sl is None or not s:
                    sys.exit(f"FATAL: can't resolve {t} / seed {s} for {year}")
                seeds[(lid[sl[0].strip()], str(sl[1]))] = int(s)
    else:
        sys.exit(f"FATAL: unknown seeding source {source}")
    return seeds


def mark_new_draft():
    """Tell the workflow a new/changed draft exists (postseason_preview posts it to LM)."""
    os.makedirs("work", exist_ok=True)
    open("work/postseason_draft.new", "a").close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--seeds")
    ap.add_argument("--data-dir")
    ap.add_argument("--publish", action="store_true", help="approve the draft: write the live bracket")
    ap.add_argument("--auto", action="store_true", help="weekly job: draft once field + seeding ballot exist, else no-op")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, field_path, draft_dir = ps.paths(a)
    _, cfg = ps.config()
    pc = cfg["playoff"]
    season = ps.read_season(season_path)
    published = ((season["Year"].astype(str) == str(year)) & (season["Round"] == "Playoff")).any()
    review = bool(pc.get("review_before_publish", True)) and not a.data_dir and not published
    draft = os.path.join(draft_dir, f"Playoff_{year}.csv")
    field_draft = os.path.join(draft_dir, f"PlayoffField_{year}.csv")
    live_field = os.path.exists(field_path) and (pd.read_csv(field_path, dtype=str)["Year"].astype(str) == str(year)).any()
    if review and a.publish and not live_field:
        sys.exit("FATAL: publish the playoff field first (playoff_field.py --publish)")
    if review and not live_field and os.path.exists(field_draft):
        field_path = field_draft  # draft bracket from the draft field
    if a.auto and (not review or not (live_field or os.path.exists(field_draft))):
        print(f"Playoff {year}: " + ("published; refresh runs manually" if published else "no field yet"))
        return
    n = int(pc["field_size"])
    if n & (n - 1):
        sys.exit(f"FATAL: field_size {n} is not a power of two (byes aren't supported)")
    field = pd.read_csv(field_path, dtype=str) if os.path.exists(field_path) else pd.DataFrame()
    field = field[field["Year"].astype(str) == str(year)] if len(field) else field
    if len(field) and (field["BidType"] == "Tied - Unresolved").any():
        sys.exit("FATAL: the playoff field has an unresolved bubble tie")
    seeds = load_seeds(year, a.seeds or pc.get("seeding", "bots"), field)
    if a.auto and sorted(seeds.values()) != list(range(1, n + 1)):
        print(f"Playoff {year}: waiting for the seeding ballot")
        return
    if sorted(seeds.values()) != list(range(1, n + 1)):
        sys.exit(f"FATAL: seeds for {year} aren't exactly 1..{n} (got {len(seeds)} teams)")
    if len(field) and set(seeds) != set(zip(field["LeagueID"], field["RosterID"])):
        diff = set(seeds) ^ set(zip(field["LeagueID"], field["RosterID"]))
        sys.exit(f"FATAL: seeded teams don't match the playoff field ({len(diff)} differ)")
    st = ps.standings(year)
    team = {(r["LeagueID"], r["RosterID"]): r for r in st.to_dict("records")}
    by_seed = {s: team[k] for k, s in seeds.items()}
    order = bracket_order(n)
    current = [[by_seed[order[2 * i]], by_seed[order[2 * i + 1]]] for i in range(n // 2)]
    rounds = pc["rounds"]
    rows, problems = [], []
    for r_i, label in enumerate(rounds, 1):
        week = int(pc["first_week"]) + r_i - 1
        nxt = []
        for g_i, pair in enumerate(current, 1):
            if pair is None:
                nxt.append(None)
                continue
            gid = f"{year}-PO-R{r_i}-G{g_i:02d}"
            gr = ps.game_rows(year, "Playoff", week, gid, pair, stage=label, playoff_round=r_i, seeds=seeds)
            rows += gr
            w = [r for r in gr if r["Outcome"] == "Win"]
            if any(r["Outcome"] == "Tie" for r in gr):
                problems.append(f"{label} {gid}: exact tie -- resolve manually")
            nxt.append(team[(w[0]["LeagueID"], w[0]["RosterID"])] if w else None)
        if len(nxt) == 1:
            break
        current = [[nxt[2 * i], nxt[2 * i + 1]] if nxt[2 * i] and nxt[2 * i + 1] else None for i in range(len(nxt) // 2)]
        if all(p is None for p in current):
            break
    if review:
        r1 = sorted((r["GameID"], r["LeagueID"], str(r["RosterID"]), str(r["Seed"])) for r in rows if str(r["PlayoffRound"]) == "1")
        if not a.publish:
            os.makedirs(draft_dir, exist_ok=True)
            if a.auto and os.path.exists(draft):
                old1 = sorted((r.GameID, r.LeagueID, str(r.RosterID), str(r.Seed)) for r in ps.read_season(draft).itertuples()
                              if str(r.PlayoffRound) == "1")
                if old1 == r1:
                    print(f"Playoff {year}: draft unchanged ({draft})")
                    return
            pd.DataFrame(rows, columns=ps.COLUMNS).to_csv(draft, index=False)
            mark_new_draft()
            print(f"Playoff {year}: DRAFT seeds + {len(r1) // 2} first-round games -> {draft} "
                  f"(awaiting review; approve with --publish / script playoff_publish)")
            return
        if not os.path.exists(draft):
            sys.exit(f"FATAL: no bracket draft to publish ({draft}); run playoff_bracket first")
        d = ps.read_season(draft)
        d1 = sorted((r.GameID, r.LeagueID, str(r.RosterID), str(r.Seed)) for r in d.itertuples() if str(r.PlayoffRound) == "1")
        if d1 != r1:
            sys.exit("FATAL: seeds or pairings changed since the draft was previewed -- rerun playoff_bracket for a new draft")
    ps.replace_rows(year, lambda r: r["Round"] != "Playoff", rows, season_path)
    print(f"Playoff {year}: {len(rows) // 2} games written ({sum(r['Status'] == 'Final' for r in rows) // 2} final) -> {season_path}")
    for p in problems:
        print("WARNING:", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
