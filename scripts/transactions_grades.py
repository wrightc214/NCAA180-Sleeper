"""Historical FantasyCalc trade valuation; no future data leakage.

Market values and NCAA 180 pick proxies use FantasyCalc points. KTC-style fallback is NOT calibrated KTC.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import league_config as lcfg

TEAM_DEFENSE_POSITIONS = {"DEF", "DST", "D/ST"}


def number(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def historical(rows, day, date_col="Date"):
    """Latest recorded snapshot on/before the event date; never look forward."""
    valid = sorted({str(r[date_col]) for r in rows if r.get(date_col) and str(r[date_col]) <= day})
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


DEFAULTS = {
    "consolidation": {"method": "ktc-style-fallback", "exponent_low": 1.04,
                      "exponent_elite": 1.4, "elite_threshold": .7},
    "grade_bands": [[60, "A"], [55, "B+"], [52, "B"], [48, "Even"], [45, "C"], [40, "D"], [0, "F"]],
    "blockbuster_min_multiple": 1.4,
    "blockbuster_min_headliner_share": .6,
    "proxy_pick_slot": "4.12",
    "surplus_swap_max_relative_error": .25,
    "draft_slots_per_round": 12,
    "draft_tier_anchors": [2, 6, 10],
    "movement_types": ["free_agent", "waiver", "commissioner"],
    "labels": {
        "rebuild": "Rebuild",
        "contender": "Contender",
        "blockbuster": "Blockbuster",
        "surplus": "Dynasty surplus",
        "team_fit": "Team Fit",
        "evaluation": "Trade evaluation",
        "trades": "Trades",
        "movement": "Player movement",
        "summary": "Season summary",
        "receives": "Receives",
        "most_added": "Most added",
        "most_dropped": "Most dropped",
        "team": "Team",
        "pick": "Pick",
        "pick_swap": "Pick swap",
        "trades_by_week": "Trades by week",
    },
}


def load_config(overrides=None):
    """Resolve the dedicated owner settings and keep existing behavior for absent keys."""
    return lcfg.transaction_settings("transactions", DEFAULTS, overrides)


def grade(share, bands=None):
    if share is None or not math.isfinite(share):
        return None
    bands = load_config()["grade_bands"] if bands is None else bands
    return next((label for bound, label in bands if share * 100 >= bound), "F")


def grade_score(share):
    """Continuous 0..100 with 50 neutral; same number drives CSS gradient."""
    return max(0, min(100, 100 * share)) if share is not None and math.isfinite(share) else None


def fallback_raw(value, top_trade, top_snapshot, cfg):
    """Elite concentration premium, increasing with elite-ness of trade's top asset.

    Raw adjustment per asset = p * (p/t)**e, with e in [1.04, 1.40].
    Its inverse is approximated by bisection for the side balancing credit. Draft picks
    and players share the same unit. This is documented KTC-*style*, not KTC math.
    """
    if value <= 0 or top_trade <= 0:
        return 0.0
    threshold = max(0.01, number(cfg["elite_threshold"]))
    elite = min(1.0, max(0.0, top_trade / max(top_snapshot, 1) / threshold))
    e = number(cfg["exponent_low"]) + elite * (
        number(cfg["exponent_elite"]) - number(cfg["exponent_low"]))
    return value * (value / top_trade) ** e


def consolidation(sides, top_snapshot, config=None):
    """Return (adjustment per side, summed raw adjustments).

    Sides is {team: [nonnegative asset values]}. Single-sided or zero-value
    transactions do not create an adjustment.
    """
    keys = list(sides)
    if len(keys) != 2:
        return {k: 0.0 for k in keys}, {k: 0.0 for k in keys}
    settings = load_config(config)["consolidation"]
    if settings["method"] == "none":
        return {k: 0.0 for k in keys}, {k: 0.0 for k in keys}
    values = [max(0.0, number(v)) for group in sides.values() for v in group]
    top = max(values, default=0.0)
    if not top or any(not any(number(v) > 0 for v in sides[k]) for k in keys):
        # Picks carry zero contender value. They must not gain a fictional
        # balancing asset that turns a 0-for-starter deal into an 'Even' grade.
        raw = {k: sum(fallback_raw(max(0.0, number(v)), top, top_snapshot, settings)
                      for v in sides[k]) for k in keys}
        return {k: 0.0 for k in keys}, raw
    raw = {k: sum(fallback_raw(max(0.0, number(v)), top, top_snapshot, settings)
                  for v in sides[k]) for k in keys}
    lo, hi = sorted(keys, key=lambda k: raw[k])
    diff = raw[hi] - raw[lo]
    adjustment = {k: 0.0 for k in keys}
    if diff > 1e-9:
        low, high = 0.0, max(top, diff)
        while fallback_raw(high, top, top_snapshot, settings) < diff:
            high *= 2
        for _ in range(70):
            mid = (low + high) / 2
            if fallback_raw(mid, top, top_snapshot, settings) < diff:
                low = mid
            else:
                high = mid
        adjustment[lo] = (low + high) / 2
    return adjustment, raw


def compare(sides, top_snapshot, config=None, proxy=None):
    """Grade the value *received* by each team; adjusted point totals retained."""
    keys = list(sides)
    raw_totals = {k: sum(max(0.0, number(v)) for v in vals) for k, vals in sides.items()}
    credit, adjustments = consolidation(sides, top_snapshot, config)
    raw_totals = {k: v + (proxy or {}).get(k, 0) for k, v in raw_totals.items()}
    adjusted = {k: raw_totals[k] + credit.get(k, 0) for k in keys}
    total = sum(adjusted.values())
    shares = {k: adjusted[k] / total if total else None for k in keys}
    bands = load_config(config)["grade_bands"]
    return {"raw": raw_totals, "credit": credit, "adjustment_sums": adjustments,
            "adjusted": adjusted, "share": shares,
            "grade": {k: grade(shares[k], bands) for k in keys},
            "score": {k: grade_score(shares[k]) for k in keys}}


def pick_slot_values(pick_rows, season, config=None):
    """Yield (value, yearless slot label, estimated) from a single snapshot."""
    settings = load_config(config)
    slots = settings["draft_slots_per_round"]
    if type(slots) is not int or slots < 1:
        slots = DEFAULTS["draft_slots_per_round"]
    anchors = settings["draft_tier_anchors"]
    if not (isinstance(anchors, list) and len(anchors) == 3
            and all(type(x) in (int, float) for x in anchors)
            and 0 < anchors[0] < anchors[1] < anchors[2] <= 12):
        anchors = DEFAULTS["draft_tier_anchors"]
    first, middle, last = anchors
    for row in pick_rows:
        if str(row.get("Season")) != str(season):
            continue
        rnd = int(row["Round"])
        early, mid, late = (number(row.get(col)) for col in ("Early", "Mid", "Late"))
        if min(early, mid, late) > 0:
            for slot in range(1, slots + 1):
                reference_slot = slot * 12 / slots
                if reference_slot <= first:
                    value = early
                elif reference_slot >= last:
                    value = late
                elif reference_slot <= middle:
                    value = early + (mid - early) * (reference_slot - first) / (middle - first)
                else:
                    value = mid + (late - mid) * (reference_slot - middle) / (last - middle)
                yield value, f"{rnd}.{slot:02d}", True
        elif number(row.get("Value")) > 0:
            yield number(row["Value"]), f"R{rnd}", False


def pick_swap(delta, season, pick_rows, config=None):
    """For small margins, find a close upgrade starting at the proxy slot."""
    settings = load_config(config)
    anchor_slot = settings["proxy_pick_slot"]
    slots = [(v, label) for v, label, estimated in pick_slot_values(pick_rows, season, settings) if estimated]
    anchor = next((v for v, label in slots if label == anchor_slot), 0)
    if not 0 < delta < anchor:
        return None
    upgrades = [(v - anchor, label) for v, label in slots if v > anchor]
    if not upgrades:
        return None
    value, label = min(upgrades, key=lambda pair: (abs(pair[0] - delta), pair[0], pair[1]))
    if abs(value - delta) > delta * settings["surplus_swap_max_relative_error"]:
        return None
    return {"from": anchor_slot, "to": label, "value": value}


def nearest_pick(delta, season, pick_rows, config=None):
    """Use one pick through the early-first cap or up to two above it."""
    delta = abs(number(delta))
    candidates = sorted(pick_slot_values(pick_rows, season, config), reverse=True)
    if not delta:
        return []
    if not candidates:
        return []
    early_first = max((v for v, label, _ in candidates if label.startswith("1.") or label == "R1"),
                      default=candidates[0][0])
    if delta <= early_first:
        return [min(candidates, key=lambda x: (abs(x[0] - delta), -x[0]))]
    primary = next((x for x in candidates if x[1] == "1.01" and x[0] <= delta), None)
    if primary is None:
        primary = next((x for x in candidates if x[0] <= delta), candidates[0])
    remain = delta - primary[0]
    if remain <= 0:
        return [primary]
    # One draft cannot contain two copies of the same slot.
    others = (x for x in candidates if x[1] != primary[1])
    secondary = min(others, key=lambda x: (abs(x[0] - remain), -x[0]), default=None)
    return [primary, secondary] if secondary else [primary]


def evaluate_trade(assets, trade_day, player_history, pick_history, trade_year, config=None):
    """Score known historical values and explicit, position-specific fallbacks."""
    by_p = group_dates(player_history)
    by_k = group_dates(pick_history)
    pd = historical(player_history, trade_day)
    kd = historical(pick_history, trade_day)
    if not pd:
        return {"status": "No values from that week", "dynasty": None, "contender": None}
    players = {str(r["SleeperID"]): r for r in by_p[pd]}
    picks = {(str(r["Season"]), str(r["Round"])): r for r in by_k.get(kd, [])}
    draft_rows = by_k.get(kd, [])
    draft = trade_year + 1
    settings = load_config(config)
    proxy_slot = settings["proxy_pick_slot"]
    proxy_value = next((v for v, label, estimated in pick_slot_values(draft_rows, draft, settings)
                        if label == proxy_slot and estimated), None)
    sides = {k: {"dynasty": [], "contender": []} for k in assets}
    problems = {"dynasty": [], "contender": []}
    proxies = {k: {} for k in assets}
    headliner_points = 0.0
    for team, traded in assets.items():
        for asset in traded:
            if asset["kind"] == "player":
                p = players.get(str(asset["id"]))
                if p is None:
                    pos = str(asset.get("position") or "").strip().upper()
                    if pos in {"K", "PK", "DEF", "DST", "D/ST"} and proxy_value is not None:
                        proxies[team][str(asset["id"])] = proxy_value
                    elif pos not in {"QB", "RB", "WR", "TE", "FB"}:
                        for mode in problems:
                            problems[mode].append(asset["id"])
                    continue
                for col, mode in (("DynastyValue", "dynasty"), ("RedraftValue", "contender")):
                    try:
                        value = float(p[col])
                    except (KeyError, ValueError, TypeError):
                        value = -1
                    if not math.isfinite(value) or value < 0:
                        problems[mode].append(asset["id"])
                    else:
                        sides[team][mode].append(value)
                        pos = str(p.get("Position") or asset.get("position") or "").strip().upper()
                        if mode == "dynasty" and pos not in TEAM_DEFENSE_POSITIONS:
                            headliner_points = max(headliner_points, value)
            else:
                # Contender value of picks is explicitly zero, regardless of pick snapshot.
                sides[team]["contender"].append(0)
                p = picks.get((str(asset["season"]), str(asset["round"])))
                if p is None:
                    problems["dynasty"].append(f'{asset["season"]} R{asset["round"]}')
                else:
                    sides[team]["dynasty"].append(number(p["Value"]))
    top_d = max((number(r.get("DynastyValue")) for r in players.values()), default=1)
    top_r = max((number(r.get("RedraftValue")) for r in players.values()), default=1)
    result = {"status": "complete", "player_date": pd, "pick_date": kd,
              "dynasty": None, "contender": None, "missing": problems, "proxies": proxies,
              "proxy_pick_slot": proxy_slot}
    proxy_totals = {team: sum(values.values()) for team, values in proxies.items()}
    for mode, top in (("dynasty", top_d), ("contender", top_r)):
        if not problems[mode]:
            result[mode] = compare({k: v[mode] for k, v in sides.items()}, top, config,
                                   proxy=proxy_totals)
    if not result["dynasty"] and not result["contender"]:
        result["status"] = "No values from that week"
    if result["dynasty"] and len(assets) == 2:
        market_total = sum(sum(side["dynasty"]) for side in sides.values())
        market_leader = max(
            (number(row.get("DynastyValue")) for row in players.values()
             if str(row.get("Position") or "").strip().upper() not in TEAM_DEFENSE_POSITIONS),
            default=0,
        )
        if market_leader > 0:
            multiple = market_total / market_leader
            headliner_share = headliner_points / market_leader
            if (multiple >= settings["blockbuster_min_multiple"]
                    and headliner_share >= settings["blockbuster_min_headliner_share"]):
                result["blockbuster"] = {
                    "points": market_total, "multiple": multiple,
                    "headliner_points": headliner_points, "headliner_share": headliner_share,
                }
        val = result["dynasty"]
        winner = max(val["adjusted"], key=val["adjusted"].get)
        surplus = val["adjusted"][winner] - min(val["adjusted"].values())
        if surplus >= 0.5:  # Do not render "+0" at whole-point precision.
            small = proxy_value is not None and surplus < proxy_value
            val["surplus"] = {
                "team": winner, "value": surplus, "draft": draft,
                "swap": pick_swap(surplus, draft, draft_rows, settings) if small else None,
                "picks": [] if small else nearest_pick(surplus, draft, draft_rows, settings),
            }
    return result
