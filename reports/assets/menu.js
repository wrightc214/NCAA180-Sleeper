// NCAA 180 site menu (todo-header-rebuild.md). GENERATED into reports/assets/menu.js by
// scripts/menu_build.py from config/nav.json + the pages in reports/. Edit this template or the
// config, never reports/assets/menu.js.
//
// Every page carries empty placeholders written once by site_common.menu_html():
//   <nav class="weeks" aria-label="Pages" data-current="standings"></nav>   main tabs
//   <nav class="weeks sub" data-row="standings-seasons"></nav>              optional sub-rows
//     (drawn below the page header: see placeRows)
//   <script src="assets/menu.js"></script>                                   this file (synchronous: no flash)
// Dev view (per device, localStorage "ncaa180.dev" = "1", switched on the About page's dev panel)
// shows hidden-dev tabs/items with a DEV tag and a "DEV — not public" bar on non-public pages.
(function () {
  "use strict";
  var D = {"tabs":[{"id":"awards","label":"Awards","href":"week-11.html"},{"id":"map","label":"Roster Map","href":"roster-map.html"},{"id":"standings","label":"Standings","href":"standings.html"},{"id":"scoreboard","label":"Games","href":"scoreboard.html"},{"id":"poll","label":"Poll","href":"poll.html","aliases":["poll-how","poll-bots"]},{"id":"postseason","label":"Postseason","href":"postseason.html"},{"id":"selection-watch","label":"Selection Watch","href":"selection-watch.html"},{"id":"special","label":"Special Events","href":"special.html"},{"id":"team","label":"Teams","href":"team.html"},{"id":"managers","label":"Managers","href":"managers.html"},{"id":"transactions","label":"Transactions","href":"transactions.html"},{"id":"records","label":"Records","href":"records.html"},{"id":"about","label":"About","href":"about.html","icon":"info"},{"id":"access","label":"Accessibility","href":"access.html","icon":"accessibility"},{"id":"app","label":"Notification settings","href":"app.html","icon":"bell"}],"rows":{"awards-weeks-2019":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"CCG","href":"ceremony-2019-12.html"},{"label":"Opening Bowls","href":"ceremony-2019-13.html"},{"label":"Showcase Bowls","href":"ceremony-2019-14.html"},{"label":"Marquee Bowls","href":"ceremony-2019-15.html"},{"label":"Championship Week","href":"ceremony-2019-16.html"}]},"awards-weeks-2020":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"CCG","href":"ceremony-2020-12.html"},{"label":"Showcase Bowls","href":"ceremony-2020-14.html"},{"label":"Marquee Bowls","href":"ceremony-2020-15.html"},{"label":"Championship Week","href":"ceremony-2020-16.html"}]},"awards-weeks-2021":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2021-01.html"},{"label":"Wk 2","href":"week-2021-02.html"},{"label":"Wk 3","href":"week-2021-03.html"},{"label":"Wk 4","href":"week-2021-04.html"},{"label":"Wk 5","href":"week-2021-05.html"},{"label":"Wk 6","href":"week-2021-06.html"},{"label":"Wk 7","href":"week-2021-07.html"},{"label":"Wk 8","href":"week-2021-08.html"},{"label":"Wk 9","href":"week-2021-09.html"},{"label":"Wk 10","href":"week-2021-10.html"},{"label":"Wk 11","href":"week-2021-11.html"},{"label":"CCG","href":"ceremony-2021-12.html"},{"label":"Opening Bowls","href":"ceremony-2021-13.html"},{"label":"Showcase Bowls","href":"ceremony-2021-14.html"},{"label":"Championship Week","href":"ceremony-2021-17.html"},{"label":"Week 18 · Postseason Week 6","href":"ceremony-2021-18.html"}]},"awards-weeks-2022":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2022-01.html"},{"label":"Wk 2","href":"week-2022-02.html"},{"label":"Wk 3","href":"week-2022-03.html"},{"label":"Wk 4","href":"week-2022-04.html"},{"label":"Wk 5","href":"week-2022-05.html"},{"label":"Wk 6","href":"week-2022-06.html"},{"label":"Wk 7","href":"week-2022-07.html"},{"label":"Wk 8","href":"week-2022-08.html"},{"label":"Wk 9","href":"week-2022-09.html"},{"label":"Wk 10","href":"week-2022-10.html"},{"label":"Wk 11","href":"week-2022-11.html"},{"label":"CCG","href":"ceremony-2022-12.html"},{"label":"Opening Bowls","href":"ceremony-2022-13.html"},{"label":"Showcase Bowls","href":"ceremony-2022-14.html"},{"label":"Marquee Bowls","href":"ceremony-2022-15.html"},{"label":"Prestige Bowls","href":"ceremony-2022-16.html"},{"label":"Championship Week","href":"ceremony-2022-17.html"},{"label":"Week 18 · Postseason Week 6","href":"ceremony-2022-18.html"}]},"awards-weeks-2023":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2023-01.html"},{"label":"Wk 2","href":"week-2023-02.html"},{"label":"Wk 3","href":"week-2023-03.html"},{"label":"Wk 4","href":"week-2023-04.html"},{"label":"Wk 5","href":"week-2023-05.html"},{"label":"Wk 6","href":"week-2023-06.html"},{"label":"Wk 7","href":"week-2023-07.html"},{"label":"Wk 8","href":"week-2023-08.html"},{"label":"Wk 9","href":"week-2023-09.html"},{"label":"Wk 10","href":"week-2023-10.html"},{"label":"Wk 11","href":"week-2023-11.html"},{"label":"CCG","href":"ceremony-2023-12.html"},{"label":"Opening Bowls","href":"ceremony-2023-13.html"},{"label":"Showcase Bowls","href":"ceremony-2023-14.html"},{"label":"Marquee Bowls","href":"ceremony-2023-15.html"},{"label":"Prestige Bowls","href":"ceremony-2023-16.html"},{"label":"Championship Week","href":"ceremony-2023-17.html"},{"label":"Week 18 · Postseason Week 6","href":"ceremony-2023-18.html"}]},"awards-weeks-2024":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2024-01.html"},{"label":"Wk 2","href":"week-2024-02.html"},{"label":"Wk 3","href":"week-2024-03.html"},{"label":"Wk 4","href":"week-2024-04.html"},{"label":"Wk 5","href":"week-2024-05.html"},{"label":"Wk 6","href":"week-2024-06.html"},{"label":"Wk 7","href":"week-2024-07.html"},{"label":"Wk 8","href":"week-2024-08.html"},{"label":"Wk 9","href":"week-2024-09.html"},{"label":"Wk 10","href":"week-2024-10.html"},{"label":"Wk 11","href":"week-2024-11.html"},{"label":"CCG","href":"ceremony-2024-12.html"},{"label":"Opening Bowls","href":"ceremony-2024-13.html"},{"label":"Showcase Bowls","href":"ceremony-2024-14.html"},{"label":"Marquee Bowls","href":"ceremony-2024-15.html"},{"label":"Prestige Bowls","href":"ceremony-2024-16.html"},{"label":"Championship Week","href":"ceremony-2024-17.html"}]},"awards-weeks-2025":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-2025-01.html"},{"label":"Wk 2","href":"week-2025-02.html"},{"label":"Wk 3","href":"week-2025-03.html"},{"label":"Wk 4","href":"week-2025-04.html"},{"label":"Wk 5","href":"week-2025-05.html"},{"label":"Wk 6","href":"week-2025-06.html"},{"label":"Wk 7","href":"week-2025-07.html"},{"label":"Wk 8","href":"week-2025-08.html"},{"label":"Wk 9","href":"week-2025-09.html"},{"label":"Wk 10","href":"week-2025-10.html"},{"label":"Wk 11","href":"week-2025-11.html"},{"label":"CCG","href":"ceremony-2025-12.html"},{"label":"Opening Bowls","href":"ceremony-2025-13.html"},{"label":"Showcase Bowls","href":"ceremony-2025-14.html"},{"label":"Marquee Bowls","href":"ceremony-2025-15.html"},{"label":"Prestige Bowls","href":"ceremony-2025-16.html"},{"label":"Championship Week","href":"ceremony-2025-17.html"}]},"awards-weeks-2026":{"label":"Week","aria":"Weeks","min":2,"items":[{"label":"Wk 1","href":"week-01.html"},{"label":"Wk 2","href":"week-02.html"},{"label":"Wk 3","href":"week-03.html"},{"label":"Wk 4","href":"week-04.html"},{"label":"Wk 5","href":"week-05.html"},{"label":"Wk 6","href":"week-06.html"},{"label":"Wk 7","href":"week-07.html"},{"label":"Wk 8","href":"week-08.html"},{"label":"Wk 9","href":"week-09.html"},{"label":"Wk 10","href":"week-10.html"},{"label":"Wk 11","href":"week-11.html"}]},"awards-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2019","href":"ceremony-2019-16.html","match":"^(?:week-2019-\\d{2}|ceremony-2019-(?:\\d{2}|year-end))\\.html$"},{"label":"2020","href":"ceremony-2020-16.html","match":"^(?:week-2020-\\d{2}|ceremony-2020-(?:\\d{2}|year-end))\\.html$"},{"label":"2021","href":"ceremony-2021-18.html","match":"^(?:week-2021-\\d{2}|ceremony-2021-(?:\\d{2}|year-end))\\.html$"},{"label":"2022","href":"ceremony-2022-18.html","match":"^(?:week-2022-\\d{2}|ceremony-2022-(?:\\d{2}|year-end))\\.html$"},{"label":"2023","href":"ceremony-2023-18.html","match":"^(?:week-2023-\\d{2}|ceremony-2023-(?:\\d{2}|year-end))\\.html$"},{"label":"2024","href":"ceremony-2024-17.html","match":"^(?:week-2024-\\d{2}|ceremony-2024-(?:\\d{2}|year-end))\\.html$"},{"label":"2025","href":"ceremony-2025-17.html","match":"^(?:week-2025-\\d{2}|ceremony-2025-(?:\\d{2}|year-end))\\.html$"},{"label":"2026","href":"week-11.html","match":"^(?:week-\\d{2}|ceremony-2026-(?:\\d{2}|year-end))\\.html$"}]},"standings-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2021","href":"standings-2021.html"},{"label":"2022","href":"standings-2022.html"},{"label":"2023","href":"standings-2023.html"},{"label":"2024","href":"standings-2024.html"},{"label":"2025","href":"standings-2025.html"},{"label":"2026","href":"standings.html","match":"^standings(-2026)?\\.html$"}]},"postseason-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2019","href":"postseason-2019.html"},{"label":"2020","href":"postseason-2020.html"},{"label":"2021","href":"postseason-2021.html"},{"label":"2022","href":"postseason-2022.html"},{"label":"2023","href":"postseason-2023.html"},{"label":"2024","href":"postseason-2024.html"},{"label":"2025","href":"postseason-2025.html"},{"label":"2026","href":"postseason.html","match":"^postseason(-2026|-proj-wk\\d+)?\\.html$"}]},"dwight-seasons":{"label":"Season","aria":"Seasons","items":[{"label":"2026","href":"dwight-fight.html","match":"^dwight-fight(-2026)?\\.html$"},{"label":"2025","href":"dwight-fight-2025.html"},{"label":"2024","href":"dwight-fight-2024.html"},{"label":"2023","href":"dwight-fight-2023.html"},{"label":"2022","href":"dwight-fight-2022.html"},{"label":"2021","href":"dwight-fight-2021.html"}]},"projection-archive":{"label":"Projection","aria":"Projection archive","min":2,"items":[{"label":"After wk 8","href":"postseason-proj-wk08.html"},{"label":"After wk 9","href":"postseason-proj-wk09.html"},{"label":"After wk 10","href":"postseason-proj-wk10.html","match":"^postseason(-proj-wk10)?\\.html$"}]},"poll":{"label":"","aria":"Poll pages","items":[{"label":"Latest poll","href":"poll.html","match":"^poll(-top25-wk\\d+)?\\.html$"},{"label":"How the poll works","href":"poll-how.html"},{"label":"Bot ballots","href":"poll-bots.html"}]},"selection-watch":{"label":"","aria":"Selection Watch pages","items":[{"label":"CCG","href":"ccg-race.html"},{"label":"Playoffs","href":"selection-watch.html"}]},"special":{"label":"Event","aria":"Special events","items":[{"label":"The Guillotine","href":"special.html","match":"^(special|guillotine-\\d{4})\\.html$","icon":"../assets/logos/Guillotine/Guillotine%20G.png"},{"label":"Dwight Fight","href":"dwight-fight.html","match":"^dwight-fight(-\\d{4})?\\.html$","icon":"../assets/logos/Dwight%20Fight/Dwight%20Fight%20Glasses.png"},{"label":"Champions League","href":"cl-standings.html","match":"^cl-[a-z-]+\\.html$","state":"hidden-dev"}]},"guillotine-seasons":{"label":"Season","min":2,"aria":"Seasons","items":[{"label":"2026","href":"special.html","match":"^special\\.html$"},{"label":"2025 replay","href":"guillotine-2025.html","state":"hidden-dev"}]},"champions-league":{"label":"","aria":"Champions League pages","items":[{"label":"Standings","href":"cl-standings.html","state":"hidden-dev"},{"label":"Schedule","href":"cl-schedule.html","state":"hidden-dev"},{"label":"Scoreboard","href":"cl-scoreboard.html","state":"hidden-dev"},{"label":"Field","href":"cl-field.html","state":"hidden-dev"},{"label":"Selection","href":"cl-selection.html","state":"hidden-dev"},{"label":"Rules","href":"cl-rules.html","state":"hidden-dev"}]}},"awards":"week-11.html"};
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
    "@media print{.n180-devbar{display:none}}" +
    "nav.weeks.sub.n180-wait{display:none}nav.weeks.sub.n180-below{margin:12px 0 0}nav.weeks.sub.n180-below+nav.weeks.sub.n180-below{margin-top:8px}";

  // Accessibility is independently maintained in templates/accessibility.js.
  // scripts/site_common.py bundles it here so existing static pages stay synchronous.
  // NCAA 180 Accessibility 5.8: independent palette and device-preference module.
