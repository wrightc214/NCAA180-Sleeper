# Selection Watch operations

## Before each conference championship week

- Update the dated Thanksgiving, Black Friday and late-final retry cron overrides at the top of `.github/workflows/live-refresh.yml`. These GitHub Actions schedules are in UTC and cannot be read from config.
- Update the Eastern checkpoint windows in `config/selection_watch.json` in the same PR. Keep the UTC offsets explicit and confirm at least one scheduled run falls after each window's games can reasonably finish, with time for retries.
- Verify the weekly run published the real Selection Watch board and Week 12 Games baseline. Do not use the provisional board or illustrative archive fixture as recorder inputs.

In 2026 the first Thu/Fri window opens **Fri Nov 27 at 11 p.m. ET**. A point becomes eligible only after the Games feeds verify completion of that window. Check the live-refresh run and the season's `selection-watch-timeline-YYYY.json`.

## If publication fails

The job fetches and rebases and retries the push once. A second rejection or an unrelated rebase conflict fails the job. If the recorder captured a point, download the **selection-watch-checkpoint-recovery** artifact from that run. It contains the year, checkpoint ID and original point.

After checking the season and checkpoint, restore the artifact's unchanged point through a reviewable patch to `reports/postseason/selection-watch-timeline-YYYY.json`, **only if that checkpoint is still absent**. Never overwrite the first published point or record later odds as if they were captured in the missed window. Without a verified original artifact, leave the checkpoint unrecorded.

Discord image drafts are available only in Dev view. Generating an image never posts to Discord.

### Steal Board v2

The Selection Watch publisher stores the `play_ins` game IDs in its season JSON. It classifies
them from every CCG outcome with all games open, including paths where an at-large tie awards a
fractional spot. A subsequent publication with the same season and pairings retains the stored
IDs. Live scores and What-if change the displayed result, not the tag. A play-in uses one spot at
the starting cut but never counts as a steal.

A non-play-in CCG win outside the natural field is a steal. A natural-field team that would be
displaced by the other steals can save its spot by winning its own CCG. The board skips that
team's held row when pairing the thieves with the teams they displace. The order switch reverses
both columns together and leaves those pairings intact.

After changing archive inputs or the page shell, run these commands from the repository root:

```sh
python3 scripts/selection_watch_history.py
python3 scripts/selection_watch_page.py
python3 scripts/menu_build.py
git diff --exit-code -- reports/assets/menu.js
```

## Archive field exceptions

A past season's board is only drawn when the rules reproduce the real playoff field exactly. If the real field differed because of an admin error, list the swap in `config/selection_watch.json` under `field_exceptions`, keyed by season: `in` played in the field, `out` qualified by rule but was left out, `note` is shown under the board. Then rerun `python3 scripts/selection_watch_history.py`.

- The board stays by rule. Both teams are marked ‡ (the † mark is already used for standard-scoring differences), and the `in` team is marked ‡ in the final field list.
- A stale entry (wrong team, reversed, or no longer needed) stops the history build with an error instead of hiding or faking a board.
- To drop an exception, or in a fresh template, delete the entry or the whole block. That season then shows no board.
- Current entry: 2022, Central Michigan in for Texas Tech (bracket entry error).
