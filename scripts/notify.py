"""
notify.py -- one announcement layer for Discord + web push (imported, not run). CWD = repo root.

announce(ann) sends one announcement to every channel it belongs on:
  - web push: every device whose follows match (todo-pwa.md). One push per device per
    announcement, personalized: the device's followed teams first, then the rest by prestige.
  - Discord league channel: only events listed in config/push.json -> discord_events.
Audience "lm" never goes to push or the league channel (push is anonymous: anyone can follow
anything, so nothing private may reach it).

Announcement (plain dict):
  id        unique per season, e.g. "2026-CCG-w12" (the ledger stops repeats)
  event     key from config/push.json -> events, or "results" for a week's results push (its
            items carry their own "event": ccg_results / playoff_results / bowl_results / nit_results)
  title     push title, e.g. "Conference championships are final"
  url       page the push opens (relative to reports/, e.g. "matchups.html")
  summary   one line for devices that matched only through the event toggle
  items     list of {"text", "tier", "order", "event", "slots": ["Big Sky:6", ...], "leagues": ["Big Sky"]}
  champion  True for national champion / Stagg Bowl (also goes to every team follower)
  also_events  more event keys that also receive it (the title game = champion + round results)
  audience  "public" (default) or "lm"
  test      True = tester devices only

Devices come from the Cloudflare Worker (worker/): {"id", "endpoint", "p256dh", "auth",
"is_test", "follows": [{"kind": "team"|"league"|"event", "key": "ncaa180|Big Sky:6"}]}.
Stored keys carry the super-league prefix (config/push.json -> group); everything below works on
the unprefixed key ("Big Sky:6", "Big Sky", "champions").

Environment (set by the workflow; missing = that channel is skipped, nothing fails):
  PUSH_ADMIN_TOKEN        Worker admin token (secret)
  VAPID_PRIVATE_KEY       push signing key, base64url raw (secret)
  DISCORD_WEBHOOK_TEAM_STATS  league channel (only for discord_events)
"""
import csv
import datetime as dt
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "push.json"
LEDGER = ROOT / "data" / "push" / "Announced_Season.csv"
LEDGER_COLS = ["Year", "AnnouncementID", "Event", "SentAt", "Devices", "Test"]
SHORTNAMES = ROOT / "data" / "LeagueShortNames.csv"
MAX_LINES = 4  # lines in a push body before "+N more"


def cfg():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


# ---------- keys: team follow = league short name + roster ID (identity = slot) ----------

def league_short_map():
    """{full Sleeper league name: short name}. Sleeper's LeagueID changes every season, so
    follows key on the short name, which doesn't."""
    with open(SHORTNAMES, encoding="utf-8-sig") as f:
        return {r["Full Name"].strip(): r["Short Name"].strip() for r in csv.DictReader(f)}


def slot_key(league_short, roster_id):
    return f"{league_short}:{int(float(roster_id))}"


# ---------- matching + text (pure; tests/test_notify.py) ----------

def _follows(device, group=None):
    """This super league's follows only, with the '<group>|' prefix removed (a phone can follow
    teams in several super leagues; each pipeline sees just its own)."""
    group = group or _group()
    pre = group + "|"
    out = {"team": set(), "league": set(), "event": set()}
    for f in device.get("follows", []):
        key = str(f.get("key", ""))
        if f.get("kind") in out and key.startswith(pre):
            out[f["kind"]].add(key[len(pre):])
    return out


def _group():
    return cfg().get("group", "ncaa180")


def matches(device, ann, conf=None):
    """Does this device get this announcement? Yes if it follows a team or league in it, has
    one of its event toggles on (the announcement's or any item's), or -- for champions --
    follows at least one team."""
    conf = conf or cfg()
    if ann.get("audience", "public") != "public":
        return False
    if ann.get("test") and not device.get("is_test"):
        return False
    if ann.get("everyone"):  # plain test push: every (tester) device
        return True
    return bool(visible_items(device, ann)) or _whole(device, ann) or (
        ann.get("champion") and conf.get("champions_to_team_followers", True) and bool(_follows(device)["team"]))


def _whole(device, ann):
    """Device follows the announcement's own event (or an also_event): it sees every item."""
    return bool(({ann.get("event")} | set(ann.get("also_events", []))) & _follows(device)["event"])


def visible_items(device, ann):
    """Items this device sees: its teams' and leagues' games, plus every item whose event it follows
    (all items when it follows the announcement's own event)."""
    f = _follows(device)
    if _whole(device, ann):
        return list(ann.get("items", []))
    return [it for it in ann.get("items", []) if _mine(it, f) or it.get("event") in f["event"]]


def _mine(item, f):
    return bool(set(item.get("slots", [])) & f["team"]) or bool(set(item.get("leagues", [])) & f["league"])


def _prestige(item, conf):
    order = conf.get("prestige", [])
    t = item.get("tier", "")
    return (order.index(t) if t in order else len(order), item.get("order", 0))


