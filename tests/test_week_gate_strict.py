"""Scheduled gate behavior from the regular-season finale onward."""
from pathlib import Path
import sys

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
