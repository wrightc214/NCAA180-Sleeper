"""
champions_league.py -- the Champions League (config/champions_league.json; CW, 2026-11-21).

A shadow event computed from home-league scores. 33 teams chosen from the previous season play
three-team pods every week (weeks 1-16, fixed schedule data/champions_league/schedule.csv), then the
top 3 play the Triad Cup (weeks 17-18, combined score + head start). Planning docs:
todo/todo-champions-league.md (rules) and todo/todo-champions-league-build.md (build).

Selection (a finished season Y -> the field for Y+1):
  ladder (Final Four, NIT champion, snub, defending champion; a team already in folds) ->
  at-large by the lowest sum of three ranks (all-play wins weeks 1-11, best-ball total weeks 1-18,
  final BotConsensus poll) with the league guarantee -> every team ranked by the tiebreak steps ->
  seed = that rank (seeds are the schedule's positions 1-33).
  Seasons up to 2025 use official scoring (results stand as played); 2026+ standard scoring
  (_postseason_common.week_points). Best ball = Sleeper official max points (MaxPoints_Season.csv,
  or the history backfill player points for past seasons), the same source as the poll's Headliner bot.

Usage (CWD = repo root):
  python scripts/champions_league.py                  weekly: every enabled season's results + the
                                                      Selection projection -> data/scoreboard/<season>/champions-league.json
  python scripts/champions_league.py --lock Y         build + freeze the field for Y+1 from season Y
                                                      -> data/champions_league/field_<Y+1>.csv (refuses to overwrite)
  python scripts/champions_league.py --lock Y --force rebuild an existing field file
  python scripts/champions_league.py --verify-owners S  check season S's field against current owners;
                                                      replaces teams whose owner changed (before week 1 only)
  --out-dir DIR    write under DIR instead of data/ (tests, replays)
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
import _postseason_common as psc  # noqa: E402
import team_names as tn  # noqa: E402

CONFIG = lcfg.ROOT / "config" / "champions_league.json"
FIELD_DIR = "data/champions_league"
FIELD_COLS = ["Seed", "LeagueName", "RosterID", "Team", "League", "Route", "AllPlay", "AllPlayRank",
              "BestBall", "BestBallRank", "PollRank", "RankSum", "WorstRank", "Playoff", "OwnerID",
              "QualifyingSeason", "LockedAt"]
EPS = 1e-9


def settings():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ schedule

def load_schedule(path):
    """{week: [(posA, posB, posC), ...]} from the fixed schedule file."""
    s = pd.read_csv(path)
    out = {}
    for r in s.itertuples():
        out.setdefault(int(r.Week), []).append((int(r.PosA), int(r.PosB), int(r.PosC)))
    return out


def validate_schedule(sched, size=33):
    """Raise if any week doesn't use every position once or any pair doesn't meet exactly once."""
    seen = {}
    for w, pods in sched.items():
        flat = sorted(p for pod in pods for p in pod)
        if flat != list(range(1, size + 1)):
            raise ValueError(f"schedule week {w}: positions are not 1..{size} exactly once")
        for pod in pods:
            for i in range(3):
                for j in range(i + 1, 3):
                    k = tuple(sorted((pod[i], pod[j])))
                    seen[k] = seen.get(k, 0) + 1
    pairs = size * (size - 1) // 2
    if len(seen) != pairs or set(seen.values()) != {1}:
        raise ValueError(f"schedule: {len(seen)} of {pairs} pairs meet, counts {sorted(set(seen.values()))}")
    return True


# ------------------------------------------------------------------ pod scoring

def pod_points(scores, points=(3, 1, 0)):
    """{team: pod points} for one pod. scores = {team: score}. Tied teams split the points of the
    places they share, so every pod awards sum(points)."""
    order = sorted(scores, key=lambda t: -scores[t])
    out, i = {}, 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and abs(scores[order[j + 1]] - scores[order[i]]) < EPS:
            j += 1
        share = sum(points[i:j + 1]) / (j - i + 1)
        for k in range(i, j + 1):
            out[order[k]] = share
        i = j + 1
    return out


def allplay_wins(week_scores):
    """{team: teams outscored (ties count half)} for one week's {team: score}."""
    vals = list(week_scores.values())
    return {t: sum(1.0 if s > o + EPS else 0.5 if abs(s - o) < EPS else 0.0 for o in vals) - 0.5
            for t, s in week_scores.items()}


