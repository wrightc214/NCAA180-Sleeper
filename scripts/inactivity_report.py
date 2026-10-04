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
from tank_check import check_week  # noqa: E402

SRC = "data/LineupStreaks_Season.csv"
MATCHUPS = "data/Matchups_Season.csv"
LIMIT = 1800
LEAGUE_SHORT = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}
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

    try:
        tank = check_week(last_done, year)
        tank = tank[tank["Tier"] != ""] if not tank.empty else tank
    except Exception as e:
        note("warning", f"Tank check failed: {e}")
        tank = pd.DataFrame()
    t_alert = tank[tank["Tier"] == "Tank alert"] if not tank.empty else tank
    t_check = tank[tank["Tier"] == "Lineup check"] if not tank.empty else tank

    red = flagged[flagged["Tier"] == "Likely inactive"]
    yel = flagged[flagged["Tier"] == "Watch"]
    mention = f" · <@{contact}>" if contact else ""

    # Message 1: tank check (lineup choices in the last completed week)
    t_head = (f"🚨 **Tank check · week {last_done} lineups**{mention}"
              f"\n🚨 Tank alert: **{len(t_alert)}** · ⚠️ Lineup check: **{len(t_check)}**")
    t_body = ""
    for title, part in (("\n\n🚨 **Tank alert**", t_alert), ("\n\n⚠️ **Lineup check**", t_check)):
        if part.empty:
            continue
        t_body += title
        for r in part.itertuples():
            ben = ", ".join(r.Benched.split(", ")[:4])
            sta = ", ".join(r.Started.split(", ")[:4])
            t_body += (f"\n• **{r.Team}** ({LEAGUE_SHORT.get(r.LeagueName, r.LeagueName)}) {r.OwnerName} · "
                       f"{int(r.Ratio * 100)}% of best lineup · benched {ben} · started {sta}")
    t_tail = ("\n\n*% of best lineup* = starters' FantasyCalc redraft value vs. the best legal lineup from "
              "players who played that week. 🚨 under 60%, ⚠️ under 75% (with a meaningful value gap). "
              "Injured/bye/inactive bench players don't count. Full table attached.")
    t_files = {}
    if not tank.empty:
        tb = io.BytesIO(tank.drop(columns=["LeagueID"]).to_csv(index=False).encode())
        t_files["files[0]"] = (f"tank-check-week{last_done}.csv", tb, "text/csv")
    post(hook, fit(t_head, t_body, t_tail), contact, t_files)

    # Message 2: inactivity (+ orphan graphic when it changed)
    head = (f"📋 **Inactivity report · through week {last_done}**{mention}"
            + f"\n🔴 Likely inactive: **{len(red)}** · 🟡 Watch: **{len(yel)}** · Orphans (excluded): {orphans}")
    body = ""
    for title, part in (("\n\n🔴 **Likely inactive**", red), ("\n\n🟡 **Watch**", yel)):
        if part.empty:
            continue
        body += title + "".join("\n" + line(r) for r in part.itertuples())
    tail = ("\n\n*lineup Nw* = same starters N completed weeks · *N×0pt* = starters who scored 0 last week · "
            "*no moves Nw* = no adds/drops/trades.\n🔴 lineup 3w+ with 2+ 0-pt starters, or 3+ 0-pt starters. "
            "🟡 lineup 3w+, or 2 0-pt starters. Full list attached.")
    out = flagged[["Tier", "Team", "League", "OwnerName", "OwnerID", "L", "Z", "R"]].rename(
        columns={"L": "SameLineupWeeks", "Z": "ZeroPointStarters", "R": "NoRosterMoveWeeks"})
    files = {}
    if not out.empty:
        files["files[0]"] = (f"inactivity-week{last_done}.csv", io.BytesIO(out.to_csv(index=False).encode()), "text/csv")
    state = {}
    try:
        state = json.load(open(ORPHAN_STATE))
    except Exception:
        pass
    send_orphans = state.get("posted") is False and os.path.exists(ORPHAN_PNG)
    extra = ""
    if send_orphans:
        files["files[1]"] = ("ncaa180-open-teams.png", open(ORPHAN_PNG, "rb"), "image/png")
        extra = "\n\n🆕 **Open-teams recruiting graphic updated** (attached) — ready to share."
    post(hook, fit(head, body, tail + extra), contact, files)
    if send_orphans:
        state["posted"] = True
        json.dump(state, open(ORPHAN_STATE, "w"))
    note("notice", f"LM reports posted (week {last_done}): {len(t_alert)} tank alert, {len(t_check)} lineup check, "
                   f"{len(red)} likely inactive, {len(yel)} watch")


def fit(head, body, tail):
    msg = head + body + tail
    if len(msg) <= LIMIT:
        return msg
    keep = LIMIT - len(head) - len(tail) - 40
    return head + body[:keep].rsplit("\n", 1)[0] + "\n… (truncated — see attached CSV)" + tail


def post(hook, content, contact, files):
    payload = {"content": content, "allowed_mentions": {"parse": [], "users": [contact] if contact else []}}
    r = requests.post(hook + "?wait=true", data={"payload_json": json.dumps(payload)}, files=files or None, timeout=60)
    try:
        ok = r.status_code < 300 and "id" in r.json()
    except ValueError:
        ok = False
    if not ok:
        note("error", f"Discord did not accept the LM report (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
