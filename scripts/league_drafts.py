"""
league_drafts.py -- drafts and draft picks, CURRENT SEASON ONLY.

Writes data/Drafts_Season.csv and data/DraftPicks_Season.csv. Past seasons are frozen in
data/Drafts_Historic.csv and data/DraftPicks_Historic.csv (never rewritten; the offseason
rollover moves the finished season there). Current season = latest Year in
LeagueIDs_AllYears.csv. Rows sorted for byte-identical output when nothing changed.
"""
import pandas as pd
import time
from sleeper_wrapper.league import League
from sleeper_wrapper.drafts import Drafts
import requests

# -------------------------
# CONFIG
# -------------------------
INPUT_FILE = "data/LeagueIDs_AllYears.csv"
OUTPUT_DRAFTS = "data/Drafts_Season.csv"
OUTPUT_PICKS = "data/DraftPicks_Season.csv"

# -------------------------
# HELPER FUNCTIONS
# -------------------------
def safe_get_drafts(league_id, league_name):
    """Safely fetch all drafts for a given league."""
    try:
        drafts = League(league_id).get_all_drafts()
        if not drafts:
            print(f"⚠️  No drafts found for {league_name} ({league_id})")
        return drafts or []
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching drafts for {league_name} ({league_id}): {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error fetching drafts for {league_name} ({league_id}): {e}")
        return []

def safe_get_picks(draft_id, league_name):
    """Safely fetch all picks for a given draft."""
    try:
        picks = Drafts(draft_id).get_all_picks()
        if isinstance(picks, dict) and "message" in picks:
            # Sleeper sometimes returns {'message': 'Not Found'} instead of raising error
            print(f"⚠️  Draft not available for {league_name} ({draft_id})")
            return []
        return picks or []
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Network error fetching picks for draft {draft_id}: {e}")
        return []
    except Exception as e:
        print(f"⚠️  Unexpected error fetching picks for draft {draft_id}: {e}")
        return []

# -------------------------
# MAIN SCRIPT
# -------------------------
league_ids_df = pd.read_csv(INPUT_FILE)
league_ids_df = league_ids_df[league_ids_df["Year"] == league_ids_df["Year"].max()]
all_drafts = []
all_picks = []

for _, row in league_ids_df.iterrows():
    league_id = row["LeagueID"]
    league_name = row["LeagueName"]

    print(f"\nFetching draft info for league {league_name} ({league_id})...")

    drafts = safe_get_drafts(league_id, league_name)
    if not drafts:
        continue  # skip this league if no drafts available

    for draft in drafts:
        draft_id = draft.get("draft_id")
        rounds = draft.get("settings", {}).get("rounds", 0)
        num_teams = draft.get("settings", {}).get("teams", 0)

        all_drafts.append({
            "LeagueID": league_id,
            "LeagueName": league_name,
            "DraftID": draft_id,
            "Status": draft.get("status"),
            "Type": draft.get("type"),
            "Season": draft.get("season"),
            "Rounds": rounds,
            "Teams": num_teams
        })

        picks = safe_get_picks(draft_id, league_name)
        if not isinstance(picks, list):
            print(f"⚠️  Invalid pick data for {league_name} ({draft_id})")
            continue

        for p in picks:
            meta = p.get("metadata", {}) or {}
            round_no = p.get("round")
            pick_no = p.get("pick_no")

            overall_pick = None
            if round_no and pick_no and num_teams:
                overall_pick = ((round_no - 1) * num_teams) + pick_no

            all_picks.append({
                "LeagueID": league_id,
                "LeagueName": league_name,
                "DraftID": draft_id,
                "Round": round_no,
                "Pick_No": pick_no,
                "OverallPick": overall_pick,
                "Picked_By": p.get("picked_by"),
                "RosterID": p.get("roster_id"),
                "PlayerID": meta.get("player_id"),
                "FirstName": meta.get("first_name"),
                "LastName": meta.get("last_name"),
                "Team": meta.get("team"),
                "Position": meta.get("position"),
                "Status": meta.get("status"),
                "YearsExp": meta.get("years_exp")
            })

        # Light rate limit buffer (Sleeper API friendly)
        time.sleep(0.2)

# -------------------------
# SAVE OUTPUTS
# -------------------------
drafts_df = pd.DataFrame(all_drafts)
picks_df = pd.DataFrame(all_picks)
if not drafts_df.empty:
    drafts_df = drafts_df.sort_values(["LeagueName", "DraftID"], key=lambda c: c if c.dtype.kind in "iuf" else c.astype(str)).reset_index(drop=True)
if not picks_df.empty:
    picks_df = picks_df.sort_values(["LeagueName", "DraftID", "Round", "Pick_No"],
                                    key=lambda c: c if c.dtype.kind in "iuf" else c.astype(str)).reset_index(drop=True)

drafts_df.to_csv(OUTPUT_DRAFTS, index=False)
picks_df.to_csv(OUTPUT_PICKS, index=False)

print(f"\n✅ Drafts and picks exported successfully!")
print(f"   • Drafts saved to: {OUTPUT_DRAFTS}")
print(f"   • Picks saved to:  {OUTPUT_PICKS}")
