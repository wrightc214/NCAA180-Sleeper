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
.sw-team .sw-number{margin-left:0}.sw-team small{font-size:9px}}
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
<header><h1><span id="sw-brand">{escape(brand)}</span> <em data-sw-label="title">{escape(title)}</em></h1>
<p id="sw-intro" class="sw-muted">Exact playoff probabilities during conference championship week · Unofficial</p></header>
"""
    html += menu_html("selection-watch")
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
<details id="sw-final-ccg-section" class="sw-section sw-archive-section" open><summary>Conference championship finals <button class="sw-save" type="button" data-save="sw-final-ccg-section">Save image</button></summary>
<div class="sw-inner" id="sw-final-ccg"></div></details>
<details id="sw-final-field-section" class="sw-section sw-archive-section" open><summary>Final playoff field <button class="sw-save" type="button" data-save="sw-final-field-section">Save image</button></summary>
<div class="sw-inner" id="sw-final-field"></div></details>
</div>
<div id="sw-content" hidden>
<div class="sw-top"><div class="sw-actions">
<label for="sw-sort">Steal Board order</label><select id="sw-sort"><option value="chance">Win chance</option><option value="margin">If it ended now · margin</option></select>
<button id="sw-collapse" type="button">Collapse all</button><button id="sw-refresh" type="button">Refresh</button></div>
<span id="sw-updated" class="sw-progress">Loading…</span></div>
<details id="sw-status-section" class="sw-section" open><summary>Status <button class="sw-save" type="button" data-save="sw-status-section">Save image</button></summary><div id="sw-status" class="sw-status" aria-live="polite">Loading selection data…</div></details>
<details id="sw-board" class="sw-section" open><summary>Steal Board <button class="sw-save" type="button" data-save="sw-board">Save image</button></summary>
<div class="sw-inner"><p class="sw-muted">One row per potential steal. The at-large team opposite the thief is the team whose place is threatened.</p><div id="sw-board-rows"></div></div></details>
<details id="sw-bubble" class="sw-section" open><summary>Bubble odds <button class="sw-save" type="button" data-save="sw-bubble">Save image</button></summary><div class="sw-inner" id="sw-bubble-rows"></div></details>
<details id="sw-locks" class="sw-section" open><summary>Locks <button class="sw-save" type="button" data-save="sw-locks">Save image</button></summary><div class="sw-inner" id="sw-lock-rows"></div></details>
<details id="sw-noimpact" class="sw-section"><summary>No-impact CCGs <button class="sw-save" type="button" data-save="sw-noimpact">Save image</button></summary><div class="sw-inner" id="sw-noimpact-rows"></div></details>
<p class="sw-muted">An unofficial estimate, not a published playoff field. Ties remaining after every ranking tiebreaker await a real coin toss.</p>
</div>
</main>
<script src="assets/snapshot.js"></script>
<script src="assets/scoreboard-core.js"></script>
<script src="assets/scoreboard-overview-model.js"></script>
<script src="assets/selection-watch-core.js"></script>
<script src="assets/selection-watch.js" defer></script>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    print("Built " + PAGE)

if __name__ == "__main__":
    main()
