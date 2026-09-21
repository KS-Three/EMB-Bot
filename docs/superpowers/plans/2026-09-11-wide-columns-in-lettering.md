# Wide columns in the browser lettering engine — quality review item 10

**2026-09-11.** Kent's *"Lets do all of them"* ordering put item 10 last of the
four (13, 12, 14, **10**). Item 10 as written:

> Eighteen of the 85 shipped fonts emit stitches longer than one DST record
> once letters get big; a two-letter monogram on a full back asks for a 44.9 mm
> cross (DOCTRINE 2026-09-07). The encoders now split the move; the engine
> still emits it. The Python engine splits satin above 5 mm with a stagger and
> routes past-cap widths to fill; the JS path has neither. Port the mechanism
> and the existing constants — no new number.
>
> Where: `satinplay.js emitZigzag`, `satinfont.js routeGlyph`,
> `digitize.js buildLetteringDesign`.

This is the build, the measurement, and the one part of it that is Kent's.

---

## 1. The instrument, and why it can be trusted

`tools/long-stitch-census.mjs` walks the 85 shipped `.embf` fonts through
`buildLetteringDesign` and counts, per design, the sewn segments past one DST
record. The chain rule is DOCTRINE's own: a move is *sewn* only when this
record is a stitch **and** the last emitted one was — a jump, trim or colour
change cuts the chain, because the move to a run's first point is travel.

**The counting rule is per axis, not per length**, and that is not a detail: a
DST record carries ±121 units *per axis*, so the test is
`max(|dx|,|dy|) > 12.1 mm`. Counted as a length instead, the same design
reports 53 more over-record segments and calls its worst 51.1 mm.

That distinction is what let the tool be validated rather than assumed. On
`manga_impact` "AB" at Full Back it reports **1,933 of 5,828 sewn segments over
one record, worst 44.9 mm**, on a design measuring **304.9 × 146.2 mm** — every
figure DOCTRINE 2026-09-07 states, to the stitch and to the tenth of a
millimetre.

*(DOCTRINE's other row, "a single-letter monogram at left-chest size gives 278
of 1,607", did not reproduce against any font/text pairing I guessed at. It is
not quoted below; the Full Back row is the one that pins the instrument.)*

## 2. What the census found, and how much of it item 10 was actually about

Sweep: 85 fonts × three texts — `AB` @ Full Back, `Yours` @ Full Back,
`A` @ Left Chest — 255 designs, at the Studio's own defaults.

| | fonts with an unsewable stitch | segments over a record | worst axis | stitches | trims |
|---|---:|---:|---:|---:|---:|
| **before any of this** | **80 / 85** | 187,174 of 1,061,115 | **98.7 mm** | 1,063,183 | — |
| two units fixes (§4) | 66 / 85 | 180,900 of 1,147,744 | 98.7 mm | 1,149,812 | 1,817 |
| **+ split satin** | **9 / 85** | 1,832 of 2,838,506 | **23.6 mm** | 2,840,574 | 1,817 |
| + wide-column fill | 9 / 85 | 1,832 of 5,880,370 | 23.6 mm | 6,005,760 | 125,014 |

Item 10's headline said "eighteen of the 85". **It is eighty**, and the
regime is not only Full Back: before any of this, a single letter at **Left
Chest** — the most common garment the product offers — broke **63 of 85**
fonts on its own (17,265 of 136,049 segments). The worst design in the library
throws a **98.7 mm** stitch. Per text, pre-change: AB @ Full Back 80/85,
`Yours` @ Full Back 61/85, `A` @ Left Chest 63/85.

The eight worst designs, `off` → `split` → `fill`:

