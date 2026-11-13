---
name: space-fault-reader-2026-11-12
description: Fourth fault reader (negative space: thread covering the midline of bays and inter-shape gaps): shown on the 44 letter pins (+0.32 over chance_pick, CI [+0.22,+0.47]), NOT a hold-out; replication on defect-marks-1112 = no verdict (2 of 9 items carry a target pin, floor 5)
metadata:
  type: project
---

Built 2026-11-12 after [[letter-fault-reader-2026-11-11]] missed both "S has
no spacing" pins (a bay filled solid changes no topology). Reader
`tools/space_fault_reader.py`, harness `--fault space` (`select_space_pins` =
the letter pins + `note_pin`). Pre-registration `837c105d`, write-up
`docs/space-fault-reader-2026-11-12.md`.

**Rule:** per thread class, glyph_read's `space` ridge per shape (hull less
ink) plus the Voronoi line between two judged shapes inside the pair hull;
ridge >= 0.15 mm from ink and its clear circle inside the hull with 0.10 to
spare (`enclosed`, a dev-item bug fix: field outlines' dents); closed = same
class thread within 0.10 mm; a fault = closed run > 0.6 mm. Reads the letter
reader's stored rasters (tree 950855bf, sha re-checked): no pipeline, ~15 s.

**Result (44 pins / 7 items / 15 notes, 3 mm):** per note 0.798 vs pick 0.483,
+0.32 [+0.22, +0.47]; per pin +0.29 [+0.24, +0.44]; every leave-one-out lower
bound >= +0.21. Both S pins and the E pin hit. Overlap with the letter reader:
33 both, 7 space only (S x2, Gaulke white spacing, TOAT T-into-border), 2
letter only (Bridge N+T join, Fremont size remark); together 14 of 15 notes.

**How to apply:** shown on pins that shaped the idea, so replicate before any
use: score it frozen at `837c105d` on a fresh sitting (e.g. `defect-marks-1112`
after the letter hold-out). It is broad: flags ~half of its candidates and
most flags are unpinned (Drone 182 flags, no target pin), so a "where" list,
not a gate. Pair it with the letter reader; they miss different pins.

**Replication 2026-11-13 (foreman's call, pre-registered `e5d811cd`): no
verdict.** On `defect-marks-1112` the frozen pin rule gave 2 pins on 2 of 9
items (floor 5): bukit_asam "no spacing between the rings" hit at 0.51 mm
(letter reader hit too), n_sync's S pin (thread angles meeting) missed at
9.0 mm (letter reader missed too). That kit drew edge/flatness/alignment
notes, not closure; a replication needs art likely to draw bay/spacing notes.
