"""
poll_backfill.py -- ONE-TIME: rebuild the bot poll for past seasons and this season's
finished weeks, so movement, weeks-ranked and the record book have history.

  Past years  -> data/Poll_Historic.csv (Top25 weeks 1-11, Seeding, Final, BotConsensus)
                 data/PollBots_Historic.csv (every bot's ranking)
  This year   -> the _Season files, for finished weeks not yet published

Past-season inputs for The Ceiling / The Coach / The Market come from the history-backfill
files (POLL_BACKFILL_DIR, default data/backfill). The Market has no FantasyCalc history:
it uses Sleeper's projected lineup for the next week instead. Missing inputs -> that bot
sits out (BotsUsed shows how many voted).
Seeding for past years ranks the actual 32-team field (Postseason_Historic.csv round 1),
matched to slots by today's Teams.csv names (unmatched names are listed).

Run once, verify, delete (run-once-then-delete convention).
Usage: python scripts/poll_backfill.py [--years 2021 2022 ...]
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


def field(year):
    p = pd.read_csv("data/Postseason_Historic.csv", dtype=str)
    r1 = p[(p["Season"] == str(year)) & (p["Event"] == "Playoff") & (p["Round"] == "1")]
    by = pb.name_lookup(year)
    names = list(r1["TeamA"]) + list(r1["TeamB"])
    keys = {by.get(pc.norm(n)) for n in names} - {None}
    miss = [n for n in names if by.get(pc.norm(n)) is None]
    return keys, miss


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", type=int)
    args = ap.parse_args()
    cfg = pc.config()
    last = int(cfg.get("last_regular_week", 11))
    lg = pd.read_csv(pc.LEAGUE_IDS, dtype=str)
    current = int(lg["Year"].astype(int).max())
    years = args.years or sorted(int(y) for y in lg["Year"].unique())

    for y in years:
        if y == current:
            from week_status import completed_weeks
            done = [w for w in completed_weeks(y) if w <= last]
            for w in done:
                if os.path.exists(pc.POLL_SEASON):
                    s = pd.read_csv(pc.POLL_SEASON, dtype=str)
                    if ((s["Year"] == str(y)) & (s["ThroughWeek"] == str(w)) & (s["PollType"] == "Top25")).any():
                        continue
                poll, allr, bots, used, _ = build(cfg, y, w, "Top25", None, "backfill")
                replace_rows(pc.POLL_SEASON, pd.concat([poll, allr]), y, w, ["Top25", pc.CONSENSUS], pc.POLL_COLS)
                replace_rows(pc.BOTS_SEASON, bots, y, w, cols=pc.BOT_COLS)
                print(f"{y} wk {w}: {len(used)} bots -> season files")
            continue

        # Past season: build into the Season paths of a scratch copy, then append to Historic.
        tmp = {pc.POLL_SEASON: "work/poll/_hist_poll.csv", pc.BOTS_SEASON: "work/poll/_hist_bots.csv"}
        for f in tmp.values():
            if os.path.exists(f):
                os.remove(f)
        slots = pb.league_slots(y)
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
        if len(keys) == 32:
            extra = pb.history_extra(y, last, slots)
            sp, _, _, used, _ = build(cfg, y, 12, "Seeding", None, "backfill", extra=extra, pool=keys)
            replace_rows(tmp[pc.POLL_SEASON], sp, y, 12, ["Seeding"], pc.POLL_COLS)
        else:
            print(f"WARNING {y}: Seeding skipped, field matched {len(keys)}/32; unmatched: {miss}")
        games, gmiss = pb.postseason_historic(y)
        if gmiss:
            print(f"WARNING {y}: postseason names not matched to a slot (games skipped): {sorted(gmiss)}")
        if (games["Event"] == "Playoff").any():
            extra = pb.history_extra(y, last, slots)
            fp, fall, _, _, _ = build(cfg, y, 17, "Final", None, "backfill", extra=extra, pool=None, games=games)
            replace_rows(tmp[pc.POLL_SEASON], pd.concat([fp, fall]), y, 17, ["Final", pc.CONSENSUS], pc.POLL_COLS)
        for live, scratch in tmp.items():
            hist_path = pc.POLL_HISTORIC if live == pc.POLL_SEASON else pc.BOTS_HISTORIC
            new = pd.read_csv(scratch, dtype=str)
            old = pd.read_csv(hist_path, dtype=str) if os.path.exists(hist_path) else pd.DataFrame(columns=new.columns)
            old = old[old["Year"] != str(y)]
            pd.concat([old, new], ignore_index=True).to_csv(hist_path, index=False)
        p = pd.read_csv(pc.POLL_HISTORIC, dtype=str)
        f = p[(p["Year"] == str(y)) & (p["PollType"] == "Top25") & (p["ThroughWeek"] == str(last)) & (p["Rank"] == "1")]
        fz = p[(p["Year"] == str(y)) & (p["PollType"] == "Final") & (p["Rank"] == "1")]
        print(f"{y}: Final poll #1 {fz['Team'].iloc[0] if len(fz) else '-'}")
        print(f"{y}: weeks 1-{last} + Seeding; week-{last} #1 {f['Team'].iloc[0] if len(f) else '?'}; bots used wk{last}: {len(used)}")


if __name__ == "__main__":
    main()
