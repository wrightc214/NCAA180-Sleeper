"""Glow versions of every team logo, for dark backgrounds.

Every normal logo in assets/logos/teams gets a copy with a thin white glow around it in
assets/logos/teams/glow-dark/<Team>.png. On a dark background pages use, in order:
  1. assets/logos/teams/alt-dark/<Team>.png   (owner-selected dark alt -- overrides the glow)
  2. assets/logos/teams/glow-dark/<Team>.png  (this script)
  3. the normal logo
Light backgrounds always use the normal logo. The glow is baked into the image (not a CSS
effect) so saved images and generated cards show it too.

Runs after logo validation. Writes changed glow files and removes orphaned output.
Run with python scripts/logo_glow.py.
"""
import glob
import os
import sys

from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402

SRC = "assets/logos/teams"
OUT = os.path.join(SRC, "glow-dark")
# Glow size relative to the logo's longest side (two layers, like a tight + soft halo).
# Tuned so a logo shown ~40px tall gets about a 1px solid + 2px soft white edge.
INNER, OUTER, PAD = 1 / 40, 1 / 20, 1 / 12
MAX_SIDE = 256  # pages show logos well under 128px; 256 covers 2x saved images and keeps files small


def glow(im):
    im = im.convert("RGBA")
    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    s = max(im.size)
    p = max(2, round(s * PAD))
    base = Image.new("RGBA", (im.width + 2 * p, im.height + 2 * p), (0, 0, 0, 0))
    base.paste(im, (p, p), im)
    a = base.getchannel("A")
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for r, strength in ((s * INNER, 2.6), (s * OUTER, 1.4)):
        halo = a.filter(ImageFilter.GaussianBlur(max(0.6, r))).point(lambda v, k=strength: min(255, int(v * k)))
        layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
        layer.putalpha(halo)
        out.alpha_composite(layer)
    out.alpha_composite(base)
    return out


def main():
    os.chdir(lcfg.ROOT)
    os.makedirs(OUT, exist_ok=True)
    have, wrote = set(), 0
    for path in sorted(glob.glob(os.path.join(SRC, "*.png"))):
        name = os.path.basename(path)
        have.add(name)
        dst = os.path.join(OUT, name)
        with Image.open(path) as source:
            output = glow(source)
        if os.path.exists(dst):
            try:
                with Image.open(dst) as existing:
                    rgba = existing.convert("RGBA")
                if rgba.size == output.size and rgba.tobytes() == output.tobytes():
                    continue
            except OSError:
                pass  # Rebuild broken generated output.
        output.save(dst, optimize=True)
        wrote += 1
    gone = [f for f in os.listdir(OUT) if f.endswith(".png") and f not in have]
    for f in gone:
        os.remove(os.path.join(OUT, f))
    print(f"logo_glow: {len(have)} logos, {wrote} glow files written, {len(gone)} removed")


if __name__ == "__main__":
    main()
