# `lettering_columns_apex_guard`: apex_cut's losses back to OFF, its gains kept (2026-11-14)

A guard for `lettering_columns_apex_cut`. Both stay OFF. The guard is
`cfg.extra["lettering_columns_apex_guard"]`, read only while apex_cut is on;
the code is `outline_cut._apex_guard_refuses`, with its notes at
`_APEX_GUARD`. It follows the OFF | ON corpus table in
`docs/apex-cut-corpus-2026-11-14.md` (#1489): 43 designs, 10 better, 4 worse
(outline_lineart_logo badly, k_line, precision_drone, mfab_lc) and 1 mixed
(and_pizza).

**Verdict:**
- **Gains kept.** All 10 gains keep their gain: Becker ×5 and ProSeal ×2
  are md5-identical to ON. Bridge ×2 and duotone keep the gaining tip
  exactly as ON sews it, window for window.
- **Losses back to OFF.** outline_lineart_logo and k_line are md5-identical
  to OFF. Drone's N top and mfab_lc's W apex are back to OFF in their
  windows. and_pizza is OFF exactly: its corner fan goes, and so does its
  Z-joint cure.
- **No new change.** The 14 unchanged lettering designs stay
  byte-identical; the 4 with no lettering shape were not run.

## What the losses share

**Read tip by tip, not design by design.** The corpus pickles hold each
design's regions and runs. Every shape apex_cut changed was re-cut with the
lane's own arguments, and each merged tip was drawn beside its OFF and ON
stitches (`eye_pairs_out/apex-guard-1114/tips/`, primary checkout,
gitignored).

**The record trap.** A cross through the crotch is stored as TWO "apex"
records, one each side of the crotch. Summed per tip, Becker's M is 1.69 W
(6.4 mm), not 0.52 and 1.17.

**Two kinds of tip, neither of them a gain.**

1. **A stroke under one satin cross** (`machine.SATIN_MIN_CROSS_MM`, 0.5 mm).
   - outline_lineart_logo's "letters" are the white rings around its black
     letters: 0.18-0.19 mm wide, tagged as text.
   - Merged at the rings' notches, they walked long bars across the black
     letter inside.
   - Every gain's stroke is 0.69 mm or wider.
2. **A cross found only by sliding to the walk's limit.**
   - The cut sits below the crotch (an `apex_stub`), and the cross takes at
     least `APEX_GUARD_SHARE` (0.9) of the limit, `min(2.4 W, 7 mm)`.
   - The walk stepped off the crotch until a cross first fitted, so the
     limit picked that cross, not two strokes closing. It is a stroke end,
     not a V.
   - The losses read 0.96-1.00:
     - k_line's K foot and N;
     - Drone's N top (two long stitches across the stem);
     - mfab_lc's W middle apex and N tops;
     - duotone's "2" foot;
     - and_pizza's Z joints.
   - The gains that slid read 0.39-0.76: Bridge's crossed blocks, duotone's
     N, Becker LC's M.

**The share alone separates nothing.** Crosses cut through the crotch sit at
0.89-1.00 of the limit too, Becker's M and ProSeal's A among them, so the
guard judges the share only on a cut that slid.

**A refused crotch tries no other tip,** so the letter cuts exactly as it
does with apex_cut OFF.

## The cost: and_pizza's Z cure

Each Z's two joints are one shape turned 180°. ON sews the bottom-left joint
flat and square (Kent's pins), and the top-right one fans. No rule on the tip
can keep one and refuse the other. What differs is the sewing order at the
joint, the Column lane's walk, which the jag-source lane owns. Its Z cure can
come back once the top-right fan is fixed there.

## The table (OFF | ON | ON+guard)

How the table was made:
- **Tree:** this branch (origin/main 1523008e plus the guard); OFF and ON
  are the corpus pickles from d0b4981a.
- **Same request:** every ON+guard run used the corpus's own request
  (`pro_pair.request`) with the guard added.
- **The drift check:** k_line, outline_lineart_logo, and_pizza,
  chalkboard and silhouette come back md5-identical to the old OFF, so the
  tree's drift since d0b4981a changes nothing here.
- **"own" in the md5 column:** a letter with one tip refused and another
  kept sews neither as OFF nor as ON. Those rows were read window by
  window: each tip's 8 mm window matches OFF where refused and ON where
  kept (Bridge ×2, duotone, Golden Tee exactly).
- **Sheets:** `eye_pairs_out/apex-guard-1114/sheets/<design>.png`, the
  whole design OFF | ON | ON+guard, then each tip's window.
  `sheets/dir/mfab_lc.png` has the direction view, where black on black
  hides the change.

| design | ON by eye | stitches OFF / ON / ON+guard | ON+guard md5 | what it keeps |
|---|---|---|---|---|
| becker_beanie | better | 13902 / 13921 / 13921 | = ON | keeps ON |
| becker_chest_small | better | 10339 / 10364 / 10364 | = ON | keeps ON |
| becker_hat_large | better | 16289 / 16320 / 16320 | = ON | keeps ON (the M's V) |
| becker_hat_small | better | 10576 / 10574 / 10574 | = ON | keeps ON |
| becker_lc_large | better | 14951 / 14700 / 14700 | = ON | keeps ON |
| bridge_hat | better | 8569 / 8581 / 8572 | own | keeps both crossed-block gains; the at-limit tip back to OFF |
| bridge_lc | better | 10998 / 10990 / 10993 | own | keeps the crossed-block gain; the at-limit tip back to OFF |
| duotone_poster | better | 52310 / 52288 / 52291 | own | keeps the N's gain; the "2" foot back to OFF |
| proseal_beanie | better | 7785 / 7805 / 7805 | = ON | keeps ON |
| proseal_hat | better | 6434 / 6485 / 6485 | = ON | keeps ON (the A's apex) |
| lt_and_pizza | mixed | 2454 / 2539 / 2454 | = OFF | **OFF** (the corner fan and the Z cure both go) |
| lt_k_line | worse | 3372 / 3341 / 3372 | = OFF | **OFF** |
| mfab_lc | worse | 17897 / 17832 / 17893 | own | W middle apex back to OFF's pattern; the N's two crotch-cut tips as ON (pinhole unreadable black on black) |
| outline_lineart_logo | worse | 14496 / 14183 / 14496 | = OFF | **OFF** (hairline rings) |
| precision_drone | worse | 14984 / 14957 / 14975 | own | the N top's long stitches back to OFF; the N's lower tip as ON ("fine") |
| arabic_calligraphy | same | 5457 / 5457 / 5457 | = OFF = ON | unchanged (ON = OFF) |
| chalkboard_lettering | same | 28285 / 28293 / 28285 | = OFF | OFF (hairline) |
| comic_halftone | same | 57988 / 57988 / 57988 | = OFF = ON | unchanged (ON = OFF) |
| devanagari_logo | same (no lettering) | 4960 | not run: no lettering shape reaches the lane | |
| distressed_grunge | same | 16974 / 16974 / 16974 | = OFF = ON | unchanged (ON = OFF) |
| gaulke_roofing_beanie | same | 7679 / 7675 / 7675 | = ON | as ON |
| gaulke_roofing_hat | same | 7494 / 7512 / 7512 | = ON | as ON |
| gaulke_roofing_lc | same | 5852 / 5870 / 5870 | = ON | as ON |
| goldentee_hat | same | 13636 / 13642 / 13636 | own | the hairline tip back to OFF, the script join as ON |
| hotel_fremont_hat | same | 16106 / 16106 / 16106 | = ON | as ON |
| hotel_fremont_patch | same | 15061 / 15068 / 15068 | = ON | as ON |
| kanji_brush | same | 13004 / 13004 / 13004 | = OFF = ON | unchanged (ON = OFF) |
| kanji_seal | same (no lettering) | 10996 | not run: no lettering shape reaches the lane | |
| lt_ahora | same | 9262 / 9262 / 9262 | = OFF = ON | unchanged (ON = OFF) |
| lt_bukit_asam | same | 2046 / 2046 / 2046 | = OFF = ON | unchanged (ON = OFF) |
| lt_but_seriously | same | 1980 / 1980 / 1980 | = OFF = ON | unchanged (ON = OFF) |
| lt_dot_music | same | 1529 / 1529 / 1529 | = OFF = ON | unchanged (ON = OFF) |
| lt_hed_p_e | same | 3849 / 3849 / 3849 | = OFF = ON | unchanged (ON = OFF) |
| lt_jakarta | same | 2966 / 2966 / 2966 | = OFF = ON | unchanged (ON = OFF) |
| lt_n_sync | same | 2479 / 2479 / 2479 | = OFF = ON | unchanged (ON = OFF) |
| mfab_hat | same | 20849 / 20882 / 20876 | own | mixed per letter (black on black, no visible change either way) |
| neon_outline_sign | same (no lettering) | 2515 | not run: no lettering shape reaches the lane | |
| silhouette_logo | same | 25036 / 25032 / 25036 | = OFF | OFF (all tips slid to the limit) |
| tires_hat_3d | same (no lettering) | 4552 | not run: no lettering shape reaches the lane | |
| toat_beanie | same | 18472 / 18472 / 18472 | = OFF = ON | unchanged (ON = OFF) |
| toat_machine_beanie | same | 18399 / 18399 / 18399 | = OFF = ON | unchanged (ON = OFF) |
| toat_machine_hat | same | 18970 / 18970 / 18970 | = OFF = ON | unchanged (ON = OFF) |
| vintage_engraved_badge | same | 33241 / 33243 / 33246 | own | mixed per letter, nothing readable |

## Not settled here

- **mfab_lc's N-foot pin-hole.** The N keeps two through-crotch tips as ON sews them. Whether the pin-hole the corpus saw persists cannot be read on black thread; the direction view shows the N mixed.
- **The flip.** Turning `lettering_columns_apex_cut` and the guard on is Kent's call.
