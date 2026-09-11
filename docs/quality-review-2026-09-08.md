# Digitizing quality review — fourteen changes, ranked — 2026-09-08

Kent, 2026-09-08: *"Let's review the progress that's been made on emb-bot so
far. I want you to identify 10-15 changes that are not necessarily low hanging
fruit, but provide the largest improvement to the overall quality of the
digitizing quality."*

This file is the record: where the auto-digitizing area stands after the
2026-09 work, three measurements made on the shipped tree today that the
ranking rests on, the fourteen changes in the order the evidence ranks them,
three cheap defects an audit pass found on the browser lane, what was left
off on purpose, and Kent's picks. Everything with a number was measured on
`main` at `bca8434` (#423) in a fresh `python3.12` venv; commands are at the
bottom. Nothing in the engine changed.

**Kent's picks, 2026-09-08:** start with items 1 and 2 together (the real-logo
lane with thin-stroke retention) and item 3 (sub-pixel edge extraction). Each
opens with a plan doc and an instrument PR before any engine change.

---

## 1. Where quality stands

Kent's own read is the best summary. The stitch-outs are about 60% of the way
to Ember parity; *"shapes are accurate but smoothness is not"*; and whole
elements go missing (`docs/kent-review-2026-08-27.md`, eight and seven of
fourteen designs respectively). The two instruments that exist score the same
designs near 80 and agree with each other at rho 0.405, so most of the
missing 40% is craft the yardstick cannot see. The one physical sew-out
(2026-09-01, 6/10) found density, seams, sequencing and a bare perimeter.
Density and seams have since been ruled and built, sequencing shipped as
borders-last, and the perimeter cap is built but off.

The pattern across the 2026-09 work is that the remaining problems sit
upstream of the stitch emitters:

- six of seven real customer logos route down the photo segmenter;
- thin strokes are dropped or blobbed before any tier sees them;
- edges are traced from a binary raster, and the curve fix is gated off on
  every design it was asked for;
- satin loses its widest and its branchiest shapes to tatami.

The five flags waiting on a decision are real but small next to those.

An audit pass in the same session ran all ten real-art fixtures through
`digitize()` at the Studio's shipped defaults (80 mm / left_chest, Becker at
100 mm, Fremont 92.5 mm / patch). Its table, kept because no single document
carries these side by side; Becker's row reproduces my own run to the stitch.

| fixture | class | src px/mm | regions | enclosed bg left bare | satin / fill / run shapes | stitches | trims | cones | grade |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| `enthusiast_logo` | flat | 17.1 | 31 | 0.7% | 12 / 1 / 14 | 2,459 | 22 | 2 | B 88 |
| `becker_marine_logo` @ 100 | flat | 1.45 | 17 | **40.8%** | **1** / 9 / 0 | 11,373 | 23 | 1 | B 88 |
| `logo_hotel_fremont` @ 92.5 | gradient | 27.0 | 55 | 0 | 44 / 7 / 4 | 17,400 | **114** | 3 | C 64 |
| `logo_bridge_bar` | gradient | 3.5 | 74 | 0 | 29 / 4 / **41** | 14,499 | 120 | **13** | F 0 |
| `logo_golden_tee` | gradient | 21.8 | 37 | **42.4%** | 32 / 0 / 1 | 6,716 | 60 | **14** | F 0 |
| `logo_gaulke_roofing` | gradient | 16.1 | 56 | 15.7% | 2 / 5 / 3 | 10,229 | 30 | 4 | F 4 |
| `drone_render` | gradient | 9.6 | 74 | 1.0% | 44 / 13 / 7 | 16,454 | 82 | **22** | F 0 |
| `logo_script_tires` | photo_scene | 13.2 | 6 | 4% | 3 / 1 / 0 | 2,340 | 8 | 1 | A 100 |

Two of its readings are load-bearing below: the largest dropped content by
AREA on real logos is the enclosed-background default, not a bug (item 9),
and in-shape trims dominate the trim problem (Fremont 70 of 113 in-shape, one
shape taking 34).

*(measured 2026-09-08 — audit pass, `digitize()` at shipped defaults)*

## 2. Three measurements the ranking rests on

### 2a. The curve-refinement gate reaches 2 of 29 fixtures at 80 mm

