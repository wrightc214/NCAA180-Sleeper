/* snapshot.js -- "Save image" for any part of any page (Chris, 2026-11-07: every collapsible section
 * gets an image button; part of the site design from here on).
 *
 *   NCAASnap.save({html, name, footer, title, stamp, whatif})   -> PNG via share sheet (phones) or download
 *     stamp:  {state: 'live'|'pregame'|'final'|'projection', time: Date, note}  -> label on top of the image
 *     whatif: ['Wyoming beats Boise State', ...]                                 -> WHAT-IF banner
 *   Labeling rule (Chris, 2026-11-07, site-wide): anything reacting to a live situation carries a
 *   timestamp and an "Unofficial" declaration; what-if images carry a clear WHAT-IF banner.
 *   NCAASnap.button(label)                       -> a small save-image <button> for a section header
 *
 * The HTML is drawn in a hidden 400px-wide frame that carries the page's styles and <html>/<body>
 * classes, so every image uses the phone layout whatever the device. html2canvas 1.4.1 (MIT, vendored
 * in assets/vendor) draws it at 2x. Colors written as color()/oklch()/lab()/color-mix() -- what Safari
 * reports in dark mode -- are converted to rgba first (html2canvas can't read them).
 */
(() => {
  const here = new URL('.', document.currentScript ? document.currentScript.src : location.href);
  const LIB = new URL('vendor/html2canvas-1.4.1.min.js', here).href;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  function plainColors(w, root) {
    const cv = w.document.createElement('canvas'); cv.width = cv.height = 1;
    const cx = cv.getContext('2d', {willReadFrequently: true});
    const rgb = v => {
      cx.clearRect(0, 0, 1, 1); cx.fillStyle = '#000'; cx.fillStyle = v; cx.fillRect(0, 0, 1, 1);
      const d = cx.getImageData(0, 0, 1, 1).data; return `rgba(${d[0]},${d[1]},${d[2]},${+(d[3] / 255).toFixed(3)})`;
    };
    const FN = /(?:color|oklch|oklab|lab|lch|color-mix)\((?:[^()]|\([^()]*\))*\)/g, BAD = /(?:color|oklch|oklab|lab|lch|color-mix)\(/;
    const props = ['color', 'background-color', 'border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color',
      'outline-color', 'text-decoration-color', 'column-rule-color', 'caret-color', 'fill', 'stroke', 'background-image', 'box-shadow', 'text-shadow'];
    for (const el of [root, ...root.querySelectorAll('*')]) {
      const cs = w.getComputedStyle(el);
      for (const p of props) { const v = cs.getPropertyValue(p); if (v && BAD.test(v)) el.style.setProperty(p, v.replace(FN, rgb), 'important'); }
    }
  }

  const ET = t => t.toLocaleString('en-US', {timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit'}) + ' ET';
  function labels(stamp, whatif) {
    let out = '';
    if (whatif && whatif.length)
      out += `<div class="snap-lab wi"><b>WHAT-IF</b> · not real results · ${esc(whatif.join(' · '))}</div>`;
    if (stamp) {
      const when = stamp.time ? ` · as of ${esc(ET(stamp.time))}` : '';
      const head = {live: 'LIVE · UNOFFICIAL', pregame: 'PREGAME PROJECTION · UNOFFICIAL',
        final: 'FINAL · UNOFFICIAL until stat corrections', projection: 'PROJECTION · UNOFFICIAL'}[stamp.state] || 'UNOFFICIAL';
      out += `<div class="snap-lab ${esc(stamp.state || '')}"><b>${head}</b>${when}${stamp.note ? ` · ${esc(stamp.note)}` : ''}</div>`;
    }
    return out;
  }

  async function render(html, footer, top = '') {
    const css = [...document.querySelectorAll('style,link[rel="stylesheet"]')].map(n => n.outerHTML).join('');
    const de = document.documentElement;
    const doc = `<!doctype html><html class="${esc(de.className)}"${de.dataset.theme ? ` data-theme="${esc(de.dataset.theme)}"` : ''}><head>` +
      `<meta charset="utf-8"><meta name="viewport" content="width=400"><base href="${esc(location.href)}">${css}` +
      `<script src="${esc(LIB)}"><\/script><style>body{margin:0;background:var(--bg,#fff)}.snapwrap{padding:12px 12px 6px;max-width:none}` +
      `.snap-foot{margin:10px 0 0;font:600 11px var(--sans,sans-serif);color:var(--mute,#667);text-align:center}` +
      `.snap-btn,.fold-bar{display:none!important}` +
      `.snap-lab{margin:0 0 8px;padding:6px 9px;border-radius:6px;font:600 11px var(--sans,sans-serif);letter-spacing:.02em;` +
      `background:#fff4d6;color:#5c4400;border:1px solid #e0b84a}.snap-lab b{font-weight:800}` +
      `.snap-lab.live b{color:#b42318}.snap-lab.wi{background:#4a1d96;color:#fff;border-color:#4a1d96;font-size:12px}</style></head>` +
      `<body class="${esc(document.body.className)}"><div class="wrap snapwrap" id="snap">${top}${html}` +
      `<p class="snap-foot">${esc(footer)}</p></div></body></html>`;
    const f = document.createElement('iframe');
    f.setAttribute('aria-hidden', 'true'); f.tabIndex = -1;
    f.style.cssText = 'position:fixed;left:-10000px;top:0;width:400px;height:4000px;border:0;visibility:hidden';
    document.body.append(f);
    try {
      await new Promise((ok, bad) => { f.onload = ok; f.onerror = bad; f.srcdoc = doc; });
      const w = f.contentWindow;
      for (let i = 0; i < 50 && !w.html2canvas; i++) await new Promise(r => setTimeout(r, 100));
      if (!w.html2canvas) throw new Error('image library did not load');
      await w.document.fonts.ready;
      await Promise.all([...w.document.images].map(im => im.complete ? 0 : new Promise(r => { im.onload = im.onerror = r; })));
      const el = w.document.getElementById('snap');
      plainColors(w, el);
      const canvas = await w.html2canvas(el, {scale: 2, windowWidth: 400, useCORS: true, logging: false,
        backgroundColor: w.getComputedStyle(w.document.body).backgroundColor});
      return await new Promise(r => canvas.toBlob(r, 'image/png'));
    } finally { f.remove(); }
  }

  async function save({html, name, footer, title, stamp, whatif}) {
    const blob = await render(html, footer ?? `${location.host}${location.pathname.replace(/[^/]*$/, '')}`, labels(stamp, whatif));
    const file = new File([blob], `${name || 'ncaa180'}.png`.replace(/[^\w .-]+/g, '').replace(/\s+/g, '-'), {type: 'image/png'});
    if (navigator.canShare && navigator.canShare({files: [file]})) {
      try { await navigator.share({files: [file], title: title || name}); } catch (e) { if (e?.name !== 'AbortError') throw e; }
      return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(file); a.download = file.name; document.body.append(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  function button(label) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'snap-btn'; b.title = 'Save image'; b.setAttribute('aria-label', `Save image: ${label}`);
    b.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 3a1 1 0 0 1 1 1v9.6l3.3-3.3a1 1 0 1 1 1.4 1.4l-5 5a1 1 0 0 1-1.4 0l-5-5a1 1 0 1 1 1.4-1.4l3.3 3.3V4a1 1 0 0 1 1-1zM5 19h14a1 1 0 1 1 0 2H5a1 1 0 1 1 0-2z"/></svg>';
    return b;
  }

  window.NCAASnap = {save, render, button, plainColors, labels};
})();
