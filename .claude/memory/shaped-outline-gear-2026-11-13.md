---
name: shaped-outline-gear-2026-11-13
description: "2026-11-13 — `border_from_outline_follow_shape` built OFF (Kent on Commons Ahora: \"now fix the Ahora gear so it sews as a gear\"): a band that fits one satin and swings by a stitch sews its loop to the art's own outer edge, needle locked to the teeth, plus a corner-exact edge run"
metadata:
  type: project
---

# A shaped outline follows its outer edge (`border_from_outline_follow_shape`) — 2026-11-13

**What Kent saw.** Commons "Ahora" (`testdata/art/commons_lettering/logo_ahora.png`):
a white gear, 17 teeth, round a yellow disc inside the O. "the ring on Ahora
looks better, but its still a circle and not a gear like the image", then
"now fix the Ahora gear so it sews as a gear".

**Cause.** Not the hairline flag: main sewed it as a ring at every size.
`border_from_outline` reads the gear as an outline round the disc and sews one
satin loop of ONE width on the disc's edge. The toothed outer edge is never
looked at. With the rule off, plain satin gave a lumpy blob.

**Built, default OFF** (`art_outline.band_thickness`, `shaped_width_mm`,
`shaped_stations`; stage 7's outline rung; `keyline_runs` takes a hole's own
stations as a third tuple item).
- Shaped = the band never thicker than `SATIN_MAX_WIDTH_MM` (5.0) AND its
  thickness swings (p90 - p10) by at least `SATIN_MIN_CROSS_MM` (0.5). No new
  constant. All of an outline's loops or none.
- Each cross is cut where it leaves the ART (reach = the art, not the art
  widened): long on a tooth, short in a root.
- The needle is locked to the teeth: every thick and thin stretch gets a whole,
  even number of stations, none on a step, counted on the OUTER edge and
  capped so ring holes stay `SATIN_SHORT_STITCH_AT_MM` apart.
- One bean round the band's outer ring, a needle point on every corner
  (`keyline_bean.stations`): without it a 1 mm tooth is three round-ended
  stitches and has no corners.

**Measured** (band square to the disc's ring).
- Gear: 60 mm 0.86-1.40 (swing 0.54), 100 mm 1.43-2.32 (0.89), 127 mm
  1.82-2.95. At 40 mm the swing is 0.36, under a stitch: stays a ring.
- To-a-T Machine's frame swings 0.14-0.19 (one width, the pro widens it).
  Becker's, MFab's, the Drone's bands pass 7 mm somewhere.
- 22 repo logos, flag ON: only the gear is taken. Plans at 100 mm: MFab,
  Becker, To-a-T, hed_p_e_logo byte-identical; the gear changes; the gear at
  40 mm identical.
- Gear at 100 mm: white 125 satin points -> 126 satin + 221 run; design 13,095
  -> 13,320 stitches.

**How it went wrong on the way** (each caught by looking, none by a number).
- Crosses cut at the art alone: teeth showed but 2 or 3 stitches each,
  unevenly, because stations were spaced evenly round the ring.
- Locked to the teeth but counted on the inner ring: teeth fanned into pairs
  of spokes.
- Stretch boundaries taken at the first reading of a stretch sat 0.04 mm
  round the ring from the tooth: the step is half a reading earlier.

**Open.** Pull on a 0.6 mm tooth is a sew-out question (gate 1). Small gaps
show between a tooth's stitches at 127 mm (the fan). Over about 200 mm the
band passes 5 mm and the rule lets go. The flip is Kent's.

Related: [[hairline-keyline-bean-2026-11-13]], [[eye-first-diagnosis-2026-11-13]],
[[border-from-outline-line-art-guard-2026-10-25]].
