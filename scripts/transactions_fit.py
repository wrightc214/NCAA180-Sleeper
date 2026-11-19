"""Historical team-goal fit. No live API reads and no future valuation inputs."""
import ast
import csv
import datetime as dt
import functools
import json
import math
import subprocess
from collections import defaultdict

import league_config as lcfg
from roster_map import best_lineup
from transactions_grades import grade, number, pick_slot_values, read_rows

DEFAULTS = {
    "meaningful_lineup_points": 6500,
    "meaningful_future_points": 4500,
    "score_points_per_unit": 20,
    "record_weight": .70,
    "playoff_context_weight": .25,
    "bowl_weight": .15,
    "odds_first_week": 8,
    "win_now_ceiling": .70,
    "rebuild_lineup_grace_through_week": 10,
    "rebuild_lineup_full_weight_at": .48,
    "rebuild_lineup_no_weight_at": .28,
    "rebuild_starter_weight": .90,
    "future_starter_floor": 1300,
    "future_starter_cap": 4500,
    "rebuild_max_weight": .38,
    "growth_horizon_years": [1, 2],
    "pick_flexibility": .42,
    "specialist_lookback_weeks": 4,
    "specialist_target_ppg": 8,
    "specialist_needs_points": 2600,
    "age_curves": {"QB": [31, .07, 35, .20], "RB": [27.5, .15, 30.5, .40],
                   "WR": [28, .10, 31, .28], "TE": [29, .09, 32, .25]},
}
ROSTERS = "data/Rosters_Current.csv"
PICKS = "data/FuturePicks_Current.csv"
TX = "data/Transactions_Season.csv"
CONTEXT = "data/RosterValues_Season.csv"
SCORES = "data/Scores_Season.csv"
PLAYER_VALUES = "data/PlayerValues_Season.csv"
PICK_VALUES = "data/PickValues_Season.csv"
MODEL_VERSION = "team-fit-v1"
ODDS_DIR = "reports/postseason/"
POSITION = {"FB": "RB", "PK": "K", "DEF": "DST", "D/ST": "DST"}


def literal(text, fallback):
    try:
        return ast.literal_eval(text) if text else fallback
    except (ValueError, SyntaxError, TypeError):
        return fallback


def pos(raw):
    value = str(raw or "").upper()
    return POSITION.get(value, value)


def age_at(birthday, date):
    try:
        return (dt.date.fromisoformat(date) - dt.date.fromisoformat(birthday)).days / 365.2425
    except (TypeError, ValueError):
        return None


def age_factor(age, years, curve):
    """Apply only incremental future decline. Rates are continuous across birthdays."""
    if age is None or age < 0 or not curve:
        return 1.0
    peak, gradual, cliff, steep = curve
    slow = max(0, min(age + years, cliff) - max(age, peak))
    fast = max(0, age + years - max(age, cliff))
    return (1 - gradual) ** slow * (1 - steep) ** fast


def contender_weight(context, odds, cfg):
    games = sum(number(context[k]) for k in ("W", "L", "T"))
    if not games:
        return None
    record = (number(context["W"]) + .5 * number(context["T"])) / games
    # Contender is already a league-wide results/lineup z-score. Map its neutral point to .5.
    signal = .5 + .5 * math.tanh(number(context["Contender"]))
    weight = cfg["record_weight"] * record + (1 - cfg["record_weight"]) * signal
    if odds:
        playoffs = min(1, max(0, number(odds["Playoff"])))
        bowl = min(1, max(0, number(odds["Bowl"])))
        rate = cfg["playoff_context_weight"]
        weight = (1 - rate) * weight + rate * min(1, playoffs + cfg["bowl_weight"] * bowl)
    return min(1, max(0, weight))


def fit_grade(lineup_delta, future_delta, w, lineup_loss_factor, cfg, grade_bands=None):
    now = lineup_delta * lineup_loss_factor if lineup_delta < 0 else lineup_delta
    units = w * now / cfg["meaningful_lineup_points"] + (1 - w) * future_delta / cfg["meaningful_future_points"]
    score = min(100, max(0, 50 + cfg["score_points_per_unit"] * units))
    return score, grade(score / 100, grade_bands)


@functools.lru_cache(maxsize=None)
def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=lcfg.ROOT, text=True, capture_output=True,
                              check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


