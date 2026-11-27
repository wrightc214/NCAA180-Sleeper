"""Deliver published NCAA 180 postseason pairings to the participating leagues."""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import uuid
from zoneinfo import ZoneInfo

import _postseason_common as postseason
import league_config
import week_gate

LEDGER = Path("data/SleeperPostseasonMatchupPosts.json")
APPROVALS = Path("data/SleeperPostseasonMatchupApprovals.json")
API = "https://api.sleeper.app/v1"
EVENTS = {"Playoff": "Playoff", "Bowl": "Bowl", "NIT": "NIT"}
TEST_LEAGUE = "1432137859359313920"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def opening_weeks(config):
    events = config["postseason"]
    return {
        "Playoff": int(events["playoff"]["first_week"]),
        "Bowl": min(int(tier["week"]) for tier in events["bowls"]["tiers"]),
        "NIT": int(events["nit"]["group_stage_1"]["week"]),
    }


def playoff_cut_line(year):
    with open(postseason.FIELD_FILE, encoding="utf-8-sig", newline="") as source:
        selected = [row for row in csv.DictReader(source)
                    if row["Year"] == year and row["BidType"] == "At-Large"]
    if not selected:
        return ""
    # The published field preserves selection order, including a resolved cut-line tie.
    last = selected[-1]
    return (f"Last at-large in: {int(last['Wins'])}–{int(last['Losses'])}, "
            f"{float(last['PointsFor']):,.1f} pts. Think there's an error? Let us know.")


def matchup_posts(rows, year, week, league_ids, handle_for, recorded, *,
                  events=EVENTS, cut_lines=None):
    games = defaultdict(list)
    for row in rows:
        if (row["Year"] == year and row["Week"] == week and row["GameID"]
                and row["Round"] in events):
            games[row["GameID"]].append(row)

    for game_id, sides in sorted(games.items()):
        group = sides[0]["Round"] == "NIT" and sides[0]["BowlName"].startswith("Group ")
        if (len(sides) < 2 or (len(sides) != 2 and not group)
                or any(side["Status"] != "Pending" for side in sides)):
            continue
        if len({(side["LeagueID"], side["RosterID"]) for side in sides}) != len(sides):
            continue
        if any(
            side["LeagueID"] not in league_ids or not side["RosterID"].isdigit()
            or not side["Team"]
            for side in sides
        ):
            continue
        first = sides[0]
        if any(side["Round"] != first["Round"] for side in sides):
            continue
        event = EVENTS[first["Round"]]
        details = first["BowlName"] or first["PlayoffRound"] or first["Stage"]
        heading = f"{year} NCAA 180 {event} {'group' if group else 'matchup'}"
        if details:
            heading += f" · {details}"
        for league_id in sorted({side["LeagueID"] for side in sides}):
            key = f"{year}/{week}/{game_id}/{league_id}"
            if key in recorded:
                continue
            teams = []
            for side in sides:
                team = side["Team"]
                if side["LeagueID"] == league_id:
                    handle = handle_for(league_id, side["RosterID"])
                    if handle:
                        team += f" & @{handle}"
                teams.append(team)
            lineup = (" · " if group else " vs. ").join(teams)
            caption = f"{heading}\n{lineup}\nGood luck!"
            cut_line = (cut_lines or {}).get(first["Round"])
            if cut_line:
                caption += f"\n{cut_line}"
            yield key, league_id, caption


