"""
draft_picks.py -- who owns every future rookie-draft pick, in all 15 leagues.

Writes data/FuturePicks_Current.csv (overwritten each run):
  LeagueID, LeagueName, Season, Round, OriginalRosterID, OwnerRosterID

How ownership is built (per league):
  1. Default: every roster owns its own pick in each round (settings.draft_rounds).
  2. Sleeper's /traded_picks lists every pick that changed hands: roster_id = original
     team, owner_id = current owner (both roster IDs). Those override the default.
  3. Seasons counted: every season Sleeper reports in traded_picks, plus the league's
     current..current+3 tradable window -- minus any season whose rookie draft is
     already complete (traded_picks keeps listing those after the draft).

Fails per league without stopping the others; a failed league keeps last run's rows,
and the run is flagged (exit 1) so it shows in the Actions summary.
CWD must be repo root.
"""
import sys
import time

import pandas as pd
import requests
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

BASE = lcfg.sleeper()
LEAGUES = "data/LeagueIDs_AllYears.csv"
OUT = "data/FuturePicks_Current.csv"
WINDOW = lcfg.cfg()["draft"]["pick_trade_window"]  # NCAA 180 allows trading picks for the current season + 3 more (confirmed: 2029 tradable in 2026)

s = requests.Session()
s.headers.update({"User-Agent": "NCAA180-Sleeper/1.0"})


def get(path):
    for attempt in range(3):
        try:
            r = s.get(f"{BASE}{path}", timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    lg = pd.read_csv(LEAGUES, dtype=str)
    year = lg["Year"].astype(int).max()
    lg = lg[lg["Year"].astype(int) == year]
    rows, failed = [], []
    for r in lg.itertuples():
        try:
            info = get(f"/league/{r.LeagueID}")
            rounds = int((info.get("settings") or {}).get("draft_rounds") or 4)
            rosters = [int(x["roster_id"]) for x in get(f"/league/{r.LeagueID}/rosters")]
            traded = get(f"/league/{r.LeagueID}/traded_picks") or []
            drafts = get(f"/league/{r.LeagueID}/drafts") or []
            done = {int(d["season"]) for d in drafts if d.get("status") == "complete" and d.get("season")}
            seasons = set(range(year, year + WINDOW)) | {int(t["season"]) for t in traded}
            seasons = sorted(x for x in seasons if x not in done)
            own = {(se, rd, ro): ro for se in seasons for rd in range(1, rounds + 1) for ro in rosters}
            for t in traded:
                k = (int(t["season"]), int(t["round"]), int(t["roster_id"]))
                if k in own and t.get("owner_id") is not None:
                    own[k] = int(t["owner_id"])
            for (se, rd, ro), ow in own.items():
                rows.append({"LeagueID": r.LeagueID, "LeagueName": r.LeagueName, "Season": se,
                             "Round": rd, "OriginalRosterID": ro, "OwnerRosterID": ow})
            print(f"{r.LeagueName}: seasons {seasons}, {rounds} rounds, {len(traded)} traded entries")
            time.sleep(0.3)
        except Exception as e:
            print(f"WARNING: {r.LeagueName} ({r.LeagueID}) failed: {e}")
            failed.append(r.LeagueName)
    out = pd.DataFrame(rows)
    if failed:
        try:  # keep last known ownership for leagues that failed this run
            prev = pd.read_csv(OUT, dtype=str)
            prev = prev[prev["LeagueName"].isin(failed)]
            out = pd.concat([out.astype(str), prev], ignore_index=True)
        except FileNotFoundError:
            pass
    out.to_csv(OUT, index=False)
    print(f"Wrote {OUT}: {len(rows)} picks")
    if failed:
        print(f"ERROR: picks missing for {failed}")
        sys.exit(1)


if __name__ == "__main__":
    main()
