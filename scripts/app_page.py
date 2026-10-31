"""
app_page.py -- reports/app.html: the app's setup / notification settings page (todo-pwa.md).

Static page; everything happens in the browser:
  - iPhone in Safari (not installed): install steps first, notifications disabled until installed
  - pick teams (by league), leagues, events -> "Turn on notifications" (the tap iOS requires)
  - saves follows to the push store (Cloudflare Worker, config/push.json -> worker_url)
  - "Stop notifications": unsubscribes this phone and deletes it from the store
  - ?test=1 marks this phone as a tester (test pushes go only to testers); ?test=0 clears it
Lists come from reports/data/push-teams.json (scripts/push_teams.py); live settings (Worker URL,
public key) from config/push.json. CWD = repo root.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import nav_html, page_head  # noqa: E402

OUT = "reports/app.html"

CSS = """
.app{max-width:720px;margin:0 auto;padding:20px 16px 60px;display:grid;gap:16px}
.app h1{font-family:var(--disp);font-size:34px;margin:0}
.app .lede{color:var(--mute);margin:0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h2{font-family:var(--disp);font-size:22px;margin:0 0 8px;letter-spacing:.02em}
.card .hint{color:var(--mute);font-size:14px;margin:0 0 10px}
.status{font-weight:600}
.status.ok{color:var(--up)} .status.warn{color:var(--dn)}
.tester{display:inline-block;background:var(--gold);color:#000;border-radius:6px;padding:2px 8px;font-size:13px;font-weight:700}
.search{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;font:inherit;background:var(--bg);color:var(--ink)}
details{border-top:1px solid var(--line)} details:first-of-type{border-top:0}
summary{cursor:pointer;padding:10px 0;font-weight:700;list-style-position:inside}
summary .n{color:var(--mute);font-weight:400}
.picks{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:4px 12px;padding:0 0 10px}
.picks label{display:flex;gap:8px;align-items:center;padding:6px 0;min-height:32px}
.picks input{width:20px;height:20px;accent-color:var(--accent)}
.chosen{color:var(--mute);font-size:14px;margin-top:6px}
.actions{display:grid;gap:10px}
.btn{display:block;width:100%;border:0;border-radius:10px;padding:14px;font:inherit;font-weight:700;cursor:pointer;text-align:center}
.btn.primary{background:var(--accent);color:#fff}
.btn.secondary{background:transparent;color:var(--ink);border:1px solid var(--line)}
.btn[disabled]{opacity:.5;cursor:not-allowed}
.steps{margin:0;padding-left:20px} .steps li{margin:6px 0}
[hidden]{display:none!important}
"""

BODY = """
<nav class="weeks" aria-label="Pages">{nav}</nav>
<main class="app">
  <div>
    <h1>NCAA 180 app</h1>
    <p class="lede">Get a notification when your teams' games are final. No account, no login.
    <span class="tester" id="tester" hidden>Tester phone</span></p>
  </div>

  <section class="card" id="install" hidden>
    <h2>First: add this app to your Home Screen</h2>
    <p class="hint">On iPhone, notifications only work once the app is on your Home Screen.</p>
    <ol class="steps">
      <li>In Safari, tap the <b>Share</b> button.</li>
      <li>Choose <b>Add to Home Screen</b>, then <b>Add</b>.</li>
      <li>Open <b>NCAA 180</b> from your Home Screen and come back to this page.</li>
    </ol>
  </section>

  <section class="card">
    <h2>Status</h2>
    <p class="status" id="status">Checking&hellip;</p>
  </section>

  <section class="card">
    <h2>1. Teams</h2>
    <p class="hint">Following a team covers every game it plays: conference championship, playoff, bowl or NIT &mdash; every season.</p>
    <input class="search" id="q" type="search" placeholder="Find a team" aria-label="Find a team">
    <div id="teams"></div>
    <p class="chosen" id="teams-chosen"></p>
  </section>

  <section class="card">
    <h2>2. Leagues</h2>
    <p class="hint">Every postseason game with a team from these leagues.</p>
    <div class="picks" id="leagues"></div>
  </section>

  <section class="card">
    <h2>3. Events</h2>
    <p class="hint">Everything in these, whoever is playing.</p>
    <div class="picks" id="events"></div>
  </section>

  <section class="actions">
    <button class="btn primary" id="save" type="button">Turn on notifications</button>
    <button class="btn secondary" id="stop" type="button" hidden>Stop notifications</button>
  </section>
</main>
<script>
(function () {
  "use strict";
  var KEY = "ncaa180.push";
  var $ = function (id) { return document.getElementById(id); };
  var state = load();
  var conf = null, lists = null;

  var q = new URLSearchParams(location.search);
  if (q.get("test") === "1") { state.test = true; save(); }
  if (q.get("test") === "0") { state.test = false; save(); }
  $("tester").hidden = !state.test;

  function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  function status(text, cls) { var s = $("status"); s.textContent = text; s.className = "status " + (cls || ""); }

  var ua = navigator.userAgent;
  var iOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var installed = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  var pushOK = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
  if (iOS && !installed) $("install").hidden = false;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }

  function box(kind, key, label, checked) {
    return '<label><input type="checkbox" data-kind="' + kind + '" value="' + esc(key) + '"' + (checked ? " checked" : "") + "> " + esc(label) + "</label>";
  }

  function chosen(kind, key) {
    return (state.follows || []).some(function (f) { return f.kind === kind && f.key === key; });
  }

  function render() {
    var first = !state.follows;  // first visit: event defaults on
    $("teams").innerHTML = lists.leagues.map(function (lg) {
      var n = lg.teams.filter(function (t) { return chosen("team", t.key); }).length;
      return '<details data-league="' + esc(lg.name) + '"' + (n ? " open" : "") + "><summary>" + esc(lg.name) +
        ' <span class="n">' + (n ? "(" + n + " followed)" : "") + '</span></summary><div class="picks">' +
        lg.teams.map(function (t) { return box("team", t.key, t.name, chosen("team", t.key)); }).join("") + "</div></details>";
    }).join("");
    $("leagues").innerHTML = lists.leagues.map(function (lg) { return box("league", lg.key, lg.name, chosen("league", lg.key)); }).join("");
    $("events").innerHTML = lists.events.map(function (e) { return box("event", e.key, e.label, first ? e.default : chosen("event", e.key)); }).join("");
    count();
  }

  function picked() {
    return Array.prototype.map.call(document.querySelectorAll("input[type=checkbox]:checked"), function (i) {
      return { kind: i.dataset.kind, key: i.value };
    });
  }

  function count() {
    var t = picked().filter(function (f) { return f.kind === "team"; });
    $("teams-chosen").textContent = t.length ? t.length + " team" + (t.length > 1 ? "s" : "") + " followed" : "No teams yet.";
  }

  document.addEventListener("change", function (e) { if (e.target.matches("input[type=checkbox]")) count(); });
  $("q").addEventListener("input", function () {
    var v = this.value.trim().toLowerCase();
    document.querySelectorAll("#teams details").forEach(function (d) {
      var any = false;
      d.querySelectorAll("label").forEach(function (l) {
        var hit = !v || l.textContent.toLowerCase().indexOf(v) >= 0 || d.dataset.league.toLowerCase().indexOf(v) >= 0;
        l.hidden = !hit; any = any || hit;
      });
      d.hidden = !any; if (v && any) d.open = true;
    });
  });

  function b64ToBytes(b64) {
    var pad = "=".repeat((4 - b64.length % 4) % 4);
    var raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    var out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  async function registration() {
    return navigator.serviceWorker.register("sw.js", { scope: "./" }).then(function () { return navigator.serviceWorker.ready; });
  }

  function refreshStatus() {
    $("stop").hidden = !state.on;
    if (!conf.worker_url) { status("Notifications are coming soon. Your picks are saved on this phone.", "warn"); return; }
    if (iOS && !installed) { status("Add the app to your Home Screen first (steps above).", "warn"); $("save").disabled = true; return; }
    if (!pushOK) { status("This browser can't receive notifications. Your picks are saved on this phone.", "warn"); return; }
    if (Notification.permission === "denied") { status("Notifications are blocked for this site in your phone's settings.", "warn"); return; }
    if (state.on && Notification.permission === "granted") {
      status("Notifications are on." + (state.test ? " (tester)" : ""), "ok");
      $("save").textContent = "Save changes";
    } else {
      status("Notifications are off.", "");
      $("save").textContent = "Turn on notifications";
    }
  }

  $("save").addEventListener("click", async function () {
    var follows = picked();
    if (follows.length > (lists.max_follows || 60)) { status("Too many picks (max " + lists.max_follows + ").", "warn"); return; }
    state.follows = follows; save();
    if (!conf.worker_url || !pushOK || (iOS && !installed)) { refreshStatus(); return; }
    this.disabled = true;
    try {
      var perm = await Notification.requestPermission();   // must run inside this tap (iOS)
      if (perm !== "granted") { state.on = false; save(); refreshStatus(); return; }
      var reg = await registration();
      var sub = await reg.pushManager.getSubscription() ||
        await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(conf.vapid_public_key) });
      var r = await fetch(conf.worker_url + "/subscribe", {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ subscription: sub.toJSON(), follows: follows, test: !!state.test })
      });
      if (!r.ok) throw new Error((await r.json().catch(function () { return {}; })).error || r.status);
      state.on = true; save(); refreshStatus();
      status((follows.length ? "Saved. " : "Saved with nothing followed — pick a team to get notifications. ") +
             "Notifications are on." + (state.test ? " (tester)" : ""), follows.length ? "ok" : "warn");
    } catch (err) {
      status("Couldn't save: " + err.message + ". Try again in a minute.", "warn");
    } finally { this.disabled = false; }
  });

  $("stop").addEventListener("click", async function () {
    this.disabled = true;
    try {
      var reg = await navigator.serviceWorker.getRegistration();
      var sub = reg && await reg.pushManager.getSubscription();
      if (sub) {
        if (conf.worker_url) await fetch(conf.worker_url + "/unsubscribe", {
          method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ endpoint: sub.endpoint })
        }).catch(function () {});
        await sub.unsubscribe();
      }
      state.on = false; save(); refreshStatus();
      status("Notifications are off. Your picks are still saved on this phone.", "");
    } catch (err) {
      status("Couldn't stop: " + err.message, "warn");
    } finally { this.disabled = false; }
  });

  Promise.all([
    fetch("../config/push.json", { cache: "no-cache" }).then(function (r) { return r.json(); }),
    fetch("data/push-teams.json", { cache: "no-cache" }).then(function (r) { return r.json(); })
  ]).then(function (res) {
    conf = res[0]; lists = res[1];
    render(); refreshStatus();
  }).catch(function () { status("Couldn't load the team list. Check your connection and reload.", "warn"); });
})();
</script>
"""


def main():
    page = page_head("NCAA 180 app: notifications", extra_css=CSS) + BODY.replace("{nav}", nav_html("app")) + "</body></html>\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if old != page:
        open(OUT, "w", encoding="utf-8").write(page)
        print(f"wrote {OUT}")
    else:
        print(f"{OUT} unchanged")


if __name__ == "__main__":
    main()
