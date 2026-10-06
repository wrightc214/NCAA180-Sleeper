"""
roster_map.py -- dynasty value vs. contender status for all 180 teams.

Writes:
  data/RosterValues_Season.csv  one row per team per run-week (replaced for the current week)
  reports/roster-map.html        interactive page: All 180 (dots, league colors) + one view
                                 per conference (logos). Hover or tap a team for its card.

Axes
  Dynasty value  = sum of FantasyCalc dynasty value for every player on the roster.
  Contender      = blend of market and results, results gaining weight each week:
                     market  = FantasyCalc redraft value of the best legal starting lineup
                     results = points per game, completed regular-season weeks
                     w = min(games, FADE_GAMES) / FADE_GAMES
                     Contender = (1 - w) * z(market) + w * z(results)     (z across all 180)
                   With FADE_GAMES = 6 the market is fully phased out by week 6, matching the
                   commissioner's old preseason-KTC fade.
  Dynasty value includes future rookie picks: ownership from FuturePicks_Current.csv
  (draft_picks.py), each pick valued at FantasyCalc's round value for that season
  (PickValues_Current.csv). A season FantasyCalc doesn't list uses its latest listed
  season for that round; a round it doesn't list counts 0. All picks in a round are
  valued the same until week 6; then the next draft's picks get an Early/Late bump
  (see pick_tier / pick_values).

Needs data/PlayerValues_Current.csv (player_values.py); exits cleanly without it.
CWD must be repo root.
"""
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import nav_html, page_head  # noqa: E402
from week_status import completed_weeks as finished_weeks  # noqa: E402

ROSTERS = "data/Rosters_Current.csv"
VALUES = "data/PlayerValues_Current.csv"
PICKS = "data/FuturePicks_Current.csv"
PICK_VALUES = "data/PickValues_Current.csv"
MAXPTS = "data/MaxPoints_Season.csv"
MATCHUPS = "data/Matchups_Season.csv"
TEAMS = "data/Teams.csv"
LEAGUE_COLORS = "data/Colors - Leagues.csv"
LEAGUES = "data/LeagueIDs_AllYears.csv"
OUT_CSV = "data/RosterValues_Season.csv"
OUT_HTML = "reports/roster-map.html"
LOGO_DIR = "assets/logos/teams"
FADE_GAMES = 6
LAST_REGULAR_WEEK = 11
DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX"]
ELIGIBLE = {"QB": {"QB"}, "RB": {"RB"}, "WR": {"WR"}, "TE": {"TE"},
            "FLEX": {"RB", "WR", "TE"}, "WRRB_FLEX": {"RB", "WR"},
            "REC_FLEX": {"WR", "TE"}, "SUPER_FLEX": {"QB", "RB", "WR", "TE"}}
LEAGUE_DISPLAY = {
    "NCAA BIG EAST & CO.": "Big East", "NCAA SEC": "SEC", "NCAA PAC 12": "Pac 12",
    "NCAA ACC": "ACC", "NCAA BIG 12": "Big 12", "NCAA SUN BELT": "Sun Belt",
    "NCAA PIONEER": "Pioneer", "NCAA IVY": "Ivy", "NCAA USA": "CUSA",
    "NCAA HISTORICALLY BLACK": "HBCU", "NCAA MOUNTAIN WEST": "Mountain West",
    "NCAA OHIO VALLEY": "Ohio Valley", "NCAA WILD": "Wild", "NCAA BIG 10": "Big 10",
    "NCAA BIG SKY": "Big Sky",
}


def best_lineup(players, slots):
    pool = sorted(players, key=lambda x: -x[0])
    used = [False] * len(pool)
    total = 0.0
    for slot in sorted(slots, key=lambda s: len(ELIGIBLE.get(s, ()))):
        ok = ELIGIBLE.get(slot)
        if not ok:
            continue  # K / DEF / unknown: FantasyCalc doesn't value them
        for i, (v, pos) in enumerate(pool):
            if not used[i] and pos in ok:
                used[i] = True
                total += v
                break
    return total


