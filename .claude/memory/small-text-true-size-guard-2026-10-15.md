---
name: small-text-true-size-guard-2026-10-15
description: "True-size switch below 81 mm: three separate 65 mm failure causes, per-glyph OCR misleads, counter-width guard 0.45 not 0.5"
metadata:
  node_type: memory
  type: project
  originSessionId: 2e253041-18f4-42e0-b11f-3fde5c820fc6
  modified: 2026-10-15T07:23:39.053Z
---

Fremont small lettering at 65/72 mm under `small_text_true_size` (2026-10-14/15, Director-led lane):

- The 65 mm "regression" had THREE causes, none of them cap height:
  1. THE merged into the date's text cluster; restore stripped it as strays and it was traced 1.8x fatter. Fixed by `small_text_keep_stray_lines` (#960).
  2. The date's ink read was spoiled by the black Wisconsin shape in the crop: strokes read 0.84–1.73 mm instead of 0.15. Fixed by `ink_ground_ring_mm` (#958, OFF).
  3. The tagline's per-glyph OCR flips (10/11 → 5/11) are mostly instrument; whole-word tesseract (psm 7) reads EAT/STAY/PLAY on every arm. The real cost is the A apex counters filling.
- Counter census (#964): only loss is at a 0.44 mm min counter, smallest win at 0.47, so a 0.45 guard separates them and 0.5 holds a real win. The guard needs a speck floor (Becker's tracer specks read 0.05 mm).
- `LETTER_MIN_HEIGHT_MM` is not the gate for small Fremont text: the date enters via rescued shapes, and lowering the floor changed nothing.

**Why:** a cap-height guard would have shipped on a wrong diagnosis; #955's claim "65 mm byte-identical to main" was false on the Studio path.
**How to apply:** before judging small text by `glyph_legibility` OCR, also run whole-word OCR and look at the render. Measure on `fremont_triage.run_arm` (the Studio-request path), not `run_stages`; they cluster differently. Related: [[hotel-fremont-pro-parity-findings]], [[font-pipeline-silent-failures]].
