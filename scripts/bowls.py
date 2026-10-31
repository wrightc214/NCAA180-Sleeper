"""
bowls.py -- bowl selection and pairings (rules: config/league.json -> postseason.bowls).

Redesign (Chris, 2026-10-28). The pool is unchanged: non-playoff teams with min_wins+ regular-season
wins; if the count is odd the best bump_wins team moves up (max_bumps); surplus beyond the bowl
slots falls to the NIT. Tiers then fill in order:

  Prestige (wk 16)  the top-ranked teams, best available pairings, bowls in priority order.
  Marquee  (wk 15)  each league's best remaining team, topped up by rank to 16. Pair by rank
                    (partners at most max_shift spots apart), then place every pair in the bowl
                    whose tie-ins fit best (anchor 3, primary 2, secondary 1; Wild has none). All 8
                    pairs are placed together; exact ties go to the bowl those leagues visited
                    least recently.
  Showcase (wk 14)  service + international bowls, always played. Service bowls (Poinsettia,
                    Armed Forces, Military, in that order) take school-name pool teams first --
                    the one away from that bowl longest; two pool teams meet unless it's a
                    repeat. The rest draw from the top-ranked remaining teams. Mirage excludes
                    the Armed Forces pool.
  Opening  (wk 13)  the only flexible week: as many bowls as the season needs, top of the list
                    first. HBCU-lean bowls give an unplaced HBCU team first shot. Home
                    state/region exclusions apply to random spots only.

Everywhere: never two teams from the same league, and no pairing of two franchises (league +
roster slot) that met in any postseason game or NIT group in the last repeat_seasons seasons
(Marquee: heavy penalty; random draws: hard rule, retried within the seeded stream).

Review step (Chris, 2026-10-27): the draw is written as a DRAFT (data/postseason_drafts/
Bowls_<year>.csv) with its random seed, so a rerun reproduces it exactly. Chris reviews, then
--publish moves it into Postseason_Season.csv (locked; later runs only refresh scores).

  python scripts/bowls.py [--year Y] [--publish | --redraw | --preview] [--data-dir DIR]
"""
import argparse
import itertools
import os
import random
import sys

import pandas as pd

import _postseason_common as ps
import team_names as tn

HIST = "data/Postseason_Historic.csv"


# ------------------------------------------------------------------ pool
def bowl_list(cfg):
    out = []
    for tier in cfg["tiers"]:
        for b in tier["bowls"]:
            out.append({**b, "tier": tier["name"], "week": tier["week"], "fill": tier["fill"]})
    return out


def build_pool(year, field_path, cfg):
    """(pool, notes): eligible non-playoff teams, best first. Flexible count (Chris, 2026-10-27):
    every non-playoff team with min_wins+ gets a bowl; odd count -> the best bump_wins team moves up."""
    st = ps.standings(year)
    field = pd.read_csv(field_path, dtype=str)
    field = field[field["Year"].astype(str) == str(year)]
    if field.empty or (field["BidType"] == "Tied - Unresolved").any():
        sys.exit("FATAL: playoff field missing or unresolved -- run playoff_field.py first")
    in_field = set(zip(field["LeagueID"], field["RosterID"]))
    non = st[[(l, r) not in in_field for l, r in zip(st["LeagueID"], st["RosterID"])]]
    pool = ps.rank(non[non["Wins"] >= cfg["min_wins"]])
    notes = []
    if len(pool) % 2:
        bump = ps.rank(non[non["Wins"] == cfg["bump_wins"]]).head(int(cfg.get("max_bumps", 1)))
        if len(bump):
            notes.append(f"{len(bump)} {cfg['bump_wins']}-win team(s) pulled up to make the count even: " + ", ".join(bump["Team"]))
        pool = ps.rank(pd.concat([pool, bump]))
    slots = 2 * len(bowl_list(cfg))
    if len(pool) > slots:
        notes.append(f"{len(pool) - slots} eligible team(s) beyond the {slots // 2} bowls fall to the NIT: "
                     + ", ".join(pool.iloc[slots:]["Team"]))
        pool = pool.head(slots)
    if len(pool) % 2:
        notes.append(f"odd pool ({len(pool)}) -- the lowest-ranked team goes to the NIT: {pool.iloc[-1]['Team']}")
        pool = pool.head(len(pool) - 1)
    return pool.to_dict("records"), notes