TIER_START_WEEK = 6   # before this, every pick uses the plain round value
TIER_FULL_WEEK = 11   # end of regular season: thresholds and bump at full strength


def pick_tier(win_val, games):
    """Early / Late / '' for the original team's NEXT-draft pick.
    Week 6 rule (commissioner): 0-1 wins -> Early, 5-6 wins -> Late, else plain.
    Scaled by games played, with the band toward 'plain' narrowing from 1/6..5/6 of
    games at week 6 to 1/3..2/3 by week 11 (bias toward the middle fades)."""
    if games < TIER_START_WEEK:
        return ""
    f = min(1.0, (games - TIER_START_WEEK) / (TIER_FULL_WEEK - TIER_START_WEEK))
    pct = win_val / games
    if pct <= 1 / 6 + f * (1 / 3 - 1 / 6) + 1e-9:
        return "Early"
    if pct >= 5 / 6 - f * (5 / 6 - 2 / 3) - 1e-9:
        return "Late"
    return ""


def pick_values(rec):
    """Per (LeagueID, OwnerRosterID): (total pick value, holdings summary).
    rec: {(LeagueID, RosterID): (win_value, games)} for the original teams.
    Only the next draft season can get an Early/Late bump; later seasons are plain.
    Bumped value = plain + s * (tier - plain), s from 0.5 at week 6 to 1.0 by week 11."""
    if not (os.path.exists(PICKS) and os.path.exists(PICK_VALUES)):
        print("Pick files missing; dynasty value excludes picks this run.")
        return {}
    fp = pd.read_csv(PICKS, dtype=str)
    pv = pd.read_csv(PICK_VALUES)
    val, tierv = {}, {}
    for r in pv.itertuples():
        k = (int(r.Season), int(r.Round))
        val[k] = float(r.Value)
        for t in ("Early", "Late"):
            v = getattr(r, t, None)
            if v is not None and pd.notna(v) and str(v) != "":
                tierv[(k, t)] = float(v)
    latest = {}
    for (se, rd), v in sorted(val.items()):
        latest[rd] = v
    next_season = int(fp["Season"].astype(int).min()) if len(fp) else None
    ords = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}
    tm = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig")
    team_of = {(r.League, r._3): r.Team for r in tm.itertuples()}  # _3 = "Roster ID"
    lname = dict(zip(fp["LeagueID"], fp["LeagueName"]))
    seasons = sorted(fp["Season"].astype(int).unique())
    span = f"{seasons[0]}" + (f"–{str(seasons[-1])[2:]}" if len(seasons) > 1 else "") if seasons else ""

    def name(lid, rid):
        return team_of.get((lname.get(lid), str(rid)), f"roster {rid}")

    out = {}
    for (lid, owner), g in fp.groupby(["LeagueID", "OwnerRosterID"]):
        total, added, own_tier = 0.0, [], ""
        for r in g.itertuples():
            se, rd, orig = int(r.Season), int(r.Round), r.OriginalRosterID
            base = val.get((se, rd), latest.get(rd, 0.0))
            v, tag = base, ""
            if se == next_season and (lid, orig) in rec:
                wv, games = rec[(lid, orig)]
                tier = pick_tier(wv, games)
                if tier and ((se, rd), tier) in tierv:
                    f = min(1.0, (games - TIER_START_WEEK) / (TIER_FULL_WEEK - TIER_START_WEEK))
                    v = base + (0.5 + 0.5 * f) * (tierv[((se, rd), tier)] - base)
                    tag = f", {tier.lower()}"
                    if orig == owner:
                        own_tier = tier
            total += v
            if orig != owner:
                added.append(f"{se} {ords.get(rd, rd)} ({name(lid, orig)}{tag})")
        gone = fp[(fp["LeagueID"] == lid) & (fp["OriginalRosterID"] == owner) & (fp["OwnerRosterID"] != owner)]
        traded = [f"{int(r.Season)} {ords.get(int(r.Round), r.Round)} (to {name(lid, r.OwnerRosterID)})"
                  for r in gone.sort_values(["Season", "Round"]).itertuples()]
        if not added and not traded:
            text = f"Holds all its own picks, {span}."
        else:
            bits = []
            if added:
                bits.append("Acquired: " + ", ".join(sorted(added)))
            if traded:
                bits.append("Traded away: " + ", ".join(traded))
            text = " · ".join(bits)
        if own_tier:
            text += f" Own {next_season} picks project {own_tier.lower()}."
        out[(lid, owner)] = (round(total), text)
    return out


