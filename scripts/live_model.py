"""
live_model.py -- Python twin of reports/assets/scoreboard-core.js (the browser scoreboard's math),
used by game_notify.py so a push shows the same score / projection / win chance as the page.

Kept function-for-function with the JS; tests/test_live_model.py runs both on the same inputs and
requires identical numbers. Change one, change the other.
"""
import math


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) else 0.0


def rnd(x):
    # JS: Math.round((x + Number.EPSILON) * 100) / 100  (round half up)
    return math.floor((x + 2.220446049250313e-16) * 100 + 0.5) / 100


PTS_BANDS = [(0, 0, "pts_allow_0"), (1, 6, "pts_allow_1_6"), (7, 13, "pts_allow_7_13"), (14, 20, "pts_allow_14_20"),
             (21, 27, "pts_allow_21_27"), (28, 34, "pts_allow_28_34"), (35, math.inf, "pts_allow_35p")]
YDS_BANDS = [(0, 99, "yds_allow_0_100"), (100, 199, "yds_allow_100_199"), (200, 299, "yds_allow_200_299"),
             (300, 349, "yds_allow_300_349"), (350, 399, "yds_allow_350_399"), (400, 449, "yds_allow_400_449"),
             (450, 499, "yds_allow_450_499"), (500, 549, "yds_allow_500_549"), (550, math.inf, "yds_allow_550p")]


def normalized_stats(raw):
    s = dict(raw or {})

    def tier(raw_key, prefix, bands):
        if s.get(raw_key) is None:
            return
        if any(k.startswith(prefix) for k in s):
            return
        v = num(s[raw_key])
        for lo, hi, key in bands:
            if lo <= v <= hi:
                s[key] = 1
                break
    tier("pts_allow", "pts_allow_", PTS_BANDS)
    tier("yds_allow", "yds_allow_", YDS_BANDS)
    return s


def jsum(values):
    """Plain left-to-right addition like JS reduce. (Python 3.12+ sum() compensates rounding
    error, which can differ from the browser in the last digit.)"""
    total = 0.0
    for v in values:
        total += v
    return total


def score(raw, rules):
    s = normalized_stats(raw or {})
    return rnd(jsum(num(s.get(k)) * num(v) for k, v in (rules or {}).items()))


def remaining(game):
    if not game or game.get("state") in ("bye", "post"):
        return 0.0
    if game.get("state") == "pre":
        return 1.0
    if num(game.get("period")) > 4:
        return 0.0
    parts = str(game.get("clock") or "0:00").split(":")
    seconds = num(parts[0]) * 60 + num(parts[1] if len(parts) > 1 else 0)
    return max(0.0, min(1.0, ((4 - max(1, num(game.get("period")))) * 900 + seconds) / 3600))


def erf(x):
    sign = -1 if x < 0 else 1
    a = abs(x)
    t = 1 / (1 + 0.3275911 * a)
    return sign * (1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * math.exp(-a * a))


def probability(a, b):
    """Win chance (0-100) of team a over team b (team models)."""
    variance = a["variance"] + b["variance"]
    if variance < 1e-10:
        return 50.0 if a["projected"] == b["projected"] else (100.0 if a["projected"] > b["projected"] else 0.0)
    return 50 * (1 + erf((a["projected"] - b["projected"]) / math.sqrt(2 * variance)))


INACTIVE = {"out", "inactive", "ir", "pup", "sus", "suspended"}


def player_model(pid, metadata, raw, projection, game, official, cfg, past=False):
    p = metadata or {"name": f"Player {pid}", "positions": [], "team": "", "status": ""}
    positions = p.get("positions") or [p.get("position")]
    pos = next((x for x in positions if cfg["position_sd"].get(x)), p.get("position"))
    inactive = (not past) and str(p.get("status") or "").lower() in INACTIVE and (not game or game.get("state") != "post")
    fraction = 0.0 if inactive else remaining(game)
    started = bool(game) and game.get("state") not in ("pre", "bye")
    correction = score(raw, cfg["standard_scoring"]) - score(raw, cfg.get("official_scoring") or cfg["standard_scoring"])
    actual = rnd(num(official) + correction) if started else 0.0
    projected = score(projection, cfg["standard_scoring"])
    phase = "out" if inactive else ("unknown" if not game else ("bye" if game.get("state") == "bye" else game.get("state")))
    return {"id": pid, "name": p.get("name"), "position": pos, "phase": phase, "actual": actual, "baseline": projected,
            "projected": rnd(actual + projected * fraction),
            "variance": (num(cfg["position_sd"].get(pos)) * fraction) ** 2,
            "minutes": 60 * fraction, "official": num(official)}


EMPTY = {"id": "0", "name": "Empty slot", "position": "", "phase": "out", "actual": 0.0, "baseline": 0.0,
         "projected": 0.0, "variance": 0.0, "minutes": 0.0, "official": 0.0}


def team_model(roster, players):
    starters = [players.get(str(i), EMPTY) for i in (roster.get("starters") or [])]
    adjustment = num(roster.get("points")) - jsum(p["official"] for p in starters)
    return {"starters": starters, "adjustment": rnd(adjustment),
            "actual": rnd(jsum(p["actual"] for p in starters) + adjustment),
            "projected": rnd(jsum(p["projected"] for p in starters) + adjustment),
            "pregame": rnd(jsum(p["baseline"] for p in starters)),
            "variance": jsum(p["variance"] for p in starters),
            "minutes": jsum(p["minutes"] for p in starters), "official": num(roster.get("points"))}


def is_done(team):
    """Every starter's NFL game is over (or he's out / on bye): 0 minutes left."""
    return all(p["phase"] not in ("pre", "in") for p in team["starters"]) and team["minutes"] < 1e-9
