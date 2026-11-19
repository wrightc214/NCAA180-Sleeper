"""Persist Team Fit evidence and published results, independent of checkout history."""
import gzip
import json
from pathlib import Path

from transactions_fit import CONTEXT, ODDS_DIR, PICKS, PICK_VALUES, PLAYER_VALUES, ROSTERS, SCORES, TX

ROOT = Path("data/trade-fit")
LEDGER = ROOT / "grades.jsonl"
SNAPSHOTS = ROOT / "snapshots"

# Only model inputs go into the snapshot. No usernames, lineups of record, or full score history.
FIELDS = {
    ROSTERS: "LeagueID PlayerID RosterID",
    PICKS: "LeagueID Season Round OriginalRosterID OwnerRosterID",
    TX: "TransactionID Status",
    CONTEXT: "Year Week LeagueID RosterID W L T Contender",
    SCORES: "LeagueYear league_id weekNum player_id points",
    PLAYER_VALUES: "Date SleeperID Position DynastyValue RedraftValue",
    PICK_VALUES: "Date Season Round Value Early Mid Late",
}


def compact(path, rows):
    fields = FIELDS[path].split()
    return [{field: row.get(field, "") for field in fields} for row in rows]


def publish_snapshot(directory, started, observed, tables, odds):
    if started > observed:
        raise ValueError("Team Fit observation window is inverted")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{observed}.json.gz"
    snapshot = {"start_ms": started, "observed_ms": observed, "tables": tables, "odds": odds}
    data = gzip.compress(json.dumps(snapshot, separators=(",", ":")).encode(), mtime=0)
    if path.exists():
        with gzip.open(path, "rb") as stream:
            if json.load(stream) != snapshot:
                raise ValueError(f"Refusing to overwrite snapshot {path}")
    else:
        atomic_write(path, data)
    return path


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(path)


class FileArchive:
    def __init__(self, directory=SNAPSHOTS):
        self.directory = directory
        self.paths = sorted((p for p in directory.glob("*.json.gz") if p.name.split(".")[0].isdigit()),
                            key=lambda p: int(p.name.split(".")[0]))
        self.bounds = [int(p.name.split(".")[0]) for p in self.paths]
        self.cache = {}

    def load(self, ref):
        if ref not in self.cache:
            with gzip.open(self.directory / ref, "rb") as stream:
                self.cache[ref] = json.load(stream)
        return self.cache[ref]

    def rows(self, ref, path):
        return self.load(ref)["tables"].get(path, [])

    def before(self, timestamp):
        return ((observed, p.name, "") for p, observed in reversed(list(zip(self.paths, self.bounds)))
                if observed < timestamp)

    def after(self, timestamp):
        return ((s["start_ms"], p.name, "") for p, observed in zip(self.paths, self.bounds)
                if observed > timestamp and (s := self.load(p.name))["start_ms"] > timestamp)

    def market(self, timestamp):
        for observed, ref, _ in self.before(timestamp):
            players = self.rows(ref, PLAYER_VALUES)
            picks = self.rows(ref, PICK_VALUES)
            if players and picks:
                return players[0]["Date"], players, picks, {"market": ref, "market_published_ms": observed}
        return None

    def odds(self, timestamp, year, week, start, league):
        for observed, ref, _ in self.before(timestamp):
            for n in range(week, start - 1, -1):
                snapshot = self.load(ref)["odds"].get(str(n), {})
                if int(snapshot.get("year", 0)) == year:
                    return ({str(r["RosterID"]): r for r in snapshot["teams"] if str(r["LeagueID"]) == league},
                            {"odds": ref, "odds_published_ms": observed, "odds_week": n})
        return {}, {}

    def pending(self, timestamp):
        # A pre-trade observation exists but no capture has ended after this trade.
        return bool(self.bounds and self.bounds[0] < timestamp and self.bounds[-1] <= timestamp)


def trade_key(row, roster):
    return str(row["Year"]), str(row["LeagueID"]), str(row["TransactionID"]), str(roster)


class FitLedger:
    def __init__(self, path=LEDGER):
        self.path = path
        self.raw = path.read_bytes() if path.exists() else b""
        self.results = {}
        for line in self.raw.splitlines():
            item = json.loads(line)
            key = tuple(item["key"])
            previous = self.results.get(key)
            if (item["revision"] != (previous["revision"] + 1 if previous else 1)
                    or (previous and not item.get("correction_reason", "").strip())):
                raise ValueError(f"Invalid Team Fit revision for {key}")
            self.results[key] = item

    def evaluate(self, row, sides):
        if not row.get("LeagueID"):
            return {}
        return {roster: self.results[key]["fit"] for roster in sides
                if (key := trade_key(row, roster)) in self.results}

    def append(self, new):
        if new:
            seen = set(self.results)
            for item in new:
                key = tuple(item["key"])
                if key in seen or item["revision"] != 1:
                    raise ValueError(f"Cannot replace a published Team Fit grade {key}")
                seen.add(key)
            data = b"".join((json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n").encode()
                            for item in new)
            prefix = self.raw if not self.raw or self.raw.endswith(b"\n") else self.raw + b"\n"
            atomic_write(self.path, prefix + data)
            self.raw = prefix + data
            self.results.update((tuple(item["key"]), item) for item in new)
