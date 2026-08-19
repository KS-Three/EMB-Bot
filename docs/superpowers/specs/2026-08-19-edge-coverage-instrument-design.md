# Edge coverage — an instrument, and the tolerance the pro sets (2026-08-19)

**Design spec.** Approved approach A of three offered 2026-08-19. Kent's report:
shapes show bare fabric at their edges, worst on the last layer, and he wants
edge borders, jump behaviour and detail cleanliness improved.

This document specifies the **instrument only**. It changes no engine behaviour,
flips no flag, and invents no millimetre. That is deliberate: "how much bare
fabric at an edge is too much" is a cloth question, and ROADMAP gate 1 says
cloth settles it. The dodge is to measure a professional's own files with the
same instrument and let the pro's number be the tolerance.

---

## 1. The question, stated so it can be answered

> Along the boundary of a shape, how much of the band just inside the edge has
> no thread on it — and how does that compare to what a professional digitiser
> leaves on the same artwork?

Two numbers per shape per side: the **bare fraction** of the edge band, and the
**longest contiguous bare arc** along the boundary, in mm.

The arc is the one that matters. Five percent of a band left bare as scattered
pinpricks is invisible; five percent as one 8 mm strip down the side of a letter
is the defect. `barecircle.py` already makes exactly this argument for shape
interiors — "a hundred pinprick slivers along a boundary are invisible while one
3 mm disc in the middle of a star is the whole defect"
(`digitizer/digitizer_core/barecircle.py:14-16`) — and then declines to make it
for edges. See §3.

---

## 2. Why this is not already answered

### 2.1 The scorecard has no edge term at all

`WEIGHTS = {coverage 20, direction 20, sttype 20, density 15, underlay 10,
travel 15}` (`digitizer/tools/pro_parity/scorecard.py:103-104`). None is an
outline or boundary term. `enginefidelity.py:7-10` states the consequence
directly: a 20 mm circle RDP'd into a 20-gon and a faithful circle score
identically. The 42.5 parity baseline is structurally incapable of noticing
what Kent is describing.

### 2.2 The bare-fabric instrument is blind to edges by construction

`barecircle.widest_bare_circle` computes

```
clearance = min(dist_out, dist_thread - thread_w/2)
```

(`digitizer/digitizer_core/barecircle.py:133-137`), where `dist_out` is the
distance to outside the polygon. A point 0.3 mm inside the boundary therefore
cannot score above 0.3 however bare it is. **A continuous uncovered band around
a whole perimeter is indistinguishable from flawless work.** That ruling was
made for the contour tier's bare-core problem and is correct there; Kent's
symptom is the case it discounts.

It is also wired into one tier only: `stage6_contour.py:68` is the sole importer
in `digitizer_core/`, plus a contour-only finding at `preflight.py:1546`. Tatami,
satin, scanline, blend and streamline never call it.

### 2.3 The preflight coverage map only looks up

`_coverage_map` (`preflight.py:1084`) rasterises every needle-down stitch into
coverage units where 1.0 is one full layer — the right raw material. But
`_coverage_findings` (`preflight.py:1167`) fires only on **over**-coverage (2.5
warn / 3.5 block, the pucker case), and `_COVERAGE_FLOOR_UNITS = 0.25`
(`preflight.py:223`) drops every cell below 0.25 out of the statistics before
percentiles are taken. Bare fabric is filtered out of the instrument before it
is measured.

---

## 3. A candidate mechanism, honestly bounded

`stage6_fill._row_spans` (`digitizer/digitizer_core/stage6_fill.py:126-132`):

```python
n_rows = max(1, int(math.floor((maxy - miny) / row_mm)))
for i in range(n_rows + 1):
    y = miny + row_mm * (i + 0.5)
    if y > maxy:
        break
```

Row **ends** land exactly on the boundary — verified, and the docstring at
`:295` says so. Row **positions** are a different story, and the two shape edges
are not treated alike:

- **Leading edge.** First centreline 0.20 mm inside at the shipped
  `FILL_ROW_MM = 0.40` (`machine.py:49`). With a 0.40 mm thread ribbon
  (`COVERAGE_THREAD_W_MM`, `machine.py:582`) the thread edge lands flush on the
  boundary. Bare: zero. Deliberate, and documented at `stage6_fill.py:117-119`.
- **Trailing edge.** The last centreline sits `d = maxy - y_last` inside, and
  `d` is whatever `(maxy - miny) mod row_mm` happens to be — uniform on
  `[0, 0.40)`, controlled by nothing. Bare band is `max(0, d - 0.20)`, so
  **0 to 0.20 mm, expected 0.05 mm**, varying per shape and per fill angle.

The same defect exists in the browser engine from the other side: `src/fill.js:55`
starts rows at `minY` itself, so the first ribbon half-overhangs the polygon and
the trailing edge still runs short by the same uncontrolled leftover.