| font | text / garment | over a record | worst axis | off st | split st | fill st | fill trims |
|---|---|---:|---:|---:|---:|---:|---:|
| `roaring_twenties_KOR` | AB / Full Back | 1,395 / 3,408 | 98.7 | 3,410 | 44,528 | 109,613 | 5 |
| `alchemy` | AB / Full Back | 1,454 / 3,569 | 89.4 | 3,571 | 21,096 | 50,174 | 940 |
| `excalibur_KOR` | AB / Full Back | 2,861 / 6,806 | 61.8 | 6,808 | 41,866 | 100,753 | 1,499 |
| `inkstitch_masego` | AB / Full Back | 1,879 / 4,566 | 53.2 | 4,570 | 34,218 | 85,445 | 212 |
| `alchemy` | A / Left Chest | 450 / 1,184 | 50.2 | 1,185 | 4,593 | 10,920 | 223 |
| `manga_impact` | AB / Full Back | 1,930 / 5,861 | 44.9 | 5,863 | 27,074 | 63,352 | 109 |

## 3. What was built — SPLIT ON, FILL OFF (Kent's ruling, §7)

Two independent answers to one defect, because DOCTRINE 2026-09-07 names three
candidates ("split satin, route wide columns to fill, cap the width") and calls
the choice between them *"a look-and-fabric decision with a sew-out behind
it"*. Both were built and measured OFF first; **Kent ruled split ON, fill off**
on the numbers in §7. The fill stays one config value away.

### `splitSatin` — `satinplay.splitLeg`, a port of `stage6_satin._split_points`

A leg past the threshold gets `k = ceil(len / SPLIT_SEGMENT_MM)` segments with
penetrations at `(j + shift)/k`, the comb shifted by the station's phase of a
4-station wave at ±0.23 of one segment. Every number mirrors `machine.py`
(`SPLIT_SEGMENT_MM` 3.0, `SPLIT_STAGGER_PERIOD` 4, `_STEP_SEGS` 0.23,
`_WAVE`), measured there over 27,256 professional k=2 split crosses. The
threshold is `machine.SPLIT_SATIN_ABOVE_MM` = 5.0. **No new number.**

**The port has one trap, and the naive version walked straight into it.** The
Python emitter keeps a constant rail order (A, B, A, B …), so flipping the
wave's sign genuinely walks the comb across the column. This module alternates
the leading rail per station — that is what makes its connector a short bounce
instead of a full traverse — so splitting in *traversal* order makes the
direction flip cancel the sign flip **exactly**. Measured on a straight 7.5 mm
column: stations 0 and 1 both put their penetrations at 24.6 and 44.6 px, a
trenched line of holes, which is the one defect the stagger exists to prevent.
The cross is split in the column's own A→B frame and the list reversed for
traversal; the same two stations then land at 0.410/0.743 and 0.257/0.590 of
the cross, as the corpus wave intends. `test/wide-columns.test.js` pins it by
name.

Because the connector is short by construction here, only the cross normally
splits — but both legs are offered to the splitter, since a run of stations
dropped at the cross floor turns the connector into a chord that must not be
thrown whole either.

`satinplay.stripSplits` is the exact inverse (mirroring
`stage6_satin.strip_splits`): split points are exact lerps, so they lie on the
segment joining their neighbours and no rail penetration ever can. Any
instrument reading a satin run as alternating rail pairs calls it first.

### `wideColumnFill` — a third class in `splitByCrossFloor`, and `fillFromGeom`

`splitByCrossFloor` already classed stretches of a column as satin or hairline.
It now classes **wide** at the other end, past `opts.maxCrossMm`, through the
same absorb loop — so a lone wide station inside a satin stretch stays satin
(its cross splits instead) and a lone satin station inside a wide stretch joins
the fill. `fillFromGeom` tatamis the stretch over its own two rails at
`machine.FILL_ROW_MM` / `FILL_STITCH_MM`, rows running at `fill.pcaAngleDeg`
of that polygon — **the same angle rule this engine's image lane already gives
every fill it emits**. (`pcaAngleDeg` moved from `digitize.js` into `fill.js`
so there is one definition rather than two that can drift.)

The ceiling is **3.0 mm, the browser's own** `satinMaxWidthMm`. Python's is 5.0
and `machine.py` says in as many words that the divergence is *"deliberate,
corpus-driven, and Python-side only until its own sew-out"*. Importing 5.0 here
would spend a sew-out this lane has not had.

