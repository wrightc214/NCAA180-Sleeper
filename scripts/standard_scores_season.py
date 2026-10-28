"""Current-season standard scores (Chris, 2026-10-15 / 2026-10-28).

From config postseason.standard_scoring_from (2026) results are decided on the standard ruleset:
the season's majority league ruleset plus config scoring.overrides (the same rules the live
scoreboard applies). Leagues whose Sleeper settings differ (2026: Big Sky DEF 550+ yds,
Ohio Valley missed XP) are restated per starter from Sleeper's weekly stat lines:

    standard = Sleeper points + sum over starters of (standard rule - league rule) x stat

Writes
  data/ScoresStandard_Season.csv   Year, LeagueID, LeagueName, Week, RosterID,
                                   PointsOfficial, PointsStandard, Delta (every team-week played)
  data/ScoringFlags_Season.csv     games whose winner differs between Sleeper and standard
  data/standard/<season>/stats_wkNN.json   slim cache: restated stats of the starters involved

Red alert (Chris): a NEW winner change posts to lm-private-data and pings Chris
(DISCORD_WEBHOOK_LM_PRIVATE_DATA; STANDARD_ALERT=0 disables). State: data/StandardAlerts_Season.json.

Run after score_details.py (needs Scores_Season.csv + Matchups_Season.csv). Needs Sleeper
access (GitHub runner). --offline uses only the cached stat files.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league_config as lcfg  # noqa: E402

OUT_SCORES = "data/ScoresStandard_Season.csv"
OUT_FLAGS = "data/ScoringFlags_Season.csv"
STATE = "data/StandardAlerts_Season.json"
REFRESH_WEEKS = 2  # Sleeper stat corrections land within days; older weeks come from the cache
COLS = ["Year", "LeagueID", "LeagueName", "Week", "RosterID", "PointsOfficial", "PointsStandard", "Delta"]
FLAG_COLS = ["Year", "LeagueName", "Week", "RosterID", "Team", "Opponent", "Type", "Official", "Standard", "Rules", "Note"]

TIERS = {
    "pts_allow": [(0, 0, "pts_allow_0"), (1, 6, "pts_allow_1_6"), (7, 13, "pts_allow_7_13"), (14, 20, "pts_allow_14_20"),
                  (21, 27, "pts_allow_21_27"), (28, 34, "pts_allow_28_34"), (35, float("inf"), "pts_allow_35p")],
    "yds_allow": [(0, 99, "yds_allow_0_100"), (100, 199, "yds_allow_100_199"), (200, 299, "yds_allow_200_299"),
                  (300, 349, "yds_allow_300_349"), (350, 399, "yds_allow_350_399"), (400, 449, "yds_allow_400_449"),
                  (450, 499, "yds_allow_450_499"), (500, 549, "yds_allow_500_549"), (550, float("inf"), "yds_allow_550p")],
}


def normalized_stats(raw):
    """Same as scoreboard-core.js normalizedStats: derive DEF tier flags when only totals are given."""
    s = dict(raw or {})
    for key, bands in TIERS.items():
        if s.get(key) is None or any(k.startswith(key + "_") for k in s):
            continue
        v = float(s[key])
        for lo, hi, name in bands:
            if lo <= v <= hi:
                s[name] = 1
                break
    return s


def deltas(scoring):
    """{league_id: {stat: standard - league}} for leagues that differ."""
    std = lcfg.standard_settings(scoring)
    out = {}
    for lid, s in scoring.items():
        n = lcfg.normalized(s)
        d = {k: round(std.get(k, 0) - n.get(k, 0), 6) for k in set(std) | set(n)}
        d = {k: v for k, v in d.items() if abs(v) > 1e-9}
        if d:
            out[str(lid)] = d
    return out


def correction(stats, delta):
    s = normalized_stats(stats)
    return sum(v * float(s.get(k, 0) or 0) for k, v in delta.items())


def get(url):
    import requests
    r = requests.get(url, timeout=60, headers={"User-Agent": "NCAA180-Sleeper/1.0"})
    r.raise_for_status()
    return r.json()


def stats_map(feed):
    if isinstance(feed, list):
        return {str(p["player_id"]): p.get("stats") or {} for p in feed if p.get("player_id")}
    if isinstance(feed, dict):
        return {str(k): (v.get("stats") if isinstance(v, dict) and "stats" in v else v) or {} for k, v in feed.items()}
    raise ValueError("Unrecognized statistics response")


def league_scoring(year, league_ids, offline):
    saved = Path(f"data/projections/{year}/scoring.json")
    scoring = json.loads(saved.read_text()) if saved.exists() else {}
    if not offline:
        for lid in league_ids:
            try:
                scoring[lid] = get(f"{lcfg.sleeper()}/league/{lid}")["scoring_settings"]
            except Exception as e:  # saved copy (weekly snapshot) is the fallback
                print(f"::warning::scoring settings for {lid} not fetched ({e}); using saved copy")
    missing = set(league_ids) - set(scoring)
    if missing:
        raise SystemExit(f"No scoring settings for leagues {sorted(missing)}")
    return {lid: scoring[lid] for lid in league_ids}


def week_stats(year, week, players, keys, refresh, offline):
    """Restated stats for the given players; cached per week (slim)."""
    path = Path(f"data/standard/{year}/stats_wk{week:02d}.json")
    cached = json.loads(path.read_text()) if path.exists() else None
    if offline or (cached is not None and not refresh and players <= set(cached)):
        if cached is None:
            raise SystemExit(f"No cached stat lines for {year} week {week} (offline)")
        return cached
    feed = stats_map(get(f"{lcfg.sleeper()}/stats/nfl/regular/{year}/{week}"))
    if len(feed) < 100:
        raise SystemExit(f"Stat feed for week {week} looks incomplete ({len(feed)} players); nothing written")
    slim = {}
    for pid in sorted(players):
        s = normalized_stats(feed.get(pid, {}))
        keep = {k: v for k, v in s.items() if k in keys and v}
        slim[pid] = keep
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(slim, sort_keys=True, indent=0) + "\n")
    return slim


def build(year, offline=False):
    m = pd.read_csv("data/Matchups_Season.csv", dtype=str)
    m = m[(m["Year"] == str(year)) & m["PointsFor"].notna()].copy()
    if m.empty:
        raise SystemExit(f"No {year} matchups")
    m["WeekN"] = m["Week"].astype(int)
    from week_status import completed_weeks
    done = set(completed_weeks(int(year)))
    m = m[m["WeekN"].isin(done)]
    if m.empty:
        raise SystemExit(f"No completed {year} weeks yet")
    leagues = sorted(m["LeagueID"].unique())
    delta = deltas(league_scoring(year, leagues, offline))
    keys = set().union(*delta.values()) if delta else set()

    sc = pd.read_csv("data/Scores_Season.csv", dtype=str)
    sc = sc[(sc["LeagueYear"] == str(year)) & (sc["is_starter"].str.lower() == "true") & sc["league_id"].isin(delta)]
    sc["roster_id"] = sc["roster_id"].str.replace(".0", "", regex=False)
    weeks = sorted(m["WeekN"].unique())
    latest = max(weeks)
    corr, detail = {}, {}
    for w in weeks:
        rows = sc[sc["weekNum"].astype(int) == w]
        if rows.empty:
            continue
        stats = week_stats(year, w, set(rows["player_id"]), keys, refresh=w > latest - REFRESH_WEEKS, offline=offline)
        for r in rows.itertuples():
            d = delta[r.league_id]
            s = stats.get(r.player_id, {})
            c = correction(s, d)
            if abs(c) > 1e-9:
                k = (r.league_id, r.roster_id, w)
                corr[k] = corr.get(k, 0) + c
                detail.setdefault(k, []).extend(kk for kk in d if s.get(kk))

    out = []
    for r in m.itertuples():
        k = (r.LeagueID, r.RosterID, r.WeekN)
        off = round(float(r.PointsFor), 2)
        dl = round(corr.get(k, 0), 2)
        out.append((int(year), r.LeagueID, r.LeagueName.strip(), r.WeekN, r.RosterID, off, round(off + dl, 2), dl))
    scores = pd.DataFrame(out, columns=COLS)
    scores = scores.assign(_r=scores["RosterID"].astype(int)).sort_values(["LeagueName", "Week", "_r"]).drop(columns="_r")
    return m, scores, detail


def flips(m, scores, detail):
    import team_names as tn
    std = {(r.LeagueID, r.RosterID, r.Week): (r.PointsOfficial, r.PointsStandard) for r in scores.itertuples()}
    res = lambda a, b: "W" if a > b else ("L" if a < b else "T")
    labels = {}
    try:
        import scoring_check
        labels = scoring_check.LABELS
    except Exception:
        pass
    flags = []
    for r in m[m["OpponentRosterID"].notna()].itertuples():
        a = std.get((r.LeagueID, r.RosterID, r.WeekN))
        b = std.get((r.LeagueID, str(r.OpponentRosterID).replace(".0", ""), r.WeekN))
        if not a or not b or res(a[0], b[0]) == res(a[1], b[1]):
            continue
        name = lambda rid: tn.season_name(int(r.Year), r.LeagueName, rid) or f"{r.LeagueName.strip()} r{rid}"
        opp = str(r.OpponentRosterID).replace(".0", "")
        rules = sorted(set(detail.get((r.LeagueID, r.RosterID, r.WeekN), []) + detail.get((r.LeagueID, opp, r.WeekN), [])))
        flags.append(dict(Year=r.Year, LeagueName=r.LeagueName.strip(), Week=r.WeekN, RosterID=r.RosterID, Team=name(r.RosterID),
                          Opponent=name(opp), Type="Game",
                          Official=f"{res(a[0], b[0])} {a[0]:.2f}-{b[0]:.2f}", Standard=f"{res(a[1], b[1])} {a[1]:.2f}-{b[1]:.2f}",
                          Rules="; ".join(labels.get(k, k) for k in rules),
                          Note=f"Decided on standard scoring: {res(a[1], b[1])} {a[1]:.2f}-{b[1]:.2f} "
                               f"(Sleeper shows {a[0]:.2f}-{b[0]:.2f})."))
    return pd.DataFrame(flags, columns=FLAG_COLS)


def alert(flags, year):
    """Post NEW winner changes once (one row per game: the standard winner's side)."""
    games = flags[flags["Standard"].str.startswith("W")] if len(flags) else flags
    keys = [f"{r.LeagueName}|{r.Week}|{r.RosterID}" for r in games.itertuples()]
    try:
        seen = set(json.load(open(STATE)).get("alerted", []))
    except Exception:
        seen = set()
    new = [(k, r) for k, r in zip(keys, games.itertuples()) if k not in seen]
    if not new:
        print(f"Standard scoring: {len(keys)} winner change(s) this season, none new")
        return
    disp = lcfg.league_display()
    uid = lcfg.cfg()["contact"]["discord_user_id"]
    lines = [f"• **{disp.get(r.LeagueName, r.LeagueName)} wk {r.Week}**: {r.Team} vs {r.Opponent} — "
             f"Sleeper {r.Official.split(' ', 1)[1]} ({r.Opponent} wins) · Standard {r.Standard.split(' ', 1)[1]} ({r.Team} wins)"
             f"{' · rule: ' + r.Rules if r.Rules else ''}" for _, r in new]
    msg = (f"<@{uid}> 🚨 **STANDARD SCORING CHANGED A RESULT — {lcfg.brand()} {year}** 🚨\n" + "\n".join(lines)
           + "\nResult is decided on standard scoring (Sleeper's score differs).")[:1990]
    hook = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "").strip()
    enabled = os.environ.get("STANDARD_ALERT", "1") != "0"
    sent = False
    if enabled and re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        import requests
        r = requests.post(hook + "?wait=true", json={"content": msg, "allowed_mentions": {"parse": [], "users": [uid]}}, timeout=30)
        sent = r.status_code < 300
    print(f"::error::STANDARD SCORING CHANGED {len(new)} RESULT(S) ({'alert sent' if sent else 'ALERT NOT SENT'})\n{msg}")
    if sent:
        json.dump({"alerted": sorted(seen | {k for k, _ in new})}, open(STATE, "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="cached stat lines and saved scoring only")
    ap.add_argument("--year", type=int, help="default: current season")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    year = a.year or lcfg.season()
    if year < int(lcfg.cfg()["postseason"]["standard_scoring_from"]):
        raise SystemExit(f"{year} is history; use standard_scores.py")
    m, scores, detail = build(year, a.offline)
    scores.to_csv(OUT_SCORES, index=False)
    flags = flips(m, scores, detail)
    flags.to_csv(OUT_FLAGS, index=False)
    restated = scores[scores["Delta"] != 0]
    print(f"{year}: {len(scores)} team-weeks, {len(restated)} restated "
          f"({restated.groupby('LeagueName').size().to_dict()}); winner changes: {len(flags) // 2}")
    alert(flags, year)


if __name__ == "__main__":
    main()
