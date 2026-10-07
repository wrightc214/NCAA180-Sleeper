"""
poll_aggregate.py -- turn counted ballots (work/poll/ballots.csv from poll_ingest.py) plus
the computer ballot into the poll, and the files other pages read.

Scoring (config/poll.json): each ballot gives points by rank (linear = size..1), times the
voter's weight (role_weights by Role in PollVoters_Current.csv; computer_ballot.weight).
Order: tiebreak list (points, first-place votes, computer rank); exact ties left after
that share a rank. Top `size` = Ranked; any other team with points = Others receiving votes.

Writes (committed, public):
  data/Poll_Season.csv           the poll (PollType Top25/Seeding) and the full computer
                                 ranking (PollType Computer, all teams), replaced per
                                 (Year, PollType, ThroughWeek) on rerun
  data/PollRanks_Current.csv     the latest poll's ranked teams (for the report/scoreboard)
  data/RankedMatchups_Current.csv  AppliesToWeek games with a ranked team (regular season)
Writes (private, work/poll/, never committed):
  flags.md   participation, ballot audit, own-team rank, highest/lowest outlier per ballot

Usage: python scripts/poll_aggregate.py [--year Y] [--week W] [--type T] [--force]
  Without --force, a poll that's already in Poll_Season.csv is left alone (exit 0) so the
  scheduled job can wake more than once.
CWD must be repo root.
"""
import argparse
import datetime as dt
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from poll_ingest import target  # noqa: E402


def already(year, ptype, week):
    if not os.path.exists(pc.POLL_SEASON):
        return False
    p = pd.read_csv(pc.POLL_SEASON, dtype=str)
    return ((p["Year"] == str(year)) & (p["PollType"] == ptype) & (p["ThroughWeek"] == str(week))).any()


def prev_ranks(year, week, ptype):
    """{(LeagueID, RosterID): rank} from the previous week's poll of the same family
    (official polls compare with the last official poll; Computer with Computer)."""
    p = pc.read_polls()
    if p.empty:
        return {}
    p = p[(p["Year"] == str(year)) & (p["ThroughWeek"] == str(week - 1))]
    p = p[p["PollType"] == "Computer"] if ptype == "Computer" else p[p["PollType"] != "Computer"]
    p = p[p["Status"].isin(["Ranked", "Computer"])]
    return {(r.LeagueID, r.RosterID): int(r.Rank) for r in p.itertuples()}


def rank_rows(order, ties_key):
    """Competition ranks (1,2,2,4) where ties_key(i) equal means a shared rank."""
    ranks, prev = [], None
    for i, k in enumerate(order):
        key = ties_key(k)
        ranks.append(ranks[-1] if key == prev else i + 1)
        prev = key
    return ranks


def build(cfg, year, week, ptype, ballots, st, teams):
    pcfg = pc.poll_cfg(cfg, ptype)
    size, pts = int(pcfg["size"]), pc.points_table(pcfg)
    pool = pc.playoff_pool(year) if pcfg.get("pool") == "playoff_field" else None

    comp = pc.computer_order(st, pool)
    comp_rank = {k: i + 1 for i, k in enumerate(comp)}

    v = pc.voters()
    weights = {r.VoterID: float(cfg.get("role_weights", {}).get(str(r.Role).strip().lower() or "panel", 1))
               for r in v.itertuples()}
    long = []
    for r in ballots.itertuples():
        long.append((r.VoterID, int(r.Rank), (r.LeagueID, r.RosterID), weights.get(r.VoterID, 1.0)))
    cb = cfg.get("computer_ballot", {})
    if cb.get("enabled", True):
        for i, k in enumerate(comp[:size]):
            long.append((cb.get("voter_id", "computer"), i + 1, k, float(cb.get("weight", 1))))

    tot, fpv, listed = {}, {}, {}
    for voter, rank, key, w in long:
        if rank > size:
            continue
        tot[key] = tot.get(key, 0) + w * pts[rank - 1]
        fpv[key] = fpv.get(key, 0) + (1 if rank == 1 else 0)
        listed[key] = listed.get(key, 0) + 1
    n_ballots = len({x[0] for x in long})

    def sort_key(k):
        out = []
        for tb in cfg.get("tiebreak", ["points"]):
            if tb == "points":
                out.append(-round(tot.get(k, 0), 6))
            elif tb == "first_place_votes":
                out.append(-fpv.get(k, 0))
            elif tb == "computer_rank":
                out.append(comp_rank.get(k, 10 ** 6))
        return tuple(out)

    order = sorted(tot, key=lambda k: (sort_key(k), k))
    ranks = rank_rows(order, sort_key)
    return order, ranks, tot, fpv, listed, n_ballots, comp_rank


