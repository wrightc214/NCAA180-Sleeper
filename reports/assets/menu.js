// NCAA 180 site menu (todo-header-rebuild.md). GENERATED into reports/assets/menu.js by
// scripts/menu_build.py from config/nav.json + the pages in reports/. Edit this template or the
// config, never reports/assets/menu.js.
//
// Every page carries empty placeholders written once by site_common.menu_html():
//   <nav class="weeks" aria-label="Pages" data-current="standings"></nav>   main tabs
//   <nav class="weeks sub" data-row="standings-seasons"></nav>              optional sub-rows
//   <script src="assets/menu.js"></script>                                   this file (synchronous: no flash)
// Dev view (per device, localStorage "ncaa180.dev" = "1", switched on the About page's dev panel)
// shows hidden-dev tabs/items with a DEV tag and a "DEV — not public" bar on non-public pages.
(function () {
  "use strict";
  var D = {"tabs":[{"id":"awards","label":"Awards","href":"week-10.html"},{"id":"map","label":"Roster Map","href":"roster-map.html"},{"id":"standings","label":"Standings","href":"standings.html"},{"id":"scoreboard","label":"Games","href":"scoreboard.html"},{"id":"poll","label":"Poll","href":"poll.html","aliases":["poll-how","poll-bots"]},{"id":"postseason","label":"Postseason","href":"postseason.html"},{"id":"special","label":"Special Events","href":"special.html"},{"id":"managers","label":"Managers","href":"managers.html"},{"id":"records","label":"Records","href":"records.html"},{"id":"app","label":"Notification settings","href":"app.html","icon":"bell"}],"rows":{"awards-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2021","href":"week-2021-11.html","match":"^week-2021-\\d+\\.html$"},{"label":"2022","href":"week-2022-11.html","match":"^week-2022-\\d+\\.html$"},{"label":"2023","href":"week-2023-11.html","match":"^week-2023-\\d+\\.html$"},{"label":"2024","href":"week-2024-11.html","match":"^week-2024-\\d+\\.html$"},{"label":"2025","href":"week-2025-11.html","match":"^week-2025-\\d+\\.html$"},{"label":"2026","href":"week-10.html","match":"^week-\\d{2}\\.html$"}]},"awards-weeks-2021":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2021-01.html"},{"label":"Wk 2","href":"week-2021-02.html"},{"label":"Wk 3","href":"week-2021-03.html"},{"label":"Wk 4","href":"week-2021-04.html"},{"label":"Wk 5","href":"week-2021-05.html"},{"label":"Wk 6","href":"week-2021-06.html"},{"label":"Wk 7","href":"week-2021-07.html"},{"label":"Wk 8","href":"week-2021-08.html"},{"label":"Wk 9","href":"week-2021-09.html"},{"label":"Wk 10","href":"week-2021-10.html"},{"label":"Wk 11","href":"week-2021-11.html"}]},"awards-weeks-2022":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2022-01.html"},{"label":"Wk 2","href":"week-2022-02.html"},{"label":"Wk 3","href":"week-2022-03.html"},{"label":"Wk 4","href":"week-2022-04.html"},{"label":"Wk 5","href":"week-2022-05.html"},{"label":"Wk 6","href":"week-2022-06.html"},{"label":"Wk 7","href":"week-2022-07.html"},{"label":"Wk 8","href":"week-2022-08.html"},{"label":"Wk 9","href":"week-2022-09.html"},{"label":"Wk 10","href":"week-2022-10.html"},{"label":"Wk 11","href":"week-2022-11.html"}]},"awards-weeks-2023":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2023-01.html"},{"label":"Wk 2","href":"week-2023-02.html"},{"label":"Wk 3","href":"week-2023-03.html"},{"label":"Wk 4","href":"week-2023-04.html"},{"label":"Wk 5","href":"week-2023-05.html"},{"label":"Wk 6","href":"week-2023-06.html"},{"label":"Wk 7","href":"week-2023-07.html"},{"label":"Wk 8","href":"week-2023-08.html"},{"label":"Wk 9","href":"week-2023-09.html"},{"label":"Wk 10","href":"week-2023-10.html"},{"label":"Wk 11","href":"week-2023-11.html"}]},"awards-weeks-2024":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2024-01.html"},{"label":"Wk 2","href":"week-2024-02.html"},{"label":"Wk 3","href":"week-2024-03.html"},{"label":"Wk 4","href":"week-2024-04.html"},{"label":"Wk 5","href":"week-2024-05.html"},{"label":"Wk 6","href":"week-2024-06.html"},{"label":"Wk 7","href":"week-2024-07.html"},{"label":"Wk 8","href":"week-2024-08.html"},{"label":"Wk 9","href":"week-2024-09.html"},{"label":"Wk 10","href":"week-2024-10.html"},{"label":"Wk 11","href":"week-2024-11.html"}]},"awards-weeks-2025":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2025-01.html"},{"label":"Wk 2","href":"week-2025-02.html"},{"label":"Wk 3","href":"week-2025-03.html"},{"label":"Wk 4","href":"week-2025-04.html"},{"label":"Wk 5","href":"week-2025-05.html"},{"label":"Wk 6","href":"week-2025-06.html"},{"label":"Wk 7","href":"week-2025-07.html"},{"label":"Wk 8","href":"week-2025-08.html"},{"label":"Wk 9","href":"week-2025-09.html"},{"label":"Wk 10","href":"week-2025-10.html"},{"label":"Wk 11","href":"week-2025-11.html"}]},"awards-weeks-2026":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-01.html"},{"label":"Wk 2","href":"week-02.html"},{"label":"Wk 3","href":"week-03.html"},{"label":"Wk 4","href":"week-04.html"},{"label":"Wk 5","href":"week-05.html"},{"label":"Wk 6","href":"week-06.html"},{"label":"Wk 7","href":"week-07.html"},{"label":"Wk 8","href":"week-08.html"},{"label":"Wk 9","href":"week-09.html"},{"label":"Wk 10","href":"week-10.html"}]},"standings-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2021","href":"standings-2021.html"},{"label":"2022","href":"standings-2022.html"},{"label":"2023","href":"standings-2023.html"},{"label":"2024","href":"standings-2024.html"},{"label":"2025","href":"standings-2025.html"},{"label":"2026","href":"standings.html","match":"^standings(-2026)?\\.html$"}]},"postseason-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2019","href":"postseason-2019.html"},{"label":"2020","href":"postseason-2020.html"},{"label":"2021","href":"postseason-2021.html"},{"label":"2022","href":"postseason-2022.html"},{"label":"2023","href":"postseason-2023.html"},{"label":"2024","href":"postseason-2024.html"},{"label":"2025","href":"postseason-2025.html"},{"label":"2026","href":"postseason.html","match":"^postseason(-2026|-proj-wk\\d+)?\\.html$"}]},"projection-archive":{"label":"Projection","aria":"Projection archive","min":2,"items":[{"label":"After wk 8","href":"postseason-proj-wk08.html"},{"label":"After wk 9","href":"postseason-proj-wk09.html"},{"label":"After wk 10","href":"postseason-proj-wk10.html","match":"^postseason(-proj-wk10)?\\.html$"}]},"poll":{"label":"","aria":"Poll pages","items":[{"label":"Latest poll","href":"poll.html","match":"^poll(-top25-wk\\d+)?\\.html$"},{"label":"How the poll works","href":"poll-how.html"},{"label":"Bot ballots","href":"poll-bots.html"}]},"special":{"label":"Event","aria":"Special events","items":[{"label":"The Guillotine","href":"special.html","icon":"../assets/logos/Guillotine/Guillotine%20G.png"}]}},"awards":"week-10.html"};
  var DEV_KEY = "ncaa180.dev";
  var here = (typeof document !== "undefined" && document.currentScript && document.currentScript.src) || "";
  var base = here ? here.replace(/assets\/menu\.js.*$/, "") : "";
  var BELL = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" style="vertical-align:-3px"><path fill="currentColor" d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg>';
  // --dev: its own token (not a team color, not the --good/--bad win % scale) so the accessibility page can remap it.
  // Darker amber on light pages, lighter on dark (readable text either way).
  var CSS = ":root{--dev:#a85f00}@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--dev:#f0a63a}}:root[data-theme=dark]{--dev:#f0a63a}" +
    ".weeks a.n180-dev{border-style:dashed;border-color:var(--dev);color:var(--dev)}" +
    ".weeks a.n180-dev[aria-current]{background:var(--dev);border-color:var(--dev);color:var(--panel,#fff)}" +
    ".n180-devtag{font:700 9px/1 var(--num,sans-serif);letter-spacing:.06em;margin-left:5px;padding:1px 3px;border:1px solid currentColor;border-radius:2px;vertical-align:1px}" +
    ".n180-devbar{background:var(--dev);color:var(--panel,#fff);font:700 12px/1.2 var(--num,sans-serif);letter-spacing:.04em;text-align:center;padding:5px 8px;margin:0 0 8px;border-radius:3px}" +
    "@media print{.n180-devbar{display:none}}";

  function devOn() { try { return localStorage.getItem(DEV_KEY) === "1"; } catch (e) { return false; } }
  function setDev(on) {
    try { if (on) localStorage.setItem(DEV_KEY, "1"); else localStorage.removeItem(DEV_KEY); } catch (e) {}
    render(true);
  }

  // This page's file name; the home page (index.html) is the latest week's awards page.
  function pageFile() {
    var f = decodeURIComponent((location.pathname.split("/").pop() || ""));
    if (!f || f === "index.html") f = D.awards || "index.html";
    return f;
  }

  function el(tag, attrs, html) {
    var x = document.createElement(tag);
    for (var k in attrs) if (attrs[k] != null) x.setAttribute(k, attrs[k]);
    if (html != null) x.innerHTML = html;
    return x;
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"}[c]; }); }
  function url(h) { return /^(https?:)?\/\//.test(h) ? h : base + h; }
  function link(item, current) {
    var a = el("a", {href: url(item.href)});
    if (current) a.setAttribute("aria-current", "page");
    var inner = item.icon && item.icon !== "bell"
      ? '<img src="' + esc(url(item.icon)) + '" alt="" width="16" height="16" style="vertical-align:-3px;margin-right:4px">' : "";
    inner += esc(item.label);
    if (item.state === "hidden-dev") { a.className = "n180-dev"; inner += '<span class="n180-devtag">DEV</span>'; }
    a.innerHTML = inner;
    return a;
  }
  function visible(item, dev) { return !item.state || item.state === "visible" || (item.state === "hidden-dev" && dev); }
  function tabFor(key) {
    for (var i = 0; i < D.tabs.length; i++) {
      var t = D.tabs[i];
      if (t.id === key || (t.aliases || []).indexOf(key) >= 0) return t;
    }
    return null;
  }

  // ---- models (pure: tested in tests/menu.test.js) ----
  // Main tabs for page key `cur`: [{label, href, current, dev, bell, icon}]
  function mainModel(cur, dev) {
    return D.tabs.filter(function (t) { return visible(t, dev); }).map(function (t) {
      return {label: t.label, href: t.href, icon: t.icon, bell: t.icon === "bell", state: t.state,
              current: t.id === cur || (t.aliases || []).indexOf(cur) >= 0};
    });
  }
  function itemMatches(item, file) {
    if (item.match) { try { return new RegExp(item.match).test(file); } catch (e) { return false; } }
    return item.href === file;
  }
  // Sub-row `key` on page `file`: {label, aria, items:[{label, href, icon, state, current}]} or null (row hidden)
  function rowModel(key, dev, file) {
    var row = D.rows[key];
    if (!row) return null;
    var items = row.items.filter(function (i) { return visible(i, dev); });
    if (items.length < (row.min || 1)) return null;
    return {label: row.label || "", aria: row.aria, items: items.map(function (i) {
      return {label: i.label, href: i.href, icon: i.icon, state: i.state, current: itemMatches(i, file)};
    })};
  }
  // "DEV — not public" bar: Dev view on and this page's tab isn't public. A page left out of this file
  // (state hidden) carries its own state in data-state, baked at build.
  function needsBar(cur, pageState, dev) {
    if (!dev) return false;
    var t = tabFor(cur);
    var state = t ? (t.state || "visible") : (pageState || "visible");
    return state !== "visible";
  }

  // ---- DOM ----
  function fillMain(nav, dev) {
    nav.innerHTML = "";
    mainModel(nav.getAttribute("data-current") || "", dev).forEach(function (t) {
      var a;
      if (t.bell) {
        a = el("a", {href: url(t.href), "class": "n180-bell" + (t.state === "hidden-dev" ? " n180-dev" : ""), "aria-label": t.label, title: t.label}, BELL);
        if (t.current) a.setAttribute("aria-current", "page");
      } else {
        a = link(t, t.current);
      }
      nav.appendChild(a);
    });
  }

  function fillRow(nav, dev, file) {
    var m = rowModel(nav.getAttribute("data-row"), dev, file);
    nav.innerHTML = "";
    if (!m) { nav.hidden = true; return; }
    nav.hidden = false;
    if (m.aria) nav.setAttribute("aria-label", m.aria);
    if (m.label) nav.appendChild(el("span", {}, esc(m.label)));
    m.items.forEach(function (i) { nav.appendChild(link(i, i.current)); });
  }

  function devBar(nav, dev) {
    var old = document.querySelector(".n180-devbar");
    if (old) old.remove();
    if (!needsBar(nav.getAttribute("data-current") || "", nav.getAttribute("data-state"), dev)) return;
    nav.parentNode.insertBefore(el("div", {"class": "n180-devbar", role: "note"}, "DEV &mdash; not public"), nav);
  }

  function render(force) {
    if (!D) return;
    if (!document.getElementById("n180-menu-css")) {
      var st = el("style", {id: "n180-menu-css"}, CSS);
      (document.head || document.documentElement).appendChild(st);
    }
    var dev = devOn(), file = pageFile();
    var mains = document.querySelectorAll('nav.weeks[aria-label="Pages"][data-current]');
    for (var i = 0; i < mains.length; i++) {
      var n = mains[i];
      if (n.getAttribute("data-r") && !force) continue;
      fillMain(n, dev);
      devBar(n, dev);
      n.setAttribute("data-r", "1");
    }
    var rows = document.querySelectorAll("nav.weeks[data-row]");
    for (var j = 0; j < rows.length; j++) {
      if (rows[j].getAttribute("data-r") && !force) continue;
      fillRow(rows[j], dev, file);
      rows[j].setAttribute("data-r", "1");
    }
  }

  var api = {render: render, dev: devOn, setDev: setDev, data: D,
             mainModel: mainModel, rowModel: rowModel, needsBar: needsBar};
  if (typeof module !== "undefined" && module.exports) { module.exports = api; return; }  // node tests
  window.NCAA180 = window.NCAA180 || {};
  window.NCAA180.menu = api;
  render(false);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { render(false); });
})();