`curve_turn_deg` (defect 22, Kent's flip 2026-09-03) re-reads each
Douglas-Peucker edge against its raw arc, but only above
`stage4_vectorize._CURVE_MIN_PX_PER_MM` = 20, because below that the
one-pixel floor read raster texture as arcs. Source width over the design
width, for every fixture the scorecard runs:

| fixture | px | px/mm at 80 mm | refines? |
|---|---:|---:|---|
| `logo_hotel_fremont.webp` | 2500 | 31.2 | yes |
| `logo_golden_tee.jpg` | 2193 | 27.4 | yes |
| `logo_script_tires.png` | 1585 | 19.8 | **no, by 0.2** |
| `drone_render.png`, `logo_drone_thermal_badge.png` | 1536 | 19.2 | no |
| `enthusiast_logo.png` | 1400 | 17.5 | no |
| `logo_gaulke_roofing.png` | 1284 | 16.1 | no |
| `screenshot_phone_ui_golke.jpg` | 1020 | 12.8 | no |
| `logo_whitebg`, `logo_alpha`, `ribbon_curve`, `bg_uncertain` | 800 | 10.0 | no |
| `logo_bridge_bar.jpg` | 400 | 5.0 | no |
| `becker_marine_logo.png` | 146 | 1.8 | no |

Every design Kent called jagged, sawtoothed or not smooth on 2026-08-27
(`logo_whitebg`, `ribbon_curve`, `becker_marine`, `logo_script_tires`,
`enthusiast_logo`) sits under the gate, so the round-curves fix is
byte-identical on exactly the designs it was asked for. The gate is correct as
a guard against a staircase; the staircase is the thing to remove (item 3).

*(measured 2026-09-08 — PIL image sizes over `target_width_mm`)*

### 2b. Becker's MARINE sews tatami at 100 mm with `satin_per_stroke` ON, refused by the width cap

Per-shape sewn tier read off the emitted plan (`tools/sewn_tiers.py`, this
PR), both flag settings, 100 mm / left_chest:

| shape | mm² | flag OFF | flag ON | `stroke_verdicts` reason |
|---|---:|---|---|---|
| `S92a90056` (BECKER outline) | 1022.4 | fill | fill | `dt_irregular`, carries over-cap strokes |
| `Sf62099db` | 211.4 | fill | fill | `dt_p90_cap`, strokes p90 5.26–7.33 |
| `Sdd5f27fb` | 210.9 | fill | fill | every stroke `dt_p90_cap`, p90 7.06–8.00 |
| `Sa587cbf9` | 184.0 | fill | fill | `dt_p90_cap`, p90 5.05–5.73 |
| `Sd77c18ad` | 178.7 | fill | fill | `dt_p90_cap`, p90 5.69–5.83 |
| `S35d83e6d` | 164.2 | fill | fill | `dt_p90_cap`, p90 5.39–6.12 |
| `S14230a1b` (the I) | 75.2 | satin | satin | satin |
| `S6d3d3130`, `Sc9b48e5a`, `Sf48a80bd` | 34.2, 22.7, 21.9 | fill | **satin** | `dt_irregular`, flag promotes |

Stitches 11,373 → 11,205, trims 23 both ways. The flag promotes three shapes
totalling 78.8 mm², none of them a letter of MARINE. The letters are refused
by `dt_p90_cap`, the 5.0 mm width ceiling, not by irregularity. At 80 mm the
same letters are 4.2–4.9 mm and three of five sew satin; two
(`Sf795e8d1` 130.4 mm², `Saee8fbe5` 129.7) still hit the cap and sew tatami.
That is the 88%-at-80 / 7.6%-at-100 flip DOCTRINE records, and its mechanism
is the cap.

**Correction to `docs/kent-review-2026-09-03.md`, Becker item 3.** That entry
quotes MARINE's strokes at 2.6–3.2 mm and MASTER_SCOPE area 1 repeats it. The
same distance transform on the artwork at 100 mm, read on the skeleton, gives
per-letter half-widths of p50 2.45–2.80 mm and p90 2.71–3.55 mm, i.e. widths
of 5.4–7.1 mm, matching the classifier's doubled p90. The 2.6–3.2 figure is
the half-width, the raw `dist/scale` value `textcluster.py`'s docstring warns
is a radius. The letters are 5–7 mm columns. The review's conclusion — the
pro satins all six — stands; the reason we do not is the cap, not
decomposition.

*(measured 2026-09-08 — `tools/sewn_tiers.py`, `tools/stroke_verdicts.py --width 100 --all`, and a skeleton distance transform on the source PNG upscaled to 4 px/mm)*

### 2c. The pro's sewn Becker files carry columns past the 5.0 mm cap

`tools/satin_columns.py`'s cross detector over the five commissioned files in
`testdata/reference/`, width percentiles and the share of crosses over three
ceilings:

| file | crosses | p50 | p90 | p95 | p99 | max | > 5.0 | > 6.0 | > 7.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `becker_hat_polo_large_beckers_logolc.dst` | 4,811 | 2.52 | 5.00 | 5.20 | 6.10 | 8.50 | 7.4% | 1.1% | 0.4% |
| `becker_hat_polo_large_beckers_logo_hat.dst` | 5,088 | 2.66 | 5.20 | 5.50 | 6.41 | 9.10 | 22.7% | 1.4% | 0.6% |
| `becker_hat_small_beckers_logo_hat_smaller.dst` | 5,128 | 2.63 | 5.20 | 5.50 | 6.41 | 9.10 | 22.3% | 1.4% | 0.6% |
| `becker_chest_small_beckers_logo_lc_2_a.dst` | 3,999 | 2.09 | 4.10 | 4.20 | 5.00 | 7.00 | 1.0% | 0.2% | 0.0% |
| `becker_hat_small_beckers_logo_hat_2_a.dst` | 3,999 | 2.09 | 4.10 | 4.20 | 5.00 | 7.00 | 1.0% | 0.2% | 0.0% |

On the large files a fifth of the pro's satin crosses are wider than our
ceiling, nearly all of them in the 5.0–6.5 mm band, with a tail to 9 mm.
These files were sewn on garments, which is the evidence class that settled
`FILL_ROW_MM` (DOCTRINE, fill row spacing). DOCTRINE's ruling that the bare
number must not be raised stands — both routes tried on 2026-09-02 broke the
per-station overlap guard — and this measurement does not reopen the number.
It says what the band above the cap is worth: every MARINE letter at hat and
chest sizes.

*(measured 2026-09-08 — `tools.satin_columns.passes_from_file` + `_crosses`, percentiles over all crosses)*

## 3. The fourteen changes, ranked by what they buy on a real logo

Gates per `ROADMAP.md`: G1 physical constants, G2 stage-0 recalibration, G3
default-OFF tier flips, G4 raw agreement numbers.

### 1. A lane for real logos: stop routing anti-aliased flat art through the superpixel segmenter

Stage 0's gradient gate (`GRAD_VAR_GRADIENT_MIN` 0.0015) was calibrated on
synthetic fixtures; real logos read 137× to 4090× over it on ordinary
anti-aliasing or JPEG ringing (`docs/classifier-misroutes-real-logos-2026-08-15.md`).
So real logos take the SEEDS+RAG lane, which cannot hold a sub-millimetre
stroke, has no colour cap, and never got the flat lane's phantom-blend
dissolve. That routing is behind the Fremont tagline blobs, Bridge Bar's grey
halo cones, and the colour slider not meaning what it says.

| evidence | figure |
|---|---|
| pro-parity logos routed gradient at confidence 1.00 | 10 of 15 |
| forced-flat gain, mean per design, chance-corrected | +4.85, better on 8 of 10, corpus +3.2 |
| committed real logos routed gradient | 6 of 7 |

Forcing flat is not the fix on its own: today it drops Fremont's rope and
EST 1895 outright (`DROPPED_SMALL_SHAPES`), which is why this lands with item
2. **Gate 2** bars recalibrating stage 0 without real TONAL artwork, and
the 2026-08-15 spec
(`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`)
already rejected four approaches and designed the replacement signal; what
blocked it was positives — one real gradient logo against six flat. The
real tonal set is larger now (Kent's icon, five real photographs), which is
what the plan's instrument re-measures first; a threshold moves only if
the boundary sites on that set. Photographs should be detected by item
13's signals so stage 0 only has to separate flat from gradient among
logos. Plan: `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`.

Where: `stage0_classify.py`, `stage2_quantize.py`, `stage2_photo_segment.py`,
`pipeline.build_generation`. Effort: large; ten fixtures change lane, so
every gradient golden moves.

### 2. Keep thin strokes and small lettering as strokes, not specks

Both lanes lose small text before any tier sees it. The flat lane's
small-shape rule is an area floor, `(min_detail_mm · px/mm)²` with
`min_detail_mm` 1.5, so a long thin stroke counts as a fleck and is absorbed
or dropped (`stage3_segment.resolve_small_regions`). The photo lane's
superpixels cannot hold a 0.4 mm stroke (Fremont: 945 superpixels → 50
regions, ten details under 1.5 mm absorbed). What survives sews as a bean
under the 0.5 mm cross floor. The pro's Fremont file sews THE, EST 1895 and
EAT | STAY | PLAY legibly at the same 92.5 mm by widening 0.25–0.55 mm
strokes to columns of 0.82–0.90 mm (`docs/kent-review-2026-09-03.md`).

Build a length-aware keep rule (a region under the area floor whose skeleton
is long and whose width is real is line art or lettering: keep it, tag it),
and widen lettering strokes to a sewable column. The widen-to width is the
one number **gate 1** owns, and ROADMAP names the satin width floor; the
mechanism is buildable behind a flag with the number read from the pro's
sewn file, the same evidence class as `FILL_ROW_MM`. Kent's call whether that
suffices or it waits on card block 5.

Where: `stage3_segment.resolve_small_regions`, the photo lane's min-area
floor, `stage6_satin`'s hairline tier, `textcluster.py`. Effort: large. This
is Kent's "elements missing" theme.

### 3. Sub-pixel, anti-alias-aware boundary extraction in stage 4

Contours come from binary label masks at the prepped raster's resolution,
then Douglas-Peucker at 0.2 mm; §2a shows the curve fix is inert on 27 of 29
fixtures. Smoothing region polygons is a measured negative (macro sprawl,
DOCTRINE) and this is upstream of it: locate the true edge inside the
anti-alias ramp, at the 50% blend between the two adjacent cluster colours,
so the boundary is known to a fraction of a pixel and refinement can run at
any resolution. It also removes the raster grain that flips the satin/fill
classifier on borderline shapes (defect 26 names `_CURVE_MIN_PX_PER_MM` as
its mitigation). For sources under the resolution floor there is no ramp to
read; a spline-fitting tracer is the fallback there (vtracer is MIT and was
evaluated 2026-08-17, with a keyword-argument crash on Python 3.14 untested on
3.12).

Where: `stage4_vectorize.vectorize`, `_refine_curves`, `_CURVE_MIN_PX_PER_MM`.
Effort: large; every golden moves. No gate. This is Kent's smoothness theme.
Plan: `docs/superpowers/plans/2026-09-08-subpixel-edges.md`.

### 4. A wide-column policy: satin between 5 and about 6.5 mm instead of tatami

`SATIN_MAX_WIDTH_MM` 5.0 is both the classifier's ceiling and the emitter's
per-station cross cap, so a letter whose stroke reads just over it falls to
tatami. §2b shows that is what happens to all of MARINE at 100 mm and to two
of its letters at 80 mm, and why the BECKER outline sews as fill at 100 mm.
§2c shows the pro sews that band. DOCTRINE is right that the bare number must
not be raised: the coupled route broke the overlap guard (18 failures) and
the split route let the classifier admit what the emitter refuses (13). The
build is that guard, rebuilt on local geometry — the doctrine entry's own
last sentence — after which the existing split-satin rule
(`SPLIT_SATIN_ABOVE_MM` 5.0, staggered) carries the band. The ceiling then
comes from the pro's sewn files. **Gate 1** applies to that number; the DST
lesson's test applies to how the gate is read (*would a machine owner answer
this faster than five sewn files?*).

Where: `stage6_satin._rail_points` (per-station cap), `classify_ribbon`
(`dt_p90_cap`), `machine.SATIN_MAX_WIDTH_MM`. Effort: medium to large.

### 5. Stroke decomposition that yields pro-like columns, with junctions covered

The raster skeleton at 6 px/mm turns the BECKER outline into 27 strokes with
five-way nodes, and every downstream defect refuted knob by knob on
2026-09-06 traces to that: trims 29 against the pro's 12 on identical
artwork, because travel is only allowed over unsewn strokes and no route
survives past 40% sewn; bare crotches at junctions because crosses are placed
per arm (the K, 37 mm²); the N's diagonal welded through a 108° fold by
`_prune_spurs`; the H and E deformation. Replace the raster thinning with a
polygon-native medial axis pruned by a millimetre-scale significance test,
add a cap-arm classifier at branch nodes, and cover junctions explicitly.
The built `satin_patch_junctions` flag is the interim for the junction half.
This also closes the class where one raster pixel decides a 3 mm tab (the
2026-08-21 extremity drop).

Where: `stage6_satin._rasterize`, `_skeleton_edges`, `_prune_spurs`,
`_merge_through_junctions`, `shapefield.py`. Effort: large. No gate on the
construction.

### 6. Pull compensation on satin rails after decomposition, with corners kept

Stage 5 dilates the whole polygon by the fabric's pull with a round join
before satin decomposes it (`stage5_overlap._grow`). Corners become 0.3 mm
arcs, exterior slots narrow by twice the pull (THERMAL E 0.936 → 0.336 mm;
DRONE E sealed), and the minimum-feature guard protects interior rings only.
The letterform study's pull=0 control took shape fidelity 0.587 → 0.747
(`.claude/memory/letterform-fidelity-2026-08-26.md`). The JS lettering engine
already pushes each station's rails outward with a counter guard
(`satinplay.js stationPush`). Give the Python satin tier rail-side
compensation, leaving fills on the polygon growth. The amount stays the
fabric preset, so gate 1 is untouched. The exterior-notch prototype Kent held
on 2026-08-28 cost trims because it split shapes; rail-side comp splits
nothing.

Where: `stage5_overlap.resolve_overlaps`, `stage6_satin._rail_points`.
Effort: medium to large; goldens move.

### 7. A design-level stitch direction policy

The pro-parity harness's `direction` component has the largest headroom of
its six (20 points, `docs/classifier-misroutes-real-logos-2026-08-15.md` §3).
On Becker lettering the house-angle rule took strokes within 20° of the modal
direction from 29% to 51% against a 22% chance floor, and it fires only on
detected text. Per-shape principal-axis angles put adjacent capitals at
22.5° and 90°; on Bridge Bar our fill angles spread across the half-circle
where the pro holds one. Extend the house angle to all fills as one design
angle with a per-shape override only on strong aspect, and give non-lettering
satin the same lean rule. No new constant.

Where: `stage6_fill.best_fill_angle_deg`, `textcluster.set_lettering_house_angle`,
the angle carried on `PlannedRegion`. Effort: medium. G4 on the number quoted.

### 8. Decide the gradient-lane colour bundle as one set, then default it

Five built flags each fix a piece of the same problem: cones the customer did
not ask for. A cone is a spool to buy and a re-thread on a single-needle
machine. They are not low-hanging in decision terms — each wants a render
look — but they are built, byte-identical off, and measured
(`docs/pending-flag-decisions-2026-09-06.md`). If item 1 lands most of this
becomes the flat lane's existing behaviour, so order matters.

| flag | what it buys |
|---|---|
| `enforce_color_cap` | designs over the promised count 6 of 26 → 1 of 26; drone 22 → 6 cones |
| `resnap_mask_matches_grader` | gaulke F 4 → D 46, −5 blocks, −4 cones, no grade down |
| `revalidate_small_shapes` | worst shard 32.7 → 1.4 ΔE00, invisible to the saturated grade |
| `bind_resnap_all_classes` | 19 stops removed, +2 blocks net, one spool revisit gone — a real trade |
| `dissolve_phantom_blends` | Bridge Bar 125 → 62 trims, 18 → 12 cones. Kent banked it OFF 2026-09-04, before the page-mask bug was fixed; re-present, do not re-open |

### 9. Enclosed letter bodies decided by garment colour, not a global unstitched default

BECKER's white letter bodies are 40.8% of the design and sew as holes; Golden
Tee leaves 42.4% bare the same way. The pro fills Becker's bodies on both the
white and the dark garment. On a black cap our letters vanish. The Studio
knows the garment and the pipeline knows the enclosed region's colour;
`preflight.DELTA_E_VISIBLE` (5.0) is an existing number. Rule: an enclosed
region whose colour differs from the garment by more than that sews, and the
review toggle stays. The default is Kent's; the mechanism is small.

Where: `stage4_vectorize.tag_enclosed_background`, `pipeline` stitched
resolution, `app/src/lib/digitizer.js` (pass the fabric colour). Effort:
medium. No gate.

### 10. Wide columns in the JS lettering engine: split satin and a fill fallback

Eighteen of the 85 shipped fonts emit stitches longer than one DST record
once letters get big; a two-letter monogram on a full back asks for a 44.9 mm
cross (DOCTRINE 2026-09-07). The encoders now split the move; the engine
still emits it. The Python engine splits satin above 5 mm with a stagger and
routes past-cap widths to fill; the JS path has neither. Port the mechanism
and the existing constants — no new number. Until then monograms and big text
are not sewable from the product.

Where: `satinplay.js emitZigzag`, `satinfont.js routeGlyph`,
`digitize.js buildLetteringDesign`. Effort: medium.

**BUILT 2026-09-11 — and "eighteen of the 85" is LOW BY FOUR TIMES.** Measured
with `tools/long-stitch-census.mjs` (validated against DOCTRINE's own Full Back
row to the stitch): **80 of 85 fonts throw a stitch no machine can sew, worst
98.7 mm**, and one letter at **Left Chest** breaks 63 of 85 on its own. Two
units bugs fixed unconditionally take it to 66; `splitSatin` or
`wideColumnFill` — both built, both measured OFF first — take it to 9, all of
them cross-stitch fonts, which is a separate question. The default was Kent's,
because DOCTRINE 2026-09-07 calls the choice between split, fill and capping
*"a look-and-fabric decision with a sew-out behind it"*; **he ruled the split
ON and the fill off** (2.47× the stitches and not one extra trim, against the
fill's 5.22× and 68.8×). Plan, numbers and the three options as they were put:
[`docs/superpowers/plans/2026-09-11-wide-columns-in-lettering.md`](superpowers/plans/2026-09-11-wide-columns-in-lettering.md).

### 11. A legibility yardstick on the render, and an un-clamped grade

Phase 1's exit is that the metric agrees with Kent's eye. Today
`dropped_elements` reads 0.2% on a design he calls completely lost, because
sewn-but-illegible counts as covered; 12 of 52 combos sit on a saturated 0
so a real fix moves no grade; the gradient lane is judged on the raw
yardstick (`docs/yardstick-disagreements-2026-09-06.md`). Render the plan,
OCR both artwork and render with the tesseract already in the dependencies,
score recovered characters per text cluster beside `lost`, report the
unclamped score, and give `THREAD_MATCH_POOR` the area floor every sibling
has. Without this items 1–6 ship blind, which is how the flags history reads.

Where: `tools/dropped_elements.py`, `preflight.py`, `corpus_scorecard.py`.
Effort: medium. G4 wants the chance-corrected form; G3 wants exactly this
before flips.

### 12. Finish fill travel under cover

`fill_travel_under_cover` halved exposed travel and is default ON, but the
three review logos still lay a third of their fill-phase travel over sewn
fill (Becker 55.8 of 148 mm, Bridge Bar 75.8 of 194, Fremont 59.6 of 185),
including the run across Becker's N Kent pointed at. The cause is not
established. Stage 5 already knows which later colour covers each shape
(`PlannedRegion.covered_by`), and the fill knows its own unsewn remainder, so
the remaining bridges can be routed along the shape's edge run or under the
covering colour, or lifted as a jump when shorter than `trim_at`.

Where: `stage6_fill.travel_path`, `_reorder_for_cover`, `stage7_sequence`.
Effort: medium. No gate.

### 13. Detect photographs from signals the repo already owns

A photograph left undeclared routes gradient, escapes the palette bind and
gets no depth sequencing. Colour statistics cannot detect it, which is why
the control is a declaration. EXIF camera tags and the shipped YuNet face
detector each separate the corpus's photos from its logos with no misses,
and DOCTRINE names the route: EXIF or face, declaration as fallback. Gate 2
does not apply because nothing in stage 0's colour gates moves.

Where: `pipeline.run_stages`, `config.is_photographic`. Effort: small to
medium. Lower priority than the logo items, and cheap for its effect.

### 14. Settle the two edge-finish flags from the render and the pro files

The design's silhouette is nobody's edge, so every fill row on it ends in
open air. `edge_cap` is built in two styles and off (icon: bean +12.6%,
satin +15.3%; drone +56.9% / +34.9%), and `satin_rails_follow_edge` is built
and off (Becker bare satin area 8.6 → 5.8% for +10–17% thread). Both are
gate-1 held. The pro's files can say whether that digitizer caps a
silhouette and how far a rail reaches, the evidence class that settled fill
density. Effort: a decision plus a render pass.

## 4. Three cheap, gate-clean defects the audit pass found on the browser lane

These are low-hanging and are listed anyway, because each is a real defect
on the lettering, manual-shape and phone lanes, and none has a gate.

- **The browser engine emits no lock stitches on any lane.** A grep of
  `src/` and `app/src/lib/` for tie or lock finds nothing; a geneva "AB" at
  40 mm decodes as `stitch, trim, jump, stitch` around every cut with no
  bounce, so every trim leaves two unlocked ends. The Python engine locks
  every start and cut (`stitches.py`, `TIE_STITCH_MM` 0.8 × `TIE_STITCHES`
  3). Lettering, manual draw, basic shapes and the flatten lane all ship
  through the JS builders. A machine's own auto-tie may be masking it; the
  09-01 sew-out went through the service, which ties. Port `tie_run`
  verbatim; the constants already exist in `machine.py`, so this is the
  move-both-or-neither rule, not a new number. Every lettering snapshot
  re-pins.
- **JS fill has no stagger and sews connectors across counters.**
  `src/fill.js` densifies every span from its own start, so interior
  penetrations land at identical x on every row (the channel pattern
  `stage6_fill.py`'s docstring warns about), and a connector is marked as
  travel only when longer than `maxStitch`, so a connector across a counter
  narrower than 4 mm is sewn. Port `_stagger_slots` and a point-in-hole test
  on connectors. Manual and basic shapes, SVG import and the phone lane.
- **Python satin has no edge-walk underlay.** Two rungs only: none under a
  5 mm extent, centre run → zigzag above 2.5 mm. The JS font path carries
  the published cap-height ladder (none under 5, centre 5–10, edge over
  10 mm, `satinfont.js`). Mirror the ladder and add an edge-walk style to
  `_stroke_underlay`. G1 for any new inset number; the JS one exists.

*(measured 2026-09-08 — audit pass; the lock-stitch and connector readings re-verified by grep and by reading `src/fill.js`)*

## 5. Left off on purpose

- **Needle-down chaining** (`chain_links`). The largest measured trim lever
  on real logos, −33%, frozen by gates 1 and 3 because it sewed thread on
  bare fabric with a green suite. Hooping 2 on the sew-out card settles it.
  Nothing above should be built to route around that.
- **Raising `SATIN_MAX_WIDTH_MM` as a bare number**, smoothing region
  polygons, the DT-first classifier swap, and contour fill are measured
  negatives and stay that way. Item 4 is the guard rebuild, not the number.
- **Faces, the shade-merge hopping, and the tonal-split flip** are tabled or
  ruled by Kent and are not reopened here.
- **Card block 2 at 0.15 mm.** `FILL_ROW_MM` 0.15 has produced no cloth;
  Kent said no physical tests until he says (2026-09-04). Items 2, 4, 6 and
  the underlay mirror all change thread per mm², so their eventual sew-out
  reads will be confounded until the row itself is verified. Recorded, not
  requested.

## 6. Reproducing the three measurements

```bash
cd digitizer
# 2a — fixture resolution against the 20 px/mm gate
.venv/bin/python - <<'EOF'
from PIL import Image; import glob
for f in sorted(glob.glob('testdata/*.png') + glob.glob('testdata/photo/*.*')):
    if f.endswith('.json'): continue
    w, h = Image.open(f).size; print(f, w, h, round(w / 80, 1))
EOF
# 2b — per-shape sewn tier, flag off and on
.venv/bin/python tools/sewn_tiers.py becker_marine_logo.png --width 100
.venv/bin/python tools/stroke_verdicts.py becker_marine_logo.png --width 100 --all
# 2c — the pro's column-width tail
.venv/bin/python - <<'EOF'
import numpy as np, sys; sys.path.insert(0, '.')
from pathlib import Path
from tools.satin_columns import passes_from_file, _crosses
for name in ['becker_hat_polo_large_beckers_logolc.dst', 'becker_chest_small_beckers_logo_lc_2_a.dst']:
    w = np.concatenate([_crosses(p)[1] for p in passes_from_file(Path('testdata/reference') / name)])
    print(name, [round(float(np.percentile(w, q)), 2) for q in (50, 90, 95, 99)], round(float(w.max()), 2), f"{np.mean(w > 5.0):.1%}")
EOF
```