def frame(year, week, ptype, order, ranks, status, tot, fpv, listed, n_ballots, comp_rank, st, teams, prev, now):
    slot = {(r.LeagueID, r.RosterID): r for r in teams.itertuples()}
    rec = {(r.LeagueID, r.RosterID): r for r in st.itertuples()}
    tied = pd.Series(ranks).duplicated(keep=False).tolist()
    rows = []
    for k, rk, s, t in zip(order, ranks, status, tied):
        tm, sr = slot.get(k), rec.get(k)
        pr = prev.get(k)
        rows.append({
            "Year": year, "PollType": ptype, "ThroughWeek": week, "AppliesToWeek": week + 1,
            "Rank": rk, "Tied": t, "Status": s,
            "Team": tm.Team if tm else "", "LeagueID": k[0],
            "LeagueName": tm.LeagueName if tm else (sr.LeagueName if sr else ""),
            "League": tm.League if tm else "", "RosterID": k[1],
            "Points": round(tot.get(k, 0), 2) if tot else "", "FirstPlaceVotes": fpv.get(k, 0) if fpv else "",
            "BallotsListing": listed.get(k, 0) if listed else "", "Ballots": n_ballots,
            "ComputerRank": comp_rank.get(k, ""), "PrevRank": pr if pr else "",
            "Move": (pr - rk) if (pr and s in ("Ranked", "Computer")) else "",
            "Wins": int(sr.Wins) if sr else "", "Losses": int(sr.Losses) if sr else "",
            "Ties": int(sr.Ties) if sr else "", "PF": sr.PF if sr else "", "PublishedAt": now})
    return pd.DataFrame(rows, columns=pc.POLL_COLS)