# ------------------------------------------------------------------ tiebreaks

class Ties:
    """Tiebreak context. metrics: {step: {team: value}} where LOWER wins (negate 'higher is better').
    weekly: {week: {team: score}} for h2h. names: {team: display name} (coin tosses, logs)."""

    def __init__(self, season, metrics, weekly, h2h_last, names, recorded=()):
        self.season, self.metrics, self.weekly = season, metrics, weekly
        self.h2h_last, self.names, self.recorded = int(h2h_last), names, list(recorded or [])
        self.log = []

    def coin(self, teams):
        names = sorted(self.names.get(t, str(t)) for t in teams)
        for r in self.recorded:
            if str(r.get("season")) == str(self.season) and sorted(r.get("teams", [])) == names:
                by = {self.names.get(t, str(t)): t for t in teams}
                order = [by[n] for n in r.get("order", []) if n in by]
                if len(order) == len(teams):
                    self.log.append(f"coin toss (recorded): {' > '.join(r['order'])}")
                    return order
        key = lambda t: hashlib.sha256(f"{self.season}|{self.names.get(t, t)}".encode()).hexdigest()
        order = sorted(teams, key=key)
        self.log.append("coin toss (simulated; record a real toss in coin_toss_results): "
                        + " > ".join(self.names.get(t, str(t)) for t in order))
        return order

    def _metric(self, teams, step):
        vals = {t: self.metrics[step][t] for t in teams}
        best, worst = min(vals.values()), max(vals.values())
        tops = [t for t in teams if abs(vals[t] - best) < EPS]
        if len(tops) == 1:
            return ("win", tops[0])
        bottoms = [t for t in teams if abs(vals[t] - worst) < EPS]
        if len(bottoms) == 1:
            return ("drop", bottoms[0])
        return None

    def _h2h(self, teams, start):
        weeks = [w for w in range(start, self.h2h_last + 1) if w in self.weekly]
        if not weeks:
            return None

        def beats(a, b):
            wa = sum(1 for w in weeks if self.weekly[w].get(a, 0) > self.weekly[w].get(b, 0) + EPS)
            wb = sum(1 for w in weeks if self.weekly[w].get(b, 0) > self.weekly[w].get(a, 0) + EPS)
            return (wa > wb) - (wa < wb)
        res = {a: [beats(a, b) for b in teams if b != a] for a in teams}
        win = [a for a in teams if all(x > 0 for x in res[a])]
        if len(win) == 1:
            return ("win", win[0])
        lose = [a for a in teams if all(x < 0 for x in res[a])]
        if len(lose) == 1:
            return ("drop", lose[0])
        return None

    def decide(self, teams, steps):
        for step in steps:
            if step == "coin_toss":
                return ("order", self.coin(teams))
            if step == "h2h":
                for start in range(1, self.h2h_last + 1):
                    r = self._h2h(teams, start)
                    if r:
                        return r
                continue
            r = self._metric(teams, step)
            if r:
                return r
        return ("order", self.coin(teams))

    def rank_order(self, teams, steps):
        """Rank a whole list: sort by the first step, then break each group tied on it with order().
        The multi-team rules apply only among teams still tied, never across the whole list."""
        first = steps[0]
        if first not in self.metrics:
            return self.order(teams, steps)
        out, group, cur = [], [], None
        for t in sorted(teams, key=lambda t: self.metrics[first][t]):
            v = self.metrics[first][t]
            if group and abs(v - cur) >= EPS:
                out += self.order(group, steps)
                group = []
            group.append(t)
            cur = v
        return out + (self.order(group, steps) if group else [])

    def order(self, teams, steps):
        """Teams still tied, best-first. At every step: a team that beats all the others wins (placed next);
        else one that loses to all the others drops (placed last of the rest); else the next step.
        After a win or a drop the rest start over from the first step."""
        front, back, rest = [], [], list(teams)
        while len(rest) > 1:
            kind, val = self.decide(rest, steps)
            if kind == "win":
                front.append(val)
                rest.remove(val)
            elif kind == "drop":
                back.insert(0, val)
                rest.remove(val)
            else:
                front += val
                rest = []
        return front + rest + back


