# 5.20a Team page review

The Team page remains hidden-dev. Shared Save Image changes are in #152. The owner handles merging.

The generated HTML is committed and tested against the template. Run `python scripts/team_pages.py` to refresh `data/teams` before approving or publishing. The generated JSON adds the annual benchmark, official PF coverage and manager appearances, and recalculates Max PF coverage. Efficiency uses completed regular-season result rows and includes genuine zero PF. A team with incomplete official PF or a missing or unusable Max PF denominator is excluded. Existing standings retain their PF fields.

Charts and game-table snapshots use the existing section exporter. Expand the desired season and chart table before saving. Transactions retain their existing export exclusion. Weekly poll rank tables have no total because ranks cannot be added. Draft and roster lists are not aggregate statistics. The timestamp records the page capture session and does not represent the source refresh time.

Run `python -m unittest discover -s tests -p 'test_team_pages*.py'` from the root. Use `RUN_SCOREBOARD_BROWSER_TESTS=1` for the browser suite. Verify the same annual benchmark across teams, aggregate rates, hidden H2H rows, placement rows, and orphan versus missing historical ownership. Verify chart patterns and footer readability on light and dark themes at 320, 390 and 1280 px. Check that Save Image and collapse act independently.

Verify actual PNGs with #152 applied locally. The reported no-action failure remains unconfirmed on the owner's device. This branch surfaces Team exporter initialization errors and exposes the season section to the shared exporter. Inspect chart patterns, table totals, colors, logos, labels and table clipping in the saved images.
