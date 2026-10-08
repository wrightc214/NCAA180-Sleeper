"""
poll_aggregate.py -- build the poll: the computer bots (scripts/poll_bots.py) combined
BCS-style, plus panel ballots as a second component once human_component is enabled.

BCS math (config/poll.json):
  ComputerPct  per team, drop the best and worst bot rank and average the rest (BotAvgRank);
               ComputerPct = (N - BotAvgRank) / (N - 1) over the N teams in the pool
  HumanPct     panel ballot points / (ballots x size)          -- only when human_component on
  Score        mean of the components present
Order: Score, then trimmed average bot rank (BotAvgRank), then the Standings bot. Top `size`
= Ranked; any other team in a counted bot's top `size` = Others receiving votes (ORV).
FirstPlaceVotes = bots (and ballots) ranking the team #1.

Timing: bots-only publishes as soon as it runs (the Tuesday weekly run). With
human_component on it waits for the ballot deadline (pass --force to override).
Seeding (week 12) needs data/PlayoffField_Season.csv; without it the script skips (exit 0).
Final (week 17) needs the season's postseason results (poll_bots.postseason_season); skips without.

Writes (public):
  data/Poll_Season.csv         Top25 / Seeding rows + BotConsensus (all teams ranked, for history)
  data/PollBots_Season.csv     every bot's full ranking that week
  data/PollRanks_Current.csv   latest poll's ranked teams
  data/RankedMatchups_Current.csv  next week's regular-season games with a ranked team
Writes (private, work/poll/, gitignored): flags.md -- only when panel ballots exist.
Usage: python scripts/poll_aggregate.py [--year Y] [--week W] [--type T] [--force]
CWD must be repo root.
"""
import argparse
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
import poll_bots as pb  # noqa: E402
from poll_ingest import target  # noqa: E402


def already(year, ptype, week):
    if not os.path.exists(pc.POLL_SEASON):
        return False
    p = pd.read_csv(pc.POLL_SEASON, dtype=str)
    return ((p["Year"] == str(year)) & (p["PollType"] == ptype) & (p["ThroughWeek"] == str(week))).any()


def prev_ranks(year, week, consensus=False):
    """{(LeagueID, RosterID): rank} from the previous week's poll (official polls compare
    with the last official poll; the full consensus with the last full consensus)."""
    p = pc.read_polls()
    if p.empty:
        return {}
    p = p[(p["Year"] == str(year)) & (p["ThroughWeek"] == str(week - 1))]
    p = p[p["PollType"] == pc.CONSENSUS] if consensus else p[(p["PollType"] != pc.CONSENSUS) & (p["Status"] == "Ranked")]
    return {(r.LeagueID, r.RosterID): int(r.Rank) for r in p.itertuples()}


def all_keys(year):
    t = pc.teams(year)
    t = t.dropna(subset=["LeagueID"])
    return sorted(zip(t["LeagueID"], t["RosterID"]))


def human_component(cfg, ballots, size, pool_keys):
    """{key: (points, first_place)} and ballot count from counted panel ballots."""
    if ballots is None or len(ballots) == 0:
        return {}, {}, 0
    v = pc.voters()
    weights = {r.VoterID: float(cfg.get("role_weights", {}).get(str(r.Role).strip().lower() or "panel", 1))
               for r in v.itertuples()}
    pts_tbl = pc.points_table({"size": size, "points": "linear"})
    pts, fpv = {}, {}
    for r in ballots.itertuples():
        k, rank = (r.LeagueID, r.RosterID), int(r.Rank)
        if rank > size or (pool_keys is not None and k not in pool_keys):
            continue
        pts[k] = pts.get(k, 0) + weights.get(r.VoterID, 1.0) * pts_tbl[rank - 1]
        fpv[k] = fpv.get(k, 0) + (rank == 1)
    return pts, fpv, ballots["VoterID"].nunique()


