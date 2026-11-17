"""logo_trim: masters survive Pillow resampling noise; real replacements retire the old master."""
import os
import sys

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import logo_trim as L  # noqa: E402


def logo(size, color=(200, 30, 30, 255), text_box=None):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w, h = size
    d.ellipse((w * 0.1, h * 0.1, w * 0.9, h * 0.9), fill=color)
    if text_box:
        d.rectangle([int(v * w) if i % 2 == 0 else int(v * h) for i, v in enumerate(text_box)],
                    fill=(255, 255, 255, 255))
    return im


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("assets/logos/Bowls")
    return tmp_path


def run():
    L.main(["assets/logos/Bowls"])


WEB = "assets/logos/Bowls/Test Bowl.png"
SRC = "assets/logos/source/Bowls/Test Bowl.png"
RETIRED = "assets/logos/source/Bowls/retired"


def test_big_upload_keeps_master(repo):
    logo((2000, 1800)).save(WEB)
    run()
    assert Image.open(SRC).size == (2000, 1800)
    assert max(Image.open(WEB).size) == 512


def test_resampling_noise_keeps_master(repo):
    """Another Pillow version's web copy (a few levels off) must not read as a new upload."""
    logo((2000, 1800)).save(WEB)
    run()
    web = Image.open(WEB).convert("RGBA")
    px = web.load()
    for x in range(0, web.width, 3):  # nudge many pixels by a couple of levels
        for y in range(0, web.height, 3):
            r, g, b, a = px[x, y]
            px[x, y] = (min(r + 2, 255), g, b, a)
    web.save(WEB)
    before = open(WEB, "rb").read()
    run()
    assert os.path.exists(SRC)
    assert not os.path.exists(RETIRED)
    assert open(WEB, "rb").read() == before  # left alone, not rewritten


def test_small_replacement_retires_master(repo):
    logo((2000, 1800)).save(WEB)
    run()
    new = logo((400, 360), color=(20, 40, 160, 255))
    new.save(WEB)
    run()
    assert not os.path.exists(SRC)
    retired = os.listdir(RETIRED)
    assert len(retired) == 1 and Image.open(os.path.join(RETIRED, retired[0])).size == (2000, 1800)
    assert Image.open(WEB).convert("RGBA").getpixel((200, 180))[2] > 100  # new logo kept


def test_big_replacement_replaces_and_retires(repo):
    logo((2000, 1800)).save(WEB)
    run()
    logo((1600, 1600), color=(20, 40, 160, 255)).save(WEB)
    run()
    assert Image.open(SRC).size == (1600, 1600)
    assert len(os.listdir(RETIRED)) == 1


def test_small_edit_counts_as_new(repo):
    """Removing a small block of text (e.g. sponsor lettering) is a real change, not noise."""
    logo((2000, 1800), text_box=(0.35, 0.7, 0.65, 0.78)).save(WEB)
    run()
    edited = logo((2000, 1800))
    edited.save(WEB)
    run()
    assert len(os.listdir(RETIRED)) == 1
    assert Image.open(SRC).size == (2000, 1800)
