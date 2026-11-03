"""Postseason export: one JSON per season for the Postseason page, the scoreboard's postseason
mode and the Discord bracket cards (Chris, 2026-10-28).

Writes data/postseason/<year>.json:
  season, weeks [{week, label, short, subtitle}], games [...], champions {...}
Each game: id, event (CCG/Playoff/Bowl/NIT), week, round (display name), round_raw (as stored),
bowl, tier (bowl week tier), sides [{team, league, league_name, league_id, roster_id, seed,
points, official, won}], format ("game" | "group"), winner.

Display rules live in config/league.json -> postseason.display (week labels, bowl tiers counted
back from each season's last bowl week, round renames, prefixes). History rows keep the names
used at the time; only the display changes.
Run: python scripts/postseason_export.py [--year 2025 ...]   (default: every season on file)
"""
import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league_config as lcfg  # noqa: E402
import team_names as tn  # noqa: E402

HIST = "data/Postseason_Historic.csv"
OUT_DIR = "data/postseason"
LEAGUE_ID_FILES = ("data/backfill/LeagueIDs_2019_2020.csv", "data/LeagueIDs_AllYears.csv")
EVENT_ORDER = {"CCG": 0, "Playoff": 1, "Bowl": 2, "NIT": 3}
PLURAL = {"Quarterfinal": "Quarterfinals", "Semifinal": "Semifinals"}  # week subtitles read as a slate


def disp():
    return lcfg.cfg()["postseason"]["display"]


def split(v):
    return [x.strip() for x in str(v).split("|")] if str(v).strip() else []