@functools.lru_cache(maxsize=None)
def archived(ref, path):
    return list(csv.DictReader(git("show", f"{ref}:{path}").splitlines()))


@functools.lru_cache(maxsize=None)
def history(path):
    entries = []
    for line in git("log", "--first-parent", "--format=%H%x09%cI", "--", path).splitlines():
        ref, date = line.split("\t")
        stamp = dt.datetime.fromisoformat(date).timestamp()
        date = dt.datetime.fromtimestamp(stamp, dt.timezone.utc).date().isoformat()
        entries.append((int(stamp * 1000), ref, date))
    return sorted(entries, reverse=True)


def event_key(row):
    # Historical CSV rows lack the completion timestamp. Creation is a
    # conservative cutoff for those rows rather than using later knowledge.
    updated = row.get("StatusUpdated") or ""
    created = int(row["Created"])
    timestamp = max(created, int(updated)) if updated.isdigit() else created
    return timestamp, int(row["TransactionID"])



def pick_key(row):
    return str(row["season"]), str(row["round"]), str(row["roster_id"])


def mutate(roster, picks, row, reverse=False):
    adds = {k: str(v) for k, v in literal(row.get("Adds"), {}).items()}
    drops = {k: str(v) for k, v in literal(row.get("Drops"), {}).items()}
    if reverse:
        adds, drops = drops, adds
    for k in drops:
        roster.pop(k, None)
    roster.update(adds)
    for pick in literal(row.get("Picks"), []):
        picks[pick_key(pick)] = str(pick["previous_owner_id" if reverse else "owner_id"])


def target_consistent(roster, picks, row, after):
    source = literal(row.get("Adds" if after else "Drops"), {})
    other = literal(row.get("Drops" if after else "Adds"), {})
    return (
        all(roster.get(pid) == str(owner) for pid, owner in source.items())
        and all(pid not in roster for pid in other if pid not in source)
        and all(picks.get(pick_key(p)) == str(p["owner_id" if after else "previous_owner_id"])
                for p in literal(row.get("Picks"), []))
    )


def holdings(archive, ref, league):
    roster = {r["PlayerID"]: r["RosterID"] for r in archive.rows(ref, ROSTERS)
              if r["LeagueID"] == league and r.get("PlayerID")}
    picks = {(r["Season"], r["Round"], r["OriginalRosterID"]): r["OwnerRosterID"]
             for r in archive.rows(ref, PICKS) if r["LeagueID"] == league}
    return roster, picks


def completed_in(archive, ref):
    rows = archive.rows(ref, TX)
    return {r["TransactionID"] for r in rows if r["Status"] == "complete"} if rows else None


def owned(mapping, team):
    return {x for x, owner in mapping.items() if team == owner}


def check_reconstruction(archive, row, sides, before, after, events):
    """Rewind a later snapshot and check it against forward replay from an earlier one."""
    league = row["LeagueID"]
    first, last = holdings(archive, before[1], league), holdings(archive, after[1], league)
    if not all(first) or not all(last):
        return None
    orig, later = completed_in(archive, before[1]), completed_in(archive, after[1])
    target = row["TransactionID"]
    if (orig is not None and target in orig) or (later is not None and target not in later):
        return None
    key = event_key(row)
    for t in events:
        ident = t["TransactionID"]
        if (event_key(t) < key and (orig is None and event_key(t)[0] > before[0]
                                   or orig is not None and ident not in orig)
                and (later is None or ident in later)):
            mutate(*first, t)
    for t in reversed(events):
        ident = t["TransactionID"]
        if (event_key(t) > key and (later is None and event_key(t)[0] <= after[0]
                                   or later is not None and ident in later)):
            mutate(*last, t, reverse=True)
    if not target_consistent(*first, row, after=False) or not target_consistent(*last, row, after=True):
        return None
    check = tuple(m.copy() for m in first)
    mutate(*check, row)
    if any(owned(a, k) != owned(b, k) for a, b in zip(check, last) for k in sides):
        return None
    return first, last


