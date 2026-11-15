# and_pizza's Z joints: one bar sewed curved (2026-11-14)

Four of Kent's pins sit on and_pizza's two Zs (#2, #3 at a Z's bottom joint,
#19, #20 on its top). `lettering_columns_apex_cut` cures them
(`docs/apex-cut-corpus-2026-11-14.md`). The apex guard (#1514) then returned
and_pizza to OFF. Each Z's two joints are one shape turned 180 deg, and only
the top-right one fanned. The guard's write-up blamed the walk's sewing
order.

## What it is (traced, by eye)

The trace is on the lane's own input for and_pizza at 80 mm, under apex cut.
The Z's apex cut gives five columns: two tips, the diagonal, and the two
bars.

- **The top bar is built as a CURVED column.**
  - Its piece is a short slab with one slanted end on the tip's cut.
  - It reads an outline coherence of 0.46 against `straight_axis`' 0.55,
    and its spine wanders past the straight limit.
  - Its crosses therefore swing round to follow a bent midline into the
    cut. That is the fan at the top-right joint.
- **The bottom bar is the same shape turned round.** It has the same 0.46
  coherence, but its spine scraped through, so it sewed straight with
  parallel crosses.
- **Walk order** adds to it. The walk runs bottom bar -> diagonal -> top
  bar, so at the top joint the top bar is sewn after the diagonal and its
  swung crosses lie on top. At the bottom joint the diagonal covers the
  bottom bar's end.
- No walk order fixes both joints. One bar must be sewn after the diagonal.

The cure is the construction, not the order: make the top bar what it is,
a straight bar.

## The build: `cfg.extra["lettering_columns_rail_pair_bars"]` (built OFF)

In `outline_cut.straight_axis`, the test applies to a piece that fails both
existing tests: a coherent outline (0.55) and a straight spine. Such a piece
is still a STRAIGHT stroke when it has two rails:
- its longest own side is at least 1.0 stroke width (`RAIL_PAIR_MIN_W`);
- an own side runs parallel to it (within the upright snap's 7 deg), at
  least half its length (`RAIL_PAIR_MIN_FRAC`);
- that side lies across the stroke, at least half a stroke width off the
  first side's line.

The axis is their length-weighted direction, and the rest of
`straight_axis` (the slab test, the upright snap) applies unchanged.

**What it reaches:**
- A half ring has no such pair and stays curved (test).
- Set plan-wide in `pipeline.plan_stitches`, as the apex guard is
  (`rail_pair_bars_scope`).
- Part of `_build_column`'s memo key.
- Registered in `shape_memo._AMBIENT`.

**On the lane fixture:** both of and_pizza's Zs build both bars straight
under apex cut. Both joints read alike: the bars' crosses parallel, the
fan at the top joint gone. Sheets (gitignored, primary checkout,
`digitizer/eye_pairs_out/jag-source-1113/z-joints/`): `z1_rp.png`,
`z2_rp.png` (each OFF | apex_cut | apex_cut+rail_pair, path and thread) and
`z2_joints.png` (both joints zoomed).

## What else it moves

**The first rule was too wide.** Without the share test it also straightened
part of Becker MARINE's R bowl, which has two straight parallel stretches,
and the bowl read angular and worse. The rule now also requires the two
rails to make up at least 0.6 of the piece's own outline
(`RAIL_PAIR_MIN_SHARE`; the Z's bar reads 0.73).

**With the final rule, on the lane's own inputs:**
- **Becker hat large's six MARINE letters, flag alone:** only the E moves.
  Its bottom arm, which was a curved column whose end fanned, becomes a
  straight bar with parallel crosses, which reads cleaner. The R and the
  others are byte-identical.
- **and_pizza's five letters under apex cut:** both Zs move, and nothing
  else does.

**A partial corpus, on the FIRST (wider) rule** (11 of #1490's 28 designs,
then stopped for time; the laptop was loaded and Jakarta alone took 27 min
for three arms):
- the flag alone moved only Becker hat large and MFab hat;
- under apex cut + guard it moved the same two;
- and_pizza, Ahora, Bukit Asam, But Seriously, Dot Music, hed p.e., Jakarta,
  k_line and N Sync were byte-identical in every arm.

The final rule moves no more than that, but this corpus has not been re-run
on it. FINAL-RULE rows for Becker hat large and MFab hat (flag alone) are in
the PR body.

## The guard

`apex_guard` refuses and_pizza's Z tips on its own geometric rule: the cut
found only by sliding to the walk's limit (0.96-1.00). It does not refuse
them because of the fan.
- With the guard on, and_pizza sews as OFF whether or not this flag is on.
- This flag makes the two joints alike under apex cut, which removes the
  reason the guard's PR gave for not keeping one and refusing the other.
- Whether the guard should let and_pizza's Z tips through is its owner's
  call.
