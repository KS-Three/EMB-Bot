# How EMB-Bot turns an image into a stitch file — the flow, and an outside review of the foundation — 2026-09-17

Kent, 2026-09-17: *"Let's get some perspective on how the embot is creating a
digitized file from an image, step by step layout and flow, followed by an in
depth analysis / review to ensure we have not been going down the wrong path.
Let's make sure our building blocks and foundation is absolutely solid! Make
sure you come into it with a bias approach and clear outside perspective."*

This is a READ, not a measurement session. Nothing in the engine changed.
Every claim below points at a file, a doc, or a number already on `main` at
`bfb204e` (#500); where I quote a figure it is the repo's own, with its date.
The review half is deliberately adversarial — it looks for the places where
the foundation is weakest, and says so plainly. Part 3 lists what I read.

---

## Part 1 — The flow, step by step

### The shape of it

```
 Studio (browser)                       digitizer service (Python, 127.0.0.1:8721)
 ─────────────────                      ──────────────────────────────────────────
 upload image ──POST /digitize──▶  build_generation   (stages 0–4, cached per image+config)
                                     └─ finish_generation (review edits, palette, layer order)
                                   plan_stitches       (stages 5–7)
                                   run_preflight       (read-only grading)
 review screen ◀──Design JSON────  adapter.plan_to_design   (the ONE y-flip)
   edit shapes ──POST /digitize──▶  finish_generation + plan_stitches only (generation cache hit)
 download     ──POST /export────▶  pystitch → DST / PES / EXP / JEF / XXX / VP3
```

Two entry points matter. `run_stages` = stages 0–4, "what shapes are in this
artwork, in what threads" — the expensive half, and what the review screen
edits. `plan_stitches` = stages 5–7, "how does a machine sew that" — cheap,
re-run on every parameter tweak. `digitizer_core/pipeline.py` is the
orchestrator; each stage is its own module; `machine.py` holds every physical
constant; `config.py` holds every knob (107 fields).

Coordinates: stage 4 emits **millimetres, floats, origin at artwork bbox
centre, y DOWN**. Nothing downstream flips. `adapter.py` converts to the
browser's integer 0.1 mm y-UP `Design` and is the only flip in the system.
`export.py` scales to pystitch's 0.1 mm y-down and does nothing else.

### Stage 0 — classify (`stage0_classify.py`, 514 lines)

Input: the raw image. Output: one of `flat` / `gradient` / `photo_subject` /
`photo_scene`, with a confidence, plus warnings.

Three colour statistics decide it: `unique_color_mass` (does a k=16 quantize
hold together locally?), `gradient_smoothness` (Sobel variance away from
edges), `alpha_softness`. The class picks the **stage 2 algorithm** (flat →
k-means; everything else → SEEDS+RAG), whether stages 1.5/2-SAM2 may run, the
stage 7 underlay/border/sequencing defaults, and which fill tier photo
subjects auto-route to. `forced_class` and `is_photographic` are the
customer's overrides (the Studio's "It's a photo" row sends the latter).

### Stage 1 — prep (`stage1_prep.py`, 504) + 1.25 + 1.5

Load as RGB uint8. Background: alpha wins; else a border-ring flood with
three guards (ring disagreement → `BACKGROUND_ABSENT`; a rival border colour
→ `BACKGROUND_UNCERTAIN`; intrusion past `bg_margin_mm` inside the hull →
uncertain). An enclosed background-coloured area (a counter, a donut hole) is
NOT deleted: it becomes its own region later, tagged `enclosed_background`,
unstitched by default, restorable in review — and since 2026-09-10 sewn by
default when the garment colour differs from it (`enclosed_by_garment`).
`strip_letterbox` (ON since 09-14) trims phone-screenshot bars.

`px_per_mm` comes from the ARTWORK bbox against `target_width_mm`. Below
`min_px_per_mm` 4.0 the raster is Lanczos-upscaled up to 4×; `input_px_per_mm`
remembers the truth. Denoise on.

Stage 1.25 (`photo_signals.py`, OFF by default): EXIF camera tag or a YuNet
face → "this is a photograph", which can only ADD to the declaration.

Stage 1.5 (`stage1_photo_prep.py`, photo classes only, double-gated): rembg
subject cutout in an isolated venv (deploy requirement; if it cannot run the
whole block is skipped, because prep-without-cutout measured worse than
nothing), YuNet face priors, then bilateral texture kill + CLAHE tone.

