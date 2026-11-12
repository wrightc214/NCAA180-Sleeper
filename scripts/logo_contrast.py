"""Which team logos get a white glow on dark backgrounds (Chris, 2026-11-12).

Scan: each logo in assets/logos/teams is scored by the share of its visible pixels that reach
3:1 contrast (the WCAG minimum for graphics) against the dark card navy (#16213A). A logo below
config logos.glow_cutoff gets the glow. Overrides (config logos): force_glow (passes the scan
but looks weak -- the scan measures color, not detail/small text) and no_glow (flagged but looks
fine). Teams with a dark alt (assets/logos/teams/alt-dark/) never glow: the alt is used instead.

Writes data/LogoGlow.json {"glow_dark": [...], "cutoff", "scores"}; pages read it through
site_common.logo_info(). Run after logos change (the logo-trim workflow runs it):
  python scripts/logo_contrast.py [--sheet out.png]   (--sheet: every glowing logo, for review)
"""
import glob
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg  # noqa: E402

LOGOS = "assets/logos/teams"
OUT = "data/LogoGlow.json"
DARK = (22, 33, 58)  # card navy, --panel in dark mode


def lum(c):
    c = c / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def score(path, bg=DARK):
    a = np.asarray(Image.open(path).convert("RGBA").resize((128, 128)), float)
    vis = a[..., 3] > 128
    if not vis.any():
        return 1.0
    L, B = lum(a[..., :3][vis]), lum(np.array(bg, float))
    cr = (np.maximum(L, B) + 0.05) / (np.minimum(L, B) + 0.05)
    return round(float((cr >= 3).mean()), 3)


def build():
    c = lcfg.cfg().get("logos", {})
    cut = float(c.get("glow_cutoff", 0.3))
    force, never = set(c.get("force_glow", [])), set(c.get("no_glow", []))
    alts = {os.path.basename(p)[:-4] for p in glob.glob(f"{LOGOS}/alt-dark/*.png")}
    scores = {os.path.basename(p)[:-4]: score(p) for p in sorted(glob.glob(f"{LOGOS}/*.png"))}
    glow = sorted(t for t, s in scores.items() if (s < cut or t in force) and t not in never and t not in alts)
    for t in sorted(force - set(scores)):
        print(f"logo_contrast: force_glow team has no logo: {t}")
    return {"glow_dark": glow, "cutoff": cut, "scores": scores}


def sheet(glow, path):
    def halo(lg):
        a = lg.getchannel("A").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.5))
        w = Image.new("RGBA", lg.size, (255, 255, 255, 0))
        w.putalpha(a.point(lambda v: min(255, int(v * 1.3))))
        w.alpha_composite(lg)
        return w
    cols, cw, ch = 6, 170, 130
    img = Image.new("RGB", (cols * cw, max(1, (len(glow) + cols - 1) // cols) * ch), DARK)
    d = ImageDraw.Draw(img)
    for k, t in enumerate(glow):
        lg = Image.open(f"{LOGOS}/{t}.png").convert("RGBA")
        lg.thumbnail((80, 80))
        pad = Image.new("RGBA", (lg.width + 8, lg.height + 8), (0, 0, 0, 0))
        pad.paste(lg, (4, 4), lg)
        x, y = (k % cols) * cw, (k // cols) * ch
        img.paste(pad, (x + 6, y + 6), pad)
        g = halo(pad)
        img.paste(g, (x + 86, y + 6), g)
        d.text((x + 6, y + 112), t, fill=(200, 210, 230))
    img.save(path)


def main():
    os.chdir(lcfg.ROOT)
    r = build()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    if old != r:
        with open(OUT, "w") as f:
            json.dump(r, f, indent=1, sort_keys=True)
            f.write("\n")
    print(f"logo_contrast: {len(r['glow_dark'])} logos glow on dark (cutoff {r['cutoff']})")
    if "--sheet" in sys.argv:
        sheet(r["glow_dark"], sys.argv[sys.argv.index("--sheet") + 1])


if __name__ == "__main__":
    main()
