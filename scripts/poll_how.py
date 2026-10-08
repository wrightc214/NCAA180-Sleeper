"""
poll_how.py -- reports/poll-how.html: "How it works" for the poll, generated from config/poll.json
(bot names, voices, what each measures, inputs and weights; consensus and final-poll rules).
Nothing is hardcoded here: rename a bot or change a weight in config and rerun.
CWD must be repo root. Run after poll_page.py (linked from the poll page and the nav).
"""
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

OUT = "reports/poll-how.html"
e = html.escape

CSS = """
.bots{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.bot{border:1px solid var(--line,#ccc);border-radius:6px;padding:12px 14px}
.bot h3{margin:0 0 2px;font-size:18px}.bot h3 small{color:var(--mute);font-weight:400;margin-left:6px}
.bot .voice{font-style:italic;color:var(--mute);margin:0 0 8px}
.bot p{margin:4px 0}
table.w{border-collapse:collapse;margin:6px 0 10px;width:100%;min-width:0;table-layout:auto}
table.w td,table.w th{padding:3px 8px;text-align:right;white-space:normal;color:inherit!important;font-weight:400;font-size:14px}
table.w th{font-weight:700;font-size:12px}
table.w td:first-child,table.w th:first-child{text-align:left}
ul.rules li{margin:4px 0}
"""

LABELS = {  # display labels for Professor's config keys
    "psv": "Preseason starter value", "last_final": "Last season's final rank",
    "allplay": "All-play win % vs all teams, weekly", "ppg": "Points per game",
    "consistency": "Weeks above the all-team weekly median",
    "win_pct": "Win %", "quality_wins": "Wins over opponents in the top half of Quality that week",
    "standing": "Division / conference standing",
}


def pctf(x):
    return f"{round(float(x) * 100)}%"


def professor_html(p):
    def block(name, d):
        rows = "".join(f"<tr><td>{e(LABELS.get(k, k))}</td><td>{pctf(v)}</td></tr>" for k, v in d.items() if not k.startswith("_"))
        return f"<p><b>{name}</b></p><table class='w'>{rows}</table>"
    w = p.get("weights", {})
    wk = sorted(w, key=int)
    wrows = "".join(f"<tr><td>{'Preseason' if int(k) == 0 else 'Week ' + k}</td>"
                    + "".join(f"<td>{v}%</td>" for v in w[k]) + "</tr>" for k in wk)
    return (block("Prior", p.get("prior", {}))
            + "<p class='note'>Frozen before week 1 (last value snapshot before the season); never refreshed in-season. "
              "Last season's final rank = the final poll, or the standings if there was no poll.</p>"
            + block("Quality", p.get("quality", {})) + block("Resume", p.get("resume", {}))
            + f"<p><b>Block weights by games played</b> (straight line between rows)</p>"
              f"<table class='w'><tr><th></th><th>Prior</th><th>Quality</th><th>Resume</th></tr>{wrows}</table>"
            + "<p class='note'>Every measure is a percentile rank across all teams. Not used: lineup efficiency, "
              "max points, points against, week-to-week spread.</p>")


def main():
    cfg = pc.config()
    bots = [b for b in cfg["bots"] if b.get("enabled", True)]
    nm = {b["id"]: b["name"] for b in cfg["bots"]}
    top = pc.poll_cfg(cfg, "Top25")
    size = int(top.get("size", 25))
    fin = cfg["polls"].get("Final", {})
    bump = fin.get("bump", {})
    cons = cfg.get("consensus", {})

    cards = []
    for b in bots:
        extra = professor_html(cfg.get("professor", {})) if b["id"] == "professor" else ""
        cards.append(f"<div class='bot' id='{e(b['id'])}'><h3>{e(b['name'])}<small>{e(b.get('short', ''))}</small></h3>"
                     f"<p class='voice'>“{e(b.get('voice', ''))}”</p>"
                     f"<p><b>Measures:</b> {e(b.get('blurb', ''))}</p>"
                     f"<p><b>Inputs:</b> {e(b.get('how', ''))}</p>{extra}</div>")

    post = ", ".join(nm[i] for i in ("record", "resume", "efficiency") if i in nm)
    frozen = ", ".join(b["name"] for b in bots if b["id"] not in ("record", "resume", "efficiency"))
    po = bump.get("Playoff", [])
    rules = [
        f"<b>Every bot ranks every team</b> in all leagues, using regular-season weeks 1–{cfg.get('last_regular_week', 11)}.",
        ("<b>One scale.</b> Each bot's rating is turned into standard deviations from the average team (z-score, capped at ±3)."
         if cons.get("method") == "zscore" else "<b>One scale.</b> Each bot's rank is used directly."),
        ("<b>Best and worst dropped.</b> For each team, its single best and single worst bot are thrown out (BCS style); "
         "the rest are averaged. That average is the Score: 0 = average team, +1 = one standard deviation better."
         if cons.get("drop_high_low", True) else "<b>Average.</b> Every bot counts."),
        f"<b>Top {size}</b> = the {size} highest Scores. Ties: Score, then average bot rank, then Scoreboard.",
        "<b>First-place votes</b> = how many bots rank the team #1.",
        f"<b>Others receiving votes</b> = outside the top {size} but in at least one counted bot's top {size}.",
        "<b>Bots sit out</b> a week when their data doesn't exist yet (e.g. no value snapshot); the page shows how many counted.",
    ]
    if fin:
        rules.append(f"<b>Final poll</b> (after the postseason): postseason games count as extra games for {e(post)}; "
                     f"{e(frozen)} stay at the end of the regular season.")
        if bump:
            rules.append("<b>Postseason bumps</b> added to Score per win: playoff rounds "
                         + "/".join(f"+{v:g}" for v in po) + f", conference title game +{bump.get('CCG', 0):g}, "
                         f"bowl +{bump.get('Bowl', 0):g}, NIT +{bump.get('NIT', 0):g} (× share of rivals outscored).")
        if fin.get("final_four_rule"):
            rules.append("<b>Final-four backstop:</b> a semifinal or final winner always ranks directly above the team it beat.")
    if cfg.get("human_component", {}).get("enabled"):
        rules.append("<b>Panel ballots</b> are a second component, averaged with the bots.")

    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("poll-how")}</nav>
<header><div><div class="eyebrow">NCAA 180 poll</div><h1>How it <em>works</em></h1></div>
<div class="kpis"><div class="kpi"><b>{len(bots)}</b><span>Computer bots</span></div></div></header>
<section><h2>The poll</h2><ul class="rules">{''.join(f'<li>{r}</li>' for r in rules)}</ul>
<p class="note"><a href="poll.html">Latest poll</a></p></section>
<section><h2>The bots</h2><div class="bots">{''.join(cards)}</div></section>
</div></body></html>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page_head("NCAA 180 Poll — How it works", CSS) + body)
    print(f"Wrote {OUT} ({len(bots)} bots)")


if __name__ == "__main__":
    main()
