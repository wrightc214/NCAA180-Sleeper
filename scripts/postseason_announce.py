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
  - guillotine: each finished week's cut (folded into that week's results push when both go out
    in the same run) and the champion (data/Guillotine_Season.csv, scripts/guillotine.py)
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
GUILLOTINE_FILE = "data/Guillotine_Season.csv"


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


def guillotine_announcements(gdf, year, smap, lc):
    """The Guillotine (Chris, 2026-11-14): one announcement per finished week (who survived the cut,
    who was eliminated) and one for the champion. Per-team lines are "quiet": only phones following
    that team or league see them; Guillotine event followers get the summary line."""
    g = lc["postseason"].get("guillotine") or {}
    if gdf.empty or not g:
        return []
    d = gdf[gdf["Year"].astype(str) == str(year)]
    last = int(g["last_week"])
    name = g.get("name", "The Guillotine")
    out = []
    for week, wk in d.groupby(d["Week"].astype(int), sort=True):
        wk = wk.copy()
        wk["_s"] = pd.to_numeric(wk["Score"], errors="coerce")
        wk = wk.sort_values("_s", ascending=False)
        if week < last:
            n_adv = int((wk["Status"] == "Advanced").sum())
            line = _pts(wk["CutLine"].iloc[0])
            items = []
            for i, (_, r) in enumerate(wk.iterrows()):
                sh = _short(r["LeagueName"], smap)
                verb = "survives" if r["Status"] == "Advanced" else "eliminated"
                items.append({"text": f"{name}: {r['Team']} {verb} ({_pts(r['Score'])}; cut {line})", "tier": "Guillotine",
                              "order": i, "event": "guillotine", "quiet": True,
                              "slots": [notify.slot_key(sh, r["RosterID"])], "leagues": [sh]})
            rnd = f"Round {week - int(g['first_week']) + 1}"
            out.append({"id": f"{year}-w{week}-guillotine", "event": "guillotine", "fold_into": f"{year}-w{week}-results",
                        "title": f"{name}: {rnd} cut", "url": "special.html",  # rounds, not weeks (Chris, 2026-11-19)
                        "summary": f"{n_adv} of {len(wk)} survive · cut line {line}", "items": items,  # event followers see the summary
                        # league channel: just the cut (Chris, 2026-11-14)
                        "discord_extra": [f"🪓 {name}, {rnd}: {n_adv} of {len(wk)} survive · cut line {line}"]})
        else:
            champs = wk[wk["Status"] == "Champion"]
            if champs.empty:
                continue  # tied for first: waits for the tiebreak week
            names = " & ".join(champs["Team"])
            co = len(champs) > 1
            items = []
            for i, (_, r) in enumerate(champs.iterrows()):
                sh = _short(r["LeagueName"], smap)
                items.append({"text": f"{name} {'co-' if co else ''}champion: {r['Team']} ({_pts(r['Score'])})",
                              "tier": "Guillotine", "order": i, "event": "guillotine",
                              "slots": [notify.slot_key(sh, r["RosterID"])], "leagues": [sh]})
            # league channel: the full final -- every finalist, ranked (Chris, 2026-11-14)
            fin = [f"{int(r['Rank'])}. {r['Team']} ({_short(r['LeagueName'], smap)}) {_pts(r['Score'])}"
                   + (f" · tiebreak {_pts(r['TiebreakScore'])}" if str(r.get('TiebreakScore', '')) else "")
                   for _, r in wk.iterrows()]
            out.append({"id": f"{year}-guillotine-champion", "event": "guillotine",
                        "title": f"🪓 {name} {'co-champions' if co else 'champion'}: {names}", "url": "special.html",
                        "summary": "", "items": items,
                        "discord_extra": [f"Final round, {len(wk)} teams:"] + fin})
    return out


def fold(anns, gann, sent=notify.already_sent):
    """One push per device per run (Chris): a week's Guillotine cut rides along with that week's
    postseason results push when both are going out now. Otherwise it goes on its own."""
    by_id = {a["id"]: a for a in anns}
    out = list(anns)
    for g in gann:
        host = by_id.get(g.get("fold_into"))
        if host and not sent(host["id"]) and not sent(g["id"]):
            host["items"] = host["items"] + g["items"]
            host["summary"] = "; ".join(x for x in [host.get("summary"), f"{g['title'].split(':')[0]}: {g['summary']}"] if x)
            host["also_ids"] = host.get("also_ids", []) + [g["id"]]
            host["discord_extra"] = host.get("discord_extra", []) + g.get("discord_extra", [])
        else:
            out.append(g)
    return out


def build(year, season_file=SEASON_FILE, field_file=FIELD_FILE, guillotine_file=GUILLOTINE_FILE, sent=None):
    conf = notify.cfg()
    smap = notify.league_short_map()
    lc = lcfg.cfg()
    anns = result_announcements(_read(season_file), year, smap, conf, lc)
    fa = field_announcement(_read(field_file), year, smap, lc)
    if fa:
        anns.append(fa)  # after CCG results: the field is set from them
    return fold(anns, guillotine_announcements(_read(guillotine_file), year, smap, lc), sent or notify.already_sent)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--season-file", default=SEASON_FILE)
    ap.add_argument("--field-file", default=FIELD_FILE)
    ap.add_argument("--guillotine-file", default=GUILLOTINE_FILE)
    ap.add_argument("--year", default=None)
    a = ap.parse_args()
    year = a.year or lcfg.season()
    anns = build(year, a.season_file, a.field_file, a.guillotine_file)
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
