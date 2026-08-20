# Edge coverage, measured — a confound, and 44 shapes (2026-08-19)

First run of `tools/pro_parity/edgeband.py` over the real-art lane, 15 designs,
both sides, band widths 0.2 / 0.4 / 0.8 mm. Instrument and method:
[`docs/superpowers/specs/2026-08-19-edge-coverage-instrument-design.md`](superpowers/specs/2026-08-19-edge-coverage-instrument-design.md).

**Headline: the artwork band does not measure what it was built to measure, and
the per-shape band does. On the designs where the artwork band can be trusted at
all, we do NOT leave more bare edge than the professional. What we do have is a
tail — 44 of 621 shapes carry a bare edge run over 1 mm, and the worst have
half their edge band bare.**

---

## 1. The artwork band is confounded by registration, not by craft

The first table read as though the professional were catastrophically worse than
us. `gaulke_roofing_hat`: pro 80.10 mm longest bare arc against our 0.64 mm.
`becker_hat_large`: pro 78.42 against our 26.13. A professional does not leave
80 mm of bare edge, so the number is the instrument's, not the pro's.

`artfidelity.py` over the same directories says exactly what went wrong:

| design | art_iou | art_missed | shift found | edgeband pro frac, W=0.4 |
|---|---|---|---|---|
| hotel_fremont_hat | 0.973 | 0.002 | 0.0, 0.0 | **0.000** |
| hotel_fremont_patch | 0.972 | 0.002 | 0.0, 0.0 | **0.000** |
| bridge_lc | 0.953 | 0.025 | 0.0, 0.0 | 0.187 |
| bridge_hat | 0.950 | 0.021 | 0.0, 0.0 | 0.125 |
| tires_hat_3d | 0.930 | 0.010 | 0.0, 0.0 | 0.050 |
| precision_drone | 0.795 | 0.059 | 0.0, -0.8 | 0.163 |
| mfab_hat | 0.743 | 0.006 | 0.0, 0.0 | 0.003 |
| becker_lc_large | 0.588 | 0.107 | 0.4, -0.4 | 0.205 |
| becker_hat_large | 0.583 | 0.113 | 0.4, -0.4 | 0.216 |
| becker_beanie | 0.474 | 0.037 | 0.0, 0.0 | 0.046 |
| gaulke_roofing_hat | 0.363 | 0.328 | **4.0, 2.4** | **0.440** |
| gaulke_roofing_lc | 0.337 | 0.345 | **3.2, 2.8** | **0.432** |

The pro's edgeband number tracks `art_iou` and the alignment shift, not edge
craft. Both Gaulke designs **pinned the shift search at its own window edge** —
`SHIFT_MM = 4.0`, and the search returned 4.0 and 3.2 with 2.4 / 2.8 on the
other axis. `enginefidelity.py:23-26` warns about precisely this failure on
re-composed layouts. An artwork sitting several millimetres off its stitches
puts *every* boundary pixel far from thread, and the band reports the
misalignment as bare fabric.

**Precondition the spec did not state, and this run discovered:** the artwork
band is only interpretable where the artwork registers against that side's
stitches. A practical filter is the pro's own `art_missed` — the fraction of
artwork ink the pro laid no thread on. Above roughly 0.03 the edgeband pro-side
figure is measuring registration.

### 1.1 On the clean subset, we are not worse

Seven designs have pro-side `art_missed` <= 0.03. Bare fraction of the edge band
at W = 0.4 mm:

| design | pro | ours | |
|---|---|---|---|
| bridge_hat | 0.125 | 0.051 | ours better |
| bridge_lc | 0.187 | 0.082 | ours better |
| tires_hat_3d | 0.050 | 0.039 | ours better |
| hotel_fremont_hat | 0.000 | 0.008 | ours worse |
| hotel_fremont_patch | 0.000 | 0.012 | ours worse |
| mfab_hat | 0.003 | 0.017 | ours worse |
| mfab_lc | 0.004 | 0.016 | ours worse |

Three better, four worse, and the mean runs in our favour (0.053 pro against
0.032 ours) only because Bridge drags it. Longest bare arcs on this subset are
tiny on both sides — nothing over 2.7 mm.

**There is no evidence here that we leave more bare edge along an artwork
boundary than the professional does.** That is a measured negative on the
headline question, and it should stop anyone rebuilding this comparison
expecting a different answer without first fixing registration.

---

## 2. The per-shape band is clean, and it found something

The per-shape band takes our polygon against our own stitches. **No artwork, no
registration, no shift search** — so §1's confound cannot touch it.

621 shapes across the 15 designs, at W = 0.4 mm:

- median bare fraction **0.004**, p90 **0.133**
- median longest bare arc **0.00 mm**, p90 **0.00 mm**
- **44 shapes (7.1%) carry a bare arc over 1 mm**

Over ninety percent of our shapes have no measurable bare edge at all. The
defect is a tail, not a baseline — which is itself worth knowing, because it
means no global constant is the cure.

The worst, at W = 0.4:

| design | shape | area mm² | arc mm | bare frac |
|---|---|---|---|---|
| becker_hat_large | Sf6a92112 | 344.2 | 24.32 | 0.487 |
| becker_hat_large | S92a90056 | 1067.0 | 22.90 | 0.057 |
| becker_chest_small | Sc32ce326 | 192.2 | 16.28 | 0.628 |
| becker_beanie | S19262c07 | 206.6 | 12.69 | 0.535 |
| becker_beanie | Sead76620 | 634.9 | 11.92 | 0.045 |
| becker_chest_small | Sed979fc2 | 576.2 | 10.12 | 0.047 |
| becker_hat_small | Sc32ce326 | 192.2 | 9.26 | 0.480 |
| becker_hat_small | Sed979fc2 | 576.2 | 8.10 | 0.029 |

By design: becker_hat_small 10, becker_chest_small 9, precision_drone 9,
becker_beanie 6, becker_hat_large 6, mfab_hat 2, mfab_lc 1, bridge_hat 1.

**Two distinct failures are visible in that table, and they are not the same
defect.**

1. **Half the edge gone.** `frac` around 0.5-0.6 on shapes of 190-350 mm².
   Sc32ce326 has 62.8% of its edge band bare. That is not an edge finish
   problem; something declined to sew most of that shape's perimeter.
2. **One long run on an otherwise healthy shape.** S92a90056, 1067 mm², bare
   fraction 0.057 but a single **22.9 mm** unbroken bare arc. Ninety-four
   percent of its edge is fine and one stretch the length of a thumb is not.
   This is the shape of the complaint that started this lane.

The same shape ids recur across designs (Sc32ce326 and Sed979fc2 appear in both
becker_chest_small and becker_hat_small), which is expected — those are the same
artwork digitised at two sizes — and it means the cause is in how we treat that
shape, not in one bad run.

---

## 3. What this rules out

**The row-phase asymmetry is not the mechanism.** The spec's candidate —
`_row_spans` leaving 0 to 0.20 mm at the trailing edge (`stage6_fill.py:126-132`)
— is bounded at 0.20 mm by arithmetic. It cannot produce a bare fraction of 0.63
at a 0.4 mm band, and it cannot produce a 22.9 mm unbroken run. The asymmetry is
still real and still has no reason to exist, but it is **not** what Kent is
seeing, and it should not be fixed on the theory that it is.

Whatever is emptying 60% of a 192 mm² shape's edge is a tier or emission
failure, and that is where the next lane should look.

---

## 4. Caveats that must travel with these numbers

1. **Everything in §1 above `art_missed` 0.03 is registration, not craft.** Both
   Gaulke designs pinned the shift search at its window edge.
2. **`art_mask` thresholds dark-on-light** (`boundarywhere.py:19-22`), so light
   ink on a dark ground reads as solid and both sides are charged for correctly
   leaving it unsewn.
3. **Registration is translation-only and never rescales**
   (`selfconsistency.py:24-27`). `art_mask` sizes the artwork to the *stitch
   span*, so a side that omits an element rasterises the artwork at the wrong
   scale — a likely contributor to the Becker family's 0.58 IoU.
4. **The per-shape band uses our polygon on both sides**, so it is a statement
   about our own emission against our own regions. That is what makes it immune
   to §1 and also what stops it saying anything about the pro.
5. **`tier` is empty in `ours_regions.json`, and not by accident** — 621 shapes,
   no tier string, so tier attribution was impossible. `prep_all.py:767` writes
   `r.meta.get("tier")`, and that key is set only by a user `shape_overrides`
   entry (`regions.py:334-342`). It is an INTENT slot — "force this shape to
   this tier" — not a record of what was sewn. Empty is its correct value when
   nobody overrode anything. The tier actually used is chosen inside
   `stage7_sequence.stitch_one`, which returns early at `:868` (run tier),
   `:895` (satin) and `:1192` (reactive rescue), and is not written per shape
   anywhere. Attribution needs that decision recorded, not this field
   populated — a different and slightly larger change than it first looks.
6. **W = 0.2 mm is two pixels** at `RES = 10` px/mm. Treat the 0.4 and 0.8
   columns as the trustworthy ones for fractions.
7. **A prior clip in the instrument, fixed before this run** (`df7a34e`): shapes
   reaching past the design-wide stitch bbox had their bare edge cut off and
   under-reported — 0.00 mm against a true 17 mm on a synthetic case. Any
   edgeband number produced before that commit is void.
8. **Minor:** the CLI accepts `manifest.json` as a design directory when the
   shell glob hands it one, and prints `(no artifacts)`. Harmless, cosmetic.

---

## 5. What to do with this

1. **Do not fix the row phase expecting it to help.** §3.
2. **Look at Sc32ce326 and Sf6a92112 directly** — same artwork, two sizes, half
   the edge band bare. Find what declined to sew that perimeter. That is the
   defect this lane was started to find.
3. **Record the tier `stitch_one` actually chose**, per shape, so the next run
   can say which tier starves. Not the same as populating `ours_regions.json`'s
   `tier` field, which is a user-override slot and is correctly empty — see
   caveat 5.
4. **Do not compare pro against ours on the artwork band until registration is
   fixed** — or restrict to `art_missed <= 0.03` and say so every time.
5. The instrument itself needs no further work for these questions.
