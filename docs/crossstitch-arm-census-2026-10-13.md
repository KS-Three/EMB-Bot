# Cross-stitch arm census — 2026-10-13

**Measure only. No rendering changed.** After the `splitSatin` flip, the 9 fonts
that still sew a stitch past one DST record are all cross-stitch fonts
(MASTER_SCOPE, lettering size guards). `src/crossfill.js` draws its lattice in
glyph units, so an X arm grows with the letter. This measures how fast, and at
what size each font crosses the machine limit.

## Reproduce

```
node tools/crossstitch-arm-census.mjs          # the sweep table below (~15 s)
node tools/crossstitch-arm-census.mjs --hoop   # long-stitch-census's own rows, with their cap
node tools/crossstitch-arm-census.mjs --detect # re-derives the 9-font list
node --test test/crossstitch-arm-census.test.js
```

Text `AB`, garment `full_back` (304 mm, so a 60 mm cap is never fit-scaled; every
cell's cap landed within 2% of the target), `splitSatin` on (the default),
weight `normal`. New tool `tools/crossstitch-arm-census.mjs` — it imports
`small-cap-census`'s calibration for the cap, and leaves `long-stitch-census.mjs`
untouched.

## Limits used

- **Record: 12.1 mm per axis** (`src/dst.js` MAX_DELTA 121 at 10 units/mm; the
  `machine.MAX_STITCH_MM` 12.1 that `exp.js` cites). This is what the encoders
  enforce and what `long-stitch-census` counts. A 45° arm of length L has axis
  delta L/√2, so an arm only breaks the record past L = 17.1 mm.
- **12.1 mm read as a length** (stricter reading, shown for completeness).
- **5.0 mm length** (`SPLIT_SATIN_ABOVE_MM`). Not a machine limit — the corpus
  threshold the satin split uses; it is where fix A would fire if it copied the
  satin rule.

An "arm" is a sewn segment at 45° (|dx| and |dy| within 0.15 mm). The longest
segment of any kind is *not* used: at small caps it is a cell-to-satin carry.

## Result 1 — at Studio sizes nothing breaks the record

Worst arm, mm (axis delta in brackets), by cap height:

| font | 10 mm | 15 mm | 25 mm | 40 mm | 60 mm | arm / cap | over 5.0 mm from cap | over 12.1 mm (length) from cap | over a record (12.1 mm/axis) from cap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| egyptian | 1.3 (0.9) | 1.8 (1.3) | 3.1 (2.2) | 4.9 (3.5) | 7.4 (5.2) | 0.124 | 40.5 mm | 97.9 mm | 138.5 mm |
| egyptian_small | 1.3 (0.9) | 1.8 (1.3) | 3.1 (2.2) | 4.9 (3.5) | 7.4 (5.2) | 0.124 | 40.5 mm | 97.9 mm | 138.5 mm |
| eloquent | 1.1 (0.8) | 1.7 (1.2) | 2.8 (2.0) | 4.4 (3.1) | 6.6 (4.7) | 0.111 | 45.0 mm | 108.8 mm | 153.9 mm |
| eloquent_small | 1.1 (0.8) | 1.7 (1.2) | 2.8 (2.0) | 4.4 (3.1) | 6.6 (4.7) | 0.111 | 45.0 mm | 108.8 mm | 153.9 mm |
| heavenly | 1.1 (0.8) | 1.7 (1.2) | 2.8 (2.0) | 4.4 (3.1) | 6.5 (4.6) | 0.110 | 45.3 mm | 109.6 mm | 155.0 mm |
| heavenly_small | 1.1 (0.8) | 1.7 (1.2) | 2.8 (2.0) | 4.4 (3.1) | 6.5 (4.6) | 0.110 | 45.3 mm | 109.6 mm | 155.0 mm |
| jaquarda_bastarda_9 | 1.6 (1.1) | 2.3 (1.6) | 3.8 (2.7) | 6.1 (4.3) | 9.1 (6.4) | 0.152 | 32.9 mm | 79.7 mm | 112.7 mm |
| jersey_15 | 0.9 (0.7) | 1.1 (0.8) | 1.8 (1.3) | 3.0 (2.1) | 4.4 (3.1) | 0.074 | 67.9 mm | 164.4 mm | 232.4 mm |
| noble | 1.1 (0.8) | 1.7 (1.2) | 2.8 (2.0) | 4.4 (3.1) | 6.6 (4.7) | 0.111 | 45.0 mm | 108.8 mm | 153.9 mm |

max arm/cap spread over caps >= 25 mm 4.27%; cap misses: none

- **No font exceeds a record, or even 12.1 mm as a length, at any size up to 60 mm
  cap.** The worst cell is jaquarda_bastarda_9 at 60 mm: 9.1 mm long, 6.4 mm axis.
- Arm length is linear in cap (arm/cap constant within 4.3%; the spread is DST
  rounding at 0.1 mm), so the "from cap" columns are the measured ratio solved
  for each limit, not a bisection. The 25–60 mm cells agree with them (e.g.
  egyptian 7.4 mm at 60 against 0.124 × 60).
- **Past the 5.0 mm line** (the satin split threshold): jaquarda_bastarda_9 from
  33 mm cap, egyptian from 41, eloquent/noble/heavenly from 45, jersey_15 from 68.
  Between 5.0 and 12.1 mm the stitch is long but sewable.
- **Past a record:** 113 mm cap (jaquarda_bastarda_9) to 232 mm (jersey_15). That is
  a hoop-filling letter, not a Studio-typical one.
- 10, 15 mm cells are noise-limited (a 0.7 mm cell on a 0.1 mm grid) and are
  excluded from the ratio fit.
- 10 fonts carry a cross grid; `jacquard_12` is the tenth and is not in the list
  because it never reaches a record. `jersey_15` is the only `double_cross` font
  here; its upright arms are one pitch long, shorter than the diagonal, so the
  worst arm is the diagonal.

## Result 2 — the long-stitch-census rows, with the cap they were sewn at

`long-stitch-census` runs `emMm: 18`; on a hoop-sized garment the engine fills
the hoop, so those rows are **not** 18 mm text. `--hoop` reproduces them (31.0 /
21.9 mm for egyptian, 24.0 / 17.0 for noble — to the 0.1 mm) and prints the cap:

```
font                  text  garment       cap mm  longest mm  arm mm  worst axis
egyptian              AB    full_back      253.7        31.0    31.0        21.9
egyptian              A     left_chest     168.6        20.6    20.6        14.6
egyptian_small        AB    full_back      253.7        31.0    31.0        21.9
egyptian_small        A     left_chest     168.6        20.6    20.6        14.6
eloquent              AB    full_back      198.2        21.6    21.6        15.3
eloquent              A     left_chest     131.7        14.4    14.4        10.2
eloquent_small        AB    full_back      198.2        21.6    21.6        15.3
eloquent_small        A     left_chest     131.7        14.4    14.4        10.2
heavenly              AB    full_back      284.5        31.0    31.0        21.9
heavenly              A     left_chest     189.2        20.6    20.6        14.6
heavenly_small        AB    full_back      284.5        31.0    31.0        21.9
heavenly_small        A     left_chest     189.2        20.6    20.6        14.6
jaquarda_bastarda_9   AB    full_back      137.4        20.6    20.6        14.6
jaquarda_bastarda_9   A     left_chest      95.9        14.4    14.4        10.2
jersey_15             AB    full_back      273.5        19.7    19.7        13.9
jersey_15             A     left_chest     134.0         9.6     9.6         6.8
noble                 AB    full_back      219.9        24.0    24.0        17.0
noble                 A     left_chest     131.5        14.4    14.4        10.2
```

So "worst 31.0 mm" is a **254–285 mm cap** on a full back, and "A at left chest,
20.6 mm" is a 169–189 mm cap. The defect is real there, but it is a very large
letter. Whether the Studio can place text that tall is a product question for
Kent, not measured here.

## Sketch of two fixes (not implemented)

**A — split long arms into sub-stitches.** In `crossFill`, emit each arm as
`ceil(L / Lmax)` collinear segments (or let the encoder's existing record split
do it at the DST level, which already happens for `.dst`/`.exp`).
- *Look:* unchanged. The X is the same X; the extra penetrations lie on the arm
  and are hidden by the thread. Same trick as `splitSatin`'s collinear points,
  though a satin split uses a wave to avoid trenching and a cross arm needs none.
- *Cost:* only fires above the limit, so **zero change at every size in Result 1**.
  Splitting to the record (arm <= 17.1 mm) turns the 31 mm arm into 2 segments,
  +1 penetration per over-limit arm: egyptian AB on a full back has 82, so about
  +82 on 520 stitches (an estimate from the census counts, not a measured build).
  Splitting to 5.0 mm instead would cost 7 segments per 31 mm arm, ~+490. A
  12-31 mm unanchored arm floats and snags, so the real `Lmax` is a fabric
  question (gate 1); the record is only the floor.
- *Risk:* penetrations pile along the diagonal where neighbouring arms cross at
  the cell centre; the split points must not coincide there.

**B — fixed-mm lattice pitch.** Make the cell a fixed size in millimetres.
- *Cost:* the cell count grows as (cap/pitch)², against fix A's roughly linear
  growth, and **the pitch is a physical constant**: ROADMAP gate 1 says no sew-out,
  no constant.
- *Look:* changes. The detected lattice matches the pixel-art outline for
  99.6–100% of vertices (`crossfill.js` header); an arbitrary pitch cuts across
  the outline cells and the glyph edge goes ragged. A softer variant keeps
  alignment: subdivide each glyph cell into `k × k` with `k = ceil(pitch / Pmax)`,
  so edges still land on cell borders. Cost is `k²` times the crosses, and the
  letter still looks like cross-stitch but finer, which is a design change to
  every affected font.
- *Verdict:* A is the cheap, look-preserving answer to the *machine limit*. B
  answers "how big should a cross be on cloth", which only a sew-out settles.

## Not done

No sew-out, no change to `crossfill.js` or any default, no quality claim.
The 5.0 mm line is a corpus threshold, not a fabric measurement.
