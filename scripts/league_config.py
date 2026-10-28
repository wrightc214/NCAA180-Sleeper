"""Shared league settings (config/league.json) for every Python script.

The browser pages read the same file, so a setting changed here changes both.
History-only rules (one-off fixes for past seasons) stay in the scripts that apply them.
"""
import collections
import csv
import datetime as dt
import functools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@functools.lru_cache(maxsize=None)
def cfg():
    return json.loads((ROOT / "config" / "league.json").read_text(encoding="utf-8"))


def brand():
    return cfg()["brand"]


def sleeper():
    """Sleeper API base, e.g. https://api.sleeper.app/v1."""
    return cfg()["api"]["sleeper"]


def sleeper_root():
    """Sleeper host without the version (projections live at /projections, not /v1)."""
    return sleeper().rsplit("/v1", 1)[0]


def espn():
    return cfg()["api"]["espn"]


def season(today=None):
    """Season label for today's date: Jan-Feb (before rollover_month) belong to last season."""
    today = today or dt.date.today()
    return today.year - 1 if today.month < cfg()["season"]["rollover_month"] else today.year


def lookup_user_id():
    return cfg()["sleeper"]["lookup_user_id"]


def observer_ids():
    return set(cfg()["sleeper"]["observer_ids"])


def eligibility():
    """{slot: set(positions)} for lineup slots."""
    return {k: set(v) for k, v in cfg()["eligibility"].items()}


def last_regular_week():
    return int(cfg()["schedule"]["last_regular_week"])


@functools.lru_cache(maxsize=None)
def league_display():
    """{full Sleeper league name: display short name}, e.g. 'NCAA SEC' -> 'SEC'."""
    c = cfg()["league_names"]
    over = c.get("display_overrides", {})
    with open(ROOT / c["file"], encoding="utf-8-sig", newline="") as f:
        return {r["Full Name"].strip(): over.get(r["Short Name"].strip(), r["Short Name"].strip()) for r in csv.DictReader(f)}


def normalized(settings):
    return {k: round(float(v), 6) for k, v in settings.items() if isinstance(v, (int, float)) and v}


def standard_settings(scoring, overrides=None):
    """Standard ruleset: the season's majority league ruleset (as a whole) plus config overrides.

    scoring = {league_id: Sleeper scoring_settings}; overrides default to config scoring.overrides."""
    choices = collections.Counter(json.dumps(normalized(s), sort_keys=True) for s in scoring.values())
    key, count = choices.most_common(1)[0]
    if count <= len(scoring) / 2:
        raise ValueError("No majority scoring ruleset; review standard settings before building")
    return {**json.loads(key), **(cfg()["scoring"]["overrides"] if overrides is None else overrides)}
