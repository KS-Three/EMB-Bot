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

## Sharded era — measured rows (appended 2026-10-28)

Since PR #669 `digitizer` is an aggregator over six `digitizer shard k/6`
jobs. The wall time tracked here is the aggregator's `completedAt` minus the
earliest shard's `startedAt`, from `/actions/runs/<id>/jobs`; every other
column is that job's own `completedAt` minus `startedAt`. Minutes, one
decimal. Rows are the six most recent green runs on `main` at the time of
writing, oldest first. (`bench-digitize` and `art-fidelity-baseline` are
push-to-`main`-only and gate nothing; listed for completeness.)

| Run started (UTC) | Run id | PR | SHA | digitizer wall | shard 1 | shard 2 | shard 3 | shard 4 | shard 5 | shard 6 | slowest | engine | studio | studio-e2e | bench-digitize | art-fidelity-baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-27 20:36 | 40579521969 | #1156 | `1c69607d` | **23.9** | 20.4 | 15.5 | 10.6 | 14.2 | 23.7 | 20.6 | 5/6 | 1.4 | 1.3 | 9.5 | 6.3 | 6.1 |
| 2026-10-27 21:16 | 40585402187 | #1157 | `9d097c1d` | **21.8** | 10.3 | 21.6 | 17.0 | 13.7 | 15.5 | 10.1 | 2/6 | 1.5 | 1.0 | 9.6 | 5.6 | 8.8 |
| 2026-10-27 23:42 | 40603927339 | #1160 | `0c80707b` | **20.0** | 13.2 | 19.8 | 8.8 | 10.9 | 16.0 | 16.9 | 2/6 | 1.1 | 1.2 | 10.4 | 3.9 | 7.5 |
| 2026-10-28 00:26 | 40608782766 | #1161 | `7326052a` | **20.9** | 19.4 | 20.7 | 17.5 | 16.4 | 11.9 | 17.3 | 2/6 | 1.2 | 0.9 | 11.6 | 6.7 | 7.7 |
| 2026-10-28 01:09 | 40613312773 | #1158 | `1ce2af22` | **19.9** | 14.2 | 19.7 | 16.1 | 10.0 | 15.1 | 14.2 | 2/6 | 1.5 | 1.4 | 11.6 | 5.0 | 8.2 |
| 2026-10-28 01:16 | 40614037007 | #1159 | `616fdaf3` | **20.2** | 18.8 | 20.0 | 13.5 | 17.6 | 15.1 | 13.6 | 2/6 | 1.2 | 1.1 | 16.3 | 6.1 | 8.0 |

Across these six runs the sharded `digitizer` wall time has a p50 of
**20.5 minutes** (range 19.9–23.9) and the slowest shard a p50 of **20.4**
(range 19.7–23.7), against a fastest shard of 8.8–11.9 in every run — so the
first sharded run's 24.1 is now the top of the band, and footgun 7's
"budget twenty-five, read fifteen as normal" still holds. The slowest shard
was **2/6 in five of the six runs** (5/6 in the first), which is the
stale-durations signal footgun 7 names: the split in
`digitizer/tests/.shard_durations.json` no longer matches where the test
minutes are, and refreshing it is the fix, not adding shards.
