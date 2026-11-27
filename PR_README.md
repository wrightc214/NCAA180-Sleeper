# Team page trophy case

The Team page generator embeds the display weights from Legend Score. The browser ranks the existing trophy array, including data generated before this change. National titles lead, followed by the incremental Legend Score weight of each achievement. A playoff bowl victory uses the weight for advancing to the next round. Ties use newest season and then event name. Unscored trophies follow in reverse chronological order.

The sorter already recognizes optional `dwight_fight` and `guillotine` keys under `managers.legend_points`. Adding points to the All-Time Managers calculation is separate.

Mobile and section exports use two trophies per shelf. National titles have a shelf of their own. Desktop can show four regular trophies per shelf, and a short final row is centered.

## Reviewer checks

- Run `python -m pytest -q tests/test_team_pages.py` and `RUN_SCOREBOARD_BROWSER_TESTS=1 python -m pytest -q tests/test_team_pages_browser.py`.
- On Arizona State, verify National Championship, Rose Bowl, Cotton Bowl, Tangerine Bowl, Holiday Bowl, and then Dwight Fight titles.
- Save the full case and an individual trophy at a phone width. Check the order, labels, and trophy art in the PNG.
