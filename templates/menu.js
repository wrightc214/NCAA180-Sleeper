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
  var D = /*__DATA__*/null;
  var DEV_KEY = "ncaa180.dev";
  var here = (typeof document !== "undefined" && document.currentScript && document.currentScript.src) || "";
  var base = here ? here.replace(/assets\/menu\.js.*$/, "") : "";
  var BELL = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" style="vertical-align:-3px"><path fill="currentColor" d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2Z"/></svg>';
  // Built-in tab icons: config/nav.json "icon": "<name>" draws an icon-only tab (label = aria-label + tooltip).
  // Any other "icon" value is an image path shown before the label. Solid 24px glyphs, same style as the bell.
  function glyph(d) { return '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" style="vertical-align:-3px"><path fill="currentColor" fill-rule="evenodd" d="' + d + '"/></svg>'; }
  var ICONS = {bell: BELL, info: glyph("M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"), accessibility: glyph("M12 2a10 10 0 1 0 0 20a10 10 0 1 0 0-20zM17.1 8.4C15.53 8.82 13.69 9 12 9s-3.54-.18-5.1-.6l-.3 1.2c1.11.3 2.4.49 3.6.6V18h1.2v-3.6h1.2V18h1.2v-7.8c1.2-.11 2.48-.3 3.6-.6l-.3-1.2zM12 8.4c.66 0 1.2-.54 1.2-1.2S12.66 6 12 6s-1.2.54-1.2 1.2.54 1.2 1.2 1.2z")};
  // --dev: its own token (not a team color, not the --good/--bad win % scale) so the accessibility page can remap it.
  // Darker amber on light pages, lighter on dark (readable text either way).
  var CSS = ":root{--dev:#a85f00}@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--dev:#f0a63a}}:root[data-theme=dark]{--dev:#f0a63a}" +
    ".weeks a.n180-dev{border-style:dashed;border-color:var(--dev);color:var(--dev)}" +
    ".weeks a.n180-dev[aria-current]{background:var(--dev);border-color:var(--dev);color:var(--panel,#fff)}" +
    ".n180-devtag{font:700 9px/1 var(--num,sans-serif);letter-spacing:.06em;margin-left:5px;padding:1px 3px;border:1px solid currentColor;border-radius:2px;vertical-align:1px}" +
    ".n180-devbar{background:var(--dev);color:var(--panel,#fff);font:700 12px/1.2 var(--num,sans-serif);letter-spacing:.04em;text-align:center;padding:5px 8px;margin:0 0 8px;border-radius:3px}" +
    "@media print{.n180-devbar{display:none}}";

  // Accessibility is independently maintained in templates/accessibility.js.
  // scripts/site_common.py bundles it here so existing static pages stay synchronous.
  /*__ACCESSIBILITY__*/
  var a11y = createNCAA180Accessibility();
  var colors = a11y.colors, access = a11y.access;
  var ACCESS_KEY = a11y.key;
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
    var inner = item.icon && !ICONS[item.icon]
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
  // Main tabs for page key `cur`: [{label, href, current, dev, bell, glyph, icon}] (glyph = built-in icon name or null)
  // Parent points to the first sub-page actually visible in this viewer's mode.
  function firstVisibleHref(tab, dev) {
    var row = D.rows[tab.id];
    if (!row) return tab.href;
    var first = row.items.find(function(item) { return visible(item, dev); });
    return first ? first.href : tab.href;
  }
  function mainModel(cur, dev) {
    return D.tabs.filter(function (t) { return visible(t, dev); }).map(function (t) {
      return {label: t.label, href: firstVisibleHref(t, dev), icon: t.icon, bell: t.icon === "bell", glyph: ICONS[t.icon] ? t.icon : null, state: t.state,
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
      if (t.glyph) {
        a = el("a", {href: url(t.href), "class": "n180-icon n180-" + t.glyph + (t.state === "hidden-dev" ? " n180-dev" : ""), "aria-label": t.label, title: t.label}, ICONS[t.glyph]);
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

  var api = {access:access, render: render, dev: devOn, setDev: setDev, data: D, colors: colors,
             mainModel: mainModel, rowModel: rowModel, needsBar: needsBar};
  if (typeof module !== "undefined" && module.exports) { module.exports = api; return; }  // node tests
  window.NCAA180 = window.NCAA180 || {};
  window.NCAA180.menu = api;
  window.NCAA180.colors = colors;
  window.NCAA180.access = access;
  // Keep open tabs on the same device in sync without touching unrelated storage keys.
  window.addEventListener("storage", function (e) {
    if (e.key === ACCESS_KEY || e.key === null) {
      access.apply();
      if (typeof window.CustomEvent === "function")
        window.dispatchEvent(new window.CustomEvent("ncaa180:accesschange", {detail:access.read()}));
    }
  });
  render(false);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { render(false); });
})();
