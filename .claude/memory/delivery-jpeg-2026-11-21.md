---
name: delivery-jpeg-2026-11-21
description: "Customer-delivery invariance: tools/delivery_jpeg.py (JPEG q95..q30, double save, thumb, alpha flattened); Becker flattened sews the page with GROUND_SEWN silent (split ground, span 0.65); gaulke q30 letterbox ringing FIXED (JPEG_RING_LINES), its edge strips still fail at q30/thumb"
metadata:
  type: project
---

Session 2026-11-21 asked "does a customer's JPEG sew the same logo as the master?" — nothing had measured it.

**Instrument:** `digitizer/tools/delivery_jpeg.py`, `--set FIELD=VALUE` prices any flag across deliveries. Doc and pictures: `docs/delivery-jpeg-2026-11-21.md`.

**Fixed:** `letterbox._run_length` voided a bar when JPEG ringing put one line between the run and the hard edge (gaulke q30). Step may now sit up to 7 lines past the run, must be hard against the previous line, crossing only uniform lines. 0 of 53 committed images and 1 of 371 deliveries change verdict.

**Open, in order of customer harm:**
1. Becker with alpha flattened (any JPEG of it): `BACKGROUND_ABSENT` (ring agreement 0.711 < 0.75, outline touches the edge) and the page sews as a white rectangle; `GROUND_SEWN` silent because the ground is split into pieces (biggest spans 0.65 of height). A detector fix (union of edge-touching border-colour pieces) is a warning only; the engine fix is stage 1.
2. Gaulke q30/thumb: `detect_edge_strips` misses the 9-px card shadow (q30 outer columns drift within 6 dE of white; thumb columns carry a resize-blended line), so BACKGROUND_ABSENT and the card sews.
3. whitebg q95 loses purple to blue; bridge q50 halo cones return (q30 better than q50).

**Why:** customers send JPEGs; both failures sew a block of cloth-coloured thread across the design.
**How to apply:** rerun `python -m tools.delivery_jpeg` before and after any stage-1 background or letterbox change.