### Stage 2 — quantize or segment

**Flat lane** (`stage2_quantize.py`, 379): k-means in CIELAB (seeded,
40k-pixel fit sample), majority-filter the anti-alias halos, merge clusters
within `merge_delta_e` 6.0, detect phantom blend colours (a cluster that is
>90% edge pixels is an AA artefact, not a colour), snap each cluster to the
thread chart by CIEDE2000, cap at `max_colors`. Enclosed-background pixels are
quantized as a SEPARATE population so they cannot steal another shape's halo.

**Gradient / photo lane** (`stage2_photo_segment.py`, 2,451): SEEDS
superpixels in Lab over the foreground → region adjacency graph →
hierarchical merge on CIEDE2000 at `MERGE_DELTAE00_THRESH` 26.0 with an
area-ratio guard and a boundary-contrast guard → k-medoids palette selection
→ optional tonal splitting (`effective_split_tonal`, ON for photo classes) →
optional thin-ink population (`thin_ink.py`, gradient class only: strokes
the superpixels would shatter are found on a flat quantise first and come
back as their own label). For `gradient` a **design ramp** is fitted first
(`design_ramp.py`): if a plane in Lab explains ≥60% of the foreground at
r² ≥ 0.4, stage 2 merges with the sweep subtracted and stage 6 later sews
the whole design as one set of shade bands.

**SAM2** (`stage2_sam2_segment.py`, OFF, opt-in download post-v1) gets first
refusal on the two photo classes and falls through to SEEDS on any failure.

Output either way: a `Quant` — an HxW label map (−1 = background), one thread
index per label, cluster RGB.

### Stage 3 — segment (`stage3_segment.py`, 692)

`ClassicalSegmenter`: connected components per thread layer, each stored as
a bbox-cropped `RegionMask` (the full-frame version was an 8.5 GB peak).
Small-region policy: a component under `(min_detail_mm · px/mm)²` (1.5 mm) is
ABSORBED into the neighbour it shares the most boundary with — or, with
`keep_thin_strokes` ON (flat lane only), absorbed by COLOUR so a contrasting
hairline survives — or KEPT for the run tier if it has no neighbour and is at
least a thread's mark, or DROPPED. All three are counted and warned.
`merge_duplicate_cone_layers` folds two layers that snapped to one cone.

### Stage 4 — vectorize + the tagging passes (`stage4_vectorize.py`, 1,069)

Per mask: pad, `cv2.findContours` (RETR_CCOMP → one shell + holes),
`subpixel_edges` (ON since 09-09: each vertex moves to where the Lab ramp
crosses halfway between the two side colours — declined on upscaled
sources), Douglas-Peucker at `simplify_tol_mm` 0.2 (0.5 px floor for
sub-detail shapes), `curve_turn_deg` 15° refinement re-reading each chord
against its raw arc, `make_valid` with a recursive part scan (the owl lost
944 mm² to a shallow scan once), to mm. Drops are returned, never swallowed.

