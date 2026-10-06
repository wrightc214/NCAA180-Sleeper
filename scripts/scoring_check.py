"""
scoring_check.py -- 🚨 all 15 NCAA 180 leagues must use IDENTICAL scoring settings.
Imported by projection_snapshot.py (weekly Tuesday baseline + every game-day window).

Problems detected:
  1. any league's scoring differs from the majority of leagues, or
  2. the shared scoring changed vs the last saved copy (data/projections/<season>/scoring.json),
     i.e. all leagues were changed at once.
Sleeper noise is ignored (missing == 0; values compared at 4 decimals).

When the alert is SENT (to lm-private-data, @everyone):
  - on the weekly Tuesday run (SCORING_WEEKLY=1) while any problem exists, and
  - on any run where the problem list differs from the previous run's (new, changed or
    additional mismatch). Otherwise only a warning on the run summary.
  SCORING_ALERT=0 disables sending (checks still run). State: data/ScoringCheck_Current.json.
Setting names are translated where known; unknown ones show Sleeper's raw label.
"""
import collections
import datetime as dt
import hashlib
import json
import os
import re

import requests

STATE = "data/ScoringCheck_Current.json"

LABELS = {
    # passing
    "pass_yd": "QB passing yards (per yd)", "pass_td": "QB passing TD", "pass_int": "QB interception",
    "pass_2pt": "Passing 2-pt conversion", "pass_att": "Pass attempt", "pass_cmp": "Pass completion",
    "pass_inc": "Incomplete pass", "pass_sack": "QB sacked", "pass_fd": "Passing first down",
    "pass_int_td": "Pick-six thrown", "bonus_pass_yd_300": "Bonus: 300+ passing yds",
    "bonus_pass_yd_400": "Bonus: 400+ passing yds",
    # rushing / receiving
    "rush_yd": "Rushing yards (per yd)", "rush_td": "Rushing TD", "rush_2pt": "Rushing 2-pt conversion",
    "rush_att": "Rush attempt", "rush_fd": "Rushing first down",
    "bonus_rush_yd_100": "Bonus: 100+ rushing yds", "bonus_rush_yd_200": "Bonus: 200+ rushing yds",
    "rec": "Reception (PPR)", "rec_yd": "Receiving yards (per yd)", "rec_td": "Receiving TD",
    "rec_2pt": "Receiving 2-pt conversion", "rec_fd": "Receiving first down",
    "bonus_rec_te": "TE reception bonus", "bonus_rec_rb": "RB reception bonus", "bonus_rec_wr": "WR reception bonus",
    "bonus_rec_yd_100": "Bonus: 100+ receiving yds", "bonus_rec_yd_200": "Bonus: 200+ receiving yds",
    "fum": "Fumble", "fum_lost": "Fumble lost", "fum_rec_td": "Fumble recovery TD",
    # kicking
    "fgm": "FG made", "fgm_0_19": "FG made 0-19", "fgm_20_29": "FG made 20-29", "fgm_30_39": "FG made 30-39",
    "fgm_40_49": "FG made 40-49", "fgm_50p": "FG made 50+", "fgmiss": "FG missed",
    "fgmiss_0_19": "FG missed 0-19", "fgmiss_20_29": "FG missed 20-29", "fgmiss_30_39": "FG missed 30-39",
    "fgmiss_40_49": "FG missed 40-49", "fgmiss_50p": "FG missed 50+",
    "xpm": "K extra point made", "xpmiss": "K missed extra point",
    # team defense
    "sack": "DEF sack", "int": "DEF interception", "fum_rec": "DEF fumble recovery", "safe": "DEF safety",
    "def_td": "DEF touchdown", "def_st_td": "DEF/ST touchdown", "blk_kick": "DEF blocked kick",
    "ff": "DEF forced fumble", "st_td": "Special teams TD", "def_2pt": "DEF 2-pt return",
    "pts_allow_0": "DEF 0 pts allowed", "pts_allow_1_6": "DEF 1-6 pts allowed",
    "pts_allow_7_13": "DEF 7-13 pts allowed", "pts_allow_14_20": "DEF 14-20 pts allowed",
    "pts_allow_21_27": "DEF 21-27 pts allowed", "pts_allow_28_34": "DEF 28-34 pts allowed",
    "pts_allow_35p": "DEF 35+ pts allowed",
    "yds_allow_0_100": "DEF 0-99 yds allowed", "yds_allow_100_199": "DEF 100-199 yds allowed",
    "yds_allow_200_299": "DEF 200-299 yds allowed", "yds_allow_300_349": "DEF 300-349 yds allowed",
    "yds_allow_350_399": "DEF 350-399 yds allowed", "yds_allow_400_449": "DEF 400-449 yds allowed",
    "yds_allow_450_499": "DEF 450-499 yds allowed", "yds_allow_500_549": "DEF 500-549 yds allowed",
    "yds_allow_550p": "DEF 550+ yds allowed",
}
LEAGUE_SHORT = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}


