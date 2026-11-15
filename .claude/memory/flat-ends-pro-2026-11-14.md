---
name: flat-ends-pro-2026-11-14
description: Kent's satin-end pins read against the pro stitch by stitch; his edge = cross ENDS on the line or the last cross ON a flat face; ours tilts because text_lean re-stations away the cut's mitre; `lean_flat_ends` (cfg.extra, OFF) mitres leaned ends; Becker #10/#11 flat
metadata:
  type: project
---

Director's queue item 1, 2026-11-14 evening: Kent's 14 end/corner pins from
#1481. The corner turn (#1518) cures none of them.

**The pro, needle by needle:**
- Becker #10 (N top): steep crosses, ends on one top line.
- Becker #11 (N foot): crosses parallel to the baseline, the last ON it.
- ProSeal #2: parallel crosses clipped on the slanted face.
- Gaulke #2: parallel crosses ending on the gap edge.
- Fremont #3: matches ours.

**Ours at Becker #10/#11:** the cut mitres an end onto a flat face
(`_mitre_ends`, 8-45 deg). The house lean (`text_lean`, ON) then
re-stations the columns with the word's cross, clamped to 10-12 deg on the
N's diagonal. That throws the mitre away, so the end is a tilted cross
across a flat face.

**`cfg.extra["lettering_columns_lean_flat_ends"]` (built OFF)** reruns the
mitre on the leaned stations against the house cross.
- The N's foot gap to the baseline: 0.534 -> 0.428 mm.
- #10 and #11 read flat by eye.
- ProSeal #2's fan and Gaulke #2's stagger are not built.
- Corpus, flag alone: 21 of 28 designs move, trims 592 -> 594 (N Sync +1),
  travel on thread 263.8 -> 261.4 mm but mixed; k_line #4 not cured.

**Why:** Kent: "The letters should be flat".
**How to apply:** a re-stationing pass must keep the end constructions the
cut made.

Write-up: `docs/flat-ends-pro-2026-11-14.md`. See
[[jag-source-2026-11-13]].