**Do not oversell this.** 0.20 mm is small — a healthy contour shape's worst
interior bare spot measures 0.067-0.129 mm (`machine.py:203-215`), so this is
the same order, not an order worse. It is a real asymmetry with no reason to
exist, and it is almost certainly **not** the whole of what Kent sees. Larger
candidates the instrument must be able to see and attribute:

- **Segmentation shrink** — our stage-4 polygon landing inside the artwork's
  ink. Unbounded, and invisible to any measure that uses our own polygon as
  ground truth. This is why §5 measures against the artwork as well.
- **Tier choice** — the scanline tier does not guarantee row ends at all: a span
  stops wherever tone stops admitting it (`stage6_scanline.py:187-193`).
- **Pull compensation** — stage 5 grows free edges before stage 6 sees them
  (`stage5_overlap.py:218`), so a shortfall may be absorbed, or not, depending
  on the preset. `directional_comp` is default-off and sew-out-gated
  (`config.py:369`), so it is out of scope for this lane.

The instrument's job is to say which of these dominates. It is not built to
confirm the row-phase theory.

### 3.1 A claim that should be retired either way

`config.py:683-689` justifies `border = "off"` partly with:

> "our tatami fill has no ragged edge to cover (measured starvation 0.00 mm with
> zero variance on 13 real letterforms at three sizes, because `_row_points`
> puts both row ends on the shape's edge by construction)"

Two problems. The reasoning covers row **ends** and is silent about row
**positions**, and the bare strip is along the edges *parallel* to the rows,
which `_row_points` never touches. And the measurement itself appears **exactly
once in the repository** — in that comment. Grepped across `.py` and `.md`:
no instrument, no doc, no fixture, no test.

**This does not overturn `border = "off"`.** That default rests independently on
corpus law 39 — 11 of 67 area-fill regions (16%) carry a covering satin column,
a second instrument, confidence high
(`docs/corpus-laws-round3-2026-08-01.md:546-555`). Only the "nothing to cover"
leg is unfounded. This spec's output is what should replace it.

---

## 4. What the harness can and cannot supply

Established by reading `digitizer/tools/pro_parity/` in full.

**The pro side has no polygons anywhere.** Only stitch files. Every "pro
boundary" in the repo today is derived from the pro's own stitches by
rasterise-then-outline. There is no independent pro-side shape.

**The recon lane is barred from this measurement.** Its `art.png` is
reconstructed from the pro's own stitches (`prep_all.py:836`), so our polygons
there are transitively derived from the pro's answer. Grading the pro against it
grades the pro against itself.

**The real lane is the only valid one:** 15 designs (`prep_both.py:68-99`), real
customer artwork through `real_art.prepare`, which does a uniform-bar crop and
nothing else (`real_art.py:16-33`). It requires `PRO_PARITY_ROOT` on Google
Drive — `G:/My Drive/EMB-Bot/Embroidery Files`, confirmed present on Kent's
machine 2026-08-19, 13 job folders. Against the git-tracked zip alone the real
lane fails 0/15 (`prep_all.py:78-82`), so **this measurement cannot run in a
cloud session.**

**Registration already exists** and is translation-only, never rescaling:
`artfidelity.best_iou` at `RES = 10.0` px/mm, `THREAD_W_MM = 0.40`, ±4.0 mm
search at 0.4 mm steps (`artfidelity.py:33`, `:111-138`).

**The seam is `gateprobe.py`.** It already registers both sides, translates our
polygons into the registered frame, joins per shape, emits a CSV, and touches no
score (`gateprobe.py:87-112`, `:176-193`, `:311-325`).

---

## 5. The instrument

New standalone probe, `digitizer/tools/pro_parity/edgeband.py`. Real lane only.

### 5.1 Two band sources, deliberately

Measuring only against our own polygons would let our segmentation define where
"the edge" is — the same circularity that disqualifies the recon lane. So both:

**(a) Artwork band — the headline.** Band is the customer artwork's ink boundary
(`artfidelity.art_mask`) eroded inward by `W`. Independent of our segmentation,
identical for both sides. Answers: *did thread reach the edge the artwork drew?*

**(b) Per-shape band — the attribution.** Band from each polygon in
`ours_regions.json` (`shape_id, area_mm2, thread, tier, bounds, wkt` —
`prep_all.py:766-771`), translated into the registered frame as `gateprobe` does.
Answers: *which shapes are short, and in which tier?* Carries the caveat that the
polygon is ours on **both** sides, so it asks whether the pro laid thread where
our shape claims its edge is.

Where (a) and (b) disagree is itself the segmentation-shrink signal from §3.

### 5.2 Band widths

Reported at **W = 0.2, 0.4 and 0.8 mm**, all three, every run. Picking one would
be inventing a physical constant, which gate 1 forbids. Three widths also
separate a thin uniform shortfall (visible at 0.2, washed out at 0.8) from a
genuinely wide gap.