def ranks(values, higher_better=True):
    """{team: rank} with equal values sharing the best rank (1 = best)."""
    s = pd.Series(values, dtype=float)
    return s.rank(method="min", ascending=not higher_better).astype(int).to_dict()


# ------------------------------------------------------------------ season inputs

class SeasonData:
    """One season's teams and measures, keyed (LeagueName, RosterID) — the team slot."""

    def __init__(self, year, through=None):
        self.year = int(year)
        self.mode = psc.mode(year)
        m = psc._matchups(year)
        done = sorted(psc.completed_weeks(year))
        self.done = [w for w in done if through is None or w <= int(through)]
        self.lid, self.owner, self.ids = {}, {}, {}
        for r in m.sort_values("Week").itertuples():
            k = (r.LeagueName.strip(), str(r.RosterID))
            self.lid[k] = str(r.LeagueID)
            self.ids[(str(r.LeagueID), str(r.RosterID))] = k
            if isinstance(r.OwnerID, str) and r.OwnerID and (not self.done or r.Week <= max(self.done)):
                self.owner[k] = r.OwnerID
        self.teams = sorted(self.lid)
        short = {k.upper(): v for k, v in lcfg.league_display().items()}
        self.league = {k: short.get(k[0].upper(), k[0]) for k in self.teams}
        self.name = {k: tn.season_name(self.year, k[0], k[1]) or f"{k[0]} #{k[1]}" for k in self.teams}
        self._weekly = {}

    def weekly(self, w):
        """{team: result points} (standard from 2026, official before)."""
        if w not in self._weekly:
            pts = psc.week_points(self.year, w)
            self._weekly[w] = {self.ids[key]: v[0] for key, v in pts.items() if key in self.ids}
        return self._weekly[w]

    def allplay(self, first, last):
        tot = {k: 0.0 for k in self.teams}
        for w in self.done:
            if first <= w <= last:
                for k, v in allplay_wins(self.weekly(w)).items():
                    tot[k] = tot.get(k, 0.0) + v
        return tot

    def bestball(self, first, last):
        tot = {k: 0.0 for k in self.teams}
        for (lid, rid, w), v in max_points(self.year).items():
            k = self.ids.get((lid, rid))
            if k and first <= w <= last and w in self.done:
                tot[k] += v
        return tot

    def poll(self, poll_type):
        """({team: rank}, through_week) from the latest poll of poll_type (missing teams rank last)."""
        f = "data/Poll_Season.csv" if self.year == psc.current_season() else "data/Poll_Historic.csv"
        p = pd.read_csv(f, dtype={"LeagueID": str, "RosterID": str})
        p = p[(p["Year"] == self.year) & (p["PollType"] == poll_type)]
        if self.done:
            p = p[p["ThroughWeek"] <= max(self.done)]
        if not len(p):
            return {k: len(self.teams) for k in self.teams}, None
        wk = int(p["ThroughWeek"].max())
        p = p[p["ThroughWeek"] == wk]
        rk = {self.ids[(r.LeagueID, r.RosterID)]: int(r.Rank) for r in p.itertuples() if (r.LeagueID, r.RosterID) in self.ids}
        last = max(rk.values(), default=0) + 1
        return {k: rk.get(k, last) for k in self.teams}, wk

    def postseason(self):
        """{'final_four': [...], 'nit_champion': team|None, 'playoff': set(...)} (empty until played)."""
        out = {"final_four": [], "nit_champion": None, "playoff": set()}
        if self.year == psc.current_season():
            df = psc.read_season()
            if not len(df):
                return out
            df = df[df["Year"].astype(str) == str(self.year)]
            key = lambda r: self.ids.get((str(r.LeagueID), str(r.RosterID)))
            pl = df[df["Round"] == "Playoff"]
            out["playoff"] = {key(r) for r in pl[pl["PlayoffRound"].astype(str) == "1"].itertuples()} - {None}
            for rnd, g in pl.groupby(pl["PlayoffRound"].astype(str)):
                if len(g) == 4:
                    out["final_four"] = [key(r) for r in g.itertuples() if key(r)]
            nit = df[(df["Round"] == "NIT") & (df["Status"].astype(str).str.lower() == "final")]
            if len(nit) and int(nit["Week"].astype(int).max()) == int(lcfg.cfg()["postseason"].get("nit", {}).get("last_week", 17)):
                last = nit[nit["Week"].astype(int) == nit["Week"].astype(int).max()]
                if last["GameID"].nunique() == 1:
                    best = last.loc[pd.to_numeric(last["Points"], errors="coerce").idxmax()]
                    out["nit_champion"] = key(best)
            return out
        import poll_bots
        import poll_common as pc
        p = pd.read_csv("data/Postseason_Historic.csv", dtype=str)
        p = p[p["Season"] == str(self.year)]
        look = poll_bots.name_lookup(self.year)

        def team(name):
            if not isinstance(name, str) or not name.strip():
                return None
            hit = look.get(pc.norm(name)) or look.get(pc.full_key(name))
            return self.ids.get(hit) if hit else None
        pl = p[p["Event"] == "Playoff"].copy()
        pl["R"] = pl["Round"].astype(int)
        out["playoff"] = {team(x) for r in pl[pl["R"] == 1].itertuples() for x in (r.TeamA, r.TeamB)} - {None}
        for rnd, g in pl.groupby("R"):
            if len(g) == 2:
                out["final_four"] = [t for r in g.itertuples() for t in (team(r.TeamA), team(r.TeamB)) if t]
        nit = p[p["Event"] == "NIT"].copy()
        if len(nit):
            nit["R"] = nit["Round"].astype(int)
            fin = nit[nit["R"] == nit["R"].max()]
            if len(fin) == 1 and isinstance(fin["Winner"].iloc[0], str):
                out["nit_champion"] = team(fin["Winner"].iloc[0])
        return out


