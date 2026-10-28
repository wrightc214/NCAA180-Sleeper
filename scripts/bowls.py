"""
bowls.py -- bowl selection and pairings (rules: config/league.json -> postseason.bowls).

Pool: non-playoff teams with min_wins+ regular-season wins; if short, the highest-scoring
bump_wins teams move up; any surplus beyond the slots falls to the NIT. The bowl table is
processed top to bottom: rank bowls (best remaining vs next best from another league),
the reserved #1 team (Holiday), conference pairs, favored teams (keyed by league + roster
spot, name_note only labels them), favored conference pairs, then random bowls with state /
region exclusions. Never two teams from the same league.

Review step (Chris, 2026-10-27): the draw is written as a DRAFT first
(data/postseason_drafts/Bowls_<year>.csv) with its random seed recorded, so the exact same
draw is reproduced on any rerun. Chris reviews, then --publish moves it into
Postseason_Season.csv (locked; later runs only refresh scores). --redraw makes a new draft.

  python scripts/bowls.py [--year Y] [--publish | --redraw] [--data-dir DIR]
"""
import argparse
import os
import random
import sys

import pandas as pd

import _postseason_common as ps


def build_pool(year, field_path, cfg):
    """Pool + the bowls to use. Count is flexible (Chris, 2026-10-27): every non-playoff team with
    min_wins+ gets a bowl; if that's an odd number, the best bump_wins team (PointsFor) is pulled
    up -- at most max_bumps. Bowls are used from the top of the table; the rest are dropped."""
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
    slots = 2 * len(cfg["table"])
    if len(pool) > slots:
        notes.append(f"{len(pool) - slots} eligible team(s) beyond the {len(cfg['table'])} bowls fall to the NIT: "
                     + ", ".join(pool.iloc[slots:]["Team"]))
        pool = pool.head(slots)
    if len(pool) % 2:
        notes.append(f"odd pool ({len(pool)}) -- the lowest-ranked team goes to the NIT: {pool.iloc[-1]['Team']}")
        pool = pool.head(len(pool) - 1)
    table = cfg["table"][:len(pool) // 2]
    dropped = [b["name"] for b in cfg["table"][len(table):]]
    if dropped:
        notes.append(f"{len(table)} bowls used; dropped (lowest priority): {', '.join(dropped)}")
    no_week = [b["name"] for b in table if not b.get("week")]
    if no_week:
        notes.append(f"WARNING: bowl(s) in use with no week set: {', '.join(no_week)}")
    return pool.to_dict("records"), notes, table


def _draw_once(pool, table, rng):
    full = ps.league_short()
    key = lambda t: (-t["Wins"], -t["PointsFor"])  # noqa: E731
    pool = sorted(pool, key=key)
    reserved = pool[0] if any(b["type"] == "reserved_plus_league" for b in table) else None
    if reserved:
        pool = pool[1:]

    def best(lg, not_league=None):
        c = [t for t in pool if t["LeagueName"] == full[lg] and t["LeagueID"] != not_league]
        return sorted(c, key=key)[0] if c else None

    def rnd_pair(b):
        c = [t for t in pool if t["State"] != b.get("exclude_state") and (not b.get("exclude_region") or t["Region"] != b["exclude_region"])]
        c = c[:]
        rng.shuffle(c)
        for i, x in enumerate(c):
            for y in c[i + 1:]:
                if x["LeagueID"] == y["LeagueID"]:
                    continue
                if b.get("max_one_state") and x["State"] == y["State"] == b["max_one_state"]:
                    continue
                return x, y
        return None

    def find(spec):
        for t in pool:
            if t["LeagueName"] == full[spec["league"]] and str(t["RosterID"]) == str(spec["roster"]):
                return t
        return None

    out, unfilled = [], []
    for b in table:
        typ, pair = b["type"], None
        if typ == "rank":
            s = sorted(pool, key=key)
            if s:
                pair = next(((s[0], y) for y in s[1:] if y["LeagueID"] != s[0]["LeagueID"]), None)
        elif typ == "reserved_plus_league":
            y = best(b["league"], reserved["LeagueID"])
            pair = (reserved, y) if y else None
        elif typ in ("conf_pair", "favored_conf_pair"):
            x, y = best(b["leagues"][0]), best(b["leagues"][1])
            pair = (x, y) if x and y else None
            if pair is None and typ == "favored_conf_pair":
                pair = rnd_pair(b)
        elif typ == "favored_teams":
            have = [t for t in (find(s) for s in b["teams"]) if t]
            if len(have) == 2 and have[0]["LeagueID"] != have[1]["LeagueID"]:
                pair = tuple(have)
            elif len(have) >= 1:
                c = [t for t in pool if t is not have[0] and t["LeagueID"] != have[0]["LeagueID"]]
                pair = (have[0], rng.choice(c)) if c else None
            else:
                pair = rnd_pair(b)
        elif typ == "random":
            pair = rnd_pair(b)
        else:
            raise ValueError(f"unknown bowl type {typ}")
        if pair is None:
            unfilled.append(b["name"])
            continue
        out.append((b, pair[0], pair[1]))
        ids = {(pair[0]["LeagueID"], pair[0]["RosterID"]), (pair[1]["LeagueID"], pair[1]["RosterID"])}
        pool = [t for t in pool if (t["LeagueID"], t["RosterID"]) not in ids]
    return out, unfilled, pool


def draw(pool, table, rng, tries=500):
    """A random draw can paint itself into a corner (e.g. the last two teams share a league).
    Redraw from the same seeded random stream until every bowl is filled and every team placed,
    so the result is still fully reproducible from the recorded seed."""
    best = None
    for _ in range(tries):
        out = _draw_once(pool, table, rng)
        if not out[1] and not out[2]:
            return out
        if best is None or len(out[1]) + len(out[2]) < len(best[1]) + len(best[2]):
            best = out
    return best


def rows_for(year, games, seed):
    rows = []
    for i, (b, x, y) in enumerate(games, 1):
        gid = f"{year}-BOWL-{b['name'].replace(' ', '')}"
        rows += ps.game_rows(year, "Bowl", b["week"], gid, [x, y], stage="Bowl", bowl=b["name"], draw=seed)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--redraw", action="store_true")
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
        import team_names as tn
        h = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
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
    pool, notes, table = build_pool(year, field_path, cfg)
    games, unfilled, left = draw(pool, table, random.Random(seed))
    rows = rows_for(year, games, seed)
    os.makedirs(draft_dir, exist_ok=True)
    pd.DataFrame(rows, columns=ps.COLUMNS).to_csv(draft, index=False)
    print(f"Bowls {year}: DRAFT {len(games)} games, seed {seed} -> {draft}")
    for n in notes:
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
