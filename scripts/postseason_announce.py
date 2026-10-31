"""
postseason_announce.py -- turn finished postseason results into announcements (notify.py).

Reads only what the postseason scripts already write (read-only; their process is unchanged):
  data/Postseason_Season.csv   one row per team per game (CCG / Playoff / Bowl / NIT)
  data/PlayoffField_Season.csv the 32-team field

Announcements (each sent once; data/push/Announced_Season.csv is the ledger):
  - results: one per (Round, Week) once every game of that round/week is Final
      CCG -> ccg_results, Playoff -> playoff_results, Bowl -> bowl_results, NIT -> nit_results
  - playoff field: once the field is complete (field_size rows, none "Tied - Unresolved")
  - champions: national championship game final; NIT final (Stagg Bowl) final
Pairings (bowl/NIT draws) are not announced here yet: they wait for Chris's review.

Usage: python scripts/postseason_announce.py [--dry-run] [--season-file F] [--field-file F]
  --dry-run prints every announcement and a sample push instead of sending.
CWD = repo root.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402
import notify  # noqa: E402

SEASON_FILE = "data/Postseason_Season.csv"
FIELD_FILE = "data/PlayoffField_Season.csv"


def _read(path):
    if not os.path.exists(path) or os.path.getsize(path) < 10:
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _pts(v):
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return "?"


def _short(full, smap):
    return smap.get(str(full).strip(), str(full).strip())


def _game_item(g, smap, conf, nit_final=None):
    """One finished game (2 rows) or group (3+ rows) -> push item."""
    rnd = g["Round"].iloc[0]
    g = g.copy()
    g["_p"] = pd.to_numeric(g["Points"], errors="coerce")
    g = g.sort_values("_p", ascending=False)
    win = g[g["Outcome"] == "Win"]
    w = win.iloc[0] if len(win) else g.iloc[0]
    others = g[g.index != w.name]
    slots = [notify.slot_key(_short(r["LeagueName"], smap), r["RosterID"]) for _, r in g.iterrows()]
    leagues = sorted({_short(r["LeagueName"], smap) for _, r in g.iterrows()})

    def seed(r):
        return f"({r['Seed']}) " if str(r.get("Seed", "")).strip() else ""

    if len(g) == 2:
        l_ = others.iloc[0]
        score = f"{seed(w)}{w['Team']} {_pts(w['Points'])} – {_pts(l_['Points'])} {seed(l_)}{l_['Team']}"
    else:  # group: top score advances
        score = f"{w['Team']} {_pts(w['Points'])} advances ({len(g)}-team group)"
    if rnd == "CCG":
        label = _short(w["LeagueName"], smap)
    elif rnd == "Bowl":
        label = w["BowlName"] or "Bowl"
    elif rnd == "NIT":
        label = "Stagg Bowl (NIT final)" if nit_final and w["Stage"] == nit_final else f"NIT {w['BowlName'] or w['Stage']}".strip()
    else:
        label = w["Stage"] or "Playoff"
    tier_order = {"Playoff": 0, "Bowl": 1, "NIT": 2, "CCG": 3}
    return {"text": f"{label}: {score}", "tier": rnd, "slots": slots, "leagues": leagues,
            "order": min((int(r["Seed"]) for _, r in g.iterrows() if str(r["Seed"]).isdigit()), default=99),
            "_winner": w, "_tier_rank": tier_order.get(rnd, 9)}


EVENT = {"CCG": "ccg_results", "Playoff": "playoff_results", "Bowl": "bowl_results", "NIT": "nit_results"}


def result_announcements(season, year, smap, conf, league_cfg):
    """One results push per postseason week (Chris: one push, the device's own teams first, then
    playoff -> bowl -> NIT), sent once every game of that week is final. Title games go out
    separately as champion pushes."""
    out = []
    if season.empty:
        return out
    s = season[season["Year"].astype(str) == str(year)]
    playoff_last = league_cfg["postseason"]["playoff"]["rounds"][-1]
    nit_last = league_cfg["postseason"]["nit"]["bracket"]["rounds"][-1]
    s = s.assign(_w=pd.to_numeric(s["Week"], errors="coerce"))
    s = s[s["Round"].isin(list(EVENT))]
    for week, wk in s.groupby("_w", sort=True):
        week = int(week)
        if (wk["Status"] != "Final").any():
            continue  # a week goes out once all its games are final
        items, parts, champs = [], [], []
        for rnd in ["Playoff", "Bowl", "NIT", "CCG"]:
            part = wk[wk["Round"] == rnd]
            if part.empty:
                continue
            its = [_game_item(g, smap, conf, nit_last) for _, g in part.groupby("GameID", sort=False)]
            for it in its:
                it["event"] = EVENT[rnd]
            stage = part["Stage"].iloc[0] if rnd in ("Playoff", "NIT") else ""
            if (rnd == "Playoff" and stage == playoff_last) or (rnd == "NIT" and stage == nit_last):
                champs.append((rnd, its))
                continue
            items += its
            parts.append(_part_label(rnd, stage, its, part))
        if items:
            ccg_only = set(wk["Round"]) == {"CCG"}
            title = "Conference championships are final" if ccg_only else f"Week {week} postseason results"
            out.append({"id": f"{year}-w{week}-results", "event": "results", "title": title, "url": "scoreboard.html",
                        "summary": "; ".join(parts), "items": _clean(items)})
        for rnd, its in champs:
            # The title game is announced once, as the champion push; its round's result followers
            # get it too (no "results" + "champion" pair for the same game).
            w = its[0]["_winner"]
            title = f"🏆 National champion: {w['Team']}" if rnd == "Playoff" else f"Stagg Bowl champion: {w['Team']}"
            out.append({"id": f"{year}-{'champion' if rnd == 'Playoff' else 'stagg'}", "event": "champions",
                        "also_events": [EVENT[rnd]], "champion": True, "title": title, "url": "scoreboard.html",
                        "summary": "", "items": _clean(its)})
    return out


def _part_label(rnd, stage, its, part):
    n = len(its)
    if rnd == "CCG":
        return f"{n} conference championships final" if n != 1 else "Conference championship final"
    if rnd == "Bowl":
        return f"{n} bowl{'s' if n != 1 else ''} final"
    if rnd == "NIT":
        return f"NIT {stage} final"
    return f"Playoff {stage} final"


def _clean(items):
    return [{k: v for k, v in it.items() if not k.startswith("_")} for it in items]


def field_announcement(field, year, smap, league_cfg):
    if field.empty:
        return None
    f = field[field["Year"].astype(str) == str(year)]
    size = int(league_cfg["postseason"]["playoff"]["field_size"])
    if len(f) != size or (f["BidType"] == "Tied - Unresolved").any():
        return None
    items = []
    for i, (_, r) in enumerate(f.iterrows()):
        sh = _short(r["LeagueName"], smap)
        bid = "auto bid" if str(r["BidType"]).startswith("Auto") else "at-large"
        items.append({"text": f"{r['Team']} ({sh}) is in ({bid})", "tier": "Playoff", "order": i,
                      "slots": [notify.slot_key(sh, r["RosterID"])], "leagues": [sh]})
    auto = int(f["BidType"].astype(str).str.startswith("Auto").sum())
    summary = f"{size} teams: {auto} auto bids, {size - auto} at-large"
    return {"id": f"{year}-playoff-field", "event": "playoff_field", "title": "The playoff field is set",
            "url": "standings.html", "summary": summary, "items": items}


def build(year, season_file=SEASON_FILE, field_file=FIELD_FILE):
    conf = notify.cfg()
    smap = notify.league_short_map()
    lc = lcfg.cfg()
    anns = result_announcements(_read(season_file), year, smap, conf, lc)
    fa = field_announcement(_read(field_file), year, smap, lc)
    if fa:
        anns.append(fa)  # after CCG results: the field is set from them
    return anns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--season-file", default=SEASON_FILE)
    ap.add_argument("--field-file", default=FIELD_FILE)
    ap.add_argument("--year", default=None)
    a = ap.parse_args()
    year = a.year or lcfg.season()
    anns = build(year, a.season_file, a.field_file)
    if not anns:
        print("Nothing to announce.")
        return
    for ann in anns:
        if a.dry_run:
            sample = {"follows": [{"kind": "event", "key": notify._group() + "|" + ann["event"]}]}
            print(f"[dry-run] {ann['id']} ({ann['event']}): {notify.payload_for(sample, ann)}")
        else:
            notify.announce(ann, year)


if __name__ == "__main__":
    main()
