# A warning that read like a ruined job, bounded to nil by reading

**2026-09-07.** `PALETTE_THREAD_MISMATCH` fires on **6 of 26** corpus
fixtures, appeared in **no document at all** (not MASTER_SCOPE, DOCTRINE,
`docs/` or memory) despite the code describing it since 2026-08-14, and its
own comment says *"the operator loads a cone that sews nothing while the
thread that IS sewn is missing from the list."*

**That is not what happens.** Read this before spending a session on it, and
before writing a severity down from a warning's own words.

## Three corrections, every one from a docstring, each SMALLER than the last

1. **Wrong list.** The first `tools/palette_mismatch.py` compared
   `result.palette` against what sews and printed **RACK-WRONG** on all six.
   But there are two palettes: `plan.palette` is per BLOCK (`palette[i]`
   describes `blocks[i]`, shipped as `stats.blocks`) and **that is what the
   operator threads from**; `result.palette` is the per-LAYER list the review
   screen edits. Reading the layer list positionally against blocks is exactly
   what shipped `golf_hat`'s black block labelled "0020 Tangerine" until
   2026-08-14 — `StitchPlan.palette`'s comment says so. The operator list is
   now checked per fixture, **26 of 26 consistent**.
2. **Confounded.** The second cut reported "threads that sew but are absent
   from the review list", up to seven on a fixture. **By design** — a blend or
   tonal region sews several shades inside one layer and they ride in
   `stats.blocks`. `gradient_ramp_linear`: **1** mismatched shape beside
   **4** "missing" threads. An all-unstitched layer (`SHAPES_LEFT_UNSEWN`,
   10 of 26) confounds the other direction the same way. The warning itself
   was clean throughout — `mismatched` is computed over REGIONS and their own
   `thread_number`, so blend bands never enter it. The TOOL was the noise.
3. **Already defended.** The clean number is real: **34 shapes over six
   fixtures, and on all six the thread those shapes sew is on no review layer
   at all** (the documented survivor after `rehome_resnapped_regions` — a
   re-snap whose target no layer declares). Then read the consumers, which
   should have been step one: `reviewFromJob` resolves a shape's colour
   `byNumber.get(s.thread_number)` **with a `stats.blocks` fallback keyed by
   the shape's own `sew_block`**, its other use is `palette[0].brand_id`
   (uniform), and `QualityReport.svelte` refuses the layer palette outright.
   **Nothing in the Studio renders the layer list as a cone list.**

## What is true

A real internal inconsistency with a **nil customer-visible blast radius**.
Its value is as a regression detector for the day someone adds a consumer that
reads `review.palette` positionally or as a cone list. MASTER_SCOPE defect 30
states that bound so nobody re-chases it.

## The reusable rule

**A warning's SEVERITY is decided by its CONSUMERS, not by its own words.**
And: **an instrument that only ever confirms is not measuring.** Three passes,
three shrinks, and every piece of correcting evidence was already in a
docstring — `StitchPlan.palette`'s, `_stats_payload`'s, `reviewFromJob`'s.
The 7-minute corpus runs produced the number; the reading produced the answer.

## Budget

`MASTER_SCOPE.md` sits at **799 of its 800-line budget** after defect 30.
Defect 29 was compacted to a fixed-state pointer in the same pass to make
room, and the file's long-line style means an entry costs a line whatever its
prose. **The next addition needs a retirement first.**
