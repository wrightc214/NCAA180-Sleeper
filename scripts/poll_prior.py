"""
poll_prior.py -- the Professor bot's frozen preseason prior, one season at a time.

  Prior = weighted percentiles (config/poll.json -> professor.prior), across every team that
  season that has the input:
    psv         Preseason Starter Value: redraft value of the best legal starting lineup
    wk1_proj    week-1 projected starter points (Sleeper's pregame projection of the
                lineup actually started)
    dynasty     preseason dynasty (overall) team value
    last_final  last season's final rank (final poll's full order; standings if no poll)
  A team missing an input gets the remaining weights, rescaled to 100% (renormalized).

Sources (paths in config/poll.json -> professor.sources):
  values       data/TeamValuesPreseason_Historic.csv  (Year, LeagueID, RosterID, PSV, DynastyValue)
  projections  week-1 team projections, first file that has the season:
               data/TeamProjectionsWk1_Historic.csv, data/backfill/TeamProjections_History.csv
  professor.exclude_value_years: seasons whose value capture is not preseason (2022 sheet was
  taken mid-season) -- their PSV and dynasty values are ignored.

The prior is FROZEN: build it once, before or right after week 1 (projections exist only
once week-1 lineups are set). Never refreshed in-season.

Writes data/PollPrior_Season.csv for the current season, data/PollPrior_Historic.csv rows
for past seasons: Year, LeagueID, LeagueName, RosterID, PSV, Wk1Proj, Dynasty, LastFinalRank,
<input>Pct for each, Prior, Inputs (which inputs the team had), Basis.

  python scripts/poll_prior.py                 # current season
  python scripts/poll_prior.py --year 2023     # one past season
CWD must be repo root.
"""
import argparse
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402

SEASON_OUT = "data/PollPrior_Season.csv"
HIST_OUT = "data/PollPrior_Historic.csv"
INPUTS = {"psv": "PSV", "wk1_proj": "Wk1Proj", "dynasty": "Dynasty", "last_final": "LastFinalRank"}


def pct(s):
    """Percentile 0..1 (1 = best) among teams that have a value; NaN stays NaN."""
    s = pd.Series(s, dtype=float)
    n = s.notna().sum()
    return (s.rank(method="average") - 1) / max(n - 1, 1)


def last_final(year, keys_by_slot):
    """{(LeagueID, RosterID) this season: last season's final rank}, matched by league name + roster."""
    prev = str(int(year) - 1)
    final = {}
    p = pc.read_polls()
    if len(p):
        p = p[(p["Year"] == prev) & (p["PollType"] == pc.CONSENSUS)]
        if len(p):
            p = p[p["ThroughWeek"].astype(int) == p["ThroughWeek"].astype(int).max()]
            final = {(r.LeagueName.strip().upper(), r.RosterID): int(r.Rank) for r in p.itertuples()}
    if not final:  # no poll that season: standings (wins, then points)
        m = pc.matchups(prev) if int(prev) in pc.seasons() else pd.DataFrame()
        if len(m):
            st = pc.standings_through(pc.config(), m, 99).sort_values(["WinVal", "PF"], ascending=False)
            final = {(r.LeagueName.strip().upper(), r.RosterID): i + 1 for i, r in enumerate(st.itertuples())}
    return {k: final.get(s) for k, s in keys_by_slot.items()}


def build(year, cfg):
    pcfg = cfg["professor"]
    w = {k: float(v) for k, v in pcfg["prior"].items() if not k.startswith("_")}
    src = pcfg.get("sources", {})
    t = pc.teams(year)
    keys = list(zip(t["LeagueID"], t["RosterID"]))
    out = pd.DataFrame({"Year": year, "LeagueID": t["LeagueID"], "LeagueName": t["LeagueName"], "RosterID": t["RosterID"]})
    basis = []

    vf = src.get("values")
    excl = {str(y) for y in pcfg.get("exclude_value_years", [])}
    psv = dyn = {}
    if vf and os.path.exists(vf) and str(year) not in excl:
        v = pd.read_csv(vf, dtype=str)
        v = v[v["Year"] == str(year)]
        psv = {(a, b): float(x) for a, b, x in zip(v["LeagueID"], v["RosterID"], v["PSV"]) if pd.notna(x)}
        dyn = {(a, b): float(x) for a, b, x in zip(v["LeagueID"], v["RosterID"], v["DynastyValue"]) if pd.notna(x)}
        if psv or dyn:
            basis.append(f"values {os.path.basename(vf)} (PSV {len(psv)}, dynasty {len(dyn)})")
    elif str(year) in excl:
        basis.append(f"values excluded for {year} (not a preseason capture)")
    out["PSV"] = [psv.get(k) for k in keys]
    out["Dynasty"] = [dyn.get(k) for k in keys]

    proj = {}
    for f in src.get("projections", []):
        if os.path.exists(f):
            p = pd.read_csv(f, dtype=str)
            p = p[(p["Year"] == str(year)) & (p["Week"].astype(int) == 1)]
            if len(p):
                proj = {(a, b): float(x) for a, b, x in zip(p["LeagueID"], p["RosterID"], p["ProjectedPts"])}
                basis.append(f"week-1 projections {os.path.basename(f)}")
                break
    out["Wk1Proj"] = [proj.get(k) for k in keys]

    slot = {k: (ln.strip().upper(), r) for k, ln, r in zip(keys, t["LeagueName"], t["RosterID"])}
    lf = last_final(year, slot)
    out["LastFinalRank"] = [lf.get(k) for k in keys]
    if any(v is not None for v in lf.values()):
        basis.append(f"final order {int(year) - 1}")

    num = pd.Series(0.0, index=out.index)
    den = pd.Series(0.0, index=out.index)
    have = [[] for _ in range(len(out))]
    for k, col in INPUTS.items():
        x = out[col].astype(float)
        p = pct(-x if k == "last_final" else x)
        out[col + "Pct"] = p.round(4)
        ok = p.notna()
        num[ok] += w.get(k, 0) * p[ok]
        den[ok] += w.get(k, 0)
        for i in out.index[ok & (w.get(k, 0) > 0)]:
            have[i].append(k)
    out["Prior"] = (num / den.where(den > 0)).round(4)
    out["Inputs"] = ["+".join(h) for h in have]
    out["Basis"] = "; ".join(basis) or "no inputs"
    return out


def save(df, year, current):
    path = SEASON_OUT if current else HIST_OUT
    old = pd.read_csv(path, dtype=str) if os.path.exists(path) else pd.DataFrame(columns=df.columns)
    if current:  # Season file holds the current season only
        old = old.iloc[0:0]
    old = old[old["Year"] != str(year)] if len(old) else old
    pd.concat([old, df.astype(str)], ignore_index=True).sort_values(["Year", "LeagueID", "RosterID"]).to_csv(path, index=False)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int)
    a = ap.parse_args()
    cfg = pc.config()
    current = max(pc.seasons())
    year = a.year or current
    df = build(year, cfg)
    path = save(df, year, year == current)
    n = df["Prior"].notna().sum()
    print(f"{path}: {year} prior for {n}/{len(df)} teams; inputs: {df['Inputs'].value_counts().to_dict()}; {df['Basis'].iloc[0]}")


if __name__ == "__main__":
    main()
