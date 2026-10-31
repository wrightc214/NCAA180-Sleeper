# App + push notifications

Design and decisions: project doc `todo-pwa.md`. This page = how it works in the repo + setup.

## Pieces
| Piece | Where | What it does |
|---|---|---|
| Install + offline | `reports/manifest.webmanifest`, `reports/sw.js`, `reports/assets/icons/` | Makes the site installable; caches pages (network first) and logos |
| First-run prompt | `reports/assets/app.js` (every page, via `site_common.page_head` / the weekly template) | Full-screen "Set up" sheet while a phone has no follows or notifications off; "Not now" hides it for the visit |
| Setup page | `reports/app.html` (built by `scripts/app_page.py`) | Pick teams / leagues / events, turn notifications on, stop them; `?test=1` = tester phone |
| Picker lists | `reports/data/push-teams.json` (`scripts/push_teams.py`) | Team keys = `ncaa180|<league short>:<roster ID>` (identity = slot) |
| Push store | `worker/` (Cloudflare Worker + D1) | Anonymous subscriptions + follows. Never sends |
| Sender | `scripts/notify.py`, `scripts/postseason_announce.py` | Weekly job: one push per device per announcement, own teams first, then playoff → bowl → NIT; ledger `data/push/Announced_Season.csv` stops repeats |
| Test sends | workflow **Push test** (`scripts/push_test.py`) | Tester phones only |
| Settings | `config/push.json` | Worker URL, public key, events, prestige order, which events also post to Discord (none yet) |

Rules baked in: LM-only content never goes to push; national champion + Stagg Bowl go to every phone that follows a team; title games are sent once (champion push), not twice.

## One-time setup
Secrets/variables live in GitHub → repo **Settings → Secrets and variables → Actions**.

1. **Cloudflare account** (free).
2. **D1 database** named `ncaa180-push` (Cloudflare dashboard, D1 section) → copy its **database ID**.
3. **Account ID** (shown in the Cloudflare dashboard) and an **API token** with permission to edit Workers and D1 (Cloudflare's "Edit Cloudflare Workers" token template, plus D1 Edit).
4. **GitHub secrets:** `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `PUSH_ADMIN_TOKEN`, `VAPID_PRIVATE_KEY`. **Variable:** `D1_DATABASE_ID`.
5. Run workflow **Push store (Cloudflare Worker)**. Its log shows the Worker address (`https://ncaa180-push.<your-subdomain>.workers.dev`). If Cloudflare asks for a workers.dev subdomain first, pick one in the dashboard and re-run.
6. Put that address in `config/push.json` → `worker_url` (no trailing slash) and commit to main.
7. Phone test: open `.../reports/app.html?test=1`, install the app, open it from the home screen, pick a team, **Turn on notifications**. Then run workflow **Push test** (optional `as_week` = `2025-14` for a realistic personalized sample).

## Keys
- VAPID key pair: public half in `config/push.json`; private half only in the `VAPID_PRIVATE_KEY` secret. Changing it means every phone must turn notifications on again.
- `PUSH_ADMIN_TOKEN`: shared by the Worker (set by the deploy workflow) and the sender.