def build(cfg, year, week, ptype, ballots, stamp, extra=None, pool="auto", games=None, size=None):
    """extra/pool/games default to the live season's inputs; the history backfill passes its own.
    size overrides the configured poll size (e.g. a 16-team Seeding field in 2019)."""
    pcfg = pc.poll_cfg(cfg, ptype)
    size = int(size or pcfg["size"])
    if pool == "auto":
        pool = pc.playoff_pool(year) if pcfg.get("pool") == "playoff_field" else None
    m = pc.matchups(year)
    keys = all_keys(year)
    last = int(cfg.get("last_regular_week", 11))
    final = ptype == "Final"
    if extra is None:
        extra = pb.current_extra(year, last if final else week)
    if final:
        if games is None:
            games = pb.postseason_season(year)
        rk, used = pb.final_ranks(cfg, m, extra, keys, games)
    else:
        pts_thru = last + 1 if (ptype == "Seeding" and cfg.get("seeding", {}).get("include_week12_points")) else None
        rk, used = pb.bot_ranks(cfg, m, week, extra, keys, points_through=pts_thru)
    if not used:
        raise SystemExit("No bot has data for this week.")

    cons = pb.consensus(cfg, rk, used, size, pool)
    hp, hf, nh = human_component(cfg, ballots, size, pool)
    cons["HumanPoints"] = [round(hp.get(k, 0), 2) if nh else "" for k in zip(cons["LeagueID"], cons["RosterID"])]
    cons["HumanPct"] = [round(hp.get(k, 0) / (nh * size), 4) if nh else "" for k in zip(cons["LeagueID"], cons["RosterID"])]
    zmode = "ZScore" in cons.columns
    base_score = cons["ZScore"] if zmode else cons["ComputerPct"]
    if final:
        bumps = pb.final_bumps(cfg, games)
        base_score = base_score + [bumps.get(k, 0.0) for k in zip(cons["LeagueID"], cons["RosterID"])]
    cons["Score"] = [round((c + h) / 2, 4) if nh else round(float(b), 4)
                     for c, h, b in zip(cons["ComputerPct"], cons["HumanPct"], base_score)]
    cons["FirstPlaceVotes"] = [int(b + hf.get(k, 0)) for b, k in zip(cons["BotFirst"], zip(cons["LeagueID"], cons["RosterID"]))]
    tie = cons["record"] if "record" in used else 0
    cons = cons.assign(_t=tie).sort_values(["Score", "BotAvgRank", "_t"], ascending=[False, True, True]).reset_index(drop=True)
    if final and pc.poll_cfg(cfg, ptype).get("final_four_rule", True):
        order = pb.final_four(list(zip(cons["LeagueID"], cons["RosterID"])), games)
        cons = cons.set_index(pd.Index(list(zip(cons["LeagueID"], cons["RosterID"])))).loc[order].reset_index(drop=True)
        cons["_t"] = range(len(cons))  # order is now final; no shared ranks
    key3 = list(zip(cons["Score"], cons["BotAvgRank"], cons["_t"]))
    ranks, prev = [], None
    for i, k in enumerate(key3):
        ranks.append(ranks[-1] if k == prev else i + 1)
        prev = k
    cons["Rank"] = ranks
    cons["Status"] = ["Ranked" if r <= size else ("ORV" if v > 0 else "") for r, v in zip(cons["Rank"], cons["TopVotes"])]

    st = pc.standings_through(cfg, m, min(week, last))
    poll = frame(year, week, ptype, cons[cons["Status"] != ""], st, prev_ranks(year, week), nh, stamp)

    # Full ranking of every team by the bots (history / prestige / record book)
    if final:  # the final poll already ranks everyone (bumps + final-four order)
        full = cons.drop(columns=["Status"]).copy()
    else:
        full = pb.consensus(cfg, rk, used, size)
        full["Score"] = full["ZScore"] if "ZScore" in full.columns else full["ComputerPct"]
    full["Rank"] = range(1, len(full) + 1)
    full["Status"] = "Consensus"
    full["FirstPlaceVotes"] = full["BotFirst"]
    full["HumanPoints"] = full["HumanPct"] = ""
    allr = frame(year, week, pc.CONSENSUS, full, st, prev_ranks(year, week, consensus=True), 0, stamp)

    names = {b["id"]: b["name"] for b in cfg["bots"]}
    tn = {(r.LeagueID, r.RosterID): r.Team for r in pc.teams(year).itertuples()}
    bots = pd.concat([pd.DataFrame({"Year": year, "ThroughWeek": week, "Bot": b, "BotName": names[b],
                                    "Rank": rk[b], "Team": [tn.get(k, "") for k in zip(rk["LeagueID"], rk["RosterID"])],
                                    "LeagueID": rk["LeagueID"], "RosterID": rk["RosterID"],
                                    "Value": rk[b + "_val"].astype(float).round(4),
                                    "ValueSource": [extra.get(b + "_src", {}).get(k, "actual")
                                                    for k in zip(rk["LeagueID"], rk["RosterID"])]}) for b in used],
                     ignore_index=True)
    return poll, allr, bots, used, nh


