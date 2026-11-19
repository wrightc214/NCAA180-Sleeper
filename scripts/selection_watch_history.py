"""Build the read-only Selection Watch archive from recorded postseason results."""
import csv
import json
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/Postseason_Historic.csv"
OUTPUT = ROOT / "reports/postseason/selection-watch-history.json"


def verified_steals(year, games, entrants):
    # Modern Steal Board labels only when the mathematical field matches the real field.
    # 2019–2020 used different formats. Older-format or incomplete data must not imply a result.
    if len(games) != 15 or len(entrants) != 32 or year <= 2020:
        return
    from selection_watch import build as build_board, field, final_labels
    previous = Path.cwd()
    try:
        os.chdir(ROOT)
        board = build_board(year)
    finally:
        os.chdir(previous)
    by_key = {team["k"]: team for team in board["order"]}
    winners = [game["winner"] for game in board["ccg"]]
    if not all(winners):
        return
    actual = {by_key[key]["team"] for key, share in field(board, winners).items() if share == 1}
    if actual != set(entrants):
        return
    labels = final_labels(board, {g["id"]: g["winner"] for g in board["ccg"]})
    names = {key: team["team"] for key, team in by_key.items()}
    recorded = {frozenset((g["a"], g["b"])): g for g in games}
    for g in board["ccg"]:
        recorded[frozenset((names[g["a"]], names[g["b"]]))]["label"] = labels[g["id"]]
    return {
        "field_size": board["field_size"],
        "order": [{"k": t["team"], "team": t["team"], "rank": t["rank"], "conf": t["conf"]}
                  for t in board["order"]],
        "ccg": [{"id": g["id"], **{k: names[g[k]] for k in ("a", "b", "winner")}}
                for g in board["ccg"]],
        "play_ins": board["play_ins"],
        "tie": [[names[k] for k in group] for group in board["tie"]],
        "colors": {name: style["background"] for name, style in board["style"].items() if style["background"]},
    }


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
            game = {"conference": r["Bowl"].strip(), "a": a, "b": b, "winner": winner,
                    "score_a": float(r["ScoreA"]), "score_b": float(r["ScoreB"])}
            for side in ("A", "B"):
                standard = r["OfficialScore" + side].strip()
                if standard and float(standard) != game["score_" + side.lower()]:
                    game["standard_" + side.lower()] = float(standard)
            games.append(game)
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
        board = verified_steals(year, games, entrants) if source == SOURCE else None
        history[str(year)] = {
            **({"cut_board": board} if board else {}),
            "champion": final["Winner"].strip(),
            "ccg": sorted(games, key=lambda g: g["conference"]),
            "field": [{"team": name, "seed": seed} for name, seed in
                      sorted(entrants.items(), key=lambda item: (item[1] is None, item[1] or 0, item[0].casefold()))],
        }
    return history


if __name__ == "__main__":
    os.chdir(ROOT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Built {OUTPUT.relative_to(ROOT)}")
