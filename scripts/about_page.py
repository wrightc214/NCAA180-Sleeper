"""
about_page.py -- reports/about.html: what NCAA 180 is, in one page (Chris, 2026-11-07).

Draft for Chris to edit: rules wording comes from the bylaws (project doc claude/bylaws.md) and, where
the scripts enforce a rule, straight from config/league.json so the page can't drift from what the
site does. Conferences/divisions come from data/Teams.csv; champions from Postseason_Historic.csv.
Not linked from the site nav until Chris approves it (direct link only).
Top: copy-the-site-link button (short link "home") + Discord invite (config about.discord_invite).
Every section folds and has a save-image button (site design rule).

  python scripts/about_page.py
"""
import html
import json
import os
import sys
from urllib.parse import quote_plus

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowl_projection as bp  # noqa: E402
import league_config as lcfg  # noqa: E402
from poll_page import colors  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

OUT = "reports/about.html"
e = html.escape
SHORT = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "short_links.json")))


def chip(team, col):
    bg, fg = col.get(team, ("#14213a", "#ffffff"))
    return f'<span class="ch" style="background:{bg};color:{fg}">{e(team)}</span>'


def card(sid, title, body, sub=""):
    return (f'<section class="card" id="{sid}"><h2>{e(title)}{f" <small>{e(sub)}</small>" if sub else ""}</h2>{body}</section>')


def champions():
    h = pd.read_csv("data/Postseason_Historic.csv", dtype=str, keep_default_na=False)
    natty = h[(h["Event"] == "Playoff") & (h["RoundName"] == "National Championship")]
    nit = h[(h["Event"] == "NIT") & (h["RoundName"] == "Final")]
    out = []
    for y in sorted({int(s) for s in h["Season"] if s.isdigit()}):
        n = natty[natty["Season"] == str(y)]
        t = nit[nit["Season"] == str(y)]
        out.append((y, n["Winner"].iloc[0] if len(n) else "", (n["TeamA"].iloc[0], n["TeamB"].iloc[0]) if len(n) else ("", ""),
                    t["Winner"].iloc[0] if len(t) else ""))
    return out


def discord_link(dc):
    """One tap to the person's Discord profile (then Message): https://discord.com/users/<numeric id>.
    The id comes from config about.data_contact.discord_id, else the DISCORD_CONTACT_ID the weekly job
    already uses to tag Chris (Chris, 2026-11-07: only his Discord for now). No id -> plain text."""
    name = dc.get("discord", "")
    did = str(dc.get("discord_id", "") or os.environ.get("DISCORD_CONTACT_ID", "")).strip()
    if did.isdigit():
        return f' <a class="dc" href="https://discord.com/users/{did}" target="_blank" rel="noopener">Discord @{e(name)}</a>'
    return f' <span class="dd">Discord @{e(name)}</span>' if name else ""