### 5.3 Metrics, per band, per width, per side

| Metric | Definition |
|---|---|
| `bare_frac` | Band area with no thread ribbon over it, as a fraction of band area |
| `bare_arc_max_mm` | Longest contiguous bare arc — see the definition below |
| `bare_arc_p90_mm` | 90th percentile arc, so one outlier does not carry the design |
| `band_mm2` | Band area, so a design's shapes can be weighted honestly |

**Arc definition, stated so two implementations cannot differ.** Boundary rings
are extracted from the band's source mask with `cv2.findContours` (outer ring
and every hole, each ring walked separately). A boundary pixel is **bare** when
the inward normal segment of length `W` from that pixel is entirely free of
thread ribbon. An **arc** is a maximal run of consecutive bare pixels along one
ring, and its length is the summed pixel-to-pixel distance in mm along that ring.
Rings close, so a run spanning the start index wraps. `bare_arc_max_mm` is the
longest such arc over all rings of the shape; a shape with no bare pixel reports
0.0, never null.

Thread masks come from the existing readers — `artfidelity.pro_mask` for the pro,
`enginefidelity.engine_mask` for ours, both at 10 px/mm — so both sides are
measured by one code path. Same rule as `pro_meta`: one builder, not two copies
(the defect fixed in `5328257`).

### 5.4 Output

- `edgeband_<slug>.csv` — one row per (shape, width, side).
- A per-design summary line, and a corpus table over all 15.
- **No `score.json` change, no new `WEIGHTS` key.** Adding a scored component
  rebalances every historical score; `scorecard.py:34-40` documents what that
  cost the last time and why `score_raw` / `parts_raw` exist.

---

## 6. What this lane does not do

- No engine change. Not the row phase, not `src/fill.js`.
- No flag flipped. Not `border`, not `directional_comp`, not `chain_links`.
- No constant set or moved. Not `BORDER_SEAM_OFFSET_MM`, not `FILL_ROW_MM`.
- No claim that the row-phase asymmetry is the defect Kent sees.

Fixes are the next lane, chosen from what this one measures.

---

## 7. Known blind spots, carried forward

1. **`art_mask` thresholds dark-on-light.** Light ink on a dark ground reads as
   solid ink, so both sides get charged for correctly leaving it unsewn
   (`boundarywhere.py:19-22`).
2. **Registration is translation-only** and never rescales
   (`selfconsistency.py:24-27`). A size mismatch shows up as edge error on every
   shape at once — a signature to watch for, not a number to trust.
3. **Instrument floor.** `enginefidelity` treats 0.35 mm Hausdorff / 0.15 mm mean
   boundary as its noise floor (`:63-64`). Differences below ~0.15 mm here should
   be assumed noise until a floor is measured for this instrument specifically.
4. **The per-shape band uses our polygon on both sides.** Stated in every table
   that reports it.
5. **`bare_frac` at W = 0.2 mm is near the raster's own resolution** (10 px/mm =
   0.1 mm/px, two pixels across the band). Reported, but the 0.4 and 0.8 columns
   are the trustworthy ones for fractions; arcs are less affected.

---

## 8. Acceptance

The instrument is done when all of these hold:

1. It runs over all 15 real-lane designs and emits both bands at all three
   widths, in a pinned worktree.
2. **Both sides are measured by one code path** — mutation-tested: hand-rolling
   a second mask reader fails a test.
3. A synthetic fixture with a known bare strip of known width measures it back
   within one pixel — the instrument is calibrated against a ground truth it
   cannot argue with, before it is pointed at real work.
4. A shape with full coverage reports `bare_arc_max_mm` at or near zero, and a
   shape with a deliberately deleted last row reports the strip's real length.
5. The corpus table states, per design, the pro's arc against ours.
6. No test in the existing suite changes result. Baseline on this branch is
   **3 failed / 1187 passed** — `test_flat_lane_byte_identical[enthusiast_logo]`,
   `test_pushcomp[logo_whitebg-towel]`, `test_stage2_photo_segment[enthusiast_logo]`,
   the known Windows golden divergence (measured 2026-08-19, `pytest -q -n auto`).

Acceptance point 3 is the one that matters most. An instrument that has never
been shown a known answer is how this repo got a "0.00 mm starvation" number
with nothing behind it.

---

## 9. Open, deliberately

- **Whether the pro's own edges are tight.** If the pro leaves comparable bare
  band, the defect is elsewhere and this lane's value is having ruled it out.
- **Whether `bare_arc_max_mm` correlates with Kent's eye.** The Foundation phase
  exit condition is agreement with his visual ranking, and no metric in this repo
  has earned that yet.
- **Band width for any future gate.** Deliberately unresolved. Cloth settles it.