Then, in this order, each a "computed fact re-derived every generation":
`tag_enclosed_background` → `revalidate_threads` (re-snap each final polygon's
pixels to the chart, restricted to the selected palette since the colour
bundle flipped 09-10) → `rehome_resnapped_regions` → `enforce_color_cap`
(the slider's promise, kept only since 09-07) → `detect_text_clusters` →
`regularize_text_clusters` → `ocr_suggest_text` → `set_lettering_house_angle`
→ the gradient lane's shared fill angle → optional `set_design_angle`.

All of this is a `Generation`, cached by the service across a review session.

### `finish_generation` — the review-edit seam

Merge/split edits, then deletions and per-shape overrides (recolour, tier,
underlay, angle, border, boundary, layer, stitched). Then the palette is
settled: `compact_layers`, duplicate-cone fold, photo depth sort
(background → foreground, dark → light) OR `borders_last` (satin-dominated
layers after the fills they fence — born of the first sew-out), explicit
layer overrides last. Output: `PipelineResult` — regions, per-LAYER palette,
background info, `SourcePixels` for the raster-reading tiers, and stage 0's
verdict carried forward.

### Stage 5 — overlap and compensation (`stage5_overlap.py`, 562)

Layers sew in palette order. For each region: grow by the fabric's
`pull_comp_mm` (isotropic buffer; `directional_comp` OFF), extend an
`overlap_mm` 0.25 tongue under whatever sews LATER, hold open a corridor
against same-thread neighbours closer than 2×pull, never grow back over a
colour already DOWN (except widened lettering), keep any counter that would
close below the detail floor open at its original size, and compute the
`visible` geometry (grown minus everything later). A region that vanishes
here is warned as `SHAPE_NOT_STITCHED`. Output: `PlannedRegion` list in sew
order, each with its compensated polygon, its cover, and its sew index.

### Stage 6 — the emitters (the big files)

Each takes a polygon and returns runs plus a report. Stage 7 chooses which
one runs.

- **Satin** (`stage6_satin.py`, 4,684 — the largest file in the repo).
  Rasterize the polygon at a fixed **6 px/mm, max 900 px**, medial axis +
  distance transform, Rutovitz crossing number for nodes, pinhole collapse,
  spur pruning, junction clustering, merge-through-junctions, split at ≥90°
  folds, Goldman join at ≥45° corners, trim free ends by half a width. Then
  per stroke: stations along the spine at `SATIN_SPACING_MM` (÷cos lean),
  rails from the DT, cross angle from the house rule (perpendicular to the
  stem family, lean ≤30°), split satin above 5 mm, junction tuck, hairline
  stretches sewn as bean runs, underlay (centre run / edge / zigzag by
  width), push-comp cutback, travel between strokes over unsewn strokes
  only, `satin_patch_junctions` (OFF) to tatami the bare crotches.
- **Fill** (`stage6_fill.py`, 1,370). Best angle = fewest monotone columns
  over 16 candidates + PCA. Rows at `FILL_ROW_MM` 0.15 (the professional's
  pitch, Kent's 09-03 ruling) × fabric `density_adjust`, stitches at 3.0 mm,
  stagger every 4 rows, boustrophedon inside monotone columns, travel
  straight-if-inside / edge-following / jump, cover-aware column ORDER
  (`fill_travel_under_cover`, ON) so travel lands under later thread.
  Contour, crosshatch, wave/chevron/brick, density boost (OFF) are variants.
- **Run / bean** (`stage6_detail.py` + `run_outline`): the rescue tier for
  anything under the detail floor — a triple pass along the outline.
- **Blend** (`stage6_blend.py`, 1,064): gradient shade bands from the design
  ramp, feathered 1.5 mm at the seams, one row lattice per region.
- **Streamline / scanline / meander / sketch** (`stage6_streamline.py` etc.):
  photo thread-paint tiers reading `SourcePixels`; `photo_subject`
  auto-routes to layered streamline.
- **Border** (`stage6_border.py`): per-shape satin border on significant,
  smooth shapes (photo classes only by default; the canvas's right-click on
  any shape), seam owned by the colour sewn on top. **Edge cap**: a bean (or
  satin) around the design silhouette's genuinely open edge (ON since
  09-11, 40% budget cap since 09-12).
- **Appliqué** (`stage6_applique.py`): placement / tack-down / trim stop /
  cover, its own blocks, sews first.

### Stage 7 — sequence (`stage7_sequence.py`, 2,823)

`sequence()` is where every rule meets. Per colour group (nearest-neighbour
ordering inside a cone), per shape, the **tier ladder** in `stitch_one`:

1. explicit `tier` override wins;
2. under the detail floor → run outline (unless widened lettering);
3. `classify_ribbon` on the ARTWORK polygon: width cap `2·area/perimeter ≤
   SATIN_MAX_WIDTH_MM` 5.0 → aspect ≥ 3 → DT regularity `2σ < μ` (with a
   `promoted_ribbon` rescue on `explained` ∈ [0.8, 1.25] and elongation ≥ 10,
   and the per-stroke rung when `satin_per_stroke` is on) → `dt_p90_cap` →
   Law 31's 1.0 mm floor on photo classes → **satin**;
4. else **fill** (or whichever tonal tier the design/shape chose), or blend
   bands if the region rides the design ramp;
5. a tier that produces nothing falls through rather than dropping artwork.

Then: tie stitches on every run (`apply_ties`, unconditional), trims for any
jump over the fabric's `trim_at_mm` (`chain_links` OFF: needle-down linking
under cover is built and gated), borders after their shapes, the edge cap as
a final block in the cone that owns the edge, same-thread block merging and
hoisting, shade blocks for the tonal tiers. Output: `StitchPlan` — blocks in
sew order, each a thread and a list of `StitchRun`s (kind, role, jump, trim).