def directory(term, short, col=None):
    """League manager, then the data contact and each conference's assistant(s) with LM powers, then the
    special accounts (Chris, 2026-11-07). Names are Sleeper display names; tap one to copy it (Sleeper has
    no public link that opens a DM)."""
    a = lcfg.cfg().get("about", {})
    # accounts without a team (Chris, 2026-11-07): users with no roster in any league they're in -- just a list
    if len(st := (pd.read_csv("data/LeagueStaff.csv", dtype=str, keep_default_na=False)
                  if os.path.exists("data/LeagueStaff.csv") else pd.DataFrame())):
        has = st.groupby("DisplayName")["HasRoster"].apply(lambda x: (x == "True").any())
        special = {n: sorted(st[st["DisplayName"] == n]["LeagueName"]) for n in has[~has].index}
    else:
        special = {}
    lm, dc = a.get("league_manager", {}), a.get("data_contact", {})
    f = "data/LeagueStaff.csv"
    st = pd.read_csv(f, dtype=str, keep_default_na=False) if os.path.exists(f) else pd.DataFrame()
    un = lambda n: f'<button type="button" class="un" data-u="{e(n)}" title="Copy Sleeper name">@{e(n)}</button>' if n else ""  # noqa: E731
    owners = st[st["IsOwner"] == "True"] if len(st) else st
    lm_name = lm.get("sleeper", "")
    if not lm_name and len(owners):  # the commissioner of the most leagues, not the data contact or a special account
        c = owners[~owners["DisplayName"].isin(list(special) + [dc.get("sleeper", "")])]["DisplayName"].value_counts()
        lm_name = c.index[0] if len(c) and c.iloc[0] > 1 else ""
    taken = {lm_name, dc.get("sleeper", ""), *special}
    # Sleeper name, then the team they manage, in its colors (Chris, 2026-11-07)
    col = col or {}
    ro = pd.read_csv("data/RosterOwners_LastSeen.csv", dtype=str, keep_default_na=False)
    tm = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
    team_of = {(str(l).strip(), str(r)): t for l, r, t in zip(tm["League"], tm["Roster ID"], tm["Team"])}
    teams_by = {}
    for l, r, n in zip(ro["LeagueName"], ro["RosterID"], ro["OwnerName"]):
        if (str(l).strip(), str(r)) in team_of:
            teams_by.setdefault(n.lower(), []).append((str(l).strip(), team_of[(str(l).strip(), str(r))]))

    def who(n, league=None):
        ts = [t for lg, t in teams_by.get(str(n).lower(), []) if league is None or lg == league.strip()]
        return f'{un(n)} {" ".join(chip(t, col) for t in ts)}' if n else ""
    h = (f'<h3>League manager</h3><p class="dl">{who(lm_name)}</p>'
         f'<h3>Data &amp; site</h3><p class="dl">{who(dc.get("sleeper", ""))}'
         + discord_link(dc) + "</p>")
    if len(owners):
        rows = ""
        for lg, g in sorted(owners.groupby("LeagueName"), key=lambda x: short.get(x[0].strip(), x[0])):
            names = [n for n in g["DisplayName"] if n not in taken]
            rows += (f'<tr><th scope="row">{e(short.get(lg.strip(), lg.strip()))}</th>'
                     f'<td>{" ".join(who(n, lg) for n in names) or "—"}</td></tr>')
        h += f'<h3>{e(term.title())} assistants <small>LM powers in their {e(term)}</small></h3><table class="ct dt"><tbody>{rows}</tbody></table>'
    else:
        h += f'<p class="sub">{e(term.title())} assistants appear after the next weekly run.</p>'
    if special:
        n_all = st["LeagueID"].nunique()

        def where(lgs):
            names = [short.get(x.strip(), x.strip()) for x in lgs]
            if len(names) >= n_all:
                return f"all {n_all} {lcfg.term(plural=True)}"
            return ", ".join(names) if len(names) <= 2 else f"{names[0]}, {names[1]} + {len(names) - 2} more"
        h += ('<h3>Accounts without a team</h3><ul class="rl">'
              + "".join(f'<li>{un(k)} <span class="dd">{e(where(v))}</span></li>' for k, v in sorted(special.items(), key=lambda kv: -len(kv[1])))
              + "</ul>")
    return h + '<p class="sub">Tap a name to copy it, then search it in Sleeper to send a message.</p>'


