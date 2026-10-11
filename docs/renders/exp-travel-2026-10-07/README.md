# A stitch that follows travel: the three files of one design (2026-10-07)

[`sheet.svg`](sheet.svg) is four designs, each written as DST, PES and EXP
by the engine's own writers and drawn from what **pystitch** reads of each
file (`tools/crossval_decode.py`), not from the engine's stream. **Blue** is
thread between two stitches in a row, **grey** every other move, a **dot** a
needle hole, and a **red ring** a needle hole the DST of the same design has
not. The fourth panel of each row is the EXP as `main` wrote it at `32b0dd3f`,
before `exp.js` had the chain rule.

Nothing here has been sewn. These are readings of the stitch files.

| design | DST | PES | EXP | EXP before |
|---|---|---|---|---|
| a T drawn by hand and set to satin, 40 mm (left chest) | 570 holes | 570 | 570 | 576: six down the stem |
| a four-point star, inner ratio 0.15, 20 mm, off the shape tool | 284 | 284 | 284 | 288: four at the star's centre |
| `test/fixtures/standard-tajima.dst`, whose first record is a stitch, imported and placed 30 mm right of the hoop's middle and 20 mm down | 10 | 10 | 10 | 12: thread sewn from where the file starts toward the design |
| lettering, then that file as the project's second element | 1,138 | 1,138 | 1,138 | 1,140: thread sewn from the end of the lettering to the design |

A hole counts as the DST's when one of the DST's is on it or within 0.1 mm of
it. The 0.1 mm is for the PES: where a SEWN move over 12.1 mm is split, the
PES writer's split point can sit one unit from the other two's (it splits
with y pointing down, and a half rounds the other way), 33 times in the T
and twice in the star. Seen, not touched.

The first two rows are the browser's satin floating to another arm of the
shape and sewing back where it was (MASTER_SCOPE defect 57). That float is
still there in all three files; what is gone is the EXP sewing along it.

To draw it yourself:

```bash
git archive 32b0dd3f src | tar -x -C <dir>
node tools/travel-sheet.mjs docs/renders/exp-travel-2026-10-07/sheet.svg --against <dir>/src
```

Without `--against` the sheet is three panels a row, the files as this
checkout writes them. The counts behind it: `docs/scope-history.md`,
2026-10-07.
