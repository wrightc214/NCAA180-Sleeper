"""
poll_discord.py -- post the new poll to the league Discord, and the private ballot notes
to the data manager / LM channel.

League channel (team-stats): headline + reports/discord-poll/*.png + link to the poll page.
  Held instead (private alert, nothing to the league) when publish.post_to_league is
  false (preview mode) or the images are missing.
Private channel (lm-private-data): work/poll/flags.md when panel ballots exist
  (participation, ballot audit, own-team rank, highest/lowest outlier). Never in the repo.

Environment (set by poll.yml):
  DISCORD_WEBHOOK_TEAM_STATS, DISCORD_WEBHOOK_LM_PRIVATE_DATA (secrets), DISCORD_CONTACT_ID
  HUMAN_BALLOTS, POLL_TYPE, WEEK (outputs of poll_aggregate.py), RUN_URL
Missing webhooks -> notice, exit 0. CWD must be repo root.
"""
import glob
import json
import os
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from discord_post import note, valid  # noqa: E402

IMAGES = "reports/discord-poll/*.png"
LIMIT = 1900  # Discord message cap is 2000 chars


def send(url, content, mentions=(), files=()):
    payload = {"content": content, "allowed_mentions": {"parse": [], "users": list(mentions)}}
    fs = {f"files[{i}]": (os.path.basename(f), open(f, "rb"), "image/png") for i, f in enumerate(files)}
    r = requests.post(url + "?wait=true", data={"payload_json": json.dumps(payload)}, files=fs or None, timeout=60)
    if r.status_code >= 300:
        note("error", f"Discord did not accept the post (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)


def chunks(text):
    out, cur = [], ""
    for line in text.splitlines():
        if len(cur) + len(line) + 1 > LIMIT:
            out.append(cur)
            cur = ""
        cur += line + "\n"
    return out + ([cur] if cur.strip() else [])


def headline(cfg, ptype, week, human):
    p = pd.read_csv(pc.POLL_SEASON, dtype=str)
    year = p["Year"].astype(int).max()
    p = p[(p["Year"] == str(year)) & (p["PollType"] == ptype) & (p["ThroughWeek"] == str(week))]
    p = p.assign(_r=p["Rank"].astype(int)).sort_values("_r")
    top = p.iloc[0]
    fpv = int(float(top["FirstPlaceVotes"] or 0))
    rvr = 0
    if os.path.exists(pc.RANKED_GAMES):
        g = pd.read_csv(pc.RANKED_GAMES, dtype=str)
        rvr = int((g["RankedVsRanked"] == "True").sum())
    label = pc.poll_cfg(cfg, ptype).get("label", ptype)
    url = cfg.get("publish", {}).get("page_url", "")
    nb = int(float(top.get("BotsUsed") or 0))
    voters = f"{nb} bots" + (f" + {human} panel ballot{'s' if human != 1 else ''}" if human else "")
    lines = [f"**NCAA 180 {label} · through week {week}** 📊",
             f"#1 {top['Team']} ({fpv} first-place vote{'s' if fpv != 1 else ''}) · {voters}"]
    if rvr:
        lines.append(f"{rvr} ranked-vs-ranked game{'s' if rvr != 1 else ''} in week {week + 1}")
    if url:
        lines.append(f"Full poll: {url}")
    return "\n".join(lines)


def main():
    league = os.environ.get("DISCORD_WEBHOOK_TEAM_STATS", "").strip()
    private = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    ptype, week = os.environ.get("POLL_TYPE", ""), int(os.environ.get("WEEK", "0") or 0)
    human = int(os.environ.get("HUMAN_BALLOTS", "0") or 0)
    run_url = os.environ.get("RUN_URL", "")
    if not league or not private:
        note("warning", "Poll post skipped: Discord webhook secrets not set")
        return
    for name, u in (("DISCORD_WEBHOOK_TEAM_STATS", league), ("DISCORD_WEBHOOK_LM_PRIVATE_DATA", private)):
        if not valid(u):
            note("error", f"{name} is not a Discord webhook URL")
            sys.exit(1)

    cfg = pc.config()
    imgs = sorted(glob.glob(IMAGES))[:10]
    msg = headline(cfg, ptype, week, human)
    problems = []
    if not imgs:
        problems.append("Poll image missing")
    env = os.environ.get("POLL_POST_TO_LEAGUE", "").strip().lower()
    to_league = (env == "true") if env in ("true", "false") else bool(cfg.get("publish", {}).get("post_to_league", False))
    if not to_league:
        problems.append("Preview only: repo variable POLL_POST_TO_LEAGUE is not true (config/poll.json publish.post_to_league is the fallback)")

    if problems:
        send(private, "⚠️ **NCAA 180 poll post held** — nothing went to the league.\n"
             + "\n".join(f"• {p}" for p in problems)
             + (f"\nRun log: {run_url}" if run_url else "")
             + "\nTo release: set repo variable POLL_POST_TO_LEAGUE = true, then rerun the Poll workflow with `force` and `post` checked."
             + "\n\n**Would have posted:**\n>>> " + msg, [contact] if contact else [], imgs)
        note("warning", "Poll post held: " + "; ".join(problems))
    else:
        send(league, msg, [], imgs)
        note("notice", f"Posted {ptype} week {week} to the league channel.")

    flags = os.path.join(pc.WORK, "flags.md")
    if os.path.exists(flags):
        for part in chunks(open(flags, encoding="utf-8").read()):
            send(private, part)


if __name__ == "__main__":
    main()
