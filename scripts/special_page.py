"""
special_page.py -- reports/special.html, the Special Events tab (Chris, 2026-11-14).

One sub-tab per non-standard event (config/nav.json rows.special). Today: The Guillotine
(scripts/guillotine.py writes its data; reports/assets/guillotine.js draws it live in the browser).
Static shell only: the page reads data/scoreboard/<season>/guillotine.json, the week's frozen
projections, Sleeper and ESPN at view time. Rebuild after a design change; data changes need nothing.
CWD = repo root.
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
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
.out-t .gl-h,.out-t .gl-r{grid-template-columns:22px minmax(0,1fr) 54px 62px}
.gl-h{font:600 10px var(--body);text-transform:uppercase;letter-spacing:.04em;color:var(--mute);border-bottom:1px solid var(--line)}
.gl-h span:nth-child(n+3){text-align:right}
.gl-r{border-top:1px solid var(--line);min-height:34px}.gl-r:first-of-type{border-top:0}
.gl-t{min-width:0;font-size:14px;line-height:1.15;overflow-wrap:anywhere}.gl-t small{display:block;font-size:11px;color:var(--mute)}
.gl-n,.gl-w{text-align:right;font:600 15px var(--num);font-variant-numeric:tabular-nums}
.gl-n.pj,.gl-n.mn,.gl-w{color:var(--mute);font-weight:500}.gl-n.od{font-weight:800}
.gl-r.live .gl-n.sc{font-weight:900}.gl-r.bubble{background:color-mix(in srgb,var(--panel),var(--gold) 10%)}
.gl-r.mine{box-shadow:inset 4px 0 0 var(--accent)}.gl-r.gone{opacity:.5}
.gl-cut{position:relative;height:22px;border-top:2px dashed var(--accent);margin:0 6px}
.gl-cut span{position:absolute;right:0;top:-1px;background:var(--accent);color:#fff;font:700 10px var(--body);text-transform:uppercase;letter-spacing:.05em;padding:2px 6px;border-radius:0 0 4px 4px}
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
"""


def main():
    os.chdir(lcfg.ROOT)
    c = lcfg.cfg()
    brand = html.escape(c.get("brand", ""))
    g = c["postseason"].get("guillotine", {})
    name = html.escape(g.get("name", "The Guillotine"))
    logo = g.get("logos", {}).get("wordmark", "")
    logo = html.escape("../" + logo.replace(" ", "%20")) if logo else ""
    body = f'''<div class="wrap gwrap">
{menu_html("special", ["special"])}
<header class="sbh gl-hdr"><div class="eyebrow">{brand} · special events · every team · postseason weeks</div>
<h1 class="gl-title">{f'<img id="gl-logo" src="{logo}" alt="{name}">' if logo else f'{brand} <em>{name}</em>'}</h1></header>
<div class="tools"><button id="refresh" type="button">↻ Refresh</button><span id="updated" role="status">Loading…</span></div>
<p id="error" role="alert" hidden></p>
<div id="board" aria-live="polite"></div>
</div>
<script src="assets/scoreboard-core.js"></script><script src="assets/guillotine-model.js"></script><script src="assets/guillotine.js" defer></script></body></html>'''
    with open("reports/special.html", "w", encoding="utf-8") as f:
        f.write(page_head(f"{brand} {g.get('name', 'The Guillotine')}", CSS) + body)

    # Dwight Fight is a separate Special Events sub-page; preserve Guillotine's layout.
    dw_css = """
.dw-wrap{max-width:1200px;min-width:0}
.dw-brand{max-width:min(650px,100%);height:auto;display:block;margin:12px auto}
.dw-bracket{display:grid;grid-template-columns:repeat(var(--dw-rounds),minmax(0,1fr));gap:12px;margin:16px 0}
.dw-round{min-width:0;display:flex;flex-direction:column;justify-content:space-around;gap:12px}
.dw-round h2{font-size:15px;margin:0;color:var(--mute)}
.dw-game{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px;min-width:0}
.dw-side{display:flex;gap:5px;align-items:center;padding:7px 2px;min-width:0;border-bottom:1px solid var(--line);flex-wrap:wrap}
.dw-side:last-child{border:0}.dw-win{color:var(--good);font-weight:800}
.dw-empty{color:var(--neutral)}.dw-team{min-width:0;flex:1;overflow-wrap:anywhere;font-size:13px}
.dw-team b{color:var(--mute)}.dw-team small{display:block;color:var(--mute);font-weight:400;font-size:11px}
.dw-score{font:700 14px var(--num);font-variant-numeric:tabular-nums}
.dw-diff{font-size:10px;color:var(--bad);width:100%;text-align:right}
.dw-warn{border:1px solid var(--bad);border-radius:6px;padding:10px;color:var(--bad)}
.dw-champion{text-align:center;padding:12px;border:1px solid var(--good);border-radius:8px}
.dw-trophy{position:relative;width:min(300px,100%);margin:auto}.dw-trophy img{width:100%;display:block}
.dw-plaque{position:absolute;left:24.6%;top:82.5%;width:50.6%;height:11.1%;display:flex;flex-direction:column;justify-content:center;align-items:center;overflow:hidden;color:#4a260d;text-align:center;font-size:clamp(5px,1vw,10px);line-height:1.1}
.dw-plaque strong,.dw-plaque span{max-width:100%;white-space:nowrap;display:block;font-size:min(100%,10px);letter-spacing:-.02em}
.dw-champs{display:flex;flex-wrap:wrap;gap:6px}.dw-champs>div{padding:7px 10px;border:1px solid var(--line);border-radius:5px;background:var(--panel);font-size:13px}
.dw-history{border:1px solid var(--line);margin:10px 0;border-radius:6px;padding:10px}
.dw-history summary{cursor:pointer;font-weight:700}.dw-past{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}
.dw-past section{min-width:0}.dw-past h3{font-size:13px}.dw-hgame{border:1px solid var(--line);background:var(--panel);padding:7px;border-radius:5px;font-size:12px;margin:5px 0}
.dw-hgame span{display:flex;justify-content:space-between;gap:5px;overflow-wrap:anywhere}
@media(max-width:900px){.dw-bracket{grid-template-columns:repeat(2,minmax(0,1fr))}.dw-past{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:450px){.dw-bracket,.dw-past{grid-template-columns:minmax(0,1fr)}.dw-wrap{padding-inline:8px}.dw-plaque{font-size:7px}}
"""
    dw = c["postseason"].get("dwight_fight", {})
    dw_name = html.escape(dw.get("name", "Dwight Fight"))
    dw_body = f'''<div class="wrap dw-wrap">
{menu_html("special", ["special"])}
<header class="sbh"><div class="eyebrow">{brand} · special events</div><h1>{dw_name}</h1>
<img id="dw-wordmark" class="dw-brand" alt="{dw_name}"></header>
<p id="dw-status" role="status">Loading bracket…</p>
<div id="dw-trophy" data-src=""></div>
<div id="dw-main" aria-live="polite"></div>
<section id="dw-history" aria-label="Dwight Fight history"></section>
</div><script src="assets/dwight-fight.js" defer></script></body></html>'''
    with open("reports/dwight-fight.html", "w", encoding="utf-8") as output:
        output.write(page_head(f"{brand} Dwight Fight", dw_css) + dw_body)
    print("wrote reports/dwight-fight.html")
    print("wrote reports/special.html")


if __name__ == "__main__":
    main()