_MAX = {}


def max_points(year):
    """{(LeagueID, RosterID, week): best possible lineup points} (Sleeper official scoring)."""
    year = int(year)
    if year in _MAX:
        return _MAX[year]
    out = {}
    if year == psc.current_season() and os.path.exists("data/MaxPoints_Season.csv"):
        m = pd.read_csv("data/MaxPoints_Season.csv", dtype={"LeagueID": str, "RosterID": str})
        m = m[m["Year"] == year]
        out = {(r.LeagueID, r.RosterID, int(r.Week)): float(r.MaxPoints) for r in m.itertuples()}
    else:
        import poll_bots
        mx = poll_bots.history_extra(year, 18, poll_bots.league_slots(year)).get("maxpts")
        if mx is None:
            raise SystemExit(f"No max points for {year} (history backfill PlayerPoints_{year} missing)")
        out = {(str(r.LeagueID), str(r.RosterID), int(r.Week)): float(r.MaxPoints) for r in mx.itertuples()}
    _MAX[year] = out
    return out


# ------------------------------------------------------------------ selection

def select(year, c=None, through=None, exclude=(), keep_seeds=None, defending=None, data=None):
    """Field for year+1 from season `year`. Returns dict with rows (best seed first), out (first 7 out),
    collapsed ladder lines and the tie log. exclude: team slots that may not enter (ownership check).
    keep_seeds: {team: seed} to keep (published schedule): new teams take the vacated seeds."""
    c = c or settings()
    sel, tb = c["selection"], c["tiebreak"]
    d = data or SeasonData(year, through)
    size = int(c["field_size"])
    teams = [t for t in d.teams if t not in set(exclude)]
    ap = d.allplay(*sel["allplay_weeks"])
    bb = d.bestball(*sel["bestball_weeks"])
    pr, poll_week = d.poll(sel["poll_type"])
    apr, bbr = ranks({t: ap[t] for t in d.teams}), ranks({t: bb[t] for t in d.teams})
    rsum = {t: apr[t] + bbr[t] + pr[t] for t in d.teams}
    worst = {t: max(apr[t], bbr[t], pr[t]) for t in d.teams}
    weekly = {w: d.weekly(w) for w in d.done if w <= int(tb["h2h_last_week"])}
    ties = Ties(year, {"rank_sum": rsum, "best_worst_rank": worst, "bestball_total": {t: -bb[t] for t in d.teams},
                       "allplay": {t: -ap[t] for t in d.teams}},
                weekly, tb["h2h_last_week"], d.name, tb.get("coin_toss_results"))
    order = ties.rank_order(teams, tb["selection_steps"])
    post = d.postseason()
    lines = []
    for line in sel["ladder"]:
        if line == "final_four":
            lines += [("Final Four", t) for t in post["final_four"]] or [("Final Four", None)]
        elif line == "nit_champion":
            lines.append(("NIT champion", post["nit_champion"]))
        elif line == "snub":
            snub = None
            if post["playoff"] and poll_week:
                cand = sorted((t for t in teams if t not in post["playoff"]), key=lambda t: pr[t])
                snub = cand[0] if cand else None
            lines.append(("Snub", snub))
        elif line == "defending_champion":
            on = int(year) + 1 >= int(sel.get("defending_champion_from", 9999))
            lines.append(("Defending champion", defending if on else None))
    field, route, collapsed = [], {}, []
    for name, t in lines:
        if t is None:
            collapsed.append({"line": name, "team": None, "why": "not decided" if name != "Defending champion" else "not active"})
        elif t in route or t in set(exclude):
            collapsed.append({"line": name, "team": d.name[t], "why": "already in" if t in route else "excluded"})
        else:
            field.append(t)
            route[t] = name
    leagues = sorted({t[0] for t in d.teams})
    rest = [t for t in order if t not in route]
    while len(field) < size and rest:
        missing = [lg for lg in leagues if lg not in {t[0] for t in field}]
        if sel.get("league_guarantee", True) and missing and len(missing) >= size - len(field):
            for lg in missing:
                t = next((x for x in rest if x[0] == lg), None)
                if t and len(field) < size:
                    field.append(t)
                    route[t] = "League guarantee"
                    rest.remove(t)
            break
        t = rest.pop(0)
        field.append(t)
        route[t] = "At-large"
    ranked = [t for t in order if t in route]
    seeds = {t: i + 1 for i, t in enumerate(ranked)}
    if keep_seeds:
        kept = {t: s for t, s in keep_seeds.items() if t in route}
        free = sorted(set(range(1, size + 1)) - set(kept.values()))
        newcomers = [t for t in ranked if t not in kept]
        seeds = {**kept, **dict(zip(newcomers, free))}
    stamp = now_iso()

    def row(t, seed=None):
        return {"Seed": seed, "LeagueName": t[0], "RosterID": t[1], "Team": d.name[t], "League": d.league[t],
                "Route": route.get(t, ""), "AllPlay": round(ap[t], 1), "AllPlayRank": apr[t], "BestBall": round(bb[t], 2),
                "BestBallRank": bbr[t], "PollRank": pr[t], "RankSum": rsum[t], "WorstRank": worst[t],
                "Playoff": int(t in post["playoff"]), "OwnerID": d.owner.get(t, ""), "QualifyingSeason": int(year),
                "LockedAt": stamp}
    rows = sorted((row(t, seeds[t]) for t in field), key=lambda r: r["Seed"])
    out = [row(t) for t in rest[:7]]
    return {"rows": rows, "out": out, "collapsed": collapsed, "ties": ties.log, "poll_week": poll_week,
            "through_week": max(d.done) if d.done else 0, "leagues": len(leagues)}