### Export and the browser

`adapter.plan_to_design` → the `Design` dict (integer 0.1 mm, y-up) with a
`runs` span index (09-15) so the Studio can draw satin differently from
tatami. The Studio treats it like any lettering design: renders it, lets the
review screen edit shapes (each edit = `finish_generation` + `plan_stitches`
on the cached generation), and on download calls the service's `/export`
(pystitch; the browser's own `encodeDST` is the offline fallback and has
matched the standard since 09-08).

### Preflight (`preflight.py`, 3,227)

A read-only grader over the finished plan: per-region coverage stack in fill
LAYERS (warn 6.67, block 9.33), thread match as the per-pixel CIEDE2000
median per spool per shade band, chaining links on the emitted thread,
trim rate against the corpus ceiling, uncovered artwork, satin width and
cross length, colour stops, legibility (OCR on the render, ON warn-only),
the photo yardstick. Findings carry a severity; pipeline warnings do not.

---

## Part 2 — The review: is the foundation solid?

### How to read this

I ranked by one question: *would this change what Kent does next?* Each
item names the mechanism, the evidence already on `main`, and what an
outsider would build instead. I have leaned on the project's own
measurements throughout — the honesty of this repo's record is what makes an
outside review possible at all.

### What is genuinely solid — keep it

- **The conventions layer.** mm / y-down / one flip in `adapter.py`; export
  through pystitch, verified against a third-party file rather than assumed;
  the DST axis fixed 09-08 by reading a reference encoder and rendering.
  RGB-in, Lab for colour math, CIEDE2000 for chart snaps, per-pixel medians
  for scoring. This is the part that silently ruins output when it is wrong,
  and it is right.
- **Machine physics in one module** (`machine.py`), every number sourced —
  format spec, corpus measurement, or Kent's ruling — and gate 1 refusing to
  tune the physical ones without cloth.
- **The stitch emitters.** Stagger, monotone columns, edge-following travel,
  cover-aware ordering, split satin, house angle derived from the art,
  ties on every run, junction handling. These are the primitives a
  professional engine has, and the 2026-09 corrections (0.15 row, borders
  last, seams owned by the top colour) moved them toward the pro corpus.
- **The engineering discipline.** Seeded determinism and byte-identity tests
  (163 test files, 49k lines); the generation cache seam; warnings as codes;
  preflight as a separate read-only pass; four required CI checks; every
  flag byte-identical OFF; every flip with a number AND a render; measured
  negatives written down so they are not rebuilt. DOCTRINE is the best asset
  in the repo.

### The foundation concerns, ranked

#### F1. The atomic unit is a colour blob, and every object-level need has become a flag

Stage 2 groups PIXELS by colour, stage 3 splits by connectivity, stage 4
vectorizes each patch. So a "region" is *one connected patch of one thread
colour*. Embroidery's atomic unit is a **stitch object** — a stroke, a
letter, a fill area, a border. The two do not line up: the BECKER outline is
one region and 27 strokes with five-way nodes; a one-colour wordmark is one
region per touching group of letters; a letter whose halo quantized
differently is two regions.

The project has measured this precisely and named it: an oracle that knows
the pro's per-shape satin/fill answer scores 76.6% against our 55.4%, and
the remainder "is NOT the classifier: it is SEGMENTATION" (MASTER_SCOPE
defect 5; `docs/segmentation-alignment-2026-08-17.md`). "Segmentation, full
stop." The response so far has been object-level heuristics layered ON the
blob: `classify_ribbon` now has six gates, a promote path, a per-stroke rung,
an area-weighted variant and a polygon-axis mode; `textcluster.py` (1,868
lines) re-derives letters from blobs; `thin_ink.py` re-derives strokes;
widened lettering needed an exemption in stage 5 AND stage 7 to sew at all;
`satin_patch_junctions` tatamis the crotches the stroke split leaves bare.
Each was measured, each helped a fixture, and four of them are default OFF.

**Outside read.** Colour-first segmentation is how every auto-digitizer
starts, so this is not a wrong path — but the engine is now at the point
where a **decomposition stage** (region → strokes / letters / fills as
first-class objects, BEFORE the tier is chosen) would replace a stack of
flags rather than add one. The repo already has this as quality-review
item 5 ("polygon-native medial axis… cap-arm classifier at branch nodes")
filed under *satin*. It is a foundation item. Note the trap: the "DT-first"
architecture was measured negative in August — but what was measured was a
*classifier rule swap* on the same regions, not a representation change.
Do not let that negative bar the decomposition.