class GitArchive:
    """Opt-in legacy evidence source for a deliberate backfill, never for routine builds."""
    rows = staticmethod(archived)

    def before(self, timestamp):
        return [a for a in history(ROSTERS) if a[0] < timestamp]

    def after(self, timestamp):
        return [a for a in reversed(history(ROSTERS)) if a[0] > timestamp]

    def market(self, timestamp):
        for published, ref, day in history(PLAYER_VALUES):
            if published >= timestamp:
                continue
            players = [r for r in self.rows(ref, PLAYER_VALUES) if r["Date"] == day]
            picks = self.rows(ref, "data/PickValues_Current.csv")
            if players and picks:
                return day, players, picks, {"market": ref, "market_published_ms": published}
        return None

    def odds(self, timestamp, year, week, start, league):
        for n in range(week, start - 1, -1):
            path = f"{ODDS_DIR}odds-wk{n:02d}.json"
            source = next((a for a in history(path) if a[0] < timestamp), None)
            if source:
                raw = git("show", f"{source[1]}:{path}")
                if raw:
                    data = json.loads(raw)
                    if int(data.get("year", 0)) == year:
                        return ({str(r["RosterID"]): r for r in data["teams"] if str(r["LeagueID"]) == league},
                                {"odds": source[1], "odds_published_ms": source[0], "odds_week": n})
        return {}, {}


