"""
poll_common.py -- shared pieces of the poll engine (imported, not run).

Settings: config/poll.json. Nothing league-specific is hardcoded here.

Team identity is the roster slot: (Year, LeagueID, RosterID). Team is the slot's display
name for that season (TeamNames_Historic.csv for past seasons, Teams.csv for the current one).

History sources come from config/history.json (league_ids, matchups, standard_scores), so
seasons kept outside the main files (data/backfill/ for 2019-2020) are read the same way.
Points: PointsFor = standard scoring where restated (ScoresStandard_Historic.csv), the
official number kept as PointsOfficial. Outcomes (W/L) are always official.

Week terms used everywhere:
  ThroughWeek    last week of results the voters saw
  AppliesToWeek  the week whose games carry these rankings (= ThroughWeek + 1)

Deadline: the poll's configured weekday/time, first occurrence after the Tuesday that
ends ThroughWeek. Week 1 kickoff comes from Sleeper's season_start_date when available,
else the Thursday after Labor Day.
"""
import datetime as dt
import json
import os
import re
import sys
import unicodedata

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CONFIG = "config/poll.json"
TEAMS = "data/Teams.csv"
SHORT = "data/LeagueShortNames.csv"
LEAGUE_IDS = "data/LeagueIDs_AllYears.csv"
MATCHUPS_SEASON = "data/Matchups_Season.csv"
MATCHUPS_HISTORIC = "data/Matchups_Historic.csv"
VOTERS = "data/PollVoters_Current.csv"
FIELD = "data/PlayoffField_Season.csv"
POLL_SEASON = "data/Poll_Season.csv"
POLL_HISTORIC = "data/Poll_Historic.csv"
RANKS_CURRENT = "data/PollRanks_Current.csv"
RANKED_GAMES = "data/RankedMatchups_Current.csv"
WORK = "work/poll"  # job-local scratch (gitignored): raw ballots, private flags

POLL_COLS = ["Year", "PollType", "ThroughWeek", "AppliesToWeek", "Rank", "Tied", "Status",
             "Team", "LeagueID", "LeagueName", "League", "RosterID",
             "Score", "ComputerPct", "HumanPct", "HumanPoints", "FirstPlaceVotes",
             "BotAvgRank", "BotHigh", "BotLow", "BotsUsed", "HumanBallots",
             "PrevRank", "Move", "Wins", "Losses", "Ties", "PF", "PublishedAt"]
BOT_COLS = ["Year", "ThroughWeek", "Bot", "BotName", "Rank", "Team", "LeagueID", "RosterID", "Value", "ValueSource"]
# ValueSource: actual | interpolated (between the nearest weeks with data) | carried (nearest
# week with data, before or after) -- see poll_bots.bridge
BOTS_SEASON = "data/PollBots_Season.csv"
BOTS_HISTORIC = "data/PollBots_Historic.csv"
CONSENSUS = "BotConsensus"  # PollType of the full bot ranking of every team, kept for history
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ---------------------------------------------------------------- config
def config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def poll_cfg(cfg, poll_type):
    if poll_type not in cfg["polls"]:
        raise SystemExit(f"Unknown poll type {poll_type!r}; config has {list(cfg['polls'])}")
    return cfg["polls"][poll_type]


def points_table(pc):
    n = int(pc["size"])
    pts = pc.get("points", "linear")
    if pts == "linear":
        return [n - i for i in range(n)]
    pts = [float(x) for x in pts]
    if len(pts) != n:
        raise SystemExit(f"points list has {len(pts)} entries, poll size is {n}")
    return pts


def poll_type_for_week(cfg, through_week):
    for name, pc in cfg["polls"].items():
        if int(pc["first_week"]) <= through_week <= int(pc["last_week"]):
            return name
    return None


# ---------------------------------------------------------------- dates
def _tz(cfg):
    from zoneinfo import ZoneInfo
    return ZoneInfo(cfg.get("timezone", "UTC"))


def week1_kickoff(year):
    """Date of week 1's Thursday: Sleeper's season_start_date if it matches `year`, else
    the Thursday after Labor Day (first Monday of September)."""
    try:
        from week_status import _get_state
        st = _get_state() or {}
        d = st.get("season_start_date")
        if d and str(st.get("season")) == str(year):
            d = dt.date.fromisoformat(d)
            return d + dt.timedelta(days=(3 - d.weekday()) % 7)
    except Exception:
        pass
    sep1 = dt.date(int(year), 9, 1)
    labor = sep1 + dt.timedelta(days=(0 - sep1.weekday()) % 7)
    return labor + dt.timedelta(days=3)


