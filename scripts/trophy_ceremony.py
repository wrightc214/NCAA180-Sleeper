"""Build Awards ceremonies from the published trophy ledger and dated results."""
import argparse
import hashlib
import html
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import league_config as lcfg
import trophies as tr
from site_common import SECTIONS_JS, awards_ceremony_state, menu_html, page_head

REPORTS = Path("reports")
MANIFEST = Path("trophy-ceremonies.json")
POSTED = Path("data/TrophyCeremonyPosts_Season.json")
SITE = "https://wrightc214.github.io/NCAA180-Sleeper/reports/"
START = "<!-- trophy-ceremony:start -->"
END = "<!-- trophy-ceremony:end -->"
IDENTITY = (*tr.KEY, "Team", "Conference")
CSS = """
.ceremony-shelf{display:flex;flex-wrap:wrap;justify-content:center}
.ceremony-card{box-sizing:border-box;width:25%;min-width:0;display:flex;flex-direction:column;
  justify-content:flex-end;align-items:center;padding:8px 0 0;text-align:center;color:var(--ink)}
.ceremony-card.featured{width:100%}
.ceremony-card .trophy{width:min(92%,180px)}
.ceremony-card.featured .trophy{width:min(75%,230px)}
.ceremony-card p{width:100%;box-sizing:border-box;border-top:2px solid var(--gold);
  padding:6px 5px 9px;margin:0;overflow-wrap:anywhere;font-size:14px}
.ceremony-card small{display:block}
#trophy-ceremony{background:var(--panel);color:var(--ink)}
@media(max-width:640px){.ceremony-card{width:50%}}
"""
e = html.escape


def identity(row):
    return tuple(str(row[k]) for k in IDENTITY)


def group_awards(ledger, dated):
    weeks = defaultdict(set)
    for row in dated:
        value = str(row.get("Week") or "")
        if value.isdigit() and 1 <= int(value) <= 18:
            weeks[identity(row)].add(int(value))
    groups = defaultdict(list)
    seen = set()
    for row in ledger:
        key = identity(row)
        if key in seen or not row["Team"]:
            continue
        found = weeks[key]
        week = next(iter(found)) if len(found) == 1 else None
        if week is None and row["EventType"] != "Bowl":
            continue
        seen.add(key)
        groups[int(row["Season"]), week].append(row)
    return groups


def sort_key(row, points):
    kind = row["EventType"]
    impact = points["PlayoffRound"].get(row["Round"], 0) if kind == "PlayoffRound" else points.get(kind, 0)
    return (kind != "NationalTitle", -impact, row["Event"].casefold(),
            row["Conference"].casefold(), row["Team"].casefold(), row["Round"].casefold())


def ceremony_labels(config, week, awards):
    display = config["postseason"]["display"]
    labels = display["awards_labels"]
    if week is None:
        return labels["year_end"], labels["year_end"]
    if any(row["EventType"] == "CCG" for row in awards):
        return labels["ccg"]["picker"], labels["ccg"]["heading"]
    if any(row["EventType"] == "NationalTitle" for row in awards) or week == config["schedule"]["postseason_end_week"]:
        return labels["championship"], labels["championship"]
    if week >= config["schedule"]["postseason_start_week"]:
        tiers = config["postseason"]["bowls"]["tiers"]
        tier = next((t["name"] for t in tiers if t["week"] == week), None)
        if tier:
            return tier, tier
    return lcfg.week_label(week), lcfg.week_label(week)


