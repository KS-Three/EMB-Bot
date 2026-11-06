# MFab LC's AND re-checked on main: the hollow A is gone, no flag built (2026-11-06)

A brief dated from the 2026-10-25 measurement (`docs/text-cluster-part-touching-2026-10-25.md`)
asked for a fix, under a new OFF flag, to the AND of "AND WELDING LLC" on MFab left
chest (96.7 mm, pair `mfab_lc`), whose A sewed as a hollow bean outline (222 run
points, no satin) while the pro sews A, N and D as black satin. **On today's main
(7ee2d98a) there is nothing to fix.** Three flips landed between the brief's
measurement and today, and the first two each close it on their own.

## Why the fault cannot happen on main

1. **`bean_ink_outlined_letters` ON since 2026-10-27** (Kent's flip, PR #1128
   built it; `docs/outlined-bean-ink-2026-10-27.md`). It is exactly the brief's
   mechanism: `ink_path.read_cluster_ink` grounds on the pixels 0.8 mm from the
   members, which on MFab is the black body, so its ink axis points at the WHITE
   keyline round each letter and the read traces that line 0.14-0.15 mm OUTSIDE
   the letter (A 0.417 mm, N 0.441; 0.4-1.7% of the spine inside). The flag
   drops any read under half inside (`beanletters.INK_INSIDE_MIN_SHARE` 0.5);
   the letter sews as the satin rider it is.
2. **`bean_only_lines` ON since 2026-10-27** (PR #1161). `tag_bean_letters`
   returns before reading any cluster: a letter is never a bean on main
   (`bean_rule`: 0 of 251 small letters in the pro's 17 files). The outline
   read is not even taken.
3. **`text_cluster_part_touching` ON since 2026-10-27**, the flag the brief said
   must wait. With both of the above it adds the N to the cluster and the N sews
   satin like the A.

## Measured today

`tools.pro_pair.digitize` on `testdata/art/logo_mfab_lc.png` at 96.7 mm,
`left_chest`, the Studio's request, main's defaults, this checkout's rembg venv
in reach (not used: the LC is `CLASSIFIED_GRADIENT`, segmenter classical,
8.0 px/mm, 68.6 s).

| | value |
|---|---|
| bean-tagged regions, whole design | **0** |
| plan md5 / stitches / trims | `7e924603` / 18,145 / 21 (pro 15,786 / 36) |
| A `Sbd0d3e9f` | thread 0020, 24.4 mm², `text_cluster_id` TC891854ec, **satin 126 points**, underlay 17 |
| N `S81d1d4a6` | thread 0020, 21.8 mm², same cluster, **satin 110**, underlay 17 |
| D `S6815bbe5-2` | thread 0020, 20.9 mm², same cluster, **satin 120**, underlay 15 |

The 10-27 doc's ON arm had the A at 116 crosses against the pro's 114; the 10-25
fault was 44. Crop, art over ours, each in its own frame:
`docs/renders/mfab-and-recheck-2026-11-06/lc_AND_art_ours.png`. The three-way
sheet with the pro's tile is local only, `pro_renders/mfab-and-recheck-2026-11-06/`
(Kent 2026-10-27: no new pro renders under `docs/`). Read against the pro's crop
there, A, N and D are black satin in both files; the pro's white keyline is a
wider, flatter satin than ours, and the D's counter in ours is a white satin
column where his is a fill. Neither is the brief's defect.

## Which paired jobs draw outlined lettering (the brief's item 2)

Every line on the lettering board (`testdata/lettering_board_lines.json`, 18
pairs, 42 lines), each prepped at the pro's width in the pipeline's own frame
and cropped from the prepared raster (sheets in `pro_renders/mfab-and-recheck-2026-11-06/<slug>.png`,
local). Read by eye; the numeric read tried beside it (crop-rim ground) is not
the reader's and is not quoted.

| pair | lines | outlined? | construction |
|---|---|---|---|
| mfab_hat, mfab_lc | MFAB; AND WELDING LLC | **yes, both lines** | black letters on a black body, each ringed by a thin white keyline (the reader's ground = the letter's colour) |
| becker x5 | BECKER; MARINE | **yes** (repo record: `sew_enclosed_white` fills "Becker's faces", `legibility.py` "outlined BECKER") | white letter faces inside a black outline; 12.8-28.5 mm tall, never near the 0.5 mm bean line. The fallback art is 146 px wide, so the sheet is blank for these five |
| precision_drone | PRECISION | **bevelled**, not keylined | chrome letters with dark bevel lines inside them: the `INK_SHAPE_MAX_RATIO` case (PR #944), a different trap |
| precision_drone | THERMAL; AND DRONE | no | solid orange / solid grey on a grey ground |
| hotel_fremont x2 | all six lines | no | solid black or tan on white |
| proseal_hat, proseal_beanie | all three | no | solid black on white |
| gaulke_roofing x3 | both | no | solid black on white |
| tires_hat_3d | Tires | no | solid black script on white |

So the keyline construction that fooled the ink reader is MFab's alone among
the pairs with small lettering; Becker's outlined letters are far too tall to
reach the bean decision, and on main nothing reaches it anyway.

## What this leaves

- No code change, no flag, no md5 pin: the engine is as it was.
- If `bean_only_lines` is ever flipped back OFF, `bean_ink_outlined_letters`
  still stands between MFab's keyline and the bean tagger; its test
  (`tests/test_bean_outlined_ink.py`) draws the construction and reads it with
  the real reader on both arms.
- The brief's "222 run points" figure, if quoted again, is the 2026-10-25 arm
  (19 + 191 points on the A plus its N top) and carries `jump=True` on the
  lift into each run; a tally that skips jump runs reads it as unsewn (trap
  recorded in `docs/outlined-bean-ink-2026-10-27.md`).
