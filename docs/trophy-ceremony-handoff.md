# Awards trophy ceremonies

Run `python scripts/trophy_ceremony.py`, then `python scripts/menu_build.py`. This rebuilds the archive and the Awards season and week rows without contacting Discord. The weekly workflow does both after processing trophies. The first run writes the generated pages and manifest.

- Check an existing weekly report, the 2025 CCG ceremony, the 2022 Week 18 Dwight Fight award, and a Year-End Awards entry when there are undated bowls. A season with no Year-End Awards content has no entry.
- On the first post-CCG run, verify that CCG is immediately after the regular-season weeks and that each finalized winner appears once. At a phone width, test the two-column case and Save Image.
- Run `python -m pytest -q tests/test_trophy_ceremony.py tests/test_trophies.py`. For a Discord integration test, set DISCORD_WEBHOOK_AWARDS to a test channel webhook, then run the builder and `python scripts/trophy_ceremony.py --post` with current-season test results. Repeat with identical inputs and with a late winner. Expect one initial message and one edit. History builds never announce archived seasons.
- Production uses DISCORD_WEBHOOK_TEAM_STATS when DISCORD_WEBHOOK_AWARDS is unset. The latter can point to a dedicated Awards channel later. The public website link may take a Pages deployment to catch up with the Discord announcement.
- Trophy ledgers retain their existing columns. The ceremony builder gets the week from source results and matches it against accepted ledger rows.
