"""tiebreak.py -- one ranking rule for every place teams are compared.

The order lives in config/league.json -> tiebreakers.order (Chris, 2026-10-30). Keys:
  win_pct       (wins + half of ties) / games played
  wins          raw wins
  points_for    regular-season points for
  head_to_head  record in regular-season games between the teams still tied at that point
Each key splits the teams still tied after the keys before it, so head_to_head only ever
compares teams that are exactly level on everything above it. Teams level after the last
key stay tied and are reported, never guessed.
"""
import pandas as pd

import league_config as lcfg

KEYS = ("win_pct", "wins", "points_for", "head_to_head")


def order_keys():
    keys = list(lcfg.cfg()["tiebreakers"]["order"])
    bad = [k for k in keys if k not in KEYS]
    if bad:
        raise ValueError(f"Unknown tiebreaker(s) in config/league.json: {bad} (allowed: {', '.join(KEYS)})")
    return keys


def _value(key, df, group, games):
    if key == "win_pct":
        gp = df.loc[group, "Wins"] + df.loc[group, "Losses"] + df.loc[group, "Ties"]
        return ((df.loc[group, "Wins"] + 0.5 * df.loc[group, "Ties"]) / gp.where(gp > 0, 1)).round(6)
    if key == "wins":
        return df.loc[group, "Wins"]
    if key == "points_for":
        return df.loc[group, "PointsFor"].round(2)
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


def order(df, games=None):
    """(df sorted best first, unresolved) -- unresolved = lists of team names still tied after
    every tiebreaker. df needs Wins, Losses, Ties, PointsFor, LeagueID, RosterID (Team optional).
    games: regular-season rows with LeagueID, RosterID, OpponentRosterID, Res (for head_to_head)."""
    df = df.reset_index(drop=True).copy()
    for c in ("Losses", "Ties"):
        if c not in df.columns:
            df[c] = 0
    keys = order_keys()

    def split(group, ks):
        if len(group) < 2 or not ks:
            return [group]
        v = _value(ks[0], df, group, games)
        blocks = []
        for val in sorted(set(v.tolist()), reverse=True):
            blocks += split([i for i in group if v[i] == val], ks[1:])
        return blocks

    blocks = split(list(df.index), keys)
    out = df.loc[[i for b in blocks for i in b]].reset_index(drop=True)
    name = lambda i: str(df.at[i, "Team"]) if "Team" in df.columns else f"{df.at[i, 'LeagueID']}#{df.at[i, 'RosterID']}"
    return out, [[name(i) for i in b] for b in blocks if len(b) > 1]
