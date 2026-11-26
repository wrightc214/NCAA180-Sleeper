"""Which basis orders a league's rookie draft (Chris, 2026-11-26).

config/league.json -> draft_order:
  default_max_pf_from  season from which EVERY league (including ones added later) uses max PF; null = none
  max_pf_from          {LeagueName: season} for leagues that switched earlier; null = not set
A league uses max PF in a season if that season is >= its own entry or >= the default.
"""
import json


def _cfg(cfg=None):
    if cfg is None:
        with open("config/league.json", encoding="utf-8") as f:
            cfg = json.load(f)
    return cfg.get("draft_order", {})


def uses_max_pf(league_name, season, cfg=None):
    d = _cfg(cfg)
    starts = [d.get("default_max_pf_from"), (d.get("max_pf_from") or {}).get(league_name)]
    return any(s is not None and int(season) >= int(s) for s in starts)


def basis(league_name, season, cfg=None):
    return "max_pf" if uses_max_pf(league_name, season, cfg) else "record"