def save_state(records, message, path=LEDGER):
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(path)], check=True)
    subprocess.run([
        "git", "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit", "--only", "-m", message, "--", str(path),
    ], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:refs/heads/main"], check=True)


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
            "client": str(uuid.uuid5(uuid.NAMESPACE_URL, f"ncaa180.postseason-matchup/{key}")),
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


def review_code(rows, year, week, league_ids, posts):
    fields = ("GameID", "Week", "Round", "Stage", "BowlName", "PlayoffRound",
              "LeagueID", "RosterID", "Team", "Seed", "Status", "Outcome", "Points")
    published = sorted(tuple(row[field] for field in fields) for row in rows
                       if row["Year"] == year and (row["Week"] == str(week)
                                                  or row["Status"] == "Final"))
    scores = {}
    for league_id in sorted(league_ids):
        matchups = fetch_json(f"{API}/league/{league_id}/matchups/{week - 1}")
        scores[league_id] = sorted(
            (row["roster_id"], row.get("points"), row.get("custom_points"),
             row.get("starters"), row.get("players_points"))
            for row in matchups
        )
    snapshot = json.dumps([year, week, published, scores, sorted(posts)], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(snapshot.encode()).hexdigest()


def post_private_review(year, week, code, posts, league_names):
    from discord_post import valid
    from poll_discord import send

    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "")
    if not valid(hook):
        raise SystemExit("The LM private-data Discord webhook is not configured.")
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    prefix = f"<@{contact}> " if contact else ""
    summary = (
        f"{prefix}**Sleeper matchup review · {year} Week {week}**\n"
        "Review the published pairings below. To approve this exact slate, run "
        "**Sleeper postseason matchups** in GitHub Actions and paste this approval code:\n"
        f"`{code}`"
    )
    send(hook, summary, mentions=[contact] if contact else [])
    batch = ""
    for _, league_id, caption in posts:
        entry = f"**{league_names[league_id]}**\n{caption}"
        if batch and len(batch) + len(entry) + 2 > 1800:
            send(hook, batch, mentions=[])
            batch = ""
        batch = f"{batch}\n\n{entry}" if batch else entry
    if batch:
        send(hook, batch, mentions=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--approve", default="")
    args = parser.parse_args()
    if sum((args.scheduled, args.review, bool(args.approve))) > 1:
        parser.error("select one notification stage")
    if args.scheduled and datetime.now(ZoneInfo("America/New_York")).weekday() != 2:
        return
    year, week, _ = week_gate.state()
    config = league_config.cfg()
    schedule = config["schedule"]
    if not int(schedule["postseason_start_week"]) <= week <= int(schedule["postseason_end_week"]):
        print(f"Week {week} is outside the NCAA 180 postseason window.")
        return

    initial = {event for event, first in opening_weeks(config).items() if first == week}
    if not initial and (args.review or args.approve):
        if args.approve:
            raise SystemExit("This week does not require matchup approval.")
        return

    short_names = {full: short for short, full in postseason.league_short().items()}
    with open("data/LeagueIDs_AllYears.csv", encoding="utf-8-sig", newline="") as source:
        league_names = {
            row["LeagueID"]: short_names.get(row["LeagueName"], row["LeagueName"])
            for row in csv.DictReader(source)
            if row["Year"] == year and row["LeagueID"].isdigit() and row["LeagueID"] != TEST_LEAGUE
        }
    league_ids = set(league_names)
    publish = args.scheduled
    token = os.environ.pop("SLEEPER_SESSION_TOKEN", "")
    if publish and not token:
        raise SystemExit("The SLEEPER_SESSION_TOKEN Actions secret is missing.")
    records = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}
    for key, record in records.items():
        if key.startswith(f"{year}/{week}/") and record["status"] == "pending":
            print(f"{key}: check the league chat before retrying this matchup.")

    rosters = {}
    accounts = {}

    def handle_for(league_id, roster_id):
        if league_id not in rosters:
            rosters[league_id] = {
                str(row["roster_id"]): str(row["owner_id"])
                for row in fetch_json(f"{API}/league/{league_id}/rosters")
            }
        owner = rosters[league_id].get(roster_id, "")
        if not owner.isdigit():
            return ""
        if owner not in accounts:
            accounts[owner] = fetch_json(f"{API}/user/{owner}") or {}
        account = accounts[owner]
        if str(account.get("user_id")) != owner:
            return ""
        handle = account.get("username") or ""
        return handle if re.fullmatch(r"[A-Za-z0-9_]+", handle) else ""

    rows = postseason.read_season().to_dict("records")
    cut_lines = {}
    if "Playoff" in initial and any(
        row["Year"] == year and row["Week"] == str(week)
        and row["Round"] == "Playoff" and row["Status"] == "Pending" for row in rows
    ):
        cut_lines["Playoff"] = playoff_cut_line(year)
    initial_posts = list(matchup_posts(
        rows, year, str(week), league_ids, handle_for, {}, events=initial, cut_lines=cut_lines,
    ))
    posts = [] if args.review or args.approve else list(matchup_posts(
        rows, year, str(week), league_ids, handle_for, {}, events=EVENTS.keys() - initial,
    ))
    approval_key = f"{year}/{week}"
    hold_changed = False
    if initial_posts and (not publish or any(key not in records for key, _, _ in initial_posts)):
        approvals = json.loads(APPROVALS.read_text(encoding="utf-8")) if APPROVALS.exists() else {}
        if publish and approval_key not in approvals:
            print(f"{approval_key}: waiting for opening matchup approval. Opening posts held.")
        else:
            review_rows = [row for row in rows if row["Week"] != str(week) or row["Round"] in initial]
            code = review_code(review_rows, year, week, league_ids, initial_posts)
            if args.approve:
                if args.approve.strip() != code:
                    raise SystemExit("This approval code does not match the current slate and scores.")
                if approvals.get(approval_key) == code:
                    print(f"{approval_key} is already approved.")
                    return
                approvals[approval_key] = code
                try:
                    save_state(approvals, f"Approve Sleeper matchups for {approval_key}", APPROVALS)
                except subprocess.CalledProcessError:
                    raise SystemExit("Could not save approval to main. No posts were sent.") from None
                print(f"Approved {approval_key} for the Wednesday run.")
                return
            if args.review:
                post_private_review(year, week, code, initial_posts, league_names)
                return
            if publish and approvals[approval_key] != code:
                hold_changed = True
            else:
                print(f"Review code: {code}")
                posts.extend(initial_posts)
    elif args.approve:
        raise SystemExit("There is no opening slate to approve.")

    failures = 0
    count = 0
    for key, league_id, caption in posts:
        if publish and key in records:
            continue
        count += 1
        print(f"{key}\n{caption}\n", flush=True)
        if not publish:
            continue
        records[key] = {"status": "pending", "caption": caption}
        try:
            save_state(records, f"Reserve Sleeper matchup post {key}")
        except subprocess.CalledProcessError:
            raise SystemExit("Could not save the matchup reservation. Further sends stopped.") from None
        try:
            message_id = send_post(key, league_id, caption, token)
        except (OSError, ValueError) as error:
            print(f"{key}: {type(error).__name__}. Check league chat before retrying.")
            failures += 1
            continue
        records[key].update(status="sent", message_id=message_id)
        try:
            save_state(records, f"Confirm Sleeper matchup post {key}")
        except subprocess.CalledProcessError:
            raise SystemExit("Could not save the Sleeper confirmation. Further sends stopped.") from None
    print(f"{count} eligible postseason matchup posts.")
    if hold_changed:
        post_private_review(year, week, code, initial_posts, league_names)
        raise SystemExit("Pairings or scoring inputs changed after approval. Opening sends held.")
    if failures:
        raise SystemExit("One or more matchup deliveries need review.")


if __name__ == "__main__":
    main()
