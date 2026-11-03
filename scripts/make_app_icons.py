"""make_app_icons.py -- app icons from the Dynasty Data bot avatar (a blue disc on any background).

  python scripts/make_app_icons.py SOURCE_IMAGE reports/assets/icons

Finds the blue disc, crops it, and writes icon-192/512, maskable-512 (disc shrunk so Android's
round crop keeps the edge text), apple-touch-icon and a one-color badge-96 (football silhouette).
The area outside the disc is filled with the disc's own blue, so the edge is seamless."""
import sys
from PIL import Image, ImageDraw
import numpy as np
src, out = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(int)
blue = (abs(a[..., 0] - 0x00) < 60) & (abs(a[..., 1] - 0x9c) < 60) & (abs(a[..., 2] - 0xde) < 60)
ys, xs = np.nonzero(blue)
cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
r = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
box = (int(cx - r), int(cy - r), int(cx + r), int(cy + r))
disc = im.crop(box)
d = disc.size[0]
mask = Image.new("L", (d, d), 0)
ImageDraw.Draw(mask).ellipse((1, 1, d - 2, d - 2), fill=255)
BLUE = tuple(int(v) for v in np.median(a[blue], axis=0))

def icon(size, disc_frac, name):
    can = Image.new("RGB", (size, size), BLUE)
    s = int(size * disc_frac)
    dd = disc.resize((s, s), Image.LANCZOS)
    mm = mask.resize((s, s), Image.LANCZOS)
    can.paste(dd, ((size - s) // 2, (size - s) // 2), mm)
    can.save(f"{out}/{name}", optimize=True)

import os
os.makedirs(out, exist_ok=True)
icon(192, 1.00, "icon-192.png")
icon(512, 1.00, "icon-512.png")
icon(512, 0.86, "maskable-512.png")   # Android round crop keeps the disc edge text
icon(180, 1.00, "apple-touch-icon.png")
# monochrome status-bar badge: solid football silhouette (convex hull of the brown pixels) in white
from scipy.spatial import ConvexHull
small = disc.resize((96, 96), Image.LANCZOS)
b = np.asarray(small).astype(int)
brown = (b[..., 0] > 90) & (b[..., 0] < 210) & (b[..., 1] < 120) & (b[..., 2] < 90) & (b[..., 0] - b[..., 2] > 40)
ys, xs = np.nonzero(brown)
pts = np.stack([xs, ys], 1)
hull = [tuple(int(v) for v in pts[i]) for i in ConvexHull(pts).vertices]
badge = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
ImageDraw.Draw(badge).polygon(hull, fill=(255, 255, 255, 255))
badge.save(f"{out}/badge-96.png")
print("disc box", box)
