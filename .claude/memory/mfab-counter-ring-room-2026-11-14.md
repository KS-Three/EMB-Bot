---
name: mfab-counter-ring-room-2026-11-14
description: "2026-11-14 — Kent's MFab 'random stitch in the middle' = photo-lane 'significant' border on the A's 3.35 mm counter, lightened to a 3-pass bean loop inside its own fill; `border_significant_ring_room` (cfg.extra, OFF) earns no ring without column room; our satin tier on it was worse"
metadata:
  type: project
---

# MFab's A counter: a border with no room — 2026-11-14

Kent's MFab hat pin: "random stitch in the middle". It was named in
[[connectors-on-top-2026-11-14]], not fixed. The Director's brief: eye-first,
fix it, built OFF.

**What sews there** (MFab hat 104.9 mm, `eye_pairs_out/mfab-triangle-1114/`):
- **Where:** S6f70d810, the A's white counter: 7.0 x 7.6 mm, 3.35 mm
  inscribed, enclosed background.
- **Ours:** a fill, plus a 3-pass bean loop 0.85 mm inside it, on top.
- **The pro:** one fanned satin.
- **Why:** MFab classes `photo_scene`, so `border_style` "significant"
  borders every shape that earns it. `BORDER_SIGNIFICANT_AREA_SHARE` is
  0.0, so the counter earns one. The column ring needs 3.8 mm across, so
  `_border_runs` lightens it to a bean loop (`core.is_empty`), which covers
  no edge.
- **At the Studio's 113.5 mm** nothing borders the counter; the pin is a
  104.9 mm one.

**Built OFF:** `cfg.extra["border_significant_ring_room"]`.
- `stage6_border.ring_has_room` reads the ring builder's own host, spine
  and core.
- `stage7_sequence._border_wanted` takes it as `room` at both readers (seam
  prediction and border block). Per-shape intent still beats it.
- **Result on MFab 104.9:** only the counter changes. The loop is gone and
  the fill stays; md5 equals the hand-set `border: off` trial.
- **Elsewhere ON = OFF md5:** MFab hat at 113.5, MFab LC, Becker hat large
  and Bridge hat (flat lane: "significant" never runs there), and the kit
  photos bw_street, architecture and landscape_lake.
- **night_neon moves on one shape:** a 19.9 mm2 grey shape. The same loop
  sat in the middle of its fill, and ON leaves the plain fill.

**Tried and rejected:** the satin tier on the counter (`tier: satin`)
sews a chunky block bulging past the triangle, worse than the fill. We
have no fanned-satin construction like the pro's.

Related: [[mfab-photo-route-2026-11-04]].
