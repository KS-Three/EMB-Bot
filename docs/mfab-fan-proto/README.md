# MFab's A counter as one fanned satin: prototype (2026-11-14, not shipped)

Kent's word on 2026-11-14 was "I want it exactly like the pros". On MFab hat at 104.9 mm the A's
white counter (S6f70d810, a triangle with a narrow arm up its right side, 3.35 mm inscribed) is
one fanned satin in the pro's file. Ours is a fill: #1519's `border_significant_ring_room` took
off the bean loop, and the fill stayed. These scripts are the offline prototype. Nothing here is
wired into the engine.

## The pro's stitches on the counter (registered at IoU 0.99, `pro_tri.py`)

- **Underlay.** About 30 white zigzag stitches (3.5-4 mm, alternating about 22° / 177°), then a
  short run of 0.7-0.9 mm stitches up into the narrow tip, and a travel back to the base.
- **Top.** ONE satin from the base to the tip. The crosses turn steadily: 3° at the base, about
  40° mid-shape, 80-90° in the narrow arm, where they run along the arm. Their length falls
  from **5.73 mm at the base** to 1.5 mm at the tip.

## What the prototype does (`fan_proto.py`)

- **The wedge.** The tip is the sharpest convex corner of the ring simplified at 0.4 mm; the base
  corners are the next two. The rails are the two boundary paths from the tip to the base
  corners.
- **The satin.** Crosses pair the rails by arc-length fraction, so at the base the cross is the
  base edge, and toward the tip it shortens. It sews satin from the base to the tip, alternating
  rails, each end pushed out by the fabric pull (the magnitude is not touched, gate 1).
- **The underlay.** Zigzag from the tip to the base on rails inset 0.4 mm, about 2 mm apart.
- **The guards.** It refuses when a cross leaves the shape, or when a cross passes the ceiling.

## Against the pro (`fan_sheet.py` → `eye_pairs_out/mfab-triangle-1114/sheets/fan_proto_104.9.png`)

By eye it is far closer than the fill: one column, level crosses at the base, each stopping on
the hypotenuse in steps as his do. Two differences are left:

1. **No pivot in the narrow arm.** His crosses turn toward vertical (80-90°) and run along the
   arm. Ours only tilt, because paired rails keep the crosses near-parallel. Copying him needs a
   pivoting sweep, not paired rails.
2. **The ceiling.** Our base cross is 5.37 mm, his 5.73 mm. Both are over
   `machine.SATIN_MAX_WIDTH_MM` = 5.0, a physical constant ("Python-side only until its own
   sew-out").

## The ceiling (gate 1, on Kent's list)

The Director's call 2026-11-14 is A: build the fan OFF, held to 5.0 mm, with the ceiling as a
parameter that reads the machine constant. At 5.0 this counter stays fill; at 5.7 it gets his
fan. **5.7 mm is not shipped: gate 1.** The pro's own sewn file crosses 5.73 mm there; whether
ours may is Kent's call, after a sew-out.

## Files

- `fan_proto.py`: the construction.
- `fan_try.py`: tries it on a corpus design's small enclosed counters.
- `fan_sheet.py`: fill | proto | pro at the counter.
- `pro_tri.py`: reads the pro's stitches.

They read the apex corpus pickles (`eye_pairs_out/jag-source-1113/apex-corpus/`, gitignored) and
the scratch helpers `gain_sheets.py` / `tri_sheet.py`, which are copied here too.
