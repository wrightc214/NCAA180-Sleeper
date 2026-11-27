# 5.20a Team page changes

Owner approves and merges; reviewer runs tests and regenerates artifacts. Keep hidden-dev.

Changed team_pages.py and team.js for annual equal-team efficiency, complete Max PF coverage, patterned charts, totals, manager appearances and unknown/orphan distinction. Shared snapshot.js and sections.js retain the existing exporter, add download fallback and visible errors. Color customization excluded.

Reviewer: run existing tests, python -m unittest discover -s tests -p test_team_pages_520a.py, and node --check on changed JS. Regenerate team artifacts. Verify annual benchmark against official PF and Max PF, missing/zero denominators, ties, historical managers, orphan detection, appearances, hidden H2H rows and placement-only games. Check all footers against underlying data. Test charts, marker-only polls, crosshair, legends and header controls at 320/390/1280px in light/dark and existing color modes. Save every enabled section/card on desktop and mobile; inspect PNG, logos, timestamps, colors, table clipping and shared exporter on other pages. Verify hidden-dev remains.

Limitations: tests not run as instructed. Static regression checks do not replace behavioral tests. Export root cause not confirmed in browser; asynchronous share activation and tooltip-only errors are suspected. Capture timestamp is not source refresh time. Verify roster OwnerID schema and official PF missing-data handling. Existing data-nosnap exclusions retained. Generated artifacts not committed. No totals for individual poll charts or non-tabular lists.
