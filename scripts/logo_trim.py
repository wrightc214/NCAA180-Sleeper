"""Logos for the site: trimmed to their visible pixels and capped at web size.

Upload logos at the best quality you have into the normal folder (e.g. assets/logos/teams/).
For each PNG this script:
  1. keeps the high-quality master: a file larger than MAX_SIDE is moved untouched to
     assets/logos/source/<folder>/ (once; a master already there is the source from then on);
  2. writes the web copy the pages use: transparent margin trimmed to a small even margin and
     scaled down to MAX_SIDE on the longer side.
Why (Chris, 2026-10-30): browsers unpack every image to full size; a 3840x2160 logo costs
~33 MB of phone memory even when drawn at 40 px, and pages can show 180 logos. Masters stay
for print, posters and future crops. Re-running is safe: unchanged files come out identical.

Usage: python scripts/logo_trim.py [folder ...]   (default: assets/logos/teams)
"""
import glob
import os
import shutil
import sys

from PIL import Image

MARGIN = 0.04       # margin on each side, as a share of the logo's longer side
TOLERANCE = 0.02    # skip files whose existing margins are already this close to the target
ALPHA_MIN = 8       # pixels at or below this alpha count as empty
MAX_SIDE = 512      # web copy: longest side in pixels (pages show logos at <= ~200 px)


def source_path(path):
    folder, name = os.path.split(path)
    rel = os.path.relpath(folder, "assets/logos")
    return os.path.join("assets/logos/source", rel, name)


def trimmed(im):
    """im cropped to its visible pixels plus an even margin; None if nothing to change."""
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] == 255:
        return None  # fully opaque: no transparent padding to remove
    bb = alpha.point(lambda v: 255 if v > ALPHA_MIN else 0).getbbox()
    if not bb:
        return None
    w, h = im.size
    cw, ch = bb[2] - bb[0], bb[3] - bb[1]
    pad = round(max(cw, ch) * MARGIN)
    gaps = (bb[0], bb[1], w - bb[2], h - bb[3])
    if max(abs(g - pad) for g in gaps) <= max(2, round(max(cw, ch) * TOLERANCE)):
        return None
    out = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    out.paste(im.crop(bb), (pad, pad))
    return out


def process(path):
    src = source_path(path)
    if not os.path.exists(src) and max(Image.open(path).size) > MAX_SIDE:
        os.makedirs(os.path.dirname(src), exist_ok=True)
        shutil.copy2(path, src)  # keep the high-quality original untouched
    base = src if os.path.exists(src) else path
    im = Image.open(base).convert("RGBA")
    out = trimmed(im) or im
    if max(out.size) > MAX_SIDE:
        out.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    if base == path and out is im:
        return False  # already trimmed and web-sized
    before = open(path, "rb").read()
    out.save(path, optimize=True)
    return open(path, "rb").read() != before


def main(folders):
    changed = [p for f in folders for p in sorted(glob.glob(f"{f}/*.png")) if process(p)]
    print(f"Logos: {len(changed)} web copy(ies) written" + (": " + ", ".join(changed) if changed and len(changed) <= 10 else ""))


if __name__ == "__main__":
    main(sys.argv[1:] or ["assets/logos/teams"])