def field_path(season, out_dir=None):
    return os.path.join(out_dir or FIELD_DIR, f"field_{int(season)}.csv")


def read_field(season, out_dir=None):
    p = field_path(season, out_dir)
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, dtype={"RosterID": str, "OwnerID": str}, keep_default_na=False)


def defending_champion(year, out_dir=None):
    p = os.path.join(out_dir or "data/scoreboard", str(int(year)), "champions-league.json")
    try:
        cup = json.load(open(p, encoding="utf-8")).get("cup") or {}
    except (FileNotFoundError, ValueError):
        return None
    ch = cup.get("champion")
    return (ch["league_name"], str(ch["roster"])) if ch else None


def lock(year, out_dir=None, force=False, exclude=(), keep_seeds=None, c=None):
    """Freeze the field for year+1."""
    c = c or settings()
    path = field_path(int(year) + 1, out_dir)
    if os.path.exists(path) and not force:
        raise SystemExit(f"{path} exists (use --force to rebuild)")
    res = select(year, c, exclude=exclude, keep_seeds=keep_seeds, defending=defending_champion(year))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame(res["rows"], columns=FIELD_COLS).to_csv(path, index=False)
    for line in res["ties"]:
        print("tiebreak:", line)
    print(f"Champions League {int(year) + 1}: field locked from {year} ({len(res['rows'])} teams) -> {path}")
    return res


