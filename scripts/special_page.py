"""
special_page.py -- reports/special.html, the Special Events tab (Chris, 2026-11-14).

One sub-tab per non-standard event (config/nav.json rows.special). Today: The Guillotine
(scripts/guillotine.py writes its data; reports/assets/guillotine.js draws it live in the browser).
Static shell only: the page reads data/scoreboard/<season>/guillotine.json, the week's frozen
projections, Sleeper and ESPN at view time. Rebuild after a design change; data changes need nothing.
CWD = repo root.
"""
import glob
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
import trophies as TR  # noqa: E402
from site_common import menu_html, page_head  # noqa: E402

CSS = """
.gwrap{max-width:900px}
.gl-hdr{padding-bottom:10px;border-bottom:3px solid var(--accent);margin-bottom:6px}.gl-title{margin:8px 0 0;line-height:0}.gl-title img{display:block;width:100%;max-width:640px;height:auto}
.tools{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:10px 0}
.tools button{font:600 14px var(--num);padding:9px 12px;border:1px solid var(--line);border-radius:5px;background:var(--panel);color:var(--ink);cursor:pointer}
.tools #updated{font-size:13px;color:var(--mute)}
#error{padding:12px;background:#fff0d7;color:#722a00;border:1px solid #aa6d15;border-radius:5px}
.gl-champ{display:flex;align-items:center;gap:14px;background:var(--panel);border:2px solid var(--gold);border-radius:10px;padding:12px 16px;margin:10px 0}
.gl-champ{flex-wrap:wrap}.gl-champ img{width:min(320px,100%);height:auto}.gl-cname{display:flex;align-items:center;gap:8px;font:800 24px var(--num)}
.gl-head{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:10px 0 6px}
.gl-k{display:flex;flex-direction:column;align-items:center;text-align:center}.gl-k b{font:800 26px/1.1 var(--num)}
.gl-k span{font:600 10px var(--body);text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}.gl-k.proj b{color:var(--accent)}
.gl-state{font:600 13px var(--body);color:var(--mute);margin:6px 2px}
.gl-table{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.gl-h,.gl-r{display:grid;gap:6px;align-items:center;padding:6px 10px}
.live-t .gl-h,.live-t .gl-r{grid-template-columns:22px minmax(0,1fr) 62px 54px 44px 58px}
.fz-t .gl-h,.fz-t .gl-r{grid-template-columns:22px minmax(0,1fr) 62px 76px}
.out-t .gl-h,.out-t .gl-r{grid-template-columns:22px minmax(0,1fr) 92px 62px}
.gl-h{font:600 10px var(--body);text-transform:uppercase;letter-spacing:.04em;color:var(--mute);border-bottom:1px solid var(--line)}
.gl-h span:nth-child(n+3){text-align:right}
.gl-r{border-top:1px solid var(--line);min-height:34px}.gl-r:first-of-type{border-top:0}
.gl-t{min-width:0;font-size:14px;line-height:1.15;overflow-wrap:anywhere}.gl-t small{display:block;font-size:11px;color:var(--mute)}
.gl-n,.gl-w{text-align:right;font:600 15px var(--num);font-variant-numeric:tabular-nums}
.gl-n.pj,.gl-n.mn,.gl-w{color:var(--mute);font-weight:500}.gl-n.od{font-weight:800}
.gl-r.live .gl-n.sc{font-weight:900}.gl-r.bubble{background:var(--bad-soft)}
.gl-r.mine{box-shadow:inset 4px 0 0 var(--accent)}.gl-r.gone{opacity:.5}
.gl-cut{position:relative;height:22px;border-top:2px dashed var(--bad);margin:0 6px}
.gl-cut span{position:absolute;right:0;top:-1px;background:var(--bad-fill);color:var(--on-fill);font:700 10px var(--body);text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;border-radius:0 0 4px 4px}
.gl-cut.final{border-top-style:solid}
.team-icon{display:flex;width:22px;height:22px;align-items:center;justify-content:center;border-radius:3px;overflow:hidden}
.team-icon img{width:100%;height:100%;object-fit:contain}
.gl-out{margin-top:16px}.gl-out>summary{list-style:none;cursor:pointer}.gl-out>summary::-webkit-details-marker{display:none}
.gl-out h3.sec small{font-weight:500;color:var(--mute)}
.gl-rules{margin:16px 0;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px}
.gl-rules summary{cursor:pointer;font:700 14px var(--body)}.gl-rules li{margin:6px 0;font-size:14px}
.gl-weeks{margin-top:8px}
@media(max-width:600px){.gl-head{grid-template-columns:repeat(2,minmax(0,1fr))}.gl-k b{font-size:22px}
.live-t .gl-h,.live-t .gl-r{grid-template-columns:20px minmax(0,1fr) 56px 46px 34px 46px;gap:4px;padding:6px 6px}
.gl-n,.gl-w{font-size:14px}.gl-t{font-size:13px}}
[hidden]{display:none!important}
.gl-champ .trophy{flex:none}
.gl-replay{margin:10px 0;padding:10px 12px;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:6px;background:var(--panel);font-size:14px}
""" + TR.CSS


