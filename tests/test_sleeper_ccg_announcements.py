"""Regression coverage for confirmed and uncertain Sleeper sends."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sleeper_ccg_announcements as announcements


@pytest.mark.parametrize("confirmed", [True, False])
def test_weekly_and_manual_sends_share_delivery_state(tmp_path, monkeypatch, confirmed, capsys):
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

    monkeypatch.setattr(announcements, "conference_league_ids", lambda year: {"ACC": league_id})
    if confirmed:
        announcements.publish_final_ccgs("2026", "ACC", tmp_path, "test-token")
        assert "already sent (Sleeper message 5678)" in capsys.readouterr().out
    else:
        with pytest.raises(SystemExit, match="prior delivery needs reconciliation"):
            announcements.publish_final_ccgs("2026", "ACC", tmp_path, "test-token")
    assert calls == [(league_id, caption)]
    expected = {"status": "sent" if confirmed else "pending", "caption": caption}
    if confirmed:
        expected["message_id"] = "5678"
    assert json.loads(records_path.read_text(encoding="utf-8")) == {key: expected}


def test_manual_send_requires_verified_final_award(tmp_path, monkeypatch):
    monkeypatch.setattr(announcements, "POSTS", tmp_path / "posts.json")
    monkeypatch.setattr(announcements, "conference_league_ids", lambda year: {"ACC": "1234"})
    monkeypatch.setattr(announcements, "previews", lambda *args, **kwargs: [])
    with pytest.raises(SystemExit, match=r"^No verified final award to send\.$"):
        announcements.publish_final_ccgs("2026", "ACC", tmp_path, "test-token")


@pytest.mark.parametrize("fail_push", [1, 2], ids=["reserve", "confirm"])
def test_push_failure_stops_further_sends(tmp_path, monkeypatch, capsys, fail_push):
    monkeypatch.setattr(announcements, "POSTS", tmp_path / "posts.json")
    monkeypatch.setattr(announcements, "previews", lambda *args, **kwargs: [
        ("1234", tmp_path / "acc.png", "ACC"),
        ("6789", tmp_path / "sec.png", "SEC"),
    ])
    posted = []
    pushes = 0

    def git(command, *, check):
        nonlocal pushes
        if command[1] == "push":
            pushes += 1
            if pushes == fail_push:
                raise subprocess.CalledProcessError(1, command)

    def send(year, league, image, text, *, token, before_post):
        before_post()
        posted.append(league)
        return "5678"

    monkeypatch.setattr(announcements.subprocess, "run", git)
    monkeypatch.setattr(announcements, "send", send)
    with pytest.raises(SystemExit, match="need review"):
        announcements.publish_final_ccgs("2026", "", tmp_path, "test-token")
    assert posted == ([] if fail_push == 1 else ["1234"])
    assert pushes == fail_push
    assert "Stopping further sends" in capsys.readouterr().out