def frame(year, week, ptype, d, st, prev, nh, stamp):
    teams = pc.teams(year)
    slot = {(r.LeagueID, r.RosterID): r for r in teams.itertuples()}
    rec = {(r.LeagueID, r.RosterID): r for r in st.itertuples()}
    tied = d["Rank"].duplicated(keep=False).tolist()
    rows = []
    for r, t in zip(d.itertuples(), tied):
        k = (r.LeagueID, r.RosterID)
        tm, sr, pr = slot.get(k), rec.get(k), prev.get(k)
        rows.append({
            "Year": year, "PollType": ptype, "ThroughWeek": week, "AppliesToWeek": week + 1,
            "Rank": r.Rank, "Tied": t, "Status": r.Status,
            "Team": tm.Team if tm else "", "LeagueID": k[0], "LeagueName": tm.LeagueName if tm else "",
            "League": tm.League if tm else "", "RosterID": k[1],
            "Score": r.Score, "ComputerPct": r.ComputerPct, "HumanPct": r.HumanPct, "HumanPoints": r.HumanPoints,
            "FirstPlaceVotes": r.FirstPlaceVotes, "BotAvgRank": r.BotAvgRank, "BotHigh": r.BotHigh,
            "BotLow": r.BotLow, "BotsUsed": r.BotsUsed, "HumanBallots": nh,
            "PrevRank": pr if pr else "", "Move": (pr - r.Rank) if (pr and r.Status in ("Ranked", "Consensus")) else "",
            "Wins": int(sr.Wins) if sr else "", "Losses": int(sr.Losses) if sr else "",
            "Ties": int(sr.Ties) if sr else "", "PF": sr.PF if sr else "", "PublishedAt": stamp})
    return pd.DataFrame(rows, columns=pc.POLL_COLS)


def replace_rows(path, df, year, week, types=None, cols=None):
    old = pd.read_csv(path, dtype=str) if os.path.exists(path) else pd.DataFrame(columns=cols or df.columns)
    drop = (old["Year"] == str(year)) & (old["ThroughWeek"] == str(week))
    if types is not None:
        drop &= old["PollType"].isin(types)
    out = pd.concat([old[~drop], df.astype(str)], ignore_index=True)
    sort = [c for c in ("Year", "PollType", "Bot", "ThroughWeek", "Rank") if c in out.columns]
    out = out.sort_values(sort, key=lambda c: c.astype(int) if c.name in ("Year", "ThroughWeek", "Rank") else c)
    out.to_csv(path, index=False)


def ranked_games(cfg, year, week, poll_df):
    """Regular-season games in AppliesToWeek involving a ranked team (Sleeper pairings are
    fictional after the regular season, so nothing is written for postseason weeks)."""
    cols = ["Year", "Week", "LeagueID", "LeagueName", "RosterID", "Team", "Rank",
            "OpponentRosterID", "OppTeam", "OppRank", "RankedVsRanked"]
    wk = week + 1
    if wk > int(cfg.get("last_regular_week", 11)):
        return pd.DataFrame(columns=cols)
    m = pc.matchups(year)
    m = m[m["Week"] == wk]
    rk = {(r.LeagueID, r.RosterID): (int(r.Rank), r.Team) for r in poll_df[poll_df["Status"] == "Ranked"].itertuples()}
    teams = {(r.LeagueID, r.RosterID): r.Team for r in pc.teams(year).itertuples()}
    rows, done = [], set()
    for r in m.itertuples():
        a, b = (r.LeagueID, r.RosterID), (r.LeagueID, r.OpponentRosterID)
        if (a not in rk and b not in rk) or frozenset((a, b)) in done:
            continue
        done.add(frozenset((a, b)))
        if b in rk and (a not in rk or rk[b][0] < rk[a][0]):
            a, b = b, a  # higher-ranked side first
        rows.append({"Year": year, "Week": wk, "LeagueID": a[0], "LeagueName": r.LeagueName,
                     "RosterID": a[1], "Team": teams.get(a, ""), "Rank": rk[a][0],
                     "OpponentRosterID": b[1], "OppTeam": teams.get(b, ""),
                     "OppRank": rk[b][0] if b in rk else "", "RankedVsRanked": b in rk})
    return pd.DataFrame(rows, columns=cols).sort_values(["RankedVsRanked", "Rank"], ascending=[False, True])