def body_for(device, ann, conf=None):
    """Push text for one device: its followed teams' games first, then its followed leagues',
    then the rest it follows by prestige (playoff, bowl, NIT). At most MAX_LINES lines, then
    '+N more'. A champion push to a team follower who follows nothing in it shows the game."""
    conf = conf or cfg()
    f = _follows(device)
    items = visible_items(device, ann) or list(ann.get("items", []))
    own = [it for it in items if set(it.get("slots", [])) & f["team"]]
    league = [it for it in items if it not in own and set(it.get("leagues", [])) & f["league"]]
    rest = [it for it in items if it not in own and it not in league]
    key = lambda i: _prestige(i, conf)  # noqa: E731
    lines = [it["text"] for it in sorted(own, key=key) + sorted(league, key=key) + sorted(rest, key=key)]
    if not own and not league and ann.get("summary"):
        lines = [ann["summary"]] + lines
    if not lines:
        return ann.get("summary", "")
    if len(lines) > MAX_LINES:
        more = len(lines) - (MAX_LINES - 1)
        lines = lines[:MAX_LINES - 1] + [f"+{more} more"]
    return "\n".join(lines)


def payload_for(device, ann, conf=None):
    return {"title": ann["title"], "body": body_for(device, ann, conf),
            "url": ann.get("url", "index.html"), "tag": ann["id"]}


# ---------- ledger (no repeats) ----------

def _ledger_rows():
    if not LEDGER.exists():
        return []
    with open(LEDGER, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def already_sent(ann_id):
    return any(r["AnnouncementID"] == ann_id and r.get("Test", "") != "True" for r in _ledger_rows())


def record(year, ann, n_devices):
    rows = _ledger_rows()
    rows.append({"Year": year, "AnnouncementID": ann["id"], "Event": ann.get("event", ""),
                 "SentAt": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "Devices": n_devices, "Test": str(bool(ann.get("test")))})
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLS)
        w.writeheader()
        w.writerows(rows)


# ---------- I/O: Worker, web push, Discord ----------

def _worker(path, method="GET", body=None):
    import requests
    url = cfg().get("worker_url", "").rstrip("/") + path
    r = requests.request(method, url, json=body, timeout=30,
                         headers={"Authorization": "Bearer " + os.environ["PUSH_ADMIN_TOKEN"]})
    r.raise_for_status()
    return r.json()


def push_ready():
    """Push is configured: Worker URL in config + both secrets present."""
    return bool(cfg().get("worker_url")) and bool(os.environ.get("PUSH_ADMIN_TOKEN")) \
        and bool(os.environ.get("VAPID_PRIVATE_KEY"))


def fetch_devices():
    return _worker("/admin/devices")["devices"]


def _send_one(device, payload):
    """True = delivered; False = device is gone (prune it); raises on other errors."""
    from pywebpush import webpush, WebPushException
    try:
        webpush(subscription_info={"endpoint": device["endpoint"],
                                   "keys": {"p256dh": device["p256dh"], "auth": device["auth"]}},
                data=json.dumps(payload),
                vapid_private_key=os.environ["VAPID_PRIVATE_KEY"],
                vapid_claims={"sub": cfg()["vapid_subject"]},
                ttl=24 * 3600)
        return True
    except WebPushException as e:
        code = getattr(e.response, "status_code", None)
        if code in (404, 410):
            return False
        raise


def send_push(ann):
    """Send to matching devices. Returns (sent, pruned, failed)."""
    conf = cfg()
    devices = fetch_devices()
    sent, gone, failed = 0, [], 0
    for d in devices:
        if not matches(d, ann, conf):
            continue
        try:
            if _send_one(d, payload_for(d, ann, conf)):
                sent += 1
            else:
                gone.append(d["id"])
        except Exception as e:  # one bad device never stops the rest
            failed += 1
            print(f"::warning::push to device {d.get('id', '?')[:8]} failed: {e}")
    if gone:
        _worker("/admin/prune", "POST", {"ids": gone})
    return sent, len(gone), failed


def send_discord(ann):
    import requests
    hook = os.environ.get("DISCORD_WEBHOOK_TEAM_STATS", "")
    if not hook:
        print("Discord webhook not set; skipped.")
        return False
    lines = [f"**{ann['title']}**"] + [it["text"] for it in sorted(ann.get("items", []),
                                                                  key=lambda i: _prestige(i, cfg()))]
    text = "\n".join(lines)[:1900]
    requests.post(hook, json={"content": text}, timeout=30).raise_for_status()
    return True


def announce(ann, year):
    """Send once (ledger-checked). Returns True if anything went out."""
    if not ann.get("test") and already_sent(ann["id"]):
        print(f"{ann['id']}: already announced; skipped.")
        return False
    if ann.get("audience", "public") != "public":
        print(f"{ann['id']}: audience {ann.get('audience')} never goes to push or the league channel.")
        return False
    went = False
    if push_ready():
        sent, pruned, failed = send_push(ann)
        print(f"{ann['id']}: pushed to {sent} device(s); pruned {pruned}; failed {failed}.")
        went = True
        n = sent
    else:
        print(f"{ann['id']}: push not configured (worker_url / secrets); skipped push.")
        n = 0
    if not ann.get("test") and ann.get("event") in cfg().get("discord_events", []):
        went = send_discord(ann) or went
    if went:
        record(year, ann, n)
    return went
