# Is a second digitize slower? (2026-11-13)

**Question.** The 2026-11-12 build walkthrough (`docs/build-walkthrough-2026-11-12.md`, "What did not work" item 5) timed one artwork at 12–15 s, then 44 s "right after a Cancel", on a laptop running two other digitize jobs.

**Answer: no. The 44 s is machine contention.** A second run and a run after Cancel took 0.55–1.26× the first run's time in every repetition. The same cold digitize swung 2.9× in wall time within 15 minutes as other processes' load changed (19.1 s → 54.8 s), and the walkthrough's 12–15 → 44 s is 2.9–3.7×. One smaller real defect was found and fixed: Cancel did not always free the worker in 1–2 s. It held the worker for up to 5.5 s, and the next run queued behind it for up to 3.4 s.

## How it was measured

`digitizer/tools/second_digitize_timing.py` starts its own service (port 8799) with `digitizer_core.deadline.check` wrapped. The wrapper logs each stage seam with wall time and the worker thread's CPU time, plus the start and end of every job's work; nothing in the pipeline changes. The client runs one repetition as:

- **A**: digitize (cold).
- **A'**: the identical request again.
- **B**: digitize again, cold. Same pixels, new bytes: a PNG text chunk changes the sha256 the caches key on.
- **X**: digitize, then Cancel at 40% of A.
- **C**: the cancelled request resubmitted at once, as the Studio does.
- **Xe / Ce**: the same, with Cancel at 12% of A, inside stage 4, then a 3 s idle check before Ce.
- **R**: digitize with a `/recount` of other bytes in flight.
- **K2**: digitize while two other processes run the same full digitize.

Machine-wide CPU comes from `typeperf`, sampled once a second over each run. "others" means that figure minus the probe's own process CPU. `tools/second_digitize_report.py` builds the tables. Art: `testdata/becker_marine_logo.png` at 96 mm (one warm-up run first). Raw JSONL is in the session scratchpad, not committed.

**What else was running.** There was no quiet window all afternoon. Other load (excluding the probe) ranged from 0.8 to 7.6 cores of 8:

- walkthrough-2's service on 8721 (about 1 core during its runs)
- a census service on 8791
- a pytest-xdist run with 7 execnet workers from 17:00 on
- Claude/node processes

Each row below carries the load measured during that run. On the same code, run CPU grew from about 21 s to about 47 s as the box got busier: hyperthread siblings and the thermal state, not the code. An interleaved A/B of origin/main's engine against this branch's in one window gave 46.5–48.1 s against 46.9–48.6 s of CPU, with identical stitch output (14,739 points each).

## Timings, before the fix (6 repetitions, 16:30–16:57)

Wall seconds of the job's own work. Queue = submit to start. "others" = cores busy outside the probe during the run (runs 1–3 predate the sampler).

| rep | A | B | B/A | X freed after Cancel | C queue | C | C/A | others (A, B, C) |
|---|---|---|---|---|---|---|---|---|
| 1 | 41.5 | 36.1 | 0.87 | 0.01 | 0.00 | 24.1 | 0.58 | — |
| 2 | 42.7 | 34.5 | 0.81 | 0.00 | 0.00 | 24.1 | 0.56 | — |
| 3 | 32.9 | 26.9 | 0.82 | 2.72 | 2.66 | 41.3 | 1.26 | — |
| 4 | 24.1 | 19.1 | 0.79 | 1.36 | 1.30 | 13.4 | 0.55 | 3.3, 1.4, 1.3 |
| 5 | 22.8 | 24.8 | 1.09 | 3.48 | 3.42 | 23.4 | 1.03 | 3.8, 3.9, 5.8 |
| 6 | 49.9 | 54.8 | 1.10 | 2.92 | 2.86 | 31.9 | 0.64 | 6.8, 7.3, 7.0 |

The other measurements in the same runs:

