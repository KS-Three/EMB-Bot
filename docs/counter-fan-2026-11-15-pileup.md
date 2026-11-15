# The counter fan's pile-up and underlay, fixed (2026-11-15, still OFF)

Kent's review card for `counter_fan_satin` (#1559) named two ways the fan was still not like the
pro's. Both are fixed in `stage6_counter_fan` before the flip.

## 1. The pile-up where the arm's crosses pivot

The pro's file (MFab hat, the A's counter, registered) gives the measure.

| at 90 mm | his | ours, #1559 | ours, now |
|---|---|---|---|
| satin needle points | 51 | 94 | 48 |
| most penetrations within 0.3 mm | 3 | 7 | 3 |

The cause was the emission, not the pairing.

- **The pairing already matched his.** His inner end climbs about 0.12 mm a stitch and stops
  0.23 of the inner rail short of the tip; ours did the same.
- **The emission did not.**
  - The stations sat at HALF the satin spacing, and each wrote both ends in the order outer,
    inner, inner, outer.
  - That put two penetrations on each rail per station, joined by a short step stitch along the
    rail. Where the inner rail moves slowly, they bunched.
- **Now** the stations sit at the satin spacing, and the rails strictly alternate, as
  `stage6_satin` writes its own satin (A1, B1, A2, B2). Every stitch is a cross.

## 2. The underlay

His zigzag legs advance 0.6-0.9 mm of the outer rail each. Ours advanced 2.0 mm, a third of his.
`FAN_UNDER_PITCH_MM` is now 0.75.

| underlay needle points | his | ours, #1559 | ours, now |
|---|---|---|---|
| at 90 mm | 17 | 6 | 13 |
| at 75 mm | 17 | 5 | 11 |

## Against the pro: angle error, `apex_pro.measure_window`

| width | today (no fan) | fan, #1559 | fan, now |
|---|---|---|---|
| 90 mm | 32.2° | 7.3° | 7.6° |
| 75 mm | 67.1° | 6.9° | 6.8° |
| 104.9 mm, cap 5.7 (picture only, NOT shipped) | 50.3° | 8.4° | 8.6° |

- The angle error is flat, within 0.3°; the construction's angles were already his.
- What moves is the crowding and the needle count, both now at his.
- These are offline captures; the window is a little wider than #1559's, so "today" reads 32°,
  not 30°.

Sheets (gitignored): `digitizer/eye_pairs_out/flips-1115/counter/fan_eval_mfab_hat_{75,90}.png`,
laid out art | today | fan #1559 | fan now | pro.

**Still not his:**
- His underlay is a zigzag from the base to the tip with a run back. Ours zigzags from the tip to
  the base and needs no run back.
- His satin ends sit about 0.28 mm outside the edge in the body and 0.15 mm at the tip. Ours sit
  at the fabric's pull, 0.4 mm on this hat; the pull is gate 1 and is not touched here.
