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
  var SETTINGS = /*__OWNER_ACCESSIBILITY_COLORS__*/null;
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
  // "No colour" (5.12.2, Chris): shown disabled on the Accessibility page until its non-colour cues
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