# ------------------------------------------------------------------ history
def slot(t):
    return (str(t["LeagueName"]).strip(), str(t["RosterID"]))


def history(year, cfg):
    """met: franchise pairs that met in the last repeat_seasons postseasons (any game or NIT group);
    league_visit[(bowl, league_full)] / slot_visit[(bowl, slot)] = last season there."""
    n = int(cfg.get("repeat_seasons", 3))
    ren = {k: v for k, v in cfg.get("history_names", {}).items() if not k.startswith("_")}
    met, league_visit, slot_visit = set(), {}, {}
    if not os.path.exists(HIST):
        return met, league_visit, slot_visit
    h = pd.read_csv(HIST, dtype=str, keep_default_na=False)
    for r in h.itertuples():
        y = int(r.Season)
        if y >= int(year):
            continue
        names = [x.strip() for x in r.TeamA.split("|") if x.strip()] + ([r.TeamB] if r.TeamB else [])
        slots = [s for s in ((tn.slot(y, t) or (None, None)) for t in names) if s[0]]
        slots = [(a.strip(), str(b)) for a, b in slots]
        if y >= int(year) - n:
            for a, b in itertools.combinations(slots, 2):
                met.add(frozenset((a, b)))
        if r.Event == "Bowl" and r.Bowl:
            bowl = ren.get(r.Bowl, r.Bowl)
            for s in slots:
                league_visit[(bowl, s[0])] = max(league_visit.get((bowl, s[0]), 0), y)
                slot_visit[(bowl, s)] = max(slot_visit.get((bowl, s), 0), y)
    return met, league_visit, slot_visit


