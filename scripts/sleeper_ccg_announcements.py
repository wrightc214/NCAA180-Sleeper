"""Preview and post the Trophy Room's final CCG awards to Sleeper."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import uuid

import trophies

LEAGUE_DATA = "https://api.sleeper.app/v1/league"
TEST_LEAGUE = "1432137859359313920"
POSTS = Path("data/SleeperTrophyPosts.json")


def public_json(url):
    return json.loads(subprocess.check_output([
        "curl", "--fail", "--silent", "--show-error", "--max-time", "20", url,
    ]))


def previews(year, selected, out, *, ledger_path, already_recorded=()):
    expected = {
        trophies.short_names().get(name, name): league_id
        for (season, name), league_id in trophies.league_ids().items()
        if season == year
    }
    if selected and selected not in expected:
        raise SystemExit("Use the official conference short name for this season.")
    with open(ledger_path, encoding="utf-8-sig", newline="") as ledger:
        rows = list(csv.DictReader(ledger))
    out.mkdir(parents=True, exist_ok=True)
    posts = []
    for conference, league_id in sorted(expected.items()):
        if selected and conference != selected:
            continue
        if f"{year}/CCG/{league_id}" in already_recorded:
            continue
        matches = [
            row for row in rows
            if row["Season"] == year and row["EventType"] == "CCG"
            and row["Status"] == "Final" and row["LeagueID"] == league_id
        ]
        if len(matches) != 1:
            print(f"{conference}: waiting for one final winner.")
            continue
        row = matches[0]
        manager_id = row["ManagerUserID"]
        if (row["Conference"] != conference or not row["RosterID"].isdigit()
                or not manager_id.isdigit() or not league_id.isdigit() or league_id == TEST_LEAGUE):
            print(f"{conference}: incomplete or inconsistent award record.")
            continue
        art = trophies.art_key(row)
        if not art or trophies.resolved_art(row) != art:
            print(f"{conference}: unique trophy artwork unavailable.")
            continue

        members = public_json(f"{LEAGUE_DATA}/{league_id}/users")
        member = next((user for user in members if str(user.get("user_id")) == manager_id), None)
        if not member:
            print(f"{conference}: winner's Sleeper account is no longer in the league.")
            continue
        account = public_json(f"https://api.sleeper.app/v1/user/{manager_id}")
        username = account.get("username", "") if isinstance(account, dict) else ""
        if (not re.fullmatch(r"[A-Za-z0-9_]+", username or "")
                or str(account.get("user_id")) != manager_id):
            print(f"{conference}: winner's username could not be verified.")
            continue

        image = out / f"{league_id}.png"
        trophies.engrave_png(row).save(image)
        caption = (f"Congrats {row['Team']} & @{username} for winning the "
                   f"{year} {conference} conference championship game!")
        posts.append((league_id, image, caption))
        print(f"{conference} | {row['Team']} | {league_id} | {image.name} | {caption}")
    return posts


def send(year, league_id, image, caption, *, token, intended_league=None, before_post=None):
    if not token:
        raise SystemExit("The SLEEPER_SESSION_TOKEN Actions secret is missing.")

    try:
        uploaded = json.loads(subprocess.check_output([
            "curl", "--fail", "--silent", "--show-error", "--max-time", "25",
            "--form", f"file=@{image};type=image/png", "https://api.sleeper.app/upload",
        ]))
    except (subprocess.CalledProcessError, ValueError):
        raise SystemExit("Sleeper image upload failed before the chat post.") from None
    urls = [uploaded["url"], uploaded["url_original"]]
    for url in urls:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "sleepercdn.com"
                or not parsed.path.startswith("/uploads/") or parsed.query or parsed.fragment):
            raise SystemExit("Sleeper returned an unexpected image URL.")
    size = [str(int(uploaded[field])) for field in ("width", "height")]
    if any(int(dimension) < 1 for dimension in size):
        raise SystemExit("Sleeper returned invalid image dimensions.")

    query = """
      mutation create_message($parentId: String!, $clientId: String, $text: String,
        $keys: [String], $values: [String]) {
        create_message(parent_type: "league", parent_id: $parentId, client_id: $clientId,
          text: $text, attachment_type: "photo", k_attachment_data: $keys, v_attachment_data: $values) {
          message_id parent_id attachment
        }
      }
    """
    body = {
        "operationName": "create_message",
        "query": query,
        "variables": {
            "parentId": league_id,
            "clientId": str(uuid.uuid5(uuid.NAMESPACE_URL, f"ncaa180.ccg/{year}/{league_id}/{intended_league or league_id}")),
            "text": caption,
            "keys": ["url", "url_original", "width", "height", "pre_optimized"],
            "values": [*urls, *size, "true"],
        },
    }
    # Keep the session credential out of process arguments and workflow logs.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            return None

    request = urllib.request.Request(
        "https://sleeper.app/graphql",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "X-Sleeper-GraphQL-Op": "create_message",
        },
    )
    if before_post:
        before_post()
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(f"Sleeper returned HTTP {error.code}. Check chat before rerunning.") from None
    except (OSError, ValueError):
        raise SystemExit("Delivery could not be confirmed. Check chat before rerunning.") from None
    posted = (payload.get("data") or {}).get("create_message") or {}
    if (not posted.get("message_id") or str(posted.get("parent_id")) != league_id
            or not posted.get("attachment")):
        raise SystemExit("Sleeper did not confirm the trophy post. Check chat before rerunning.")
    print(f"Sleeper confirmed photo message {posted['message_id']} in league {league_id}.")
    return str(posted['message_id'])


def save_post_state(records, message):
    POSTS.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(POSTS)], check=True)
    subprocess.run([
        "git", "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit", "--only", "-m", message, "--", str(POSTS),
    ], check=True)
    subprocess.run(["git", "push", "origin", "HEAD:refs/heads/main"], check=True)


def publish_final_ccgs(year, conference, out, token):
    if not token:
        raise SystemExit("The SLEEPER_SESSION_TOKEN Actions secret is missing.")
    records = json.loads(POSTS.read_text(encoding="utf-8")) if POSTS.exists() else {}
    unresolved = [key for key, record in records.items()
                  if key.startswith(f"{year}/CCG/") and record["status"] == "pending"]
    for key in unresolved:
        print(f"{key}: prior delivery needs reconciliation. Skipping automatic resend.")
    posts = previews(year, conference, out, ledger_path=trophies.SEASON, already_recorded=records)
    failed = False
    for league_id, image, caption in posts:
        key = f"{year}/CCG/{league_id}"

        def reserve():
            records[key] = {"status": "pending", "caption": caption}
            save_post_state(records, f"Reserve Sleeper trophy post {key}")

        try:
            message_id = send(year, league_id, image, caption, token=token, before_post=reserve)
        except SystemExit as error:
            # Before reservation, an upload failure leaves the award eligible for a retry.
            # After reservation, further sends require someone to check the league chat.
            print(f"{key}: {error}")
            failed = True
            continue

        records[key].update(status="sent", message_id=message_id)
        save_post_state(records, f"Confirm Sleeper trophy post {key}")
    if failed:
        raise SystemExit("One or more Sleeper CCG notifications need review.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year")
    parser.add_argument("--conference", default="")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--replay-2025", action="store_true")
    parser.add_argument("--publish-scheduled", action="store_true")
    args = parser.parse_args()
    token = os.environ.pop("SLEEPER_SESSION_TOKEN", None)
    if args.publish_scheduled:
        if args.year or args.conference or args.send or args.replay_2025:
            parser.error("scheduled publishing uses the current season and final CCG ledger")
        import league_config
        import week_gate

        year, week, _ = week_gate.state()
        if week <= int(league_config.cfg()["schedule"]["ccg_week"]):
            print("CCG week has not finished.")
            return
        publish_final_ccgs(year, "", args.out, token)
        return

    if not re.fullmatch(r"[0-9]{4}", args.year or ""):
        parser.error("use a four-digit season")
    if args.replay_2025 and (args.year != "2025" or args.send or args.conference):
        parser.error("replay requires season 2025 and is independent of live send")
    if args.send and not args.conference:
        parser.error("select exactly one conference to send")
    if args.send:
        publish_final_ccgs(args.year, args.conference, args.out, token)
        return
    ledger = trophies.HIST if args.replay_2025 else trophies.SEASON
    posts = previews(args.year, args.conference, args.out, ledger_path=ledger)
    if args.replay_2025:
        if len(posts) != 15 or len({post[0] for post in posts}) != 15:
            raise SystemExit("Replay requires 15 verified awards. No test posts were sent.")
        for intended_league, image, caption in posts:
            print(f"Replaying award for league {intended_league} into test league {TEST_LEAGUE}.", flush=True)
            send(args.year, TEST_LEAGUE, image, caption, token=token, intended_league=intended_league)


if __name__ == "__main__":
    main()
