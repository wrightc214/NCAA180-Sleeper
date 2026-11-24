"""5.12.2 browser check: every page follows the viewer's colour mode (manual / on demand, not in CI).

  python3 tests/color_modes_browser.py            all pages, 3 modes x 2 themes x 2 widths
  python3 tests/color_modes_browser.py --quick    1280 px only, no screenshots (numbers only)

For each page: stores the mode exactly as the Accessibility page does (localStorage "ncaa180.access"),
emulates light/dark, and at 390 and 1280 px:
  - screenshots the first meaningful-colour element's area -> work/color-modes/<page>.png (grid:
    rows standard / rg / by x light / dark, columns 390 / 1280)
  - fingerprints every element's colours; reports how many change between modes and fails if an
    element painted with team colours (inline style background) changes
  - measures text contrast of every element drawn in --good / --bad / --neutral against the
    background behind it (must be >= 4.5:1)
  - checks a stored "none" paints exactly like Standard
Then the Save-image check: NCAASnap.save() in rg mode must draw rg's --good.
Network-free: Sleeper/ESPN calls on the Games page are served from tests/fixtures; fonts are blocked.
Writes work/color-modes/report.json and prints a summary; exit 1 on any failure.
"""
import copy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "color-modes")
MODES = ["standard", "rg", "by"]
THEMES = ["light", "dark"]
WIDTHS = [390, 1280]

# name, url (relative to reports/), selector of a meaningful colour to centre the screenshot on
PAGES = [
    ("games", "scoreboard.html?league=1316899756005412864&week=6&roster=6", ".chance,.odds,.wp,.win-pct,main"),
    ("standings", "standings.html", ".up,.dn,td.mv"),
    ("poll", "poll.html", "td.mv .up,td.mv .dn"),
    ("poll-bots", "poll-bots.html", ".card td.b"),
    ("selection-watch", "selection-watch.html?preview=2025", ".sw-cut-line,.sw-good,.sw-bad"),
    ("transactions", "transactions.html", ".tx-surplus,.tx-grade strong[data-score],.tx-bar"),
    ("bowl-projection", "postseason.html", ".ot td,.hi,.lo,.mv.up"),
    ("bracket", "_bracket-fixture-e8-live.html", ".bk-g"),
    ("ccg-race", "ccg-race.html?preview=midweek", ".race li.in,.race li.cutline,.race"),
    ("champions-league", "cl-standings.html", ".cl-t tr.cut,.cl-pr.top,.cl-t"),
    ("dwight-fight", "dwight-fight-2023.html", ".bk-row.win,.bk-row.lose,.dw-champs,main"),
    ("guillotine", "special.html", ".gl-cut,.gl-r"),
    ("guillotine-live", "special.html", ".gl-cut"),  # week-13 live fixture: draws the cut line
    ("records", "records.html", ".card .v.up,.card .v.dn,.card"),
    ("weekly-report", "week-10.html", "td.mv .up,td.mv .dn,.up"),
    ("app", "app.html", ".status,main"),
]

