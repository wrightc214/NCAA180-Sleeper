"""
orphans.py -- registry of orphaned rosters (no real coach), past and present.

Writes:
  data/Orphans.csv  one row per orphan run:
    Team, League, LeagueName, RosterID, PreviousOwnerID, PreviousOwnerName,
    OrphanedYear, OrphanedWeek, Status (Active/Filled),
    FilledYear, FilledWeek, NewOwnerID, NewOwnerName
  data/RosterOwners_LastSeen.csv  each roster's owner at the last run. Needed because
    league_matchups.py stamps the CURRENT owner on every week of the season, so a
    mid-season departure would otherwise erase who the previous owner was.

"Orphan" = OwnerID == "Orphan" in the Matchups files (set by league_matchups.py and
patch_orphans_historic.py: caretaker, vacant, or deleted-account rosters).

First run (no Orphans.csv yet): seeds every orphan run found in Matchups_Historic +
Matchups_Season. Before tracking began only the season is known, so OrphanedWeek and
FilledWeek are blank on seeded rows.

Every later run: compares current owners with the registry.
  - newly orphaned roster  -> new Active row, OrphanedWeek = current week
  - Active roster now owned -> Status Filled, FilledYear/Week, NewOwner*
"Current week" = first regular/post-season week without final results (the week in
progress or about to start).

Rosters are matched across seasons by LeagueName + RosterID (LeagueIDs change yearly).
Team names come from the current-season Teams.csv.

CWD must be repo root. No API calls -- reads only files the pipeline already wrote,
so run it after `matchups`.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import current_week as cw  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

HIST = "data/Matchups_Historic.csv"
SEASON = "data/Matchups_Season.csv"
TEAMS = "data/Teams.csv"
OUT = "data/Orphans.csv"
LASTSEEN = "data/RosterOwners_LastSeen.csv"
ORPHAN = "Orphan"

LEAGUE_DISPLAY = lcfg.league_display()  # data/LeagueShortNames.csv + config display overrides
COLS = ["Team", "League", "LeagueName", "RosterID", "PreviousOwnerID", "PreviousOwnerName",
        "OrphanedYear", "OrphanedWeek", "Status", "FilledYear", "FilledWeek",
        "NewOwnerID", "NewOwnerName"]


def season_owners(df):
    """One owner per (Year, LeagueName, RosterID)."""
    return (df.sort_values("Week", key=lambda s: s.astype(int))
              .groupby(["Year", "LeagueName", "RosterID"], as_index=False)
              .agg(OwnerID=("OwnerID", "last"), OwnerName=("OwnerName", "last")))


def current_week(season):
    return str(cw(season["Year"].iloc[0]))


def team_lookup():
    t = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig")
    return {(r.League, r._3): r.Team for r in t.itertuples()}  # _3 = "Roster ID"


def seed(owners, teams):
    rows = []
    for (lg, rid), g in owners.groupby(["LeagueName", "RosterID"]):
        g = g.sort_values("Year", key=lambda s: s.astype(int))
        prev_id = prev_name = None
        run = None
        for r in g.itertuples():
            if r.OwnerID == ORPHAN:
                if run is None:
                    run = {"Team": teams.get((lg, rid), ""), "League": LEAGUE_DISPLAY.get(lg, lg),
                           "LeagueName": lg, "RosterID": rid,
                           "PreviousOwnerID": prev_id or "", "PreviousOwnerName": prev_name or "",
                           "OrphanedYear": r.Year, "OrphanedWeek": "", "Status": "Active",
                           "FilledYear": "", "FilledWeek": "", "NewOwnerID": "", "NewOwnerName": ""}
            else:
                if run is not None:
                    run.update(Status="Filled", FilledYear=r.Year,
                               NewOwnerID=r.OwnerID, NewOwnerName=r.OwnerName)
                    rows.append(run)
                    run = None
                prev_id, prev_name = r.OwnerID, r.OwnerName
        if run is not None:
            rows.append(run)
    return pd.DataFrame(rows, columns=COLS)


def last_real_owner(owners, lg, rid, last_seen):
    """Previous owner for a roster that just became orphaned."""
    ls = last_seen.get((lg, rid))
    if ls and ls[0] != ORPHAN:
        return ls
    g = owners[(owners.LeagueName == lg) & (owners.RosterID == rid) & (owners.OwnerID != ORPHAN)]
    if g.empty:
        return ("", "")
    r = g.sort_values("Year", key=lambda s: s.astype(int)).iloc[-1]
    return (r.OwnerID, r.OwnerName)


def main():
    hist = pd.read_csv(HIST, dtype=str)
    season = pd.read_csv(SEASON, dtype=str)
    year = season["Year"].iloc[0]
    owners = season_owners(pd.concat([hist, season], ignore_index=True))
    teams = team_lookup()
    week = current_week(season)
    now = owners[owners.Year == year]

    last_seen = {}
    if os.path.exists(LASTSEEN):
        ls = pd.read_csv(LASTSEEN, dtype=str)
        last_seen = {(r.LeagueName, r.RosterID): (r.OwnerID, r.OwnerName) for r in ls.itertuples()}

    if not os.path.exists(OUT):
        reg = seed(owners, teams)
        print(f"Seeded {OUT}: {len(reg)} orphan runs ({(reg.Status == 'Active').sum()} active)")
    else:
        reg = pd.read_csv(OUT, dtype=str, keep_default_na=False)[COLS]
        active = {(r.LeagueName, r.RosterID): i for i, r in reg[reg.Status == "Active"].iterrows()}
        new_rows = []
        for r in now.itertuples():
            k = (r.LeagueName, r.RosterID)
            if r.OwnerID == ORPHAN and k not in active:
                pid, pname = last_real_owner(owners, *k, last_seen)
                new_rows.append({"Team": teams.get(k, ""), "League": LEAGUE_DISPLAY.get(k[0], k[0]),
                                 "LeagueName": k[0], "RosterID": k[1],
                                 "PreviousOwnerID": pid, "PreviousOwnerName": pname,
                                 "OrphanedYear": year, "OrphanedWeek": week, "Status": "Active",
                                 "FilledYear": "", "FilledWeek": "", "NewOwnerID": "", "NewOwnerName": ""})
                print(f"NEW ORPHAN: {teams.get(k, k)} ({k[0]}), previous owner {pname}")
            elif r.OwnerID != ORPHAN and k in active:
                i = active[k]
                reg.loc[i, ["Status", "FilledYear", "FilledWeek", "NewOwnerID", "NewOwnerName"]] = \
                    ["Filled", year, week, r.OwnerID, r.OwnerName]
                print(f"FILLED: {reg.loc[i, 'Team']} ({k[0]}) by {r.OwnerName}")
        if new_rows:
            reg = pd.concat([reg, pd.DataFrame(new_rows, columns=COLS)], ignore_index=True)

    reg = reg.sort_values(["Status", "League", "Team"], ascending=[True, True, True])
    reg.to_csv(OUT, index=False)
    now[["LeagueName", "RosterID", "OwnerID", "OwnerName"]].to_csv(LASTSEEN, index=False)
    act = reg[reg.Status == "Active"]
    print(f"Active orphans ({len(act)}):")
    print(act[["Team", "League", "PreviousOwnerName", "OrphanedYear", "OrphanedWeek"]].to_string(index=False))


if __name__ == "__main__":
    main()
