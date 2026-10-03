# Lock stitches on the shape lane, and what the lettering port got wrong (2026-10-03)

`ties: true` now means the same thing in both browser builders, and it is
**default OFF in both**: nothing a customer exports changes until Kent flips
it. Nothing here has been sewn.

## What was missing

`buildQualityDesign` tied nothing. That is the builder behind manual draw,
basic shapes, SVG import and the flatten lane, so every trim in those lanes
left two loose ends. Quality review 2026-09-08 §4 named it for the whole
browser engine. The lettering builder got `ties` on 2026-09-14
([`lettering-ties-2026-09-14.md`](lettering-ties-2026-09-14.md)); this one
did not.

## What the lettering port got wrong

Two things, both found by measuring the stitch file instead of the points on
their way into it. Neither reached a customer: the flag is off and no caller
in the Studio passes it.

**Its leg was 0.8 pixels, not 0.8 mm.** `tieRun` took `TIE_STITCH_MM` as a
length in whatever units it was handed, and it was handed pixels. So the leg
depended on the design's resolution and size: 0.5 mm on a default two-letter
design, 0.3 mm on one fitted to 40 mm, 2.0 mm at 2 px per mm, 0.2 mm at 20.

**Its tie-in sat in front of the run's own first stitch.** The stream read
`inner, at, inner, at` and then `at` again: the needle went down twice in one
hole. Python sews `at, inner, at, inner` and then the run. The writers do not
drop a zero-length stitch, so it reached the file.

All 85 shipped fonts, ties on, before and after:

| text | locks | leg before: median (longest) | leg after: median (longest) | doubled holes added, before | after |
|---|---|---|---|---|---|
| `KENT` (4 ch) | 2,272 | 0.30 mm (0.57) | 0.81 mm (0.86) | 1,136 | 0 |
| `Fritsch's Stitches` (18 ch) | 5,132 | 0.10 mm (0.28) | 0.80 mm (0.86) | 4,574 | 0 |
| two lines (37 ch) | 10,264 | 0.10 mm (0.28) | 0.80 mm (0.86) | 8,695 | 0 |

*(measured 2026-10-03 with `node tools/lock-stitch-census.mjs`; "before" is
the same tool pointed at the engine as it stood at `5c1fd615`)*

- **Before, not one lock of 17,668 reached 0.75 mm.** On the 18-character
  text the shortest rounded to 0.00 mm: four penetrations of one hole.
- **The stitch counts did not move.** +3.31% and +8.00%, the 09-14 doc's own
  numbers to the stitch. A lock is still four stitches and there are still
  `2 + 2 × trims` of them. That doc's cost table stands. Its sentence about
  "a point 0.8 mm into the shape" did not.

## The rule now

One function, `applyTies`, for both builders. It is asked of the **finished
record stream**, which is in DST units (0.1 mm), so a leg is 8 units and
nothing else.

- **A thread is the records between two cuts.** A `trim` cuts. A `color`
  cuts. A `jump` does not: the question is whether the thread starts or ends
  here, not whether the needle lifted.
- **Each thread is locked on its first sewn stitch and on its last.** A sewn
  stitch is two penetrations in a row in two places. The lock is `tieRun`'s
  bounce laid along that stitch, put straight after its anchor. That is the
  sequence Python sews at both ends.
- **A lock never reaches past the stitch it lies on.** On a stitch shorter
  than 0.8 mm the leg is the stitch. Python's rule.
- **A thread that sews no stitch gets no lock.** One lone penetration has
  nothing to hold.
- **A lock belongs to the run it protects.** Its records sit inside that
  run's span in `design.runs`.

Asking the stream is what makes the shape lane possible at all. A fill has a
cut in the middle of it (center-out's, or the column walk's), a run can open
with a float, and the first penetration after a cut is not always the first
point of anything.

## What it costs on shapes

Left chest, the pique preset, underlay on, called the way the manual lane
calls it:

