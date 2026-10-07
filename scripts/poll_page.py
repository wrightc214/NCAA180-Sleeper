"""
poll_page.py -- reports/poll.html (latest official poll) plus one archive page per
published poll this season (reports/poll-<type>-wkNN.html), built from data/Poll_Season.csv.

Static HTML (no script needed), so poll_png.py can screenshot sections for Discord.
Sections: the poll (rank, movement, team in its colors, record, points, first-place
votes), others receiving votes + dropped out, ranked games in the week it applies to,
and the computer ranking alongside. Team blocks use site_common.team_colors().
CWD must be repo root. Run after poll_aggregate.py.
"""
import html
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from site_common import nav_html, page_head, team_colors  # noqa: E402
from poll_aggregate import ranked_games  # noqa: E402

COLORS = "data/Colors - Teams.csv"
OUT_DIR = "reports"
e = html.escape

CSS = """
.pt{display:inline-block;padding:3px 9px;border-radius:3px;font-weight:700;line-height:1.25}
td.tm .pt{margin-right:8px}
td.rk{font:700 18px var(--num);width:42px;text-align:right}
.fpv{color:var(--mute);font-size:12px}
.orv{line-height:1.9}
.orv .pt{font-size:13px;padding:1px 7px;margin:0 4px 0 0}
.archive{display:flex;flex-wrap:wrap;gap:6px 14px;font:600 14px var(--num)}
.archive a{color:var(--accent)}.archive b{color:var(--ink)}
ul.games{list-style:none;margin:0;padding:0;display:grid;gap:6px}
ul.games li{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
ul.games .vs{color:var(--mute);font:600 12px var(--num);letter-spacing:.1em}
.rvr{border-left:4px solid var(--gold);padding-left:8px}
"""


def colors():
    c = pd.read_csv(COLORS, dtype=str, encoding="utf-8-sig").fillna("")
    return {r.Team: team_colors(r.Primary, r.Secondary, r.Background, r.Text, name=r.Team) for r in c.itertuples()}


def pill(team, col, rank=None):
    bg, fg = col.get(team, ("#14213a", "#ffffff"))
    r = f"#{rank} " if rank else ""
    return f'<span class="pt" style="background:{bg};color:{fg}">{e(r)}{e(team)}</span>'


def rec(r):
    if r.Wins == "" or pd.isna(r.Wins):
        return ""
    t = int(float(r.Ties)) if str(r.Ties) not in ("", "nan") else 0
    return f"{int(float(r.Wins))}-{int(float(r.Losses))}" + (f"-{t}" if t else "")


def mv(r, first=False):
    if first:
        return ""
    if str(r.PrevRank) in ("", "nan"):
        return '<span class="up">NEW</span>' if r.Status == "Ranked" else ""
    x = int(float(r.Move)) if str(r.Move) not in ("", "nan") else 0
    return (f'<span class="up">▲{x}</span>' if x > 0 else f'<span class="dn">▼{-x}</span>' if x < 0
            else '<span class="eq">–</span>')


def fname(ptype, week):
    return f"poll-{ptype.lower()}-wk{int(week):02d}.html"


def page(cfg, poll, comp, archive, col, year, week, ptype, prev_ranked):
    pcfg = pc.poll_cfg(cfg, ptype)
    label, size = pcfg.get("label", ptype), int(pcfg["size"])
    ranked = poll[poll["Status"] == "Ranked"]
    orv = poll[poll["Status"] == "ORV"]
    nb = int(poll["Ballots"].iloc[0])
    human = nb - (1 if cfg.get("computer_ballot", {}).get("enabled", True) else 0)

    first = not prev_ranked and poll["PrevRank"].replace("", None).isna().all()
    rows = "".join(
        f'<tr><td class="rk">{"T-" if r.Tied == "True" else ""}{int(r.Rank)}</td><td class="mv">{mv(r, first)}</td>'
        f'<td class="tm">{pill(r.Team, col)}<small>{rec(r)} · {e(r.League)}</small></td>'
        f'<td class="n">{float(r.Points):g}</td>'
        f'<td class="n fpv">{"(" + str(int(float(r.FirstPlaceVotes))) + ")" if float(r.FirstPlaceVotes) else ""}</td></tr>'
        for r in ranked.itertuples())
    orv_html = ", ".join(f'{e(r.Team)} {float(r.Points):g}' for r in orv.itertuples()) or "None"
    now_keys = set(zip(ranked["LeagueID"], ranked["RosterID"]))
    dropped = [t for k, t in prev_ranked.items() if k not in now_keys]
    dropped_html = ", ".join(e(t) for t in dropped) or "None"

    games = ranked_games(cfg, year, week, poll)
    if len(games):
        g = "".join(
            f'<li class="{"rvr" if str(r.RankedVsRanked) == "True" else ""}">{pill(r.Team, col, r.Rank)}'
            f'<span class="vs">VS</span>{pill(r.OppTeam, col, r.OppRank if str(r.OppRank) not in ("", "nan") else None)}'
            f'<small>{e(str(r.LeagueName))}</small></li>' for r in games.itertuples())
        games_html = (f'<section><h2>Ranked games <small>Week {week + 1}</small></h2><ul class="games">{g}</ul>'
                      f'<p class="note">Gold bar: ranked vs. ranked.</p></section>')
    else:
        games_html = ""

    c25 = comp.head(size)
    crow = "".join(
        f'<tr><td class="rk">{int(r.Rank)}</td><td class="mv">{mv(r, str(r.PrevRank) in ("", "nan") and c25["PrevRank"].isin(["", "nan"]).all())}</td>'
        f'<td class="tm">{pill(r.Team, col)}<small>{rec(r)} · {float(r.PF):.2f} PF</small></td></tr>'
        for r in c25.itertuples())

    arch = " ".join(
        (f'<b>{e(a_label)} wk {w}</b>' if (t == ptype and w == week) else f'<a href="{fname(t, w)}">{e(a_label)} wk {w}</a>')
        for t, w, a_label in archive)

    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("poll")}</nav>
