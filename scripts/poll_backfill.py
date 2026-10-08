"""
poll_backfill.py -- ONE-TIME: rebuild the bot poll for past seasons and this season's
finished weeks, so movement, weeks-ranked and the record book have history.

  Past years  -> data/Poll_Historic.csv (Top25 weeks 1-11, Seeding, Final, BotConsensus)
                 data/PollBots_Historic.csv (every bot's ranking)
  This year   -> the _Season files, for finished weeks not yet published

Past-season inputs for Headliner / Monday Morning QB / Bagman come from the history-backfill
files (POLL_BACKFILL_DIR, default data/backfill). Bagman has no FantasyCalc history:
it uses Sleeper's projected lineup for the next week instead. Missing inputs -> that bot
sits out (BotsUsed shows how many voted).
Seeding for past years ranks the actual field (Postseason_Historic.csv round 1; 16 teams in
2019, 32 after), matched to slots by that season's names (unmatched names are listed).
Seasons run in order: each one's Professor prior (poll_prior.py) needs the previous final.
Seasons and their source files come from config/history.json (2019-2020 live in data/backfill/).

Run once, verify, delete (run-once-then-delete convention).
Usage: python scripts/poll_backfill.py [--years 2019 2020 ...] [--force]
CWD must be repo root.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
import poll_bots as pb  # noqa: E402
from poll_aggregate import build, replace_rows  # noqa: E402
import poll_prior as pp  # noqa: E402


def field(year):
    """Slots in that season's playoff round 1 (groups 'A | B | C | D' split) and unmatched names."""
    p = pd.read_csv("data/Postseason_Historic.csv", dtype=str)
    r1 = p[(p["Season"] == str(year)) & (p["Event"] == "Playoff") & (p["Round"] == "1")]
    by = pb.name_lookup(year)
    names = [x.strip() for col in ("TeamA", "TeamB") for v in r1[col].dropna() for x in str(v).split("|") if x.strip()]
    keys = {pc.find(by, n) for n in names} - {None}
    miss = [n for n in names if pc.find(by, n) is None]
    return keys, miss


def season_files(y):
    """Build one past season into scratch copies of the Season files, then move it to Historic."""
    cfg = pc.config()
    last = int(cfg.get("last_regular_week", 11))
    tmp = {pc.POLL_SEASON: "work/poll/_hist_poll.csv", pc.BOTS_SEASON: "work/poll/_hist_bots.csv"}
    for f in tmp.values():
        if os.path.exists(f):
            os.remove(f)
    pp.save(pp.build(y, cfg), y, current=False)  # frozen prior first (needs last season's final)
    slots = pb.league_slots(y)
    used = []
    for w in range(1, last + 1):
        extra = pb.history_extra(y, w, slots)
        poll, allr, bots, used, _ = build(cfg, y, w, "Top25", None, "backfill", extra=extra, pool=None)
        replace_rows(tmp[pc.POLL_SEASON], pd.concat([poll, allr]), y, w, ["Top25", pc.CONSENSUS], pc.POLL_COLS)
        replace_rows(tmp[pc.BOTS_SEASON], bots, y, w, cols=pc.BOT_COLS)
        # prev_ranks reads Poll_Historic; keep it current while the season builds
        hist = pd.read_csv(pc.POLL_HISTORIC, dtype=str) if os.path.exists(pc.POLL_HISTORIC) else pd.DataFrame(columns=pc.POLL_COLS)
        hist = hist[~((hist["Year"] == str(y)) & (hist["ThroughWeek"] == str(w)))]
        pd.concat([hist, pd.concat([poll, allr]).astype(str)]).to_csv(pc.POLL_HISTORIC, index=False)
    keys, miss = field(y)
    if keys:  # field size is that season's (2019: 16, 2020+: 32)
        extra = pb.history_extra(y, last, slots)
        sp, _, _, _, _ = build(cfg, y, last + 1, "Seeding", None, "backfill", extra=extra, pool=keys, size=len(keys))
        replace_rows(tmp[pc.POLL_SEASON], sp, y, last + 1, ["Seeding"], pc.POLL_COLS)
    if miss:
        print(f"WARNING {y}: playoff field names not matched to a slot: {miss}")
    games, gmiss = pb.postseason_historic(y)
    if gmiss:
        print(f"WARNING {y}: postseason names not matched to a slot (games skipped): {sorted(gmiss)}")
    if (games["Event"] == "Playoff").any():
        fw = int(games["Week"].max())  # that season's last postseason week (2019-2020: 16)
        extra = pb.history_extra(y, last, slots)
        fp, fall, _, _, _ = build(cfg, y, fw, "Final", None, "backfill", extra=extra, pool=None, games=games)
        replace_rows(tmp[pc.POLL_SEASON], pd.concat([fp, fall]), y, fw, ["Final", pc.CONSENSUS], pc.POLL_COLS)
    for live, scratch in tmp.items():
        hist_path = pc.POLL_HISTORIC if live == pc.POLL_SEASON else pc.BOTS_HISTORIC
        new = pd.read_csv(scratch, dtype=str)
        old = pd.read_csv(hist_path, dtype=str) if os.path.exists(hist_path) else pd.DataFrame(columns=new.columns)
        old = old[old["Year"] != str(y)]
        pd.concat([old, new], ignore_index=True).to_csv(hist_path, index=False)
    p = pd.read_csv(pc.POLL_HISTORIC, dtype=str)
    f = p[(p["Year"] == str(y)) & (p["PollType"] == "Top25") & (p["ThroughWeek"] == str(last)) & (p["Rank"] == "1")]
    fz = p[(p["Year"] == str(y)) & (p["PollType"] == "Final") & (p["Rank"] == "1")]
    print(f"{y}: week-{last} #1 {f['Team'].iloc[0] if len(f) else '?'}; Final #1 {fz['Team'].iloc[0] if len(fz) else '-'}; "
          f"bots wk{last}: {len(used)}; field {len(keys)}")


def current_season(y, force):
    cfg = pc.config()
    last = int(cfg.get("last_regular_week", 11))
    pp.save(pp.build(y, cfg), y, current=True)
    from week_status import completed_weeks
    for w in [w for w in completed_weeks(y) if w <= last]:
        if not force and os.path.exists(pc.POLL_SEASON):
            s = pd.read_csv(pc.POLL_SEASON, dtype=str)
            if ((s["Year"] == str(y)) & (s["ThroughWeek"] == str(w)) & (s["PollType"] == "Top25")).any():
                continue
        poll, allr, bots, used, _ = build(cfg, y, w, "Top25", None, "backfill")
        replace_rows(pc.POLL_SEASON, pd.concat([poll, allr]), y, w, ["Top25", pc.CONSENSUS], pc.POLL_COLS)
        replace_rows(pc.BOTS_SEASON, bots, y, w, cols=pc.BOT_COLS)
        print(f"{y} wk {w}: {len(used)} bots -> season files")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int)
    ap.add_argument("--force", action="store_true", help="rebuild current-season weeks already published")
    args = ap.parse_args()
    seasons = pc.seasons()
    current = max(seasons)
    # in order: each season's Professor prior needs the season before's final poll
    for y in sorted(args.years or seasons):
        if y == current:
            current_season(y, args.force)
        else:
            season_files(y)


if __name__ == "__main__":
    main()
