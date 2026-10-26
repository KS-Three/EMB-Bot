# Isolated pieces: what makes them, and the fragment fix (2026-10-25)

Queue item W4-02. PR #1072 (`docs/sequence-like-pro-2026-10-25.md`) ranked our
trim gap against the professional's over five hats and put ISOLATED PIECES
second: any greedy tour of our pieces is forced into 129 cuts, of his 96
(+33), "mostly MFab's slivers and white left as fabric". This page reads every
one of those pieces, says which the `sew_enclosed_white` flip (Kent, ON,
2026-10-25, option A of #1087; the flip PR comes after #1057) already removes,
and measures the fix built for what the flip leaves:
`cfg.extra["absorb_fragments"]`, built OFF.

## Instrument

`digitizer/tools/isolated_pieces.py` (new, pinned by
`tests/test_isolated_pieces.py`). One reader on both DSTs, each in its own
frame, trims from the DST, never the PES. It keeps `tools/sequence_pro.py`'s
piece rule and its "within reach" rule (a gap of 3 mm or less whose straight
thread lies on thread, any colour) unchanged; its greedy tour reproduces
#1072's pro column exactly (11 / 6 / 4 / 42 / 33 = 96).

- Per colour block, the reach graph's **components**. One per block is free
  (the colour change cuts anyway): the largest, the body. Every other
  component is **isolated**: any order pays a cut to enter it.
- **Entries**: components over the whole file -- each is entered by a colour
  change or by a cut. Compare files by entries, not by isolated or greedy
  counts: those free one piece per BLOCK, so a file in more blocks reads
  fewer for the same construction.
- For each isolated component of ours: colour, footprint area, width, the
  gap to its nearest same-colour piece and what lies on it, and the stage
  that made it, from the plan runs that sewed it and their regions' meta
  (`white_fragment`: a region lying within 0.3 mm of an unsewn enclosed region
  of its OWN thread, a piece of a field left as fabric).
- **The pro at the same place** (`register_pair`, ours onto his, named by his
  thread on top): `drops`, `merges` (his piece there also covers our nearest
  same-colour piece), `bridges` (joined within reach to another of his
  pieces), `alone` (he cuts to it too), `run`.

Jobs as #1072 and #1091: Fremont hat 92.5 mm, Becker hat large 101.9, MFab
hat 104.9, Precision Drone 62.6, Gaulke roofing hat 114.2; hat preset; the
Studio's request (`tools.pro_pair`); stages 0-4 once per job and white arm,
`plan_stitches` per arm. Tree: `main` 7995d515, rembg from the main checkout
(a worktree has none; MFab's art is the committed corpus crop, G: not
mounted). Arms: `off` = defaults; `cut` = `trim_bury_under_later` +
`cut_every_jump` (#1072's arm); `w0` / `w1` = `sew_enclosed_white` False /
True.

## What makes them (white OFF, today's default)

| job | isolated ours / pro | entries ours / pro | by cause, ours | the pro at the same place |
|---|---|---|---|---|
| Fremont | 3 / 8 | 7 / 19 | segment 1, sliver 1, lettering 1 | merges 1, alone 1, bridges 1 |
| Becker | 6 / 5 | 7 / 10 | lettering 4, white_fragment 2 | lettering alone 3, bridges 1; white_fragment alone 2 |
| **MFab** | **22 / 2** | **24 / 7** | **white_fragment 22** | **merges 17, bridges 5** |
| Drone | 52 / 38 | 61 / 60 | sliver 20, lettering 16, segment 13, white_fragment 3 | sliver bridges 11, alone 6, merges 2, run 1; lettering alone 9, bridges 7; segment bridges 10, merges 2, alone 1 |
| Gaulke | 30 / 32 | 33 / 33 | lettering 30 | alone 24, bridges 6 |
| **five** | 113 / 85 | **132 / 129** | | |

- **In entries the gap is MFab's alone (+17).** Fremont is 12 under the pro,
  Becker 3 under, Drone +1, Gaulke level. #1072's greedy +33 is mostly block
  accounting: the pro sews Drone in 22 colour blocks to our 9, each block's
  first piece free, so Drone reads 52 isolated to his 38 for 61 entries to his
  60. Drone's "slivers" (satin lines of the drone drawing, 2-12 mm from their
  same-colour neighbour) are reached in his file through his other colours
  and his long buried walks (#1072 item 3), not through a construction we lack.
- **MFab's 22 are white fragments of the white keyline** (all `rescued_small_shape`
  sub-floor regions stage 3 kept for their contrast, drawn 0.3-0.7 mm wide,
  each 0.0-0.2 mm from the white field the keyline belongs to). With the field
  left as fabric they are white specks on garment-coloured keyline, each
  sewn as its own run loop and each a cut. The pro sews every one of those
  places as part of his white band: 17 inside his band's piece, 5 joined to it
  within reach.
- **The pro's width census does not separate them by width.** Over 28 of his
  DSTs (1,116 pieces) he sews isolated pieces down to the reader's 0.6 mm
  footprint floor; below ~1.1 mm those are 7-9-penetration knots, not bodies.
  His narrowest sewn satin COLUMN, read as its swing across the column, is the
  usable floor: p01 0.70 mm over 2,141 columns in 868 pieces; eight pieces
  sit at 0.60-0.66 (Fremont's small text, one Proseal column) and one 0.44
  column is a single taper inside a 79.8 mm2 Drone piece.

## What the flip already removes (white ON)

| job | trims w0 / w1 | isolated w0 / w1 / pro | entries w0 / w1 / pro | greedy w0 / w1 / pro |
|---|---|---|---|---|
| Fremont | 51 / 51 | 3 / 3 / 8 | 7 / 7 / 19 | 8 / 8 / 11 |
| Becker | 19 / **38** | 6 / 6 / 5 | 7 / 8 / 10 | 7 / 7 / 6 |
| MFab | 59 / **77** | 22 / **1** / 2 | 24 / **3** / 7 | 31 / 10 / 4 |
| Drone | 106 / 109 | 52 / 52 / 38 | 61 / 62 / 60 | 54 / 54 / 42 |
| Gaulke | 32 / 32 | 30 / 30 / 32 | 33 / 33 / 33 | 30 / 30 / 33 |

(the `off` arm; the `cut` arm reads the same but on Fremont, 5 isolated and 9 entries.)

- **The flip removes all of MFab's isolated pieces (22 -> 1, entries 24 -> 3,
  his 7).** Of #1072's +33 (greedy, cut arm) it takes MFab's 21 of 27; the +12
  left on Drone is the block accounting above.
- **But MFab's trims rise, 59 -> 77.** The cuts move inside the now-joined
  pieces: between pieces 38 -> 16, inside one piece 21 -> 61. Of those 61
  (`tools/inpiece_cuts.py`): shape-to-shape 25 -- 16 of them cut from one
  white fragment to the next, the same fragments, now lying on the sewn band
  but still sewn as separate run loops -- satin splits 28 (11 the field's own),
  fill sections 8.
- **Becker, for the flip PR**: white ON doubles its stitches (8,056 -> 16,921),
  trims 19 -> 38 and exposed travel 14.0 -> 43.8 mm (`tools/travel_cover`,
  bare thread 0.00 both). Not this flag; recorded here because gate 3 will be
  asked of the flip.

## The fix: `cfg.extra["absorb_fragments"]` (OFF)

`digitizer_core/fragment_absorb.py`. The single line is in
`pipeline._plan_stitches`, right after stage 5:
`planned = absorb(planned, cfg, hairline)` (with its import on the line above;
`hairline` keeps the hairline tier's strands its own), so
`config.py` and `stage7_sequence.py` (#1057's) are untouched.

On stage 5's planned regions: a fragment -- narrower everywhere than the
pro's narrowest sewn column (`PRO_MIN_SWING_MM` 0.70, the census's p01), not
lettering -- lying within one thread (`GAP_MM` 0.4, `sequence_pro.THREAD_MM`)
of a BODY of the same thread is unioned into it, artwork polygon and sewing
polygon both, across the gap by the lens of points within half a thread of
both, and is not sewn on its own. A body is a shape in its own right: not
narrow, not lettering, not itself a rescued sub-floor speck (Fremont's
clusters of 26 specks would otherwise grow a body out of a speck); one pass,
nothing chains. A pocket the join walls in that is narrower than the pro's
narrowest column is filled; the body's own holes and any wider pocket stay.

**Built before stage 5 first, and refused by gate 3.** Unioned into the
region list stage 5 reads, the white field's new outline made stage 5
re-plan the black round it (one black letter's holes 6 -> 4), the black fill
re-sectioned, and MFab's exposed travel rose 25.0 -> 41.3 mm on one 17.4 mm
leg over finished black fill. After stage 5, every other colour's planned
polygon is exactly stage 5's.

## Result: OFF | ON | pro

Trims, isolated, entries, greedy and needle-up moves left uncut from each DST
(`tools/isolated_pieces.py`, `tools/sequence_pro.py`); exposed travel
(`tools/travel_cover.py`) and bare thread (`tools/hairline_travel.scan`, the
chaining benchmark's instrument) from each plan. The pro's DST has no travel
runs: n/a.

| job | arm | trims | isolated | entries | greedy | needle-up uncut | exposed travel mm | bare thread mm | stitches |
|---|---|---|---|---|---|---|---|---|---|
| MFab | white ON, OFF | 77 | 1 | 3 | 10 | 22 | 25.0 | 0.73 | 20,267 |
| | white ON, **ON** | **60** | **0** | **2** | **7** | **11** | **22.8** | 0.73 | 19,144 |
| | white ON + cut, OFF | 57 | 1 | 3 | 10 | 0 | 25.0 | 0.20 | 20,306 |
| | white ON + cut, **ON** | **43** | **0** | **2** | **7** | 0 | **22.8** | 0.20 | 19,129 |
| | white OFF, OFF / ON | 59 / 59 | 22 / 22 | 24 / 24 | 31 / 31 | 18 / 18 | 28.1 / 28.1 | 2.35 / 2.35 | 11,125 / 11,125 |
| | pro | 18 | 2 | 7 | 4 | 0 | n/a | n/a | 17,568 |
| Drone | white OFF, OFF / ON | 106 / 106 | 52 / 53 | 61 / 62 | 54 / 55 | 47 / 47 | 35.2 / 35.2 | 4.63 / 4.63 | 14,077 / 14,077 |
| | white ON, OFF / ON | 109 / 109 | 52 / 53 | 62 / 63 | 54 / 55 | 47 / 47 | 35.2 / 35.2 | 4.63 / 4.63 | 14,205 / 14,205 |
| | white ON + cut, OFF / ON | 117 / 117 | 52 / 53 | 62 / 63 | 54 / 55 | 4 / 4 | 35.2 / 35.2 | 1.24 / 1.24 | 14,312 / 14,312 |
| | pro | 58 | 38 | 60 | 42 | 0 | n/a | n/a | 14,552 |
| Fremont | every arm, OFF = ON | 51 (cut 44) | 3 (5) | 7 (9) | 8 (10) | 171 (0) | 45.8 | 0.00 | 18,563 (18,598) |
| | pro | 20 | 8 | 19 | 11 | 0 | n/a | n/a | 17,067 |
| Becker | white OFF, OFF = ON | 19 (cut 22) | 6 | 7 | 7 | 5 (2) | 14.0 | 0.00 | 8,056 (8,080) |
| | white ON, OFF = ON | 38 (cut 29) | 6 | 8 | 7 | 11 (2) | 43.8 | 0.00 | 16,921 (16,957) |
| | pro | 9 | 5 | 10 | 6 | 0 | n/a | n/a | 12,356 |
| Gaulke | every arm, OFF = ON | 32 (cut 47) | 30 | 33 | 30 | 16 (0) | 19.6 | 9.02 (0.20) | 7,881 (8,005) |
| | pro | 41 | 32 | 33 | 33 | 0 | n/a | n/a | 6,138 |
| **five** | white ON, OFF / **ON** | 307 / **290** | 92 / 92 | 113 / 113 | 109 / 107 | 267 / 256 | 169.4 / **167.2** | 14.38 / 14.38 | 77,837 / 76,714 |
| | white ON + cut, OFF / **ON** | 294 / **280** | 94 / 94 | 115 / 115 | 111 / 109 | 6 / 6 | 169.4 / **167.2** | 1.64 / 1.64 | 78,178 / 77,001 |
| | pro | 146 | 85 | 129 | 96 | 0 | n/a | n/a | 67,681 |

- **MFab with the field sewn: 77 -> 60 trims (cut arm 57 -> 43), its last
  isolated piece gone, exposed travel down 2.2 mm, bare thread unchanged.**
  Inside-piece shape-to-shape cuts 25 -> 9; what is left inside its pieces is
  satin splits (30), W4-01's next class. 30 fragments joined (26.8 mm2 of
  artwork) with 27.2 mm2 of lens and filled pockets -- the black hairline
  between fragment and band, which the pro's continuous band covers too.
- **White OFF, the flag is inert on MFab** (DST byte-identical): there is no
  sewn field to join, which is the flip's job.
- **Fremont, Becker, Gaulke: byte-identical DSTs in every arm.**
- **Drone: one 0.28 mm2 fragment** (a 21-stitch run loop) is now sewn inside
  the satin beside it; trims, stitches, exposed travel and bare thread equal,
  and one more isolated piece by the reader (the loop's thread had been
  joining two pieces within reach). A real, small cost; reported, not hidden.

Renders (`docs/renders/isolated-pieces-2026-10-25/`): `mfab_hat_fragments_crop.jpg`
(MFab's M, 24 px/mm) and `..._whole.jpg`, ours registered onto the pro's frame:
main (white left as fabric) | white ON | white ON + absorb | pro. Absorbing a
piece is layout, judged from renders (Kent 2026-10-22).

## Gate checks

- **Gate 3 (no exposed travel added):** five jobs, every arm: exposed travel
  ON <= OFF (MFab -2.2 mm, the rest equal), bare thread equal. The chaining
  benchmark (`tests/test_chaining.py`'s bare-thread reading on its three
  fixtures, chain off and on, white off and on): absorb ON identical to OFF
  in all 24 cells (bare 3.93 / 4.75 / 0.00 mm).
- **Gate 4:** no agreement figure is quoted.
- **Threshold provenance:** `PRO_MIN_SWING_MM` from the census above
  (`python -m tools.isolated_pieces --census`), stated in the module.
- **OFF:** `absorb` returns its input list itself; a synthetic plan's md5 was
  captured on `main` 7995d515's own code and is pinned, Windows-only, beside
  the platform-safe in-process check (OFF equals ON with the pass stubbed),
  `tests/test_cut_every_jump.py`'s pattern.

## For whoever picks this up

- Flip order: this flag only acts where a field is sewn, so it belongs after
  (or with) the `sew_enclosed_white` flip.
- MFab after both: 60 trims to his 18; 30 of them are satin splits inside one
  piece (`tools/inpiece_cuts.py`), the field's own keyline band among them.
- Becker under the white flip doubles its stitches and triples its exposed
  travel; worth a look before that flip lands.