class TeamFit:
    def __init__(self, transactions, players, market_config, archive):
        self.cfg = lcfg.transaction_settings("team_fit", DEFAULTS)
        self.market = market_config
        self.players = players
        self.archive = archive
        self.birth = {r["SleeperID"]: r for r in read_rows("data/PlayerBirthDates.csv")}
        self.events = defaultdict(list)
        for row in transactions:
            if row.get("Status") == "complete" and row.get("LeagueID") and str(row["TransactionID"]).isdigit():
                self.events[row["LeagueID"]].append(row)
        for events in self.events.values():
            events.sort(key=event_key)
        self.slots = [pos(r["Position"]) for r in read_rows("data/Lineup.csv")]

    def situation(self, anchor, yr, league, ids):
        context = {}
        for r in self.archive.rows(anchor[1], CONTEXT):
            k = r["RosterID"]
            if (r["Year"] == str(yr) and r["LeagueID"] == league and k in ids
                    and (k not in context or int(r["Week"]) > int(context[k]["Week"]))):
                context[k] = r
        return context

    def specialist_rates(self, anchor, yr, league, week):
        points = defaultdict(dict)
        for r in self.archive.rows(anchor[1], SCORES):
            w = int(r["weekNum"])
            if (r["LeagueYear"] == str(yr) and r["league_id"] == league
                    and week - self.cfg["specialist_lookback_weeks"] < w <= week):
                points[r["player_id"]][w] = number(r["points"])
        return points

    def measure(self, state, owner, values, pickvals, proxy, date, recent, week, rebuild):
        roster, picks = state
        pool, specialists, future = [], defaultdict(list), [0.] * len(self.cfg["growth_horizon_years"])
        future_pools = [[] for _ in future]
        raw, capital = 0., 0.
        for x in owned(roster, owner):
            v = values.get(x, {})
            bio = self.birth.get(x, {})
            kind = pos(v.get("Position") or self.players.get(x, {}).get("position") or bio.get("Position"))
            dynasty, redraft = number(v.get("DynastyValue")), number(v.get("RedraftValue"))
            if kind in ("K", "DST"):
                if not v:
                    if proxy is None:
                        return None
                    dynasty = proxy
                    if self.cfg["specialist_target_ppg"] > 0:
                        n = min(week, self.cfg["specialist_lookback_weeks"])
                        ppg = sum(recent[x].values()) / n if n else 0
                        redraft = proxy * min(1, max(0, ppg / self.cfg["specialist_target_ppg"]))
                specialists[kind].append(redraft)
            else:
                pool.append((redraft, kind))
            raw += dynasty
            age = age_at(bio.get("BirthDate"), date)
            for i, h in enumerate(self.cfg["growth_horizon_years"]):
                v_h = dynasty * age_factor(age, h, self.cfg["age_curves"].get(kind))
                future[i] += v_h
                if kind not in ("K", "DST"):
                    starter_utility = max(0, min(v_h, self.cfg["future_starter_cap"]) - self.cfg["future_starter_floor"])
                    future_pools[i].append((starter_utility, kind))
        for key in owned(picks, owner):
            if key[:2] not in pickvals:
                return None
            v = pickvals[key[:2]]
            raw += v
            capital += v
            for i in range(len(future)):
                future[i] += v * (1 + self.cfg["pick_flexibility"] if rebuild else 1)
        lineup = best_lineup(pool, self.slots)
        coverage = sum(sum(sorted(specialists[k], reverse=True)[:self.slots.count(k)]) for k in ("K", "DST"))
        # Extra fit weight for evidenced scarce starter coverage, not an addition to market value.
        scale = self.cfg["specialist_needs_points"] / proxy if proxy else 0
        return lineup + coverage, raw, future, coverage * scale, [best_lineup(p, self.slots) for p in future_pools], capital

    def evaluate(self, row, sides):
        if not self.slots or not row.get("LeagueID") or not str(row["TransactionID"]).isdigit():
            return {}
        t, year, league = event_key(row)[0], int(row["Year"]), row["LeagueID"]
        archive = self.archive
        before = next((a for a in archive.before(t) if holdings(archive, a[1], league)[1]), None)
        market = archive.market(t)
        if not before or not market:
            return {}
        state = None
        for after in archive.after(t):
            state = check_reconstruction(archive, row, sides, before, after, self.events[league])
            if state:
                break
        if not state:
            return {}
        context = self.situation(before, year, league, sides)
        day, player_rows, pick_rows, sources = market
        odds, odds_sources = archive.odds(t, year, int(row["Week"]), self.cfg["odds_first_week"], league)
        sources = {**sources, **odds_sources, "before": before[1], "before_ms": before[0],
                   "after": after[1], "after_ms": after[0]}
        values = {r["SleeperID"]: r for r in player_rows}
        picks = {(r["Season"], r["Round"]): number(r["Value"]) for r in pick_rows}
        proxy = next((v for v, label, est in pick_slot_values(pick_rows, year + 1, self.market)
                      if label == self.market["proxy_pick_slot"] and est), None)
        result = {}
        for k in sides:
            if k not in context:
                continue
            w = contender_weight(context[k], odds.get(k), self.cfg)
            if w is None:
                continue
            # The archive can label a row with the run week, but completed games are what cap scores.
            week = min(int(context[k]["Week"]), int(sum(number(context[k][x]) for x in ("W", "L", "T"))))
            recent = self.specialist_rates(before, year, league, week)
            rebuild = w <= self.cfg["rebuild_max_weight"]
            weight = min(w, self.cfg["win_now_ceiling"])
            loss_factor = 1.
            if int(row["Week"]) <= self.cfg["rebuild_lineup_grace_through_week"]:
                low = self.cfg["rebuild_lineup_no_weight_at"]
                high = self.cfg["rebuild_lineup_full_weight_at"]
                loss_factor = min(1., max(0., (w - low) / max(.0001, high - low)))
            date = dt.datetime.fromtimestamp(t / 1000, dt.timezone.utc).date().isoformat()
            pairs = [self.measure(v, k, values, picks, proxy, date, recent, week, rebuild) for v in state]
            if None in pairs:
                continue
            (l0, d0, f0, c0, s0, picks0), (l1, d1, f1, c1, s1, picks1) = pairs
            # The extra coverage weight is only a Team Fit input. Report raw estimated lineup delta.
            wins_now = l1 - l0 + c1 - c0
            futures = [b - a for a, b in zip(f0, f1)]
            starters = [b - a for a, b in zip(s0, s1)]
            blend = self.cfg["rebuild_starter_weight"] if rebuild else 0
            # Picks are flexibility, not guaranteed starters. Once a seller has stocked
            # future capital, don't also charge the roster as if that capital must go unused.
            horizon_utility = [a + blend * (max(0, b) if picks1 > picks0 else b)
                               for a, b in zip(futures, starters)]
            future = sum(horizon_utility) / len(horizon_utility)
            score, letter = fit_grade(wins_now, future, weight, loss_factor, self.cfg,
                                      self.market["grade_bands"])
            letters_by_horizon = [fit_grade(wins_now, u, weight, loss_factor, self.cfg,
                                            self.market["grade_bands"])[1] for u in horizon_utility]
            result[k] = {"weight": w, "lineup_before": l0, "lineup_after": l1,
                         "dynasty_before": d0, "dynasty_after": d1, "future": futures,
                         "score": score, "letter": letter, "date": day, "rebuild": rebuild,
                         "starter_future": starters, "future_utility": future, "fit_weight": weight,
                         "sources": sources, "lineup_utility_delta": wins_now, "lineup_loss_factor": loss_factor,
                         "horizon_gaps": list(zip(self.cfg["growth_horizon_years"], horizon_utility, letters_by_horizon))}
        return result
