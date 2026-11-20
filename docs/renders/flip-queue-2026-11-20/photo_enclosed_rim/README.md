Moved: 1 of 44 runs; pictured: 1.

# `photo_enclosed_rim`: flip-readiness evidence, 2026-11-20

**What it does** (built OFF 2026-11-06, `stage2_photo_segment.enclosed_rim`).
On the photo lane, rim pixels of an ENCLOSED ground (bg-coloured and not
border-connected, such as MFab's white keyline) join that ground's
population before the min-detail floor. Without the flag, the floor hands
those rim fragments to the neighbouring ink. It was aimed at MFab's white
keyline at small sizes.

**The sweep.** All 44 runs (18 tripwire placements and 26 corpus fixtures)
finished with 0 errors. One run moved:

- `corpus:photo/summit_badge.png` (81 mm, hat_front): stitches 28,990 -> 27,563
  (-1,427), trims 33 -> 32, jumps 117 -> 112, needle-up 902.7 -> 822.7 mm.

`mfab_hat` and `mfab_lc`, the placements the flag was built for, are
**byte-identical** OFF and ON on today's engine. The memory note
(`robust-pc-sweep-2026-11-13`) also records a regression ON: one black patch
at 35 to 37 and 40 mm on MFab. Those sizes are outside this population, so
the sweep neither confirms nor clears that regression.

**By-eye read against the original art** (`summit_badge.png`, ORIGINAL |
BEFORE | AFTER):

- summit_badge: **same.** I diffed the two renders after a 4 px blur. The only
  change is a few pixels along the ragged outer edge of the grey ground disc.
  The ring, the X arms, the centre and the lettering do not change. Neither arm
  is closer to the art: both sew the art's full-square gradient ground as a
  ragged disc, and both lose the X arms over the dark half. The 1,427 fewer
  stitches come from that ground edge.

No mover reads worse. No mover reads better either.

`summit_badge.png` here is our own render of the committed synthetic fixture
`digitizer/testdata/photo/summit_badge.png`, shrunk to 1800 px wide.
