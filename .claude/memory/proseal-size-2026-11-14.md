---
name: proseal-size-2026-11-14
description: "ProSeal hat at the auto-fit 109.6 mm breaks its tagline (teal sliver in the P, FOAM's A without crossbar, T broken) because its cap measures 4.01 mm >= the re-set's 0.9 x cap_mm (3.6) -> skipped tall_enough, sewn as raw trace; at 85.7 (3.1 mm) it is re-set and reads. flat_blend_band_any_scale neither cause nor cure. A near-cap re-set tried, still no_room: not shipped"
metadata:
  type: project
---

**What (Director's order 2026-11-14, eye-sweep fault 4):** ProSeal at the
Studio's hat auto-fit (109.6 mm; the pro sews 85.9) shows three gross faults
in "SPRAY FOAM + COATINGS"; at 85.7 the line reads. The size is the auto-fit
bug (another worker); this traced why the LARGER size breaks the letters.

**One number:** the tagline's cap is 4.01-4.05 mm at 109.6. The small-text
re-set skips a line at `cap >= 0.9 * cap_mm` (3.6 mm; below 4.0 it could not
grow by `MIN_SCALE` 1.15 anyway), so all three clusters are `tall_enough`
and sew their raw trace. At 85.7 the same clusters (3.04-3.15 mm) are re-set
1.29x: retraced from the art, widened, read. The raw trace at 109.6 keeps the
letters' anti-aliased edges as shapes of their own: the teal bar is
`Sa9d6b963`, thread 4101, 0.13 x 3.6 mm at the P's left edge,
`rescued_small_shape` + `thread_resnapped_de00`; black (1776) slivers sit in
other letters; the A's crossbar and the T's join fall out of the thin trace.

**`flat_blend_band_any_scale` (ON 11-14): neither cause nor cure** -- OFF,
109.6 is identical (9,346 stitches, same 44 tagline regions, same sliver).

**Tried, not shipped (`small_text_reset_near_cap`):** re-set a line from 0.9
to 1.25 caps at `MIN_SCALE`. The tagline is then considered but stays
`no_room`: it sits on the design's bottom edge with its top touching
(`grow_away` up 0.0) and its own slivers count as obstacles (widening the
inner-piece tolerance to 0.3 mm cleared them on two of three clusters, not
the room). md5 unchanged, so no flag was kept. Next lever: a re-set at
scale 1.0 (retrace + widen only, no growth, no room needed) for lines just
over the cap. Sheets: `eye_pairs_out/proseal-size-1114/sheets/`.