PROBE_JS = r"""
(sel) => {
  const cs = getComputedStyle(document.documentElement);
  const tok = n => cs.getPropertyValue(n).trim().toLowerCase();
  const toRgb = c => { const x = document.createElement('i'); x.style.color = c; document.body.append(x);
    const v = getComputedStyle(x).color; x.remove(); return v; };
  const nums = c => (String(c).match(/[\d.]+/g) || []).map(Number);
  const lin = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = c => { const n = nums(c); return .2126 * lin(n[0]) + .7152 * lin(n[1]) + .0722 * lin(n[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); };
  const opaque = c => { const n = nums(c); return n.length >= 3 && (n.length < 4 || n[3] >= 0.99); };
  const bgOf = el => { for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none' && !/url\(/.test(s.backgroundImage)) return null;
      if (opaque(s.backgroundColor)) return s.backgroundColor; } return 'rgb(255, 255, 255)'; };
  const T = {good: toRgb(tok('--good')), bad: toRgb(tok('--bad')), neutral: toRgb(tok('--neutral'))};
  const all = [...document.querySelectorAll('body *')].filter(e => e.getClientRects().length);
  const finger = all.map(e => { const s = getComputedStyle(e);
    return [s.color, s.backgroundColor, s.borderTopColor, s.borderLeftColor, s.backgroundImage.slice(0, 120)].join('|'); });
  const teamish = all.map(e => { const st = e.getAttribute('style') || '';
    return /background/.test(st) && !e.hasAttribute('data-p') ? 1 : 0; });
  let min = 99, worst = null, n = 0;
  for (const e of all) {
    const s = getComputedStyle(e);
    const own = [...e.childNodes].some(c => c.nodeType === 3 && c.textContent.trim());
    if (!own) continue;
    const which = Object.keys(T).find(k => s.color === T[k]);
    if (!which) continue;
    const bg = bgOf(e); if (!bg) continue;
    n++; const r = ratio(s.color, bg);
    if (r < min) { min = r; worst = {token: which, text: e.textContent.trim().slice(0, 30), cls: e.className, color: s.color, bg}; }
  }
  const panel = toRgb(tok('--panel') || '#fff');
  const tokens = {good: tok('--good'), bad: tok('--bad'), neutral: tok('--neutral'), goodFill: tok('--good-fill'),
                  badFill: tok('--bad-fill'), panel: tok('--panel')};
  const tokenContrast = {good: ratio(T.good, panel), bad: ratio(T.bad, panel), neutral: ratio(T.neutral, panel),
    goodFill: ratio(toRgb(tok('--good-fill')), toRgb(tok('--on-fill') || '#fff')),
    badFill: ratio(toRgb(tok('--bad-fill')), toRgb(tok('--on-fill') || '#fff'))};
  const focus = sel.split(',').map(s => document.querySelector(s.trim())).find(Boolean);
  let y = 0; if (focus) { const r = focus.getBoundingClientRect(); y = Math.max(0, r.top + scrollY - 120); }
  return {finger, teamish, min: n ? min : null, n, worst, tokens, tokenContrast, focusY: y, focus: !!focus};
}
"""


def serve():
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def games_routes(page):
    """Sleeper/ESPN fixtures for the Games page (as tests/test_scoreboard_browser.py, live phase)."""
    fixture = json.load(open(os.path.join(ROOT, "tests/fixtures/scoreboard-week06.json")))
    meta = json.load(open(os.path.join(ROOT, "data/scoreboard/2026/players.json")))
    base = json.load(open(os.path.join(ROOT, "data/scoreboard/2026/week-06.json")))
    rosters = copy.deepcopy(fixture["rosters"])
    teams = {p["team"] for p in meta.values() if p["team"]} | {p["team"] for p in base["player_info"].values() if p["team"]}
    espn = {"season": {"year": 2026}, "week": {"number": 6}, "events": [{
        "id": "g", "date": "2026-10-20T00:15:00Z",
        "status": {"period": 4, "displayClock": "6:12", "type": {"state": "in", "completed": False}},
        "competitions": [{"competitors": [{"team": {"abbreviation": t}} for t in teams]}]}]}

    def api(route):
        u = route.request.url
        if "/matchups/" in u:
            d = rosters
        elif "/stats/" in u:
            d = fixture["stats"]
        elif u.endswith("/users"):
            d = [{"user_id": "u%s" % r["roster_id"], "display_name": "Manager %s" % r["roster_id"]} for r in rosters]
        elif u.endswith("/rosters"):
            d = [{"roster_id": r["roster_id"], "owner_id": "u%s" % r["roster_id"]} for r in rosters]
        else:
            d = {"scoring_settings": fixture["scoring"]}
        route.fulfill(content_type="application/json", body=json.dumps(d))
    page.route("https://api.sleeper.app/**", api)
    page.route("https://site.api.espn.com/**", lambda r: r.fulfill(content_type="application/json", body=json.dumps(espn)))


