"""
scoring_check.py -- 🚨 all 15 NCAA 180 leagues must use IDENTICAL scoring settings.
Imported by projection_snapshot.py (runs before every kickoff window + the weekly run),
so a change is caught within hours.

Alerts (to lm-private-data via DISCORD_WEBHOOK_LM_PRIVATE_DATA, @everyone in that
2-person channel) when:
  1. any league's scoring differs from the majority of leagues, or
  2. the shared scoring changed vs the last saved copy (data/projections/<season>/scoring.json),
     i.e. all leagues were changed at once.
Repeats at most once per 24h for the same problem; a new/different problem alerts at once.
State: data/ScoringCheck_Current.json.
"""
import collections
import datetime as dt
import hashlib
import json
import os
import re

import requests

STATE = "data/ScoringCheck_Current.json"


def _key(d):
    return json.dumps(d, sort_keys=True)


def _diff(a, b):
    keys = sorted(set(a) | set(b))
    return [f"{k}: {a.get(k, '—')} → {b.get(k, '—')}" for k in keys if a.get(k) != b.get(k)]


def check(scoring_all, names, previous):
    """scoring_all/previous: {league_id: settings}. Returns list of problem lines."""
    problems = []
    counts = collections.Counter(_key(v) for v in scoring_all.values())
    majority_key, n = counts.most_common(1)[0]
    majority = json.loads(majority_key)
    for lid, s in scoring_all.items():
        if _key(s) != majority_key:
            d = _diff(majority, s)
            problems.append(f"**{names.get(lid, lid)}** differs from the other leagues "
                            f"({len(d)} setting{'s' if len(d) != 1 else ''}): " + "; ".join(d[:8])
                            + (" …" if len(d) > 8 else ""))
    if previous:
        prev_counts = collections.Counter(_key(v) for v in previous.values())
        prev_major = json.loads(prev_counts.most_common(1)[0][0])
        if _key(prev_major) != majority_key:
            d = _diff(prev_major, majority)
            problems.append(f"League-wide scoring changed since last check ({len(d)} setting"
                            f"{'s' if len(d) != 1 else ''}): " + "; ".join(d[:8]) + (" …" if len(d) > 8 else ""))
    return problems


def alert(problems, season):
    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    fp = hashlib.sha1("\n".join(problems).encode()).hexdigest()[:12]
    now = dt.datetime.now(dt.timezone.utc)
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    if not problems:
        if st.get("status") != "ok":
            json.dump({"status": "ok", "checked": now.isoformat()}, open(STATE, "w"))
        print("Scoring check: all leagues identical")
        return
    last = st.get("alerted")
    if st.get("fingerprint") == fp and last and (now - dt.datetime.fromisoformat(last)).total_seconds() < 86400:
        print("::warning::Scoring mismatch still present (alerted within 24h)")
        return
    msg = ("@everyone 🚨 **SCORING SETTINGS ALERT — NCAA 180** 🚨\n"
           "All 15 leagues must have identical scoring. Found:\n"
           + "\n".join(f"• {p}" for p in problems)
           + f"\nSeason {season}. Fix in Sleeper league settings. Repeats daily until resolved.")[:1990]
    sent = False
    if hook and re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        r = requests.post(hook + "?wait=true", json={"content": msg, "allowed_mentions": {"parse": ["everyone"]}},
                          timeout=30)
        sent = r.status_code < 300
    print(f"::error::SCORING MISMATCH ({'alert sent' if sent else 'ALERT NOT SENT'}): " + " | ".join(problems))
    json.dump({"status": "mismatch", "fingerprint": fp, "alerted": now.isoformat() if sent else last,
               "problems": problems}, open(STATE, "w"), indent=1)
