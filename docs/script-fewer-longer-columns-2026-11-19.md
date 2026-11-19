# Script words: "fewer, longer columns" measured; the split is not in the pen strokes (2026-11-19)

**Verdict: the premise holds on Tires only, and it is not the pen-stroke split. Our script words have as few
or fewer PEN STROKES than the professional's chains; the extra columns come from (1) patch columns and (2)
the walk in `columns.column_runs` cutting a stroke into spans where another column's end lands on it. A
flag that merges patches into the stroke they continue was built OFF (`script_strokes_patch_merge`): it
removes patches but does not move the column count, and the whole word is indistinguishable at print size,
so it stays OFF.** Numbers only; the professional's files were read from the committed zip, extracted outside
the repo, nothing of them rendered or committed. Readers: `tools.script_flow`, `tools.script_ends` (PR #1692).

## Table (plan = before the emitter; DST chains = `script_ends` columns of 6+ crosses, whole block)

| word | pen strokes | patches | ours DST chains / ends / free / median len | pro chains / ends / free / median len |
|---|---|---|---|---|
| tires_hat_3d | 5 | 5 | 26 / 52 / 19 / 8.3 mm (32 crosses) | 14 / 28 / 16 / 31.1 mm (265 crosses) |
| bridge_hat | 9 | 5 | | pro file not in the committed zip |
| bridge_lc | 9 | 6 | | pro file not in the committed zip |
| toat_machine_hat | 11 | 2 | 20 / 40 / 11 / 7.9 mm (word box) | 24 / 48 / 20 / 6.8 mm (box also holds the M) |
| toat_machine_beanie | 10 | 1 | 22 / 44 / 12 / 7.9 mm | 22 / 44 / 19 / 6.5 mm |
| toat_beanie | 13 | 4 | | `To a T Beanie.DST` is not in the zip |

On Toat Machine ours is not split further than his in a comparable box; only Tires shows the pattern (ours 26
chains, pro 14, the "26 vs 14" of #1692). His free ends are MORE than ours on Machine.

## Where ours splits (Tires)

- Pen strokes: 5, against his 14 chains. `pen_strokes` / `_split_cusps` are not the cause: there is nothing
  to merge at a corner.
- Patches: 5 patch columns (uncovered ground 18.3, 0.8, 1.2, 2.6, 0.4 mm2 of a 925 mm2 word), each a column of
  its own with two ends. The e/s step end near design (37, 15) is the 1.2 mm2 patch.
- The walk: the 5 strokes sew as about 21 chains. Plan column 2 (250 stations) is 8 chains in the DST. The
  cause is `columns._span_graph`: a column is cut into spans where another column's END lands on its
  centreline, and the Euler walk sews the spans in their own order with underpaths between.

## Built OFF: `cfg.extra["script_strokes_patch_merge"]` (`digitizer_core/patch_merge.py`)

A patch whose nearer end is within 2.5 mm of a stroke's end, its first cross turned no more than 35 deg from
that end's, joins that column (stations appended or prepended, the gap filled at the pitch, every filled cross
on the art). Result (plan; DST):

| | patches | stitches | trims | jumps | needle-up mm |
|---|---|---|---|---|---|
| tires_hat_3d | 5 -> 3 | 4644 -> 4660 | 7 -> 4 | 11 -> 8 | 71.3 -> 64.8 |
| bridge_hat | 5 -> 1 | 7942 -> 7905 | 15 -> 14 | 28 -> 27 | 163.2 -> 180.8 (WORSE) |
| toat_machine_hat | 2 -> fewer (md5 moved, +1 stitch) | 17100 -> 17101 | 18 | 45 | 267.9 |
| toat_machine_beanie | unchanged | | | | |
| toat_beanie | | 17193 -> 17014 | 25 -> 22 | 42 | 233.6 -> 254.2 (WORSE) |

Tires chains 26 -> 26, free ends 19 -> 17, median length 8.3 -> 9.1 mm: the count does not move, because the
walk, not the patches, makes most of the chains. Pictures: `docs/renders/patch-merge-2026-11-19/`. At print size
the words are indistinguishable. **Not clearly better, left OFF; the 44-run sweep was not run.**

## A second experiment, not kept: no cut at a junction

Skipping the junction cut in `_span_graph` for a script word (the through column runs on, the butting column's
end is a node of its own) on Tires: trims 7 -> 9, jumps 11 -> 20, needle-up 71 -> 175 mm, chains 26 -> 24.
**Worse and barely fewer columns: not built.** The cut is what connects the butting column to the walk; without
it the walk lifts the needle. A real fix has to let the walk run a through column on AND still reach the butting
column's end from it (a tuck from the through column's own pass), which is a change to `column_runs` for every
lettering lane, not a script flag.

## Next step, if one is taken
Count, per Tires column end, whether the end is a plan-column end, a span cut, or a patch end (this note counts
patches and chains, not each end). Then try the walk change above on the script lane only, measured with the
Tires e/s step as the case: four ends about 1 mm apart, his one free end.
