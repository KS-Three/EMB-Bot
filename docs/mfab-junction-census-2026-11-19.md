# MFab top line: satin-piece census of the five junctions (2026-11-19)

Follows `docs/mfab-top-line-faults-2026-11-19.md` (#1694): five grader faults on `L_mfab_hat` (1, 3, 4, 5, 8)
were put down to one junction construction. Before building anything, this reads how the professional
sews the same five junctions, piece by piece. Numbers and words only: nothing from the committed zip is
rendered or committed.

## A correction first: the white is not the satin ladder

The white M-F-A-B is not sewn by `stage6_satin` (the brief's "satin ladder"). It is
`stage6_border.keyline_runs`, reached through `border_from_outline` in `stage7_sequence.stitch_one`:
**one 1.88 mm satin loop round each black hole** (11 loops; plan runs M 563, F 252 + 310, A 426, B 532
points), with `keyline_rest` fill under them. Traced with a stack on every white satin run, main `2c6bb99`.
The fault note's "two 1.9 mm bars 0.5 mm apart" are two hole loops sharing a strip about 3 mm wide.

## The reader: `digitizer/tools/satin_census.py`

It works on throws, not runs. A needle-down run's collinear segments (a split stitch) merge into one
throw. Consecutive throws make one satin step when:

- both are at least 0.3 mm;
- they are anti-parallel within 35 deg;
- the midpoint moves at most 1.2 mm;
- their lengths are comparable;
- the throws two apart are parallel (one rail to the other);
- the centreline does not turn back (a second pass).

A piece is a maximal chain of such steps, 4 throws or more. So a direction change, a reversal, a width
jump or an interleaved other piece each end one, and interleaved groups are read as their own pieces
(`tests/test_satin_census.py`).

**Validated on our own output first.** `--ours mfab_hat --validate` digitizes the hat at 104.9 mm and
drops the plan's run boundaries the way a machine file does (`machine_runs`: runs are joined until the
needle lifts). It then reads the pieces against the plan's own satin runs. A loop counts as read at
coverage of 0.85 or more and purity of 0.95 or more.

- **7 of 11 loops read**, all the large ones among them: M, both F loops, A, the dash, the B stem's
  neighbour.
- B's loop is purity 0.92: one underlay throw is taken into a piece at a loop start.
- Two tiny counter loops have 0.3-0.6 mm corner crosses that break the chain (coverage 0.73-0.86).
- One 97-stitch loop has purity 0.71 at a 6-throw edge piece.

Frames agree to 0.08 mm (top-left of the stitch extents: ours (-52.58, -19.75), his (-52.5, -19.7)).

## Census, hat at 104.9 mm

Points are mm from the extents' top-left. Layers: 0.4 mm lines at 20 px/mm, white only, r 2.5 mm,
mean over the covered pixels / max. "w" is the median throw length.

| junction | professional | ours | layers pro | layers ours |
|---|---|---|---|---|
| J1 M mark (16, 18.5) | 5 short columns 2.0-2.6 w, 5-7 mm, sewn after his outer loop, ends overlapping 0.3-0.7 | 4 loop sides 1.5-1.9 w | 5.0 / 13 | 2.9 / 7 |
| J2 F upright / top bar (35, 6) | his OUTER loop (2.41 w, one 130 mm run round all of M-F) runs through; the inner F piece (1.95 w), sewn before, ends 0.44 into it | two loop sides end, plus a 12-throw corner piece | 4.06 / 11 | 3.34 / 11 |
| J3 F diagonal / arm (45, 12.5) | ONE column 3.80 w (51 throws, 11.7 mm, crosses 83 +-22) | two 1.88 loop sides end; 12 consecutive crosses of one loop through one point (a corner pivot) | 3.49 / 8 | 4.19 / 15 |
| J4 dash counter (36, 17) | dash piece 1.8 w; a 2.62 w column and the outer loop pass through | 6 pieces, four loop sides ending | 4.23 / 12 | 5.23 / 15 |
| J5 B lower slot, left end (89, 18.5) | ONE straight column 2.83 w, 7.8 mm, crosses 46 +-7 (the letter's lean); the leg piece stops 0.55 short of it | the loop passes the slot twice (1.54 / 1.58 w), plus a fan | 3.43 / 8 | 5.51 / 13 |

Only J3, J4 and J5 are heavier than his. J1 is lighter: the fault there is the black mark, not the white.
J2 is on a par with his. At J3 the max of 15 is ONE loop pivoting at a hole corner. At J5 it is one loop
passing the slot twice. Two bars stacking is not the cause in either case.

**His construction (hat and LC alike).** The white top line is two needle-down runs, M+F and A+B. In each:

1. Every strip between two holes is sewn once, as a full-width column: F arm 3.8, B slots 2.83 twice,
   B stem 2.40, A bar 3.0 (LC: 3.50, 2.69 twice, 2.20, 2.83).
2. Then ONE 2.4 mm outer loop runs round the group (hat 130 / 73 mm, LC 116 / 67 mm).
3. Then the M's inner pieces.

There is no fill. That is `outline_one_band`'s construction (#1663, #1665): stem columns plus one outer
loop.

`outline_loop_split_shared` (existing, OFF), measured here, lowers the means (J3 4.19 -> 3.74,
J4 5.23 -> 4.34) but not the maxima (15, 17).

## Reproduce

```
cd digitizer
python -m tools.satin_census --ours mfab_hat --validate --at 45,12.5
python -m tools.satin_census --pro mfab_hat --scratch scratch_census --at 45,12.5 --list
```

`--pro` extracts the member from the committed zip into a gitignored `scratch_*` folder.
