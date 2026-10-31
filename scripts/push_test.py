"""
push_test.py -- send a test push to TESTER phones only (opened app.html?test=1). Run by the
"Push test" workflow. Real members never receive these (announcements marked test=True).

  MESSAGE="..."            plain test notification
  AS_WEEK="2025-14"        instead: a sample results push rebuilt from a past postseason week
                           (Postseason_Historic.csv), personalized per phone exactly like the real
                           thing -- your followed teams first, then playoff, bowl, NIT.
CWD = repo root.
"""
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402

HIST = "data/Postseason_Historic.csv"
TEAMS = "data/Teams.csv"
EVENT = {"Playoff": "playoff_results", "Bowl": "bowl_results", "NIT": "nit_results", "CCG": "ccg_results"}


def _slots():
    """Current team name -> (league short, slot key). Past seasons are mapped by today's name."""
    smap = notify.league_short_map()
    out = {}
    with open(TEAMS, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sh = smap.get(r["League"].strip(), r["League"].strip())
            out[r["Team"].strip()] = (sh, notify.slot_key(sh, r["Roster ID"]))
    return out


def sample_week(year, week):
    slots = _slots()
    items = []
    with open(HIST, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["Season"] == str(year) and r["Week"] == str(week)]
    for r in rows:
        ev = r["Event"]
        if ev not in EVENT:
            continue
        teams = [t.strip() for t in r["TeamA"].split("|") + ([r["TeamB"]] if r["TeamB"] else []) if t.strip()]
        found = [slots[t] for t in teams if t in slots]
        if len(teams) > 2:
            text = f"{r['Bowl'] or r['RoundName']}: {r['Winner']} advances"
        else:
            sa = f"({r['SeedA']}) " if r["SeedA"] else ""
            sb = f"({r['SeedB']}) " if r["SeedB"] else ""
            text = f"{r['Bowl'] or r['RoundName']}: {sa}{r['TeamA']} {r['ScoreA']} – {r['ScoreB']} {sb}{r['TeamB']}"
        seed = min((int(x) for x in (r["SeedA"], r["SeedB"]) if x.isdigit()), default=99)
        items.append({"text": text, "tier": ev, "event": EVENT[ev], "order": seed,
                      "slots": [s for _, s in found], "leagues": sorted({lg for lg, _ in found})})
    return items


def main():
    stamp = time.strftime("%Y%m%d%H%M%S")
    as_week = os.environ.get("AS_WEEK", "").strip()
    if as_week:
        year, week = as_week.split("-")
        items = sample_week(year, week)
        if not items:
            sys.exit(f"No postseason games found for {as_week} in {HIST}")
        ann = {"id": f"test-{stamp}", "event": "results", "test": True, "url": "matchups.html",
               "title": f"[TEST] Week {week} postseason results ({year})",
               "summary": f"Sample from {year}, week {week}", "items": items}
    else:
        msg = os.environ.get("MESSAGE", "").strip() or "Test push from NCAA 180"
        # A test push goes to every tester whatever it follows: an "event" every device matches.
        ann = {"id": f"test-{stamp}", "event": "test", "test": True, "url": "app.html",
               "title": "[TEST] NCAA 180", "summary": msg, "items": [], "everyone": True}
    if not notify.push_ready():
        sys.exit("Push is not configured: set config/push.json worker_url and the "
                 "VAPID_PRIVATE_KEY + PUSH_ADMIN_TOKEN secrets.")
    sent, pruned, failed = notify.send_push(ann)
    print(f"Test push sent to {sent} tester phone(s); pruned {pruned}; failed {failed}.")
    if sent == 0:
        print("::warning::No tester phones matched. Open app.html?test=1 on the phone, save, and try again.")


if __name__ == "__main__":
    main()
