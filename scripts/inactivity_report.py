"""
inactivity_report.py -- weekly inactive-manager report to the private LM Discord channel
(lm-private-data, via DISCORD_ALERT_WEBHOOK_URL). Never posts to the league channel.

Source: data/LineupStreaks_Season.csv (lineup_streaks.py). Orphans are excluded (already
known) and only counted.

Counts are adjusted to COMPLETED weeks: LineupStreaks may run through the upcoming week,
whose lineup is "whatever is set right now" -- on Tuesday nobody has set it yet, so that
week is dropped from the streak to avoid flagging everyone by one extra week.

Tiers (L = same starting lineup, consecutive completed weeks; Z = starters who scored 0.0
in the last completed week -- bye/injured/cut players left in):
  🔴 Likely inactive : L >= 3 and Z >= 2,  or  Z >= 3
  🟡 Watch           : L >= 3,             or  Z == 2
Full flagged list attached as CSV.

Posts every run (an empty report confirms it ran).
Env: DISCORD_ALERT_WEBHOOK_URL (secret), DISCORD_CONTACT_ID (variable). CWD must be repo root.
"""
import io
import json
import os
import re
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from week_status import completed_weeks  # noqa: E402

SRC = "data/LineupStreaks_Season.csv"
MATCHUPS = "data/Matchups_Season.csv"
LIMIT = 1800
ORPHAN_PNG = "reports/orphans.png"
ORPHAN_STATE = "data/OrphanCard_Current.json"  # posted=false -> new graphic not yet delivered  # Discord message cap is 2000 chars


def note(kind, text):
    print(f"::{kind}::{text}")


def tiers(df, last_done):
    d = df[df["OwnerName"].astype(str) != "Orphan"].copy()
    upcoming = d["ThroughWeek"] > last_done
    d["L"] = (d["SameLineupWeeks"] - upcoming.astype(int)).clip(lower=0)
    d["R"] = (d["SameRosterWeeks"] - upcoming.astype(int)).clip(lower=0)
    d["Z"] = d["ZeroStarters"].fillna(0).astype(int)
    red = ((d["L"] >= 3) & (d["Z"] >= 2)) | (d["Z"] >= 3)
    yellow = ~red & ((d["L"] >= 3) | (d["Z"] == 2))
    d["Tier"] = ""
    d.loc[red, "Tier"] = "Likely inactive"
    d.loc[yellow, "Tier"] = "Watch"
    flagged = d[d["Tier"] != ""].sort_values(["Tier", "L", "Z"], ascending=[True, False, False])
    return flagged, int((df["OwnerName"].astype(str) == "Orphan").sum())


def line(r):
    bits = [f"lineup {r.L}w"] if r.L >= 2 else []
    if r.Z:
        bits.append(f"{r.Z}×0pt")
    if r.R >= 3:
        bits.append(f"no moves {r.R}w")
    return f"• **{r.Team}** ({r.League}) {r.OwnerName} · " + " · ".join(bits)


def main():
    hook = os.environ.get("DISCORD_ALERT_WEBHOOK_URL", "").strip()
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    if not hook:
        note("warning", "Inactivity report skipped: DISCORD_ALERT_WEBHOOK_URL not set")
        return
    if not re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        note("error", "DISCORD_ALERT_WEBHOOK_URL is not a Discord webhook URL")
        sys.exit(1)

    df = pd.read_csv(SRC)
    year = pd.read_csv(MATCHUPS, dtype=str)["Year"].iloc[0]
    done = completed_weeks(year)
    last_done = max(done, default=0)
    if last_done < 2:
        note("notice", "Inactivity report skipped: fewer than 2 completed weeks")
        return
    flagged, orphans = tiers(df, last_done)

    red = flagged[flagged["Tier"] == "Likely inactive"]
    yel = flagged[flagged["Tier"] == "Watch"]
    head = (f"📋 **Inactivity report · through week {last_done}**"
            + (f" · <@{contact}>" if contact else "")
            + f"\n🔴 Likely inactive: **{len(red)}** · 🟡 Watch: **{len(yel)}** · Orphans (excluded): {orphans}")
    body = ""
    for title, part in (("\n\n🔴 **Likely inactive**", red), ("\n\n🟡 **Watch**", yel)):
        if part.empty:
            continue
        chunk = title
        for r in part.itertuples():
            chunk += "\n" + line(r)
        body += chunk
    tail = ("\n\n*lineup Nw* = same starters N completed weeks · *N×0pt* = starters who scored 0 last week · "
            "*no moves Nw* = no adds/drops/trades.\n🔴 lineup 3w+ with 2+ 0-pt starters, or 3+ 0-pt starters. "
            "🟡 lineup 3w+, or 2 0-pt starters. Full list attached.")
    msg = head + body + tail
    if len(msg) > LIMIT:
        keep = LIMIT - len(head) - len(tail) - 60
        msg = head + body[:keep].rsplit("\n", 1)[0] + "\n… (truncated — see attached CSV)" + tail

    out = flagged[["Tier", "Team", "League", "OwnerName", "OwnerID", "L", "Z", "R"]].rename(
        columns={"L": "SameLineupWeeks", "Z": "ZeroPointStarters", "R": "NoRosterMoveWeeks"})
    buf = io.BytesIO(out.to_csv(index=False).encode())
    payload = {"content": msg, "allowed_mentions": {"parse": [], "users": [contact] if contact else []}}
    files = {}
    if not out.empty:
        files["files[0]"] = (f"inactivity-week{last_done}.csv", buf, "text/csv")
    state = {}
    try:
        state = json.load(open(ORPHAN_STATE))
    except Exception:
        pass
    send_orphans = state.get("posted") is False and os.path.exists(ORPHAN_PNG)
    if send_orphans:
        files["files[1]"] = ("ncaa180-open-teams.png", open(ORPHAN_PNG, "rb"), "image/png")
        payload["content"] += "\n\n🆕 **Open-teams recruiting graphic updated** (attached) — ready to share."
    files = files or None
    r = requests.post(hook + "?wait=true", data={"payload_json": json.dumps(payload)}, files=files, timeout=60)
    try:
        ok = r.status_code < 300 and "id" in r.json()
    except ValueError:
        ok = False
    if not ok:
        note("error", f"Discord did not accept the inactivity report (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)
    if send_orphans:
        state["posted"] = True
        json.dump(state, open(ORPHAN_STATE, "w"))
    note("notice", f"Inactivity report posted: {len(red)} likely inactive, {len(yel)} watch (week {last_done})")


if __name__ == "__main__":
    main()
