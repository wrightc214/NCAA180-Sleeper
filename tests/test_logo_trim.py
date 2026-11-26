"""Web validation and glow generation regressions."""
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import logo_glow
import logo_trim


def logo(root, relative, size, *, padded=False):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", size, (0, 0, 0, 0) if padded else "blue")
    if padded:
        ImageDraw.Draw(image).rectangle((40, 40, 59, 59), fill="blue")
    image.save(path)
    return path


def test_validation_scope_and_no_writes(tmp_path):
    config = tmp_path / "config/logo_check.json"
    config.parent.mkdir()
    config.write_bytes((ROOT / "config/logo_check.json").read_bytes())
    folders = json.loads(config.read_text())["folders"]
    assert len(folders) == 6
    oversized = logo(tmp_path, "assets/logos/teams/big.png", (513, 30))
    padded = logo(tmp_path, "assets/logos/Bowls/padded.png", (100, 100), padded=True)
    logo(tmp_path, "assets/logos/teams/alt-dark/good.png", (512, 20))
    for folder in ("Guillotine", "Dwight Fight", "Leagues", "Playoffs/Archive", "teams/glow-dark"):
        logo(tmp_path, f"assets/logos/{folder}/excluded.png", (800, 30))
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert logo_trim.validate(tmp_path) == [
        "assets/logos/teams/big.png: 513x30 exceeds 512px",
        "assets/logos/Bowls/padded.png: transparent margins exceed trim tolerance",
    ]
    assert logo_trim.validate(tmp_path, "assets/logos/teams/alt-dark") == []
    assert before == {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert not (tmp_path / "assets/logos/source").exists()
    assert oversized.is_file() and padded.is_file()


def test_glow_second_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(logo_glow.lcfg, "ROOT", tmp_path)
    source = logo(tmp_path, "assets/logos/teams/team.png", (50, 50))
    original = source.read_bytes()
    logo_glow.main()
    destination = tmp_path / logo_glow.OUT / source.name
    with Image.open(destination) as image:
        image.copy().save(destination, compress_level=0)
    before = destination.read_bytes(), destination.stat().st_mtime_ns
    logo_glow.main()
    assert before == (destination.read_bytes(), destination.stat().st_mtime_ns)
    assert source.read_bytes() == original
