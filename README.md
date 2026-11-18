# NCAA180-Sleeper
League Data for NCAA 180

Attempting to create a public dashboard for NCAA 180 that doesn't require user logins.  Data should be as close to real time as possible.

link to site: http://ncaa180.short.gy/home

## Accessibility 5.8 — development review (PR #109)

Accessibility 5.8 is being developed on `feature/accessibility-5-8`. **It is not released, validated, or approved for merge.** The proposed settings page is `reports/access.html` (developer-only navigation), and device-local preferences are stored at `localStorage["ncaa180.access"]`.

**Reviewer / developer starting point:** [Accessibility 5.8 independent review handoff](docs/accessibility-5-8-review.md). That document contains the complete current implementation inventory, acceptance criteria, exact safe test commands, confirmed vs. unconfirmed test results, known gaps, and no-merge guardrails. The test suite has passed an emulated JavaScript harness (18/18); native Node/CI/browser testing is **not yet confirmed**.

Do not deploy, merge PR #109, or change `main` as part of review. Generate checked-in assets from their sources and inspect diffs before committing.
