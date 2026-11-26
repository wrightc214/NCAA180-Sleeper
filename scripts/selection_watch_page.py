"""Build the unlisted Selection Watch board. python scripts/selection_watch_page.py

The page is a prebuilt shell; the data and live scores are retrieved in the browser.
Generated output is reports/selection-watch.html. Never edit it directly.
"""
from html import escape
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg
from site_common import menu_html, page_head
from selection_watch_history import OUTPUT as HISTORY

PAGE = "reports/selection-watch.html"
CSS = """
.sw-page{grid-template-columns:minmax(0,1fr)}
.sw-page>*{min-width:0}
.sw-page>header>*{min-width:0;overflow-wrap:anywhere}
.sw-status>*,.sw-actions>*{min-width:0;max-width:100%;overflow-wrap:anywhere}
.sw-odds th,.sw-odds td{white-space:normal;overflow-wrap:anywhere}
.sw-season{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.sw-season[hidden]{display:none}
.sw-season select,.sw-season button{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);padding:7px 10px}
.sw-archive-section .sw-odds{table-layout:fixed}.sw-archive-section .sw-odds th:first-child{width:22%}
.sw-archive-section .sw-odds td:last-child{font:inherit;text-align:left}
.sw-archive-section .sw-field{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%, 155px),1fr));gap:6px 22px;padding-left:30px}
.sw-conf-short{display:none}
.sw-score-note{display:block;font-weight:400}
@media(max-width:600px){.sw-conf-full{display:none}.sw-conf-short{display:inline;white-space:nowrap}}
.sw-whatif{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,235px),1fr));gap:10px}
.sw-whatif label{display:grid;min-width:0;gap:3px}.sw-whatif select{max-width:100%;min-width:0}
.sw-whatif-banner{border:2px solid var(--accent);padding:8px;margin:8px 0;overflow-wrap:anywhere}
.sw-toss{font-weight:800;border:1px dashed var(--neutral);padding:1px 4px}
.sw-track{margin:8px 0}.sw-track>div{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:4px}
.sw-track span{border:1px solid var(--line);padding:4px}.sw-track small{display:block}
.sw-cut-note{margin:6px 0;font-weight:700}.sw-cut-line{border-top:2px dashed var(--bad);margin:5px 0}
.sw-order{display:flex;align-items:center;flex-wrap:wrap;gap:8px}
.sw-order button{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);padding:6px 9px}
.sw-order button[aria-pressed=true]{border-color:var(--accent)}
.sw-placard{--protect:var(--protect-gold);display:flex;align-items:center;gap:10px;border:2px solid var(--protect);border-left-width:6px;border-radius:8px;background:var(--panel);padding:8px 10px;min-width:0}
:root{--protect-gold:#9A730C}@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--protect-gold:#E0B84C}}:root[data-theme=dark]{--protect-gold:#E0B84C}
.sw-cut-row .sw-inline.sw-protect-cap{--protect:var(--protect-gold);color:var(--protect);font-weight:600}.sw-cut-row .sw-protect-cap a{color:inherit}
.sw-team .sw-logo{position:relative}.sw-ccg-badge{position:absolute;right:-7px;bottom:-7px;width:22px;height:22px;object-fit:contain;background:var(--panel);border:1px solid var(--line);border-radius:50%;padding:1px}
.sw-team.dim .sw-ccg-badge{opacity:1}
.sw-protect-icon{flex:none;width:34px;height:40px;color:var(--protect)}
.sw-protect-text{display:flex;flex-direction:column;min-width:0;flex:1 1 90px;line-height:1.25;overflow-wrap:break-word;word-break:normal}
.sw-protect-text b{color:var(--protect);text-transform:uppercase;letter-spacing:.03em}
.sw-protect-text span{font-size:.85em;color:var(--mute)}
.sw-placard{flex-wrap:wrap}
.sw-protect-pct{flex:none;border:2px solid var(--protect);border-radius:999px;padding:2px 10px;font-weight:800;color:var(--protect)}
@media (max-width:560px){.sw-ccg-badge{width:16px;height:16px;right:-4px;bottom:-4px}.sw-placard{gap:6px;padding:6px;border-left-width:4px}.sw-protect-icon{width:22px;height:26px}.sw-protect-text{font-size:.85em}.sw-protect-text b{letter-spacing:0}.sw-protect-pct{padding:1px 6px;font-size:.85em}}
.sw-playin-game p{margin:8px 0 0}.sw-playin-game .sw-pair>div{min-width:0;overflow-wrap:anywhere}
.sw-playin-winner{display:block;font-weight:800}
.sw-metrics{display:flex;align-items:baseline;gap:4px 8px;flex-wrap:wrap}
.sw-team .sw-number .sw-margin,.sw-metrics .sw-margin{color:var(--mute);white-space:nowrap}
.sw-team.admitted .sw-number .sw-margin{color:inherit;opacity:.85}
.sw-team .sw-number{display:flex;gap:5px;justify-content:flex-end;align-items:baseline;flex-wrap:wrap}
.sw-cut-row[data-held=pair] [data-thief] .sw-team{border-color:var(--neutral)}
.sw-cut-row .sw-team strong{min-width:0}
.sw-playin-game .sw-metrics small{font:600 11px var(--num)}
.sw-cut-row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:4px 0}
.sw-cut-row>*{min-width:0;overflow-wrap:anywhere}
.sw-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.sw-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.sw-actions button,.sw-actions select{border:1px solid var(--line);border-radius:6px;background:var(--panel);color:var(--ink);padding:7px 10px}
.sw-status{border:1px solid var(--line);border-radius:8px;padding:11px 14px;margin:12px 0;display:flex;flex-wrap:wrap;gap:7px 18px;align-items:center}
.sw-flag{font:800 11px var(--num);letter-spacing:.08em;border:1px solid var(--neutral);border-radius:4px;padding:3px 6px}
.sw-muted{color:var(--mute)}
.sw-section{margin:14px 0;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel)}
.sw-section>summary{display:flex;align-items:center;justify-content:space-between;cursor:pointer;padding:14px;gap:12px;font-weight:800;font-size:17px}
.sw-section>summary::marker{font-size:12px}
.sw-inner{padding:0 14px 14px}
.sw-save{font:600 12px var(--sans,sans-serif);padding:5px 8px;background:transparent;color:var(--ink);border:1px solid var(--line);border-radius:5px}
.sw-head{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:9px;padding:7px 10px;color:var(--mute);font:800 11px var(--num);letter-spacing:.05em}
.sw-pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:9px;padding:7px 9px;border-bottom:1px solid var(--line)}
.sw-pair:last-child{border-bottom:0}
.sw-pair.cut{border-top:3px dashed var(--neutral);margin-top:3px;padding-top:11px}
.sw-team{display:flex;align-items:center;min-width:0;gap:8px;border-radius:6px;border-left:5px solid var(--team,#889);background:var(--panel);padding:6px}
.sw-team.admitted{background:var(--team-fill,var(--panel));color:var(--team-ink,var(--ink))}
.sw-team.admitted small,.sw-team.admitted .sw-number{color:inherit}
.sw-team.dim{opacity:.45;filter:grayscale(.35)}
.sw-team .sw-logo{display:grid;place-items:center;width:42px;height:42px;flex:none;background:white;border:1px solid #ddd;border-radius:5px}
.sw-logo img{max-width:38px;max-height:38px;object-fit:contain}
.sw-team .sw-name{font-weight:800;overflow-wrap:anywhere}
.sw-team small{display:block;font:600 11px var(--num);color:var(--mute);margin-top:3px}
.sw-team .sw-number{font-weight:900;color:var(--ink);margin-left:auto;text-align:right}
.sw-team .sw-number small{white-space:nowrap}
.sw-inline{font:600 11px var(--num);color:var(--mute)}
.sw-empty{color:var(--mute);padding:8px}
.sw-odds{width:100%;border-collapse:collapse}
.sw-odds th,.sw-odds td{padding:9px;border-bottom:1px solid var(--line);text-align:left}
.sw-odds td:last-child{text-align:right;font:800 14px var(--num)}
.sw-locks{display:flex;flex-wrap:wrap;gap:7px}
.sw-lock{border:1px solid var(--line);border-left:4px solid var(--tc,var(--neutral));border-radius:5px;padding:6px 9px;font-weight:700;font-size:12px}
.sw-good{color:var(--good)}.sw-bad{color:var(--bad)}
.sw-alert{border:1px solid var(--bad);border-radius:6px;padding:10px;margin:12px 0}
.sw-progress{font:600 12px var(--num);color:var(--mute)}
@media(max-width:600px){.sw-odds{table-layout:fixed}
.sw-odds th:first-child{width:34%}.sw-odds th:last-child{width:24%}
.sw-pair,.sw-head{grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:4px;padding-left:2px;padding-right:2px}
.sw-team{gap:4px;padding:4px;border-left-width:3px;font-size:11px;flex-wrap:wrap}
.sw-team .sw-logo{width:30px;height:30px}.sw-logo img{max-width:27px;max-height:27px}
.sw-team .sw-number{margin-left:auto}.sw-team small{font-size:9px}}
"""