def num(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def round_name(event, year, raw):
    r = disp()["round_renames"].get(event, {})
    return r.get(str(year), {}).get(raw) or r.get("*", {}).get(raw) or raw


def stagg():
    """NIT Final display name (Chris, 2026-10-28: past finals relabeled too)."""
    return lcfg.cfg()["postseason"]["bowls"].get("nit_final_label", "")


def location(bowl):
    """League location for a bowl that's in the current lineup (or the Stagg Bowl); else None."""
    if not bowl:
        return None
    b = lcfg.cfg()["postseason"]["bowls"]
    if bowl == b.get("nit_final_label"):
        return b.get("nit_final_location")
    for tier in b["tiers"]:
        for x in tier["bowls"]:
            if x["name"] == bowl:
                return x.get("location")
    return None


def week_label(week):
    w = disp()["week_labels"]
    last = lcfg.last_regular_week()
    if week <= last:
        k, n = "regular", week
    elif week == last + 1:
        k, n = "ccg", 0
    else:
        k, n = "post", week - last - 1
    long_, short = w[k]
    return long_.format(n=n), short.format(n=n)


def bowl_tiers(bowl_weeks):
    """{week: tier}: the season's last bowl week gets the top tier, counting back."""
    tiers = disp()["bowl_tiers"]
    out = {}
    for i, w in enumerate(sorted(bowl_weeks, reverse=True)):
        out[w] = tiers[max(len(tiers) - 1 - i, 0)]
    return out


def league_ids():
    out = {}
    for f in LEAGUE_ID_FILES:
        if os.path.exists(f):
            for r in pd.read_csv(f, dtype=str).itertuples():
                out[(int(r.Year), r.LeagueName.strip())] = r.LeagueID
    return out


def sides(year, row, lids, short):
    teams = split(row.TeamA) + ([row.TeamB] if row.TeamB else [])
    seeds = split(row.SeedA) + ([row.SeedB] if row.TeamB else [])
    pts = split(row.ScoreA) + ([row.ScoreB] if row.TeamB else [])
    off = split(row.OfficialScoreA) + ([row.OfficialScoreB] if row.TeamB else [])
    out = []
    for i, t in enumerate(teams):
        sl = tn.slot(year, t)
        lname = sl[0].strip() if sl else ""
        p = num(pts[i]) if i < len(pts) else None
        o = num(off[i]) if i < len(off) and off[i] else None
        out.append({"team": t, "league": short.get(lname, lname), "league_name": lname,
                    "league_id": lids.get((year, lname), ""), "roster_id": str(sl[1]) if sl else "",
                    "seed": int(seeds[i]) if i < len(seeds) and str(seeds[i]).isdigit() else None,
                    "points": p, "official": o if o is not None and o != p else None,
                    "won": t == row.Winner})
    return out


def build(year, hist, lids, short):
    h = hist[hist["Season"] == str(year)].copy()
    h["W"] = h["Week"].astype(int)
    tiers = bowl_tiers(set(h.loc[h["Event"] == "Bowl", "W"]))
    games, counters = [], {}
    for r in h.sort_values(["W", "Event", "Round", "Bowl", "TeamA"], key=lambda c: c.map(EVENT_ORDER).fillna(c) if c.name == "Event" else c).itertuples():
        ev = r.Event
        key = (ev, r.W)
        counters[key] = counters.get(key, 0) + 1
        sd = sides(year, r, lids, short)
        rnd = "Bowl" if ev == "Bowl" else ("Conference Championship" if ev == "CCG" else round_name(ev, year, r.RoundName))
        games.append({"id": f"{year}-{ev}-W{r.W}-{counters[key]:02d}", "event": ev, "week": r.W,
                      "round": rnd, "round_raw": r.RoundName,
                      "bowl": r.Bowl if ev == "Bowl" else (stagg() if ev == "NIT" and rnd == "Final" else ""),
                      "location": location(r.Bowl if ev == "Bowl" else (stagg() if ev == "NIT" and rnd == "Final" else "")),
                      "conference": short.get(r.Bowl.strip(), r.Bowl) if ev == "CCG" else "",
                      "tier": tiers.get(r.W, "") if ev == "Bowl" else "",
                      "group": r.Bowl if ev in ("NIT", "Playoff") and len(sd) > 2 else "",
                      "format": "group" if len(sd) > 2 else "game",
                      "sides": sd, "winner": r.Winner})  # source notes stay internal (history CSV)
    weeks = []
    for w in sorted({g["week"] for g in games}):
        if w in disp()["week_labels"].get("hide_weeks", []):
            continue
        gw = [g for g in games if g["week"] == w]
        nit_rounds = {g["round"] for g in gw if g["event"] == "NIT"}
        parts = []
        for ev in ("CCG", "Playoff", "Bowl", "NIT"):
            rounds = list(dict.fromkeys(g["round"] for g in gw if g["event"] == ev))
            for rd in rounds:
                if ev == "CCG":
                    parts.append("Conference Championships")
                elif ev == "Bowl":
                    parts.append(tiers.get(w, "Bowls"))
                elif ev == "NIT":
                    parts.append(stagg() if rd == "Final" and stagg() else f"NIT {PLURAL.get(rd, rd)}")
                else:
                    parts.append(f"Playoff {rd}" if rd in nit_rounds else rd)
        label, short_label = week_label(w)
        weeks.append({"week": w, "label": label, "short": short_label, "subtitle": " · ".join(dict.fromkeys(parts))})
    return {"season": year, "weeks": weeks, "games": games, "champions": champions(games)}


def champions(games):
    out = {}
    for ev, rd, key in (("Playoff", "National Championship", "national"), ("NIT", "Final", "nit"),
                        ("Playoff", "Third Place Game", "third_place")):
        g = [x for x in games if x["event"] == ev and x["round"] == rd]
        if g:
            win = [s for s in g[-1]["sides"] if s["won"]]
            lose = [s for s in g[-1]["sides"] if not s["won"]]
            out[key] = {"champion": win[0]["team"] if win else "", "runner_up": lose[0]["team"] if lose else "",
                        "game": g[-1]["id"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, nargs="*")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    hist = pd.read_csv(HIST, dtype=str, keep_default_na=False)
    years = a.year or sorted(int(y) for y in hist["Season"].unique())
    lids, short = league_ids(), lcfg.league_display()
    os.makedirs(OUT_DIR, exist_ok=True)
    index = []
    for y in years:
        d = build(y, hist, lids, short)
        Path(f"{OUT_DIR}/{y}.json").write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n")
        index.append({"season": y, "champion": d["champions"].get("national", {}).get("champion", "")})
        missing = sum(1 for g in d["games"] for s in g["sides"] if not s["league_id"] or not s["roster_id"])
        print(f"{y}: {len(d['games'])} games, {len(d['weeks'])} weeks{f', {missing} sides unresolved' if missing else ''}")
    if not a.year:
        Path(f"{OUT_DIR}/index.json").write_text(json.dumps({"seasons": index}, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