def verify_owners(season, current_owner, out_dir=None, today=None, c=None):
    """Replace field teams whose owner changed since the lock. current_owner: {team slot: OwnerID}.
    Before the schedule publish date the field is re-seeded; after it replacements take the vacated
    seed. Returns the list of replaced teams (empty = nothing to do)."""
    c = c or settings()
    f = read_field(season, out_dir)
    if f is None:
        raise SystemExit(f"no field file for {season}")
    changed = [(r.LeagueName, str(r.RosterID)) for r in f.itertuples()
               if r.OwnerID and current_owner.get((r.LeagueName, str(r.RosterID))) not in (None, r.OwnerID)]
    if not changed:
        return []
    today = today or dt.date.today()
    pub = c.get("schedule_publish_date", {}).get(str(season))
    published = bool(pub) and today >= dt.date.fromisoformat(pub)
    xpath = os.path.join(out_dir or FIELD_DIR, f"excluded_{int(season)}.csv")
    old = pd.read_csv(xpath, dtype=str) if os.path.exists(xpath) else pd.DataFrame(columns=["LeagueName", "RosterID", "Team", "LockedOwner", "NewOwner", "At"])
    old_excl = [(r.LeagueName, str(r.RosterID)) for r in old.itertuples()]
    names = {(r.LeagueName, str(r.RosterID)): (r.Team, r.OwnerID) for r in f.itertuples()}
    add = pd.DataFrame([{"LeagueName": t[0], "RosterID": t[1], "Team": names[t][0], "LockedOwner": names[t][1],
                         "NewOwner": current_owner.get(t), "At": now_iso()} for t in changed])
    pd.concat([old, add], ignore_index=True).to_csv(xpath, index=False)
    keep = {(r.LeagueName, str(r.RosterID)): int(r.Seed) for r in f.itertuples()} if published else None
    if keep:
        for t in changed:
            keep.pop(t, None)
    lock(int(season) - 1, out_dir, force=True, exclude=set(changed) | set(old_excl), keep_seeds=keep, c=c)
    return changed


# ------------------------------------------------------------------ the season

def standings(field, sched, weekly, c, ties_names, season, bestball=None):
    """Pod results for every played pod week. field: {seed: team}; weekly: {week: {team: score}}.
    Returns (table rows, week results, cup seeds or None)."""
    pts = {t: 0.0 for t in field.values()}
    rec = {t: [0, 0, 0] for t in field.values()}
    ap = {t: 0.0 for t in field.values()}
    weeks = []
    first, last = c["pod_weeks"]
    for w in range(int(first), int(last) + 1):
        if w not in weekly:
            break
        sc = weekly[w]
        if any(t not in sc for t in field.values()):
            print(f"WARNING: week {w}: {sum(t not in sc for t in field.values())} field team(s) have no score; counted as 0")
        sc = {t: float(sc.get(t, 0.0)) for t in field.values()}
        for t, v in allplay_wins(sc).items():
            ap[t] += v
        pods = []
        for pod in sched[w]:
            teams = [field[p] for p in pod]
            pp = pod_points({t: sc[t] for t in teams}, c["pod_points"])
            for t in teams:
                pts[t] += pp[t]
                beat = sum(sc[t] > sc[o] + EPS for o in teams if o != t)
                rec[t][{2: 0, 1: 1, 0: 2}.get(beat, 2)] += 1
            pods.append([{"seed": p, "score": round(sc[field[p]], 2), "pts": pp[field[p]]} for p in pod])
        weeks.append({"week": w, "pods": pods})
    seed_of = {t: s for s, t in field.items()}
    rk = ranks(pts)
    table = sorted(({"seed": seed_of[t], "rank": rk[t], "pts": pts[t], "sweeps": rec[t][0], "splits": rec[t][1],
                     "losses": rec[t][2], "allplay": ap[t]} for t in field.values()), key=lambda r: (r["rank"], r["seed"]))
    cup = None
    if weeks and weeks[-1]["week"] == int(last):
        tb = c["tiebreak"]
        bb_season = {t: -float((bestball or {}).get(t, 0.0)) for t in field.values()}
        ties = Ties(season, {"allplay": {t: -ap[t] for t in field.values()}, "bestball_total": bb_season},
                    {w: s for w, s in weekly.items() if w <= int(tb["h2h_last_week"])}, tb["h2h_last_week"],
                    ties_names, tb.get("coin_toss_results"))
        # pod points first: break ties only inside the group straddling the cut
        order = sorted(field.values(), key=lambda t: -pts[t])
        n = int(c["cup_size"])
        line = pts[order[n - 1]]
        above = [t for t in order if pts[t] > line + EPS]
        tied = [t for t in order if abs(pts[t] - line) < EPS]
        cup = above + ties.order(tied, tb["cup_steps"])[:n - len(above)]
        for msg in ties.log:
            print("cup tiebreak:", msg)
    return table, weeks, cup


