---
name: enclosed-white-like-pro-2026-10-23
description: Census of every enclosed white on the seven paired jobs against the pro's DST — the pro sews bodies/fields/bands and leaves letter counters open, which is the rule sew_enclosed_white already carries (32/34 rows); MFab's 45% overshoot is band CONSTRUCTION (253 satin columns on a ring with 17 holes), not selection. Read before touching sew_enclosed_white or pricing MFab.
metadata:
  type: project
---

Built 2026-10-23 after Kent held `sew_enclosed_white` OFF over MFab (25,512 ON vs
pro 17,568). Doc: `docs/enclosed-white-like-pro-2026-10-23.md`; crops
`docs/renders/enclosed-white-like-pro-2026-10-23/`.

- **Instrument:** our OFF DST registered to the pro's (`pairframe.register_pair`),
  each enclosed polygon carried into his frame, eroded 0.35 mm, read against a
  10 px/mm raster of his stitch lines. Calibrate on our own sewn regions first:
  98.4-100% covered on every job, so 1.0 = sewn, 0.1-0.4 = bare with satin bleed.
- **The pro's rule is by ROLE, not size:** hollow letter bodies (Becker, 118-218
  mm²), keyline bands and fields (MFab 868 mm², 11 mm²) sew; letter counters
  (Becker, Gaulke, 0.6-11 mm²) stay open; counters inside a sewn band sew with
  it (MFab's four). Tires' two script loops (28, 43 mm²) are counters he leaves
  open; the text cluster tags the one-blob script word with nothing, so we sew
  them. Pinned as a strict xfail. An area-ratio rule would separate Tires but
  would leave a white star inside a black badge unsewn — not built.
- **MFab's band already sews SATIN** and that is the cost: medial axis breaks
  at every letter corner into 253 columns (median 24 pts), 203 underlay runs,
  159 travels, 34 trims: 11,204 st where one pass at 0.4 mm is ~1,800. Pinned to
  FILL it is 23,564 (719 fill runs). The pro's white is 6,672 st, which only
  fits one layer if it runs holeless UNDER the black letters (R13).
- Drone's pro coverage is unreadable for this question (he relaid the text).
- **Traps:** a `Monitor` expires at 5 min regardless of `timeout`; reading a
  pro file off G: died with ENOSPC when C: had 0.35 GB free — read
  `scratch_kent/Embroidery Files` via `PRO_PARITY_ROOT`; under 48 sibling
  Python processes one MFab cell took 12 min, Becker 4.

**How to apply:** do not re-census selection; the next MFab lever is a keyline
satin with the band's edges as rails or the R13 under-fill, both stage 5/6.
Related: [[sew-white-areas-2026-10-21]], [[flip-sheet-2026-10-23]],
[[layout-judged-in-preview-2026-10-22]].
