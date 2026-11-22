"""
champions_league_page.py -- the Champions League pages (Special Events → Champions League; hidden-dev).

Six static shells; reports/assets/champions-league.js fills them in the browser from
data/scoreboard/<season>/champions-league.json (scripts/champions_league.py). A data change needs no
rebuild; rebuild after a design or rules-config change (the Rules page text is built from
config/champions_league.json). CWD = repo root.
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
from site_common import SECTIONS_JS, menu_html, page_head  # noqa: E402

PAGES = [  # file, title, sections [(id, heading)]
    ("cl-standings.html", "Standings", [("cl-cup", "Triad Cup"), ("cl-table", "Standings")]),
    ("cl-schedule.html", "Schedule", [("cl-sched", "Schedule")]),
    ("cl-scoreboard.html", "Scoreboard", [("cl-week", "Pods")]),
    ("cl-field.html", "Field", [("cl-field", "How the field was chosen"), ("cl-leagues", "Teams per conference")]),
    ("cl-selection.html", "Selection", [("cl-proj", "Projected field"), ("cl-out", "First teams out")]),
    ("cl-rules.html", "Rules", []),
]

CSS = """
.clwrap{max-width:980px}
.cl-hdr{padding-bottom:10px;border-bottom:3px solid var(--accent);margin-bottom:6px}
.cl-hdr h1{margin:6px 0 0}
.cl-banner{margin:10px 0;padding:8px 12px;border:1px dashed var(--accent);border-radius:6px;font:600 13px var(--body);color:var(--accent)}
.cl-state{font:600 13px var(--body);color:var(--mute);margin:8px 2px}
#cl-error{padding:12px;background:#fff0d7;color:#722a00;border:1px solid #aa6d15;border-radius:5px}
.cl-tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 0 10px}
.cl-tools select,.cl-tools button{font:600 14px var(--num);padding:7px 10px;border:1px solid var(--line);border-radius:5px;background:var(--panel);color:var(--ink)}
.cl-body{overflow-x:auto;-webkit-overflow-scrolling:touch;overscroll-behavior-x:contain} /* wide tables scroll inside the section on phones; Save image widens to the table (sections.js) */
.cl-t{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:14px}
.cl-t th{font:600 10px var(--body);text-transform:uppercase;letter-spacing:.04em;color:var(--mute);text-align:right;padding:7px 8px;border-bottom:1px solid var(--line)}
.cl-t td{padding:6px 8px;border-top:1px solid var(--line);text-align:right;font-variant-numeric:tabular-nums}
.cl-t th.l,.cl-t td.l{text-align:left}
.cl-t tr.mine td{box-shadow:inset 0 0 0 9999px color-mix(in srgb,transparent,var(--accent) 8%)}
.cl-t tr.cut td{border-top:2px dashed var(--bad)}
.cl-team{display:flex;align-items:center;gap:7px;min-width:0}.cl-team b{font-weight:700}
.cl-team small{display:block;font-size:11px;color:var(--mute);font-weight:400}
.team-icon{display:inline-flex;flex:0 0 22px;width:22px;height:22px;align-items:center;justify-content:center;border-radius:3px;overflow:hidden}
.team-icon img{width:100%;height:100%;object-fit:contain}
.cl-pods{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:10px}
.cl-pod{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 10px}
.cl-pod h3{margin:2px 0 4px;font:600 11px var(--body);text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}
.cl-pr{display:grid;grid-template-columns:26px minmax(0,1fr) 62px 34px;gap:6px;align-items:center;padding:5px 0;border-top:1px solid var(--line)}
.cl-pr:first-of-type{border-top:0}.cl-pr .s{font:500 12px var(--num);color:var(--mute)}
.cl-pr .n{text-align:right;font:700 15px var(--num);font-variant-numeric:tabular-nums}.cl-pr .p{text-align:right;font:800 14px var(--num)}
.cl-pr.top .p{color:var(--good)}.cl-pr.bot .p{color:var(--mute)}.cl-pr.mine{box-shadow:inset 4px 0 0 var(--accent)}
.cl-note{font-size:13px;color:var(--mute);margin:8px 2px}
.cl-rules{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px 16px}
.cl-rules li{margin:6px 0;font-size:14px;line-height:1.4}
.cl-chip{display:inline-block;font:600 11px var(--body);padding:1px 6px;border-radius:10px;border:1px solid var(--line);color:var(--mute);white-space:nowrap}
@media(max-width:600px){.cl-t{font-size:13px}.cl-t th,.cl-t td{padding:5px 4px}.cl-hide-s{display:none}}
[hidden]{display:none!important}
"""


def fmt_list(xs):
    return ", ".join(str(x) for x in xs)


def rules_html(c, term, term_pl):
    sel, tb = c["selection"], c["tiebreak"]
    p = c["pod_points"]
    hs = c["cup_head_start"]
    pw, cw = c["pod_weeks"], c["cup_weeks"]
    cup = html.escape(c.get("cup_name", "Triad Cup"))
    ap, bb = sel["allplay_weeks"], sel["bestball_weeks"]
    ladder = {"final_four": "the four playoff semifinalists (Final Four)",
              "nit_champion": "the NIT champion",
              "snub": "the snub: the best team on the final poll that missed the playoff",
              "defending_champion": f"the defending {cup} champion (from {sel.get('defending_champion_from')})"}
    sec = []

    def section(title, items):
        sec.append(f'<section class="cl-rules-sec"><h2>{html.escape(title)}</h2><div class="cl-rules"><ul>'
                   + "".join(f"<li>{i}</li>" for i in items) + "</ul></div></section>")
    section("Format", [
        f"{c['field_size']} teams, chosen from last season's results. Every team keeps playing in its own {term}; "
        f"the Champions League scores the same weekly score (standard scoring).",
        f"Weeks {pw[0]}–{pw[1]}: three-team pods. Every team plays the other two in its pod, and over the season "
        f"every team meets every other team exactly once.",
        f"Weeks {cw[0]}–{cw[1]}: the {cup}. The top {c['cup_size']} play one final pod on their combined score over both weeks."])
    section("Pod points", [
        f"Beat both = {p[0]}, split = {p[1]}, lose both = {p[2]}. Every pod awards {sum(p)} points a week.",
        "Ties split the points of the places they share: two tied for 1st get "
        f"{(p[0] + p[1]) / 2:g} each, two tied for 2nd get {(p[1] + p[2]) / 2:g} each, a three-way tie "
        f"gets {sum(p)}/3 each."])
    section("Standings", [
        "Sorted by pod points. Teams on equal points share a place.",
        "All-play wins (teams in the field you outscored each week; ties count half) are shown in their own column.",
        f"Only the top {c['cup_size']} need breaking: pod points, then all-play wins, then best-ball points "
        f"(best possible lineup), then head-to-head weekly scores (weeks 1–{tb['h2h_last_week']}, then 2–{tb['h2h_last_week']}, …), then a coin toss."])
    section(cup, [
        f"Head start by standings place: {', '.join(f'{x:g}' for x in hs)} points, added to the combined score of weeks {cw[0]} and {cw[1]}.",
        "Highest total wins. A tie goes to the higher seed."])
    section("How the field is chosen", [
        "In order, from last season (a team already in counts once; its line passes to no one): "
        + "; ".join(ladder[x] for x in sel["ladder"]) + ".",
        f"Every other place: the lowest sum of three ranks — all-play wins (weeks {ap[0]}–{ap[1]}), best-ball points "
        f"(weeks {bb[0]}–{bb[1]}) and the final bot poll.",
        f"Every {term} is guaranteed one team: if the {term_pl} still without a team equal the places left, "
        f"each gets its best team by that sum. {term[:1].upper() + term[1:]} winners get no automatic place.",
        f"Seeds 1–{c['field_size']} follow the same ranking; the schedule is fixed by seed and repeats every year."])
    section("Ties in the field", [
        "Rank sum, then the best worst rank, then best-ball points, then head-to-head weekly scores, then a coin toss.",
        "Three or more tied: a team that beats every other tied team wins; otherwise a team that loses to every other "
        "tied team drops out and the rest start over; otherwise the next step."])
    section("Owners and orphans", [
        "A place belongs to the owner who earned it. A team whose owner changes before the season gives up its place; "
        "before the schedule is published the field is re-seeded, after it the replacement takes the open seed.",
        "The field locks in week 1. Teams orphaned during the season keep playing."])
    return "".join(sec)


def page(c, brand, file, title, sections, nav_row):
    name = html.escape(c.get("name", "Champions League"))
    body_sections = "".join(f'<section id="{sid}"><h2>{html.escape(h)}</h2><div class="cl-body" data-for="{sid}"></div></section>'
                            for sid, h in sections)
    tools = ""
    if file == "cl-schedule.html":
        tools = '<div class="cl-tools"><label>View <select id="cl-view"><option value="week">By week</option><option value="team">By team</option></select></label><select id="cl-pick" aria-label="Week or team"></select></div>'
    if file == "cl-scoreboard.html":
        tools = '<div class="cl-tools"><label>Week <select id="cl-wk"></select></label></div>'
    rules = rules_html(c, lcfg.term(), lcfg.term(plural=True)) if file == "cl-rules.html" else ""
    js = "" if file == "cl-rules.html" else '<script src="assets/scoreboard-core.js"></script><script src="assets/champions-league.js" defer></script>'
    body = f'''<div class="wrap clwrap">
{menu_html("special", ["special", nav_row])}
<header class="sbh cl-hdr"><div class="eyebrow">{html.escape(brand)} · special events</div>
<h1>{name} <em>{html.escape(title)}</em></h1></header>
<p class="cl-banner" id="cl-banner" hidden></p>
<p class="cl-state" id="cl-state" role="status">{'' if file == 'cl-rules.html' else 'Loading…'}</p>
<p id="cl-error" role="alert" hidden></p>
{tools}{body_sections}{rules}
</div>
<script>window.CL_PAGE={json.dumps(file[3:-5])};</script>{js}{SECTIONS_JS}</body></html>'''
    return page_head(f"{brand} {c.get('name', 'Champions League')} {title}", CSS) + body


def main():
    os.chdir(lcfg.ROOT)
    with open("config/champions_league.json", encoding="utf-8") as f:
        c = json.load(f)
    brand = lcfg.brand()
    for file, title, sections in PAGES:
        with open(os.path.join("reports", file), "w", encoding="utf-8") as f:
            f.write(page(c, brand, file, title, sections, "champions-league"))
        print("wrote reports/" + file)


if __name__ == "__main__":
    main()
