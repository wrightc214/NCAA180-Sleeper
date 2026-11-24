"""
league_roles.py -- who holds an official league role (task 5.18; imported, not run).

One lookup shared by the About page directory (about_page.py) and the Dwight Fight bracket
(dwight_page.py), so both always agree:
  league manager   config about.league_manager.sleeper, else the commissioner of the most conferences
                   (not the data contact or an account without a team)
  data contact     config about.data_contact.sleeper
  assistants       everyone else with LM powers in a conference (data/LeagueStaff.csv IsOwner, written by
                   league_staff.py)
Names are Sleeper names; matching is case-insensitive (Sleeper usernames are case-insensitive handles).
"""
import os

import pandas as pd

import league_config as lcfg

STAFF = "data/LeagueStaff.csv"
RANK = {"league_manager": 0, "data_contact": 1, "assistant": 2}  # highest role wins


def staff():
    """{'league_manager', 'data_contact', 'special': {name: [conference]}, 'owners': rows with LM powers,
    'staff': every LeagueStaff row}. Same rules the About page has always used."""
    a = lcfg.cfg().get("about", {})
    st = pd.read_csv(STAFF, dtype=str, keep_default_na=False) if os.path.exists(STAFF) else pd.DataFrame()
    # accounts without a team (Chris, 2026-11-07): users with no roster in any league they're in
    if len(st):
        has = st.groupby("DisplayName")["HasRoster"].apply(lambda x: (x == "True").any())
        special = {n: sorted(st[st["DisplayName"] == n]["LeagueName"]) for n in has[~has].index}
    else:
        special = {}
    lm, dc = a.get("league_manager", {}), a.get("data_contact", {})
    owners = st[st["IsOwner"] == "True"] if len(st) else st
    lm_name = lm.get("sleeper", "")
    if not lm_name and len(owners):  # the commissioner of the most leagues, not the data contact or a special account
        c = owners[~owners["DisplayName"].isin(list(special) + [dc.get("sleeper", "")])]["DisplayName"].value_counts()
        lm_name = c.index[0] if len(c) and c.iloc[0] > 1 else ""
    return {"league_manager": lm_name, "data_contact": dc.get("sleeper", ""), "special": special,
            "owners": owners, "staff": st}


def roles(s=None):
    """{casefolded Sleeper name: (role, conference)} for everyone with an official role; role is
    'league_manager' / 'data_contact' / 'assistant' (conference = the full Sleeper league name for an
    assistant, else ''). A person with several roles keeps the highest (RANK)."""
    s = s or staff()
    out = {}

    def put(name, role, conf=""):
        k = str(name or "").strip().casefold()
        if k and (k not in out or RANK[role] < RANK[out[k][0]]):
            out[k] = (role, conf)
    put(s["league_manager"], "league_manager")
    put(s["data_contact"], "data_contact")
    taken = {s["league_manager"], s["data_contact"], *s["special"]}
    if len(s["owners"]):
        for lg, n in sorted(zip(s["owners"]["LeagueName"], s["owners"]["DisplayName"]), key=lambda x: x[0].strip()):
            if n not in taken:
                put(n, "assistant", lg.strip())
    return out
