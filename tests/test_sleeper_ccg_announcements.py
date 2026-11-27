"""Regression coverage for confirmed and uncertain Sleeper sends."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sleeper_ccg_announcements as announcements


@pytest.mark.parametrize("confirmed", [True, False])
def test_weekly_and_manual_sends_share_delivery_state(tmp_path, monkeypatch, confirmed):
    records_path = tmp_path / "posts.json"
    monkeypatch.setattr(announcements, "POSTS", records_path)
    league_id = "1234"
    key = f"2026/CCG/{league_id}"
    caption = "Congrats Clemson & @manager for winning the 2026 ACC conference championship game!"
    calls = []

    def previews(year, conference, out, *, ledger_path, already_recorded):
        if key in already_recorded:
            return []
        return [(league_id, tmp_path / "trophy.png", caption)]

    def save(records, message):
        records_path.write_text(json.dumps(records), encoding="utf-8")

    def send(year, league, image, text, *, token, before_post):
        before_post()
        assert json.loads(records_path.read_text(encoding="utf-8"))[key]["status"] == "pending"
        calls.append((league, text))
        if not confirmed:
            raise SystemExit("Delivery could not be confirmed")
        return "5678"

    monkeypatch.setattr(announcements, "previews", previews)
    monkeypatch.setattr(announcements, "save_post_state", save)
    monkeypatch.setattr(announcements, "send", send)

    if confirmed:
        announcements.publish_final_ccgs("2026", "", tmp_path, "test-token")
    else:
        with pytest.raises(SystemExit, match="need review"):
            announcements.publish_final_ccgs("2026", "", tmp_path, "test-token")

    announcements.publish_final_ccgs("2026", "ACC", tmp_path, "test-token")
    assert calls == [(league_id, caption)]
    expected = {"status": "sent" if confirmed else "pending", "caption": caption}
    if confirmed:
        expected["message_id"] = "5678"
    assert json.loads(records_path.read_text(encoding="utf-8")) == {key: expected}