A fill on a curved column needs one more thing the satin never did: a scanline
crossing a column that bends back on itself hits the ink twice, and the move
between the two crossings goes over bare fabric. `tatamiFill`'s
`markConnectors` tags those, and `fillFromGeom` cuts the fill there, each piece
becoming its own run reached needle-up — the run-level mechanism this module
already has, not a new per-point one. That is where the fill arm's **125,014
trims against the split arm's 1,817** come from.

## 4. Two units bugs the measurement turned up — fixed unconditionally

Neither is behind a knob, because neither is a choice.

**The Euler-walk underpath.** `routeGlyph` stepped its needle-down travel at a
bare `2` in the *layout* frame, while the underlay pitch three lines away in
the same function was correctly `UNDERLAY_STEP_MM / fitScale`. Found because
after the satin split, the only sewn segments left over a record on the "AB"
Full Back were three underpath steps of 22.1, 19.0 and 22.3 mm — in a design
whose longest satin leg was 5.0.

**The authored run pitch.** `routeRuns` used the font's own `lenMm` in the
layout frame too. Eighteen shipped fonts are runs-only and all were affected:
`western_light`'s "A" at Left Chest sewed **92 stitches, 66 of them past a DST
record, worst 22.5 mm** — about a sixth of the stitches it needed, at seven
times the pitch its own font asked for. It now sews **560, worst 3.0 mm**.

It is wrong in both directions, and that is what settles it as a units bug
rather than a look question: grown, it throws stitches no machine can make;
shrunk, it takes an authored 1.0 mm run to 0.2 mm at a 0.2 fit, straight
through Law 51's min-stitch floor. A run's pitch is a property of needle and
thread, not of how big the letter is.

**What moved.** `SATIN_BASELINE`'s five pinned fonts: montecarlo 1157 → 1166,
alchemy 751 → 751 (unmoved), venezia 996 → 997, cats 1238 → 1243, apesplit
2470 → 2475 — +0.00% to +0.78%. Isolated rather than asserted: applying **only**
the underpath fix to the pre-change tree reproduces all five new numbers and
the whole stitch array with them, **byte for byte**, so nothing else landing
here moves that stream. `satinfont.test.js`'s 40 mm AB goes 701 → 703 and its
8 mm AB goes 189 → **188** — one number, two directions, because the bug was
the frame.

## 5. What NEITHER knob fixes, and why it is a separate question

Nine fonts still throw a stitch over a record with the split on: `egyptian`,
`eloquent`, `heavenly` and their `_small` twins, `jaquarda_bastarda_9`,
`jersey_15`, `noble`. **All nine are cross-stitch fonts**, routed through
`crossfill.js` and not through `routeGlyph` at all. The long segment is the arm
of an X.

`crossfill.js` is explicit that this is by design: the lattice *"is expressed in
GLYPH UNITS, so it scales with the letterform exactly as satin column width
does. Nothing here has an opinion about millimetres."* A cross-stitch X is part
of the letterform. So a big cross-stitch letter genuinely has big Xs, an arm
past 12.1 mm genuinely cannot be sewn, and the fix — a penetration in the
middle of each arm — visibly changes what a cross-stitch X looks like. That is
a look call, not a port. Worst arm in the sweep: **23.6 mm** (`heavenly`, AB at
Full Back).

## 6. The two knobs are near-substitutes, not complements

With both on, the split fires **zero** times on the monogram: every stretch the
ceiling would have split had already gone to fill. They answer the same
question at different prices.

| | over a record | worst axis | stitches | trims |
|---|---:|---:|---:|---:|
| off | 180,900 | 98.7 mm | 1,149,812 | 1,817 |
| split | 1,832 | 23.6 mm | **2.47×** | 1,817 (unchanged) |
| fill | 1,832 | 23.6 mm | **5.22×** | **68.8×** |

Both reach the same sewability. The split costs penetrations and no trims; the
fill costs penetrations, a trim every time a curved column's scanline leaves
the ink, and a completely different look — a tatami where a satin ribbon was.

