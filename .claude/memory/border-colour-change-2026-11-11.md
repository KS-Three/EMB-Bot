---
name: border-colour-change-2026-11-11
description: Kent's low_poly pin 2 ("border stitches that contain colour changes"): no border there, a drawn black line re-snapped to grey by revalidate_threads; pro borders per colour patch, ends meet inside a column; resnap_hairline_never_lightens built OFF
metadata:
  type: project
---

2026-11-11, defect-marks sitting 2, `C_low_poly` pin 2 (nitpick): "the change in
bean stitch bordering looks off ... investigate how to do border stitches that
contain colour changes". Write-up: `docs/border-colour-change-2026-11-11.md`.

- **No border on that row.** 0 runs with role `border` / `edge_cap`; flipping
  `border_by_size`, `border_from_outline` changes nothing. The "bean border" is the
  art's drawn outline, thin satin regions (1.05 mm columns).
- **The grey is a re-snap, not a seam.** The art's line is black on every pixel
  (darkest 0, 63 of 63 grey-stretch samples). `revalidate_threads` took a hairline's
  halo median and moved `S217d4f0e` to 1972 Silvery Grey (43.6 dE00 from black):
  18 mm of fin top, two visible ends, one of them the pin. 7 outline pieces were
  re-snapped, 6 only Black to Blackberry (12.2 dE00).
- **The pro borders per colour patch.** 18 pro pairs, `border_pro` v3: 11 have a
  different-colour handover (44 total), ends meet within a column (median
  0.97 mm vs columns 1.1-3.5 mm), 8 border one fill in 2+ colours, 3 files no
  border at all. Ours: a generated ring crossing a seam is rare (3 ends, 1 row
  of 21).
- **Built, default OFF:** `resnap_hairline_never_lightens` (a line of at most
  `bean_rule.LINE_MAX_MM` keeps its stage-2 thread when the re-check would
  lighten it). OFF byte-identical to the stored capture; ON moves 5 of 21 rows,
  low_poly +339 stitches, trims 91 to 85, blocks 6 to 8 (not isolated why).
  CLOSED 2026-11-11: Kent chose fix B (`line_chain_one_thread`) over this flag, then
  ruled fix B OFF ("Keep off, very little improvements were made, if any."). Both
  flags stay OFF; no flip, no join-overlap (C) work.

**Why:** thread colour for a thin line was chosen from its own pixels, which for a
hairline are halo; the cure is the ink, not the median.
**How to apply:** do not blame `border_by_size` for a colour break in a drawn
line; check `thread_resnapped_de00` on the region first. The silhouette
handover counter in the doc is crude, read it as an upper bound.
Related: [[border-by-size-colour-seams-2026-10-28]], [[bean-census-2026-10-27]],
[[defect-marks-sitting-2-2026-11-11]], [[border-seam-ownership-2026-09-09]].