def _norm(d):
    """Treat missing == 0 and compare at 4 decimals (Sleeper float noise, explicit 0.0 keys)."""
    return {k: round(float(v), 4) for k, v in (d or {}).items()
            if isinstance(v, (int, float)) and round(float(v), 4) != 0}


def _key(d):
    return json.dumps(_norm(d), sort_keys=True)


def _val(v):
    if v is None:
        return "not scored"
    v = float(v)
    return (f"{v:+g}".replace("+", "") if v >= 0 else f"−{abs(v):g}")


def _lines(ref, other):
    keys = sorted(k for k in set(ref) | set(other) if ref.get(k) != other.get(k))
    return keys, {k: (ref.get(k), other.get(k)) for k in keys}


def check(scoring_all, names, previous):
    """scoring_all/previous: {league_id: settings}. Returns list of readable problem lines."""
    problems = []
    counts = collections.Counter(_key(v) for v in scoring_all.values())
    majority_key = counts.most_common(1)[0][0]
    majority = json.loads(majority_key)
    for lid, s in sorted(scoring_all.items(), key=lambda x: names.get(x[0], x[0])):
        if _key(s) != majority_key:
            keys, d = _lines(majority, _norm(s))
            lg = LEAGUE_SHORT.get(names.get(lid, ""), names.get(lid, lid))
            for k in keys:
                ref, val = d[k]
                problems.append(f"**{lg}**: {LABELS.get(k, k)} is **{_val(val)}** (other leagues: {_val(ref)})")
    if previous:
        prev_major = json.loads(collections.Counter(_key(v) for v in previous.values()).most_common(1)[0][0])
        if json.dumps(prev_major, sort_keys=True) != majority_key:
            keys, d = _lines(prev_major, majority)
            for k in keys:
                was, now = d[k]
                problems.append(f"**All leagues**: {LABELS.get(k, k)} changed from {_val(was)} to **{_val(now)}**")
    return problems


def alert(problems, season):
    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    weekly = os.environ.get("SCORING_WEEKLY") == "1"
    enabled = os.environ.get("SCORING_ALERT", "1") != "0"
    fp = hashlib.sha1("\n".join(problems).encode()).hexdigest()[:12] if problems else "ok"
    try:
        prev_fp = json.load(open(STATE)).get("fingerprint")
    except Exception:
        prev_fp = None
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    json.dump({"fingerprint": fp, "checked": now, "problems": problems}, open(STATE, "w"), indent=1)
    if not problems:
        print("Scoring check: all leagues identical")
        return
    changed = fp != prev_fp
    summary = " | ".join(problems)
    if not enabled or not (weekly or changed):
        why = "alerts disabled" if not enabled else "unchanged since last run; next alert Tuesday"
        print(f"::warning::Scoring mismatch ({why}): {summary}")
        return
    msg = ("@everyone 🚨 **SCORING SETTINGS ALERT — NCAA 180** 🚨\n"
           + ("Weekly reminder — still unresolved. " if weekly and not changed else "")
           + "All 15 leagues must have identical scoring. Found:\n"
           + "\n".join(f"• {p}" for p in problems)
           + f"\nSeason {season}. Fix in Sleeper league settings. "
             "Re-alerts every Tuesday until resolved, or immediately if anything changes.")[:1990]
    sent = False
    if hook and re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        r = requests.post(hook + "?wait=true", json={"content": msg, "allowed_mentions": {"parse": ["everyone"]}},
                          timeout=30)
        sent = r.status_code < 300
    if not sent:  # let the next run retry
        json.dump({"fingerprint": prev_fp, "checked": now, "problems": problems}, open(STATE, "w"), indent=1)
    print(f"::error::SCORING MISMATCH ({'alert sent' if sent else 'ALERT NOT SENT'}): {summary}")
