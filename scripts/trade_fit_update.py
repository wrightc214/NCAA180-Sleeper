"""Capture weekly Team Fit evidence, grade new results, or explicitly backfill from Git."""
import argparse
import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import league_config as lcfg
from trade_fit_store import FitLedger, FileArchive, SNAPSHOTS, compact, publish_snapshot, trade_key
from transactions_fit import (CONTEXT, MODEL_VERSION, ODDS_DIR, PICK_VALUES, PICKS, PLAYER_VALUES,
                              ROSTERS, SCORES, TX, GitArchive, TeamFit, archived, event_key, git, history)
from transactions_grades import load_config, read_rows
from transactions_page import PLAYERS, build_teams, trade_assets, TEAMS

TABLES = (ROSTERS, PICKS, TX, CONTEXT, SCORES, PLAYER_VALUES, PICK_VALUES)


def collect(read, read_odds, year, published_day):
    tables = {path: read(path) for path in TABLES}
    # Freeze dated market values from this observation, not from later copies of a history file.
    p_dates = {r["Date"] for r in tables[PLAYER_VALUES]}
    k_dates = {r["Date"] for r in tables[PICK_VALUES]}
    day = max((d for d in p_dates & k_dates if d <= published_day), default=None)
    if not day or not all(tables[path] for path in (ROSTERS, PICKS, CONTEXT, SCORES)):
        raise ValueError("Missing roster, pick, context, score or paired FantasyCalc data")
    for path in (PLAYER_VALUES, PICK_VALUES):
        tables[path] = [r for r in tables[path] if r["Date"] == day]
    context = {}
    for r in tables[CONTEXT]:
        if int(r["Year"]) != year:
            continue
        k = r["LeagueID"], r["RosterID"]
        if k not in context or int(r["Week"]) > int(context[k]["Week"]):
            context[k] = r
    tables[CONTEXT] = list(context.values())
    tables[TX] = [r for r in tables[TX] if r["Status"] == "complete" and int(r["Year"]) == year]
    teams = {(r["LeagueID"], r["RosterID"]) for r in tables[ROSTERS] if r.get("PlayerID")}
    leagues = {r["LeagueID"]: r["LeagueName"] for r in read("data/LeagueIDs_AllYears.csv") if int(r["Year"]) == year}
    named = build_teams(read(TEAMS))
    expected = {(league, roster) for league, name in leagues.items()
                for conference, roster in named if conference == name}
    if not expected or not expected <= teams or not set(context) <= teams:
        raise ValueError("Team Fit capture has incomplete roster coverage")
    if not {league for league, _ in teams} <= {r["LeagueID"] for r in tables[PICKS]}:
        raise ValueError("Team Fit capture has incomplete future-pick coverage")
    # Keep all known specialist scores, so an increased lookback still works on captured data.
    specialist_ids = {r["player_id"] for r in read_rows(PLAYERS)
                      if r.get("position", "").upper() in {"K", "PK", "DST", "DEF", "D/ST"}}
    specialist_ids.update(r["SleeperID"] for r in read_rows("data/PlayerBirthDates.csv")
                          if r["Position"].upper() in {"K", "PK", "DST", "DEF", "D/ST"})
    tables[SCORES] = [r for r in tables[SCORES]
                      if int(r["LeagueYear"]) == year and r["player_id"] in specialist_ids]
    odds = {}
    for name, raw in read_odds():
        if raw:
            data = json.loads(raw)
            if int(data.get("year", 0)) == year:
                odds[name] = {"year": year, "teams": [
                    {k: r[k] for k in ("LeagueID", "RosterID", "Playoff", "Bowl")} for r in data["teams"]
                ]}
    return {path: compact(path, rows) for path, rows in tables.items()}, odds


def odds_names():
    # Consult the present file list for stable week filenames. Legacy reads still resolve
    # their contents at the chosen Git revision, never from the present output.
    return [(p.stem.split("-wk")[1], p) for p in sorted(Path(ODDS_DIR).glob("odds-wk*.json"))
            if p.stem.split("-wk")[1].isdigit()]


def capture(started):
    observed = int(time.time() * 1000)
    day = dt.datetime.fromtimestamp(observed / 1000, dt.timezone.utc).date().isoformat()
    tables, odds = collect(read_rows, lambda: ((str(int(n)), p.read_text()) for n, p in odds_names()),
                           lcfg.season(), day)
    return publish_snapshot(SNAPSHOTS, started, observed, tables, odds)


def seed():
    observed, ref, day = history(ROSTERS)[0]

    def read(path):
        if path == PICK_VALUES:
            return [{**row, "Date": day} for row in archived(ref, "data/PickValues_Current.csv")]
        return archived(ref, path)

    tables, odds = collect(read, lambda: ((str(int(n)), git("show", f"{ref}:{p}"))
                                           for n, p in odds_names()), lcfg.season(), day)
    # The seed is used only as pre-trade evidence in file-based grading of new trades.
    return publish_snapshot(SNAPSHOTS, observed, observed, tables, odds)


def update(archive):
    transactions = read_rows(TX)
    players = {p["player_id"]: p for p in read_rows(PLAYERS)}
    teams = build_teams(read_rows(TEAMS))
    ledger = FitLedger()
    model = TeamFit(transactions, players, load_config(), archive)
    settings = {"model": model.cfg, "bands": model.market["grade_bands"],
                "slots": model.slots, "proxy": model.market["proxy_pick_slot"]}
    fingerprint = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()
    new = []
    ungraded = 0
    for row in sorted(transactions, key=event_key):
        if row["Type"] != "trade" or row["Status"] != "complete":
            continue
        sides = trade_assets(row, teams, players)
        if len(sides) != 2:
            continue
        missing = [r for r in sides if trade_key(row, r) not in ledger.results]
        if not missing:
            continue
        results = model.evaluate(row, sides)
        ungraded += sum(r not in results for r in missing)
        for roster in missing:
            if roster in results:
                new.append({"key": trade_key(row, roster), "revision": 1, "model": MODEL_VERSION,
                            "settings_sha256": fingerprint, "trade_cutoff_ms": event_key(row)[0],
                            "fit": results[roster]})
    ledger.append(new)
    print(f"Team Fit: {len(new)} team grades appended, {len(ledger.results)} retained, {ungraded} unresolved sides")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--capture-start-ms", type=int, metavar="MS")
    mode.add_argument("--backfill-from-git", action="store_true")
    args = parser.parse_args()
    if args.backfill_from_git:
        if git("rev-parse", "--is-shallow-repository").strip() != "false" or not history(ROSTERS):
            parser.error("Backfill requires a full Git checkout with roster history")
        print("Team Fit seed:", seed())
        update(GitArchive())
    else:
        print("Team Fit captured:", capture(args.capture_start_ms))
        update(FileArchive())


if __name__ == "__main__":
    main()