def guillotine_routes(page):
    """Live week-13 Guillotine fixture (as tests/test_guillotine_browser.py test_live_week)."""
    from test_guillotine_browser import _gd
    fixture = json.load(open(os.path.join(ROOT, "tests/fixtures/scoreboard-week06.json")))
    base6 = json.load(open(os.path.join(ROOT, "data/scoreboard/2026/week-06.json")))
    index = json.load(open(os.path.join(ROOT, "data/scoreboard/index.json")))
    week = 13
    idx = {**index, "week": week, "weeks": index["weeks"] + [13, 14]}
    base = {**base6, "week": week, "odds": [], "event": "postseason", "games": []}
    teams = sorted({p["team"] for p in base6["player_info"].values() if p["team"]})
    gd = _gd(index, live=True)
    state = {"period": 4, "displayClock": "5:00", "type": {"state": "in", "completed": False}}

    def api(route):
        u = route.request.url
        d = (copy.deepcopy(fixture["rosters"]) if "/matchups/" in u else fixture["stats"] if "/stats/" in u
             else {"scoring_settings": fixture["scoring"]})
        route.fulfill(content_type="application/json", body=json.dumps(d))
    espn = {"season": {"year": 2026}, "week": {"number": week}, "events": [{"id": "0", "date": "2026-12-08T01:15:00Z",
            "status": state, "competitions": [{"competitors": [{"team": {"abbreviation": x}} for x in teams]}]}]}
    page.route("https://api.sleeper.app/**", api)
    page.route("https://site.api.espn.com/**", lambda r: r.fulfill(content_type="application/json", body=json.dumps(espn)))
    page.route("**/scoreboard/index.json", lambda r: r.fulfill(content_type="application/json", body=json.dumps(idx)))
    page.route("**/2026/guillotine.json", lambda r: r.fulfill(content_type="application/json", body=json.dumps(gd)))
    page.route(f"**/week-{week:02d}.json", lambda r: r.fulfill(content_type="application/json", body=json.dumps(base)))


