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
- **Each thread is locked at its ends: on its first penetration and on its
  last.** The lock is `tieRun`'s bounce, put straight after its anchor. That
  is the sequence Python sews at both ends.
- **The bounce is laid toward the nearest other place the frame goes.** That
  is the next stitch, nearly always, and then the lock lies on that stitch.
- **A thread's end can be one stitch with a float beside it.** A row shorter
  than a stitch is a single record after a float or a cut, because the frame
  lands on its start. The lock is then laid back along that row, toward where
  the frame was just before the stitch. Along the float is the last choice: a
  float can cross a hole.
- **A lock never reaches past the place it is laid toward.** On a stitch
  shorter than 0.8 mm the leg is the stitch. Python's rule.
- **A thread that goes down in one place only gets no lock.** It sews
  nothing.
- **A lock sits in the span its anchor is in** (`design.runs`), so it belongs
  to the run it protects. Ten shipped fonts give their own runs no span, and
  there the locks have none either.

Asking the stream is what makes the shape lane possible at all. A fill has a
cut in the middle of it (center-out's, or the column walk's), a run can open
with a float, and the first penetration after a cut is not always the first
point of anything.

**Where a lock sits is an audit's doing.** The first version locked a thread
on its first and last "two stitch records in a row". Where a thread ended in
a float and one stitch, that was up-thread, and the tail hung loose behind
the lock: 6.1% of tie-offs in shape designs with `fillColumns` off, by as
much as 371 mm of thread. A lock belongs where the thread ends. The second
version put it there and laid it along the float, which on a frame was
0.8 mm into the hole. The third lays it back along the row.

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
| Badge, 36 holes, 60 mm | on | 0 | 2 | 8,738 | 8,746 | +0.09% | 0.28 mm |
| Thin bar, 3 x 40 mm (satin) | off | 0 | 2 | 226 | 234 | +3.54% | 0.80 mm |
| Three squares apart, one colour | off | 5 | 12 | 3,015 | 3,063 | +1.59% | 0.80 mm |
| Three squares, three colours | off | 5 | 12 | 3,015 | 3,063 | +1.59% | 0.80 mm |
| Twelve 6 mm dots, one colour | off | 11 | 24 | 1,590 | 1,686 | +6.04% | 0.10 mm |

*(measured 2026-10-03 — the same tool prints all 22 rows, of which these are
eleven. The 36-hole row is as re-measured after `fillColumns` stopped sewing
a corner on a scanline, below: of the eleven rows with that option on, three
moved, by 2 to 18 stitches.)*

- **Locks: `2 + 2 × cuts`, four stitches each.** The percentage is a statement
  about how many pieces a design is in, not about locks. One 40 mm square
  pays 0.5%. Twelve dots pay 6%.
- **Over 9,869 audited shape designs: +1.2% stitches on average**, +1.0% on
  the median design, under +2.3% on nine in ten, +9.6% at worst. With
  `fillColumns` on: +0.9%, +0.5%, +2.0%, +14.4%.
- **Lettering varies more than the two texts above show.** Over 2,490 builds
  (85 fonts, 31 sizes and options) the median is +5.1%, the mean +9.1%, nine
  in ten are under +24%, and the worst is +87%: a small design in many pieces.
- **No cut is added.** A lock bounces between a penetration that was already
  there and a point on the way to the next place the frame goes.
- **`fillColumns` and this work together.** Fewer cuts, fewer locks.

## What an independent audit found

An agent with its own reader, written from the rule as stated and handed the
claims as claims. Three rounds.

- **What held from the first:** flag off identical to the commit before and
  to `main` on 12,880 shape designs (and the same 12,880 with `fillColumns`
  on) and 2,635 lettering builds; the before and after table above,
  re-derived; no trim, jump or colour change added; no hole doubled; the
  design's size unmoved; 200,015 random streams without a throw or a lost
  record.
- **What did not: where a lock sits.** The first rule locked a thread on its
  first and last "two stitch records in a row". 6.1% of tie-offs on shapes
  with `fillColumns` off were more than 4 mm of thread before the cut they
  guard, the worst 371 mm. Now: none, in any set.
- **And then where it points.** Laid along a float, 285 locks of 37,082 put
  their inner point in ground the shape does not cover, up to 0.91 mm into a
  hole. Laid back along the row: 21, the deepest 0.65 mm. Those 21 are one
  kind: a fill that opens on a row of no length (two penetrations in one
  hole) and then floats, so there is no row for the lock to lie along.
- **One claim of mine was wrong.** "A lock is always inside a span" fails for
  ten shipped fonts whose own runs carry no span at all.

*(measured 2026-10-03 — the auditor's sweeps; the engine's tied stream
equalled its own, record for record, in 29,050 builds)*

## Seen, not changed

- **A lock on a short stitch is a short lock, and on shapes that is one lock
  in five.** Under 0.3 mm: 9,021 of 47,812 locks with `fillColumns` off,
  7,570 of 31,088 with it on, nearly all in the fill, where a thread ends on
  the tiny last row at a tip or a curve. Five penetrations inside 0.3 mm.
  Lettering: 911 of 123,888. `min(leg, d)` is Python's rule, it never
  overshoots, and moving one lane without the other would be a new number.
  The audit's advice, and mine: **sew one before flipping the default for
  shapes.**
- **With `fillColumns` off a thread can end on a stitch that crosses a gap.**
  The engine sews across any gap narrower than a stitch. 734 locks lie on
  such a stitch, and so have their inner point in open ground too (to
  0.85 mm). The flag removes the stitch, and the lock with it.
- **In lettering, 1,959 locks lie along a needle-down connector**, 348 of
  them under 0.3 mm. A connector is sewn thread, so the lock holds where it
  is long enough.
- **With `fillColumns` on, 18 threads in 12,880 designs were two penetrations
  in one hole**, at a tooth tip, cut to and cut from. They sewed nothing and
  got no lock. The stub was the column walk's: a corner lying exactly on a
  scanline was a column of its own. It is left out since (fixed the same
  day: [`renders/fill-columns-2026-10-03/`](renders/fill-columns-2026-10-03/README.md),
  "A corner on a scanline").
- **The untied lettering stream already has doubled holes**: 9,093 across the
  85 fonts on `KENT`. Where a needle-down connector ends on a run's first
  point, that point is pushed twice. Not caused by locks, and the same with
  them on or off.
- **`app/src/lib/combine.js` drops `_debug.nTies`** when it joins elements. It
  keeps `nSatin`, `nFill` and `nTrims`.

## Safety

- **Off is byte-identical.** The audit hashed it: 0 of 12,880 shape designs
  and 0 of 2,635 lettering builds differ from `main`. In the suite, every
  engine test that existed passes unchanged, and a guard holds `ties: false`
  equal to no flag, spans included.
- **Take the locks out and the design is the untied one**, record for record.
  That is a test.
- **Mutation check: 32 rules broken one at a time, 31 caught by a test.** The
  one survivor is not a defect: measuring the design's size from the tied or
  the untied stream gives the same answer, because in every build a lock
  leaves the box alone, and that is itself a test.

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

Against: 3% to 8% more stitches on lettering as a whole (far more on a small
design in many pieces), about 1% on shapes, and locks no one has sewn. On
shapes one lock in five is five penetrations inside 0.3 mm. A candidate for
the sew-out card, not a desk decision. Lettering could flip without shapes:
its short locks are under 1%.

MASTER_SCOPE "Waiting on Kent" 23.
