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

## `studio-e2e` rows (appended 2026-10-28)

`studio-e2e` is one unsharded job. CLAUDE.md footgun 7 budgeted it at "about
three (p50 2.7)"; the sharded-era table above already shows it at 9.5 to 16.3
minutes on 2026-10-27/28. Re-measured **2026-10-28 over the last ten green
`CI` runs on `main`** (`gh run list --branch main --status success --limit 10`,
then `gh run view <id> --json jobs`): wall time is the job's own `completedAt`
minus `startedAt`, minutes to one decimal, oldest first.

| Run started (UTC) | Run id | PR | SHA | studio-e2e | m:ss |
|---|---|---|---|---|---|
| 2026-10-28 02:03 | 40618663158 | #1164 | `133bb9a0` | 14.0 | 14:02 |
| 2026-10-28 02:05 | 40618839004 | #1166 | `09cfbaea` | 15.2 | 15:13 |
| 2026-10-28 02:12 | 40619595024 | #1168 | `10655360` | 16.6 | 16:36 |
| 2026-10-28 02:56 | 40623854814 | #1169 | `136a1c8a` | 15.2 | 15:10 |
| 2026-10-28 03:08 | 40624939488 | #1170 | `bb9388fa` | 14.9 | 14:53 |
| 2026-10-28 04:00 | 40629835997 | #1165 | `5a3181dc` | 11.4 | 11:25 |
| 2026-10-28 06:32 | 40644482625 | #1171 | `8cc12f33` | 11.6 | 11:36 |
| 2026-10-28 14:30 | 40706659658 | #1172 | `a71fd5cd` | 16.5 | 16:32 |
| 2026-10-28 16:53 | 40730395193 | #1173 | `8724cd58` | 17.7 | 17:39 |
| 2026-10-28 16:56 | 40730854496 | #1174 | `dbd3c8da` | 18.1 | 18:03 |

p50 **15.2 minutes (15m11s)**, min 11.4, max **18.1**. Not every row is a full
sample of a quiet runner: several of these started minutes apart, and this
note does not separate contention from the suite growing, so it makes no
claim about the cause. The two fastest (11.4, 11.6) and the two slowest
(17.7, 18.1) are the span to read as normal. Same rule as the `digitizer`
rows: spend one `curl` on `/actions/runs/<id>/jobs` before calling a long
`studio-e2e` stuck.

## `studio-e2e` rows (appended 2026-11-06)

Re-measured 2026-11-06 over the last twelve green `CI` runs on `main`
(`gh run list --workflow python-package-conda.yml --branch main --event push`,
then `/actions/runs/<id>/jobs`), the same arithmetic as the 10-28 table,
oldest first. The Reshape, Add-hole and Move-shape e2e specs landed in between
(PRs #1237 to #1260); the serial, service-backed step runs 100 specs now.

| Run started (UTC) | Run id | PR | SHA | studio-e2e | m:ss |
|---|---|---|---|---|---|
| 2026-11-05 20:40 | 42105594081 | #1248 | `67319af2` | 19.2 | 19:15 |
| 2026-11-05 21:30 | 42113319819 | #1249 | `6e08d7ca` | 20.5 | 20:29 |
| 2026-11-05 21:34 | 42113845140 | #1250 | `284590b7` | 25.0 | 25:00 |
| 2026-11-05 21:45 | 42115485974 | #1251 | `2f7c543a` | 24.0 | 24:00 |
| 2026-11-05 22:24 | 42121276789 | #1253 | `07f57b96` | 20.9 | 20:53 |
| 2026-11-05 22:31 | 42122256046 | #1252 | `e9205673` | 17.7 | 17:41 |
| 2026-11-05 22:56 | 42125668730 | #1254 | `fb682ef9` | 25.2 | 25:15 |
| 2026-11-06 03:20 | 42155925222 | #1256 | `9660b28b` | 25.2 | 25:10 |
| 2026-11-06 04:24 | 42162301246 | #1255 | `7e27f9f6` | 20.4 | 20:22 |
| 2026-11-06 04:32 | 42163085294 | #1257 | `13c0eb85` | 19.6 | 19:39 |
| 2026-11-06 05:47 | 42170485946 | #1261 | `b331dcef` | 28.8 | 28:50 |
| 2026-11-06 05:53 | 42171039338 | #1258 | `9225955d` | 23.2 | 23:11 |

p50 **22.1 minutes**, min 17.7, max **28.8**; the 10-28 table read 15.2 / 11.4
/ 18.1. Same caveat as before: runs minutes apart share runners, so this does
not separate contention from the suite growing.

**The 40-minute `timeout-minutes` cancelled a green run.** PR #1260's run
42166746724 (job 127724888465, `a7dca9d2`) was cancelled at 40m0s with every
finished spec passing: 82 of the 100 serial specs done, none failed, (m9) and
(m10) among the passes. Its steps: Tesseract apt 3.6 min and "Install
Playwright system libraries" 9.1 min (the same commit's sibling run, PR #1259
`b4c2b3d4`, spent under half a minute on each and finished in 22.4), parallel
specs 3.2 min, serial specs 23.3 min at the cut (19.0 for all 100 on the
sibling). The job alone was re-run as attempt 2 of that run. The budget moved
to 60 in this PR: twice the slowest green in the table, about three times its
median, and the job's own comment now points here.

## `studio-e2e` apt rows (appended 2026-11-07)

