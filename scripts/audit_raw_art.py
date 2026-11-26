"""Verify every removed App raw-art blob exists in the pinned Asset migration."""
import argparse
import csv
import io
from pathlib import Path
import subprocess

APP_BASE = "b6faeb8304791225a2d99742a7024ed0011f2b1e"
ASSET_MIGRATION = "d16308612c0a6efb98a23f06b8f704f21b56ae62"
RAW = ("assets/logos/source/", "assets/logos/logo jackpot/")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode()


def blobs(repo, commit):
    result = {}
    for entry in git(repo, "ls-tree", "-r", "-z", commit).split("\0"):
        if entry:
            meta, path = entry.split("\t", 1)
            _, kind, oid = meta.split()
            if kind == "blob":
                result[path] = oid
    return result


def verified_rows(app, asset, asset_ref):
    before = blobs(app, APP_BASE)
    migrated = blobs(asset, asset_ref)
    manifest = csv.DictReader(io.StringIO(git(asset, "show", f"{asset_ref}:migration-manifest.csv")))
    destinations = {f"assets/{row['original_path']}": row["new_path"] for row in manifest}
    for path, oid in sorted(before.items()):
        if path.startswith(RAW):
            dest = destinations.get(path)
            if not dest or not dest.startswith(("Master/", "Archive/", "Unused/")) or migrated.get(dest) != oid:
                raise ValueError(f"Missing identical Asset blob {oid}: {path} -> {dest}")
            yield path, oid, dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset_repo", type=Path)
    parser.add_argument("--app-head", default="HEAD")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    before = blobs(root, APP_BASE)
    after = blobs(root, args.app_head)
    removed_art = {path for path in before.keys() - after.keys() if path.startswith("assets/")}
    rows = list(verified_rows(root, args.asset_repo, ASSET_MIGRATION))
    if removed_art != {path for path, _, _ in rows} or any(path.startswith(RAW) for path in after):
        raise ValueError("App artwork removals do not exactly match the verified raw-art paths")
    print(f"Verified {len(rows)} removed App blobs at Asset commit {ASSET_MIGRATION}")


if __name__ == "__main__":
    main()