#### F2. Raster → vector → raster → skeleton, at resolutions the customer's art does not have

Stage 1 upscales anything under 4 px/mm (Lanczos, ≤4×). Stage 4 traces at
that raster's resolution. Stage 6 satin then **re-rasterizes the polygon at
a fixed 6 px/mm (max 900 px)** to skeletonize (`_RASTER_PX_PER_MM`,
`_RASTER_MAX_PX`). A 0.6 mm stroke is 3.6 pixels wide in that raster; one
pixel has decided a 3 mm tab (memory `satin-extremity-drop`), the pinhole
and junction-cluster code exist because of it, and DOCTRINE 09-16 records
the plain conclusion: *"the satin/fill size cliff is INPUT RESOLUTION, and
no threshold rule reaches it."*

The real customer files are the low end: Becker is 146 px wide, 1.45–1.8
px/mm at hat size; bridge_bar 3.5. `subpixel_edges` (the smoothness fix Kent
approved) is **declined on upscaled sources** by design, so it does nothing
for exactly that class. The engine's polygon fidelity is good at ≥20 px/mm
(Fremont, Golden Tee) and structurally weak where the customer lives.

**Outside read.** For low-resolution sources the resolution-independent
foundation is (a) curve-fitting vector tracing (potrace/vtracer class —
vtracer is MIT and was evaluated 08-17) instead of pixel contours + DP, and
(b) a **polygon-native medial axis** (Voronoi/straight-skeleton of the
polygon, pruned by a mm-scale significance test) instead of a raster
skeleton at a fixed pixel pitch. (b) is the same build as F1's
decomposition stage — one change addresses both.

#### F3. Stage 0 sends real logos down the photo lane, and the product promise is the flat lane

"Flat art in, pro out" is the standing quality rule. Six of seven committed
real logos, ten of fifteen parity logos, route `gradient` at confidence
1.00 because anti-aliasing and JPEG ringing read 137–4,090× over a gate
calibrated on synthetic fixtures (`docs/classifier-misroutes-real-logos-
2026-08-15.md`). So the lane that received the flat-art engineering — the
phantom-blend dissolve, the colour cap (until 09-07 the gradient lane had
none; the slider said 6, the design sewed 13–22 cones), the chain rescue —
is the one customers do not get, and half the gradient-lane flag work of
September was compensating.

Item 1 is picked and in flight; its own PR 5 found that once a real
photograph must count as tonal, the candidate signal's margin is **zero**
(DOCTRINE 09-11). Gate 2 correctly bars a threshold move without real art.

**Outside read.** A router that decides *which segmentation algorithm* runs
from *colour statistics* is fragile by construction — AA halos and
compression are not content. Two architectural exits, neither a threshold:
make the segmenter lane-agnostic (SEEDS+RAG carrying the flat lane's
dissolve and cap, or run both and choose by an objective), or route on
signals that are invariant to export resolution (the built EXIF/face pair
for photographs; edge-sharpness or vector-ness for flat vs gradient among
logos). The zero-margin finding is the evidence that stage 0 *as designed*
cannot separate these classes on real input.

#### F4. The yardstick still does not agree with Kent's eye — and that is Phase 1's exit condition

ROADMAP phase 1: *"a yardstick that agrees with Kent's eyes… nothing he
judges better ever scores worse."* Where it stands: the two quality
instruments correlate at ρ 0.405; ARTFID is not comparable across routes;
the preflight score saturates at 0 on floored designs; chance-corrected
parity is 42.5 with a pro-vs-pro ceiling of 75–84; Kent puts the stitch-outs
at 60% of Ember while the instruments say ~80. `docs/yardstick-vs-kents-eye-
2026-08-28.md` attempted the exit question and did not settle it (element
COUNT matches his judgement, AREA does not). Since then: 457 commits, ten
default flips, each justified by an instrument number plus a render plus
Kent's eye on a few crops.

