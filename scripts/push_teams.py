"""
push_teams.py -- the team/league lists for the app's follow picker (reports/app.html).

Writes reports/data/push-teams.json from data/Teams.csv (current season) + LeagueShortNames.
Keys match what the sender (notify.py) uses: "<group>|<league short>:<roster ID>" for teams,
"<group>|<league short>" for leagues, so a follow survives team renames (identity = slot).
Runs in the weekly job (cheap); CWD = repo root.
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402

OUT = "reports/data/push-teams.json"


def build():
    conf = notify.cfg()
    group = conf.get("group", "ncaa180")
    smap = notify.league_short_map()
    leagues = {}
    with open("data/Teams.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sh = smap.get(r["League"].strip(), r["League"].strip())
            lg = leagues.setdefault(sh, {"key": f"{group}|{sh}", "name": sh, "teams": []})
            lg["teams"].append({"key": f"{group}|{notify.slot_key(sh, r['Roster ID'])}", "name": r["Team"].strip()})
    out = []
    for sh in sorted(leagues):
        lg = leagues[sh]
        lg["teams"].sort(key=lambda t: t["name"])
        out.append(lg)
    events = [{"key": f"{group}|{e['key']}", "label": e["label"], "default": e.get("default", False)}
              for e in conf["events"]]
    return {"group": group, "app_name": conf["app_name"], "worker_url": conf.get("worker_url", ""),
            "vapid_public_key": conf["vapid_public_key"], "max_follows": conf.get("max_follows", 60),
            "leagues": out, "events": events}


def main():
    data = build()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if not os.path.exists(OUT) or open(OUT, encoding="utf-8").read() != text:
        open(OUT, "w", encoding="utf-8").write(text)
        print(f"wrote {OUT}: {sum(len(l['teams']) for l in data['leagues'])} teams, {len(data['leagues'])} leagues")
    else:
        print(f"{OUT} unchanged")


if __name__ == "__main__":
    main()
