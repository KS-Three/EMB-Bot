---
name: white-rerule-packet-2026-10-25
description: Re-rule numbers for the three white switches. Under border_from_outline ON, sew_enclosed_white ALONE already fills Becker's faces under the outline (0 deg) at 1.00-1.39x OFF CPU; #1076's fields_fill forces the fill tier and costs up to 5.6x (MFab lc); the keyline is inert. tools/enclosed_pro_census.py rebuilds the 10-23 census.
metadata:
  type: project
---

W3-01 (2026-10-25) was planned against 682ff401 to route the BECKER faces
out of the Column lane inside `enclosed_white.py`. #1076 had already done
that on main behind a new OFF switch, `sew_enclosed_white_fields_fill`, so
the foreman turned it into a no-engine-change packet of re-rule numbers.

- **`border_from_outline` (ON since 10-24) changed the premise.** Its
  outline-body branch (`stage7_sequence` "a plain fill under that loop")
  runs before the Column lane. With `sew_enclosed_white` alone, the faces
  already fill under the outline at the word's house angle, 0 deg. The 8.4x
  slowdown is gone without #1076's switch.
- **`sew_enclosed_white_fields_fill` is the costly part.** It forces the fill
  tier and so bypasses that branch. CPU against OFF, at the pro's width:

  | job | white alone | all three ON |
  |---|---|---|
  | Becker chest | 1.15x | 2.13x |
  | Becker beanie | 1.21x | 2.46x |
  | MFab lc | 1.28x | 5.60x (391 s) |

  MFab hat's white stitches under 1 mm go 2,347 -> 5,026 (pro 572). It buys
  only the 22 deg row angle.
- **`enclosed_white_keyline` is byte-identical to white alone on MFab hat**:
  `border_from_outline` takes the band.
- **The census:** calibration 29/31, kappa 0.870. The only misses are Tires'
  loops. The doc's "32/34" does not follow from its own table (30/32).
- **Traps:**
  - Wall time on Kent's shared laptop moved 2-3x run to run (OFF 76-445 s).
    Compare arms by `time.process_time` CPU instead.
  - Name a pro colour block by the thread on TOP. Most-penetrations picks
    his black under-fill.
  - His Becker faces are BLACK under a GREY outline (PES + his own JPG).
  - Studio `max_colors` 6: the white takes a slot, and Golden Tee's teal
    folds into black.

**How to apply:** the angle question is Kent's (0 vs 22 deg). The cheap form
of 22 deg is the angle on the outline-body path, not a forced tier: a
`stage7_sequence` change, a separate PR. Related:
[[white-faces-fill-2026-10-25]], [[enclosed-white-like-pro-2026-10-23]],
[[keyline-band-2026-10-23]], [[border-from-outline-2026-10-24]].