<header><div><div class="eyebrow">Results through week {week} · applies to week {week + 1} games</div>
<h1>NCAA 180 <em>{e(label)}</em></h1></div>
<div class="kpis"><div class="kpi"><b>{human}</b><span>Panel ballots</span></div>
<div class="kpi"><b>+1</b><span>Computer ballot</span></div></div></header>
<section id="poll"><h2>{e(label)} <small>Points (first-place votes)</small></h2>
<div class="tbl"><table><thead><tr><th class="r">Rk</th><th></th><th>Team</th><th class="r">Pts</th><th></th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="orv"><b>Others receiving votes:</b> {orv_html}</p>
{"" if first else f'<p class="orv"><b>Dropped out:</b> {dropped_html}</p>'}</section>
{games_html}
<section id="computer"><h2>Computer ranking <small>Wins, then points · counts as one ballot</small></h2>
<div class="tbl"><table><tbody>{crow}</tbody></table></div></section>
<section><h2>Archive <small>{year}</small></h2><div class="archive">{arch}</div>
<p class="note">Each ballot ranks {size} teams; #1 earns {size} points down to 1 point for #{size}. Every ballot counts
equally, including the computer's. Ties in points go to more first-place votes, then the computer rank.
<a href="../data/Poll_Season.csv">Raw CSV</a></p></section>
</div></body></html>
"""
    return page_head(f"NCAA 180 {label}", CSS) + body


def main():
    if not os.path.exists(pc.POLL_SEASON):
        print(f"{pc.POLL_SEASON} missing; skipping poll page.")
        return
    cfg = pc.config()
    p = pd.read_csv(pc.POLL_SEASON, dtype=str).fillna("")
    year = int(p["Year"].astype(int).max())
    p = p[p["Year"] == str(year)]
    off = p[p["PollType"] != "Computer"]
    if off.empty:
        print("No official poll published yet; skipping poll page.")
        return
    col = colors()
    polls = (off[["PollType", "ThroughWeek"]].drop_duplicates()
             .assign(w=lambda d: d["ThroughWeek"].astype(int)).sort_values("w"))
    archive = [(r.PollType, r.w, pc.poll_cfg(cfg, r.PollType).get("label", r.PollType)) for r in polls.itertuples()]
    os.makedirs(OUT_DIR, exist_ok=True)
    html_latest = None
    prev = {}
    for ptype, w, _ in archive:
        poll = off[(off["PollType"] == ptype) & (off["ThroughWeek"] == str(w))].copy()
        poll["_r"] = poll["Rank"].astype(int)
        poll = poll.sort_values(["_r", "Team"])
        comp = p[(p["PollType"] == "Computer") & (p["ThroughWeek"] == str(w))].copy()
        comp = comp.assign(_r=comp["Rank"].astype(int)).sort_values("_r")
        doc = page(cfg, poll, comp, archive, col, year, w, ptype, prev)
        with open(os.path.join(OUT_DIR, fname(ptype, w)), "w", encoding="utf-8") as f:
            f.write(doc)
        ranked = poll[poll["Status"] == "Ranked"]
        prev = {(r.LeagueID, r.RosterID): r.Team for r in ranked.itertuples()}
        html_latest = doc
    with open(os.path.join(OUT_DIR, "poll.html"), "w", encoding="utf-8") as f:
        f.write(html_latest)
    print(f"Wrote {OUT_DIR}/poll.html + {len(archive)} archive page(s)")


if __name__ == "__main__":
    main()
