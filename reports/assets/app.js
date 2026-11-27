// NCAA 180 app layer, loaded on every page (todo-pwa.md):
//  1. registers the service worker (offline + push)
//  2. first-run prompt (installed app only, once push is live): a full-screen "Set up NCAA 180" sheet on every open while this phone has no
//     follows or notifications are off. "Not now" hides it for this visit only; it never blocks the site.
// The setup itself lives on app.html.
(function () {
  "use strict";
  var KEY = "ncaa180.push";            // localStorage: {follows:[...], on:bool, test:bool}
  var SNOOZE = "ncaa180.push.snooze";  // sessionStorage: "Not now" for this visit
  var here = document.currentScript && document.currentScript.src || "";
  var base = here ? here.replace(/assets\/app\.js.*$/, "") : "";

  function store() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
  // Existing follows (CW, 2026-11-14): a device that follows teams but has no My team gets its first
  // followed team as My team (follows keep list order, so this is the first one ticked on app.html).
  // Flagged myTeamAuto so the notifications page can ask them to confirm it.
  (function () {
    var s = store(); if (s.myTeam) return;
    var t = (s.follows || []).filter(function (f) { return f && f.kind === "team"; })[0];
    if (!t) return;
    s.myTeam = t.key; s.myTeamAuto = true;
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
  })();
  // My team (CW, 2026-11-14): the team this device's manager runs, picked on app.html. Any page can
  // use it for team-specific visuals: NCAA180.myTeam() -> {key, conf, roster} or null.
  window.NCAA180 = window.NCAA180 || {};
  window.NCAA180.myTeam = function () {
    var k = store().myTeam; if (!k) return null;
    var t = String(k).split("|").slice(1).join("|"), i = t.lastIndexOf(":");
    return i < 0 ? null : { key: k, conf: t.slice(0, i), roster: t.slice(i + 1) };
  };

  if ("serviceWorker" in navigator && base) {
    navigator.serviceWorker.register(base + "sw.js", { scope: base }).catch(function () {});
  }

  function needsSetup() {
    var s = store();
    var hasFollows = Array.isArray(s.follows) && s.follows.length > 0;
    var granted = ("Notification" in window) && Notification.permission === "granted";
    return !(hasFollows && s.on && granted);
  }

  function installed() {
    return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  }

  function showPrompt() {
    if (!installed()) return;  // CW, 2026-10-31: the full-screen prompt is for the installed app only; browsers use the bell
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
      '<img src="' + base + '../assets/app/icon-192.png" alt="" width="64" height="64">' +
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

  // Tester flag (todo-about-page.md §6): the About page's dev panel switches it here; the notifications
  // page keeps its own title-tap trick. Same flag ({test} in KEY) either way. When this phone already has
  // notifications on, the change is saved to the push store right away (test pushes go only to testers).
  // Resolves to "saved" | "local" (saved on this phone only; notifications off) or rejects with the error.
  window.NCAA180.setTester = function (on) {
    var s = store(); s.test = !!on;
    try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
    if (!s.on || !base || !("serviceWorker" in navigator)) return Promise.resolve("local");
    return fetch(base + "../config/push.json", { cache: "no-cache" })
      .then(function (r) { return r.json(); })
      .then(function (c) {
        if (!c || !c.worker_url) return "local";
        return navigator.serviceWorker.getRegistration()
          .then(function (reg) { return reg && reg.pushManager.getSubscription(); })
          .then(function (sub) {
            if (!sub) return "local";
            return fetch(c.worker_url + "/subscribe", {
              method: "POST", headers: { "content-type": "application/json" },
              body: JSON.stringify({ subscription: sub.toJSON(), follows: s.follows || [], test: !!s.test })
            }).then(function (r) { if (!r.ok) throw new Error(r.status); return "saved"; });
          });
      });
  };
  window.NCAA180.tester = function () { return !!store().test; };

  // Only prompt once push is live (config/push.json -> worker_url set), so members never see a
  // "set up notifications" sheet that leads to "coming soon".
  function start() {
    if (window.parent !== window) return;  // embedded board (My team): no prompt
    if (!base) return;
    fetch(base + "../config/push.json", { cache: "no-cache" })
      .then(function (r) { return r.json(); })
      .then(function (c) { if (c && c.worker_url) showPrompt(); })
      .catch(function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
