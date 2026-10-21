"""Trim empty canvas around team logos so every page shows the logo at full size.

Many logos sit on a wide 500x281 canvas; a tall logo (e.g. Sparky) fills only the middle,
and pages that fit the canvas into a square box shrink the logo with the empty sides.
This crops each PNG to its visible pixels (alpha > 8) plus a small even margin.

Idempotent: files already within the target margin are left untouched, so it is safe to
run every week; new uploads get trimmed automatically. Originals remain in git history.

Usage: python scripts/logo_trim.py [folder ...]   (default: assets/logos/teams)
"""
import glob
import sys

from PIL import Image

MARGIN = 0.04       # margin on each side, as a share of the logo's longer side
TOLERANCE = 0.02    # skip files whose existing margins are already this close to the target
ALPHA_MIN = 8       # pixels at or below this alpha count as empty


def trim(path):
    im = Image.open(path)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] == 255:
        return False  # fully opaque: no transparent padding to remove
    bb = alpha.point(lambda v: 255 if v > ALPHA_MIN else 0).getbbox()
    if not bb:
        return False
    w, h = im.size
    cw, ch = bb[2] - bb[0], bb[3] - bb[1]
    pad = round(max(cw, ch) * MARGIN)
    gaps = (bb[0], bb[1], w - bb[2], h - bb[3])
    if max(abs(g - pad) for g in gaps) <= max(2, round(max(cw, ch) * TOLERANCE)):
        return False
    out = Image.new("RGBA", (cw + 2 * pad, ch + 2 * pad), (0, 0, 0, 0))
    out.paste(im.crop(bb), (pad, pad))
    out.save(path, optimize=True)
    return True


def main(folders):
    changed = [p for f in folders for p in sorted(glob.glob(f"{f}/*.png")) if trim(p)]
    print(f"Logo trim: {len(changed)} file(s) trimmed" + (": " + ", ".join(changed) if changed and len(changed) <= 10 else ""))


if __name__ == "__main__":
    main(sys.argv[1:] or ["assets/logos/teams"])
