---
name: infill-fault-reader-2026-11-11
description: Third fault reader (extra/uneven in-fill = thread sewn in an empty space of the art) vs Kent's pins on both sittings: per note 0.29 vs candidate-pick null 0.27, CI [-0.31,+0.28] = not shown; it finds the region, not which spaces he pinned
metadata:
  type: project
---

Built 2026-11-11 after [[letter-fault-reader-2026-11-11]] and
[[defect-marks-sitting-2-2026-11-11]]. Harness `tools/fault_reader_harness.py`
`--fault infill`; reader `tools/infill_fault_reader.py`; shared job runner
`tools/fault_reader_jobs.py` (L_ pro jobs and C_ corpus rows, stitch refusal).

**What "extra in-fill" is (read at the pins first):** on `C_kanji_seal` (28
pins) and `C_devanagari_logo` (1, 5, 6) the thread is white satin over pixels
the source PNG leaves TRANSPARENT: `sew_enclosed_white` (ON) sewing enclosed
background it takes for a body/field, leaving what it takes for a letter
counter open ([[enclosed-white-like-pro-2026-10-23]]). On seal script and
Devanagari that role split looks arbitrary to Kent. The reader reads
emptiness from the art's alpha (else the frame colour), never from `bg_mask`.

**Pin rule:** `select_infill_pins`, a contrast between places or the word
in-fill; colour and pro comparisons out; ranges "#1-#28" / "(#5-#6)" /
"for 7-8" cover bare pins; `note_pin` per pin. 36 pins, 6 items, 8 notes.

**Result (tree 950855bf, pre-registration `ba01dcb7`):** per note 0.29 vs
`chance_pick` 0.27 (random candidate spaces), CI [-0.31, +0.28]; per pin 0.33
vs pick 0.82; vs the area null 0.29 vs 0.04, CI [-0.003, +0.63]; precision
0.46 vs 0.40. Not shown. Devanagari is the only selection signal (3/3, pick
0.50). Kanji: all 28 pins sit in white-sewn empty spaces, but 17 read
"closed" because the white satin spills over the red strokes and wins the
0.6 mm ring; the reader also flags every white space, so pick = 1.0 there.
Pixel-art and gradient pins sit on ink, not empty space; Bridge 1/4 and
emoji 3 are shape/width/direction (predicted misses).

**How to apply:** do not use as a gate. The candidate-pick null is the one
that is not fooled by a band; keep it for the next reader. The edge-band
null is 0 by definition inside sewn fields (`edge_band` docstring), not a
bug. The reader cannot tell a hollow letter body the pro also sews (Becker:
5 false alarms) from a counter sewn by mistake (kanji); `sew_enclosed_white`'s
role split on non-Latin scripts is where Kent's complaint lands.
Write-up: `docs/infill-fault-reader-2026-11-11.md`.