def deadline(cfg, year, poll_type, through_week):
    """Timezone-aware deadline for the poll covering results through `through_week`."""
    dl = poll_cfg(cfg, poll_type)["deadline"]
    wd = WEEKDAYS.index(dl["weekday"].strip().lower())
    hh, mm = (int(x) for x in dl["time"].split(":"))
    week_over = week1_kickoff(year) + dt.timedelta(days=7 * (through_week - 1) + 5)  # Tuesday
    d = week_over + dt.timedelta(days=(wd - week_over.weekday()) % 7)
    return dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=_tz(cfg))


# ---------------------------------------------------------------- teams
def norm(s):
    """Loose key for matching typed/dropdown team and voter names."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"\(.*?\)", " ", s)  # "Auburn (SEC)" -> "auburn"
    return re.sub(r"[^a-z0-9]+", "", s)


def full_key(s):
    """Like norm() but keeps a parenthesized qualifier: 'Miami (OH)' -> 'miamioh'."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", s)


def find(by, name):
    """Look a typed/recorded name up in a {key: value} map built with both key styles."""
    return by.get(full_key(name), by.get(norm(name)))


def league_short():
    t = pd.read_csv(SHORT, dtype=str, encoding="utf-8-sig")
    return {r["Full Name"].strip().upper(): r["Short Name"].strip() for _, r in t.iterrows()}


def history_cfg():
    p = "config/history.json"
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def leagues_all():
    """Every season's leagues: Year, LeagueID, LeagueName, RosterPositions (history files first)."""
    paths = history_cfg().get("league_ids", [LEAGUE_IDS])
    cols = ["Year", "LeagueID", "LeagueName", "RosterPositions"]
    frames = [pd.read_csv(p, dtype=str) for p in paths if os.path.exists(p)]
    lg = pd.concat([f.reindex(columns=cols) for f in frames], ignore_index=True)
    lg["LeagueName"] = lg["LeagueName"].str.strip()
    return lg.drop_duplicates(["Year", "LeagueID"], keep="last")


def seasons():
    return sorted(int(y) for y in leagues_all()["Year"].unique())


def league_ids(year):
    lg = leagues_all()
    lg = lg[lg["Year"] == str(year)]
    return {r.LeagueName.strip().upper(): r.LeagueID for r in lg.itertuples()}


def teams(year):
    """Slot table for `year`: Team, LeagueName, League (short), LeagueID, RosterID, Key.
    Names are that season's (team_names.names: TeamNames_Historic.csv, else Teams.csv)."""
    import team_names
    t = team_names.names(year).copy()
    t["Team"] = t["Team"].str.strip()
    t["LeagueName"] = t["LeagueName"].str.strip()
    ids, short = league_ids(year), league_short()
    t["LeagueID"] = t["LeagueName"].str.upper().map(ids)
    t["League"] = t["LeagueName"].str.upper().map(short).fillna(t["LeagueName"])
    t["Key"] = t["Team"].map(norm)
    clash = t["Key"].duplicated(keep=False)  # e.g. Miami vs Miami (OH): keep the qualifier
    t.loc[clash, "Key"] = t.loc[clash, "Team"].map(lambda x: re.sub(r"[^a-z0-9]+", "", str(x).lower().replace("&", "and")))
    dup = t[t["Key"].duplicated(keep=False)]
    if len(dup):
        raise SystemExit(f"{year}: team names collide after normalizing: {sorted(dup['Team'])}")
    return t[["Team", "LeagueName", "League", "LeagueID", "RosterID", "Key"]]


# ---------------------------------------------------------------- standings / computer ballot
def matchups(year):
    """Matchup rows for `year` (Season file, then history sources). PointsFor = standard
    scoring where restated; PointsOfficial = Sleeper's number. Outcome stays official."""
    hc = history_cfg()
    paths = [MATCHUPS_SEASON] + hc.get("matchups", [MATCHUPS_HISTORIC])
    frames = [pd.read_csv(p, dtype=str) for p in paths if os.path.exists(p)]
    m = pd.concat(frames, ignore_index=True)
    m = m[m["Year"] == str(year)].copy()
    for c in ("RosterID", "OpponentRosterID"):  # some pulls stored roster ids as '3.0'
        if c in m.columns:
            m[c] = m[c].str.replace(r"\.0$", "", regex=True)
    m["Week"] = m["Week"].astype(int)
    m["PointsFor"] = m["PointsFor"].astype(float)
    m = m.drop_duplicates(["LeagueID", "Week", "RosterID"], keep="first")
    m["PointsOfficial"] = m["PointsFor"]
    sp = hc.get("standard_scores")
    if sp and os.path.exists(sp):
        s = pd.read_csv(sp, dtype=str)
        s = s[s["Year"] == str(year)]
        if len(s):
            std = {(a, int(w), b): float(v) for a, w, b, v in zip(s["LeagueID"], s["Week"], s["RosterID"], s["PointsStandard"])}
            m["PointsFor"] = [std.get((a, w, b), p) for a, w, b, p in zip(m["LeagueID"], m["Week"], m["RosterID"], m["PointsFor"])]
    return m


