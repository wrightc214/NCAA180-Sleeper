"""tiebreak.py -- one ranking rule for every place teams are compared.

The order lives in config/league.json -> tiebreakers.order (Chris, 2026-10-30). Keys:
  win_pct       (wins + half of ties) / games played
  wins          raw wins
  points_for    regular-season points for
  points_against regular-season points against (higher ranks higher -- Sleeper)
  head_to_head  record in regular-season games between the teams still tied at that point
  coin_toss     reproducible "coin toss": a fixed hash of season + team, so reruns agree
Each key splits the teams still tied after the keys before it, so head_to_head only ever
compares teams that are exactly level on everything above it. Teams level after the last
key stay tied and are reported. Every coin toss used is reported too.
Sleeper's default (support.sleeper.com, checked 2026-10-30): points for, points against, coin toss.

Real coin toss (Chris, 2026-11-12): where a tie decides a real outcome -- the last playoff at-large
spot or a division title -- there is NO hidden toss. order(..., real_toss=True) skips coin_toss; a
tie still standing is reported, and a real toss is held with both managers present. Its result is
recorded in config/league.json -> tiebreakers.coin_toss_results and applied on the next run:
  {"year": 2026, "teams": ["Team A", "Team B"], "order": ["Team A", "Team B"], "note": "..."}
Lower-stakes orders (bowl / NIT pools, projections) keep the simulated toss, which is reported.
"""
import zlib

import pandas as pd

import league_config as lcfg

KEYS = ("win_pct", "wins", "points_for", "points_against", "head_to_head", "coin_toss")


def order_keys():
    keys = list(lcfg.cfg()["tiebreakers"]["order"])
    bad = [k for k in keys if k not in KEYS]
    if bad:
        raise ValueError(f"Unknown tiebreaker(s) in config/league.json: {bad} (allowed: {', '.join(KEYS)})")
    return keys


def _value(key, df, group, games, label=""):
    if key == "win_pct":
        gp = df.loc[group, "Wins"] + df.loc[group, "Losses"] + df.loc[group, "Ties"]
        return ((df.loc[group, "Wins"] + 0.5 * df.loc[group, "Ties"]) / gp.where(gp > 0, 1)).round(6)
    if key == "wins":
        return df.loc[group, "Wins"]
    if key == "points_for":
        return df.loc[group, "PointsFor"].round(2)
    if key == "points_against":
        return df.loc[group, "PointsAgainst"].round(2)
    if key == "coin_toss":
        return pd.Series({i: zlib.crc32(f"{label}|{df.at[i, 'LeagueID']}|{df.at[i, 'RosterID']}".encode()) for i in group})
    # head_to_head: only games between teams of this group (same league)
    out = {i: 0.0 for i in group}
    if games is None or len(group) < 2:
        return pd.Series(out)
    slots = {(str(df.at[i, "LeagueID"]), str(df.at[i, "RosterID"])): i for i in group}
    g = games[[(str(l), str(r)) in slots and (str(l), str(o)) in slots
               for l, r, o in zip(games["LeagueID"], games["RosterID"], games["OpponentRosterID"])]]
    for l, r, res in zip(g["LeagueID"], g["RosterID"], g["Res"]):
        out[slots[(str(l), str(r))]] += 1.0 if res == "Win" else 0.5 if res == "Tie" else 0.0
    return pd.Series(out)


def recorded(year):
    """Real coin tosses recorded for a season: {frozenset(teams): [winner first, ...]}."""
    out = {}
    for r in lcfg.cfg()["tiebreakers"].get("coin_toss_results", []):
        if str(r.get("year")) == str(year):
            out[frozenset(r["teams"])] = list(r.get("order") or r["teams"])
    return out


def order(df, games=None, label="", real_toss=False):
    """(df sorted best first, unresolved, coin_tosses). unresolved = lists of team names still
    tied after every tiebreaker; coin_tosses = lists of team names split by the coin toss.
    df needs Wins, Losses, Ties, PointsFor (PointsAgainst for that key), LeagueID, RosterID,
    Team optional. games: regular-season rows with LeagueID, RosterID, OpponentRosterID, Res
    (head_to_head). label: season/context string for the coin toss (keeps reruns identical)."""
    df = df.reset_index(drop=True).copy()
    for c in ("Losses", "Ties"):
        if c not in df.columns:
            df[c] = 0
    keys = order_keys()
    if real_toss:
        keys = [k for k in keys if k != "coin_toss"]
    tosses = []

    def split(group, ks):
        if len(group) < 2 or not ks:
            return [group]
        v = _value(ks[0], df, group, games, label)
        if ks[0] == "coin_toss":
            tosses.append(list(group))
        blocks = []
        for val in sorted(set(v.tolist()), reverse=True):
            blocks += split([i for i in group if v[i] == val], ks[1:])
        return blocks

    blocks = split(list(df.index), keys)
    name = lambda i: str(df.at[i, "Team"]) if "Team" in df.columns else f"{df.at[i, 'LeagueID']}#{df.at[i, 'RosterID']}"
    if real_toss:  # apply real tosses already held; the rest stay tied (reported)
        rec = recorded(label)
        for bi, b in enumerate(blocks):
            res = rec.get(frozenset(name(i) for i in b)) if len(b) > 1 else None
            if res:
                blocks[bi:bi + 1] = [[i] for i in sorted(b, key=lambda i: res.index(name(i)))]
    out = df.loc[[i for b in blocks for i in b]].reset_index(drop=True)
    return (out, [[name(i) for i in b] for b in blocks if len(b) > 1],
            [[name(i) for i in g] for g in tosses])
