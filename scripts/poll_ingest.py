"""
poll_ingest.py -- read raw ballots (Google Form response sheet as CSV) and validate them
for one poll. Raw ballots are private: they are written to work/poll/ (gitignored), never
to data/, unless config ballots.commit_raw is true.

Sources (any combination; rows are pooled):
  $POLL_BALLOTS_CSV_URL   the response tab's "Publish to web" CSV link (repo secret)
  --file PATH             local CSV(s): a manual export, or a non-Google intake

Expected columns (names set in config intake.columns; matching ignores case):
  Timestamp, Voter, Week (results-through week; optional but strongly recommended),
  Poll (optional: Top25 / Seeding or the label), Email Address (optional),
  and one column per rank whose header matches rank_column_regex ("1", "#1", "Rank 1").

Each submission gets one Status:
  counted      the voter's latest valid on-time ballot
  superseded   valid and on time, but the voter submitted again later
  late         after the deadline (kept, not counted)
  invalid      duplicate team, unknown team, missing rank, or team outside the poll's pool
  own_team     ranks own team while ballots.allow_own_team is false
  unknown_voter  voter not in data/PollVoters_Current.csv

Outputs:
  work/poll/ballots.csv  counted ballots, long form (VoterID, Rank, LeagueID, RosterID, ...)
  work/poll/audit.csv    one row per submission with Status and Reason
  work/poll/participation.csv  VoterID x ThroughWeek of every identified submission this season

Usage: python scripts/poll_ingest.py [--year Y] [--week W] [--type Top25] [--file a.csv ...]
CWD must be repo root.
"""
import argparse
import io
import os
import re
import sys

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402


def target(args, cfg):
    """(year, through_week, poll_type) from args, else the most recent finished week."""
    year = args.year
    if year is None:
        lg = pd.read_csv(pc.LEAGUE_IDS, dtype=str)
        year = int(lg["Year"].astype(int).max())
    week = args.week
    if week is None:
        from week_status import completed_weeks
        done = completed_weeks(year)
        if not done:
            raise SystemExit(f"No completed weeks for {year}; nothing to poll.")
        week = max(done)
    ptype = args.type or pc.poll_type_for_week(cfg, week)
    if ptype is None:
        raise SystemExit(f"No poll is configured for results through week {week}.")
    return int(year), int(week), ptype


def read_sources(files, cfg):
    frames = []
    url = os.environ.get(cfg["intake"].get("source_env", ""), "").strip()
    if url:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        frames.append(pd.read_csv(io.StringIO(r.content.decode("utf-8-sig")), dtype=str))
        print(f"Read {len(frames[-1])} response row(s) from the sheet link")
    for f in files or []:
        frames.append(pd.read_csv(f, dtype=str, encoding="utf-8-sig"))
        print(f"Read {len(frames[-1])} response row(s) from {f}")
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True).fillna("")


def find_col(df, name):
    if not name:
        return None
    for c in df.columns:
        if c.strip().lower() == name.strip().lower():
            return c
    return None


