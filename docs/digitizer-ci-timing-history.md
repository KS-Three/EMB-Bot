# `digitizer` CI job timing — pre-sharding history

Moved from the root `CLAUDE.md` footgun 7 (2026-10-26). Historical only: the job
has been sharded since PR #669 (2026-10-08) and these budgets no longer apply.
Kept for the lesson — every budget went stale in one direction.

**`digitizer` runs 33 to 55 minutes** — re-measured 2026-09-12 over the
last 36 successful jobs: min **32.7**, p50 **49.7**, p90 54.6, max 55.4,
with daily medians 48.6 (09-11) and 50.6 (09-12). **Budget an hour, and
 read a 50-minute job as normal rather than stuck.** **Re-measured
 2026-09-29 on PR #562: 1h 02m 50s — above the 09-12 range; the drift the
 paragraph below predicts is happening.**
**Re-measured 2026-09-30: 65.2 minutes on PR #563, green** — the last
five successful jobs read 33.3 / 45.0 / 54.0 / 58.4 / 65.2, so the top
has moved past the hour the line above budgets. Budget seventy, read an
hour as normal, and spend the one `curl` on `/actions/runs/<id>/jobs`
before calling anything stuck: that job's test step was live the whole
time. **And 66.2 on PR #567 the same night, green** — a tree that took
four merges of `main` inside one PR; the record moves a minute at a
time now, so seventy is the budget until a job passes it.
**One did — 75.9 minutes (1h 15m 56s) on PR #575, 2026-09-30, green**,
on a diff that touched only `.claude/skills/`, so the job's length is the
suite's, not the change's. **Budget eighty**, read seventy-five as normal,
and still spend the `curl` before calling anything stuck.
**Passed by three seconds — 76.0 minutes (1h 15m 59s) on PR #631,
2026-10-04, green**, on a one-line `CLAUDE.md` change. It was not alone:
the eight successful jobs that followed it that evening read 40.0 / 53.9 /
42.1 / 51.7 / 57.6 / 71.8 / 75.5 / 53.4 in start order (job start and
completion stamps from `/actions/runs/<id>/jobs`), so three of nine sat
above seventy and the top is a band now, not one outlier. Eighty still
holds; read anything under it as normal, and the `curl` still comes
before any verdict. (A fifth job,
`art-fidelity-baseline`, is push-to-`main`-only and `continue-on-error` — it
never appears on a PR and gates nothing.)

This line keeps going stale in one direction, so read the trend rather
than the number: "12–18" (medians 15.0–15.2, 2026-08-27/28) → "10 to 42"
(220 jobs, 2026-09-06, after the daily median walked 15.0 → 16.5 → 17.6 →
18.7 → 20.7 → **29.6**, max 41.8) → this. Every revision was TRUE WHEN
WRITTEN. **The 09-06 text is what makes this worth re-measuring rather
than nudging:** it said budget half an hour and read 35 minutes as normal,
and half an hour is now BELOW the fastest job on record — so a session
trusting it reads a perfectly healthy run as hung and goes looking for a
failure that is not there. That nearly happened on PR #469, whose
`digitizer` job took **53m 59s** and went green. If you are reading this
after 2026-09-12, assume it has drifted again and spend one `curl` on
`/actions/runs/<id>/jobs` before concluding anything about a long job.
