"""
league_staff.py -- who runs each conference league (Chris, 2026-11-07, About page Directory).

For every league this season (found through the lookup account, like users.py), Sleeper's league users
list marks commissioners with is_owner. Writes data/LeagueStaff.csv:
  LeagueID, LeagueName, UserID, DisplayName, IsOwner (LM powers), HasRoster
Special accounts (config about.special_accounts) and the league manager / data contact
(config about.league_manager / about.data_contact, by Sleeper display name) are labeled on the page.
Runs in the weekly job (needs Sleeper; ~30 requests).

  python scripts/league_staff.py
"""
import os
import sys

import pandas as pd
from sleeper_wrapper import League, User

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402

OUT = "data/LeagueStaff.csv"


def main():
    os.chdir(lcfg.ROOT)
    rows = []
    for lg in User(int(lcfg.lookup_user_id())).get_all_leagues("nfl", lcfg.season()):
        lid, name = str(lg["league_id"]), lg["name"]
        api = League(lid)
        owners = set()
        for r in api.get_rosters():
            owners.add(str(r.get("owner_id")))
            owners.update(str(x) for x in (r.get("co_owners") or []))
        for u in api.get_users():
            rows.append({"LeagueID": lid, "LeagueName": name, "UserID": str(u["user_id"]), "DisplayName": u.get("display_name", ""),
                         "IsOwner": bool(u.get("is_owner")), "HasRoster": str(u["user_id"]) in owners})
    df = pd.DataFrame(rows).sort_values(["LeagueName", "DisplayName"])
    df.to_csv(OUT, index=False)
    print(f"{OUT}: {df['LeagueID'].nunique()} leagues, {int(df['IsOwner'].sum())} users with LM powers, "
          f"{int((~df['HasRoster']).sum())} without a roster")


if __name__ == "__main__":
    main()
