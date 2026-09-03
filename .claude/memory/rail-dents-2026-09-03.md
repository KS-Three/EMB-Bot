---
name: rail-dents-2026-09-03
description: defect 23 FIXED — `_rail_points.place` put an overshooting rail 15% in however small the overshoot (70–90% of them sub-pixel); now on the edge along its own normal with a micron of containment tolerance, taper zones and caps keep the ladder. Rail jitter halves on every fixture. The recorded "one whole rail 15% short in every golden" was a synthetic-bar artefact (the ulp coin flip is 1–11% of real retreats; the micron alone moved 4 stitches) — measured negative in DOCTRINE. Open: the symmetric-offset rail model leaves 8–24% of lettering rail points > 0.1 mm inside the art.
metadata:
  type: reference
---

# Rail dents (defect 23), 2026-09-03

Full record: `docs/rail-dents-2026-09-03.md`.

- **Diagnosis corrected.** The synthetic 3 mm bar (exact spine) dents 29–54%
  of stations by the ulp coin flip; real raster art almost never has the
  smoothed width equal the hit to the ulp. A census of every containment
  miss on the real fixtures (`tools/rail_edge.py --ladders`) found the real
  mechanism: 250–1000 overshoots per design, 70–90% under one pixel, three
  quarters retreating 0.15 w.
- **Fix.** `place`: nearest boundary crossing along the normal (skipping the
  station's own contact within 0.05 mm like `hit`), ladder only when no
  crossing; `inside = poly.buffer(1e-6)` for containment. Scoped to the
  column body — unscoped, the ribbon head gained a guard-mangled cross
  (1.005 mm same-rail interval, starburst test).
- **Numbers.** Jitter p50 Fremont 0.012 → 0.0045, Becker 0.061 → 0.038;
  holes 11 → 5 / 72 → 63; crosses wider; Becker −81 st (fewer refinement
  stations, the zig-zag was inflating the outer-rail advance).
- **The open half, BUILT 2026-09-03 as `satin_rails_follow_edge` (OFF, Kent's
  flip).** The inside-gap metric was NOT the rail model (Becker: 353/670
  guard retractions, 115 corridor caps, 129 corners, 48 tips); coverage is
  bare satin area (`rail_edge.py --bare`): Becker 8.6 → 5.8%, ENTHUSIAST
  5.7 → 4.4%, drone 6.1 → 4.6% for +10–17% thread and +50% rail jitter.
  Sew-out question (pull comp tuned with the far rail short).
- **Open.** Tips (exact-edge rails bunch on a converging tip).
