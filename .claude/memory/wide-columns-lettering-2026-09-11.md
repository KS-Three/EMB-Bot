# Wide columns in the browser lettering engine — 2026-09-11 (quality review item 10)

The last of Kent's four (13, 12, 14, **10**). Item 10 asked for a port:
*"The Python engine splits satin above 5 mm with a stagger and routes past-cap
widths to fill; the JS path has neither. Port the mechanism and the existing
constants — no new number."*

## The instrument had to earn the right to be quoted

`tools/long-stitch-census.mjs`. It counts a sewn segment as over one DST record
when `max(|dx|,|dy|) > 12.1 mm` — **per axis**, because that is what a record
carries. Counting by segment LENGTH instead reports 53 more on the same design
and calls its worst 51.1 mm instead of 44.9.

That distinction is what let it be validated rather than assumed: on
`manga_impact` "AB" at Full Back it reproduces **every figure DOCTRINE
2026-09-07 states** — 1,933 of 5,828 sewn segments, worst 44.9 mm, design
304.9 × 146.2 mm — to the stitch and the tenth of a millimetre. (DOCTRINE's
other row, "278 of 1,607", did not reproduce against any font/text pairing I
guessed at; it is not quoted anywhere in the PR.)

## The review item's own headline was low by four times

Item 10 said "eighteen of the 85 shipped fonts". Measured over 85 fonts × three
texts: **80 of 85, worst 98.7 mm.** And it is not a Full Back problem — one
letter at **Left Chest** breaks 63 of 85 on its own.

The 2026-09-07 number was honestly measured; it swept three texts at sizes
where the defect barely starts. Same lesson as the DST sentinel entry four days
earlier, from the same file: **a defect measured on the quiet path and carried
forward as a headline understates itself forever.**

## Three frame bugs, none visible in a diff

Every mirrored constant was right and the port still did nothing useful.

1. **The stagger cancelled itself exactly.** Python keeps a constant rail order
   so the wave's sign flip walks the comb; this module alternates the leading
   rail per station, so splitting in TRAVERSAL order made the direction flip
   undo it. Stations 0 and 1 both landed at 24.6 and 44.6 px of a 7.5 mm
   column — a perfectly trenched line of holes, from code that reads as a
   faithful port. Fixed by splitting in the column's own A→B frame and
   reversing the list; pinned by name in `test/wide-columns.test.js`.
2. **The split SEGMENT was not fit-scaled while its threshold was.** The tell
   was a result that moved the WRONG WAY: worst segment only 44.9 → 28.4 mm
   and the over-record COUNT went up. A fix that makes its own headline metric
   worse is not a partial fix.
3. **Two pre-existing bugs of the same shape.** `routeGlyph`'s Euler-walk
   underpath stepped a bare `2` in the layout frame; `routeRuns` measured the
   font's authored `lenMm` there too. `western_light`'s "A" at left chest sewed
   **92 stitches, 66 past a DST record, worst 22.5 mm** — a sixth of the
   stitches it needed at seven times its own font's pitch. Now 560, worst 3.0.

**The tell, all three times: a sibling line doing the same conversion correctly
a few lines away.** And a value wrong in BOTH directions — unsewable grown,
under Law 51's needle floor shrunk — is a units bug, not a look decision, so it
ships without a flag.

## What is built, and what Kent ruled

Both knobs were built and measured OFF; **Kent ruled `splitSatin` ON and
`wideColumnFill` off** the same day. `splitSatin` ports `stage6_satin._split_points`
(3.0 mm segment, 4-station ±0.23 wave, 5.0 mm threshold, all mirrored);
`wideColumnFill` adds a WIDE class to `splitByCrossFloor` past the **browser's
own 3.0 mm** ceiling — not Python's 5.0, which `machine.py` calls
"Python-side only until its own sew-out" — and tatamis the stretch over its own
rails at `fill.pcaAngleDeg` (moved out of `digitize.js` so there is one
definition).

| | fonts over a record | worst axis | stitches | trims |
|---|---:|---:|---:|---:|
| before | 80 / 85 | 98.7 mm | 1,063,183 | — |
| units fixes only | 66 / 85 | 98.7 mm | 1,149,812 | 1,817 |
| + split | 9 / 85 | 23.6 mm | **2.47×** | 1,817 |
| + fill | 9 / 85 | 23.6 mm | **5.22×** | **68.8×** |

They are near-**substitutes**, not complements: with both on the split fires
zero times, because every stretch it would have split went to fill first.

The default was his because DOCTRINE 2026-09-07 already ruled that it is —
*"split satin, route wide columns to fill, cap the width — is a look-and-fabric
decision with a sew-out behind it."* He took the split: same sewability, a
quarter of the stitch cost, no trims at all, and the smaller look change.

**The flip exposed three tests measuring the wrong quantity**, and that is the
part worth carrying forward. Each stood a raw stitch count or an average
stitch length in for "wider" or "the same stations". A split cross is the SAME
THREAD in more, shorter segments — so a bold column read as a SHORTER average
stitch than a thin one (24.537 against 24.678, inverted) and a sub-millimetre
fit nudge moved 594 penetrations. All three now measure TOTAL SEWN PATH, which
splitting cannot move, and the slant claim got tighter doing it: 1/cos 15° =
1.0353 is the geometric bound and 1.0300 is what both arms measure.
`stripSplits` is NOT the escape hatch — on DST-rounded integer coordinates
ordinary rail penetrations are collinear and it removes 2,950 of them; it is
exact only on the engine's own float geometry. Only `alchemy` moved among the
five pinned fonts (751 → 786), and it is the one font of 85 the census had
already singled out.

## What neither knob fixes

The 9 remaining fonts are **all cross-stitch fonts**. `crossfill.js` states that
its lattice is in GLYPH UNITS by design — "nothing here has an opinion about
millimetres" — so a big cross-stitch letter genuinely has big Xs, an arm past
12.1 mm genuinely cannot be sewn, and splitting it puts a penetration in the
middle of an X. Separate question, separate look call. Worst arm: 23.6 mm.

## Read before

Quoting how many fonts are broken, touching `emitZigzag`, `routeRuns`,
`splitByCrossFloor` or `routeGlyph`'s underpath, flipping either knob, or
raising the browser's 3.0 mm satin ceiling toward Python's 5.0.

Plan: `docs/superpowers/plans/2026-09-11-wide-columns-in-lettering.md`.
