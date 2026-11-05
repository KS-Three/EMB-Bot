---
name: free-digitizer-followups-2026-11-05
description: Kent's 2026-11-05 rulings on the seven "worth taking" ideas from the free-digitizer survey and the DADE/Stitchist teardowns - what to build, how far, and what is skipped
metadata:
  type: project
---

**Context.** The survey ([[free-digitizer-survey-2026-11-04]]), the DADE and
Stitchist teardowns ([[dade-app-teardown-2026-11-04]],
[[stitchist-teardown-2026-11-04]]) and the Tier 1 scoreboard
(`docs/scoreboards/free-digitizers-2026-11-04.md`) left seven untaken ideas.
Kent went through them one at a time on 2026-11-05 (side-by-side table:
today / built / cost / catch, then one question each).

**Rulings (Kent, 2026-11-05):**

1. **Numeric stitch-out score: METRICS-ONLY.** Premise corrected the same
   day by the build session: `run_preflight` has returned `score` =
   max(0, 100 - sum(_DEDUCT)) (info 0 / warn 12 / block 30; grade A >= 90,
   B >= 75, C >= 60, D >= 40, else F) since 2026-07-31 (d0b79b1e), the
   service passes it through, and the Studio already shows `score/100`
   beside the grade (`app/src/ui/QualityReport.svelte:189`). Kent 11-05,
   second ruling: **keep that display as is**, add no new one, no Show, no
   Fix buttons. What gets built: a module comment on the mapping, tests
   pinning grade/score monotonicity, the blocking-finding cap and the
   floor, a service field test, and the score beside the grade in the
   scoreboard tools that print only the grade.
2. **Suggestions wizard: RECOUNT ONLY.** When the size changes, the reading
   row shows the object and colour count re-traced at that size (Stitchist's
   footer recount). No pre-answered cards; the pipeline keeps deciding
   enclosed white / line type / background silently.
3. **Export bundle: ZIP ONLY.** One Download-all: every format the service
   writes + the existing worksheet PDF (`exportWorksheetPDF`) + preview PNG +
   colour chart. No basting frame, no max-stitch split, no PES v1/v6 pair.
4. **Re-read before download: BLOCK ON MISMATCH.** Kent: "you pick"; pick =
   block. Service and browser re-parse the bytes they just wrote (stitch
   count, trims, colour blocks, max stitch 12.1 mm); a mismatch stops the
   download with a reason. Rationale given: a file that fails its own
   read-back is broken, not low quality, so 10-02 does not apply.
5. **TSP segment ordering: SKIP.** Order is not the gap
   ([[sequence-like-pro-2026-10-25]]: 18 of 145 extra cuts).
6. **heatstitch width-rule floor row: ADD.** One scoreboard row per job, our
   kappa vs heatstitch's untuned 0.13. Laptop-only (heatstitch DSTs live in
   gitignored `scratch_bench/`, the cloud nightly cannot run them).
7. **Literature lanes (streamline fills, skeleton-fork split, MSEmbGAN
   labels): PARK ALL.** Revisit after the Hatch trial; the photo lane has an
   active fix session ([[mfab-photo-route-2026-11-04]]), do not stack.

**Why:** each is sized to the smallest form that keeps the idea's value
without a customer-facing change or a sew-out claim. **How to apply:** a
session building 1-4 or 6 builds exactly that form; widening any of them
(Show/Fix buttons, cards, basting frame) is a new ruling, ask first. Order
not yet set; Hatch trial install (`docs/hatch-trial-export-plan-2026-11-04.md`)
is still the next approved external step.