**Outside read.** This is the actual foundation risk, because everything
else is being steered by it. The repo's answer — a render in every PR, Kent
looks — is the right fallback and does not scale; it is also what Phase 1
was meant to replace. Stop trying to build ONE metric. Build a **paired-
comparison harness**: two renders of the same design, Kent picks, ~30 s a
pair, 40 pairs across the real corpus; then fit which instrument components
predict his picks. That is a half-day of his time and it is the single most
leveraged thing in the project, and it has been sitting since August.

#### F5. One sew-out. Everything else is geometry

Thread has met cloth once (09-01, 6/10). Of the four findings it produced,
none had been flagged by an instrument first (density, seams, sequencing, a
bare perimeter). `FILL_ROW_MM` then moved 0.40 → 0.15 — a 2.7× stitch-count
change — on a corpus reading, after two instruments disagreed 2× about the
pitch of the one sewn file. The controlled card
(`EMBBOT_SEWOUT_CARD.dst`) exists and, as far as the record shows, has not
been sewn; Kent ruled 09-04 *"no physical tests until Kent says."*

Gate 1 is right to refuse *tuning* physical constants without cloth. The
consequence is that the satin width floor, pull compensation, underlay
styles, the trim threshold and link cover tolerance are all spec values or
corpus reads, and the engine is being optimized against a 2-D proxy of a
3-D product. Not a flaw in the engineering — a flaw in the loop. The ruling
is Kent's; the cost should be named plainly, which is what this paragraph is
for.

#### F6. 107 config fields, 42 booleans, ten flips in two weeks — the flag economy has no lifecycle

`config.py` is 2,469 lines — the second-largest file in the core. 27 booleans
default True, 15 False. Flags interact: `subpixel_edges` and `curve_turn_deg`
share a bill; `split_satin` and `wide_columns` are near-substitutes; the
edge cap's bill oscillates with `classify_ribbon`'s stability; `flagcost.py`
measured everything under the parity config, which switches
`fill_density_boost` ON — *"nothing has been timed with the boost off."*

The byte-identical-OFF discipline is excellent for safety. Its cost is that
the customer ships at one point in a 2⁴² space, every measurement is at one
config, and a default-OFF flag that never flips is dead weight that every
reader pays for. **Outside read:** give every flag a decision date; after N
weeks it is ON, deleted, or promoted to a named mode. Measure at customer
defaults first, parity config second.

#### F7. Two engines, mirrored by hand

JS (8,880 lines) owns lettering, fonts, DST import, manual shapes; Python
owns the image path. Satin exists in both (`satin.js` ↔ `stage6_satin.py`),
DST codecs in both (the JS one transposed until 09-08), fabric tables in
both ("mirror `src/fabrics.js` exactly"), and constants diverge — satin cap
3.0 mm in JS, 5.0 in Python, "until its own sew-out". The JS lane emitted no
lock stitches at all until 09-14. "The missing-port defect (27) this repo
keeps rediscovering" is DOCTRINE's own phrase.

**Outside read.** A known cost, paid steadily. The structural fix is for
lettering to go through the Python engine too (font glyph → polygon →
`satin_shape`), leaving JS as renderer and editor; the cheap fix is a
cross-engine conformance test (same polygon in, compare stitches). Flagged,
not pushed — it is a scope call.

#### F8. `sequence()` is where every rule meets, and it is one function

Stage 7 is 2,823 lines; `sequence()` holds the tier ladder, seam ownership,
borders, chaining cover, edge cap, appliqué, blend, streamline, shade binding
and block assembly, with `stitch_one` a closure inside a loop. Three
different predicates must agree about who sews satin (`classify_ribbon`,
`_sews_satin`, `_comp_axis`), and the comments say so. Not a quality defect
today; the place a foundation crack would hide, and a velocity tax on every
change. **Outside read:** split into a pure tier decision (`PlannedRegion →
(tier, reason)`), emitter dispatch, and block assembly. The tier decision is
the one that F1 replaces anyway.

#### F9. Prose outweighs code, and only tests can enforce prose

DOCTRINE 5,704 lines, scope-history 12,937, `docs/` 42,266, COOKBOOK 1,577,
MASTER_SCOPE 839 — roughly 63k lines of load-bearing prose against 41k of
core Python. MEMORY.md overflowed its loader silently on 09-15. The record
is the project's best asset (measured negatives are not rebuilt); the risk
is that a session reads a subset and re-derives. The repo has already
started converting prose rules into tests (scope budget, AST tripwires,
pointer checks) — that is the right direction. The growth is all in
DOCTRINE's "Gotchas" (75% of the file); a quarterly "does this still change
what someone does?" pass would keep it a doctrine and not a diary.

