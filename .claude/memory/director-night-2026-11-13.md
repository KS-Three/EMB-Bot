---
name: director-night-2026-11-13
description: The 11-13/14 director night. No single engine switch; the eye-first method gave 11 merged PRs. Agent eye PARTIAL (0.35 corrected vs bar 0.40, grade kappa 0.66). Two of the director's own theories disproved. apex_cut needs a guard. App limits for directors.
metadata:
  type: project
---

One laptop, about eight local workers, working from Kent's defect-marks pins.
Write-up: `docs/director-night-2026-11-13.md`. The source reports are
gitignored in the primary checkout under `digitizer/eye_pairs_out/`.

**No single switch.** Kent's pins split into many small causes. The method
was look beside the ORIGINAL, trace to a stage, fix one cause (see
[[eye-first-diagnosis-2026-11-13]]). It gave 11 merged PRs (#1476-#1490) and
5 fixes the director confirmed by eye.

**Kent's rulings, 2026-11-14:**
- He approved five flips, which land in their own PR:
  - `inshape_piece_lift`;
  - `small_text_reset_one_baseline` + `text_cluster_solid_guard`;
  - the four `group_consistent_*` flags;
  - `outline_redraw_k` 0.75;
  - `flat_blend_band_any_scale`.
- `lettering_columns_connectors_buried` stays OFF: "Build edge-walk" ([[connectors-on-top-2026-11-14]]).
- `bevel_ring_fold` is a Studio tickbox, OFF.
- An agent eye is the working judge for gross faults only.
- `lettering_columns_apex_cut` must not be flipped as built: 4 of 43 designs
  are worse ([[flip-candidates-2026-11-14]]).

**Disproved that night:**
- "The pro makes repeats identical": the art's Bridge handles are 0.21 mm
  apart, the pro's 0.21, ours 0.58. Our pipeline adds the irregularity.
- "We sew fatter than the pro": the width ledger (#1485) reads Becker 1.18 vs
  1.19 and Bridge 1.09 vs 1.09. We are heavier on MFab and Gaulke only.
- Proof-read as a guard: its hits on Kent's groups are barely above chance
  (satin 38 vs 29.7, fill 23 vs 19.7). It is a tracing tool
  ([[proofread-2026-11-13]]).

**Agent eye vs Kent's pins** (pre-registered, 45 designs): PARTIAL.
- 0.35 chance-corrected at his spot, against a 0.40 bar.
- 0.52 for the same fault named anywhere in the design.
- Grade kappa 0.66 (0.44 without his Terrible designs).
- Weak on jagged edges and pen flow.

**The pro adapts the art; we trace it.** 45 of 93 pins sit where he changed
the art: flattened shading 24, lettering raised 14, cleaned edges 7.

**Why:** the director put both "repeats identical" and "sew fatter" to Kent
as findings before they were measured against the art. **How to apply:**
- Before claiming a pro habit, measure it against the ART, not only against
  ours.
- Plan within the app's limits (`docs/superpowers/plans/2026-10-23-opus-team-architecture.md` §8):
  - a timer-fired or session-fired turn cannot start sessions;
  - each session is capped at 20 cross-session messages until its user types;
  - a worker's report reaches the director only through an explicit
    SendMessage;
  - `archive_session` leaves the lane folder behind.
