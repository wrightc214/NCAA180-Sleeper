"""Scheduled gate behavior from the regular-season finale onward."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import week_gate


@pytest.mark.parametrize(
    "active_week, behind, missing, expected",
    [
        (11, ["SEC"], ["ACC"], True),
        (12, ["SEC"], [], False),
        (12, [], ["ACC"], False),
        (12, [], [], True),
        (13, ["SEC"], [], False),
        (17, [], ["ACC"], False),
    ],
)
def test_scheduled_finale_and_postseason_wait_for_every_league(
    monkeypatch, active_week, behind, missing, expected,
):
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setattr(sys, "argv", ["week_gate.py", "check"])
    monkeypatch.setattr(week_gate, "state", lambda: ("2026", active_week, "regular"))
    monkeypatch.setattr(week_gate, "last", lambda: ("2026", active_week - 1))
    monkeypatch.setattr(week_gate, "past_deadline", lambda: True)
    monkeypatch.setattr(week_gate.lcfg, "last_regular_week", lambda: 11)
    monkeypatch.setattr(week_gate, "not_ready", lambda season, done: (behind, missing))
    monkeypatch.setattr(week_gate, "out", lambda run, why: run)

    assert week_gate.main() is expected


@pytest.mark.parametrize(
    "held, expired, fail, expected_alerts",
    [(True, True, False, 1), (True, False, False, 0),
     (False, True, False, 0), (True, True, True, 1)],
)
def test_strict_hold_alert_is_reserved_once_without_changing_gate(
    monkeypatch, tmp_path, capsys, held, expired, fail, expected_alerts,
):
    output = tmp_path / "gate-output"
    webhook = "https://discord.com/api/webhooks/123/dummy"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    monkeypatch.setenv("DISCORD_WEBHOOK_LM_PRIVATE_DATA", webhook)
    monkeypatch.setenv("DISCORD_CONTACT_ID", "456")
    monkeypatch.setattr(sys, "argv", ["week_gate.py", "check"])
    monkeypatch.setattr(week_gate, "state", lambda: ("2026", 12, "regular"))
    monkeypatch.setattr(week_gate, "last", lambda: ("2026", 11))
    monkeypatch.setattr(week_gate, "past_deadline", lambda: expired)
    monkeypatch.setattr(week_gate.lcfg, "last_regular_week", lambda: 11)
    waiting = (["SEC (scored through wk 10)"], ["ACC"]) if held else ([], [])
    monkeypatch.setattr(week_gate, "not_ready", lambda *_: waiting)
    ref = "refs/tags/automation/strict-week-gate/2026/11"
    reserved = False
    posts = []

    def git(command, **kwargs):
        nonlocal reserved
        if command[1] == "ls-remote":
            assert command[-1] == ref
            return SimpleNamespace(returncode=0 if reserved else 2)
        assert command == ["git", "push", "origin", f"HEAD:{ref}"]
        assert not reserved
        reserved = True

    def post(url, **kwargs):
        assert url == webhook
        assert reserved
        posts.append(kwargs["json"])
        if fail:
            raise week_gate.requests.ConnectionError(webhook)
        return SimpleNamespace(status_code=204)

    monkeypatch.setattr(week_gate.subprocess, "run", git)
    monkeypatch.setattr(week_gate.requests, "post", post)
    week_gate.main()
    week_gate.main()
    expected_run = "false" if held else "true"
    assert output.read_text().splitlines() == [f"run={expected_run}"] * 2
    assert len(posts) == expected_alerts
    if posts:
        assert posts[0]["allowed_mentions"] == {"parse": [], "users": ["456"]}
        for text in ("<@456>", "2026 Week 11", "SEC (scored through wk 10)",
                     "ACC (missing last_scored_leg)", 'manual "Weekly League Update" run bypasses'):
            assert text in posts[0]["content"]
    logs = capsys.readouterr().out
    if fail:
        assert "Strict week gate alert failed" in logs
        assert webhook not in logs
