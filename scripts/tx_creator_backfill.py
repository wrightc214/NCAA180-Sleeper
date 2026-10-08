"""
tx_creator_backfill.py -- ONE-TIME: add CreatorID (who actually made each move) to
transaction files pulled before league_transactions.py saved it.

Why: OwnerIDs holds each roster's owner at the time of the pull, so a team that changed
hands credits the new owner with the old owner's moves (e.g. Arizona State's Jan-May 2020
moves show Chris, whose account was created Aug 6, 2020). Sleeper's `creator` field is the
real actor (the commissioner for commissioner moves).

For every (LeagueID, Week) in the file it fetches
  https://api.sleeper.app/v1/league/<LeagueID>/transactions/<Week>
and maps transaction_id -> creator. Rows already carrying a CreatorID are kept.
Files processed: whichever exist of
  data/Transactions_Historic.csv, data/Transactions_Season.csv,
  data/backfill/Transactions_2019_2020.csv
or the paths given as arguments. Writes tx_creator_report.txt (coverage per file/year).

Run via the "Transaction creator backfill" workflow (Sleeper isn't reachable from every
environment). Run once, verify, then delete this script and its workflow.
CWD must be repo root.
"""
import os
import sys
import time

import pandas as pd
import requests

URL = "https://api.sleeper.app/v1/league/{}/transactions/{}"
DEFAULT = ["data/Transactions_Historic.csv", "data/Transactions_Season.csv",
           "data/backfill/Transactions_2019_2020.csv"]
HEAD = {"User-Agent": "NCAA180-Sleeper/1.0"}


def fetch(lid, week, tries=4):
    for i in range(tries):
        try:
            r = requests.get(URL.format(lid, week), timeout=30, headers=HEAD)
            if r.status_code == 200:
                return r.json() or []
            if r.status_code == 404:
                return []
        except requests.RequestException:
            pass
        time.sleep(2 ** i)
    print(f"::warning::gave up on league {lid} week {week}")
    return None


def main(paths):
    report = []
    for path in paths:
        if not os.path.exists(path):
            continue
        d = pd.read_csv(path, dtype=str, keep_default_na=False)
        if "CreatorID" not in d.columns:
            d["CreatorID"] = ""
        need = d[d["CreatorID"] == ""]
        pairs = sorted(set(zip(need["LeagueID"], need["Week"])))
        print(f"{path}: {len(need)} rows without CreatorID across {len(pairs)} league-weeks")
        creator = {}
        for n, (lid, wk) in enumerate(pairs, 1):
            txs = fetch(lid, str(int(float(wk))))
            for t in txs or []:
                creator[str(t.get("transaction_id"))] = str(t.get("creator") or "")
            if n % 50 == 0:
                print(f"  {n}/{len(pairs)} league-weeks")
            time.sleep(0.15)
        fill = d["CreatorID"] == ""
        d.loc[fill, "CreatorID"] = d.loc[fill, "TransactionID"].map(creator).fillna("")
        d.to_csv(path, index=False)
        for y, g in d.groupby("Year"):
            got = int((g["CreatorID"] != "").sum())
            # rows where the creator differs from every owner listed on the row
            diff = sum(1 for c, o in zip(g["CreatorID"], g["OwnerIDs"]) if c and c not in o)
            report.append(f"{path} {y}: {got}/{len(g)} with CreatorID; {diff} where the creator is not "
                          f"a listed owner (commissioner moves or teams that changed hands)")
    with open("tx_creator_report.txt", "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
