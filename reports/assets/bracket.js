/* bracket.js -- the bracket component's browser side (Chris, 2026-11-20, task 5.13; markup from
 * scripts/bracket.py).
 *
 * Phone (ESPN bracket-app model): one round in focus, packed top to bottom; the next round peeks at
 * the right edge with each game at the midpoint of its two feeders. Swipe left/right, tap a round tab
 * or press Left/Right (bracket focused) to move one round. The track slides and the new round
 * re-packs (~350 ms; instant with prefers-reduced-motion or the site's Reduce motion setting). Vertical scrolling stays native
 * (touch-action: pan-y).
 *
 * Save image: one button on the Bracket section. Choices come from the <template class="bk-x">
 * images scripts/bracket.py writes (This round, each quad, Elite 8 & beyond, Champion) plus the
 * Full bracket (the desktop board itself, at 2x or 1.5x). Drawn by NCAASnap (assets/snapshot.js).
 * html2canvas can't draw CSS filter, so dimmed losers use precomputed colours (data-xbg/-xfg) and
 * grayscaled logo copies in the image.
 */
(() => {
  const PHONE = '(max-width: 719px)';
  const REDUCED = '(prefers-reduced-motion: reduce)';
  const LEFT = 14, PEEK = 60, GAP = 12, VGAP = 12, HQ = 34, TOP = 8;
  const mm = q => window.matchMedia ? window.matchMedia(q).matches : false;
  const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  // ------------------------------------------------------------------ phone
  function phone(root) {
    const ph = root.querySelector('.bk-phone');
    if (!ph) return null;
    const view = ph.querySelector('.bk-view'), track = ph.querySelector('.bk-track');
    const tabs = [...ph.querySelectorAll('.bk-tab')];
    let ready = false;
    const cols = [...ph.querySelectorAll('.bk-col')];
    const qheads = [...ph.querySelectorAll('.bk-pq')];
    const qr = Number(ph.dataset.quadRound), nq = Number(ph.dataset.quads);
    const last = cols.length - 1;
    // reduced motion = the OS setting or the site's own Reduce motion setting (both shorten the CSS transition)
    const still = () => mm(REDUCED) || (parseFloat(getComputedStyle(track).transitionDuration) || 0) < 0.05;
    const cards = cols.map(c => [...c.querySelectorAll(':scope>.bk-card')]);
    const champ = cols[last]?.querySelector(':scope>.bk-champ');
    // open on the round being played: the first with a live / upcoming game, else the last
    let f = cards.findIndex(cs => cs.some(c => c.classList.contains('st-live') || c.classList.contains('st-upcoming')));
    if (f < 0) f = cards.every(cs => cs.every(c => c.classList.contains('st-tbd'))) ? 0 : last;

    function layout() {
      if (!ph.offsetParent) return;  // desktop: phone view hidden
      // narrow phones (<360px) give the focused round more room: smaller margin and peek
      const W = view.clientWidth, nar = W < 340, L = nar ? 10 : LEFT, P = nar ? 40 : PEEK;
      const colW = Math.max(200, W - L - P - GAP), COL = colW + GAP;
      cols.forEach((c, r) => { c.style.left = `${L + r * COL}px`; c.style.width = `${colW}px`;
        for (const x of c.children) x.style.width = `${colW}px`; });
      qheads.forEach(q => { q.style.width = `${colW}px`; });
      const h = cards.map(cs => cs.map(c => c.offsetHeight));
      const champH = champ ? champ.offsetHeight : 0;
      const tops = [];
      let y = TOP;
      if (f === last && champ) { champ.style.top = `${y}px`; y += champH + VGAP; }
      const per = (qr >= 0 && f <= qr && nq) ? cards[f].length / nq : 0;
      const qtops = [];
      tops[f] = cards[f].map((c, i) => {
        if (per && i % per === 0) { qtops.push(y); y += HQ; }
        const t = y; y += h[f][i] + VGAP; return t;
      });
      for (let r = f + 1; r <= last; r++)
        tops[r] = cards[r].map((c, i) => {
          const a = tops[r - 1][2 * i] + h[r - 1][2 * i] / 2, b = tops[r - 1][2 * i + 1] + h[r - 1][2 * i + 1] / 2;
          return (a + b) / 2 - h[r][i] / 2;
        });
      for (let r = f - 1; r >= 0; r--)
        tops[r] = cards[r].map((c, i) => tops[r + 1][i >> 1] + h[r + 1][i >> 1] / 2 + (i % 2 ? VGAP / 2 : -VGAP / 2 - h[r][i]));
      cards.forEach((cs, r) => cs.forEach((c, i) => { c.style.top = `${tops[r][i]}px`; }));
      if (champ && f !== last) champ.style.top = `${tops[last][0] - champH - VGAP}px`;
      if (champ) champ.style.opacity = f === last ? '1' : '0';
      qheads.forEach((q, k) => {
        const on = per && qtops[k] !== undefined;
        q.style.left = `${L + f * COL}px`; q.style.top = `${on ? qtops[k] : 0}px`;
        q.style.opacity = on ? '1' : '0'; q.style.visibility = on ? 'visible' : 'hidden';
      });
      // only the focused round and the peek are visible; everything else is off to the sides
      cols.forEach((c, r) => {
        const on = r === f, peek = r === f + 1;
        c.style.opacity = on ? '1' : peek ? '.55' : '0';
        c.setAttribute('aria-hidden', on ? 'false' : 'true');
        for (const a of c.querySelectorAll('a')) a.tabIndex = on ? 0 : -1;
      });
      let bottom = Math.max(...tops[f].map((t, i) => t + h[f][i]), f === last ? champH : 0);
      if (f < last) bottom = Math.max(bottom, ...tops[f + 1].map((t, i) => t + h[f + 1][i]));
      view.style.height = `${Math.ceil(bottom + 16)}px`;
      track.style.transform = `translateX(${-f * COL}px)`;
      tabs.forEach((t, r) => t.setAttribute('aria-current', r === f ? 'true' : 'false'));
      // centre the focused tab; the strip stays a native scroller so every tab can be reached
      const strip = ph.querySelector('.bk-tabs'), tt = tabs[f];
      const off = Math.max(0, Math.min(strip.scrollWidth - strip.clientWidth, tt.offsetLeft + tt.offsetWidth / 2 - strip.clientWidth / 2));
      if (strip.scrollTo) strip.scrollTo({left: off, behavior: (still() || !ready) ? 'auto' : 'smooth'}); else strip.scrollLeft = off;
      ph.dataset.focus = String(f);
    }

    function go(n) {
      const to = Math.max(0, Math.min(last, n));
      if (to === f) return;
      f = to; layout();
      const top = ph.getBoundingClientRect().top;
      if (top < 0) ph.scrollIntoView({block: 'start', behavior: still() ? 'auto' : 'smooth'});
    }

    tabs.forEach((t, r) => t.addEventListener('click', () => go(r)));
    ph.addEventListener('keydown', ev => {
      if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
      if (ev.target.closest && ev.target.closest('input,select,textarea')) return;
      ev.preventDefault(); go(f + (ev.key === 'ArrowRight' ? 1 : -1));
    });
    // swipe: pointer events, horizontal intent only (vertical scroll stays native via touch-action:pan-y)
    for (const x of view.querySelectorAll('a,img')) x.draggable = false;  // a link drag would cancel the swipe
    let sx = null, sy = 0, swiped = false;
    view.addEventListener('pointerdown', ev => { if (ev.isPrimary) { sx = ev.clientX; sy = ev.clientY; swiped = false; } });
    view.addEventListener('pointerup', ev => {
      if (sx === null) return;
      const dx = ev.clientX - sx, dy = ev.clientY - sy; sx = null;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.2) { swiped = true; go(f + (dx < 0 ? 1 : -1)); }
    });
    view.addEventListener('pointercancel', () => { sx = null; });
    // a swipe is not a tap; a tap on the peeking round moves to it instead of opening the game
    view.addEventListener('click', ev => {
      const card = ev.target.closest('.bk-card');
      if (swiped) { ev.preventDefault(); swiped = false; return; }
      if (card && Number(card.dataset.r) !== f) { ev.preventDefault(); go(Number(card.dataset.r)); }
    }, true);
    if (window.ResizeObserver) new ResizeObserver(() => layout()).observe(view);
    else window.addEventListener('resize', layout);
    for (const im of ph.querySelectorAll('img')) if (!im.complete) im.addEventListener('load', layout, {once: true});
    layout();
    ready = true;
    return {get focus() { return f; }, go, layout};
  }

  // ------------------------------------------------------------------ export
  async function grayLogo(src, g) {
    const im = new Image();
    im.src = src;
    await im.decode();
    const c = document.createElement('canvas');
    c.width = im.naturalWidth; c.height = im.naturalHeight;
    const x = c.getContext('2d', {willReadFrequently: true});
    x.drawImage(im, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height), p = d.data, a = 1 - g;
    for (let i = 0; i < p.length; i += 4) {  // CSS grayscale(g) matrix
      const r = p[i], gg = p[i + 1], b = p[i + 2];
      p[i] = (0.2126 + 0.7874 * a) * r + (0.7152 - 0.7152 * a) * gg + (0.0722 - 0.0722 * a) * b;
      p[i + 1] = (0.2126 - 0.2126 * a) * r + (0.7152 + 0.2848 * a) * gg + (0.0722 - 0.0722 * a) * b;
      p[i + 2] = (0.2126 - 0.2126 * a) * r + (0.7152 - 0.7152 * a) * gg + (0.0722 + 0.9278 * a) * b;
    }
    x.putImageData(d, 0, 0);
    return c.toDataURL('image/png');
  }

  // dimmed losers without CSS filter (html2canvas can't draw it): precomputed colours + grey logos
  async function forImage(el, gray) {
    const cache = new Map();
    for (const row of el.querySelectorAll('.bk-row.lose')) {
      row.style.background = row.dataset.xbg; row.style.color = row.dataset.xfg; row.style.filter = 'none';
      for (const im of row.querySelectorAll('img')) {
        const src = im.src;
        if (!cache.has(src)) cache.set(src, grayLogo(src, gray).catch(() => src));
        im.src = await cache.get(src);
      }
    }
    for (const a of el.querySelectorAll('a')) a.removeAttribute('href');
    return el;
  }

  const ICON = {
    desktop: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M3 4h18a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1h-7v2h3v2H7v-2h3v-2H3a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1zm1 2v9h16V6z"/></svg>',
    phone: '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm0 3v13h8V5zm3 14.5a1 1 0 1 0 2 0 1 1 0 0 0-2 0z"/></svg>',
  };

  function menu(root, ph) {
    const S = window.NCAASnap, sec = root.closest('section');
    if (!S || !sec) return;
    const xs = root.querySelector('.bk-xs'), meta = JSON.parse(xs.dataset.meta || '{}');
    const T = [...xs.querySelectorAll('template.bk-x')];
    const board = root.querySelector('.bk-desk .bk-board');
    const dimGray = Number(getComputedStyle(board).getPropertyValue('--bk-gray')) || 0.6;
    const foot = root.dataset.foot || '';
    const btn = S.button('Bracket');
    sec.append(btn);
    sec.style.position = sec.style.position || 'relative';
    let panel = null;
    const close = () => { if (panel) { panel.remove(); panel = null; btn.setAttribute('aria-expanded', 'false'); btn.focus(); } };
    btn.setAttribute('aria-haspopup', 'dialog'); btn.setAttribute('aria-expanded', 'false');
    btn.addEventListener('keydown', ev => ev.stopPropagation());
    btn.addEventListener('click', ev => {
      ev.stopPropagation();
      if (panel) { close(); return; }
      const focus = ph ? ph.focus : 0;
      const rnd = T.find(t => t.dataset.key === `round-${focus}`);
      const opts = [];
      if (rnd) opts.push({key: rnd.dataset.key, label: `This round <small>${rnd.content.querySelector('.bk-h1')?.textContent || ''}</small>`});
      for (const t of T) if (t.dataset.group === 'quad') opts.push({key: t.dataset.key, label: t.dataset.label});
      const e8 = T.find(t => t.dataset.group === 'e8');
      if (e8) opts.push({key: 'e8', label: `Elite 8 &amp; beyond${e8.dataset.note ? ` <small>${e8.dataset.note}</small>` : ''}`, off: !!e8.dataset.note});
      if (T.some(t => t.dataset.group === 'champ')) opts.push({key: 'champ', label: 'Champion'});
      opts.push({key: 'full', label: 'Full bracket'});
      const def = mm(PHONE) && rnd ? rnd.dataset.key : 'full';
      const ios = isIOS();
      panel = document.createElement('div');
      panel.className = 'bk-menu'; panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-label', 'Save bracket image');
      panel.innerHTML = `<fieldset><legend>Save image</legend>${opts.map(o => `<label class="${o.off ? 'off' : ''}"><input type="radio" name="bk-what" value="${o.key}"${o.off ? ' disabled' : ''}${o.key === def ? ' checked' : ''}><span>${o.label}</span></label>`).join('')}</fieldset>` +
        `<fieldset class="bk-sz"><legend>Full bracket size</legend>` +
        `<label><input type="radio" name="bk-size" value="2"${ios ? '' : ' checked'}>${ICON.desktop}<span>2× <small>Recommended for Android &amp; desktop</small></span></label>` +
        `<label><input type="radio" name="bk-size" value="1.5"${ios ? ' checked' : ''}>${ICON.phone}<span>1.5× <small>Recommended for iPhone</small></span></label></fieldset>` +
        `<div class="bk-do"><button type="button" class="cancel">Cancel</button><button type="button" class="go">Save</button></div><p class="bk-err" role="status"></p>`;
      sec.append(panel);
      btn.setAttribute('aria-expanded', 'true');
      const sz = panel.querySelector('.bk-sz');
      const sync = () => { sz.hidden = panel.querySelector('input[name=bk-what]:checked')?.value !== 'full'; };
      panel.addEventListener('change', sync); sync();
      panel.addEventListener('click', e2 => e2.stopPropagation());
      panel.addEventListener('keydown', e2 => { e2.stopPropagation(); if (e2.key === 'Escape') close(); });
      panel.querySelector('.cancel').addEventListener('click', close);
      panel.querySelector('input:checked')?.focus();
      panel.querySelector('.go').addEventListener('click', async () => {
        const what = panel.querySelector('input[name=bk-what]:checked')?.value;
        const scale = Number(panel.querySelector('input[name=bk-size]:checked')?.value || 2);
        const go = panel.querySelector('.go'), err = panel.querySelector('.bk-err');
        go.disabled = true; btn.classList.add('busy'); err.textContent = 'Making image…';
        try {
          await save(what, scale);
          close();
        } catch (x) {
          err.textContent = 'Image could not be made: ' + (x.message || x) + (what === 'full' && scale > 1.5 ? ' Try 1.5×.' : '');
          console.error(x);
        } finally { go.disabled = false; btn.classList.remove('busy'); }
      });
    });
    document.addEventListener('click', ev => { if (panel && !panel.contains(ev.target) && ev.target !== btn) close(); });

    async function save(what, scale) {
      const host = document.createElement('div');
      host.className = 'bk';
      let w, file, live;
      if (what === 'full') {
        const b = board.cloneNode(true);
        b.querySelector('.bk-foot')?.remove();
        host.append(b); w = parseInt(board.style.width, 10); file = meta.full; live = meta.live;
      } else {
        const t = T.find(x => x.dataset.key === what);
        host.append(t.content.cloneNode(true));
        w = Number(t.dataset.w); file = t.dataset.file; live = t.dataset.live === '1'; scale = Number(t.dataset.scale) || 2;
      }
      // the export copy lives off-screen while logos are converted
      host.style.cssText = 'position:fixed;left:-20000px;top:0';
      document.body.append(host);
      try { await forImage(host, dimGray); } finally { host.remove(); host.removeAttribute('style'); }
      const stamp = live ? {state: 'live', time: new Date()} : null;
      await S.save({html: host.outerHTML, name: file, footer: foot, title: file, stamp, width: w + 24, scale});
      return file;
    }
    root.bkSave = save;  // for tests
  }

  function init() {
    for (const root of document.querySelectorAll('.bk')) {
      if (root.dataset.ready) continue;
      root.dataset.ready = '1';
      const ph = phone(root);
      root.bkPhone = ph;
      menu(root, ph);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  window.NCAABracket = {init};
})();