def cup_result(cup, weekly, c):
    """Triad Cup state: seeds in order, head start, totals, champion (tie -> higher seed)."""
    weeks = list(range(int(c["cup_weeks"][0]), int(c["cup_weeks"][1]) + 1))
    head = list(c["cup_head_start"]) + [0] * len(cup)
    rows = []
    for i, t in enumerate(cup):
        sc = {w: weekly[w].get(t) for w in weeks if w in weekly}
        rows.append({"team": t, "cup_seed": i + 1, "head_start": head[i],
                     "weeks": {str(w): round(v, 2) for w, v in sc.items() if v is not None},
                     "total": round(head[i] + sum(v for v in sc.values() if v is not None), 2)})
    final = all(w in weekly for w in weeks)
    champ = None
    if final:
        champ = sorted(rows, key=lambda r: (-r["total"], r["cup_seed"]))[0]["team"]
    return {"rows": rows, "final": final, "champion": champ}


def season_json(season, c, field, sched, data, proj=None, dev=False):
    seeds = {int(r.Seed): (r.LeagueName, str(r.RosterID)) for r in field.itertuples()}
    name = {t: tn.season_name(int(season), t[0], t[1]) or r.Team for r in field.itertuples() for t in [(r.LeagueName, str(r.RosterID))]}
    league = {(r.LeagueName, str(r.RosterID)): r.League for r in field.itertuples()}
    weekly = {}
    if data is not None:
        for w in data.done:
            sc = data.weekly(w)
            weekly[w] = {t: sc[t] for t in seeds.values() if t in sc}
    bb = data.bestball(*c["pod_weeks"]) if data is not None else {}
    table, weeks, cup = standings(seeds, sched, weekly, c, name, season, bb)
    seed_of = {t: s for s, t in seeds.items()}
    teams = [{"seed": s, "team": name[t], "league": league[t], "league_name": t[0], "roster": t[1],
              "lid": data.lid.get(t) if data else None, "route": r.Route, "qualified": {
                  "allplay": r.AllPlay, "allplay_rank": int(r.AllPlayRank), "bestball": r.BestBall,
                  "bestball_rank": int(r.BestBallRank), "poll_rank": int(r.PollRank), "rank_sum": int(r.RankSum),
                  "worst_rank": int(r.WorstRank), "qualifying_name": r.Team}}
             for r in field.itertuples() for s, t in [(int(r.Seed), (r.LeagueName, str(r.RosterID)))]]
    out = {"season": int(season), "name": c.get("name", "Champions League"), "cup_name": c.get("cup_name", "Triad Cup"),
           "dev": bool(dev), "banner": c.get("preview_banner", "") if dev else "",
           "pod_weeks": c["pod_weeks"], "cup_weeks": c["cup_weeks"], "pod_points": c["pod_points"],
           "cup_size": int(c["cup_size"]), "cup_head_start": c["cup_head_start"],
           "qualifying_season": int(field["QualifyingSeason"].iloc[0]),
           "schedule": {str(w): [list(p) for p in pods] for w, pods in sched.items()},
           "teams": sorted(teams, key=lambda x: x["seed"]), "standings": table, "weeks": weeks,
           "through_week": weeks[-1]["week"] if weeks else 0,
           "status": "upcoming" if not weeks else "pods",
           "built_at": now_iso()}
    if cup:
        res = cup_result(cup, weekly, c)
        out["cup"] = {"seeds": [seed_of[r["team"]] for r in res["rows"]],
                      "rows": [{**{k: v for k, v in r.items() if k != "team"}, "seed": seed_of[r["team"]]} for r in res["rows"]],
                      "final": res["final"],
                      "champion": ({"seed": seed_of[res["champion"]], "team": name[res["champion"]],
                                    "league_name": res["champion"][0], "roster": res["champion"][1]}
                                   if res["champion"] else None)}
        out["status"] = "final" if res["final"] else "cup"
    if proj:
        out["projection"] = proj
    return out


