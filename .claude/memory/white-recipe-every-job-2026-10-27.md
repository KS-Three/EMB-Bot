---
name: white-recipe-every-job-2026-10-27
description: Kent 2026-10-27 "Every job (Recommended)" — the white-keyline recipe's switches are plain defaults (not a gate that always passes); 3 recipe defects + a counter-growth defect fixed first; 22-job re-proof
metadata:
  type: project
---

Kent, 2026-10-27, verbatim: "Every job (Recommended)". The white-keyline recipe
(`white_keyline_art.RECIPE` + `absorb_fragments`) now sews on every job (PR #1143).

**Plain defaults, not detect=True.** The gate's `apply` forces every switch ON over
a caller's explicit OFF. Made to pass on all art, it overrode the Studio's unticked
"Sew white areas" (`sew_enclosed_white=false`) on every job; studio-e2e caught it.
So the seven OFF switches default True and `absorb_fragments` became a field
(`cfg.extra` still wins). The 10-27 snapshot holds False for each; tests about
other flags spread `conftest.RECIPE_2026_10_27`. (Main's #1146 had already taken
the name `FLIP_2026_10_27` for its own three flips.)

**Defects the flip exposed, all present on MFab art before, fixed in #1143:**

- D1: the under-fill rim ringed a gradient host. The rim now skips a host sewn as
  shade bands.
- D2: a shape merged into a host had no sew facts in the review payload.
  `StitchPlan.merged_into` now maps it, and the payload and blocks read the
  host's facts.
- D3: a review-screen layer pin was beaten by the host move. A pinned shape is
  never merged, and no host moves ahead of a pinned layer.
- Becker's B counter grew into the white face. The face merged into the white
  ground, so stage 5 lost the "never grow over a colour already down" trim
  (hat large counter 26.1 -> 36.3 mm², pro 24.2).
  `silhouette_underfill.MERGED_ART_KEY` keeps merged art down at the host's layer.

**Still true, measured.** A layer pin into a MIXED layer never opened the design,
even pre-flip. Kent ruled "Yes, pinned shape leads (Recommended)"; the build is
left to the director's handoff.

**Named follow-up:** Becker small's band corner tip ends blunt where the pro runs
the satin to a point (+1.1 mm² bare on hat small).

How to apply: measure a flip on BOTH engines through the same harness
(`today` = the flipped fields set False explicitly). Check a gate-based flip
against explicit OFFs from the Studio. Read "lost detail" crops before
calling a job closer. [[white-keyline-art-gate-2026-10-26]] [[silhouette-underfill-2026-10-24]]