def section(title, year, awards, date_unknown=False):
    cards = []
    for row in awards:
        featured = " featured" if row["EventType"] == "NationalTitle" else ""
        status = "<small>Reconstructed</small>" if row["Status"] == "Reconstructed" else ""
        event, team = e(row["Event"]), e(row["Team"])
        cards.append(f'<article class="ceremony-card{featured}">{tr.trophy_html(row, lazy=False)}'
                     f'<p><strong>{team}</strong><small>{event}</small>{status}</p></article>')
    sub = (f'<h3>{e(lcfg.cfg()["postseason"]["display"]["awards_labels"]["unknown_bowls"])}</h3>'
           if date_unknown else "")
    return (f'<section id="trophy-ceremony"><h2>{e(title)} <small>{year}</small></h2>{sub}'
            f'<div class="ceremony-shelf">{"".join(cards)}</div></section>')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def build():
    current = tr.current_season()
    config = lcfg.cfg()
    dated = (tr.from_postseason_history() + tr.from_dwight_history()
             + tr.from_postseason_season(current) + tr.from_special_events(current))
    groups = group_awards(tr.ledger().to_dict("records"), dated)
    points = tr.trophy_display_points()
    manifest = []
    previous = load_json(REPORTS / MANIFEST, [])
    weekly = {}
    public = awards_ceremony_state() == "visible"
    for (year, week), rows in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1] or 99)):
        rows.sort(key=lambda row: sort_key(row, points))
        picker, heading = ceremony_labels(config, week, rows)
        key = f"{year}-{'year-end' if week is None else f'{week:02d}'}"
        href = f"ceremony-{key}.html"
        content = section(heading, year, rows, week is None)
        css = tr.CSS + CSS
        nav = menu_html("awards", ["awards-seasons", f"awards-weeks-{year}"])
        title = f"{heading} · {year} · {lcfg.brand()}"
        write(REPORTS / href, page_head(title, css) + f'<div class="wrap">{nav}{content}</div>'
              + SECTIONS_JS + "</body></html>\n")
        week_href = f"week-{year}-{week:02d}.html" if year != current and week else ""
        if year == current and week:
            week_href = f"week-{week:02d}.html"
        regular = bool(public and week and week <= config["schedule"]["last_regular_week"]
                       and (REPORTS / week_href).is_file())
        if regular:
            weekly[week_href] = section("Trophies", year, rows)
        digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        manifest.append(dict(year=year, week=week, label=picker, heading=heading, key=key,
                             href=href, inline=regular, digest=digest))
    for item in previous:
        if item["href"] not in {row["href"] for row in manifest} and re.fullmatch(r"ceremony-\d{4}-(?:\d{2}|year-end)\.html", item["href"]):
            (REPORTS / item["href"]).unlink(missing_ok=True)
    for path in [*REPORTS.glob("week-*.html"), REPORTS / "index.html"]:
        if not path.is_file() or (path.name not in weekly and not previous and path.name != "index.html"):
            continue
        original = path.read_text(encoding="utf-8")
        page = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", original, flags=re.S)
        name = path.name
        if name == "index.html":
            week_title = re.search(r"<title>[^<]* Week (\d+) Awards</title>", page)
            if week_title:
                name = f"week-{int(week_title[1]):02d}.html"
        if name in weekly:
            block = f"{START}<style>{tr.CSS + CSS}</style>{weekly[name]}{END}\n"
            page = page.replace("</header>\n", "</header>\n" + block, 1)
        if page != original:
            write(path, page)
    write(REPORTS / MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest


def pending_posts(manifest, ledger, year, destination):
    return [item for item in manifest if item["year"] == year and item["week"] is not None
            and (ledger.get(item["key"], {}).get("destination"), ledger.get(item["key"], {}).get("digest"))
            != (destination, item["digest"])]


def publish(check=False):
    if check and awards_ceremony_state() != "visible":
        print("pending=false")
        return
    webhook = os.environ.get("DISCORD_WEBHOOK_AWARDS") or os.environ.get("DISCORD_WEBHOOK_TEAM_STATS")
    if not webhook:
        if check:
            print("pending=false")
        print("Trophy ceremony Discord webhook unavailable; leaving announcements pending.")
        return
    if not re.fullmatch(r"https://(?:discord\.com|discordapp\.com)/api/webhooks/\d+/[\w-]+/?", webhook):
        raise ValueError("Expected a Discord webhook URL")
    webhook = webhook.rstrip("/")
    destination = webhook.split("/")[-2]
    ledger = load_json(POSTED, {})
    pending = pending_posts(load_json(REPORTS / MANIFEST, []), ledger, tr.current_season(), destination)
    if check:
        print(f"pending={'true' if pending else 'false'}")
        return
    if not pending:
        return

    import requests
    from playwright.sync_api import sync_playwright

    contact_id = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    mention = f"<@{contact_id}> " if re.fullmatch(r"[0-9]+", contact_id) else ""
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 620, "height": 900},
                                device_scale_factor=2, color_scheme="dark")
        for item in pending:
            page.goto((REPORTS / item["href"]).resolve().as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.add_style_tag(content=".snap-btn,.fold-bar{display:none!important}")
            png = page.locator("#trophy-ceremony").screenshot(animations="disabled")
            previous = ledger.get(item["key"], {})
            message = previous.get("id") if previous.get("destination") == destination else None
            payload = {"content": f'{mention}**{item["year"]} · {item["heading"]}**\n{SITE}{item["href"]}',
                       "allowed_mentions": {"parse": [], "users": [contact_id] if mention and not message else []},
                       "attachments": [{"id": 0, "filename": "trophy-ceremony.png"}]}
            files = {"files[0]": ("trophy-ceremony.png", png, "image/png")}
            try:
                response = (requests.patch(f"{webhook}/messages/{message}", data={"payload_json": json.dumps(payload)},
                                           files=files, timeout=30) if message else
                            requests.post(webhook, params={"wait": "true"}, data={"payload_json": json.dumps(payload)},
                                          files=files, timeout=30))
            except requests.RequestException:
                raise RuntimeError("Discord ceremony request failed") from None
            if not response.ok:
                raise RuntimeError(f"Discord ceremony request returned HTTP {response.status_code}")
            ledger[item["key"]] = {"destination": destination, "digest": item["digest"], "id": response.json()["id"]}
            write(POSTED, json.dumps(ledger, sort_keys=True, indent=2) + "\n")
            print(f'Posted ceremony {item["key"]}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-post", action="store_true")
    mode.add_argument("--post", action="store_true")
    args = parser.parse_args()
    if args.check_post or args.post:
        publish(check=args.check_post)
    else:
        print(f"Built {len(build())} trophy ceremony entries")
