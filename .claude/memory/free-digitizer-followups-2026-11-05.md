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

1. **Numeric stitch-out score: METRICS-ONLY.** A /100 derived from preflight's
   existing codes and `_DEDUCT` weights goes into the preflight JSON and
   scoreboards. Customer sees nothing (the 10-02 "no warnings reach readouts"
   ruling stands, [[no-warnings-reaches-readouts]]). No Show, no Fix buttons.
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
