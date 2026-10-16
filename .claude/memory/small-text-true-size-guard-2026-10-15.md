---
name: small-text-true-size-guard-2026-10-15
description: "True-size switch below 81 mm: three separate 65 mm failure causes, per-glyph OCR misleads, counter guard 0.45 x 40/wt (unsewn candidate); ink ring still OFF"
metadata:
  node_type: memory
  type: project
  originSessionId: 2e253041-18f4-42e0-b11f-3fde5c820fc6
  modified: 2026-10-15T07:23:39.053Z
---

Fremont small lettering at 65/72 mm under `small_text_true_size` (2026-10-14/15, Director-led lane):

- The 65 mm "regression" had THREE causes, none of them cap height:
  1. THE merged into the date's text cluster; restore stripped it as strays and it was traced 1.8x fatter. Cured by `small_text_keep_stray_lines` (#960, merged OFF). It is live ONLY because the true-size switch fills it True (`config.SMALL_TEXT_TRUE_SIZE`, #955); switch OFF or PRE_FLIP, THE breaks again.
  2. The date's ink read was spoiled by the black Wisconsin shape in the crop: strokes read 0.84–1.73 mm instead of 0.15. `ink_ground_ring_mm` (#958) cures it but is NOT ON: default None, not filled by the switch, "a separate Kent flip" (#955). At shipped defaults the date still mis-reads.
  3. The tagline's per-glyph OCR flips (10/11 on main → 5/11 on the UNGUARDED switch; 8/11 with the guard) are mostly instrument; whole-word tesseract (psm 7) reads EAT/STAY/PLAY on every arm. The real cost is the A apex counters filling.
- Counter census (#964): only loss is at a 0.439 mm min counter, smallest win at 0.47, so a 0.45 guard separates them and 0.5 holds a real win. The guard is `SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM` scaled `x 40 / thread_wt` (`config.counter_floor_mm`): 0.45 mm at 40 wt, 0.30 at 60, 0.24 at 75. **An unsewn gate-1 CANDIDATE**, 0.011 mm above the loss; a 65/72 mm tagline sew-out settles it. The speck floor is BUILT (#955: holes under 0.003 mm² or narrower than max(0.1 mm, 5% of cap) are skipped — Becker's 0.05 mm specks).
- `LETTER_MIN_HEIGHT_MM` is not the gate for small Fremont text: the date enters via rescued shapes, and lowering the floor changed nothing.

**Why:** a cap-height guard would have shipped on a wrong diagnosis; an earlier DRAFT of #955 claimed "65 mm byte-identical to main", false on the Studio path (the merged body corrects it).
**How to apply:** before judging small text by `glyph_legibility` OCR, also run whole-word OCR and look at the render. Measure on `fremont_triage.run_arm` (the Studio-request path), not `run_stages`; they cluster differently. Related: [[hotel-fremont-pro-parity-findings]], [[font-pipeline-silent-failures]].
