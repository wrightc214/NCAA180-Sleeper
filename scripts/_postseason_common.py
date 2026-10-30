"""
Shared postseason engine (imported by conference_championships.py, playoff_field.py,
playoff_bracket.py, bowls.py, nit.py, postseason_replay.py). Not run directly. CWD = repo root.

Rules live in config/league.json -> "postseason" (no league/team counts are typed in code).

Key facts:
- Sleeper runs all 18 weeks as "regular season" so every team always has points. The real
  regular season is weeks 1..last_regular_week (11); Sleeper's opponents/outcomes after that
  are placeholders. Postseason games use each team's OWN points that week, paired by our rules.
- Results: from postseason.standard_scoring_from (2026) games are decided on standard-scoring
  points; earlier seasons keep Sleeper's official points (results stand as played).
- Output contract (Postseason_Season.csv, one row per team per game; poll_bots.py reads it):
  Year, Round (CCG/Playoff/Bowl/NIT), Week, LeagueID, RosterID, Points, Status,
  OpponentRosterID + OpponentLeague (name) + OpponentPoints ('|'-lists for group games),
  PlayoffRound on Playoff rows. Plus GameID / Stage / BowlName / Seed / Team columns.
"""
import json
import os
import zlib

import pandas as pd

import team_names as tn
import tiebreak  # noqa: E402 (shared tiebreak order)

CONFIG = "config/league.json"
LEAGUES = "data/LeagueIDs_AllYears.csv"
TEAMS = "data/Teams.csv"
STANDINGS_HIST = "data/Standings_Historic.csv"
STANDARD_FILES = ["data/ScoresStandard_Historic.csv", "data/ScoresStandard_Season.csv"]
REGIONS = "data/TeamRegions.csv"
SHORTNAMES = "data/LeagueShortNames.csv"
SEASON_FILE = "data/Postseason_Season.csv"
FIELD_FILE = "data/PlayoffField_Season.csv"
DRAFT_DIR = "data/postseason_drafts"

COLUMNS = ["Year", "Round", "Stage", "Week", "GameID", "BowlName", "PlayoffRound", "Seed",
           "LeagueID", "LeagueName", "RosterID", "Team", "OwnerName",
           "RegularSeasonWins", "RegularSeasonPoints",
           "OpponentRosterID", "OpponentLeague", "OpponentTeam", "OpponentPoints",
           "Points", "OfficialPoints", "Outcome", "Margin", "Status", "DrawSeed"]


def config():
    c = json.load(open(CONFIG))
    return c, c["postseason"]


def last_regular_week():
    c, _ = config()
    return int(c["schedule"]["last_regular_week"])


def ccg_week():
    c, _ = config()
    return int(c["schedule"]["ccg_week"])


def current_season():
    return int(pd.read_csv(LEAGUES, dtype=str)["Year"].astype(int).max())


def league_short():
    s = pd.read_csv(SHORTNAMES, dtype=str, encoding="utf-8-sig")
    return dict(zip(s["Short Name"], s["Full Name"].str.strip()))


def short_to_full(short):
    m = league_short()
    if short not in m:
        raise ValueError(f"Unknown league short name '{short}' (see {SHORTNAMES})")
    return m[short]


def mode(year):
    _, ps = config()
    return "standard" if int(year) >= int(ps.get("standard_scoring_from", 9999)) else "official"


def _matchups(year):
    year = int(year)
    path = "data/Matchups_Season.csv" if year == current_season() else "data/Matchups_Historic.csv"
    m = pd.read_csv(path, dtype=str)
    m = m[m["Year"] == str(year)].copy()
    m["LeagueName"] = m["LeagueName"].str.strip()
    m["Week"] = m["Week"].astype(int)
    m["PointsFor"] = pd.to_numeric(m["PointsFor"], errors="coerce")
    return m


def _standard(year):
    out = {}
    for f in STANDARD_FILES:
        if os.path.exists(f):
            s = pd.read_csv(f, dtype=str)
            s = s[s["Year"] == str(year)]
            for r in s.itertuples():
                out[(r.LeagueID, r.RosterID, int(r.Week))] = float(r.PointsStandard)
    return out


def completed_weeks(year):
    if int(year) < current_season():
        return set(range(1, 19))
    from week_status import completed_weeks as cw
    return set(cw(int(year)))


_cache = {}