def main(quick=False):
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageDraw
    os.makedirs(OUT, exist_ok=True)
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    cwd = os.getcwd()
    import bracket_fixture
    fixture_page = bracket_fixture.write_page("e8-live", name="_bracket-fixture-e8-live.html")
    os.chdir(cwd)
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_port}/reports/"
    report, fails = {}, []
    widths = [1280] if quick else WIDTHS
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            for name, url, sel in PAGES:
                shots, rec = {}, report.setdefault(name, {})
                for theme in THEMES:
                    for width in widths:
                        fps = {}
                        for mode in MODES + ["none"]:
                            ctx = br.new_context(viewport={"width": width, "height": 900 if width > 500 else 844},
                                                 color_scheme=theme, service_workers="block")
                            ctx.add_init_script("try{localStorage.setItem('ncaa180.access',JSON.stringify({mode:%s}));"
                                                "localStorage.setItem('ncaa180.dev','1');"
                                                "sessionStorage.setItem('ncaa180.push.snooze','1')}catch(e){}" % json.dumps(mode))
                            pg = ctx.new_page()
                            pg.route("https://fonts.googleapis.com/**", lambda r: r.abort())
                            pg.route("https://fonts.gstatic.com/**", lambda r: r.abort())
                            if name == "games":
                                games_routes(pg)
                            if name == "guillotine-live":
                                guillotine_routes(pg)
                            try:
                                pg.goto(base + url, wait_until="load", timeout=30000)
                                if url.startswith("_bracket-fixture"):  # fixture page has no menu: add the tokens
                                    pg.add_script_tag(url=base + "assets/menu.js")
                                pg.wait_for_timeout(3000 if name == "guillotine-live" else 1500)
                                res = pg.evaluate(PROBE_JS, sel)
                            except Exception as e:  # noqa: BLE001
                                fails.append(f"{name} {theme} {width} {mode}: load error {e}")
                                ctx.close()
                                continue
                            fps[mode] = res
                            key = f"{theme}-{width}-{mode}"
                            rec[key] = {k: res[k] for k in ("min", "n", "worst", "tokens", "tokenContrast", "focus")}
                            if res["min"] is not None and res["min"] < 4.5 and mode != "none":
                                fails.append(f"{name} {key}: text on a token colour {res['min']:.2f}:1 {res['worst']}")
                            for k, v in res["tokenContrast"].items():
                                if v < 4.5 and mode != "none":
                                    fails.append(f"{name} {key}: token {k} contrast {v:.2f}:1")
                            if not quick and mode != "none":
                                pg.evaluate(f"window.scrollTo(0,{res['focusY']})")
                                pg.wait_for_timeout(200)
                                shots[(mode, theme, width)] = Image.open(io.BytesIO(pg.screenshot()))
                            ctx.close()
                        if "standard" not in fps:
                            continue
                        s = fps["standard"]
                        for mode in ("rg", "by", "none"):
                            m = fps.get(mode)
                            if not m or len(m["finger"]) != len(s["finger"]):
                                rec[f"{theme}-{width}-{mode}-changed"] = "element count differs (page content varies)"
                                continue
                            changed = [i for i, (a, b) in enumerate(zip(s["finger"], m["finger"])) if a != b]
                            team = [i for i in changed if s["teamish"][i] and m["teamish"][i]]
                            rec[f"{theme}-{width}-{mode}-changed"] = len(changed)
                            if mode == "none" and changed:
                                fails.append(f"{name} {theme} {width}: stored none differs from Standard on {len(changed)} elements")
                            if mode != "none" and team:
                                fails.append(f"{name} {theme} {width} {mode}: {len(team)} team-coloured elements changed colour")
                if shots:
                    grid(name, shots, Image, ImageDraw)
            # Saved image in rg mode carries rg colours.
            ctx = br.new_context(viewport={"width": 1280, "height": 900}, color_scheme="light", accept_downloads=True)
            ctx.add_init_script("localStorage.setItem('ncaa180.access',JSON.stringify({mode:'rg'}))")
            pg = ctx.new_page()
            pg.route("https://fonts.googleapis.com/**", lambda r: r.abort())
            pg.goto(base + "ccg-race.html?preview=midweek", wait_until="load")
            pg.wait_for_timeout(800)
            with pg.expect_download() as dl:
                pg.evaluate("NCAASnap.save({html:'<div style=\"height:120px;background:var(--good)\"></div>"
                            "<div style=\"height:120px;background:var(--bad)\"></div>',name:'rg-check'})")
            path = os.path.join(OUT, "save-image-rg.png")
            dl.value.save_as(path)
            want = pg.evaluate("[getComputedStyle(document.documentElement).getPropertyValue('--good').trim(),"
                               "getComputedStyle(document.documentElement).getPropertyValue('--bad').trim()]")
            im = Image.open(path).convert("RGB")
            px = [im.getpixel((im.width // 2, y)) for y in range(0, im.height, 4)]
            hexes = {"#%02x%02x%02x" % p for p in px}
            ok = all(w.lower() in hexes for w in want)
            report["save-image-rg"] = {"tokens": want, "found": ok, "file": path}
            if not ok:
                fails.append(f"Save-image in rg: {want} not found in the PNG")
            ctx.close()
            br.close()
    finally:
        srv.shutdown()
        os.remove(os.path.join(ROOT, "reports", fixture_page))
    json.dump(report, open(os.path.join(OUT, "report.json"), "w"), indent=1)
    for name in report:
        r = report[name]
        if name == "save-image-rg":
            print(f"save-image-rg: rg --good/--bad in PNG: {r['found']}")
            continue
        mins = [v["min"] for k, v in r.items() if isinstance(v, dict) and v.get("min") is not None and not k.endswith("none")]
        ch = {k: v for k, v in r.items() if k.endswith("-changed")}
        print(f"{name:17s} min text contrast {min(mins) if mins else float('nan'):.2f} "
              f"| changed vs Standard: " + ", ".join(f"{k.replace('-changed', '')}={v}" for k, v in ch.items()))
    print("\n".join(fails) or "OK: no failures")
    return 1 if fails else 0


def grid(name, shots, Image, ImageDraw):
    cell_w = {390: 390, 1280: 640}
    rows = [(m, t) for t in THEMES for m in MODES]
    H, lab = 520, 22
    W = sum(cell_w.values()) + 110
    g = Image.new("RGB", (W, lab + H * len(rows)), "white")
    d = ImageDraw.Draw(g)
    x0 = 110
    for w in WIDTHS:
        d.text((x0 + 4, 4), f"{w} px", fill="black")
        x0 += cell_w[w]
    for r, (mode, theme) in enumerate(rows):
        y = lab + r * H
        d.text((6, y + 6), f"{mode}\n{theme}", fill="black")
        x = 110
        for w in WIDTHS:
            im = shots.get((mode, theme, w))
            if im:
                im = im.crop((0, 0, im.width, min(im.height, int(H * im.width / cell_w[w]))))
                im = im.resize((cell_w[w], int(im.height * cell_w[w] / im.width)))
                g.paste(im, (x, y))
            x += cell_w[w]
        d.line([(0, y), (W, y)], fill="#999")
    g.save(os.path.join(OUT, f"{name}.png"), optimize=True)


if __name__ == "__main__":
    sys.exit(main(quick="--quick" in sys.argv))
