import requests
import sys
import json
from datetime import datetime
import pytz
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

URL = lcfg.espn()

# ------------------------------------------------------------
# Timezone-aware timestamp
# ------------------------------------------------------------
eastern = pytz.timezone("America/New_York")
now_et = datetime.now(eastern)
weekday = now_et.strftime("%a")  # e.g. 'Mon'
hour_et = now_et.hour

# ------------------------------------------------------------
# Fetch API
# ------------------------------------------------------------
try:
    resp = requests.get(URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
except Exception as e:
    print(f"⚠️ Error fetching game status: {e}")
    sys.exit(2)

# ------------------------------------------------------------
# Extract week number
# ------------------------------------------------------------
week_number = data.get("week", {}).get("number")
if not week_number:
    print("⚠️ Could not determine current NFL week.")
    sys.exit(2)

# ------------------------------------------------------------
# Check if any games are active
# ------------------------------------------------------------
games_active = any(
    event.get("status", {}).get("type", {}).get("state", "").lower() == "in"
    for event in data.get("events", [])
)

# ------------------------------------------------------------
# Determine refresh interval
# ------------------------------------------------------------
refresh_interval = 15  # default

# Monday Night Football → faster refresh
if (weekday == "Mon" and hour_et >= 20) or (weekday == "Tue" and hour_et < 1):
    refresh_interval = 5

if not games_active:
    refresh_interval = 15

# ------------------------------------------------------------
# Output summary
# ------------------------------------------------------------
print(f"📅 Current NFL Week: {week_number}")
print(f"🕒 Local ET time: {now_et.strftime('%Y-%m-%d %I:%M %p')}")
print(f"🏈 Games active: {'YES' if games_active else 'NO'}")
print(f"🔁 Suggested refresh interval: {refresh_interval} min")

# ------------------------------------------------------------
# Save to JSON
# ------------------------------------------------------------
with open("nfl_status.json", "w") as f:
    json.dump(
        {
            "week_number": week_number,
            "games_active": games_active,
            "refresh_interval": refresh_interval,
            "timestamp_et": now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
        },
        f,
        indent=2,
    )

# ------------------------------------------------------------
# Exit codes
# ------------------------------------------------------------
if games_active:
    sys.exit(0)
else:
    sys.exit(1)