def week_points(year, week):
    """{(LeagueID, RosterID): (points used for the result, Sleeper official points)} for one week.
    Standard points from 2026 on; if a standard score is missing the official one is used and
    the gap is reported (results must never silently mix systems)."""
    key = (int(year), int(week))
    if key in _cache:
        return _cache[key]
    m = _matchups(year)
    m = m[m["Week"] == int(week)]
    std = _standard(year) if mode(year) == "standard" else {}
    out, missing = {}, 0
    for r in m.itertuples():
        if pd.isna(r.PointsFor):
            continue
        off = round(float(r.PointsFor), 2)
        if mode(year) == "standard":
            v = std.get((r.LeagueID, r.RosterID, int(week)))
            if v is None:
                missing += 1
                v = off
        else:
            v = off
        out[(r.LeagueID, r.RosterID)] = (round(v, 2), off)
    if missing:
        print(f"WARNING: {missing} team(s) in week {week} have no standard-scoring points; "
              f"Sleeper official points used for them (build ScoresStandard for {year}).")
    _cache[key] = out
    return out


def divisions(year):
    """{(LeagueName, RosterID): division} for a season."""
    if int(year) == current_season():
        t = pd.read_csv(TEAMS, dtype=str, encoding="utf-8-sig")
        return {(r["League"].strip(), str(r["Roster ID"])): str(r["Division Name"]).strip().upper()
                for _, r in t.iterrows()}
    s = pd.read_csv(STANDINGS_HIST, dtype=str)
    s = s[s["Year"] == str(year)]
    return {(r.LeagueName.strip(), r.RosterID): str(r.DivisionName).strip().upper() for r in s.itertuples()}


def regular_games(year):
    """Regular-season game rows (weeks 1..last_regular_week, completed only) with each side's
    points (PF) and result (Res) decided under this season's scoring mode."""
    year = int(year)
    lr = last_regular_week()
    m = _matchups(year)
    reg = m[(m["Week"] <= lr) & m["Outcome"].isin(["Win", "Loss", "Tie"])].copy()
    if year == current_season():
        reg = reg[reg["Week"].isin(completed_weeks(year))]
    if mode(year) == "standard":
        pts = {}
        for w in sorted(reg["Week"].unique()):
            for k, (v, _) in week_points(year, w).items():
                pts[(k[0], k[1], w)] = v
        reg["PF"] = [pts.get((a, b, w), p) for a, b, w, p in zip(reg["LeagueID"], reg["RosterID"], reg["Week"], reg["PointsFor"])]
        opp = dict(zip(zip(reg["LeagueID"], reg["RosterID"], reg["Week"]), reg["PF"]))
        reg["PA"] = [opp.get((a, b, w)) for a, b, w in zip(reg["LeagueID"], reg["OpponentRosterID"], reg["Week"])]
        reg["Res"] = ["Win" if pa is not None and pf > pa else "Loss" if pa is not None and pf < pa else
                      ("Tie" if pa is not None else o) for pf, pa, o in zip(reg["PF"], reg["PA"], reg["Outcome"])]
    else:
        reg["PF"], reg["Res"] = reg["PointsFor"], reg["Outcome"]
    return reg


def standings(year):
    """One row per team: regular season (weeks 1..last_regular_week) Wins/Losses/PointsFor,
    decided under this season's scoring mode; plus division, team name, owner, state/region."""
    global _last_games
    year = int(year)
    reg = regular_games(year)
    _last_games = reg
    owner = reg.sort_values("Week").groupby(["LeagueID", "RosterID"])["OwnerName"].last()
    g = reg.groupby(["LeagueID", "LeagueName", "RosterID"]).agg(
        Wins=("Res", lambda s: int((s == "Win").sum())), Losses=("Res", lambda s: int((s == "Loss").sum())),
        Ties=("Res", lambda s: int((s == "Tie").sum())), PointsFor=("PF", "sum")).reset_index()
    g["PointsFor"] = g["PointsFor"].round(2)
    g["OwnerName"] = [owner.get((a, b), "") for a, b in zip(g["LeagueID"], g["RosterID"])]
    div = divisions(year)
    g["Division"] = [div.get((l, r)) for l, r in zip(g["LeagueName"], g["RosterID"])]
    g["Team"] = [tn.season_name(year, l, r) or f"{l} #{r}" for l, r in zip(g["LeagueName"], g["RosterID"])]
    reg_ = pd.read_csv(REGIONS, dtype=str, encoding="utf-8-sig").fillna("") if os.path.exists(REGIONS) else pd.DataFrame(columns=["Team", "State", "Region"])
    st = dict(zip(reg_["Team"], zip(reg_["State"], reg_["Region"])))
    g["State"] = [st.get(t, ("", ""))[0] for t in g["Team"]]
    g["Region"] = [st.get(t, ("", ""))[1] for t in g["Team"]]
    missing = g[g["Division"].isna()]
    if len(missing):
        print(f"WARNING: no division for {len(missing)} team(s): {', '.join(missing['Team'])}")
    return g


_last_games = None  # regular-season rows from the latest standings() call (for head-to-head)


