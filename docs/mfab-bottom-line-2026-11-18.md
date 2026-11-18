# MFab hat bottom line (AND WELDING LLC): why it reads mushed (2026-11-18)

Prime-grader fault: thread outlines thin and ragged, black piling over letter edges.
Measured on main `ea4257d0`, `mfab_hat` at 104.9 mm, hat_front, `pro_pair.digitize`
(20,564 stitches, 25 trims). Nothing built; no flag.

**What sews the line.** Three blocks. (0) black body fill `Sb250f949`. (1) white thread:
`S1a1cc475`, one 772.7 mm2 keyline network, sewn as FILL rows (2,510 fill points in the
line) plus a few satin pieces. (2) black thread again: each small letter is ONE region
(`Sd2b8aef9` etc., 20-33 mm2) sewn as ONE satin (underlay + satin); the A counter and a
few specks are separate small regions. So "one clean piece per letter" already holds.

**Strokes at 105 mm.** Black letter strokes 1.2-1.4 mm (measured satin width 1.2-1.4,
max inscribed width 1.5-2.2 incl. junctions). The white keyline ring is about 0.9-1.2 mm,
starting 0.3-0.6 mm out from the letter edge.

**Where black lands on white.** Black is sewn last. Rasterising the block-2 thread at
0.4 mm over the white polygon in the band: 52.8 of 303.8 mm2 (17%) of the white is covered
by black thread, as a continuous ~0.2 mm rim round every letter (cyan rim in the check
image, not committed). Polygon overlap itself is tiny (0.0-0.8 mm2 per letter), so the rim
is rail pull compensation (0.2 per side) plus half a thread width, not a shape error.

**Tried.** Letting lettering use `satin_seam_hold` (remove the `text_candidate`
exemption in `stage7_sequence.seam_ground`): byte-identical, 20,564 stitches. Lettering
goes through the column lane, which does not use that hold.

**Verdict.** Real in the stitches, but it is the pull-comp / thread-width limit acting on
a ~1 mm keyline beside 1.3 mm strokes: ROADMAP gate 1 (pull comp is a sew-out constant).
A geometry-only fix would hold the column lane's rail pull off a lighter, already-sewn
neighbour within ~0.6 mm; that needs lane work and a sew-out to say whether the black
then draws back. Not built. mfab_lc and 30 mm not run.
