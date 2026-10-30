---
name: service-timeout-cancel-2026-10-30
description: a digitize job past JOB_TIMEOUT_S now STOPS at the next stage seam (digitizer_core.deadline, ContextVar scope armed by the registry worker) instead of holding the one worker; the next upload waited 497.9 s behind a dead job before, 10.5 s after; no flag; stage 2's region former and the rembg/SAM2 subprocesses still run to their end
metadata:
  type: project
---

2026-10-30. Photo-style census item 6 (`docs/photo-style-census-2026-10-27.md`):
`jobs._expire_locked` marked a RUNNING job `TIMED_OUT` lazily when `/jobs/{id}`
was READ, but the single-worker ThreadPool kept computing it, so the customer's
next upload sat `queued` behind work whose answer the Studio had already thrown
away. Follows [[studio-wait-600-2026-10-26]] (the Studio now waits the full 600 s)
and [[stage7-scene-speed-2026-10-29]] (why a scene reaches the limit at all).

**Measured** (real service on port 8741, `night_skyline.jpg` at the Studio's 80 mm
left-chest request, job timeout set to 20 s, then `logo_whitebg.png` the moment the
first read `error`; Kent's loaded laptop): before, the fast job waited **497.9 s**
(the scene ran 518 s; `inflight` 2 until then). After, **10.5 s** -- the service log
reads "abandoned at stage 2, 10.7s past the deadline; worker freed". The Studio's
`error` text read the same before and after the worker stopped, both arms.

**Built (no flag).** `digitizer_core/deadline.py`: `scope(seconds)` arms a
thread-scoped deadline (ContextVar, the `fill_section_travel` pattern);
`check(stage)` raises `Abandoned` past it; inert without a scope. `JobRegistry.run`
arms it round `work()`, catches `Abandoned`, frees the worker, marks the job only
if a read has not already. Checks after stages 0, 1, 1.5, 2, 3, 4 and before OCR
in `build_generation`; top of `finish_generation` / `plan_stitches`; after stage 5;
before every shape in stage 7's `stitch_one`; top of `run_preflight`.
`EMBBOT_JOB_TIMEOUT_S` shortens the budget for a reproduction.

**Why no flag.** A check reads a clock and moves no number; a job that finishes in
time is byte-identical (design md5 pinned under a 3600 s scope vs none,
`tests/test_service.py`). Only work already reported dead changes.

**Still uninterruptible** (one call ends, then the next seam fires): stage 2's
region former (`photo_segment` / `quantize`), the rembg and SAM2 subprocesses
(own `*_timeout_s`), stage 7's chaining passes after emission, preflight's body.
Harness: the session scratchpad's `repro/serve.py` + `jam.py` (port 8721 is the
live service; 8731 was someone's `http.server`).
