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