def save_poll(df, year, week, types):
    old = pd.read_csv(pc.POLL_SEASON, dtype=str) if os.path.exists(pc.POLL_SEASON) else pd.DataFrame(columns=pc.POLL_COLS)
    keep = ~((old["Year"] == str(year)) & (old["ThroughWeek"] == str(week)) & (old["PollType"].isin(types)))
    out = pd.concat([old[keep], df.astype(str)], ignore_index=True)
    out = out.sort_values(["Year", "PollType", "ThroughWeek", "Rank"],
                          key=lambda c: c.astype(int) if c.name in ("Year", "ThroughWeek", "Rank") else c)
    out.to_csv(pc.POLL_SEASON, index=False)


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
    """Private notes for the data manager / LM; returned as markdown text."""
    out = [f"**NCAA 180 poll — private ballot notes** ({ptype}, {year} through week {week})"]
    v = pc.voters()
    counted = set(ballots["VoterID"]) if len(ballots) else set()
    out.append(f"Ballots counted: {len(counted)} of {len(v)} active panel voters (+ computer).")
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
            n = 0
            for w in range(week, first - 1, -1):
                if w in wks:
                    break
                n += 1
            if n >= k:
                streak.append(f"{r.VoterName} ({n} straight)")
        if streak:
            out.append(f"⚠️ Missed {k}+ polls in a row: " + ", ".join(streak))
    audit_f = os.path.join(pc.WORK, "audit.csv")
    if os.path.exists(audit_f) and os.path.getsize(audit_f) > 2:
        au = pd.read_csv(audit_f, dtype=str).fillna("")
        bad = au[~au["Status"].isin(["counted"])]
        for r in bad.itertuples():
            who = r.VoterName or r.VoterInput
            out.append(f"• {who}: {r.Status}" + (f" — {r.Reason}" if r.Reason else ""))
    if len(ballots) == 0:
        return "\n".join(out)

    cons = {(r.LeagueID, r.RosterID): int(r.Rank) for r in poll_df.itertuples() if r.Status == "Ranked"}
    thr = int(cfg["ballots"].get("outlier_spots", 8))
    out.append(f"\n**Per ballot** (consensus = this poll; unranked = {size + 1}; ⚠️ = {thr}+ spots off)")
    for vid, b in ballots.groupby("VoterID"):
        name = b["VoterName"].iloc[0]
        mine = {(r.LeagueID, r.RosterID): int(r.Rank) for r in b.itertuples()}
        names = {(r.LeagueID, r.RosterID): r.Team for r in teams.itertuples()}
        diffs = {kk: cons.get(kk, size + 1) - mine.get(kk, size + 1) for kk in set(mine) | set(cons)}
        hi = max(diffs, key=lambda kk: diffs[kk])
        lo = min(diffs, key=lambda kk: diffs[kk])
        vr = v[v["VoterID"] == vid]
        own = pc.own_slot(m, vr["SleeperUserID"].iloc[0]) if len(vr) else None

        def fmt(kk):
            r = mine.get(kk)
            return f"{names.get(kk, kk)} {'#' + str(r) if r else 'unranked'} (poll {'#' + str(cons[kk]) if kk in cons else 'unranked'})"
        line = (f"• {name}: highest {'⚠️ ' if diffs[hi] >= thr else ''}{fmt(hi)}; "
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
    ap.add_argument("--force", action="store_true", help="rebuild even if already published")
    ap.add_argument("--now", help="ISO time to treat as now (testing)")
    args = ap.parse_args()

    cfg = pc.config()
    year, week, ptype = target(args, cfg)
    pcfg = pc.poll_cfg(cfg, ptype)
    size = int(pcfg["size"])
    due = pc.deadline(cfg, year, ptype, week)
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    gh = os.environ.get("GITHUB_OUTPUT")

    def output(k, v):
        if gh:
            with open(gh, "a") as f:
                f.write(f"{k}={v}\n")

    if now < due and not args.force:
        print(f"Deadline {due:%a %Y-%m-%d %H:%M %Z} not reached; nothing to do.")
        output("published", "false")
        return
    if already(year, ptype, week) and not args.force:
        print(f"{ptype} {year} week {week} already published; use --force to rebuild.")
        output("published", "false")
        return

    bf = os.path.join(pc.WORK, "ballots.csv")
    ballots = pd.read_csv(bf, dtype=str) if os.path.exists(bf) and os.path.getsize(bf) > 2 else pd.DataFrame(
        columns=["VoterID", "VoterName", "Rank", "Team", "LeagueID", "RosterID"])
    if len(ballots):
        ballots = ballots[(ballots["Year"] == str(year)) & (ballots["PollType"] == ptype)
                          & (ballots["ThroughWeek"] == str(week))]

    m = pc.matchups(year)
    st = pc.standings_through(cfg, m, week)
    teams = pc.teams(year)
    stamp = now.strftime("%Y-%m-%d %H:%M UTC")

    order, ranks, tot, fpv, listed, n_ballots, comp_rank = build(cfg, year, week, ptype, ballots, st, teams)
    status = ["Ranked" if r <= size else "ORV" for r in ranks]
    poll = frame(year, week, ptype, order, ranks, status, tot, fpv, listed, n_ballots, comp_rank, st,
                 teams, prev_ranks(year, week, ptype), stamp)

    comp_all = pc.computer_order(st)
    comp = frame(year, week, "Computer", comp_all, list(range(1, len(comp_all) + 1)), ["Computer"] * len(comp_all),
                 {}, {}, {}, 1, {k: i + 1 for i, k in enumerate(comp_all)}, st, teams,
                 prev_ranks(year, week, "Computer"), stamp)
    save_poll(pd.concat([poll, comp], ignore_index=True), year, week, [ptype, "Computer"])

    poll[poll["Status"] == "Ranked"][["Year", "PollType", "ThroughWeek", "AppliesToWeek", "Rank", "Tied",
                                      "Team", "LeagueID", "LeagueName", "League", "RosterID"]].to_csv(pc.RANKS_CURRENT, index=False)
    ranked_games(cfg, year, week, poll).to_csv(pc.RANKED_GAMES, index=False)

    os.makedirs(pc.WORK, exist_ok=True)
    with open(os.path.join(pc.WORK, "flags.md"), "w", encoding="utf-8") as f:
        f.write(flags(cfg, year, week, ptype, ballots, poll, size, m, teams))

    human = ballots["VoterID"].nunique() if len(ballots) else 0
    top = poll.iloc[0]
    print(f"{ptype} {year} wk {week}: {human} panel ballot(s) + computer; #1 {top.Team} "
          f"({top.Points} pts, {top.FirstPlaceVotes} first-place); ORV {int((poll['Status'] == 'ORV').sum())}")
    output("published", "true")
    output("human_ballots", human)
    output("poll_type", ptype)
    output("week", week)


if __name__ == "__main__":
    main()