def rank(df, games=None):
    """Best first, by config/league.json -> tiebreakers.order (shared everywhere; see tiebreak.py).
    Head-to-head uses `games`, else the regular season of the latest standings() call."""
    return tiebreak.order(df, games if games is not None else _last_games)[0]


def rank_ties(df, games=None):
    """(ranked df, teams still tied after every tiebreaker)."""
    return tiebreak.order(df, games if games is not None else _last_games)


def draw_seed(year, label):
    """Recorded random seed for a draw, so a reviewed draft can be reproduced exactly."""
    return zlib.crc32(f"{year}|{label}".encode())


# ---------- results for a set of games ----------

def game_rows(year, rnd, week, game_id, teams, stage="", bowl="", playoff_round="", seeds=None, draw=""):
    """Per-team rows for one game (2 teams) or group (3+ teams; top score advances).
    teams: list of dicts with LeagueID, LeagueName, RosterID, Team, OwnerName, Wins, PointsFor."""
    has_week = week is not None and str(week) != ""
    done = has_week and int(week) in completed_weeks(year)
    pts = week_points(year, week) if done else {}  # an unplayed week has no scores yet
    vals = [pts.get((t["LeagueID"], str(t["RosterID"]))) for t in teams]
    final = done and all(v is not None for v in vals)
    top = max(v[0] for v in vals) if final else None
    n_top = sum(1 for v in vals if final and v[0] == top)
    rows = []
    for i, t in enumerate(teams):
        others = [j for j in range(len(teams)) if j != i]
        v = vals[i]
        if final:
            outcome = "Tie" if (v[0] == top and n_top > 1) else ("Win" if v[0] == top else "Loss")
            second = max(vals[j][0] for j in others)
            margin = round(abs(v[0] - (second if v[0] == top else top)), 2)
        else:
            outcome, margin = "Pending", ""
        rows.append({
            "Year": year, "Round": rnd, "Stage": stage, "Week": week if has_week else "",
            "GameID": game_id, "BowlName": bowl, "PlayoffRound": playoff_round,
            "Seed": (seeds or {}).get((t["LeagueID"], str(t["RosterID"])), ""),
            "LeagueID": t["LeagueID"], "LeagueName": t["LeagueName"], "RosterID": str(t["RosterID"]),
            "Team": t["Team"], "OwnerName": t.get("OwnerName", ""),
            "RegularSeasonWins": t.get("Wins", ""), "RegularSeasonPoints": t.get("PointsFor", ""),
            "OpponentRosterID": "|".join(str(teams[j]["RosterID"]) for j in others),
            "OpponentLeague": "|".join(teams[j]["LeagueName"] for j in others),
            "OpponentTeam": "|".join(teams[j]["Team"] for j in others),
            "OpponentPoints": "|".join(str(vals[j][0]) for j in others) if final else "",
            "Points": v[0] if v else "", "OfficialPoints": v[1] if v else "",
            "Outcome": outcome, "Margin": margin, "Status": "Final" if final else "Pending", "DrawSeed": draw,
        })
    return rows


def game_winner(df, game_id):
    """The winning team row of a finished game; None if not final; 'TIE' if tied at the top."""
    g = df[df["GameID"] == game_id]
    if g.empty or (g["Status"] != "Final").any():
        return None
    w = g[g["Outcome"] == "Win"]
    return w.iloc[0] if len(w) == 1 else "TIE"


def as_team(row):
    """Team dict from a Postseason_Season row (for building the next round)."""
    return {"LeagueID": row["LeagueID"], "LeagueName": row["LeagueName"], "RosterID": str(row["RosterID"]),
            "Team": row["Team"], "OwnerName": row["OwnerName"],
            "Wins": row["RegularSeasonWins"], "PointsFor": row["RegularSeasonPoints"]}


# ---------- file I/O ----------

def read_season(path=None):
    path = path or SEASON_FILE
    if not os.path.exists(path) or os.path.getsize(path) < 10:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype=str, keep_default_na=False).astype(object)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df


def replace_rows(year, keep_fn, new_rows, path=None):
    """Drop this year's rows where keep_fn(row) is False, append new_rows, write."""
    path = path or SEASON_FILE
    df = read_season(path)
    if len(df):
        mine = df["Year"].astype(str) == str(year)
        drop = mine & ~df.apply(keep_fn, axis=1).astype(bool)
        df = df[~drop]
    out = pd.concat([df, pd.DataFrame(new_rows, columns=COLUMNS)], ignore_index=True)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out[COLUMNS].to_csv(path, index=False)
    return read_season(path)


def paths(args):
    """Season/field/draft paths, overridable for replays (--data-dir)."""
    d = getattr(args, "data_dir", None)
    if not d:
        return SEASON_FILE, FIELD_FILE, DRAFT_DIR
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "Postseason_Season.csv"), os.path.join(d, "PlayoffField_Season.csv"), os.path.join(d, "drafts")
