"""Build the read-only Selection Watch archive from recorded postseason results."""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/Postseason_Historic.csv"
OUTPUT = ROOT / "reports/postseason/selection-watch-history.json"


def build(source=SOURCE):
    seasons = defaultdict(list)
    with source.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            seasons[int(row["Season"])].append(row)

    history = {}
    for year, rows in sorted(seasons.items()):
        ccgs = [r for r in rows if r["Event"] == "CCG"]
        playoff = [r for r in rows if r["Event"] == "Playoff"]
        final = next((r for r in playoff if r["RoundName"] == "National Championship"), None)
        if not ccgs or final is None or not final["Winner"].strip():
            continue
        games = []
        for r in ccgs:
            a, b, winner = (r[key].strip() for key in ("TeamA", "TeamB", "Winner"))
            if not a or not b or winner not in (a, b):
                raise ValueError(f"{year} {r['Bowl']} CCG has no recorded winner")
            games.append({"conference": r["Bowl"].strip(), "a": a, "b": b, "winner": winner,
                          "score_a": float(r["ScoreA"]), "score_b": float(r["ScoreB"])})
        entrants = {}
        for r in playoff:
            for side in ("A", "B"):
                names = [v.strip() for v in r["Team" + side].split("|") if v.strip()]
                seeds = [v.strip() for v in r["Seed" + side].split("|")]
                for i, name in enumerate(names):
                    seed = int(seeds[i]) if len(seeds) == len(names) and seeds[i].isdigit() else None
                    if name not in entrants or entrants[name] is None:
                        entrants[name] = seed
                    elif seed is not None and entrants[name] != seed:
                        raise ValueError(f"{year} has conflicting seeds for {name}")
        history[str(year)] = {
            "champion": final["Winner"].strip(),
            "ccg": sorted(games, key=lambda g: g["conference"]),
            "field": [{"team": name, "seed": seed} for name, seed in
                      sorted(entrants.items(), key=lambda item: (item[1] is None, item[1] or 0, item[0].casefold()))],
        }
    return history


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Built {OUTPUT.relative_to(ROOT)}")