def zscore(s):
    sd = s.std(ddof=0)
    return (s - s.mean()) / sd if sd else s * 0


def main():
    if not os.path.exists(VALUES):
        print(f"{VALUES} missing (run player_values first); skipping roster map.")
        return
    ro = pd.read_csv(ROSTERS, dtype=str)
    year = ro["Year"].iloc[0]
    ro = ro[ro["Year"] == year]
    pv = pd.read_csv(VALUES, dtype={"SleeperID": str})
    ro = ro.merge(pv[["SleeperID", "DynastyValue", "RedraftValue", "Position"]].rename(
        columns={"SleeperID": "PlayerID", "Position": "VPos"}), on="PlayerID", how="left")
    ro["Pos"] = ro["VPos"].fillna(ro["Position"]).replace({"FB": "RB"})
    ro[["DynastyValue", "RedraftValue"]] = ro[["DynastyValue", "RedraftValue"]].fillna(0)

    slots = {}
    if os.path.exists(LEAGUES):
        lg = pd.read_csv(LEAGUES, dtype=str)
        if "RosterPositions" in lg.columns:
            for r in lg[lg["Year"] == year].itertuples():
                if isinstance(r.RosterPositions, str):
                    slots[r.LeagueID] = [x for x in r.RosterPositions.split(",")
                                         if x not in ("BN", "IR", "TAXI", "K", "DEF")]

    rows = []
    for (lid, lname, rid), g in ro.groupby(["LeagueID", "LeagueName", "RosterID"]):
        rows.append({"LeagueID": lid, "LeagueName": lname, "RosterID": rid,
                     "DynastyTotal": round(g["DynastyValue"].sum()),
                     "LineupRedraft": round(best_lineup(list(zip(g["RedraftValue"], g["Pos"])),
                                                        slots.get(lid, DEFAULT_SLOTS)))})
    t = pd.DataFrame(rows)

    m = pd.read_csv(MATCHUPS, dtype=str)
    m["Week"] = m["Week"].astype(int)
    m["P"] = m["PointsFor"].astype(float)
    reg = m[m["Week"].isin([w for w in finished_weeks(year) if w <= LAST_REGULAR_WEEK])]
    rec = reg.groupby(["LeagueID", "RosterID"]).agg(
        Owner=("OwnerName", "last"), G=("P", "size"), PPG=("P", "mean"),
        W=("Outcome", lambda x: int((x == "Win").sum())),
        L=("Outcome", lambda x: int((x == "Loss").sum())),
        T=("Outcome", lambda x: int((x == "Tie").sum()))).reset_index()
    t = t.merge(rec, on=["LeagueID", "RosterID"], how="left")
    owners = m.drop_duplicates(["LeagueID", "RosterID"]).set_index(["LeagueID", "RosterID"])["OwnerName"]
    t["Owner"] = t["Owner"].fillna(pd.Series([owners.get(k, "") for k in zip(t.LeagueID, t.RosterID)], index=t.index))
    t[["G", "W", "L", "T"]] = t[["G", "W", "L", "T"]].fillna(0).astype(int)
    pk = pick_values({(r.LeagueID, r.RosterID): (r.W + 0.5 * r.T, r.G) for r in t.itertuples()})
    t["PlayerDynasty"] = t["DynastyTotal"]
    t["PickValue"] = [pk.get((a, b), (0, ""))[0] for a, b in zip(t.LeagueID, t.RosterID)]
    t["Picks"] = [pk.get((a, b), (0, ""))[1] for a, b in zip(t.LeagueID, t.RosterID)]
    t["DynastyTotal"] = t["PlayerDynasty"] + t["PickValue"]
    games = int(t["G"].max()) if len(t) else 0
    w = min(games, FADE_GAMES) / FADE_GAMES
    t["PPG"] = t["PPG"].fillna(t["PPG"].mean() if games else 0)
    t["Contender"] = (1 - w) * zscore(t["LineupRedraft"]) + (w * zscore(t["PPG"]) if games else 0)
    # Lineup efficiency: season points / season max possible, finished regular-season weeks
    t["Eff"] = float("nan")
    if os.path.exists(MAXPTS):
        mxp = pd.read_csv(MAXPTS, dtype={"LeagueID": str, "RosterID": str})
        fin = [w for w in finished_weeks(year) if w <= LAST_REGULAR_WEEK]
        mxp = mxp[mxp["Week"].astype(int).isin(fin)]
        e = mxp.groupby(["LeagueID", "RosterID"]).agg(pf=("PointsFor", "sum"), mx=("MaxPoints", "sum"))
        e = (e["pf"] / e["mx"]).rename("Eff").reset_index()
        t = t.drop(columns="Eff").merge(e, on=["LeagueID", "RosterID"], how="left")
    t["EffRank"] = t["Eff"].rank(ascending=False, method="min").fillna(0).astype(int)
    t["PickValueRank"] = t["PickValue"].rank(ascending=False, method="min").astype(int)
    for c in ("DynastyTotal", "LineupRedraft", "Contender", "PPG"):
        t[c + "Rank"] = t[c].rank(ascending=False, method="min").astype(int)

    tm = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig").rename(
        columns={"League": "LeagueName", "Roster ID": "RosterID"})
    t = t.merge(tm[["LeagueName", "RosterID", "Team"]], on=["LeagueName", "RosterID"], how="left")
    t["Team"] = t["Team"].fillna(t["Owner"])
    t["Lg"] = t["LeagueName"].map(LEAGUE_DISPLAY).fillna(t["LeagueName"])

    week = games
    t["Year"], t["Week"], t["ResultsWeight"] = year, week, round(w, 3)
    keep = ["Year", "Week", "LeagueID", "LeagueName", "RosterID", "Team", "Owner", "W", "L", "T",
            "PPG", "DynastyTotal", "PlayerDynasty", "PickValue", "Picks", "LineupRedraft", "Contender", "ResultsWeight"]
    out = t[keep].copy()
    out["PPG"] = out["PPG"].round(2)
    out["Contender"] = out["Contender"].round(3)
    if os.path.exists(OUT_CSV):
        old = pd.read_csv(OUT_CSV, dtype=str)
        old = old[~((old["Year"] == str(year)) & (old["Week"] == str(week)))]
        out = pd.concat([old, out.astype(str)], ignore_index=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}: week {week}, results weight {w:.2f}")

    lc = pd.read_csv(LEAGUE_COLORS, dtype=str, encoding="utf-8-sig")
    up = {k.upper(): v for k, v in LEAGUE_DISPLAY.items()}
    tc = pd.read_csv("data/Colors - Teams.csv", dtype=str, encoding="utf-8-sig")
    team_colors = {r.Team: [r.Background, r.Font] for r in tc.itertuples()
                   if isinstance(r.Background, str) and isinstance(r.Font, str)}
    colors = {}
    for r in lc.itertuples():
        s = up.get(str(r.League).upper())
        if s and isinstance(r.Background, str):
            colors[s] = r.Background if r.Background.startswith("#") else "#" + r.Background

    teams = []
    for r in t.itertuples():
        logo = os.path.exists(os.path.join(LOGO_DIR, f"{r.Team}.png"))
        teams.append({"team": r.Team, "owner": r.Owner, "lg": r.Lg,
                      "rec": f"{r.W}-{r.L}" + (f"-{r.T}" if r.T else ""),
                      "ppg": round(float(r.PPG), 1), "dyn": int(r.DynastyTotal),
                      "red": int(r.LineupRedraft), "pv": int(r.PickValue), "pvR": int(r.PickValueRank),
                      "eff": None if pd.isna(r.Eff) else round(float(r.Eff) * 100, 1), "effR": int(r.EffRank), "picks": r.Picks, "con": round(float(r.Contender), 3),
                      "dynR": int(r.DynastyTotalRank), "redR": int(r.LineupRedraftRank),
                      "conR": int(r.ContenderRank), "ppgR": int(r.PPGRank),
                      "logo": f"../{LOGO_DIR}/{r.Team}.png" if logo else None})
    payload = {"teams": teams, "colors": colors, "tcolors": team_colors, "week": week, "w": round(w, 2),
               "leagues": sorted(set(t["Lg"]))}
    page = page_head("NCAA 180 Roster Map", MAP_CSS) + MAP_BODY.replace(
        "{{NAV}}", nav_html("map")).replace("{{WEEK}}", str(week)).replace(
        "{{WPCT}}", f"{round(w * 100)}").replace(
        "{{DATA}}", json.dumps(payload).replace("</", "<\\/"))
    os.makedirs("reports", exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {OUT_HTML}")


MAP_CSS = """
.picker{display:flex;flex-wrap:wrap;gap:6px}
.picker button{font:600 13px var(--num);letter-spacing:.04em;padding:5px 10px;border:1px solid var(--line);
 border-radius:3px;background:var(--panel);color:var(--ink);cursor:pointer}
.picker button[aria-pressed=true]{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.picker button:focus-visible,.dot:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chartwrap{position:relative;width:100%}
svg.map{width:100%;height:auto;display:block;overflow:visible}
.ax{stroke:var(--ink);stroke-width:1.5}.mid{stroke:var(--line);stroke-dasharray:4 4}
.qlab{fill:var(--mute);font:600 11px var(--num);letter-spacing:.12em;text-transform:uppercase}
.axlab{fill:var(--mute);font:600 12px var(--num);letter-spacing:.12em;text-transform:uppercase}
.dot{cursor:pointer}
.dot.sel .pt,.dot.sel .ring{stroke:var(--accent)!important;stroke-width:3.5}
.ring{fill:var(--panel);stroke:var(--line);stroke-width:1}
.lsel{display:none;font:600 14px var(--num)}.lsel select{font:600 15px var(--num);padding:6px 8px;margin-left:6px;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink)}
@media (max-width:640px){.picker{display:none}.lsel{display:block}}
.tlab{fill:var(--ink);font-weight:600;font-family:var(--body);text-anchor:middle;paint-order:stroke;stroke:var(--panel);stroke-width:3px}
.card{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:start;min-height:120px}
.card img{width:72px;height:72px;object-fit:contain}
.card h3{margin:0;font:700 22px var(--disp);text-transform:uppercase;letter-spacing:.03em}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px 16px;margin-top:8px}
.stats div b{display:block;font:600 22px var(--num);font-variant-numeric:tabular-nums}
.stats div span{font:600 11px var(--num);letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}
.hint{color:var(--mute);font-size:13px}
.qlab.go{cursor:pointer;fill:var(--ink);text-decoration:underline;text-decoration-color:var(--line)}
.ctr{fill:transparent;stroke:var(--mute);stroke-opacity:.55;stroke-dasharray:3 5;cursor:zoom-in}
.ctr:hover{fill:var(--ink);fill-opacity:.04}
.zoombar{display:none;align-items:center;gap:10px;margin:6px 0}
.zoombar.on{display:flex}
.zoombar button{font:600 13px var(--num);padding:5px 10px;border:1px solid var(--ink);border-radius:3px;background:var(--ink);color:var(--panel);cursor:pointer}
.zoombar b{font:700 18px var(--disp);text-transform:uppercase;letter-spacing:.03em}
"""

MAP_BODY = """
<div class="wrap">
<nav class="weeks" aria-label="Pages">{{NAV}}</nav>
<header>
  <div><div class="eyebrow">15 conferences · 180 teams · after week {{WEEK}}</div><h1>Roster <em>Map</em></h1></div>
</header>
<section>
  <h2>Dynasty value vs. contender <small>Tap a team</small></h2>
  <div class="picker" id="picker" role="group" aria-label="Conference"></div>
  <label class="lsel">Conference <select id="lsel"></select></label>
  <div class="zoombar" id="zoombar"><button type="button" id="zback">← All 180</button><b id="ztitle"></b><span class="hint" id="zcount"></span></div>
  <div class="chartwrap"><svg class="map" id="map" viewBox="0 0 800 560" role="img" aria-label="Scatter of dynasty value against contender score"></svg></div>
  <p class="note">Right = more total dynasty value (FantasyCalc: whole roster plus future rookie picks). Up = stronger contender:
  a blend of the best lineup's redraft value and actual points per game. Results count {{WPCT}}% this week
  and take over fully by week 6. Dashed lines are the NCAA 180 medians. Tap a corner label to zoom into that quadrant, or the dotted center box
  (the middle half on both axes) to zoom into the middle of the pack. From week 6, next year's picks from clearly bad or good teams get an early/late bump.</p>
</section>
<section id="card" aria-live="polite"><p class="hint">Hover or tap a team to see its numbers.</p></section>
<footer>Values: FantasyCalc (1 QB, 12 teams, PPR). Results: Sleeper, via the NCAA180-Sleeper pipeline.</footer>
</div>
<script>
const D = {{DATA}};
let W = 800, H = 560; const M = {l: 46, r: 24, t: 20, b: 46};
const svg = document.getElementById('map'), NS = 'http://www.w3.org/2000/svg';
const med = a => { const s = [...a].sort((x, y) => x - y), n = s.length; return n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2; };
const mx = med(D.teams.map(t => t.dyn)), my = med(D.teams.map(t => t.con));
const pct = (a, p) => { const s = [...a].sort((x, y) => x - y), i = (s.length - 1) * p, lo = Math.floor(i);
  return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (i - lo); };
const dyns = D.teams.map(t => t.dyn), cons = D.teams.map(t => t.con);
const box = {x0: pct(dyns, .25), x1: pct(dyns, .75), y0: pct(cons, .25), y1: pct(cons, .75)};
// Zoom views: quadrants split at the medians; Center = middle half on BOTH axes (25th-75th pct).
const ZOOM = {
  'Loaded':   t => t.dyn >= mx && t.con >= my,
  'Win now':  t => t.dyn <  mx && t.con >= my,
  'Building': t => t.dyn >= mx && t.con <  my,
  'Rebuild':  t => t.dyn <  mx && t.con <  my,
  'Center':   t => t.dyn >= box.x0 && t.dyn <= box.x1 && t.con >= box.y0 && t.con <= box.y1,
};
const HASH = {'loaded': 'Loaded', 'win-now': 'Win now', 'building': 'Building', 'rebuild': 'Rebuild', 'center': 'Center'};
const slug = v => Object.keys(HASH).find(k => HASH[k] === v) || '';
const valid = v => v === 'All 180' || D.leagues.includes(v) || v in ZOOM;
let view = 'All 180', sel = null;
try { const v = localStorage.getItem('rm-view'); if (v && valid(v)) view = v; } catch (e) {}
if (HASH[location.hash.slice(1)]) view = HASH[location.hash.slice(1)];
function go(v) {
  view = v; sel = null;
  try { localStorage.setItem('rm-view', v); } catch (e) {}
  try { history.replaceState(null, '', slug(v) ? '#' + slug(v) : location.pathname + location.search); } catch (e) {}
  draw();
}
window.addEventListener('hashchange', () => { const v = HASH[location.hash.slice(1)]; if (v && v !== view) { view = v; sel = null; draw(); } });
document.getElementById('zback').onclick = () => go('All 180');

const picker = document.getElementById('picker'), lsel = document.getElementById('lsel');
['All 180', ...D.leagues].forEach(n => { const o = document.createElement('option'); o.textContent = n; lsel.appendChild(o); });
lsel.onchange = () => go(lsel.value);
let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(draw, 150); });
['All 180', ...D.leagues].forEach(name => {
  const b = document.createElement('button'); b.type = 'button'; b.textContent = name;
  b.onclick = () => go(name);
  picker.appendChild(b);
});
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); (parent || svg).appendChild(e); return e; }
function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c])); }
function paleHex(h) { const m = /^#?([0-9a-f]{6})$/i.exec(String(h).trim()); if (!m) return false;
  const n = parseInt(m[1], 16), r = n >> 16 & 255, g = n >> 8 & 255, b = n & 255;
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 > 0.82; }
function fmt(n) { return n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n); }

function draw() {
  [...picker.children].forEach(b => b.setAttribute('aria-pressed', b.textContent === view));
  const narrow = svg.parentNode.clientWidth < 600;
  W = narrow ? 400 : 800; H = narrow ? 520 : 560; svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const zoom = view in ZOOM;
  if (lsel) lsel.value = zoom ? 'All 180' : view;
  svg.textContent = '';
  const all = view === 'All 180';
  const ts = all ? D.teams : zoom ? D.teams.filter(ZOOM[view]) : D.teams.filter(t => t.lg === view);
  const zb = document.getElementById('zoombar'); zb.classList.toggle('on', zoom);
  if (zoom) { document.getElementById('ztitle').textContent = view;
    document.getElementById('zcount').textContent = `${ts.length} teams`; }
  const fx = v => v;  // linear: real dynasty totals are near-symmetric (sqrt tested, no gain)
  const xs = ts.map(t => fx(t.dyn)).concat(view === 'Center' ? [box.x0, box.x1] : [fx(mx)]),
        ys = ts.map(t => t.con).concat(view === 'Center' ? [box.y0, box.y1] : [my]);
  let x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys);
  const px = (x1 - x0) * 0.1 || 1, py = (y1 - y0) * 0.16 || 0.1; x0 -= px; x1 += px; y0 -= py; y1 += py;
  const X = v => M.l + (fx(v) - x0) / (x1 - x0) * (W - M.l - M.r), Y = v => H - M.b - (v - y0) / (y1 - y0) * (H - M.t - M.b);
  el('line', {x1: X(mx), x2: X(mx), y1: M.t, y2: H - M.b, class: 'mid'});
  el('line', {x1: M.l, x2: W - M.r, y1: Y(my), y2: Y(my), class: 'mid'});
  el('line', {x1: M.l, x2: M.l, y1: M.t, y2: H - M.b, class: 'ax'});
  el('line', {x1: M.l, x2: W - M.r, y1: H - M.b, y2: H - M.b, class: 'ax'});
  if (all) {  // tap the dotted middle box (white space) to zoom to the center of the pack
    const cb = el('rect', {x: X(box.x0), y: Y(box.y1), width: X(box.x1) - X(box.x0), height: Y(box.y0) - Y(box.y1),
                           class: 'ctr', role: 'button', tabindex: 0, 'aria-label': 'Zoom to the middle of the pack'});
    cb.addEventListener('click', () => go('Center'));
    cb.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go('Center'); } });
  }
  const q = (x, y, t, a) => { if (view === t) return;
    const e = el('text', {x, y, class: 'qlab' + (all ? ' go' : ''), 'text-anchor': a}); e.textContent = t;
    if (all) { e.setAttribute('role', 'button'); e.setAttribute('tabindex', 0);
      e.addEventListener('click', () => go(t));
      e.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); go(t); } }); } };
  if (!zoom || view === 'Center') {
    q(W - M.r - 4, M.t + 14, 'Loaded', 'end'); q(M.l + 8, M.t + 14, 'Win now', 'start');
    q(W - M.r - 4, H - M.b - 8, 'Building', 'end'); q(M.l + 8, H - M.b - 8, 'Rebuild', 'start');
  }
  const xl = el('text', {x: (M.l + W - M.r) / 2, y: H - 12, class: 'axlab', 'text-anchor': 'middle'}); xl.textContent = 'Dynasty value →';
  const yl = el('text', {x: 14, y: (M.t + H - M.b) / 2, class: 'axlab', 'text-anchor': 'middle', transform: `rotate(-90 14 ${(M.t + H - M.b) / 2})`}); yl.textContent = 'Contender →';
  const r = all ? (narrow ? 4.5 : 6) : zoom ? (narrow ? 9 : 12) : (narrow ? 15 : 22);
  ts.slice().sort((a, b) => (a === sel) - (b === sel)).forEach(t => {
    const g = el('g', {class: 'dot' + (t === sel ? ' sel' : ''), tabindex: 0, role: 'button', 'aria-label': `${t.team}, ${t.owner}`});
    const cx = X(t.dyn), cy = Y(t.con);
    if (!all && t.logo) {
      el('circle', {cx, cy, r: r + 3, class: 'ring'}, g);
      el('image', {href: encodeURI(t.logo), x: cx - r, y: cy - r, width: r * 2, height: r * 2, preserveAspectRatio: 'xMidYMid meet'}, g);
    } else {
      const tc = D.tcolors[t.team];  // two-tone: school primary fill, secondary ring
      // Near-white secondaries overwhelm the chart in dark mode: give those a hairline neutral ring instead.
      const pale = !tc || paleHex(tc[1]);
      const ring = pale ? 'var(--mute)' : tc[1];
      el('circle', {cx, cy, r: all ? r : 10, fill: tc ? tc[0] : (D.colors[t.lg] || '#888'),
                    stroke: ring, 'stroke-width': all ? (pale ? 0.8 : 1.6) : 2.5, class: 'pt'}, g);
    }
    el('circle', {cx, cy, r: all ? 11 : r + 4, fill: 'transparent'}, g);  // larger tap target (sits above the center box)
    if (!all && !zoom) { const lb = el('text', {x: cx, y: cy + r + (narrow ? 12 : 15), class: 'tlab', 'font-size': narrow ? 9 : 11}, g); lb.textContent = t.team; }
    const pick = () => { sel = t; show(t); draw(); };
    g.addEventListener('mouseenter', () => show(t));
    g.addEventListener('click', pick);
    g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
  });
  if (sel && ts.includes(sel)) show(sel);
}
function show(t) {
  const c = document.getElementById('card');
  c.innerHTML = `<div class="card">${t.logo ? `<img src="${encodeURI(t.logo)}" alt="">` : '<span></span>'}
  <div><h3>${esc(t.team)}</h3><div class="hint">${esc(t.owner)} · ${esc(t.lg)} · ${esc(t.rec)}</div>
  <div class="stats">
   <div><b>${fmt(t.dyn)}</b><span>Dynasty value · #${t.dynR}</span></div>
   <div><b>${fmt(t.pv)}</b><span>Draft picks · #${t.pvR}</span></div>
   <div><b>${fmt(t.red)}</b><span>Lineup value · #${t.redR}</span></div>
   <div><b>${t.ppg}</b><span>Points per game · #${t.ppgR}</span></div>
   <div><b>#${t.conR}</b><span>Contender rank of 180</span></div>
   ${t.eff == null ? '' : `<div><b>${t.eff}%</b><span>Lineup efficiency · #${t.effR}</span></div>`}
  </div>${t.picks ? `<p class="hint">${esc(t.picks)}</p>` : ''}</div></div>`;
}
draw();
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
