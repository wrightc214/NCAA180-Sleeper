"""
discord_post.py -- post the weekly report to the league Discord, or hold it and alert the
commissioner privately if anything about the run looks wrong.

Normal:   league channel gets the message + reports/latest.png + short link + @commissioner.
Abnormal: nothing goes to the league; the commissioner channel gets the reason, the exact
          message/image that would have posted, and the run-log link.

Inputs (environment, set by the workflow):
  DISCORD_WEBHOOK_URL          league channel webhook (secret)
  DISCORD_COMMISH_WEBHOOK_URL  private commissioner channel webhook (secret)
  DISCORD_COMMISH_ID           commissioner's Discord user ID (repo variable)
  FAILED                       space-separated failed script names ("" = none)
  PNG_STATUS                   outcome of the render step: success / skipped / failure / ""
  RUN_URL                      link to this workflow run
Missing webhooks -> prints a notice and exits 0 (feature not set up yet).
CWD must be repo root.
"""
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import built_weeks  # noqa: E402

PNG = "reports/latest.png"
SHORT_LINK = "https://ncaa180.short.gy/home"
MAX_BYTES = 9_500_000  # stay under Discord's smallest upload limit


def message(week, commish):
    ask = f"<@{commish}>" if commish else "the commissioner"
    return (f"**NCAA 180 · Week {week} Awards** 🏆\n"
            f"Full report, standings and roster map: {SHORT_LINK}\n"
            f"Questions? Ask {ask}.")


def send(url, content, mention_ids, with_png):
    payload = {"content": content, "allowed_mentions": {"parse": [], "users": mention_ids}}
    files = {}
    if with_png:
        files["files[0]"] = ("ncaa180-weekly.png", open(PNG, "rb"), "image/png")
    r = requests.post(url, data={"payload_json": json.dumps(payload)}, files=files or None, timeout=60)
    if r.status_code >= 300:
        print(f"ERROR: Discord returned {r.status_code}: {r.text[:300]}")
        sys.exit(1)


def main():
    league = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    commish_hook = os.environ.get("DISCORD_COMMISH_WEBHOOK_URL", "").strip()
    commish = os.environ.get("DISCORD_COMMISH_ID", "").strip()
    failed = os.environ.get("FAILED", "").split()
    png_status = os.environ.get("PNG_STATUS", "")
    run_url = os.environ.get("RUN_URL", "")

    if not league or not commish_hook:
        print("Discord webhooks not configured; skipping post.")
        return

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

    msg = message(week if week else "?", commish)
    if not problems:
        send(league, msg, [commish] if commish else [], True)
        print(f"Posted week {week} to the league channel.")
        return

    alert = ("⚠️ **NCAA 180 weekly post held** — nothing went to the league.\n"
             + "\n".join(f"• {p}" for p in problems)
             + (f"\nRun log: {run_url}" if run_url else "")
             + "\nTo release after fixing: run the workflow manually with `post` checked."
             + "\n\n**Would have posted:**\n>>> " + msg)
    send(commish_hook, alert, [commish] if commish else [], png_ok)
    print("Held league post; alerted commissioner:\n" + "\n".join(problems))


if __name__ == "__main__":
    main()
