"""
league_transactions.py -- all transactions, CURRENT SEASON ONLY.

Writes data/Transactions_Season.csv. Past seasons are frozen in
data/Transactions_Historic.csv (never rewritten; the offseason rollover moves the
finished season there). Current season = latest Year in LeagueIDs_AllYears.csv.
Rosters are fetched once per league (not once per transaction).
Rows are sorted so unchanged data produces a byte-identical file (no git churn).
"""
import pandas as pd
from sleeper_wrapper import League
import time

league_df = pd.read_csv("data/LeagueIDs_AllYears.csv")
league_df = league_df[league_df["Year"] == league_df["Year"].max()]

all_transactions = []

OBSERVER_IDS = [731808894699028480]

for idx, row in league_df.iterrows():
    league_id = row['LeagueID']
    year = row['Year']
    league_name = row['LeagueName']

    print(f"Processing transactions for {league_name} ({year})")

    league_api = League(league_id)
    try:
        rosters = league_api.get_rosters()
    except Exception:
        rosters = []

    # Loop through each week (1–18)
    for week in range(1, 19):
        try:
            weekly_tx = league_api.get_transactions(week)
        except Exception as e:
            print(f"  ERROR fetching transactions for {league_id} week {week}: {e}")
            continue

        if not weekly_tx:
            continue

        for tx in weekly_tx:
            roster_ids = tx.get('roster_ids', [])
            owner_ids = []

            for r_id in roster_ids:
                owner_id = next((r['owner_id'] for r in rosters if r['roster_id'] == r_id), None)
                if owner_id is None or owner_id in OBSERVER_IDS:
                    owner_id = 0
                owner_ids.append(owner_id)

            all_transactions.append({
                "Year": year,
                "LeagueID": league_id,
                "LeagueName": league_name,
                "Week": week,
                "TransactionID": tx.get('transaction_id'),
                "Type": tx.get('type'),
                "RosterIDs": roster_ids,
                "OwnerIDs": owner_ids,
                "Picks": tx.get('draft_picks', []),
                "Adds": tx.get('adds', {}),
                "Drops": tx.get('drops', {}),
                "Status": tx.get('status'),
                "Created": tx.get('created')
            })

        # Polite pause
        time.sleep(0.5)

out_file = "data/Transactions_Season.csv"
tx_df = pd.DataFrame(all_transactions)
if not tx_df.empty:
    tx_df = tx_df.sort_values(["LeagueName", "Week", "Created", "TransactionID"],
                              key=lambda c: c if c.dtype.kind in "iuf" else c.astype(str)).reset_index(drop=True)
tx_df.to_csv(out_file, index=False)
print(f"Saved {len(all_transactions)} transactions to {out_file}")
