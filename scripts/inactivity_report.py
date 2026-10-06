"""
inactivity_report.py -- weekly inactive-manager report to the private LM Discord channel
(lm-private-data, via DISCORD_WEBHOOK_LM_PRIVATE_DATA). Never posts to the league channel.

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
Env: DISCORD_WEBHOOK_LM_PRIVATE_DATA (secret), DISCORD_CONTACT_ID (variable). CWD must be repo root.
"""
import io
import time
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
LIMIT = 1900  # Discord message cap is 2000 chars
LEAGUE_SHORT = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}
ORPHAN_PNG = "reports/orphans.png"
ORPHAN_STATE = "data/OrphanCard_Current.json"  # posted=false -> new graphic not yet delivered


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
    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    if not hook:
        note("warning", "Inactivity report skipped: DISCORD_WEBHOOK_LM_PRIVATE_DATA not set")
        return
    if not re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        note("error", "DISCORD_WEBHOOK_LM_PRIVATE_DATA is not a Discord webhook URL")
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

    # One combined report, grouped by league (how the LM investigates), most serious first.
    SEV = {"Tank alert": 0, "Lineup check": 1, "Likely inactive": 2, "Watch": 3}
    ICON = {"Tank alert": "🚨", "Lineup check": "⚠️", "Likely inactive": "🔴", "Watch": "🟡"}
    teams = {}  # (league, team) -> [best severity, owner, reasons]; a team in both checks shows once

    def add(league, team, owner, tier, reason):
        t = teams.setdefault((league, team), [9, owner, []])
        t[0] = min(t[0], SEV[tier])
        t[2].append(reason)

    for r in (tank.itertuples() if not tank.empty else []):
        ben = ", ".join(r.Benched.split(", ")[:3])
        sta = ", ".join(r.Started.split(", ")[:3])
        add(LEAGUE_SHORT.get(r.LeagueName, r.LeagueName), r.Team, r.OwnerName, r.Tier,
            f"started only {int(r.Ratio * 100)}% of their best lineup (benched {ben}; started {sta})")
    for r in flagged.itertuples():
        why = []
        if r.L >= 2:
            why.append(f"same starting lineup {r.L} weeks in a row")
        if r.Z:
            why.append(f"{r.Z} starter{'s' if r.Z != 1 else ''} scored 0 last week")
        if r.R >= 3:
            why.append(f"no roster moves in {r.R} weeks")
        add(r.League, r.Team, r.OwnerName, r.Tier, ", ".join(why))
    icon_by_sev = {v: ICON[k] for k, v in SEV.items()}
    items = sorted(((lg, sev, team, f"{icon_by_sev[sev]} **{team}** · {owner} — " + "; ".join(why) + ".")
                    for (lg, team), (sev, owner, why) in teams.items()), key=lambda x: (x[0], x[1], x[2]))

    head = (f"📋 **LM report · week {last_done}**{mention}\n"
            f"🚨 Tank alert **{len(t_alert)}** · ⚠️ Lineup check **{len(t_check)}** · "
            f"🔴 Likely inactive **{len(red)}** · 🟡 Watch **{len(yel)}** · Orphans {orphans} (not listed)\n"
            "-# 🚨/⚠️ = benched clearly better players who played that week (under 60% / 75% of their "
            "best possible lineup, by FantasyCalc value). 🔴/🟡 = signs nobody is managing the team.")
    # Header message, then ONE MESSAGE PER LEAGUE (Discord formatting; easy to copy per league).
    by_league = {}
    for league, _, _, text in items:
        by_league.setdefault(league, []).append(text)
    msgs = [head + ("" if by_league else "\n\n✅ Nothing flagged this week.")]
    for league in sorted(by_league):
        body = f"__**{league}**__ · week {last_done}\n" + "\n".join(by_league[league])
        if len(body) > LIMIT:
            body = body[:LIMIT].rsplit("\n", 1)[0] + "\n… (more in the attached CSV)"
        msgs.append(body)

    files = {}
    if not tank.empty:
        tb = io.BytesIO(tank.drop(columns=["LeagueID"]).to_csv(index=False).encode())
        files["files[0]"] = (f"tank-check-week{last_done}.csv", tb, "text/csv")
    out = flagged[["Tier", "Team", "League", "OwnerName", "OwnerID", "L", "Z", "R"]].rename(
        columns={"L": "SameLineupWeeks", "Z": "ZeroPointStarters", "R": "NoRosterMoveWeeks"})
    if not out.empty:
        files["files[1]"] = (f"inactivity-week{last_done}.csv",
                             io.BytesIO(out.sort_values(["League", "Tier"]).to_csv(index=False).encode()), "text/csv")
    state = {}
    try:
        state = json.load(open(ORPHAN_STATE))
    except Exception:
        pass
    send_orphans = state.get("posted") is False and os.path.exists(ORPHAN_PNG)
    if send_orphans:
        files["files[2]"] = ("ncaa180-open-teams.png", open(ORPHAN_PNG, "rb"), "image/png")
        msgs[0] += "\n\n🆕 **Open-teams recruiting graphic updated** (attached) — ready to share."

    for i, m in enumerate(msgs):
        post(hook, m, contact if i == 0 else "", files if i == 0 else {})
        time.sleep(1.2)  # stay under Discord's webhook rate limit
    if send_orphans:
        state["posted"] = True
        json.dump(state, open(ORPHAN_STATE, "w"))
    note("notice", f"LM report posted (week {last_done}, {len(msgs)} message(s)): {len(t_alert)} tank alert, "
                   f"{len(t_check)} lineup check, {len(red)} likely inactive, {len(yel)} watch")


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
