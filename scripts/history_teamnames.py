"""One-off: user-entered team names per league/season (Sleeper league users metadata) mapped to roster slots.
Each season's league keeps its own user metadata, so a past league shows the name last set in that league."""
import csv, requests, time
B = "https://api.sleeper.app/v1"
ids = []
for f in ["data/LeagueIDs_AllYears.csv", "data/backfill/LeagueIDs_2019_2020.csv"]:
    for r in csv.DictReader(open(f)):
        ids.append((r["Year"], r["LeagueID"], r["LeagueName"].strip()))
out = []
for y, lid, name in sorted(set(ids)):
    users = requests.get(f"{B}/league/{lid}/users", timeout=30).json() or []
    rosters = requests.get(f"{B}/league/{lid}/rosters", timeout=30).json() or []
    u = {x["user_id"]: x for x in users}
    for r in rosters:
        for oid in [r.get("owner_id")] + (r.get("co_owners") or []):
            if not oid: continue
            x = u.get(oid, {})
            out.append([y, lid, name, r["roster_id"], oid, x.get("display_name", ""),
                        (x.get("metadata") or {}).get("team_name", ""), "co" if oid != r.get("owner_id") else "owner"])
        if not r.get("owner_id"):
            out.append([y, lid, name, r["roster_id"], "", "", "", "no owner"])
    time.sleep(0.2)
w = csv.writer(open("data/backfill/UserTeamNames_AllYears.csv", "w", newline=""))
w.writerow(["Year", "LeagueID", "LeagueName", "RosterID", "UserID", "DisplayName", "UserTeamName", "Role"])
w.writerows(out)
print(len(out))
