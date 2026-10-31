// NCAA 180 app layer, loaded on every page (todo-pwa.md):
//  1. registers the service worker (offline + push)
//  2. first-run prompt (only once push is live): a full-screen "Set up NCAA 180" sheet on every open while this phone has no
//     follows or notifications are off. "Not now" hides it for this visit only; it never blocks the site.
// The setup itself lives on app.html.
(function () {
  "use strict";
  var KEY = "ncaa180.push";            // localStorage: {follows:[...], on:bool, test:bool}
  var SNOOZE = "ncaa180.push.snooze";  // sessionStorage: "Not now" for this visit
  var here = document.currentScript && document.currentScript.src || "";
  var base = here ? here.replace(/assets\/app\.js.*$/, "") : "";

  function store() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }

  if ("serviceWorker" in navigator && base) {
    navigator.serviceWorker.register(base + "sw.js", { scope: base }).catch(function () {});
  }

  function needsSetup() {
    var s = store();
    var hasFollows = Array.isArray(s.follows) && s.follows.length > 0;
    var granted = ("Notification" in window) && Notification.permission === "granted";
    return !(hasFollows && s.on && granted);
  }

  function showPrompt() {
    if (/\/app\.html$/.test(location.pathname)) return;     // already on setup
    try { if (sessionStorage.getItem(SNOOZE)) return; } catch (e) {}
    if (!needsSetup()) return;
    var d = document.createElement("div");
    d.className = "n180-setup";
    d.setAttribute("role", "dialog");
    d.setAttribute("aria-modal", "true");
    d.setAttribute("aria-labelledby", "n180-setup-h");
    d.innerHTML =
      '<div class="n180-card">' +
      '<img src="' + base + 'assets/icons/icon-192.png" alt="" width="64" height="64">' +
      '<h2 id="n180-setup-h">Get NCAA 180 notifications</h2>' +
      '<p>Pick your teams, leagues and events. You’ll get a notification when their games are final — no account, no login.</p>' +
      '<a class="n180-go" href="' + base + 'app.html">Set up</a>' +
      '<button type="button" class="n180-later">Not now</button>' +
      '</div>';
    var css = document.createElement("style");
    css.textContent =
      ".n180-setup{position:fixed;inset:0;z-index:9999;background:rgba(10,16,30,.72);display:grid;place-items:center;padding:20px}" +
      ".n180-card{background:var(--panel,#fff);color:var(--ink,#14213a);border-radius:14px;max-width:360px;width:100%;padding:24px;text-align:center;font-family:var(--body,system-ui,sans-serif)}" +
      ".n180-card h2{font-family:var(--disp,Impact,sans-serif);font-size:26px;margin:10px 0 6px;letter-spacing:.02em}" +
      ".n180-card p{margin:0 0 18px;color:var(--mute,#5d6a80)}" +
      ".n180-go{display:block;background:var(--accent,#c8102e);color:#fff;border-radius:10px;padding:12px;font-weight:700;text-decoration:none}" +
      ".n180-later{margin-top:10px;background:none;border:0;color:var(--mute,#5d6a80);font:inherit;padding:8px;cursor:pointer}";
    document.head.appendChild(css);
    document.body.appendChild(d);
    var later = d.querySelector(".n180-later");
    later.addEventListener("click", function () {
      try { sessionStorage.setItem(SNOOZE, "1"); } catch (e) {}
      d.remove();
    });
    later.focus();
  }

  // Settings button on every page (bottom-left; the back-to-top arrow is bottom-right), so people
  // can always get back to their notification settings.
  function bell() {
    if (/\/app\.html$/.test(location.pathname)) return;
    var a = document.createElement("a");
    a.href = base + "app.html";
    a.className = "n180-bell";
    a.setAttribute("aria-label", "Notification settings");
    a.title = "Notification settings";
    a.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg>';
    var css = document.createElement("style");
    css.textContent = ".n180-bell{position:fixed;left:16px;bottom:16px;z-index:50;width:44px;height:44px;border-radius:50%;" +
      "display:grid;place-items:center;background:var(--panel,#fff);color:var(--ink,#14213a);border:1px solid var(--line,#d5dbe5);" +
      "box-shadow:0 2px 8px rgba(0,0,0,.18)}@media print{.n180-bell{display:none}}";
    document.head.appendChild(css);
    document.body.appendChild(a);
  }

  // Only prompt once push is live (config/push.json -> worker_url set), so members never see a
  // "set up notifications" sheet that leads to "coming soon".
  function start() {
    if (!base) return;
    fetch(base + "../config/push.json", { cache: "no-cache" })
      .then(function (r) { return r.json(); })
      .then(function (c) { if (c && c.worker_url) { bell(); showPrompt(); } })
      .catch(function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
