# A walk that never ended: the star before and after (2026-10-03)

Every picture here is one design drawn from its own DST bytes: the engine's
encoder writes the file and `src/dstimport.js` reads it back. **Grey** is the
shape as drawn, **black** is thread, **red** is a needle-up move. Each design
is built the way `app/src/lib/generate.js` builds a `shape` element (left
chest, the pique knit preset, underlay on).

Nothing here has been sewn. These are measurements of the stitch file.

Before is `origin/main` at `f887e27d`. To draw one yourself:

```bash
git archive f887e27d src app/package.json app/src/lib | tar -x -C <dir>
node tools/satin-walk-census.mjs --against <dir> --render before.png --shape star:12:0.15:20
node tools/satin-walk-census.mjs --render after.png --shape star:12:0.15:20
```

## What was fixed

| design | before | after |
|---|---|---|
| 12-point star, inner ratio 0.15, 20 mm | [48,645 stitches](star-20mm-before.png) | [729](star-20mm-after.png) |
| the same star at 24 mm | [128,239 stitches](star-24mm-before.png) | [873](star-24mm-after.png) |
| a 73 x 3 mm bar with round ends | [397 stitches, sewn 72.7 x 10.3 mm](pill-73x3-before.png) | [397, sewn 72.4 x 3.6 mm](pill-73x3-after.png) |

**The star.** The black knot left of centre in the two "before" pictures is
the whole defect: 47,988 of the 20 mm star's stitches, and 127,447 of the
24 mm one's, on a millimetre or two of skeleton. Of the 729 stitches the
20 mm star sews now, 657 are stitches it sewed before, in the same places;
the other 72 are the walks that used to run away, sewn as the short edges
they are. The tangle of long stitches across the centre is in both pictures:
that is a different defect and is still there (below).

**The bar.** Before, two stitches leave the bar's left end, one of them
28 mm long and reaching 7 mm below it. After, every cross is inside the
outline.

## What the same sweep found and this change does not touch

These three are as they sew on `origin/main` and as they sew now.

- [`standing-bar-30x3.png`](standing-bar-30x3.png): a plain 30 x 3 mm bar,
  sharp corners. The crosses are right for 29 mm, then fan round at the left
  end: seven lean across it and the last is one stitch 30.2 mm long, the
  length of the bar. 185 of the 276 sharp-cornered satin bars the census
  makes on left chest carry a stitch at least nine tenths as long as the bar
  (`node tools/satin-walk-census.mjs --kind rect`).
- [`standing-star-78mm.png`](standing-star-78mm.png): a 10-point star, ratio
  0.15, 78 mm. Ten clean arms and a centre of stitches up to 72.5 mm long,
  laid from arm to arm. Every satin star in the sweep has a stitch over 3 mm;
  the median longest is 21 mm.
- [`standing-star-6pt-15mm.png`](standing-star-6pt-15mm.png): a 6-point star,
  ratio 0.45, 15 mm: 1,812 stitches where its neighbours in size sew about
  550. No walk ran away here. The ring scan found "rings" in a shape that has
  no hole, each one a lap of arms already sewn, and sewed them again.

Numbers, the cause and what moved: `docs/scope-history.md`, the entry of this
date. Live status: MASTER_SCOPE defect 57.
