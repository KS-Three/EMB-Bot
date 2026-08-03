EMB-Bot, C:\Users\EE-LT-11030\EMB-Bot. Read CLAUDE.md and COOKBOOK.md first
— COOKBOOK.md especially, it's the handoff doc and has the architecture map,
running instructions, and a "Known bugs" section with everything below
already logged.

## Where things stand

Last session shipped the first slice of photo/gradient digitizing (classifier
+ gradient blend tier + SLIC/RAG region-former for photo-class input) —
merged to `main` and pushed, 402 digitizer + 265 engine + 321 app tests
green. Also landed, same session: a real geometry bug fix
(`principal_angle_deg`, affects every fill/satin shape system-wide,
independently verified against a rasterized ground truth before trusting
it) and cleanup of 6 stale worktrees.

The morning after, a real-world test (a gradient logo with white icon
linework, run through Studio) surfaced two regressions in what just
shipped. Diagnosed and queued, not fixed yet:

## Immediate task

Read `docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`
in full — it has the confirmed root causes, evidence, a repro fixture
(`digitizer/testdata/photo/repro_gradient_white_icon.png`), and fix-direction
options for both:

1. **Gradient designs fragment before blend treatment.** `gradient`-class
   designs still segment via plain k-means first (23 regions on the repro),
   so each fragment picks its own independent fill angle instead of one
   shared gradient direction — reads as a patchwork, not a smooth ramp.
   The plan doc recommends fitting one whole-image ramp model at stage 2
   (reusing `stage6_blend.detect_ramp`'s existing fitting logic, run one
   stage earlier) over just widening the photo region-former's dispatch to
   include `gradient` — the latter fixes fragment count, not angle
   consistency, which is the actual reported defect.
2. **Enclosed white design elements drop as unstitched holes.**
   `BACKGROUND_ENCLOSED` fires even when the region survives stage 1's
   background detection intact — general to the whole pipeline, not new,
   just newly customer-visible on exactly this art. Needs reading
   `stage3_segment.py`'s actual enclosed-hole logic closely (the diagnosis
   session didn't get that far) before picking a fix direction.

Both need their own measurement/design pass before building — same
discipline as every other slice this project has used (brainstorm → spec →
plan → build in an isolated worktree → TDD → verify independently → merge).
Don't skip the verification step even though the bug reports feel urgent —
last session found real, subtle bugs specifically by NOT trusting first-pass
fixes (a report-contract mismatch that would have crashed on first use, a
synthetic fixture that didn't actually test what it claimed to, a merge that
silently left a stale golden on `main` for a full commit before being
caught).

## Also true, lower priority

- `feat/satin-rails`'s chaining tier has a known, documented coverage
  blind spot (up to 29mm of bare cloth measured on a real fixture) — ships
  off by default, not blocking, but real. See COOKBOOK's Known Bugs.
- A sew-out is still not scheduled. Kent's explicit call last session:
  more work needed first, don't push for it.
- **Sequencing decision (2026-08-03):** once the two regressions above are
  closed, do NOT go straight to photo-digitizing steps 5+. Run M0+M1 of the
  DT-first migration first — see
  `docs/superpowers/plans/2026-08-03-dt-first-sequencing.md`. Steps 5+
  (direction fields, mono tonal tiers, streamline/portrait) all lean harder
  on satin-vs-fill classification quality than anything shipped so far, and
  the classifier is the one thing `docs/dt-first-architecture-2026-08-01.md`
  found EMB-Bot structurally behind on. Building more stitch-tier logic on
  top of it first just compounds that debt. M0/M1 are desk-safe,
  byte-identical, ~3 days combined — not a detour, a small slice ahead of a
  bigger one.
