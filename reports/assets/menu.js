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
  var D = {"tabs":[{"id":"awards","label":"Awards","href":"week-10.html"},{"id":"map","label":"Roster Map","href":"roster-map.html"},{"id":"standings","label":"Standings","href":"standings.html"},{"id":"scoreboard","label":"Games","href":"scoreboard.html"},{"id":"poll","label":"Poll","href":"poll.html","aliases":["poll-how","poll-bots"]},{"id":"postseason","label":"Postseason","href":"postseason.html"},{"id":"special","label":"Special Events","href":"special.html"},{"id":"managers","label":"Managers","href":"managers.html"},{"id":"records","label":"Records","href":"records.html"},{"id":"about","label":"About","href":"about.html"},{"id":"access","label":"Accessibility","href":"access.html","state":"hidden-dev"},{"id":"app","label":"Notification settings","href":"app.html","icon":"bell"}],"rows":{"awards-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2021","href":"week-2021-11.html","match":"^week-2021-\\d+\\.html$"},{"label":"2022","href":"week-2022-11.html","match":"^week-2022-\\d+\\.html$"},{"label":"2023","href":"week-2023-11.html","match":"^week-2023-\\d+\\.html$"},{"label":"2024","href":"week-2024-11.html","match":"^week-2024-\\d+\\.html$"},{"label":"2025","href":"week-2025-11.html","match":"^week-2025-\\d+\\.html$"},{"label":"2026","href":"week-10.html","match":"^week-\\d{2}\\.html$"}]},"awards-weeks-2021":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2021-01.html"},{"label":"Wk 2","href":"week-2021-02.html"},{"label":"Wk 3","href":"week-2021-03.html"},{"label":"Wk 4","href":"week-2021-04.html"},{"label":"Wk 5","href":"week-2021-05.html"},{"label":"Wk 6","href":"week-2021-06.html"},{"label":"Wk 7","href":"week-2021-07.html"},{"label":"Wk 8","href":"week-2021-08.html"},{"label":"Wk 9","href":"week-2021-09.html"},{"label":"Wk 10","href":"week-2021-10.html"},{"label":"Wk 11","href":"week-2021-11.html"}]},"awards-weeks-2022":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2022-01.html"},{"label":"Wk 2","href":"week-2022-02.html"},{"label":"Wk 3","href":"week-2022-03.html"},{"label":"Wk 4","href":"week-2022-04.html"},{"label":"Wk 5","href":"week-2022-05.html"},{"label":"Wk 6","href":"week-2022-06.html"},{"label":"Wk 7","href":"week-2022-07.html"},{"label":"Wk 8","href":"week-2022-08.html"},{"label":"Wk 9","href":"week-2022-09.html"},{"label":"Wk 10","href":"week-2022-10.html"},{"label":"Wk 11","href":"week-2022-11.html"}]},"awards-weeks-2023":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2023-01.html"},{"label":"Wk 2","href":"week-2023-02.html"},{"label":"Wk 3","href":"week-2023-03.html"},{"label":"Wk 4","href":"week-2023-04.html"},{"label":"Wk 5","href":"week-2023-05.html"},{"label":"Wk 6","href":"week-2023-06.html"},{"label":"Wk 7","href":"week-2023-07.html"},{"label":"Wk 8","href":"week-2023-08.html"},{"label":"Wk 9","href":"week-2023-09.html"},{"label":"Wk 10","href":"week-2023-10.html"},{"label":"Wk 11","href":"week-2023-11.html"}]},"awards-weeks-2024":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2024-01.html"},{"label":"Wk 2","href":"week-2024-02.html"},{"label":"Wk 3","href":"week-2024-03.html"},{"label":"Wk 4","href":"week-2024-04.html"},{"label":"Wk 5","href":"week-2024-05.html"},{"label":"Wk 6","href":"week-2024-06.html"},{"label":"Wk 7","href":"week-2024-07.html"},{"label":"Wk 8","href":"week-2024-08.html"},{"label":"Wk 9","href":"week-2024-09.html"},{"label":"Wk 10","href":"week-2024-10.html"},{"label":"Wk 11","href":"week-2024-11.html"}]},"awards-weeks-2025":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2025-01.html"},{"label":"Wk 2","href":"week-2025-02.html"},{"label":"Wk 3","href":"week-2025-03.html"},{"label":"Wk 4","href":"week-2025-04.html"},{"label":"Wk 5","href":"week-2025-05.html"},{"label":"Wk 6","href":"week-2025-06.html"},{"label":"Wk 7","href":"week-2025-07.html"},{"label":"Wk 8","href":"week-2025-08.html"},{"label":"Wk 9","href":"week-2025-09.html"},{"label":"Wk 10","href":"week-2025-10.html"},{"label":"Wk 11","href":"week-2025-11.html"}]},"awards-weeks-2026":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-01.html"},{"label":"Wk 2","href":"week-02.html"},{"label":"Wk 3","href":"week-03.html"},{"label":"Wk 4","href":"week-04.html"},{"label":"Wk 5","href":"week-05.html"},{"label":"Wk 6","href":"week-06.html"},{"label":"Wk 7","href":"week-07.html"},{"label":"Wk 8","href":"week-08.html"},{"label":"Wk 9","href":"week-09.html"},{"label":"Wk 10","href":"week-10.html"}]},"standings-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2021","href":"standings-2021.html"},{"label":"2022","href":"standings-2022.html"},{"label":"2023","href":"standings-2023.html"},{"label":"2024","href":"standings-2024.html"},{"label":"2025","href":"standings-2025.html"},{"label":"2026","href":"standings.html","match":"^standings(-2026)?\\.html$"}]},"postseason-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2019","href":"postseason-2019.html"},{"label":"2020","href":"postseason-2020.html"},{"label":"2021","href":"postseason-2021.html"},{"label":"2022","href":"postseason-2022.html"},{"label":"2023","href":"postseason-2023.html"},{"label":"2024","href":"postseason-2024.html"},{"label":"2025","href":"postseason-2025.html"},{"label":"2026","href":"postseason.html","match":"^postseason(-2026|-proj-wk\\d+)?\\.html$"}]},"projection-archive":{"label":"Projection","aria":"Projection archive","min":2,"items":[{"label":"After wk 8","href":"postseason-proj-wk08.html"},{"label":"After wk 9","href":"postseason-proj-wk09.html"},{"label":"After wk 10","href":"postseason-proj-wk10.html","match":"^postseason(-proj-wk10)?\\.html$"}]},"poll":{"label":"","aria":"Poll pages","items":[{"label":"Latest poll","href":"poll.html","match":"^poll(-top25-wk\\d+)?\\.html$"},{"label":"How the poll works","href":"poll-how.html"},{"label":"Bot ballots","href":"poll-bots.html"}]},"special":{"label":"Event","aria":"Special events","items":[{"label":"The Guillotine","href":"special.html","icon":"../assets/logos/Guillotine/Guillotine%20G.png"}]}},"awards":"week-10.html"};
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

  // ---- Colour tokens (Project Manager 5.8; todo-ranked-odds-colorblind.md) ----------------
  // Shared good/bad colours for every page. Hard-coded Standard (red/green) for now; the
  // accessibility page will replace this style element's text per device (colour-blind presets,
  // custom pickers). Use the tokens, never hex, for anything that means good/bad:
  //   --good / --bad      text and lines (>= 4.5:1 on --panel, light and dark)
  //   --neutral           the 50% midpoint of the win % scale (grey, text-safe)
  //   --good-soft / --bad-soft   background tints (rows, bubbles)
  //   --good-fill / --bad-fill   solid fills with --on-fill text (same in light and dark)
  // Diverging scale (win %): NCAA180.colors.scale(p) -> colour for p in 0..1 (bad -> neutral -> good,
  // blended in OKLab so the middle stays grey). Kept in a <style> element, not inline on <html>,
  // so saved images (snapshot.js copies style elements) carry the viewer's colours.
  var TOKENS_ID = "n180-tokens";
  var TOKENS_LIGHT = {"--good": "#1a7f37", "--bad": "#b42318", "--neutral": "#6b7484",
    "--good-soft": "#e3f3e8", "--bad-soft": "#fbe4e1"};
  var TOKENS_DARK = {"--good": "#4fc785", "--bad": "#ff7b72", "--neutral": "#8a96ab",
    "--good-soft": "#173a2a", "--bad-soft": "#4a2024"};
  var TOKENS_BOTH = {"--good-fill": "#1a7f37", "--bad-fill": "#b42318", "--on-fill": "#ffffff"};
  function decl(o) { var s = ""; for (var k in o) s += k + ":" + o[k] + ";"; return s; }
  function tokensCss(light, dark, both) {
    var d = decl(dark);
    return ":root{" + decl(light) + decl(both) + "}" +
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){" + d + "}}" +
      ":root[data-theme=dark]{" + d + "}";
  }
  function applyTokens(css) {
    if (typeof document === "undefined") return;
    var st = document.getElementById(TOKENS_ID);
    if (!st) {
      st = document.createElement("style");
      st.id = TOKENS_ID;
      (document.head || document.documentElement).appendChild(st);
    }
    st.textContent = css;
  }

  // OKLab blend (sRGB hex in, rgb() out).
  function hexRgb(h) {
    h = String(h).trim().replace(/^#/, "");
    if (h.length === 3) h = h.replace(/./g, "$&$&");
    var n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function lin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function gam(c) { c = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; return Math.round(Math.max(0, Math.min(1, c)) * 255); }
  function toLab(rgb) {
    var r = lin(rgb[0]), g = lin(rgb[1]), b = lin(rgb[2]);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function fromLab(o) {
    var l = Math.pow(o[0] + 0.3963377774 * o[1] + 0.2158037573 * o[2], 3);
    var m = Math.pow(o[0] - 0.1055613458 * o[1] - 0.0638541728 * o[2], 3);
    var s = Math.pow(o[0] - 0.0894841775 * o[1] - 1.2914855480 * o[2], 3);
    return [gam(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            gam(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            gam(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)];
  }
  function mix(a, b, t) {
    var A = toLab(hexRgb(a)), B = toLab(hexRgb(b));
    var c = fromLab([A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t, A[2] + (B[2] - A[2]) * t]);
    return "rgb(" + c[0] + "," + c[1] + "," + c[2] + ")";
  }
  // Current token values on this page (theme-aware); falls back to the light set off-browser.
  function tokens() {
    var out = {good: TOKENS_LIGHT["--good"], bad: TOKENS_LIGHT["--bad"], neutral: TOKENS_LIGHT["--neutral"]};
    if (typeof getComputedStyle === "undefined" || typeof document === "undefined") return out;
    var cs = getComputedStyle(document.documentElement);
    for (var k in out) { var v = cs.getPropertyValue("--" + k).trim(); if (/^#[0-9a-f]{3,6}$/i.test(v)) out[k] = v; }
    return out;
  }
  // p: 0..1 (0.5 = toss-up). t: optional {good, bad, neutral} (from tokens(); pass it when colouring many cells).
  function scale(p, t) {
    t = t || tokens();
    p = Math.max(0, Math.min(1, Number(p)));
    if (!isFinite(p)) return t.neutral;
    return mix(t.neutral, p >= 0.5 ? t.good : t.bad, Math.abs(p - 0.5) * 2);
  }
  var colors = {tokens: tokens, scale: scale, mix: mix, css: tokensCss(TOKENS_LIGHT, TOKENS_DARK, TOKENS_BOTH),
                defaults: {light: TOKENS_LIGHT, dark: TOKENS_DARK, both: TOKENS_BOTH}, buildCss: tokensCss, apply: applyTokens};
  // Legacy report CSS defines --up/--dn directly. Override it in the later-loaded shared
  // token style so historical reports respond without rebuilding ~100 static pages.
  colors.css += ":root{--up:var(--good);--dn:var(--bad)}" +
    "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--up:var(--good);--dn:var(--bad)}}" +
    ":root[data-theme=dark]{--up:var(--good);--dn:var(--bad)}";
  // Accessibility preferences are device-local. Invalid or inaccessible storage is harmless.
  var ACCESS_KEY = "ncaa180.access";
  var ACCESS_DEFAULTS = {mode:"standard",custom:{bad:"#b42318",good:"#1a7f37"},motion:"system",emphasis:false};
  var ACCESS_MODES = {
    standard:{light:["#1a7f37","#b42318"],dark:["#4fc785","#ff7b72"]},
    rg:{light:["#0758a8","#a65300"],dark:["#79b9ff","#ffb45d"]},
    by:{light:["#007b73","#b42318"],dark:["#65d4c6","#ff7b72"]},
    none:{light:["#252525","#595959"],dark:["#f2f2f2","#c5c5c5"]}
  };
  function validHex(x) { return typeof x==="string" && /^#[0-9a-fA-F]{6}$/.test(x); }
  function accessRead() {
    var o;
    try { o=JSON.parse(localStorage.getItem(ACCESS_KEY)||"null"); } catch(e) { o=null; }
    if(!o || typeof o!=="object" || Array.isArray(o)) o={};
    return {
      mode: ["standard","rg","by","none","custom"].indexOf(o.mode)>=0?o.mode:"standard",
      custom:{bad:validHex(o.custom&&o.custom.bad)?o.custom.bad:ACCESS_DEFAULTS.custom.bad,
              good:validHex(o.custom&&o.custom.good)?o.custom.good:ACCESS_DEFAULTS.custom.good},
      motion:["system","on","off"].indexOf(o.motion)>=0?o.motion:"system",
      emphasis:o.emphasis===true
    };
  }
  function contrast(a,b) {
    function lum(h) { var c=hexRgb(h).map(lin); return .2126*c[0]+.7152*c[1]+.0722*c[2]; }
    var x=lum(a),y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
  }
  function accessibleHex(h,bg) {
    var bgLum=contrast("#000000",bg)>contrast("#ffffff",bg)?"#000000":"#ffffff";
    if(contrast(h,bg)>=4.5) return h;
    var lo=0,hi=1,answer=bgLum;
    for(var i=0;i<22;i++) {
      var mid=(lo+hi)/2, candidate=mix(h,bgLum,mid), nums=candidate.match(/\d+/g).map(Number);
      var hex="#"+nums.map(function(n){return n.toString(16).padStart(2,"0");}).join("");
      if(contrast(hex,bg)>=4.5){answer=hex;hi=mid;}else lo=mid;
    }
    return answer;
  }
  function accessCss(o) {
    var m=ACCESS_MODES[o.mode],light={},dark={},both={};
    if(o.mode==="custom") {
      m={light:[o.custom.good,o.custom.bad],dark:[o.custom.good,o.custom.bad]};
    }
    if(m) {
      [["light",light,"#ffffff"],["dark",dark,"#171b22"]].forEach(function(row) {
        var pair=m[row[0]];
        row[1]["--good"]=accessibleHex(pair[0],row[2]);
        row[1]["--bad"]=accessibleHex(pair[1],row[2]);
        if(o.mode!=="standard") {
          row[1]["--good-soft"]=row[0]==="light"?"#e9eef2":"#26313a";
          row[1]["--bad-soft"]=row[0]==="light"?"#f1edf0":"#342c32";
        }
      });
    }
    // Solid fills must follow the selected palette too; white labels need 4.5:1 contrast.
    // Standard keeps its exact historical fills for visual compatibility.
    if(o.mode==="none") both={"--good-fill":"#3c3c3c","--bad-fill":"#656565"};
    else if(o.mode!=="standard") both={"--good-fill":accessibleHex(m.light[0],"#ffffff"),
      "--bad-fill":accessibleHex(m.light[1],"#ffffff")};
    var css=tokensCss(Object.assign({},TOKENS_LIGHT,light),Object.assign({},TOKENS_DARK,dark),
      Object.assign({},TOKENS_BOTH,both));
    css+=":root{--up:var(--good);--dn:var(--bad)}"+
      "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--up:var(--good);--dn:var(--bad)}}"+
      ":root[data-theme=dark]{--up:var(--good);--dn:var(--bad)}";
    if(o.motion==="on") css+="html *,html *::before,html *::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}";
    if(o.motion==="system") css+="@media (prefers-reduced-motion:reduce){html *,html *::before,html *::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}";
    if(o.motion==="off") css+="html{scroll-behavior:smooth}";
    if(o.emphasis||o.mode==="none") css+=":root{--n180-emphasis:1} .up,.dn,[class*=win],[class*=loss]{outline-offset:2px} a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid currentColor!important;outline-offset:3px}";
    return css;
  }
  function accessApply() { var o=accessRead(); colors.css=accessCss(o); applyTokens(colors.css); return o; }
  function accessSave(partial) {
    var o=accessRead();
    if(partial && typeof partial==="object") {
      if(partial.mode!==undefined)o.mode=partial.mode;
      if(partial.motion!==undefined)o.motion=partial.motion;
      if(partial.emphasis!==undefined)o.emphasis=partial.emphasis;
      if(partial.custom)o.custom=Object.assign({},o.custom,partial.custom);
    }
    o={mode:["standard","rg","by","none","custom"].includes(o.mode)?o.mode:"standard",
      custom:{good:validHex(o.custom&&o.custom.good)?o.custom.good:ACCESS_DEFAULTS.custom.good,
              bad:validHex(o.custom&&o.custom.bad)?o.custom.bad:ACCESS_DEFAULTS.custom.bad},
      motion:["system","on","off"].includes(o.motion)?o.motion:"system",emphasis:o.emphasis===true};
    try { localStorage.setItem(ACCESS_KEY,JSON.stringify(o)); }catch(e){}
    accessApply();
    if (typeof window !== "undefined" && typeof window.CustomEvent === "function")
      window.dispatchEvent(new CustomEvent("ncaa180:accesschange", {detail:accessRead()}));
    return accessRead();
  }
  function accessReset() {
    try {localStorage.removeItem(ACCESS_KEY);}catch(e){}
    var o=accessApply();
    if (typeof window !== "undefined" && typeof window.CustomEvent === "function")
      window.dispatchEvent(new CustomEvent("ncaa180:accesschange", {detail:o}));
    return o;
  }
  var access={read:accessRead,save:accessSave,reset:accessReset,apply:accessApply,
    contrast:contrast,adjust:accessibleHex,defaults:ACCESS_DEFAULTS,modes:ACCESS_MODES};

  accessApply();  // before the menu draws: no flash

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
      accessApply();
      if (typeof window.CustomEvent === "function")
        window.dispatchEvent(new CustomEvent("ncaa180:accesschange", {detail:accessRead()}));
    }
  });
  render(false);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { render(false); });
})();
