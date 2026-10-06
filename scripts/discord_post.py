"""
discord_post.py -- post the weekly report to the league Discord, or hold it and alert the
data manager privately if anything about the run looks wrong.

Normal:   league channel gets the message + reports/latest.png + short link + @data manager.
Abnormal: nothing goes to the league; the data manager channel gets the reason, the exact
          message/image that would have posted, and the run-log link.

Inputs (environment, set by the workflow):
  DISCORD_WEBHOOK_TEAM_STATS          league channel webhook (secret)
  DISCORD_WEBHOOK_LM_PRIVATE_DATA  private data manager channel webhook (secret)
  DISCORD_CONTACT_ID           data manager's Discord user ID (repo variable)
  FAILED                       space-separated failed script names ("" = none)
  PNG_STATUS                   outcome of the render step: success / skipped / failure / ""
  RUN_URL                      link to this workflow run
Missing webhooks -> prints a notice and exits 0 (feature not set up yet).
CWD must be repo root.
"""
import json
import re
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import built_weeks  # noqa: E402

PNG = "reports/latest.png"
SHORT_LINK = "https://ncaa180.short.gy/home"
MAX_BYTES = 9_500_000  # stay under Discord's smallest upload limit


def message(week, contact):
    ask = f"<@{contact}>" if contact else "the data manager"
    return (f"**NCAA 180 · Week {week} Awards** 🏆\n"
            f"Full report, standings and roster map: {SHORT_LINK}\n"
            f"Questions? Ask {ask}.")


def note(kind, text):
    """Print + GitHub annotation, so the outcome shows on the run summary page."""
    print(f"::{kind}::{text}")


def valid(url):
    return re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", url) is not None


def send(url, content, mention_ids, with_png):
    payload = {"content": content, "allowed_mentions": {"parse": [], "users": mention_ids}}
    files = {}
    if with_png:
        files["files[0]"] = ("ncaa180-weekly.png", open(PNG, "rb"), "image/png")
    r = requests.post(url + "?wait=true", data={"payload_json": json.dumps(payload)}, files=files or None, timeout=60)
    ok = r.status_code < 300
    try:
        ok = ok and "id" in r.json()  # wait=true returns the created message
    except ValueError:
        ok = False
    if not ok:
        note("error", f"Discord did not accept the post (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)


def main():
    league = os.environ.get("DISCORD_WEBHOOK_TEAM_STATS", "").strip()
    alert_hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    failed = os.environ.get("FAILED", "").split()
    png_status = os.environ.get("PNG_STATUS", "")
    run_url = os.environ.get("RUN_URL", "")

    if not league or not alert_hook:
        note("warning", "Discord post skipped: DISCORD_WEBHOOK_TEAM_STATS / DISCORD_WEBHOOK_LM_PRIVATE_DATA secret not set")
        return
    for name, u in (("DISCORD_WEBHOOK_TEAM_STATS", league), ("DISCORD_WEBHOOK_LM_PRIVATE_DATA", alert_hook)):
        if not valid(u):
            note("error", f"{name} is not a Discord webhook URL (expected https://discord.com/api/webhooks/<id>/<token>)")
            sys.exit(1)
    if not contact:
        note("warning", "DISCORD_CONTACT_ID variable not set; posting without the @ mention")

    weeks = built_weeks()
    week = max(weeks) if weeks else None
    png_ok = os.path.exists(PNG) and os.path.getsize(PNG) <= MAX_BYTES and png_status != "failure"

    problems = []
    if failed:
        problems.append(f"Scripts failed: {', '.join(failed)}")
    if week is None:
        problems.append("No weekly report found (reports/data/week-*.json)")
    if not os.path.exists(PNG):
        problems.append("Report image missing")
    elif os.path.getsize(PNG) > MAX_BYTES:
        problems.append(f"Report image too large for Discord ({os.path.getsize(PNG):,} bytes)")
    elif png_status == "failure":
        problems.append("Report image failed to render (existing image may be last week's)")

    msg = message(week if week else "?", contact)
    if not problems:
        send(league, msg, [contact] if contact else [], True)
        note("notice", f"Posted week {week} to the league channel.")
        return

    alert = ("⚠️ **NCAA 180 weekly post held** — nothing went to the league.\n"
             + "\n".join(f"• {p}" for p in problems)
             + (f"\nRun log: {run_url}" if run_url else "")
             + "\nTo release after fixing: run the workflow manually with `post` checked."
             + "\n\n**Would have posted:**\n>>> " + msg)
    send(alert_hook, alert, [contact] if contact else [], png_ok)
    note("warning", "League post held; alert sent: " + "; ".join(problems))


if __name__ == "__main__":
    main()