The job's system packages (Tesseract, and the nine font packages
`playwright install-deps chromium` adds on ubuntu-26.04) now install from
`.deb` files held in `actions/cache` (PR #1291). Before it, the last 14 green
`main` runs (42287412040 to 42334498906) spent 0.17 to 0.38 minutes on the two
apt steps, except run 42294672308, which spent **14.27**: Tesseract 3.82 and
the Playwright font deps 10.45, both downloading at 35 to 40 kB/s while the
specs on the same runner ran at normal speed. Run 42166746724 (the one that
hit the old 40-minute budget) did the same for about 13. Job minutes on those
14 runs: min 20.5, p50 27.4, max 39.4.

| Run id | Branch | apt cache | apt step (min) | studio-e2e job (min) | Specs (parallel + serial) |
|---|---|---|---|---|---|
| 42336840714 | PR #1291 | miss (populated) | 0.22 | 30.5 | 143 + 100, 0 skipped |
| 42340021914 | PR #1291 | hit | 0.10 (6 s `dpkg -i`) + 1 s restore | 25.0 | 143 + 100, 0 skipped |

The hit run fetched nothing from the mirror: no `apt-get update`, no `Get:`
line, the same 15 packages unpacked from the cache, `tesseract 5.5.0` printed.
That 6 seconds is what every run now pays, so the 14-minute tail cannot recur
until the image build or Playwright version changes the key.

On a healthy mirror the step costs what it did before; the change only
removes the download from the slow tail, so read a single slow apt step after
this as a cache miss (an image or Playwright bump) before reading it as the
mirror.

## `studio-e2e` sharded rows (appended 2026-11-07)

Since this PR `studio-e2e` is an aggregator over two `studio-e2e shard k/2`
jobs, split by spec file in `app/playwright.config.js` (`E2E_SHARD`), the
same shape as `digitizer`. Wall time is measured the same way as the
`digitizer` rows above: the aggregator's `completedAt` minus the earlier
shard's `startedAt`.

**The baseline moved again before the split.** The last twelve green `main`
runs before it (42338094254 to 42344364123, all 2026-11-07, all cache hits on
the apt step) took min **20.4**, p50 **30.1**, max **31.1** minutes; the
11-06 table above read p50 22.1. Setup was 0.9 to 1.3 minutes on every one of
them. The rest was the two test steps: service-free 2.5 to 4.1, serial
digitizer-service 17.0 to 26.3, and `field-reshape-mode.spec.js` alone is
about half the serial step (614 of 1,238 summed test-seconds, median of three
of those runs).

**Prediction**, per run of those twelve: each shard pays the full setup plus
half the test time (the partition puts 708 cost-seconds on each side, a
service-free file counting a quarter because it shares four workers) plus
about 0.1 minutes for the `--list` and upload steps. That gives a shard p50 of
**15.6** (min 10.8, max 16.1), and `studio-e2e` about half a minute more for
the aggregator.

| Run id | Event | SHA | shard 1 | shard 2 | studio-e2e wall | predicted | tests (shard 1 + shard 2) |
|---|---|---|---|---|---|---|---|
| 42398725440 | PR #1303 (`engine` red: the checker lacked `--help`, fixed in the next commit; the e2e jobs are independent of it) | `8c44a9f9` | 13.3 | 10.5 | **13.5** | 15.6 p50; 12.2 at this run's own test speed | 94 + 149 = 243, each once (checker OK) |
| 42399967770 | PR #1303 (all checks green, merged on this run) | `795e72f7` | 15.2 | 11.9 | **16.2** | 15.6 p50; 13.9 at this run's own test speed | 94 + 149 = 243, each once (checker OK) |

"At this run's own test speed" re-scales the prediction to the runner drawn:
the four test steps summed to 21.9 minutes (1.2 + 11.0 parallel and serial on
shard 1, 1.9 + 7.8 on shard 2), so half of that plus 1.3 minutes of setup is
12.2 per shard. Shard 1, which holds `field-reshape-mode.spec.js`, ran 1.1
over that and shard 2 ran 1.7 under it: the 2.8-minute gap between them is the
balance error of a file-level split whose largest file is half the serial
step. That is under the 3-minute re-measure threshold in
`app/playwright.config.js`; if it holds above 3 over several runs, refresh
`SPEC_SECONDS`, or split that spec file.

Run 42399967770 (the second run): the four test steps summed to 25.1 minutes, so the own-speed prediction is 25.1 / 2 + 1.3 = 13.9 per shard. The serial step on shard 1 (`field-reshape-mode.spec.js`) ran 12.9 minutes against 8.8 on shard 2, a ratio of 1.47 (1.41 on run 1) where `SPEC_SECONDS` predicted 1.11, and the 3.3-minute shard gap crossed the 3-minute re-measure threshold in `app/playwright.config.js`. It leaned the same way on both runs, so the table under-counts that file; re-derive it from wall time with `node tools/e2e-spec-times.mjs <run-id>...`.


Run 42409970223 (PR #1323, `SPEC_SECONDS` re-derived by `tools/e2e-spec-times.mjs` over main runs 42406340687, 42407202584, 42407932826, 42408103660, all after the #1318 split): shard 1 ran 15.6 minutes (20:13:01 to 20:28:35), shard 2 ran 15.9 (to 20:28:54), a gap of 0.3 minutes against 3.3 on the second run before the split and 0.5 to 3.3 across the earlier runs. The table moved most on `field-reshape-mode` 159 to 201, `field-reshape-move` 262 to 218, `quality-report` 73 to 92; the predicted split is 12.28 / 12.29 minutes of test time (old table on the same listing: 11.80 / 11.80).
