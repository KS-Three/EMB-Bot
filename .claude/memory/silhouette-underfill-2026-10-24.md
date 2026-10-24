---
name: silhouette-underfill-2026-10-24
description: L9's "pro fills the silhouette" is NOT a per-shape tier rule (kappa 0.170 vs 0.198 best); it is an under-fill of a ring's outline in the colour covering most of it, built OFF as `silhouette_underfill`
metadata:
  type: project
---

L9 asked for a satin->fill TIER flag for MFab's band / Becker's ring. Measured
first (`tools/tier_census.py`, one reader on both DSTs, 21 jobs, 191 non-lettering
shapes; reader 198/213 vs our plan's truth): today kappa 0.170, best width/area
rule 0.198 — it moves only MFab's band, threshold in a 0.4 mm gap (Becker's 2.48
mm ring he satins, MFab's 2.9-3.1 mm band he fills; he satins Tires' 4.3 mm
925 mm2 shape). Premise false; director was told before building.

**Read per COLOUR BLOCK instead** (cover of ring / holes / outline-holes-closed):
MFab black 1.00/0.82/0.88, Becker letter colour 0.75/1.01/0.91, Fremont ground
0.92 — he fills the ring's OUTLINE once underneath in the colour covering most
of it, then sews ring/keyline/letters on top. Drone (gradient) is the row against
(0.51). Kent 10-24: "Build under-fill, OFF" -> `cfg.silhouette_underfill`,
`digitizer_core/silhouette_underfill.py`, doc `docs/silhouette-underfill-2026-10-24.md`.

Proof (both enclosed-white flags ON): MFab hat trims 81->37 (pro 19), st
18,916->17,540 (pro 17,568); LC trims 72->44; Becker +2,225 st (our under-fill
2.8 st/mm2 vs his 2.1 — density, gate 1). White now sews ON TOP of black on
MFab: the reverse of #1059's keyline order, Kent's flip.

**Why:** a stitch-type difference seen in a render can be a LAYERING difference;
per-shape readers average a fill-under-satin into "satin".
**How to apply:** before building a tier rule, read the pro per colour block over
the shape AND its holes. Stage 5 clips later colours by EARLIER artwork — a new
region with the outline polygon would erase everything on top; use the
ground-under path (footprint = artwork, sewn = outline). Cut the outline back off
UNSEWN shapes or it sews over garment the design shows (MFab's keyline when
`sew_enclosed_white` is OFF). Related: [[keyline-band-2026-10-23]],
[[enclosed-white-like-pro-2026-10-23]], [[border-by-size-2026-10-23]],
[[cross-underlay-presets-2026-10-21]].
