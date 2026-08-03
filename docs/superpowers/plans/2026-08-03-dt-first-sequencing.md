# Sequencing decision: DT-first (M0/M1) before photo steps 5+

Not a new build — a scheduling call on work that's already fully specced in
`docs/dt-first-architecture-2026-08-01.md` (masters-teardown research,
2026-08-01). This doc just pins where it sits in the queue relative to
everything else in flight.

## The decision

**Run DT-first migration steps M0 (measure, desk-safe, 0.5d) and M1 (hoist
the field, desk-safe, byte-identical required, 2-3d) before resuming
`docs/photo-digitizing-plan-2026-07-31.md` steps 5+ (direction fields,
mono-tonal tiers, streamline/portrait).**

Does NOT reorder anything ahead of it — the two active gradient/enclosed-white
regressions (`docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`,
`docs/superpowers/handoffs/2026-08-03-gradient-defects-handoff.md`) and the
background-existence guard (`fix/bg-existence-guard` worktree, in progress)
still go first. This only fixes the order of what comes *after* those land.

## Why

`docs/masters-teardown-2026-08-01.md` and `docs/dt-first-architecture-2026-08-01.md`
found EMB-Bot is structurally behind every patented auto-digitizer
architecture in one specific way: commercial tools compute contour, skeleton,
and distance transform as **one artifact**, then decide satin-vs-fill from
distance-transform statistics sampled at skeletal pixels. EMB-Bot rasterizes →
vectorizes → re-rasterizes → skeletonizes, and the DT (`stage6_satin.py`'s
`medial_axis(return_distance=True)`) exists only *after* `stage7_sequence.py:97`
has already made the satin/fill call from `2·area/perimeter` — a statistic
the source patent explicitly warns against, and one measured (§3.3 of the
architecture doc) to be wrong on a straight bar's own boundary noise (satins
a 20mm disc under a 5mm cap once the edge is serrated) and blind to mixed-
thickness shapes.

An independent spot-check (asked ChatGPT for its own auto-digitizer stack
recommendation, 2026-08-03) converged on the same structural point from a
completely different reading of the field — a second, cheap signal that this
is worth acting on rather than filing away as one research doc's opinion.

Photo-digitizing steps 5+ (direction fields, mono-tonal tiers, streamline/
portrait) all lean harder on satin-vs-fill classification quality than
anything shipped so far — they're new stitch-tier decisions built on the same
classifier this migration replaces. Building them on the known-wrong ordering
just grows the backlog the 2026-08-01/02 sessions spent real effort clearing
elsewhere in the pipeline.

## Scope of what actually lands here

Only **M0 + M1** from the migration map (`docs/dt-first-architecture-2026-08-01.md` §2):

- **M0** — instrument only. Add a `dt` section to `digitizer/tools/shape_lens.py`
  measuring `max/μ/σ` of DT at skeletal pixels against the current
  `area/perimeter` call, on the fixture logo and all 37 `scratch_corpus/`
  files. Zero engine changes, zero golden impact.
- **M1** — new `digitizer_core/shapefield.py` (`ShapeField` dataclass: mask,
  skeleton, exact EDT, scale, origin), hoisting one `medial_axis(rng=0)` call
  so skeleton and distance transform are computed together and available to
  every downstream stage, matching the patent's core architectural claim.
  Ships behind `cfg.extra["shapefield"]` defaulting to today's path — **byte-
  identical output is a hard requirement**, proven by the M0 instrument
  before flipping anything.

**Explicitly NOT in this slice:** M2/M3 (the classifier itself, corpus-gated
+ sew-out-gated — the change a customer can see), M4-M8 (spur pruning, fixed
vertices, per-branch classification, fragment-count fill angle, letterform
wins). Those stay queued behind M0/M1 exactly as the architecture doc already
sequences them — this decision only moves M0/M1 ahead of the photo-steps-5+
queue, it doesn't touch the rest of the migration map's internal order.

## Where this leaves the overall queue

1. Gradient fragmentation + enclosed-white-icon regressions (active now,
   `fix/bg-existence-guard` + the fill-axis-model plan doc)
2. **M0 + M1 of the DT-first migration** (this doc)
3. Photo-digitizing plan steps 5+ (direction fields, mono-tonal, streamline/
   portrait)
4. M2/M3 onward of the DT-first migration, once M0/M1 are in and the corpus
   disagreement table exists to gate them