// Bundled into generated reports/assets/menu.js at build time to keep old static pages
// compatible and apply tokens synchronously before the menu draws (no extra network fetch).
// This module owns only semantic colours, accessibility storage and motion/emphasis.
function createNCAA180Accessibility() {
  // ---- Colour tokens (Project Manager 5.8; todo-ranked-odds-colorblind.md) ----------------
  // Shared semantic colours for every page. Standard colours are injected from
  // config/league.json during menu generation; user presets and custom pickers
  // custom pickers). Use the tokens, never hex, for anything that means good/bad:
  //   --good / --bad      text and lines (>= 4.5:1 on --panel, light and dark)
  //   --neutral           the 50% midpoint of the win % scale (grey, text-safe)
  //   --good-soft / --bad-soft   background tints (rows, bubbles)
  //   --good-fill / --bad-fill   solid fills with --on-fill text (same in light and dark)
  // Diverging scale (win %): NCAA180.colors.scale(p) -> colour for p in 0..1 (bad -> neutral -> good,
  // blended in OKLab so the middle stays grey). Kept in a <style> element, not inline on <html>,
  // so saved images (snapshot.js copies style elements) carry the viewer's colours.
  var SETTINGS = {"palettes":{"standard":{"light":{"positive":"#1a7f37","negative":"#b42318","neutral":"#6b7484"},"dark":{"positive":"#4fc785","negative":"#ff7b72","neutral":"#8a96ab"}},"rg":{"light":{"positive":"#0758a8","negative":"#a65300"},"dark":{"positive":"#79b9ff","negative":"#ffb45d"}},"by":{"light":{"positive":"#007b73","negative":"#b42318"},"dark":{"positive":"#65d4c6","negative":"#ff7b72"}},"none":{"light":{"positive":"#252525","negative":"#595959"},"dark":{"positive":"#f2f2f2","negative":"#c5c5c5"}}},"appearance":{"soft":{"light":{"positive":"#e3f3e8","negative":"#fbe4e1"},"dark":{"positive":"#173a2a","negative":"#4a2024"}},"alternate_soft":{"light":{"positive":"#e9eef2","negative":"#f1edf0"},"dark":{"positive":"#26313a","negative":"#342c32"}},"fill_text":"#ffffff","monochrome_fills":{"positive":"#3c3c3c","negative":"#656565"}},"contrast":{"minimum_ratio":4.5,"distinguishability_ratio":1.5,"light_background":"#ffffff","dark_background":"#16213a"},"defaults":{"mode":"standard","motion":"system","emphasis":false,"auto_contrast":true},"labels":{"auto_contrast":"Automatically improve contrast","low_light":"Selected colours may be difficult to read on light backgrounds.","low_dark":"Selected colours may be difficult to read on dark backgrounds.","low_fill":"White text on solid fills may be difficult to read.","similar":"Positive and negative colours may be difficult to distinguish; automatic contrast correction cannot guarantee distinguishability."}};
  // Safe runtime defaults also protect manually loaded templates and older bundles.
  var P = SETTINGS && SETTINGS.palettes || {};
  var A = SETTINGS && SETTINGS.appearance || {};
  var C = SETTINGS && SETTINGS.contrast || {};
  var D = SETTINGS && SETTINGS.defaults || {};
  var L = SETTINGS && SETTINGS.labels || {};
  function settingHex(value, fallback) { return typeof value==="string" && /^#[0-9a-fA-F]{6}$/.test(value)?value:fallback; }
  function palette(mode,theme,role,fallback) {
    return settingHex(P[mode]&&P[mode][theme]&&P[mode][theme][role],fallback);
  }
  function appearance(section,theme,role,fallback) {
    return settingHex(A[section]&&A[section][theme]&&A[section][theme][role],fallback);
  }
  var LIGHT_BG = settingHex(C.light_background,"#ffffff");
  var DARK_BG = settingHex(C.dark_background,"#16213a");
  var FILL_TEXT = settingHex(A.fill_text,"#ffffff");
  var MIN_CONTRAST = typeof C.minimum_ratio==="number" && C.minimum_ratio>=1 && C.minimum_ratio<=21?C.minimum_ratio:4.5;
  var DISTINGUISH_RATIO = typeof C.distinguishability_ratio==="number" && C.distinguishability_ratio>=1 && C.distinguishability_ratio<=21?C.distinguishability_ratio:1.5;
  var TOKENS_ID = "n180-tokens";
  var TOKENS_LIGHT = {"--good":palette("standard","light","positive","#1a7f37"),"--bad":palette("standard","light","negative","#b42318"),
    "--neutral":palette("standard","light","neutral","#6b7484"),
    "--good-soft":appearance("soft","light","positive","#e3f3e8"),"--bad-soft":appearance("soft","light","negative","#fbe4e1")};
  var TOKENS_DARK = {"--good":palette("standard","dark","positive","#4fc785"),"--bad":palette("standard","dark","negative","#ff7b72"),
    "--neutral":palette("standard","dark","neutral","#8a96ab"),
    "--good-soft":appearance("soft","dark","positive","#173a2a"),"--bad-soft":appearance("soft","dark","negative","#4a2024")};
  var TOKENS_BOTH = {"--good-fill":TOKENS_LIGHT["--good"],"--bad-fill":TOKENS_LIGHT["--bad"],"--on-fill":FILL_TEXT};
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
  var ACCESS_DEFAULTS = {
    mode:["standard","rg","by","none","custom"].includes(D.mode)?D.mode:"standard",
    custom:{bad:TOKENS_LIGHT["--bad"],good:TOKENS_LIGHT["--good"]},
    motion:["system","on","off"].includes(D.motion)?D.motion:"system",
    emphasis:D.emphasis===true,autoContrast:D.auto_contrast!==false
  };
  var ACCESS_MODES = {
    standard:{light:[TOKENS_LIGHT["--good"],TOKENS_LIGHT["--bad"]],dark:[TOKENS_DARK["--good"],TOKENS_DARK["--bad"]]},
    rg:{light:[palette("rg","light","positive","#0758a8"),palette("rg","light","negative","#a65300")],dark:[palette("rg","dark","positive","#79b9ff"),palette("rg","dark","negative","#ffb45d")]},
    by:{light:[palette("by","light","positive","#007b73"),palette("by","light","negative","#b42318")],dark:[palette("by","dark","positive","#65d4c6"),palette("by","dark","negative","#ff7b72")]},
    none:{light:[palette("none","light","positive","#252525"),palette("none","light","negative","#595959")],dark:[palette("none","dark","positive","#f2f2f2"),palette("none","dark","negative","#c5c5c5")]}
  };
  function validHex(x) { return typeof x==="string" && /^#[0-9a-fA-F]{6}$/.test(x); }
  function accessRead() {
    var o;
    try { o=JSON.parse(localStorage.getItem(ACCESS_KEY)||"null"); } catch(e) { o=null; }
    if(!o || typeof o!=="object" || Array.isArray(o)) o={};
    return {
      mode: ["standard","rg","by","none","custom"].indexOf(o.mode)>=0?o.mode:ACCESS_DEFAULTS.mode,
      custom:{bad:validHex(o.custom&&o.custom.bad)?o.custom.bad:ACCESS_DEFAULTS.custom.bad,
              good:validHex(o.custom&&o.custom.good)?o.custom.good:ACCESS_DEFAULTS.custom.good},
      motion:["system","on","off"].indexOf(o.motion)>=0?o.motion:ACCESS_DEFAULTS.motion,
      emphasis:typeof o.emphasis==="boolean"?o.emphasis:ACCESS_DEFAULTS.emphasis,
      autoContrast:typeof o.autoContrast==="boolean"?o.autoContrast:ACCESS_DEFAULTS.autoContrast
    };
  }
  function contrast(a,b) {
    function lum(h) { var c=hexRgb(h).map(lin); return .2126*c[0]+.7152*c[1]+.0722*c[2]; }
    var x=lum(a),y=lum(b); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
  }
  function accessibleHex(h,bg) {
    var bgLum=contrast("#000000",bg)>contrast("#ffffff",bg)?"#000000":"#ffffff";
    if(contrast(h,bg)>=MIN_CONTRAST) return h;
    var lo=0,hi=1,answer=bgLum;
    for(var i=0;i<22;i++) {
      var mid=(lo+hi)/2, candidate=mix(h,bgLum,mid), nums=candidate.match(/\d+/g).map(Number);
      var hex="#"+nums.map(function(n){return n.toString(16).padStart(2,"0");}).join("");
      if(contrast(hex,bg)>=MIN_CONTRAST){answer=hex;hi=mid;}else lo=mid;
    }
    return answer;
  }
  // "No colour" (5.12.2, CW): shown disabled on the Accessibility page until its non-colour cues
  // exist. A stored "none" stays stored (read() still returns it) but paints exactly like Standard.
  // The none palette, monochrome fills and forced emphasis below are kept for when it ships.
  var NONE_AVAILABLE = false;
  function accessCss(o) {
    if(o.mode==="none"&&!NONE_AVAILABLE) o=Object.assign({},o,{mode:"standard"});
    var m=ACCESS_MODES[o.mode],light={},dark={},both={};
    if(o.mode==="custom") {
      m={light:[o.custom.good,o.custom.bad],dark:[o.custom.good,o.custom.bad]};
    }
    if(m) {
      [["light",light,LIGHT_BG],["dark",dark,DARK_BG]].forEach(function(row) {
        var pair=m[row[0]];
        row[1]["--good"]=o.mode==="custom"&&!o.autoContrast?pair[0]:accessibleHex(pair[0],row[2]);
        row[1]["--bad"]=o.mode==="custom"&&!o.autoContrast?pair[1]:accessibleHex(pair[1],row[2]);
        if(o.mode!=="standard") {
          row[1]["--good-soft"]=appearance("alternate_soft",row[0],"positive",row[0]==="light"?"#e9eef2":"#26313a");
          row[1]["--bad-soft"]=appearance("alternate_soft",row[0],"negative",row[0]==="light"?"#f1edf0":"#342c32");
        }
      });
    }
    // Solid fills must follow the selected palette too; white labels need 4.5:1 contrast.
    // Even owner-configured Standard fills must be legible with white labels.
    // Contrast-safe existing defaults retain their historical values.
    if(o.mode==="none") both={"--good-fill":settingHex(A.monochrome_fills&&A.monochrome_fills.positive,"#3c3c3c"),"--bad-fill":settingHex(A.monochrome_fills&&A.monochrome_fills.negative,"#656565")};
    else if(o.mode==="custom"&&!o.autoContrast) both={"--good-fill":m.light[0],"--bad-fill":m.light[1]};
    else both={"--good-fill":accessibleHex(m.light[0],FILL_TEXT),
      "--bad-fill":accessibleHex(m.light[1],FILL_TEXT)};
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
      if(partial.autoContrast!==undefined)o.autoContrast=partial.autoContrast;
      if(partial.custom)o.custom=Object.assign({},o.custom,partial.custom);
    }
    o={mode:["standard","rg","by","none","custom"].includes(o.mode)?o.mode:"standard",
      custom:{good:validHex(o.custom&&o.custom.good)?o.custom.good:ACCESS_DEFAULTS.custom.good,
              bad:validHex(o.custom&&o.custom.bad)?o.custom.bad:ACCESS_DEFAULTS.custom.bad},
      motion:["system","on","off"].includes(o.motion)?o.motion:"system",emphasis:o.emphasis===true,
      autoContrast:o.autoContrast!==false};
    try { localStorage.setItem(ACCESS_KEY,JSON.stringify(o)); }catch(e){}
    accessApply();
    if (typeof window !== "undefined" && typeof window.CustomEvent === "function")
      window.dispatchEvent(new window.CustomEvent("ncaa180:accesschange", {detail:accessRead()}));
    return accessRead();
  }
  function accessReset() {
    try {localStorage.removeItem(ACCESS_KEY);}catch(e){}
    var o=accessApply();
    if (typeof window !== "undefined" && typeof window.CustomEvent === "function")
      window.dispatchEvent(new window.CustomEvent("ncaa180:accesschange", {detail:o}));
    return o;
  }
  var access={read:accessRead,save:accessSave,reset:accessReset,apply:accessApply,
    contrast:contrast,adjust:accessibleHex,defaults:ACCESS_DEFAULTS,modes:ACCESS_MODES,settings:{contrast:{minimum_ratio:MIN_CONTRAST,distinguishability_ratio:DISTINGUISH_RATIO,light_background:LIGHT_BG,dark_background:DARK_BG,fill_text:FILL_TEXT},labels:L}};

  accessApply();  // before the menu draws: no flash

  return {colors:colors, access:access, key:ACCESS_KEY};
}

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
  // A public tab can still have a non-public sub-page (Selection Watch: CCG public, Playoffs Dev-only):
  // the sub-row item for this file decides then.
  function needsBar(cur, pageState, dev, file) {
    if (!dev) return false;
    var t = tabFor(cur);
    var state = t ? (t.state || "visible") : (pageState || "visible");
    if (state !== "visible") return true;
    if (!file) return false;
    for (var k in D.rows) {
      var items = D.rows[k].items || [];
      for (var i = 0; i < items.length; i++)
        if (itemMatches(items[i], file) && (items[i].state || "visible") !== "visible") return true;
    }
    return false;
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

  function devBar(nav, dev, file) {
    var old = document.querySelector(".n180-devbar");
    if (old) old.remove();
    if (!needsBar(nav.getAttribute("data-current") || "", nav.getAttribute("data-state"), dev, file)) return;
    nav.parentNode.insertBefore(el("div", {"class": "n180-devbar", role: "note"}, "DEV &mdash; not public"), nav);
  }

  // Sub-rows display directly below the page header, not between the main menu and the header
  // (CW, 2026-11-20). Pages keep writing the placeholders next to the main menu (site_common.menu_html);
  // this moves them after the <header> that follows them as a sibling, skipping only script/noscript/nav
  // and the dev bar. No such header: the row stays where it is. Order of several rows is kept.
  var SKIP = {SCRIPT: 1, NOSCRIPT: 1, NAV: 1, STYLE: 1, LINK: 1};
  function headerAfter(node) {
    for (var n = node.nextElementSibling; n; n = n.nextElementSibling) {
      var t = (n.tagName || "").toUpperCase();
      if (t === "HEADER") return n;
      if (!SKIP[t] && !(n.className && /(^|\s)n180-devbar(\s|$)/.test(n.className))) return null;
    }
    return null;
  }
  function placeRows(final) {
    var rows = document.querySelectorAll("nav.weeks.sub[data-row]:not(.n180-below)");
    var anchors = [];
    for (var i = 0; i < rows.length; i++) {
      var nav = rows[i], h = headerAfter(nav);
      if (!h) {
        if (final) nav.classList.remove("n180-wait");  // no header on this page: leave it in place
        else nav.classList.add("n180-wait");             // header not parsed yet: hide until it is
        continue;
      }
      var after = h;
      for (var k = 0; k < anchors.length; k++) if (anchors[k][0] === h) after = anchors[k][1];
      after.parentNode.insertBefore(nav, after.nextSibling);
      nav.classList.remove("n180-wait");
      nav.classList.add("n180-below");
      anchors.push([h, nav]);
    }
    return document.querySelectorAll("nav.weeks.sub.n180-wait").length === 0;
  }
  function watchRows() {
    if (placeRows(document.readyState !== "loading")) return;
    if (typeof MutationObserver === "undefined") return;
    var mo = new MutationObserver(function () { if (placeRows(false)) mo.disconnect(); });
    mo.observe(document.documentElement, {childList: true, subtree: true});
    document.addEventListener("DOMContentLoaded", function () { mo.disconnect(); placeRows(true); });
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
      devBar(n, dev, file);
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
             mainModel: mainModel, rowModel: rowModel, needsBar: needsBar, headerAfter: headerAfter};
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
  watchRows();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { render(false); });
})();
