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
  var OWNER_COLORS = /*__OWNER_ACCESSIBILITY_COLORS__*/null;
  var TOKENS_ID = "n180-tokens";
  var TOKENS_LIGHT = {"--good": OWNER_COLORS.light.positive, "--bad": OWNER_COLORS.light.negative,
    "--neutral": OWNER_COLORS.light.neutral, "--good-soft": "#e3f3e8", "--bad-soft": "#fbe4e1"};
  var TOKENS_DARK = {"--good": OWNER_COLORS.dark.positive, "--bad": OWNER_COLORS.dark.negative,
    "--neutral": OWNER_COLORS.dark.neutral, "--good-soft": "#173a2a", "--bad-soft": "#4a2024"};
  var TOKENS_BOTH = {"--good-fill": OWNER_COLORS.light.positive,
    "--bad-fill": OWNER_COLORS.light.negative, "--on-fill": "#ffffff"};
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
  var ACCESS_DEFAULTS = {mode:"standard",custom:{bad:OWNER_COLORS.light.negative,good:OWNER_COLORS.light.positive},motion:"system",emphasis:false};
  var ACCESS_MODES = {
    standard:{light:[OWNER_COLORS.light.positive,OWNER_COLORS.light.negative],dark:[OWNER_COLORS.dark.positive,OWNER_COLORS.dark.negative]},
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
    // Even owner-configured Standard fills must be legible with white labels.
    // Contrast-safe existing defaults retain their historical values.
    if(o.mode==="none") both={"--good-fill":"#3c3c3c","--bad-fill":"#656565"};
    else both={"--good-fill":accessibleHex(m.light[0],"#ffffff"),
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
    contrast:contrast,adjust:accessibleHex,defaults:ACCESS_DEFAULTS,modes:ACCESS_MODES};

  accessApply();  // before the menu draws: no flash

  return {colors:colors, access:access, key:ACCESS_KEY};
}
