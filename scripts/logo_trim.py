"""Validate web logos without writing artwork."""
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MARGIN = 0.04
TOLERANCE = 0.02
ALPHA_MIN = 8
MAX_SIDE = 512


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


def web_copy(base):
    im = Image.open(base).convert("RGBA")
    out = trimmed(im) or im
    if max(out.size) > MAX_SIDE:
        out.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    return im, out


def png_bytes(im):
    import io
    b = io.BytesIO()
    im.save(b, format="PNG", optimize=True)
    return b.getvalue()


# How close two images must be to count as the same logo. Pillow versions resize slightly
# differently (found 2026-11-17: a run on another Pillow read 4 unchanged bowl logos as new
# uploads and deleted their masters), so exact pixel equality is too strict. Resampling noise
# moves pixels by a few levels; a real edit moves some pixels a lot.
PIXEL_DIFF = 24       # a pixel "differs" if any channel moved by more than this
DIFF_SHARE = 0.0005   # same logo if at most this share of pixels differ (0.05%)


def same_pixels(a, b):
    """True if a and b are the same logo, allowing small resampling differences."""
    a, b = a.convert("RGBA"), b.convert("RGBA")
    if a.size != b.size:
        return False
    if a.tobytes() == b.tobytes():
        return True
    from PIL import ImageChops
    d = ImageChops.difference(a, b)
    ch = d.split()
    m = ImageChops.lighter(ImageChops.lighter(ch[0], ch[1]), ImageChops.lighter(ch[2], ch[3]))
    big = sum(m.point(lambda v: 255 if v > PIXEL_DIFF else 0).histogram()[255:])
    return big <= DIFF_SHARE * a.size[0] * a.size[1]


def validate(root, selection=None):
    folders = json.loads((root / "config/logo_check.json").read_text(encoding="utf-8"))["folders"]
    if selection is not None:
        if selection not in folders:
            raise ValueError(f"Folder is outside configured logo validation scope: {selection}")
        folders = [selection]
    problems = []
    for folder in folders:
        for path in sorted((root / folder).glob("*.png")):
            reasons = []
            try:
                with Image.open(path, formats=["PNG"]) as image:
                    rgba = image.convert("RGBA")
                if max(rgba.size) > MAX_SIDE:
                    reasons.append(f"{rgba.width}x{rgba.height} exceeds {MAX_SIDE}px")
                if trimmed(rgba) is not None:
                    reasons.append("transparent margins exceed trim tolerance")
            except (OSError, ValueError, Image.DecompressionBombError) as error:
                reasons.append(f"invalid PNG: {error}")
            if reasons:
                problems.append(f"{path.relative_to(root).as_posix()}: {', '.join(reasons)}")
    return problems


def main(selection=None):
    try:
        problems = validate(ROOT, selection)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    print("Logo validation passed")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit("Usage: python scripts/logo_trim.py [configured folder]")
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