def standings_through(cfg, m, through_week):
    """W/L/T/PF per slot for regular-season weeks 1..through_week (capped at last_regular_week)."""
    upto = min(int(through_week), int(cfg.get("last_regular_week", 11)))
    r = m[(m["Week"] <= upto) & m["Outcome"].isin(["Win", "Loss", "Tie"])].copy()
    r["W"] = (r["Outcome"] == "Win").astype(int)
    r["L"] = (r["Outcome"] == "Loss").astype(int)
    r["T"] = (r["Outcome"] == "Tie").astype(int)
    r["LeagueName"] = r["LeagueName"].str.strip()
    s = r.groupby(["LeagueID", "LeagueName", "RosterID"], as_index=False).agg(
        Wins=("W", "sum"), Losses=("L", "sum"), Ties=("T", "sum"), PF=("PointsFor", "sum"))
    s["WinVal"] = s["Wins"] + 0.5 * s["Ties"]
    s["PF"] = s["PF"].round(2)
    return s


def computer_order(st, pool=None):
    """Slots ordered by WinVal then PF (the league's own Playoff Rank rule), stable by key."""
    s = st.copy()
    if pool is not None:
        s = s[[(a, b) in pool for a, b in zip(s["LeagueID"], s["RosterID"])]]
    s = s.sort_values(["WinVal", "PF", "LeagueID", "RosterID"], ascending=[False, False, True, True])
    return list(zip(s["LeagueID"], s["RosterID"]))


def playoff_pool(year):
    if not os.path.exists(FIELD):
        raise SystemExit(f"{FIELD} missing: the Seeding poll needs playoff_field.py to have run.")
    f = pd.read_csv(FIELD, dtype=str)
    f = f[f["Year"] == str(year)]
    if len(f) == 0:
        raise SystemExit(f"{FIELD} has no rows for {year}.")
    return set(zip(f["LeagueID"], f["RosterID"]))


# ---------------------------------------------------------------- voters
def voters():
    if not os.path.exists(VOTERS):
        return pd.DataFrame(columns=["VoterID", "VoterName", "Aliases", "Email", "SleeperUserID", "Role", "Active"])
    v = pd.read_csv(VOTERS, dtype=str, encoding="utf-8-sig").fillna("")
    return v[v["Active"].str.strip().str.lower().isin(["", "true", "yes", "y", "1"])]


def own_slot(m, sleeper_user_id):
    """(LeagueID, RosterID) the user owns in the latest week of `m`, or None."""
    if not sleeper_user_id:
        return None
    last = m[m["Week"] == m["Week"].max()]
    hit = last[last["OwnerID"] == str(sleeper_user_id)]
    return (hit["LeagueID"].iloc[0], hit["RosterID"].iloc[0]) if len(hit) else None


# ---------------------------------------------------------------- poll files
def read_polls():
    frames = [pd.read_csv(p, dtype=str) for p in (POLL_HISTORIC, POLL_SEASON) if os.path.exists(p)]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=POLL_COLS)


def latest_official(year=None):
    """Latest published poll (Top25/Seeding, not the full bot consensus), optionally for one year."""
    p = read_polls()
    if p.empty:
        return p
    p = p[p["PollType"] != CONSENSUS]
    if year is not None:
        p = p[p["Year"] == str(year)]
    if p.empty:
        return p
    p = p.assign(_tw=p["ThroughWeek"].astype(int), _y=p["Year"].astype(int))
    last = p.sort_values(["_y", "_tw"]).iloc[-1]
    return p[(p["_y"] == last["_y"]) & (p["_tw"] == last["_tw"]) & (p["PollType"] == last["PollType"])]


def ranks_for_week(year, applies_to_week):
    """{Team: rank} for ranked teams in the poll that applies to that week's games ({} if none)."""
    if not os.path.exists(POLL_SEASON):
        return {}
    p = pd.read_csv(POLL_SEASON, dtype=str)
    p = p[(p["Year"] == str(year)) & (p["AppliesToWeek"] == str(applies_to_week))
          & (p["Status"] == "Ranked") & (p["PollType"] != CONSENSUS)]
    return {r.Team: int(r.Rank) for r in p.itertuples()}
