"""Announce the latest finalized Guillotine cut after Tuesday's trophy posts."""
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import uuid

import guillotine
import week_gate
from sleeper_ccg_announcements import conference_league_ids, public_json, save_post_state

POSTS = Path("data/SleeperGuillotinePosts.json")
API = "https://api.sleeper.app/v1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def survivor_posts(rows, year, week, allowed_leagues, recorded, username_for):
    cut = [row for row in rows if row["Year"] == year and row["Week"] == str(week)]
    slots = {(row["LeagueID"], row["RosterID"]) for row in cut}
    if (not cut or len(slots) != len(cut)
            or any(row["FieldSize"] != str(len(cut)) or not row["FrozenAt"]
                   or row["Status"] not in {"Advanced", "Eliminated"} for row in cut)):
        return
    survivors = {}
    for row in cut:
        if row["Status"] == "Advanced":
            survivors.setdefault(row["LeagueID"], []).append(row)
    for league_id, teams in sorted(survivors.items()):
        key = f"{year}/{week}/{league_id}"
        if league_id not in allowed_leagues or key in recorded:
            continue
        lines = [f"The Guillotine · Week {week} survivors"]
        for team in sorted(teams, key=lambda row: row["Team"].casefold()):
            handle = username_for(league_id, team["RosterID"])
            lines.append(f"{team['Team']} & @{handle}" if handle else team["Team"])
        lines.append(f"You survived the cut. See you in Week {week + 1}!")
        yield key, league_id, "\n".join(lines)


def send_post(key, league_id, caption, token):
    body = {
        "operationName": "create_message",
        "query": """mutation create_message($league: String!, $client: String, $text: String) {
            create_message(parent_type: "league", parent_id: $league, client_id: $client, text: $text) {
                message_id parent_id
            }
        }""",
        "variables": {
            "league": league_id,
            "client": str(uuid.uuid5(uuid.NAMESPACE_URL, f"ncaa180.guillotine/{key}")),
            "text": caption,
        },
    }
    request = urllib.request.Request(
        "https://sleeper.app/graphql", data=json.dumps(body).encode(),
        headers={"Authorization": token, "Content-Type": "application/json",
                 "X-Sleeper-GraphQL-Op": "create_message"},
    )
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
        result = json.load(response)
    posted = (result.get("data") or {}).get("create_message") or {}
    if str(posted.get("parent_id")) != league_id or not posted.get("message_id"):
        raise ValueError("Sleeper did not confirm delivery")
    return str(posted["message_id"])


def main():
    token = os.environ.pop("SLEEPER_SESSION_TOKEN", "")
    year, active_week, _ = week_gate.state()
    week = active_week - 1
    settings = guillotine.settings()
    if not int(settings["first_week"]) <= week < int(settings["last_week"]):
        return
    if not Path(guillotine.SEASON_FILE).exists():
        return
    with open(guillotine.SEASON_FILE, encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    allowed_leagues = set(conference_league_ids(year).values())
    records = json.loads(POSTS.read_text(encoding="utf-8")) if POSTS.exists() else {}
    for key, record in records.items():
        if key.startswith(f"{year}/{week}/") and record["status"] == "pending":
            print(f"{key}: check league chat before reconciling the pending post.")

    rosters = {}
    accounts = {}

    def username_for(league_id, roster_id):
        if league_id not in rosters:
            rosters[league_id] = {
                str(row["roster_id"]): str(row["owner_id"])
                for row in public_json(f"{API}/league/{league_id}/rosters")
            }
        owner = rosters[league_id].get(roster_id, "")
        if not owner.isdigit():
            return ""
        if owner not in accounts:
            accounts[owner] = public_json(f"{API}/user/{owner}") or {}
        account = accounts[owner]
        username = account.get("username") or ""
        if str(account.get("user_id")) == owner and re.fullmatch(r"[A-Za-z0-9_]+", username):
            return username
        print(f"{league_id}/{roster_id}: could not verify the Sleeper username.")
        return ""

    failures = False
    posts = list(survivor_posts(rows, year, week, allowed_leagues, records, username_for))
    for key, league_id, caption in posts:
        if not token:
            raise SystemExit("The SLEEPER_SESSION_TOKEN Actions secret is missing.")
        records[key] = {"status": "pending", "caption": caption}
        try:
            save_post_state(records, f"Reserve Guillotine survivors {key}", POSTS)
        except subprocess.CalledProcessError:
            raise SystemExit("Could not save the reservation. Further sends stopped.") from None
        try:
            message_id = send_post(key, league_id, caption, token)
        except (OSError, ValueError) as error:
            print(f"{key}: {type(error).__name__}. Check league chat before retrying.")
            failures = True
            continue
        records[key].update(status="sent", message_id=message_id)
        try:
            save_post_state(records, f"Confirm Guillotine survivors {key}", POSTS)
        except subprocess.CalledProcessError:
            raise SystemExit("Could not save the confirmation. Further sends stopped.") from None
        print(f"{key}: sent Sleeper message {message_id}.")
    if failures:
        raise SystemExit("One or more Guillotine posts need review.")
    if not posts:
        print(f"No new finalized Guillotine survivor posts for Week {week}.")


if __name__ == "__main__":
    main()
