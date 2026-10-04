---
name: no-warnings-reaches-readouts
description: Kent's 2026-10-02 "we shouldn't have to warn the user of anything" covers always-on info rows and readouts too — a new instrument goes to preflight METRICS, not to the customer's report
metadata:
  type: feedback
---

Defect 46 (edge smoothness invisible to preflight) was first designed as an
always-on `info` row in the Studio's Quality report — no threshold, no score
cost, "just a readout". Shown that design against his 2026-10-02 ruling, Kent
picked **metrics only** (2026-10-03): numbers in `report["metrics"]`
(`edge_wobble_<tier>_<stat>_mm`), nothing rendered.

**And a metric still has to be honest to the tools that read it.** The first
build exported one POOLED figure; the engine's run tier reads exactly 0, so
the pool moved with tier mix (enthusiast: satin p95 0.247, pooled 0.186). Per
tier fixed it. The same review caught the docs closing defect 46 on a
docstring read halfway: Law 37's quantity is `curve_fidelity.roughness_deg`,
not edge deviation, and it is still offline. Read the whole docstring, and
check this index — it already said "read `roughness_deg` per design". Later
the same evening the curve half shipped the same way (`curve_roughness_deg`,
`curve_turn_gini`, `curve_vertices`, `curve_corner_vertices`, `curve_traces`;
commit 84fb94a5), so defect 46 is metrics-only on both halves;
`edge_smoothness` is what stays offline.

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