#### F10. Lettering is the make-or-break element and the pipeline treats it as geometry

Real logos are mostly text. Today text arrives as colour blobs →
`textcluster` tags → regularize → house angle → (widened lettering, OFF) →
satin or bean. Fremont's THE sews "T H C"; ENTHUSIAST's 1.6 mm subline
smears under the widening flag; the legibility instrument is a lower bound.
Meanwhile `ocr_suggest_text` and the Studio's "Convert to text" already
exist — the path where recognized text is **re-typed and rendered through
the font engine**, which is what a professional digitizer does with a logo's
tagline. **Outside read:** the highest-yield lettering lever is not better
stroke extraction; it is making OCR → font the default *suggestion* for a
tagged text cluster, with a font-matching step. A product move that
sidesteps F1 and F2 for the element class that matters most.

#### F11. The path is the engine; the launch bar has not moved (flag only)

Kent ruled engine quality a parallel investment, not a launch gate. Noted
without judgement: 457 commits since 09-01, essentially all engine; launch
row 3 (starter pack) untouched since August; billing undecided. "Are we
going down the wrong path" includes "is the path we are on the one that
ships."

### Verdict

**The foundation is sound at the bottom and the edges, and weakest at the
top and in the loop.** The conventions, the export path, the physical
constants, the emitters and the engineering discipline are the parts of an
embroidery engine that are hard to get right and they are right. The parts
that bound quality today are (1) how the image is cut into objects (F1, F2,
F3 — one problem seen from three sides), and (2) how quality is judged (F4,
F5). Most of September's work landed in the emitters, behind flags, steered
by instruments that do not yet agree with the eye. **Not the wrong path —
the wrong end of it for the next month.** The building blocks are solid;
the block that is missing is a decomposition stage between segmentation and
tiering, and the thing that is missing is a yardstick Kent trusts.

### What I would do next, in order

1. **Phase 1 exit, for real** — the paired-comparison harness (F4). Half a
   day of Kent's time; makes every later decision cheaper.
2. **Decomposition as a foundation item, not a satin item** (F1 + F2) — a
   polygon-native medial axis and stroke/letter/fill objects before tiering,
   built behind a flag, judged by (1). Quality-review item 5, re-ranked.
3. **Stage 0 exit that is not a threshold** (F3) — pick lane-agnostic
   segmentation or resolution-invariant routing; the zero-margin finding
   has already ruled out the third option.
4. **Sew the card** (F5) — Kent's, on his schedule; named because it is the
   cheapest large-information action in the project.
5. **Flag lifecycle** (F6) — housekeeping that compounds.

Everything else in Part 2 is worth knowing and can wait.

---

## Part 3 — What was read

`digitizer_core/pipeline.py` in full; `stage0_classify`, `stage1_prep`,
`stage2_quantize`, `stage2_photo_segment` (header), `stage3_segment`
(header), `stage4_vectorize` (`vectorize` and header), `stage5_overlap`
(`resolve_overlaps`), `stage6_satin` (`classify_ribbon`, `satin_shape`,
constants, header), `stage6_fill` (header, `best_fill_angle_deg`),
`stage7_sequence` (`sequence` through the tier ladder), `stitches.py`,
`export.py`, `adapter.py`, `machine.py` (fill section), `config.py`
(defaults), `preflight.py` (header); `digitizer_service/jobs.py` (entry
points); `app/src/lib/digitizer.js`, `exporters.js` (grep); `CLAUDE.md`,
`COOKBOOK.md` (architecture), `PRODUCT.md`, `ROADMAP.md`, `MASTER_SCOPE.md`
(live defects, latent), `DOCTRINE.md` (standing rulings in full, headings
of the rest), `docs/quality-review-2026-09-08.md`, `docs/handoff-2026-08-
16.md`, `docs/flag-runtime-bills-2026-09-12.md`, `docs/scope/1-auto-
digitizing-quality.md` (header), `docs/becker-axis-review-2026-09-17.md`,
and the memory entries `real-artwork-parity`, `quality-review-2026-09-08`,
`first-physical-sewout-2026-09-01`, `sewout-five-points-2026-09-03`,
`emb-bot-digitizer`. Counts (config fields, booleans, line counts, commits,
docs) were measured on the tree at `bfb204e`.