def projection(season, c, data=None):
    """Projected field for season+1 from season's results so far (Selection page)."""
    sel = c["selection"]
    data = data or SeasonData(season)
    if not data.done or max(data.done) < int(sel.get("projection_start_week", 10)):
        return {"shown": False, "starts_week": int(sel.get("projection_start_week", 10))}
    res = select(season, c, data=data)
    keep = ["Seed", "Team", "League", "Route", "AllPlay", "AllPlayRank", "BestBall", "BestBallRank", "PollRank",
            "RankSum", "WorstRank", "Playoff"]
    return {"shown": True, "for_season": int(season) + 1, "through_week": res["through_week"],
            "poll_week": res["poll_week"], "rows": [{k: r[k] for k in keep} for r in res["rows"]],
            "out": [{k: r[k] for k in keep} for r in res["out"]], "collapsed": res["collapsed"],
            "leagues": res["leagues"], "final": max(data.done) >= 18, "playoff_known": bool(data.postseason()["playoff"])}


def run_season(season, c, out_dir=None, dev=False):
    f = read_field(season, out_dir)
    if f is None:
        print(f"Champions League {season}: no field file ({field_path(season, out_dir)}); skipped")
        return None
    sched = load_schedule(c["schedule_file"])
    validate_schedule(sched, int(c["field_size"]))
    data = SeasonData(season) if int(season) <= psc.current_season() else None
    proj = projection(season, c, data) if data else None
    js = season_json(season, c, f, sched, data, proj, dev)
    path = os.path.join(out_dir or os.path.join("data", "scoreboard", str(season)), "champions-league.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(js, fh, ensure_ascii=False, separators=(",", ":"))
    top = js["standings"][:3]
    print(f"Champions League {season}{' (dev)' if dev else ''}: through week {js['through_week']}, status {js['status']}; "
          f"leaders " + ", ".join(f"#{r['seed']} {r['pts']:g}" for r in top) + f" -> {path}")
    return js


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lock", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--verify-owners", type=int, default=None)
    ap.add_argument("--season", type=int, default=None)
    ap.add_argument("--out-dir", default=None)
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    c = settings()
    if a.lock is not None:
        lock(a.lock, a.out_dir, a.force, c=c)
        return
    if a.verify_owners is not None:
        s = int(a.verify_owners)
        d = SeasonData(s)
        if d.done:
            print(f"Champions League {s}: field locked (week 1 has started); no replacements")
            return
        changed = verify_owners(s, d.owner, a.out_dir, c=c)
        print(f"Champions League {s}: " + (f"replaced {len(changed)} team(s): {changed}" if changed else "owners unchanged"))
        return
    seasons = [a.season] if a.season else sorted(set(c.get("seasons", [])) | set(c.get("dev_seasons", [])))
    for s in seasons:
        if int(s) > psc.current_season():
            continue
        run_season(int(s), c, a.out_dir, dev=int(s) in set(c.get("dev_seasons", [])) and int(s) not in set(c.get("seasons", [])))


if __name__ == "__main__":
    main()
