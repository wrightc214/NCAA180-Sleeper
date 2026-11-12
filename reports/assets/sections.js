/* sections.js -- the site's standard section treatment (Chris, 2026-11-08: every page gets collapsible
 * sections, a Collapse all / Expand all button and a save-image button on each section).
 *
 * Works on any page: every <section> inside .wrap whose first-level child is an <h2> becomes foldable
 * (tap the title) and gets a save-image button (needs assets/snapshot.js loaded first). Folds persist
 * per page in this browser; pages open expanded when nothing is stored, so headless screenshots
 * capture full sections. Optional <body> data attributes:
 *   data-snap-foot   image footer (default: site address)
 *   data-snap-tag    file-name suffix
 *   data-snap-state  live | pregame | final | projection -> labeled image (with data-snap-time ISO)
 * Sections with data-nosnap get no image button; data-nofold stays open.
 */
(() => {
  const css = `section.fold>h2{cursor:pointer;position:relative;padding-right:56px}
section.fold>h2::after{content:"\\25BE";position:absolute;right:0;top:2px;font-size:14px;opacity:.7}
section.fold.closed>h2::after{content:"\\25B8"}
section.fold.closed>:not(h2):not(.snap-btn){display:none!important}
section.fold{position:relative}
.fold-bar{display:flex;justify-content:flex-end;margin:0 0 8px}
.fold-all{font:700 12px var(--sans,sans-serif);padding:5px 10px;border:1px solid var(--line,#ccd);border-radius:6px;background:var(--panel,#fff);color:inherit;cursor:pointer}
section.fold>.snap-btn{position:absolute;top:2px;right:22px;display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;padding:0;border:1px solid var(--line,#ccd);border-radius:6px;background:var(--panel,#fff);color:var(--mute,#667);cursor:pointer}
section.card.fold>.snap-btn{top:12px;right:30px}
.snap-btn:hover{color:inherit}.snap-btn.busy{opacity:.5;cursor:progress}.snap-btn:focus-visible{outline:2px solid #38638b;outline-offset:2px}`;
  const st = document.createElement('style'); st.textContent = css; document.head.append(st);

  const secs = [...document.querySelectorAll('section')].filter(s => s.querySelector(':scope>h2') && !s.parentElement.closest('section'));
  if (!secs.length) return;
  const slug = t => t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'section';
  const used = new Set();
  secs.forEach((s, i) => {
    if (!s.id) { let id = slug(s.querySelector(':scope>h2').childNodes[0]?.textContent || ''); while (used.has(id) || document.getElementById(id)) id += '-' + i; s.id = id; }
    used.add(s.id);
  });

  const K = 'fold:' + location.pathname.replace(/[^/]*\/(?=[^/]*$)/, '');
  const get = () => { try { return new Set(JSON.parse(localStorage.getItem(K) || '[]')); } catch (e) { return new Set(); } };
  const put = f => { try { localStorage.setItem(K, JSON.stringify([...f])); } catch (e) {} };
  const folds = secs.filter(s => !s.hasAttribute('data-nofold'));
  const f = get();
  const set = (s, closed) => { s.classList.toggle('closed', closed); s.querySelector(':scope>h2').setAttribute('aria-expanded', String(!closed)); };
  folds.forEach(s => {
    s.classList.add('fold'); set(s, f.has(s.id));
    const h = s.querySelector(':scope>h2'); h.setAttribute('role', 'button'); h.tabIndex = 0;
    const t = e => { if (e.target.closest('a,button,select,input')) return; set(s, !s.classList.contains('closed'));
      const g = get(); s.classList.contains('closed') ? g.add(s.id) : g.delete(s.id); put(g); lab(); };
    h.addEventListener('click', t);
    h.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); t(e); } });
  });
  const bar = document.createElement('div'); bar.className = 'fold-bar';
  const b = document.createElement('button'); b.type = 'button'; b.className = 'fold-all'; bar.append(b);
  const lab = () => { b.textContent = folds.some(s => !s.classList.contains('closed')) ? 'Collapse all' : 'Expand all'; };
  if (folds.length > 1) { folds[0].before(bar); lab(); }
  b.addEventListener('click', () => { const close = folds.some(s => !s.classList.contains('closed')); const g = get();
    folds.forEach(s => { set(s, close); close ? g.add(s.id) : g.delete(s.id); }); put(g); lab(); });

  const S = window.NCAASnap; if (!S) return;
  const d = document.body.dataset;
  const stamp = d.snapState ? {state: d.snapState, time: d.snapTime ? new Date(d.snapTime) : new Date()} : null;
  const page = (document.title || 'ncaa180').replace(/\s*[·|]\s*/g, ' ').trim();
  secs.filter(s => !s.hasAttribute('data-nosnap')).forEach(s => {
    const title = (s.querySelector(':scope>h2').childNodes[0]?.textContent || s.id).trim();
    const btn = S.button(title); s.append(btn);
    btn.addEventListener('keydown', e => e.stopPropagation());
    btn.addEventListener('click', async e => {
      e.stopPropagation(); btn.disabled = true; btn.classList.add('busy');
      try {
        const cl = s.cloneNode(true); cl.classList.remove('closed', 'fold');
        cl.querySelectorAll('.snap-btn,[data-nosnap-part]').forEach(x => x.remove());
        // keep what the reader filtered out of view hidden in the image too
        const live = [...s.querySelectorAll('*')], copy = [...cl.querySelectorAll('*')];
        live.forEach((x, i) => { if (x.hidden && copy[i]) copy[i].hidden = true; });
        cl.querySelectorAll('.tools').forEach(x => x.remove());
        // long tables: the first 25 rows of what is on screen (filters and sort kept)
        cl.querySelectorAll('tbody').forEach(tb => { const rows = [...tb.rows].filter(r => !r.hidden);
          if (rows.length > 30) { rows.slice(25).forEach(r => r.remove()); const n = document.createElement('p'); n.className = 'note';
            n.textContent = `Showing 25 of ${rows.length} rows in the current view.`; tb.closest('table').after(n); } });
        // wide tables: widen the image frame to fit every column (phone width otherwise)
        const wide = Math.max(0, ...[...s.querySelectorAll('table')].map(t => t.scrollWidth));
        const width = Math.min(1100, Math.max(400, wide + 56));
        await S.save({width, html: cl.outerHTML, name: [page, title, d.snapTag].filter(Boolean).join(' '), footer: d.snapFoot || undefined, title, stamp});
      } catch (err) { btn.title = 'Image could not be made (' + (err && err.message || err) + ')'; console.error(err); }
      finally { btn.disabled = false; btn.classList.remove('busy'); }
    });
  });
})();