# ------------------------------------------------------------------ draw
class Draw:
    def __init__(self, year, pool, cfg, rng, hist=None):
        self.year, self.cfg, self.rng = int(year), cfg, rng
        self.order = {slot(t): i for i, t in enumerate(pool)}  # pool is best-first
        self.left = list(pool)
        self.met, self.lvisit, self.svisit = hist if hist else history(year, cfg)
        full = ps.league_short()
        self.short = {v: k for k, v in full.items()}
        self.pools = {k: {tn.norm(x) for x in v} for k, v in cfg["pools"].items() if not k.startswith("_")}
        self.games, self.unfilled, self.notes = [], [], []

    # helpers
    def lg(self, t):
        return self.short.get(str(t["LeagueName"]).strip(), str(t["LeagueName"]).strip())

    def ok_pair(self, x, y):
        return x["LeagueID"] != y["LeagueID"] and frozenset((slot(x), slot(y))) not in self.met

    def take(self, *ts):
        ids = {slot(t) for t in ts}
        self.left = [t for t in self.left if slot(t) not in ids]

    def place(self, b, x, y):
        self.games.append((b, x, y))
        self.take(x, y)

    def in_pool(self, t, name):
        return tn.norm(t["Team"]) in self.pools.get(name, set())

    def allowed(self, b, t):
        """Home exclusions for random spots."""
        if b.get("exclude_state") and t.get("State") == b["exclude_state"]:
            return False
        if b.get("exclude_region") and t.get("Region") == b["exclude_region"]:
            return False
        if b.get("exclude_pool") and self.in_pool(t, b["exclude_pool"]):
            return False
        return True

    # tiers
    def prestige(self, bowls):
        for b in bowls:
            s = self.left
            pair = next(((s[0], y) for y in s[1:] if self.ok_pair(s[0], y)), None) if s else None
            if pair is None:
                self.unfilled.append(b["name"])
                continue
            self.place(b, *pair)

    def fit(self, b, t):
        lg = self.lg(t)
        if lg in b.get("anchor", []):  # a league's one home bowl (Celebration = HBCU)
            return 3
        return 2 if lg in b.get("primary", []) else 1 if lg in b.get("secondary", []) else 0

    def marquee(self, bowls, max_shift):
        n = 2 * len(bowls)
        picks, seen = [], set()
        for t in self.left:  # each league's best remaining team
            if t["LeagueID"] not in seen:
                picks.append(t)
                seen.add(t["LeagueID"])
        picks = picks[:n]
        for t in self.left:  # top up by rank
            if len(picks) >= n:
                break
            if t not in picks:
                picks.append(t)
        if len(picks) % 2:
            picks = picks[:-1]
        picks.sort(key=lambda t: self.order[slot(t)])
        bowls = bowls[:len(picks) // 2]
        if not bowls:
            return

        def novelty(b, x, y):
            yrs = [min(self.year - self.lvisit.get((b["name"], str(t["LeagueName"]).strip()), 0), 10) for t in (x, y)]
            return 0.001 * sum(yrs)

        def assign(pairs):
            """Best one-to-one placement of pairs into bowls (bitmask DP)."""
            k = len(pairs)
            val = [[self.fit(b, x) + self.fit(b, y) + novelty(b, x, y) for b in bowls] for x, y in pairs]
            dp = {0: (0.0, [])}
            for i in range(k):
                nxt = {}
                for mask, (sc, chosen) in dp.items():
                    for j in range(k):
                        if mask & (1 << j):
                            continue
                        m2, s2 = mask | (1 << j), sc + val[i][j]
                        if m2 not in nxt or s2 > nxt[m2][0]:
                            nxt[m2] = (s2, chosen + [j])
                dp = nxt
            return dp[(1 << k) - 1]

        best = None

        def search(rest, pairs, penalty):
            nonlocal best
            if not rest:
                fit_sc, chosen = assign(pairs)
                total = fit_sc - penalty
                if best is None or total > best[0] + 1e-9:
                    best = (total, list(pairs), chosen)
                return
            x, others = rest[0], rest[1:]
            px = picks.index(x)
            for y in others:
                gap = picks.index(y) - px
                if gap > max_shift:
                    break
                if x["LeagueID"] == y["LeagueID"]:
                    continue
                rep = 100 if frozenset((slot(x), slot(y))) in self.met else 0
                search([t for t in others if t is not y], pairs + [(x, y)], penalty + (gap - 1) + rep)

        search(picks, [], 0)
        if best is None:
            self.notes.append("Marquee: no pairing within the rank-shift limit; falling back to neighbours")
            pairs = [(picks[i], picks[i + 1]) for i in range(0, len(picks), 2)]
            chosen = list(range(len(pairs)))
        else:
            _, pairs, chosen = best
        for (x, y), j in sorted(zip(pairs, chosen), key=lambda p: p[1]):
            self.place(bowls[j], x, y)

    def random_fill(self, slots, candidates):
        """slots: [(bowl, fixed_team_or_None)]. Fill from candidates (list) with every rule; retries."""
        for _ in range(500):
            cand = candidates[:]
            self.rng.shuffle(cand)
            used, out, ok = set(), [], True
            for b, fixed in slots:
                if fixed is not None:
                    y = next((t for t in cand if slot(t) not in used and self.allowed(b, t) and self.ok_pair(fixed, t)), None)
                    if y is None:
                        ok = False
                        break
                    used.add(slot(y))
                    out.append((b, fixed, y))
                    continue
                pair = None
                for i, x in enumerate(cand):
                    if slot(x) in used or not self.allowed(b, x):
                        continue
                    for y in cand[i + 1:]:
                        if slot(y) in used or not self.allowed(b, y) or not self.ok_pair(x, y):
                            continue
                        if b.get("max_one_state") and x.get("State") == y.get("State") == b["max_one_state"]:
                            continue
                        pair = (x, y)
                        break
                    if pair:
                        break
                if pair is None:
                    ok = False
                    break
                used |= {slot(pair[0]), slot(pair[1])}
                out.append((b, *pair))
            if ok:
                return out
        return None

    def showcase(self, bowls):
        slots = []
        for b in bowls:
            if not b.get("pool"):
                slots.append((b, None))
                continue
            c = [t for t in self.left if self.in_pool(t, b["pool"])]
            c.sort(key=lambda t: (self.svisit.get((b["name"], slot(t)), 0), self.order[slot(t)]))
            if not c:
                slots.append((b, None))
                continue
            first = c[0]
            mate = next((t for t in c[1:] if self.ok_pair(first, t)), None)
            if mate is None and len(c) > 1:
                self.notes.append(f"{b['name']}: pool teams {first['Team']} / {c[1]['Team']} would repeat or share a league; "
                                  f"{first['Team']} keeps the spot (away longest), fresh opponent drawn")
            if mate is not None:
                self.place(b, first, mate)
            else:
                self.take(first)
                slots.append((b, first))
        need = sum(2 if f is None else 1 for _, f in slots)
        cand = self.left[:need]  # week 14 = the best remaining teams
        res = self.random_fill(slots, cand) or self.random_fill(slots, self.left[:need + 6])
        if res is None:
            self.unfilled += [b["name"] for b, _ in slots]
            return
        for b, x, y in res:
            self.games.append((b, x, y))
            self.take(x, y)

    def opening(self, bowls):
        k = min(len(self.left) // 2, len(bowls))
        bowls = bowls[:k]
        slots = []
        for b in bowls:
            fixed = None
            if b.get("lean"):
                fixed = next((t for t in self.left if self.lg(t) == b["lean"]), None)
                if fixed is not None:
                    self.take(fixed)
            slots.append((b, fixed))
        res = self.random_fill(slots, list(self.left))
        if res is None:
            self.unfilled += [b["name"] for b, _ in slots]
            return
        for b, x, y in res:
            self.games.append((b, x, y))
            self.take(x, y)

    def run(self):
        for tier in self.cfg["tiers"]:
            bowls = [{**b, "tier": tier["name"], "week": tier["week"]} for b in tier["bowls"]]
            if len(self.left) < 2:
                if tier["fill"] != "random":
                    self.unfilled += [b["name"] for b in bowls]
                continue
            if tier["fill"] == "rank":
                self.prestige(bowls[:len(self.left) // 2])
            elif tier["fill"] == "marquee":
                self.marquee(bowls, int(tier.get("max_shift", 3)))
            elif tier["fill"] == "showcase":
                self.showcase(bowls)
            elif tier["fill"] == "random":
                self.opening(bowls)
            else:
                raise ValueError(f"unknown bowl tier fill {tier['fill']}")
        return self.games, self.unfilled, self.left


def draw(year, pool, cfg, rng, hist=None):
    d = Draw(year, pool, cfg, rng, hist)
    games, unfilled, left = d.run()
    return games, unfilled, left, d.notes


def rows_for(year, games, seed):
    rows = []
    for b, x, y in games:
        gid = f"{year}-BOWL-{b['name'].replace(' ', '')}"
        rows += ps.game_rows(year, "Bowl", b["week"], gid, [x, y], stage="Bowl", bowl=b["name"], draw=seed)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--redraw", action="store_true")
    ap.add_argument("--preview", action="store_true", help="print a draw under the current rules; writes nothing")
    ap.add_argument("--from-history", action="store_true", help="replay: publish that year's actual bowls")
    ap.add_argument("--data-dir")
    a = ap.parse_args()
    year = a.year or ps.current_season()
    season_path, field_path, draft_dir = ps.paths(a)
    _, pcfg = ps.config()
    cfg = pcfg["bowls"]
    draft = os.path.join(draft_dir, f"Bowls_{year}.csv")
    season = ps.read_season(season_path)
    published = season[(season["Year"].astype(str) == str(year)) & (season["Round"] == "Bowl")]

    if a.preview:
        pool, notes = build_pool(year, field_path, cfg)
        seed = ps.draw_seed(year, "bowls")
        games, unfilled, left, dnotes = draw(year, pool, cfg, random.Random(seed))
        for b, x, y in games:
            print(f"wk{b['week']} {b['name']:<20} {x['Team']} ({x['Wins']}-{x['Losses']}) vs {y['Team']} ({y['Wins']}-{y['Losses']})")
        for n in notes + dnotes:
            print("  note:", n)
        print(f"{len(games)} bowls; unfilled {unfilled}; unplaced {[t['Team'] for t in left]}")
        return

    if len(published):  # locked: refresh scores only
        st = {(r["LeagueID"], r["RosterID"]): r for r in ps.standings(year).to_dict("records")}
        rows = []
        for gid, g in published.groupby("GameID", sort=False):
            teams = [st[(r.LeagueID, str(r.RosterID))] for r in g.itertuples()]
            r0 = g.iloc[0]
            rows += ps.game_rows(year, "Bowl", r0["Week"] or None, gid, teams, stage="Bowl", bowl=r0["BowlName"], draw=r0["DrawSeed"])
        ps.replace_rows(year, lambda r: r["Round"] != "Bowl", rows, season_path)
        print(f"Bowls {year}: locked; refreshed {len(rows) // 2} games")
        return

    if a.from_history:
        h = pd.read_csv(HIST, dtype=str, keep_default_na=False)
        h = h[(h["Season"] == str(year)) & (h["Event"] == "Bowl")]
        lg = pd.read_csv(ps.LEAGUES, dtype=str)
        lid = dict(zip(lg[lg["Year"] == str(year)]["LeagueName"].str.strip(), lg[lg["Year"] == str(year)]["LeagueID"]))
        st = {(r["LeagueID"], r["RosterID"]): r for r in ps.standings(year).to_dict("records")}
        rows = []
        for r in h.itertuples():
            teams = []
            for t in (r.TeamA, r.TeamB):
                sl = tn.slot(year, t)
                teams.append(st[(lid[sl[0].strip()], str(sl[1]))])
            rows += ps.game_rows(year, "Bowl", int(r.Week), f"{year}-BOWL-{r.Bowl.replace(' ', '')}", teams,
                                 stage="Bowl", bowl=r.Bowl, draw="history")
        ps.replace_rows(year, lambda r: r["Round"] != "Bowl", rows, season_path)
        print(f"Bowls {year}: published {len(rows) // 2} games from history")
        return

    if a.publish:
        if not os.path.exists(draft):
            sys.exit(f"FATAL: no draft to publish ({draft})")
        d = ps.read_season(draft)
        ps.replace_rows(year, lambda r: r["Round"] != "Bowl", d.to_dict("records"), season_path)
        print(f"Bowls {year}: published {len(d) // 2} games from {draft}")
        return

    if os.path.exists(draft) and not a.redraw:
        print(f"Bowls {year}: draft awaiting review ({draft}); publish with --publish or --redraw for a new draw")
        return

    prev = ps.read_season(draft)["DrawSeed"].iloc[0] if os.path.exists(draft) else None
    seed = int(prev) + 1 if prev else ps.draw_seed(year, "bowls")
    pool, notes = build_pool(year, field_path, cfg)
    games, unfilled, left, dnotes = draw(year, pool, cfg, random.Random(seed))
    rows = rows_for(year, games, seed)
    os.makedirs(draft_dir, exist_ok=True)
    pd.DataFrame(rows, columns=ps.COLUMNS).to_csv(draft, index=False)
    print(f"Bowls {year}: DRAFT {len(games)} games, seed {seed} -> {draft}")
    for n in notes + dnotes:
        print("  note:", n)
    if unfilled:
        print(f"  WARNING: {len(unfilled)} bowl(s) unfilled: {', '.join(unfilled)}")
    if left:
        print(f"  WARNING: {len(left)} eligible team(s) not placed: {', '.join(t['Team'] for t in left)}")
    if not cfg.get("review_before_publish", True):
        ps.replace_rows(year, lambda r: r["Round"] != "Bowl", rows, season_path)
        print("  published (review_before_publish is off)")


if __name__ == "__main__":
    main()
