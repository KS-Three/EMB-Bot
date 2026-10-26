---
name: mfab-underfill-panels-2026-10-25
description: Kent's "chaotic satin between and around MFab's letters" is reachable as one flip (silhouette_underfill + white + keyline + new silhouette_underfill_panels, all OFF): pro layering on hat and LC. Under-fill alone used to drop every keyline-held body in stage 5 (_split_clip, by band ink); fields_fill pre-empted the outline loops.
metadata:
  type: project
---

2026-10-25, branch `claude/mfab-underfill-panels`. Doc
`docs/mfab-underfill-panels-2026-10-25.md`, crops
`docs/renders/mfab-underfill-panels-2026-10-25/`.

**The pro's MFab:** black tatami under the whole silhouette, then the white
keyline as satin loops ON it, then AND WELDING / LLC as black satin AFTER the
white, on a white panel CLOSED under them (white under 1.000, black 0.13-0.15).

**Three fixes, everything OFF at defaults:**
- (A) `silhouette_underfill` alone, with the keyline unsewn, cut the outline
  into band + bodies. Stage 5 `_split_clip` (both clip flags default ON) kept
  only the piece with the HOST's ink and dropped every body uncounted: MFab LC
  had 26 merged shapes sewn by nobody. Now the pieces are judged on artwork +
  outline and sew as host fill at one angle.
- (B) `sew_enclosed_white_fields_fill` forced the fill tier on the white
  keyline and skipped the outline loops. `_white_field_fill` now declines an
  outline or a keyline band.
- (C) The new `silhouette_underfill_panels`: riders (text-tagged, host thread,
  in a white field's hole, word mostly not outline bodies) are not merged, sew
  in a layer after the white, and get a closed white panel.

**d2+panels against the pro (hat / LC):**
- white under the small letters 0.973 / 0.977;
- black under them 0.158 / 0.137;
- black footprint 3,285 / 2,811 (pro 3,258 / 2,773).

It costs +3.2k stitches and +20-23 trims against d2.

**#1064's 17,540/37 vs today's 12,308/54** was a flag set, not a regression:
the flip sheet ran under-fill on `_WHITE_SEWN`.

**Traps:**
- A lane has no rembg venv. Point `stage1_photo_prep.REMBG_VENV_PYTHON` at the
  main checkout's, pin the timeout at 900 s, and check
  `PHOTO_BACKGROUND_REMOVED` per arm.
- Never edit engine files while an arm chain runs: each arm is a new process,
  and it imports what is on disk.
- `layers.py` "white under small" must be read per block: LLC sits on the
  second white block.

**How to apply:** measure layering with `panels/scripts/panel_metrics.py` (in
the director's evidence folder). Residual corner spikes are stage6_border's
(apex-cut, task 10).

Related: [[silhouette-underfill-2026-10-24]], [[white-rerule-packet-2026-10-25]],
[[keyline-band-2026-10-23]], [[border-from-outline-2026-10-24]].