def main():
    os.chdir(lcfg.ROOT)
    c = lcfg.cfg()
    brand = html.escape(c.get("brand", ""))
    g = c["postseason"].get("guillotine", {})
    name = html.escape(g.get("name", "The Guillotine"))
    logo = g.get("logos", {}).get("wordmark", "")
    logo = html.escape("../" + logo.replace(" ", "%20")) if logo else ""
    body = f'''<div class="wrap gwrap">
{menu_html("special", ["special", "guillotine-seasons"])}
<header class="sbh gl-hdr"><div class="eyebrow">{brand} · special events · every team · postseason weeks</div>
<h1 class="gl-title">{f'<img id="gl-logo" src="{logo}" alt="{name}">' if logo else f'{brand} <em>{name}</em>'}</h1></header>
<div class="tools"><button id="refresh" type="button">↻ Refresh</button><span id="updated" role="status">Loading…</span></div>
<p id="error" role="alert" hidden></p>
<div id="board" aria-live="polite"></div>
</div>
<script src="assets/scoreboard-core.js"></script><script src="assets/trophy.js"></script><script src="assets/guillotine-model.js"></script><script src="assets/guillotine.js" defer></script></body></html>'''
    with open("reports/special.html", "w", encoding="utf-8") as f:
        f.write(page_head(f"{brand} {g.get('name', 'The Guillotine')}", CSS) + body)

    # Replays (Dev only, Chris 2026-11-24): a past season run through the Guillotine rules, to preview the
    # finished page. data/replays/guillotine-<year>.json (scripts/guillotine.py --year Y --out-dir, json
    # copied there) -> reports/guillotine-<year>.html. Kept out of data/scoreboard/ so the trophy ledger
    # never reads a replay as a real champion. Menu: config/nav.json rows.guillotine-seasons (hidden-dev).
    for src in sorted(glob.glob("data/replays/guillotine-*.json")):
        year = re.search(r"guillotine-(\d{4})\.json$", src)
        if not year:
            continue
        y = year.group(1)
        note = (f'<p class="gl-replay" role="note"><b>Replay, not an official result.</b> {y} was not played as '
                f'{name}: these are {y}\'s real week 13–17 scores run through this season\'s rules.</p>')
        page = (body.replace('<div id="board" aria-live="polite"></div>',
                             f'{note}<div id="board" aria-live="polite" data-src="../{html.escape(src)}"></div>')
                .replace(menu_html("special", ["special", "guillotine-seasons"]),
                         menu_html("special", ["special", "guillotine-seasons"])))
        with open(f"reports/guillotine-{y}.html", "w", encoding="utf-8") as f:
            f.write(page_head(f"{brand} {g.get('name', 'The Guillotine')} {y} replay", CSS) + page)
        print(f"wrote reports/guillotine-{y}.html (replay)")

    # Dwight Fight is its own Special Events sub-page, drawn with the bracket component (task 5.18)
    import dwight_page
    dwight_page.main()
    print("wrote reports/special.html")


if __name__ == "__main__":
    main()