def build():
    cfg = lcfg.cfg()
    pc = cfg["postseason"]
    col = colors()
    term, terms = lcfg.term(), lcfg.term(plural=True)
    teams = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
    short = {v: k for k, v in ps.league_short().items()}
    n_conf = teams["League"].nunique()
    n_teams = len(teams)
    per = teams.groupby("League").size().max()
    champs = champions()
    first = champs[0][0] if champs else ""
    lr, ccg = ps.last_regular_week(), ps.ccg_week()
    po = pc["playoff"]
    field, n_auto = int(po["field_size"]), int(po["auto_bids_per_league"]) * n_conf
    bw = pc["bowls"]
    tiers = [t["name"] for t in bw["tiers"]][::-1]  # lowest -> highest
    n_bowls = sum(len(t["bowls"]) for t in bw["tiers"])
    nit = pc.get("nit", {}).get("realigned", {})
    slots = json.load(open("data/scoreboard/index.json"))["leagues"]
    slots = next(iter(slots.values())).get("slots", [])
    lineup = " · ".join(f"{n} {s}" if n > 1 else s for s, n in
                        [(s, slots.count(s)) for s in dict.fromkeys(slots)]) if slots else "QB · 2 RB · 3 WR · TE · 2 FLEX · K · DEF"
    home = SHORT.get("home", "")
    invite = cfg.get("about", {}).get("discord_invite", "")

    top = (f'<div class="share"><button type="button" id="copy-home" data-url="{e(home)}">Copy site link</button>'
           + (f'<a class="btn" href="{e(invite)}" target="_blank" rel="noopener">Join the Discord</a>' if invite else "")
           + f'<span id="copied" role="status" aria-live="polite"></span></div>'
           # install = add the site to the home screen (Chris: link a prefilled search, one per platform)
           + '<p class="inst"><b>Install the app:</b> '
           + " · ".join(f'<a href="https://letmegooglethat.com/?q={quote_plus(q)}" target="_blank" rel="noopener">{lbl}</a>'
                        for lbl, q in (("iPhone (Safari)", "how to add a website to the home screen on iPhone Safari"),
                                       ("Android (Chrome)", "how to add a website to the home screen on Android Chrome")))
           + '</p>')

    glance = (f'<div class="facts">'
              f'<div><b>{n_teams}</b><span>teams</span></div><div><b>{n_conf}</b><span>{terms}</span></div>'
              f'<div><b>{per}</b><span>teams per {term}</span></div><div><b>{first}</b><span>first season</span></div></div>'
              f'<p>NCAA 180 is a dynasty fantasy football super league on Sleeper: {n_teams} teams, each named for a college program, '
              f'in {n_conf} {terms} of {per}. Each {term} runs as its own Sleeper league through the regular season and its '
              f'championship game; then all {n_teams} teams meet in one shared postseason — a {field}-team playoff, bowl games and the NIT.</p>')

    cal = (f'<ol class="cal"><li><b>Weeks 1–{lr}</b> Regular season, inside each {term}.</li>'
           f'<li><b>Week {ccg}</b> {term.title()} championship games: the two division winners meet.</li>'
           f'<li><b>Weeks {ccg + 1}–{ccg + 5}</b> Postseason: playoff, bowls and the NIT.</li></ol>'
           f'<p class="sub">Trade deadline: the end of Monday Night Football in week 10.</p>')

    rules = (f'<ul class="rl"><li><b>Format:</b> dynasty, PPR scoring.</li>'
             f'<li><b>Starting lineup:</b> {e(lineup)}; 30 bench spots.</li>'
             f'<li><b>Position limits:</b> QB 10 · RB 25 · WR 25 · TE 15 · K 6 · DEF 6.</li>'
             f'<li><b>Common scoring:</b> {terms} have used different scoring settings over the years, so the site rescores every game '
             f'on one standard scheme to compare across {terms}. From 2026, results are decided on it; a † marks a game where Sleeper\'s '
             f'own number differs.</li>'
             f'<li><b>No waiver wire</b> (except briefly after rookie drafts): free agents are first come, first served.</li>'
             f'<li><b>Trades</b> can be vetoed by the {term} manager or by a 7 of 10 vote (the two teams in the trade don\'t vote; '
             f'6 of 9 for three-team trades, and so on).</li>'
             f'<li><b>Draft picks</b> can be traded two seasons out; the season "resets" after each rookie draft.</li>'
             f'<li><b>No tanking by lineup:</b> you must start a real lineup. To tank, trade players away. The {term} manager can '
             f'edit lineups, including after the fact.</li></ul>')

    post = (f'<h3>Playoff</h3><p>{field} teams: the {n_auto} {term} champions (championship-game winners) plus the {field - n_auto} '
            f'best remaining teams by regular-season record (win %, then points for, then points against). The ranking committee '
            f'seeds the field; the bracket is fixed (1 v {field}, 2 v {field - 1} …), with no reseeding and no byes. The Elite 8 and '
            f'Final Four are hosted by the six playoff bowls on a yearly rotation, and the National Championship follows the real '
            f'title game\'s site.</p>'
            f'<h3>Bowls</h3><p>Every non-playoff team with {bw["min_wins"]}+ wins goes bowling; if the count is odd, the best '
            f'{bw["bump_wins"]}-win team is added. {n_bowls} bowls in four tiers, weakest to strongest: {", ".join(tiers)}. '
            f'Prestige Bowls take the top of the bowl order (poll rank, with each extra win worth '
            f'{bw.get("rank", {}).get("poll_spots_per_win", 25)} poll spots); Marquee Bowls give each {term} a seat. '
            f'Bowl winners earn a compensatory 3rd-round pick (playoff games don\'t count).</p>'
            f'<h3>NIT</h3><p>Everyone else. Group stages of four (seeded by pots from the poll), with each group winner '
            + (f'plus the best-scoring runners-up ("lucky dogs") advancing to {nit.get("round2_field", 28)} teams, then '
               f'{8 - int(nit.get("round2_lucky_dogs", 1))} groups and {nit.get("round2_lucky_dogs", 1)} more lucky dog to an '
               f'8-team bracket: quarterfinals, semifinals and the {e(bw.get("nit_final_label", "final"))}. ' if nit else "advancing, then a bracket. ")
            + f'The NIT winner earns a compensatory 4th-round pick.</p>'
            f'<h3>Rookie draft order</h3><p>{term.title()} champions pick last in their {term}\'s rookie draft and championship-game '
            f'losers pick 11th; everyone else by record.</p>')

    rows = "".join(
        f'<tr><th scope="row">{y}</th><td>{chip(w, col) if w else "—"}'
        f'<small>{e(" over " + (b if w == a else a)) if w and a else ""}</small></td><td>{chip(n, col) if n else "—"}</td></tr>'
        for y, w, (a, b), n in reversed(champs))
    hist = (f'<table class="ct"><thead><tr><th>Season</th><th>National champion</th><th>NIT champion</th></tr></thead>'
            f'<tbody>{rows}</tbody></table><p class="sub">Full results: the Postseason page, season by season.</p>')

    confs = ""
    for lg, g in sorted(teams.groupby("League"), key=lambda x: short.get(x[0].strip(), x[0])):
        name = short.get(lg.strip(), lg.strip())
        divs = "".join(f'<div class="dv"><p>{e(str(d).title())}</p>{"".join(chip(t, col) for t in sorted(dg["Team"]))}</div>'
                       for d, dg in g.groupby("Division Name"))
        confs += f'<details class="cf"><summary>{e(name)} <small>{len(g)} teams</small></summary><div class="dvs">{divs}</div></details>'

    site = ('<ul class="rl">'
            '<li><b>Games</b> — every matchup live on game day, with win chances and each lineup.</li>'
            '<li><b>Poll</b> — the weekly Top 25 from the bot ballots.</li>'
            '<li><b>Postseason</b> — the projected field and bowls during the season, odds and the most impactful games; '
            'every past postseason since 2019.</li>'
            '<li><b>Standings, Weekly Awards, Managers, Records, Roster Map.</b></li>'
            '<li>Anything live is <b>unofficial</b> until the weekly run after stat corrections; projections are estimates.</li></ul>')

    body = (top
            + card("glance", "At a glance", glance)
            + card("directory", "Directory", directory(term, short, col))
            + card("calendar", "The season", cal)
            + card("rules", "Rosters & rules", rules, "from the league bylaws")
            + card("postseason", "Postseason", post)
            + card("champions", "Champions", hist, f"since {first}")
            + card("conferences", terms.title(), confs, f"{n_conf} {terms} · {n_teams} teams")
            + card("site", "This site", site))
    foot = f"{lcfg.brand()} · About · {home.replace('https://', '')}"
    js = """<script>(()=>{const b=document.getElementById('copy-home'),s=document.getElementById('copied');if(!b)return;
b.addEventListener('click',async()=>{const u=b.dataset.url;let ok=false;
try{await navigator.clipboard.writeText(u);ok=true;}catch(e){const t=document.createElement('textarea');t.value=u;document.body.append(t);t.select();
try{ok=document.execCommand('copy');}catch(x){}t.remove();}
s.textContent=ok?'Copied: '+u:u;setTimeout(()=>{s.textContent='';},4000);});
document.querySelectorAll('.un').forEach(x=>x.addEventListener('click',async()=>{const u=x.dataset.u;try{await navigator.clipboard.writeText(u);}catch(e){}
const t=x.textContent;x.textContent='Copied';setTimeout(()=>{x.textContent=t;},1500);}));})();</script>"""
    doc = (page_head(f"About {lcfg.brand()}", CSS)
           + f'<div class="wrap"><nav class="weeks" aria-label="Pages">{nav_html(None)}</nav>'
           + f'<header><h1>About <em>{lcfg.brand()}</em></h1></header>{body}'
           + bp.FOLD_JS + bp.snap_js(0, foot=foot, tag="about", projection=False) + js + "</div></body></html>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(doc)
    return OUT


CSS = bp.CSS + """
.share{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 16px}
.share button,.share .btn{font:700 14px var(--sans,sans-serif);padding:9px 14px;border-radius:8px;border:1px solid var(--line);
 background:var(--panel,#fff);color:inherit;cursor:pointer;text-decoration:none}
.share .btn{background:#5865f2;border-color:#5865f2;color:#fff}
#copied{font-size:12px;color:var(--mute)}
.un{font:700 12px var(--sans,sans-serif);padding:2px 7px;margin:2px 3px 2px 0;border:1px solid var(--line);border-radius:12px;background:var(--panel,#fff);color:inherit;cursor:pointer}
.dl{margin:0 0 6px}.dc{font:700 12px var(--sans,sans-serif);padding:2px 8px;border-radius:12px;background:#5865f2;color:#fff;text-decoration:none}.dd{font-size:12px;color:var(--mute)}.dt th{width:38%}
.inst{margin:-6px 0 16px;font-size:13px}.inst a{font-weight:700}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 0 10px}
.facts div{text-align:center;padding:8px 4px;border:1px solid var(--line);border-radius:8px}
.facts b{display:block;font:800 26px var(--num)}.facts span{font-size:11px;color:var(--mute);text-transform:uppercase;letter-spacing:.04em}
.cal{margin:0;padding-left:18px}.cal li{margin:0 0 6px}.rl{margin:0;padding-left:18px}.rl li{margin:0 0 6px}
.card h3{margin:12px 0 4px;font-size:14px}.card p{margin:0 0 8px}
.ch{display:inline-block;padding:2px 7px;margin:2px 3px 2px 0;border-radius:4px;font-weight:700;font-size:12px}
.ct{border-collapse:collapse;width:100%;font-size:13px}.ct th,.ct td{padding:5px 4px;border-bottom:1px solid var(--line);text-align:left}
.ct td small{display:block;color:var(--mute);font-size:11px}.ct td,.ct th{white-space:normal}
.cf{border-top:1px solid var(--line);padding:6px 0}.cf summary{cursor:pointer;font-weight:700}.cf summary small{color:var(--mute);font-weight:500}
.dvs{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:6px 0 2px}.dv p{margin:0 0 3px;font:700 11px var(--sans,sans-serif);
 text-transform:uppercase;letter-spacing:.04em;color:var(--mute)}
@media(max-width:560px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}.dvs{grid-template-columns:1fr}}
"""


if __name__ == "__main__":
    os.chdir(lcfg.ROOT)
    print(build())
