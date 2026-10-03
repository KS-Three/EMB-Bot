---
name: no-warnings-reaches-readouts
description: Kent's 2026-10-02 "we shouldn't have to warn the user of anything" covers always-on info rows and readouts too — a new instrument goes to preflight METRICS, not to the customer's report
metadata:
  type: feedback
---

Defect 46 (edge smoothness invisible to preflight) was first designed as an
always-on `info` row in the Studio's Quality report — no threshold, no score
cost, "just a readout". Shown that design against his 2026-10-02 ruling, Kent
picked **metrics only** (2026-10-03): three numbers in `report["metrics"]`,
nothing rendered.

**Why:** his words were about a low-resolution warning, but the principle is
the tool's job — "identify the image it's being given and follow a path to
produce the best output possible." Telling the customer an edge is 0.9 mm off
is the tool reporting its own flaw instead of fixing it, whatever severity the
row carries.

**How to apply:** when wiring an instrument into preflight, default to a
metric that judges nothing (precedent: `tiny_steps`, `raw_score`,
`edge_wobble_*`). Propose a customer-facing finding only for something the
CUSTOMER can act on (their file, their size, their garment), and ask first.
Existing findings are not retracted by this — it governs what gets added.
Related: [[next-work-from-main-not-handoffs]], [[warn-sooner-small-files-handoff-2026-10-01]].