- **A'**, the identical request, returned in 0.17–0.44 s (job cache).
- **Cancel inside stage 4 (Xe)** freed the worker 2.58, 4.08 and 5.45 s after Cancel returned. The 3 s idle check then still saw the cancelled job in flight twice in three runs, with the probe burning 0.5–0.8 cores. Ce queued 0.0, 1.0 and 2.3 s, then ran at A's speed: no generation was cached.
- **R**, with a concurrent `/recount`: 37.2, 41.3 and 49.5 s against A's 41.5, 42.7 and 32.9 s. That is 0.90×, 0.97× and 1.51×; the 1.51× run had heavy other load.
- **K2**, two deliberate extra digitizes: 30.8 s at 6.2 other cores (1.28× that rep's A), and 54.5 s and 82.7 s at 7.3–7.6 other cores.

## The candidate causes, one by one

| Cause | Measured | Verdict |
|---|---|---|
| Machine contention | The same cold run was 19.1 s at 1.4 other cores and 54.8 s at 7.3; K2 at 7.6 other cores was 82.7 s. Run CPU stays flat while wall time grows. | **The cause.** The walkthrough's 3× sits inside the swing measured here. |
| Cache cold or invalidated on the second run | A' was a 0.2–0.4 s cache hit. C after a stage-7 cancel was a generation-cache hit at 0.55–0.64× A. Ce after a stage-4 cancel was a miss, at A's speed. | Not a slowdown. A run after Cancel is the same speed or faster. |
| `/recount` overlapping the run | R/A was 0.90–0.97 at normal load. The Studio pauses recount while a run is in flight, but aborting the fetch does not stop the server's stages 0–4. | Small: a recount still in flight on the server when Auto Digitize is pressed adds its stages 0–4 as contention. |
| `/classify` overlapping | Not measured. The Studio calls it on upload or a forced-class change, never during a run, and it costs 0.1–2.5 s. | Not a candidate for a 30 s gap. |
| Single worker: C waits behind the cancelled job | C queued 0–3.4 s; the worker ran 0–5.5 s past Cancel. | **Real but small; fixed below.** |

## The defect fixed: three stretches with no Cancel seam

Stack sampling, and a check recorder over a full Becker run, found the three longest stretches where `deadline.check` never ran:

1. **Stage 4, from thread revalidation to text clusters: 4.1–5.7 s quiet, 19.5 s loaded.**
   - `textcluster._neck_split`'s loop over the pieces a neck leaves (393 on Becker's ring border; 5 s).
   - `letterform_priors.plan_letterform_priors` (about 0.4 s per letter).
2. **Stage 7, around a keyline, twice per run: 1.8–5.3 s.** `stage6_border.keyline_runs` → `_satin_loop`'s exact cross per ring sample, and `_bury_walks`.

Seams now sit in those loops: "text cluster neck splits", "letterform priors" and "keyline". A check reads a clock and moves no number. `tests/test_cancel_seams_1113.py` pins five things:

- the guarded loops are reached
- no gap after stage 3 is over 0.35 of stage 4's stretch
- no gap in the plan is over 0.1 of the plan
- a Cancel raised at each new seam is taken there
- the generation and the plan are identical with a scope armed

That file is the failing test: four of its tests were red before the change. The longest gap left is 1.2 s (stage 4's vectorize, one call) and 1.0 s (the preflight's OCR render).

## After the fix (3 repetitions, 17:32–17:45, busier machine)

| rep | A | B | B/A | X freed | C queue | C | C/A | Xe freed | idle after Cancel | Ce/A | others (A, B, C) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 46.6 | 37.5 | 0.80 | 0.00 | 0.01 | 26.3 | 0.56 | 0.10 | 0.02 cores | 0.74 | 3.0, 3.1, 2.8 |
| 2 | 48.7 | 39.6 | 0.81 | 0.01 | 0.01 | 57.9 | 1.19 | 0.01 | 0.005 cores | 1.02 | 3.7, 3.1, 6.7 |
| 3 | 70.3 | 56.0 | 0.80 | 0.02 | 0.01 | 40.2 | 0.57 | 0.21 | 0.04 cores | 0.75 | 7.2, 6.1, 5.5 |

The worker is now free within 0.0–0.21 s of Cancel, against up to 5.5 s before, and C no longer queues. B and C stay within 1.5× of A in every repetition. This window was not quiet (3–7 other cores), and nobody could provide one this afternoon. Absolute times are about 2× the 16:30 runs for the same CPU reason the A/B shows.

## Follow-ups (not done here)

- **Contention under several jobs.** Several digitize jobs on one laptop slow each other two to four times, and only Kent can decide how jobs from different sessions share the box. The service already runs one job at a time.
- **`/recount` keeps running after the Studio aborts it** (stages 0–4, 5–7 s). A server-side cancel for it would remove the R overlap.
- **`_neck_split` cost.** It rebuffers every part once per leftover piece: 393 pieces × parts on Becker is 5 s of a 24 s job. Hoisting `g.buffer(1e-6)` out of the loop would change no number.
