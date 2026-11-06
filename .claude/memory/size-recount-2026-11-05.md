---
name: size-recount-2026-11-05
description: "`POST /recount` + the reading row's 'N shapes, M colors at W mm' (Kent 2026-11-05, Stitchist footer, counts only). Own route: stages 0-4 cost 5-60 s vs /classify's 0.2-9 s; it leaves the generation cached so the run skips them"
metadata:
  type: project
---

Kent, 2026-11-05, after the Stitchist teardown (its footer says 13 objects / 3
colours at 100 mm, 4 / 2 at 36.7): build the RECOUNT ONLY. No suggestion
cards, no new decisions; the pipeline keeps deciding enclosed white, line type
and background silently. A count is a readout (allowed under the 10-02 "no
warnings reach readouts" ruling), never advice. See
[[free-digitizer-followups-2026-11-05]] and [[lane-reading-before-run-2026-10-28]].

- **Service `POST /recount`**: same upload and `config` as `/digitize`
  (`target_width_mm`, garment, edits). Runs `build_generation` +
  `finish_generation` and stops: nothing from stage 5 on adds or removes a
  region. Returns `{shape_count, color_count, size_mm, generation_cache,
  elapsed_ms}`. `shape_count` = regions with `meta.stitched`; `color_count` =
  distinct `thread_number` among them. One at a time (`_RECOUNT_SLOTS`).
  Additive, no `VERSION` bump (/classify bumped nothing either; `schemas.Recounted`
  and the route docstring are the contract). Old service: 404 -> Studio shows
  nothing.
- **Why not folded into `/classify`**: measured on Kent's laptop with three
  other sessions running (so upper bounds): MFab hat 7-17 s, owl 5-9 s,
  golden_tee 56-62 s, against /classify 0.2-0.4, 1.1, 7-9 s. The lane reading
  stays as fast as it was.
- **It writes the generation cache** (`generation_key`, same as `/digitize`): a
  run at the size just counted reports `generation_cache: "hit"` and skips stages
  0-4. The catch: the cache holds 4, so a size drag that settles on several
  widths evicts older ones (the 500 ms debounce keeps that to the settled ones).
- **Studio**: `lib/recount.js` (`createRecounter`: 500 ms debounce, abort the
  superseded fetch, module-level answer cache, 404 = never again, silent on
  failure) + `recountArt()` in `lib/digitizer.js`. `DigitizePanel` asks only
  while `phase === "idle"` (a run in flight would fight the worker for CPU),
  with the run's own config including a field resize's width, keyed on the whole
  config so a garment change re-asks. The line (`data-testid="art-recount"`)
  shows only while its key is the one on screen: a size change hides the old
  number at once. Spelled "colors", like the rest of the UI.
- **MFab hat, real service + Studio, headless Chromium**: 36.7 mm = 22 shapes,
  2 colors; 113.5 mm = 93 shapes, 2 colors (7.5 s each). Stitchist's 4 / 13 are
  its objects, not our regions: do NOT read the two as comparable.

**Why:** Kent wants the cost of a size visible before the run, as Stitchist
shows it, without another decision to make.

**How to apply:** a count before the run comes from `/recount`, never a Studio
guess. A new row of advice beside it is out of scope (Kent's ruling). Count
differences against the finished design (a blend band is one region but several
spools; `palette` can exceed `color_count`, owl at 113.5: 14 vs 12) are the
region stage vs the plan, not a bug in either.