def parse_week(v):
    m = re.search(r"\d+", str(v))
    return int(m.group(0)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    ap.add_argument("--week", type=int, help="results-through week")
    ap.add_argument("--type", help="poll type key from config (default: by week)")
    ap.add_argument("--file", nargs="*")
    args = ap.parse_args()

    cfg = pc.config()
    if not cfg.get("human_component", {}).get("enabled"):
        print("Panel ballots are off (human_component.enabled = false); nothing to ingest.")
        return
    year, week, ptype = target(args, cfg)
    pcfg = pc.poll_cfg(cfg, ptype)
    size, bcfg, icfg = int(pcfg["size"]), cfg["ballots"], cfg["intake"]
    due = pc.deadline(cfg, year, ptype, week)
    tz = due.tzinfo
    print(f"{ptype} poll, {year} through week {week}; deadline {due:%a %Y-%m-%d %H:%M %Z}")

    os.makedirs(pc.WORK, exist_ok=True)
    raw = read_sources(args.file, cfg)
    if raw is None:
        print("::warning::No ballot source (set POLL_BALLOTS_CSV_URL or pass --file); "
              "the poll will be computer-only.")
        pd.DataFrame().to_csv(os.path.join(pc.WORK, "ballots.csv"), index=False)
        pd.DataFrame().to_csv(os.path.join(pc.WORK, "audit.csv"), index=False)
        pd.DataFrame().to_csv(os.path.join(pc.WORK, "participation.csv"), index=False)
        return

    cols = icfg["columns"]
    c_ts, c_voter = find_col(raw, cols.get("timestamp")), find_col(raw, cols.get("voter"))
    c_week, c_poll, c_email = (find_col(raw, cols.get(k)) for k in ("week", "poll", "email"))
    if not c_ts or not c_voter:
        raise SystemExit(f"Ballot sheet needs '{cols.get('timestamp')}' and '{cols.get('voter')}' columns; "
                         f"found {list(raw.columns)}")
    rx = re.compile(icfg["rank_column_regex"], re.I)
    rank_cols = {int(rx.match(c).group(1)): c for c in raw.columns if rx.match(c)}
    if not c_week:
        print("::warning::No Week column: ballots are assigned to a poll by timestamp, so a late "
              "ballot can't be told from an early one for the next poll. Add a Week question to the form.")

    teams = pc.teams(year)
    by_key = {r.Key: r for r in teams.itertuples()}
    pool = pc.playoff_pool(year) if pcfg.get("pool") == "playoff_field" else None
    if pool is not None and len(pool) != size:
        print(f"::warning::Playoff field has {len(pool)} teams but the Seeding poll size is {size}")

    v = pc.voters()
    vmap = {}
    for r in v.itertuples():
        names = [r.VoterID, r.VoterName] + [a for a in str(r.Aliases).split("|") if a.strip()]
        for n in names:
            if str(n).strip():
                vmap[pc.norm(n)] = r
        if str(r.Email).strip():
            vmap["email:" + str(r.Email).strip().lower()] = r
    m = pc.matchups(year)
    prev_due = pc.deadline(cfg, year, ptype, week - 1) if week > 1 and pc.poll_type_for_week(cfg, week - 1) == ptype else None

    audit, ballots, seen = [], {}, []
    for idx, row in raw.iterrows():
        ts = pd.to_datetime(row[c_ts], format=icfg.get("timestamp_format"), errors="coerce")
        if pd.isna(ts):
            continue
        ts = ts.tz_localize(tz) if ts.tzinfo is None else ts.tz_convert(tz)
        voter = vmap.get(pc.norm(row[c_voter]))
        if voter is None and c_email and str(row[c_email]).strip():
            voter = vmap.get("email:" + str(row[c_email]).strip().lower())
        if voter is not None and c_week and parse_week(row[c_week]) is not None:
            seen.append({"VoterID": voter.VoterID, "ThroughWeek": parse_week(row[c_week])})
        if c_poll and str(row[c_poll]).strip():
            pv = pc.norm(row[c_poll])
            if pv not in (pc.norm(ptype), pc.norm(pcfg.get("label", ptype))):
                continue
        if c_week and str(row[c_week]).strip():
            if parse_week(row[c_week]) != week:
                continue
        elif not (ts <= due and (prev_due is None or ts > prev_due)):
            continue

        rec = {"Row": idx + 2, "Submitted": ts.isoformat(), "VoterInput": row[c_voter],
               "VoterID": "", "VoterName": "", "Status": "", "Reason": ""}
        if voter is None:
            rec.update(Status="unknown_voter", Reason=f"'{row[c_voter]}' not in {pc.VOTERS}")
            audit.append(rec)
            continue
        rec.update(VoterID=voter.VoterID, VoterName=voter.VoterName)

        problems, picks = [], []
        for k in range(1, size + 1):
            cell = str(row[rank_cols[k]]).strip() if k in rank_cols else ""
            if not cell:
                if bcfg.get("require_full", True):
                    problems.append(f"rank {k} empty")
                continue
            t = by_key.get(pc.norm(cell))
            if t is None:
                problems.append(f"rank {k}: unknown team '{cell}'")
                continue
            if pool is not None and (t.LeagueID, t.RosterID) not in pool:
                problems.append(f"rank {k}: {t.Team} not in the playoff field")
            picks.append((k, t))
        placed = {}
        for k, t in picks:
            if t.Team in placed:
                problems.append(f"{t.Team} at ranks {placed[t.Team]} and {k}")
            placed.setdefault(t.Team, k)
        own = pc.own_slot(m, voter.SleeperUserID)
        if own and not bcfg.get("allow_own_team", True) and any((t.LeagueID, t.RosterID) == own for _, t in picks):
            rec.update(Status="own_team", Reason="ranked own team")
        elif problems:
            rec.update(Status="invalid", Reason="; ".join(problems))
        elif ts > due:
            rec.update(Status="late", Reason=f"after {due:%a %H:%M %Z}")
        else:
            rec.update(Status="valid")
            ballots[id(rec)] = picks
        audit.append(rec)

    # Latest valid on-time ballot per voter counts; earlier ones are superseded.
    latest = {}
    for rec in audit:
        if rec["Status"] == "valid":
            if rec["VoterID"] not in latest or rec["Submitted"] >= latest[rec["VoterID"]]["Submitted"]:
                latest[rec["VoterID"]] = rec
    rows = []
    for rec in audit:
        if rec["Status"] != "valid":
            continue
        if latest[rec["VoterID"]] is rec:
            rec["Status"] = "counted"
            for k, t in ballots[id(rec)]:
                rows.append({"Year": year, "PollType": ptype, "ThroughWeek": week,
                             "VoterID": rec["VoterID"], "VoterName": rec["VoterName"],
                             "Submitted": rec["Submitted"], "Rank": k, "Team": t.Team,
                             "LeagueID": t.LeagueID, "RosterID": t.RosterID})
        else:
            rec["Status"], rec["Reason"] = "superseded", "voter submitted again later"

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(pc.WORK, "ballots.csv"), index=False)
    au = pd.DataFrame(audit)
    au.to_csv(os.path.join(pc.WORK, "audit.csv"), index=False)
    # Who submitted anything, any week this season (for the missed-ballot streak alert).
    pd.DataFrame(seen, columns=["VoterID", "ThroughWeek"]).drop_duplicates().to_csv(
        os.path.join(pc.WORK, "participation.csv"), index=False)
    if bcfg.get("commit_raw"):
        path = "data/PollBallots_Season.csv"
        old = pd.read_csv(path, dtype=str) if os.path.exists(path) else pd.DataFrame()
        if not old.empty:
            old = old[~((old["Year"] == str(year)) & (old["PollType"] == ptype) & (old["ThroughWeek"] == str(week)))]
        pd.concat([old, out.astype(str)], ignore_index=True).to_csv(path, index=False)
    counts = au["Status"].value_counts().to_dict() if len(au) else {}
    print(f"Submissions for this poll: {len(au)} {counts}; counted ballots: {out['VoterID'].nunique() if len(out) else 0}")


if __name__ == "__main__":
    main()