## 7. Kent's call — RULED: split ON, fill off (2026-09-11)

Everything above was built, tested and measured with both knobs off, and the
default put to Kent, because DOCTRINE already says why it is his: *"what to do
about it — split satin, route wide columns to fill, cap the width — is a
look-and-fabric decision with a sew-out behind it."*

**He chose the split.** `splitSatin` is now the default (`false` or `0` turns
it off, a number overrides the threshold); `wideColumnFill` stays off.

The three options as they were put, with what each delivers, what it costs, and
its catch:

- **Split ON, fill off — CHOSEN.** Takes 80 fonts of 85 to 9 and the worst
  stitch from 98.7 mm to 23.6. Costs 2.47× the stitches across the sweep and no
  trims at all. Catch: a 20 mm-wide letter stroke is still sewn as satin, just
  with penetrations in it — the widest strokes keep a look the corpus says
  professionals stop using around 5 mm.
- **Fill ON, split off.** Same sewability; the widest strokes get the tatami a
  professional would give them. Costs 5.22× the stitches and 68.8× the trims,
  and changes the look of every letter wider than 3.0 mm, which at Full Back
  is most of them.
- **Both off (today).** Nothing changes but the two units fixes, which land
  either way and take the library from 80 broken fonts to 66. Catch: the
  product still cannot sew a monogram, and **48 of 85 fonts break on a single
  letter at Left Chest** even after those fixes.

**Not offered, deliberately:** raising the browser's 3.0 mm ceiling to Python's
5.0. That is exactly the divergence `machine.py` says needs its own sew-out,
and one config value changes it once there is one.

The cross-stitch arm (§5) is a separate question and is not part of this one.

### What the flip moved

Four tests, and the blast radius is small because only 2.0% of sewn segments
are past 5.0 mm at quick-start sizes:

- `SATIN_BASELINE`: **only `alchemy` moves**, 751 → 786 (+4.7%) — and it is the
  one font of 85 that threw a stitch past a DST record on the small-text sweep,
  so it is the only one of the five with crosses past 5.0 mm at 40 mm. The
  other four are untouched, which is the threshold doing its job.
- **Two slant tests and one bold/thin test were measuring the wrong quantity,
  and the split exposed it.** Each compared a raw stitch count or an average
  stitch length; a split cross is *the same thread in more, shorter segments*,
  so a wider column can read as a shorter average (bold 24.537 against thin
  24.678 — inverted) and a sub-millimetre fit nudge can move 594 penetrations.
  All three now measure **total sewn path**, which is exactly invariant under
  splitting because every split point lies ON the segment it divides. The slant
  claim got *tighter* in the move: a 15° lean stretches each cross by at most
  1/cos 15° = 1.0353, and the measured ratio is **1.0300 in both arms**.
- `EMB.stripSplits` looks like the right tool for that and is not: on a
  design's DST-rounded integer coordinates ordinary rail penetrations are
  routinely collinear, and it removed 2,950 of them. It is exact on the
  engine's own float geometry, which is where the module's own tests use it.

## 8. Files

- `src/satinplay.js` — `splitLeg`, `stripSplits`, `fillFromGeom`, the `wide`
  class, `emitZigzag`'s `splitAboveMm`.
- `src/satinfont.js` — the four mirrored constants, `UNDERPATH_STEP_MM`, the
  two knobs resolved in `layoutText`, the fill part and its single underlay in
  `routeGlyph`, `routeRuns`' `fitScale`.
- `src/fill.js` — `pcaAngleDeg` (moved), exported.
- `src/digitize.js` — `splitSatin` / `wideColumnFill` passed through
  `buildLetteringDesign`; `pcaAngleDeg` re-pointed.
- `tools/long-stitch-census.mjs` — the instrument, with `--doctrine`,
  `--big` and `--arm`.
- `test/wide-columns.test.js` — 17 tests, including the stagger trap and both
  directions of the run-pitch bug.
