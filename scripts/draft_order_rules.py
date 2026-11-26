"""Which basis orders a league's rookie draft (Chris, 2026-11-26).

config/league.json -> draft_order:
  default_basis   "max_pf" for every league, including ones added later
  record_through  {LeagueName: season}: the league orders by record (Sleeper's default) for seasons
                  up to and including this one, then falls back to the default. null = no override.
"Season" is the one whose results set the order (the 2026 season sets the next rookie draft).
"""
import json


def _cfg(cfg=None):
    if cfg is None:
        with open("config/league.json", encoding="utf-8") as f:
            cfg = json.load(f)
    return cfg.get("draft_order", {})


def basis(league_name, season, cfg=None):
    d = _cfg(cfg)
    until = (d.get("record_through") or {}).get(league_name)
    if until is not None and int(season) <= int(until):
        return "record"
    return d.get("default_basis", "max_pf")


def uses_max_pf(league_name, season, cfg=None):
    return basis(league_name, season, cfg) == "max_pf"
