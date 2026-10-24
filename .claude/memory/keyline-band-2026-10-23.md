---
name: keyline-band-2026-10-23
description: L3 keyline band — `enclosed_white_keyline` OFF: a satin loop round each letter hole on the ARTWORK polygon; MFab ON 25,512 → 19,214 st (pro 17,568), band sub-1 mm 2,816 → 144; Becker untouched
metadata:
  type: project
---

Built 2026-10-23 (L3, unblocks `sew_enclosed_white`, which Kent held OFF over
MFab's 1.45x stitch count). Flag `cfg.enclosed_white_keyline`, built OFF, read
only on a `sew_enclosed_white == "field"` region that is a keyline
(`stage6_border.keyline_band`: holes, >= 0.9 of it within 2.1 mm of a hole).

- **Where the sub-1 mm stitches were:** the satin tier's skeleton on MFab's
  white band (868 mm², 17 letter holes, medial width p25 0.72 / p50 1.20 mm):
  253 columns, 2,181 short crosses + 522 underlay + 100 hairline runs.
- **The pro's band (one zigzag reader, his DST):** MFab white block = satin
  round each letter, cross median 2.33 (p25 1.43) + one holeless tatami under
  AND WELDING LLC with the letters on top; Becker = body fill under, keyline
  satin 2.09 / 2.06 on top. `machine.KEYLINE_WIDTH_MM` 2.1.
- **Two traps hit, both in the PR body:** (1) stage 5's sewing polygon for a
  FRONT-layer band is grown under every later letter -- MFab's held 224 holes
  (868 → 1,418 mm²); loops on it gave 55 runs. Read the ARTWORK polygon.
  (2) band and letters are vectorized apart, so `reach.covers(cross)` failed on
  hairline gaps: 1,702 clamped crosses, 687 under 1 mm. Closing the reach by
  2 x `simplify_tol_mm` (the seam tolerance) left 53 clamped, 0 under 1 mm.
- **Not done, named:** convex letter corners fan (far rail sparse; the pro
  mitres); AND WELDING strip is loops, the pro fills it holeless; 14 jumps
  between loops (joining them = links under later thread, gate 3); Becker's
  bodies sew satin where the pro fills under the keyline (not a keyline band,
  byte-identical ON).
- A scratch file named `numbers.py` beside a script shadows the stdlib and
  kills numpy's import -- a run "finished" with no output.

**How to apply:** flipping it is Kent's (layout, ruling 2026-10-22). Related:
[[sew-white-areas-2026-10-21]], [[enclosed-white-like-pro-2026-10-23]].
