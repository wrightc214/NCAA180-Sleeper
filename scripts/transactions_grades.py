"""Historical FantasyCalc trade valuation; no future data leakage.

All monetary values are FantasyCalc points. KTC-style fallback is NOT calibrated KTC.
"""
import bisect
import csv
import datetime as dt
import math
import json
from collections import defaultdict
from pathlib import Path

DEFAULT_CONFIG = {
    "consolidation": {"method": "ktc-style-fallback", "exponent_low": 1.04,
                      "exponent_elite": 1.40, "elite_threshold": 0.7},
    "grade_bands": [[60, "A"], [55, "B+"], [52, "B"], [48, "Even"],
                    [45, "C"], [40, "D"], [0, "F"]],
}


def number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def historical(rows, day, date_col="Date"):
    """Latest recorded snapshot on/before the event date; never look forward."""
    valid = sorted({str(r.get(date_col, "")) for r in rows if str(r.get(date_col, "")) <= day})
    return valid[-1] if valid else None


def group_dates(rows):
    by = defaultdict(list)
    for r in rows:
        if r.get("Date"):
            by[r["Date"]].append(r)
    return by


def read_rows(path):
    if not Path(path).exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_config(path="config/transactions.json"):
    """Read explicit adjustable coefficients/bands; defaults used for pure unit fixtures."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else DEFAULT_CONFIG


def grade(share, bands=None):
    if share is None or not math.isfinite(share):
        return None
    bands = bands or DEFAULT_CONFIG["grade_bands"]
    return next((label for bound, label in bands if share * 100 >= bound), "F")


def grade_score(share):
    """Continuous 0..100 with 50 neutral; same number drives CSS gradient."""
    return max(0, min(100, 100 * share)) if share is not None and math.isfinite(share) else None


def fallback_raw(value, top_trade, top_snapshot, config=None):
    """Elite concentration premium, increasing with elite-ness of trade's top asset.

    Raw adjustment per asset = p * (p/t)**e, with e in [1.04, 1.40].
    Its inverse is solved analytically for the side balancing credit. Draft picks
    and players share the same unit. This is documented KTC-*style*, not KTC math.
    """
    if value <= 0 or top_trade <= 0:
        return 0.0
    cfg = (config or DEFAULT_CONFIG).get("consolidation", config or DEFAULT_CONFIG["consolidation"])
    threshold = max(0.01, number(cfg.get("elite_threshold", 0.7)))
    elite = min(1.0, max(0.0, top_trade / max(top_snapshot, 1) / threshold))
    e = number(cfg.get("exponent_low", 1.04)) + elite * (
        number(cfg.get("exponent_elite", 1.40)) - number(cfg.get("exponent_low", 1.04)))
    return value * (value / top_trade) ** e


def consolidation(sides, top_snapshot, config=None):
    """Return (adjustment per side, summed raw adjustments).

    Sides is {team: [nonnegative asset values]}. Single-sided or zero-value
    transactions do not create an adjustment.
    """
    keys = list(sides)
    if len(keys) != 2:
        return {k: 0.0 for k in keys}, {k: 0.0 for k in keys}
    values = [max(0.0, number(v)) for group in sides.values() for v in group]
    top = max(values, default=0.0)
    if not top or any(not any(number(v) > 0 for v in sides[k]) for k in keys):
        # Picks carry zero contender value. They must not gain a fictional
        # balancing asset that turns a 0-for-starter deal into an 'Even' grade.
        raw = {k: sum(fallback_raw(max(0.0, number(v)), top, top_snapshot, config)
                      for v in sides[k]) for k in keys}
        return {k: 0.0 for k in keys}, raw
    raw = {k: sum(fallback_raw(max(0.0, number(v)), top, top_snapshot, config)
                  for v in sides[k]) for k in keys}
    lo, hi = sorted(keys, key=lambda k: raw[k])
    diff = raw[hi] - raw[lo]
    adjustment = {k: 0.0 for k in keys}
    if diff > 1e-9:
        low, high = 0.0, max(top, diff)
        while fallback_raw(high, top, top_snapshot, config) < diff:
            high *= 2
        for _ in range(70):
            mid = (low + high) / 2
            if fallback_raw(mid, top, top_snapshot, config) < diff:
                low = mid
            else:
                high = mid
        adjustment[lo] = (low + high) / 2
    return adjustment, raw


def compare(sides, top_snapshot, config=None):
    """Grade the value *received* by each team; adjusted point totals retained."""
    keys = list(sides)
    raw_totals = {k: sum(max(0.0, number(v)) for v in vals) for k, vals in sides.items()}
    credit, adjustments = consolidation(sides, top_snapshot, config)
    adjusted = {k: raw_totals[k] + credit.get(k, 0) for k in keys}
    total = sum(adjusted.values())
    shares = {k: adjusted[k] / total if total else 0.5 for k in keys}
    return {"raw": raw_totals, "credit": credit, "adjustment_sums": adjustments,
            "adjusted": adjusted, "share": shares,
            "grade": {k: grade(shares[k], (config or DEFAULT_CONFIG).get("grade_bands")) for k in keys},
            "score": {k: grade_score(shares[k]) for k in keys}}


def nearest_pick(delta, season, pick_rows):
    """One nearest pick through early-first cap; larger delta anchors at highest
    fitting pick and uses a second pick only for the leftover. Exact slot picks
    aren't in historical CSV; interpolate between early/mid/late anchor points.
    All slot prices are estimates; return 'estimated' marker.
    """
    delta = abs(number(delta))
    rows = [r for r in pick_rows if str(r.get("Season")) == str(season)]
    if not rows or delta <= 0:
        return []
    candidates = []
    for r in rows:
        rnd = int(r["Round"])
        points = [(2, number(r.get("Early"))), (6, number(r.get("Mid"))),
                  (10, number(r.get("Late")))]
        if all(v > 0 for _, v in points):
            for slot in range(1, 13):
                if slot <= 2:
                    v = points[0][1]
                elif slot >= 10:
                    v = points[-1][1]
                else:
                    a, b = (points[0], points[1]) if slot <= 6 else (points[1], points[2])
                    v = a[1] + (b[1] - a[1]) * (slot - a[0]) / (b[0] - a[0])
                candidates.append((v, f"{season} Pick {rnd}.{slot:02d}", True))
        else:
            candidates.append((number(r.get("Value")), f"{season} R{rnd}", False))
    candidates = sorted((x for x in candidates if x[0] > 0), reverse=True)
    if not candidates:
        return []
    early_first = max((v for v, label, _ in candidates if "Pick 1." in label or label.endswith(" R1")),
                      default=candidates[0][0])
    if delta <= early_first:
        return [min(candidates, key=lambda x: (abs(x[0] - delta), -x[0]))]
    primary = next((x for x in candidates if x[0] <= delta), candidates[0])
    remain = delta - primary[0]
    if remain <= 0:
        return [primary]
    secondary = min(candidates, key=lambda x: (abs(x[0] - remain), -x[0]))
    return [primary, secondary]


def evaluate_trade(assets, trade_day, player_history, pick_history, trade_year, config=None):
    """assets: {team: [{kind:'player', id:'...' } or {kind:'pick',season,round}]}.
    If any traded asset lacks a recorded historic value, withhold that grade.
    Historic player snapshot date and pick snapshot date may differ; both must
    precede the trade. Players lacking FantasyCalc coverage are not silently 0.
    """
    by_p = group_dates(player_history)
    by_k = group_dates(pick_history)
    pd = historical(player_history, trade_day)
    kd = historical(pick_history, trade_day)
    if not pd:
        return {"status": "No values from that week", "dynasty": None, "contender": None}
    players = {str(r["SleeperID"]): r for r in by_p[pd]}
    picks = {(str(r["Season"]), str(r["Round"])): r for r in by_k.get(kd, [])}
    sides = {k: {"dynasty": [], "contender": []} for k in assets}
    problems = {"dynasty": [], "contender": []}
    for team, traded in assets.items():
        for asset in traded:
            if asset["kind"] == "player":
                p = players.get(str(asset["id"]))
                if p is None:
                    problems["dynasty"].append(asset["id"])
                    problems["contender"].append(asset["id"])
                    continue
                for col, mode in (("DynastyValue", "dynasty"), ("RedraftValue", "contender")):
                    sides[team][mode].append(number(p.get(col)))
            else:
                # Contender value of picks is explicitly zero, regardless of pick snapshot.
                sides[team]["contender"].append(0)
                p = picks.get((str(asset["season"]), str(asset["round"])))
                if p is None:
                    problems["dynasty"].append(f'{asset["season"]} R{asset["round"]}')
                else:
                    sides[team]["dynasty"].append(number(p["Value"]))
    top_d = max((number(r["DynastyValue"]) for r in players.values()), default=1)
    top_r = max((number(r["RedraftValue"]) for r in players.values()), default=1)
    result = {"status": "complete", "player_date": pd, "pick_date": kd,
              "dynasty": None, "contender": None, "missing": problems}
    for mode, top in (("dynasty", top_d), ("contender", top_r)):
        if not problems[mode]:
            result[mode] = compare({k: v[mode] for k, v in sides.items()}, top, config)
    if not result["dynasty"] and not result["contender"]:
        result["status"] = "No values from that week"
    if result["dynasty"] and kd:
        val = result["dynasty"]
        if len(val["adjusted"]) == 2:
            winner = max(val["adjusted"], key=lambda k: val["adjusted"][k])
            surplus = val["adjusted"][winner] - min(val["adjusted"].values())
            if surplus > 1e-6:
                val["surplus"] = {"team": winner, "value": surplus, "picks": nearest_pick(
                    surplus, trade_year + 1, by_k[kd])}
    return result