def main():
    os.chdir(lcfg.ROOT)
    config = lcfg.cfg()
    labels = lcfg.selection_watch().get("labels") or {}

    def label(key, fallback):
        value = labels.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else fallback

    brand_value = config.get("brand")
    brand = brand_value.strip() if isinstance(brand_value, str) and brand_value.strip() else "NCAA 180"
    title = label("title", "Selection Watch")
    html = page_head(f"{title} | {brand}", CSS)
    html += f"""
<main class="wrap sw-page">
"""
    html += menu_html("selection-watch", rows=("selection-watch",))  # CCG / Playoffs sub-row (#126)
    html += f"""
<header><h1><span id="sw-brand">{escape(brand)}</span> <em data-sw-label="title">{escape(title)}</em></h1>
<p id="sw-intro" class="sw-muted">Exact playoff probabilities during conference championship week · Unofficial</p></header>
"""
    seasons = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {}
    options = "".join(f'<option value="{year}">{year} · Final</option>'
                      for year in sorted(seasons, key=int, reverse=True))
    html += f"""
<form id="sw-season-picker" class="sw-season" method="get" hidden>
<label for="sw-season">Season</label><select id="sw-season" name="season"><option value="">Current season</option>{options}</select>
<button type="submit">View season</button>
</form>
"""
    html += """
<div id="sw-error" role="status" class="sw-alert" hidden></div>
<div id="sw-final" class="sw-final" hidden>
<div class="sw-actions"><button id="sw-final-collapse" type="button">Collapse all</button></div>
<div id="sw-final-status" class="sw-status"></div>
<details id="sw-final-cut-section" class="sw-section" open><summary>Steal Board · Final <button class="sw-save" type="button" data-save="sw-final-cut-section">Save image</button></summary>
<div class="sw-inner"><div class="sw-order"><button id="sw-final-sort" type="button" aria-pressed="false">Ranking order</button></div>
<div id="sw-final-cut"></div></div></details>
<details id="sw-final-playins" class="sw-section" open hidden><summary>Play-in games <button class="sw-save" type="button" data-save="sw-final-playins">Save image</button></summary>
<div class="sw-inner" id="sw-final-playin-rows"></div></details>
<details id="sw-final-ccg-section" class="sw-section sw-archive-section" open><summary>Conference championship finals <button class="sw-save" type="button" data-save="sw-final-ccg-section">Save image</button></summary>
<div class="sw-inner" id="sw-final-ccg"></div></details>
<details id="sw-final-field-section" class="sw-section sw-archive-section" open><summary>Final playoff field <button class="sw-save" type="button" data-save="sw-final-field-section">Save image</button></summary>
<div class="sw-inner" id="sw-final-field"></div></details>
</div>
<div id="sw-content" hidden>
<p id="sw-whatif-banner" class="sw-whatif-banner" role="status" hidden></p>
<div class="sw-top"><div class="sw-actions">
<button id="sw-collapse" type="button">Collapse all</button><button id="sw-refresh" type="button">Refresh</button><button id="sw-discord-draft" type="button" hidden>Save Discord draft</button></div>
<span id="sw-updated" class="sw-progress">Loading…</span></div>
<details id="sw-status-section" class="sw-section" open><summary>Status <button class="sw-save" type="button" data-save="sw-status-section">Save image</button></summary><div id="sw-status" class="sw-status" aria-live="polite">Loading selection data…</div></details>
<details id="sw-board" class="sw-section" open><summary>Steal Board <button class="sw-save" type="button" data-save="sw-board">Save image</button></summary>
<div class="sw-inner"><div class="sw-order"><button id="sw-sort" type="button" aria-pressed="false">Ranking order</button></div>
<div id="sw-board-rows"></div></div></details>
<details id="sw-playins" class="sw-section" open hidden><summary>Play-in games <button class="sw-save" type="button" data-save="sw-playins">Save image</button></summary>
<div class="sw-inner" id="sw-playin-rows"></div></details>
<details id="sw-bubble" class="sw-section" open><summary>Bubble odds <button class="sw-save" type="button" data-save="sw-bubble">Save image</button></summary><div class="sw-inner" id="sw-bubble-rows"></div></details>
<details id="sw-locks" class="sw-section" open><summary>Locks <button class="sw-save" type="button" data-save="sw-locks">Save image</button></summary><div class="sw-inner" id="sw-lock-rows"></div></details>
<details id="sw-noimpact" class="sw-section"><summary>No-impact CCGs <button class="sw-save" type="button" data-save="sw-noimpact">Save image</button></summary><div class="sw-inner" id="sw-noimpact-rows"></div></details>
<details id="sw-whatif" class="sw-section" hidden><summary>What-if <button class="sw-save" type="button" data-save="sw-whatif">Save image</button></summary>
<div class="sw-inner"><p>Pick winners for unfinished games. These picks change only your view.</p>
<button id="sw-reset-picks" type="button">Reset picks</button><div id="sw-picks" class="sw-whatif"></div></div></details>
<p class="sw-muted">An unofficial estimate, not a published playoff field. Ties remaining after every ranking tiebreaker await a real coin toss.</p>
</div>
</main>
<script src="assets/snapshot.js"></script>
<script src="assets/scoreboard-core.js"></script>
<script src="assets/scoreboard-overview-model.js"></script>
<script src="assets/selection-watch-core.js"></script>
<script src="assets/selection-watch-games.js"></script>
<script src="assets/selection-watch.js" defer></script>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    print("Built " + PAGE)

if __name__ == "__main__":
    main()