def flags(cfg, year, week, ptype, ballots, poll_df, size, m, teams):
    """Private notes about panel ballots (only when ballots exist); markdown text."""
    out = [f"**NCAA 180 poll — private ballot notes** ({ptype}, {year} through week {week})"]
    v = pc.voters()
    counted = set(ballots["VoterID"])
    out.append(f"Panel ballots counted: {len(counted)} of {len(v)} active voters.")
    miss = [r.VoterName for r in v.itertuples() if r.VoterID not in counted]
    if miss:
        out.append("No ballot: " + ", ".join(sorted(miss)))
    part_f = os.path.join(pc.WORK, "participation.csv")
    k = int(cfg.get("voter_alerts", {}).get("consecutive_misses", 2))
    if os.path.exists(part_f) and os.path.getsize(part_f) > 2 and miss:
        part = pd.read_csv(part_f, dtype=str)
        first = int(pc.poll_cfg(cfg, ptype)["first_week"])
        streak = []
        for r in v.itertuples():
            wks = set(part.loc[part["VoterID"] == r.VoterID, "ThroughWeek"].astype(int))
            n = next((i for i, w in enumerate(range(week, first - 1, -1)) if w in wks), week - first + 1)
            if n >= k:
                streak.append(f"{r.VoterName} ({n} straight)")
        if streak:
            out.append(f"⚠️ Missed {k}+ polls in a row: " + ", ".join(streak))
    audit_f = os.path.join(pc.WORK, "audit.csv")
    if os.path.exists(audit_f) and os.path.getsize(audit_f) > 2:
        au = pd.read_csv(audit_f, dtype=str).fillna("")
        for r in au[au["Status"] != "counted"].itertuples():
            out.append(f"• {r.VoterName or r.VoterInput}: {r.Status}" + (f" — {r.Reason}" if r.Reason else ""))
    cons = {(r.LeagueID, r.RosterID): int(r.Rank) for r in poll_df.itertuples() if r.Status == "Ranked"}
    names = {(r.LeagueID, r.RosterID): r.Team for r in teams.itertuples()}
    thr = int(cfg["ballots"].get("outlier_spots", 8))
    out.append(f"\n**Per ballot** (consensus = this poll; unranked = {size + 1}; ⚠️ = {thr}+ spots off)")
    for vid, b in ballots.groupby("VoterID"):
        mine = {(r.LeagueID, r.RosterID): int(r.Rank) for r in b.itertuples()}
        diffs = {kk: cons.get(kk, size + 1) - mine.get(kk, size + 1) for kk in set(mine) | set(cons)}
        hi, lo = max(diffs, key=diffs.get), min(diffs, key=diffs.get)
        vr = v[v["VoterID"] == vid]
        own = pc.own_slot(m, vr["SleeperUserID"].iloc[0]) if len(vr) else None

        def fmt(kk):
            r = mine.get(kk)
            return f"{names.get(kk, kk)} {'#' + str(r) if r else 'unranked'} (poll {'#' + str(cons[kk]) if kk in cons else 'unranked'})"
        line = (f"• {b['VoterName'].iloc[0]}: highest {'⚠️ ' if diffs[hi] >= thr else ''}{fmt(hi)}; "
                f"lowest {'⚠️ ' if -diffs[lo] >= thr else ''}{fmt(lo)}")
        if own:
            line += f"; own team {fmt(own)}"
        out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--week", type=int)
    ap.add_argument("--type")
    ap.add_argument("--force", action="store_true", help="rebuild even if published / before the deadline")
    ap.add_argument("--now", help="ISO time to treat as now (testing)")
    args = ap.parse_args()

    cfg = pc.config()
    gh = os.environ.get("GITHUB_OUTPUT")
    os.makedirs(pc.WORK, exist_ok=True)

    def output(**kv):
        if gh:
            with open(gh, "a") as f:
                for k, v in kv.items():
                    f.write(f"{k}={v}\n")
        with open(os.path.join(pc.WORK, "published.env"), "w") as f:
            for k, v in kv.items():
                f.write(f"{k.upper()}={v}\n")

    try:
        year, week, ptype = target(args, cfg)
    except SystemExit as e:
        print(e)
        output(published="false")
        return
    pcfg = pc.poll_cfg(cfg, ptype)
    size = int(pcfg["size"])
    human_on = bool(cfg.get("human_component", {}).get("enabled"))
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)

    if human_on and not args.force:
        due = pc.deadline(cfg, year, ptype, week)
        if now < due:
            print(f"Panel ballots due {due:%a %Y-%m-%d %H:%M %Z}; poll waits until then.")
            output(published="false")
            return
    if already(year, ptype, week) and not args.force:
        print(f"{ptype} {year} week {week} already published; use --force to rebuild.")
        output(published="false")
        return
    if pcfg.get("pool") == "playoff_field" and not os.path.exists(pc.FIELD):
        print(f"::warning::{ptype} poll skipped: {pc.FIELD} missing (run playoff_field first, then the Poll workflow).")
        output(published="false")
        return

    if ptype == "Final":
        g = pb.postseason_season(year)
        if g.empty or not ((g["Event"] == "Playoff") & (g["PlayoffRound"] == g["PlayoffRound"].max())
                           & (g["PlayoffRound"] > 0)).any():
            print(f"::warning::Final poll skipped: no final postseason results in Postseason_Season.csv for {year} "
                  "(needs the playoff bracket + NIT scripts writing the per-team format; see poll_bots.postseason_season).")
            output(published="false")
            return

    ballots = None
    if human_on:
        bf = os.path.join(pc.WORK, "ballots.csv")
        if os.path.exists(bf) and os.path.getsize(bf) > 2:
            ballots = pd.read_csv(bf, dtype=str)
            ballots = ballots[(ballots["Year"] == str(year)) & (ballots["PollType"] == ptype)
                              & (ballots["ThroughWeek"] == str(week))]

    stamp = now.strftime("%Y-%m-%d %H:%M UTC")
    poll, allr, bots, used, nh = build(cfg, year, week, ptype, ballots, stamp)
    replace_rows(pc.POLL_SEASON, pd.concat([poll, allr], ignore_index=True), year, week, [ptype, pc.CONSENSUS], pc.POLL_COLS)
    replace_rows(pc.BOTS_SEASON, bots, year, week, cols=pc.BOT_COLS)
    poll[poll["Status"] == "Ranked"][["Year", "PollType", "ThroughWeek", "AppliesToWeek", "Rank", "Tied",
                                      "Team", "LeagueID", "LeagueName", "League", "RosterID"]].to_csv(pc.RANKS_CURRENT, index=False)
    ranked_games(cfg, year, week, poll).to_csv(pc.RANKED_GAMES, index=False)
    flag_f = os.path.join(pc.WORK, "flags.md")
    if nh:
        with open(flag_f, "w", encoding="utf-8") as f:
            f.write(flags(cfg, year, week, ptype, ballots, poll, size, pc.matchups(year), pc.teams(year)))
    elif os.path.exists(flag_f):
        os.remove(flag_f)

    top = poll.iloc[0]
    print(f"{ptype} {year} wk {week}: {len(used)} bots ({', '.join(used)}) + {nh} panel ballot(s); "
          f"#1 {top.Team} (score {top.Score}, {top.FirstPlaceVotes} first-place); ORV {int((poll['Status'] == 'ORV').sum())}")
    output(published="true", poll_type=ptype, week=week, human_ballots=nh, bots=len(used))


if __name__ == "__main__":
    main()