| design | `fillColumns` | cuts | locks | stitches off | on | more | shortest leg |
|---|---|---|---|---|---|---|---|
| Square, 40 mm | off | 1 | 4 | 3,331 | 3,347 | +0.48% | 0.80 mm |
| Circle, 30 mm | off | 1 | 4 | 1,574 | 1,590 | +1.02% | 0.80 mm |
| Star, 40 mm | off | 1 | 4 | 1,445 | 1,461 | +1.11% | 0.20 mm |
| Triangle, 10 mm | off | 0 | 2 | 230 | 238 | +3.48% | 0.20 mm |
| Badge, two cut-outs, 40 mm | off | 1 | 4 | 3,149 | 3,165 | +0.51% | 0.80 mm |
| Badge, two cut-outs, 40 mm | on | 0 | 2 | 3,253 | 3,261 | +0.25% | 0.80 mm |
| Badge, 36 holes, 60 mm | on | 0 | 2 | 8,740 | 8,748 | +0.09% | 0.20 mm |
| Thin bar, 3 x 40 mm (satin) | off | 0 | 2 | 226 | 234 | +3.54% | 0.80 mm |
| Three squares apart, one colour | off | 5 | 12 | 3,015 | 3,063 | +1.59% | 0.80 mm |
| Three squares, three colours | off | 5 | 12 | 3,015 | 3,063 | +1.59% | 0.80 mm |
| Twelve 6 mm dots, one colour | off | 11 | 24 | 1,590 | 1,686 | +6.04% | 0.10 mm |

*(measured 2026-10-03 — the same tool prints all 22 rows, of which these are
eleven)*

- **Locks: `2 + 2 × cuts`, four stitches each.** The percentage is a statement
  about how many pieces a design is in, not about locks. One 40 mm square
  pays 0.5%. Twelve dots pay 6%.
- **No cut is added.** A lock bounces between a penetration that was already
  there and a point on the stitch beside it.
- **`fillColumns` and this work together.** Fewer cuts, fewer locks.

## Seen, not changed

- **A lock on a short stitch is a short lock.** 9 of the 144 locks on the
  shapes above are under 0.75 mm, the shortest 0.10 mm: the thread starts on
  the tiny first row at a tip, or on a dot. On lettering it is 108 of 2,272
  (`KENT`) and 1,646 of 5,132 (18 characters): narrow columns. `min(leg, d)`
  is Python's rule, and moving one lane without the other would be a new
  number.
- **The untied lettering stream already has doubled holes**: 9,093 across the
  85 fonts on `KENT`. Where a needle-down connector ends on a run's first
  point, that point is pushed twice. Not caused by locks, and the same with
  them on or off.
- **`app/src/lib/combine.js` drops `_debug.nTies`** when it joins elements. It
  keeps `nSatin`, `nFill` and `nTrims`.

## Safety

- **Off is byte-identical.** Lettering: the untied stream is the same record
  for record on 85 of 85 fonts, three texts. Shapes: every engine test that
  existed passes unchanged, and a guard holds `ties: false` equal to no flag,
  spans included.
- **Take the locks out and the design is the untied one**, record for record.
  That is a test.
- **Mutation check: 24 rules broken one at a time, 23 caught by a test.** The
  one survivor is not a defect: measuring the design's size from the tied or
  the untied stream gives the same answer, because a lock never moves the
  box, and that is itself a test.

## What a flip needs

- `app/src/lib/generate.js` passes `ties: true` at its four call sites (three
  shapes, one lettering). `combine.js` already puts a trim between every two
  elements, so each element's own locks are in the right place.
- Every lettering and shape snapshot re-pins.
- The 0.8 mm leg and the three legs are `machine.py`'s, and have not met
  cloth there either.

## The open question: Kent's

Flip `ties` on for the browser lanes? One flag, both builders.

For: the Python lane ties every block and always has. An untied file is a
real defect on a real garment, and a machine's own auto-tie may be all that
hides it.

Against: 3% to 8% more stitches on lettering, 0.1% to 6% on shapes, and
locks no one has sewn. A candidate for the sew-out card, not a desk decision.

MASTER_SCOPE "Waiting on Kent" 23.
