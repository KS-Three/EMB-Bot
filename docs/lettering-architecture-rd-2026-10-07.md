# Why auto-digitized lettering is poor, and the architecture that fixes it (2026-10-07)

**Status: R&D report. Nothing wired, no default changed, no engine edit.**
Kent asked (2026-10-07) to troubleshoot why the tool "cannot digitize lettering
very well" and to work out the architecture a professional result needs. This
doc re-measures the failure on today's `main` (`32b0dd3`), runs the
outline-cut spike on today's polygons (the step its own write-up listed first
and nobody had done), surveys what every shipping tool and the literature do,
and proposes the architecture. Renders in
`docs/renders/lettering-rd-2026-10-07/`. Scripts are session scratch (method
recorded in §2 so it can be redone); the one piece of code run here that is
not on `main` is `digitizer/tools/outline_cut_spike/oc.py` from lane
`claude/outline-cut-columns`, untouched.

## 1. The answer in one paragraph

The engine has no lettering construction. A letter is traced as a generic
region, pull-compensated as a blob, skeletonised at 6 px/mm, pruned, and cut
into satin columns whose rails are normals cast from a *smoothed skeleton* to
the edge (`stage6_satin.py`, `extract_strokes` → `satin_stroke` → `_rail_points`).
Every shipping tool and both relevant patent families do the opposite: the
column's rails ARE pieces of the glyph outline, and the skeleton (or medial
axis, or Delaunay triangulation) is used only to decide where to cut and
which outline pieces pair up. Twenty-odd lettering flags since 2026-08-26
(house angle, Euler order, corner twigs, junction stack, crown cover, cap
recentre, rail comp, outer-rail pitch, join square …) each moved a number
and Kent's eye said the pairs were "VERY hard to tell apart", because they
all tune the skeleton model at its floor
(`rail-wobble-is-the-models-floor-2026-09-21`). Below about 5 mm cap height
a second, independent problem takes over: strokes under the needle's width,
where the only professional answers are a widened column, a run/bean
centreline, or "size up", and the engine's answer is a bean run round the
outline ("tube letters"). And a third problem sits upstream of both on
coarse uploads: at 0.5–0.7 mm per source pixel the trace is not
letter-shaped before construction starts. The architecture that fixes this
is a **lettering lane**: text detected and grouped once, letterform recovered
under a source-pixel cap, the outline cut into stroke pieces whose rails are
outline arcs, and those pieces handed as *column objects* to the one
construction engine the repo already has for typed text (`satinplay.js` /
`satinfont.js` rules, ported where Python needs them). Both halves of the
geometry exist as spikes on sibling lanes; what is missing is the object
that joins them to the font engine, a word-level size policy, and
text-scoped halo removal.

## 2. What today's `main` does, re-measured

Method: `digitize()` at the corpus's own width and garment, `max_colors=6`
(`tools/thin_strokes.py` `REAL_ART`), the plan rendered with `stitchviz`
at 12 px/mm, and per text-tagged region (`meta.text_candidate`) the runs
grouped by `shape_id`: satin runs, trims, and the concentration of the
cross angles (mean resultant length of the doubled angle over stitches
≥ 0.8 mm; 1.0 = one angle, the instrument of
`letterform-fidelity-2026-08-26`). Stroke width is the 2·area/perimeter
proxy. Source px is the upload's pixels over the design width.

| fixture | upload | mm per source px | text-tagged letters | cap h (med) | stroke (med) | tier | satin runs / letter (med, max) | trims on letters | angle concentration / letter (med, min) |
|---|---|---|---|---|---|---|---|---|---|
| becker 100 mm | 146 × 91 px | **0.68** | 11 (6 MARINE + 5 band) | 16.8 mm | 4.5 mm | 6 satin, 5 inside the band | **6, 9** | **42** (7–9 each) | **0.37, 0.20** |
| enthusiast 80 mm | 1400 px | 0.057 | 24 | 1.6 mm (subline) | 0.18 | 10 satin, 14 run | 2, 5 | 9 | 0.42, 0.29 |
| fremont 92.5 mm | 2500 px | 0.037 | 32 | 3.0 mm | 0.27 | 15 satin, 17 run | 4, 6 | 8 | 0.29, 0.16 |
| gaulke 80 mm | 1284 px | 0.071 | 39 | 4.4 mm | 0.96 | 37 satin, 2 fill | 2, 5 | 26 | 0.30, 0.05 |
| drone 80 mm | 1536 px | 0.052 | 22 | 6.6 mm | 1.46 | 22 satin | 2, 5 | 21 | 0.39, 0.08 |
| bridge 80 mm | 400 px | 0.20 | 8 (blobs, see B) | 4.8 mm | 1.27 | 8 satin | 2, 3 | 8 | 0.58, 0.24 |
| fremont, 371 px `art/` copy, 92.5 mm | 371 px | 0.25 | 15 | 6.6 mm | 0.79 | 12 satin, 3 run | 3, 6 | 8 | 0.33, 0.12 |

Whole-design: becker 10,347 stitches / 64 trims; fremont 20,177 / 58 (+145
jumps); gaulke 4,583 / 34; enthusiast 2,614 / 15; drone 19,353 / 139;
bridge 18,401 / 98; the 371 px Fremont 23,117 / 62. Read the per-letter
columns, not the totals: the whole-design trims are mostly the other
shapes'.

What the renders show (`docs/renders/lettering-rd-2026-10-07/`):

- **`becker_marine_today_main.jpg`** — the patchwork. MARINE's M is five
  slabs at four directions crossing mid-stroke, the N's diagonal is a slab
  laid over its stems, the E's arms are three slabs with a fourth across
  them. Six to nine satin columns and seven to nine trims per letter where
  the professional's file sews each letter as one needle path at one angle
  (`docs/kent-review-2026-09-03.md`; pro 6 of 7 MARINE runs within ±20° of
  one angle, 12 trims for the whole design).
- **`enthusiast_today_main.jpg`** — the same on a clean 1400 px upload: the
  S fans, the N and A are slabs. So this is **not** a resolution problem.
  The route review's controlled experiment settled that already
  (`docs/lettering-route-review-2026-09-19.md` §3: a library font's own
  letters, rasterised at 12 px/mm and traced, sew with 41 trims and 0.23
  angle concentration where the font engine sews the identical shapes with
  3 and 0.63).
- **`fremont_the_bean_tube_letters.jpg`** — "THE" at 2.6 mm caps and
  0.27 mm strokes sewn as a bean run round each letter's outline: three
  bulbous tubes. The pro widens this tagline to a 0.8 mm satin column
  (`lettering-thickness-fremont-2026-10-06`). 17 of Fremont's 32 tagged
  letters and 14 of enthusiast's 24 are on this tier today.
- **`gaulke_80mm_today_main.jpg`** — 4.4 mm caps at 0.96 mm strokes, all
  sewn now (the 2026-09-16 "78% unsewn" went away with `work_px_per_mm`),
  but every counter is choked and the letters read as one bloated mass:
  each letter's two or three columns overlap at the junctions with
  pull comp on both, and nothing holds the counter open except the
  interior-ring guard.

So "cannot digitize lettering well" is, measured, **three different
failures by letter size**, agreeing with the outline-cut write-up's A/B/C
split (`docs/outline-cut-columns-2026-10-05.md`) and adding the two that
sit outside construction:

| | failure | where it lives | letters affected here |
|---|---|---|---|
| A | **patchwork** — several columns per letter at unrelated angles, 7–9 trims a letter | stage 6 construction model (skeleton-derived rails) | every satin letter over ~5 mm: becker, enthusiast wordmark, drone, fremont HOTEL FREMONT |
| B | **tube letters** — caps under ~4 mm sewn as a bean round the outline | tier policy: `routes_to_run`, `classify_ribbon`'s width floor, no column floor (gate 1) | fremont taglines, enthusiast subline, bridge's BAR & RESTAURANT |
| C | **halo strands** — anti-alias colours quantised to their own thin regions and sewn on top of one-colour text | stage 2/3, `dissolve_phantom_blends` OFF | gaulke, bridge, drone (23–30% of gaulke's text stitches per the 10-05 census) |
| D | **blob letterforms** — the trace is faithful to a 0.5–0.7 mm pixel ramp, so the letter is not letter-shaped before construction | stage 1/4 on coarse uploads | becker (0.68 mm/px), bridge (0.2 mm/px on 2 mm caps), the `art/` copies of gaulke and fremont |
| E | **two taggers** — `text_candidate` (textcluster `tag`) and `_lettering_groups` (house angle) disagree; the split flag reads one, the house angle the other, the priors spike both | textcluster.py | enthusiast's wordmark is a house group, its subline the text cluster; gaulke's 39 letters were not a cluster at all on 09-16 |

B is a size problem, not a segmentation problem: on bridge's source the
tagline's letters are 10–13 px tall with 2 px strokes, which at 80 mm is
2–2.6 mm caps and a 0.4 mm stroke. No construction sews that as satin; the
professional's choices are a run font, 60-weight thread, or a bigger
design, and the product already names the way out
(`LETTERING_TOO_SMALL`, "size up" chips). What the engine owes B is the
pro's *widened column* for the 0.5–1.0 mm band, which is a cloth constant
(ROADMAP gate 1), and a centreline bean rather than an outline bean below
it (`bean_letters`, built OFF).

## 3. The outline-cut construction on today's polygons

The outline-cut spike (`oc.py`, lane `claude/outline-cut-columns`) was
measured on polygons from `cf9f89f1`, 135 commits behind `main`; its
write-up's first "next" was to rerun it on current output. Done here on the
becker and fremont regions from the §2 runs, `oc.py` untouched, its own
`batch.py` check (30 px/mm raster, 0.4 mm thread):

| fixture | letters | cuts / pieces | covered | thread off the art | over-long stitches | its "clean" count |
|---|---|---|---|---|---|---|
| becker (today's polygons) | 11 | 30 / 37 (22 straight, 15 curved) | 99.5% | 0.0% | 10.8% | 5 / 11 |
| fremont (today's polygons) | 32 | 106 / 134 | 99.3% | 0.0% | 2.1% | 16 / 32 |

Against the write-up's second look on the old polygons (becker 9.5%,
6/11; fremont 2.1%, 16/32) the construction behaves the same on current
output: the engine's month of stage-4 and stage-6 changes neither helped
nor hurt it, which is expected — none of them touch the outline it reads.

**`becker_outline_cut_plan.jpg` / `becker_outline_cut_on_today_polygons.jpg`**
are the picture that matters. On the same traced polygons that today's
engine sews as `becker_marine_today_main.jpg`: the M is two stems and two
mitred diagonals, the A two legs and a crossbar, the R a stem, a bowl and a
leg, the N stem–diagonal–stem, the I one column — each stroke one column
at one angle, rails on the outline, stitches square to the stroke. What is
still wrong is exactly the write-up's failure class 1: the MARINE E's body
is one uncut piece and fans; the band's C, B and E fan where a bowl or a
stem-plus-arms is left as one piece. Those are missing cut rules (an E as
stem plus three arms; a bowl paired against its counter or split at its
extremes), not a ceiling of the approach. The spike has no underlay,
sequencing, pull comp, ties or split satin yet — those are what the font
engine already does and what §5 hands it.

## 4. What professionals and the literature do (survey, 2026-10-07)

A research pass over the vendors' own documentation, two patent families,
and the stroke-decomposition literature (URLs and quotes in the session;
the load-bearing ones repeated here). Three things every source agrees on:

1. **Rails come from the outline; the skeleton only says where to cut.**
   Wilcom's auto-digitizing gives narrow shapes a "Turning Satin Object"
   and otherwise tells you to tag shapes or go through text; Pulse's "Auto
   Satin" builds a column from two *user-supplied* artwork segments;
   Ink/Stitch's *Fill to Satin* (`lib/extensions/fill_to_satin.py`) splits
   the fill's boundary at user-drawn rungs, pairs the outline sections
   between rungs into rails and bridges junctions; Embrilliance's satin
   object auto-inclines a shape *you draw*. Soft Sight's US 6,804,573
   family (scanned image → contour + skeleton → "contour points on opposite
   sides of a skeletal branch are connected via vectors … normal to the
   stroke", cuts at concavities; 1998 priority, parent expired 2018) and
   VSM's US 6,934,599 (font outline → thinning skeleton → cut lines from
   corner classes, adjacent satins merged when the join is smooth; expired
   2023-06-09) are the same design. Tian/Luo/Hu 2005 ("Shape decomposition
   algorithm in embroidery") and Pérez Rocha 2013 do it with a pruned
   straight skeleton and a boundary feature transform. StrokeStyles (Berio
   et al., TOG 2022) pairs interior and exterior medial-axis concavities
   into stroke crossings with seven junction types, no training data, and
   names its own failure case: "very thick glyphs in which the average
   stroke thickness is larger than the average stroke length" — Becker's
   band letters. The chordal axis transform (Prasad) gives junction /
   sleeve / terminal triangles from a constrained Delaunay triangulation,
   whose sleeve chains are zigzag-ready strips; it is the standard
   Chinese-character stroke extractor.
   **Nobody ships skeleton ± half-width rails.** Adobe's US 11,704,848
   (filed 2021, runs to about 2041) claims filled path → medial axis →
   width by perpendicular distance → stroked path, i.e. the representation
   today's engine builds; rails-from-outline with the skeleton used only
   to cut sits outside its claim 1 as summarised. Counsel's question, not
   mine, but it points the same way as the quality evidence.
2. **Text is a font object whenever possible; raster text is a fallback
   the pros expect to hand-tag.** No vendor claims to auto-digitize raster
   lettering well; no "font match" feature exists in Wilcom or Hatch
   documentation. The repo's own measurement agrees that library-font
   identification is dead for logos (`lettering-route-review` §2), and
   Convert-to-text stays the manual escape hatch.
3. **The small-lettering numbers are near-universal:** column floor 0.8–1.0
   mm (ASI/Freeman, Impressions, Ink/Stitch's 1 mm stroke-to-satin floor;
   Ignition Drawing's production floor 0.6–0.66 mm), cap floor ~5 mm for
   satin caps (Campbell, Ignition; mixed case 6.2), a run/monoline font at
   3–4 mm, extra per-side compensation on tiny columns (0.17 → 0.28 mm),
   centre-walk underlay never edge-walk on small columns, lowercase at 70%
   of caps. Wilcom's own classifier: a shape that cannot fit a 2 mm circle
   is "lettering". The pro's Fremont file does exactly this (0.30 → 0.80 mm
   on the tagline, +0.3/side everywhere).

Unsettled in the literature: fully automatic cut placement on 100–200 px
logo text (Ink/Stitch and Pulse need human rungs; StrokeStyles has no
public code; Goldman/Viking were built for clean scans and font outlines),
and whether dynamic-time-warping rail pairing (the spike) beats Goldman's
normal-pairing or Viking's corner scoring — no comparison exists. Learned
text super-resolution is trained on 16 × 64 px crops for OCR accuracy and
hallucinates shape; nothing evaluates it for tracing fidelity, so for
failure D the geometric refit under a pixel cap (the letterform-priors
spike) has more support than any upscaler.

## 5. The required architecture: a lettering lane

Today a letter walks the generic shape pipeline and twenty flags try to
make the generic path behave like a lettering engine from the inside. The
professional architecture is a separate lane whose unit is the **column
object** — two rails plus rungs, the same thing an `.embf` glyph already
is (`railA` / `railB` / `rungs`, `satinplay.js:1-7`: "no skeletonization,
no guessing") — so that a traced letter and a typed letter reach one
construction engine and every rule applies to both.

```
raster ──► stages 1-4 as today ──► regions
                                      │
                       ┌──────────────┴───────────────┐
                       │ L1 text detection & grouping │  ONE tagger: words, line, slant,
                       │   (textcluster, OCR advisory) │  cap/baseline, stroke modes
                       └──────────────┬───────────────┘
                                      │ per word
                       ┌──────────────┴───────────────┐
                       │ L2 letterform recovery        │  lines+arcs under k·source px
                       │   (letterform_priors, gated)  │  (failure D); refuse → trace
                       └──────────────┬───────────────┘
                                      │ clean outline per letter
                       ┌──────────────┴───────────────┐
                       │ L3 size policy per WORD       │  stroke ≥ floor → columns
                       │   cap h, stroke modes         │  0.5–1.0 → widened column (gate 1)
                       └──────────────┬───────────────┘  < 0.5 → centreline bean / size-up
                                      │ column letters
                       ┌──────────────┴───────────────┐
                       │ L4 stroke decomposition       │  outline cut at concave corners,
                       │   (outline_cut → Column[])    │  rails = outline arcs, junction
                       └──────────────┬───────────────┘  ownership, bowls vs counters
                                      │ Column objects (railA, railB, rungs, order hints)
                       ┌──────────────┴───────────────┐
                       │ L5 construction = font engine │  Euler walk, underlay by cap h,
                       │   (routeGlyph rules, ported)  │  rail pull comp + counter guard,
                       └──────────────┬───────────────┘  split > 5 mm, short stitches on
                                      │                  inside bends, ties, one house angle
                                      ▼
                        stage 7 sequencing with the other shapes
```

Per layer — what exists, what is a spike, what is missing:

**L1 — one tagger.** Exists twice (failure E). `detect_text_clusters`
(textcluster.py:803, two doors, ≥ 3 members, one-ink link) and
`_lettering_groups` (textcluster.py:1263, no ink or CV gate) must become
one word model that carries: members, line of text and slant
(`_line_of_text_deg`, `_stem_slant_deg` — already computed for the house
angle), cap and baseline, stroke-width modes
(`fit.word_prior` in the priors spike), and the OCR string as advisory
metadata. Every downstream flag then reads the same group. Cost: a
refactor inside textcluster.py plus re-pinning the house-angle and split
fixtures. No physical constant.

**L2 — letterform recovery.** Spike done and wired default-OFF on
`claude/letterform-priors-wire` (`cfg.letterform_priors_k`, 0.75; Kent's
option A). Byte-identical on fine uploads by its grid gate; refits 10/11 on
becker. Its 2026-10-07 labelled pairs are on Kent's sitting list. The one
design change this lane should make before wiring: run it **before** the
house angle and `measure_stitch_widths`, so the word's slant and widths are
read off straightened stems (the write-up's open question 1, first option).
The bridge class — letters lost to a 2 mm cap, not to the trace — is L3's,
not L2's.

**L3 — size policy per word.** Missing as a unit. Pieces exist: the 0.5 mm
cross floor (`machine.SATIN_MIN_CROSS_MM`), hairline stretches as beans,
`bean_letters` (OFF; centreline bean along the source ink, the right
technique for the < 0.5 mm band), `LETTERING_TOO_SMALL` and the Studio
chips. What is missing is the decision made once per word from cap height
and stroke modes instead of per shape from a distance-transform p90
(`classify_ribbon`), which is where the 87 → 88 mm cliff and the
"letter sews / does not sew" jitter come from
(`classifier-cliff-is-input-resolution-2026-09-16` on the gaulke lane).
The widened-column floor for the 0.5–1.0 mm band is the pro's 0.8 mm and
Wilcom's 0.8–1.0; it is a cloth constant and **stays behind ROADMAP gate 1
until a sew-out** — build the mechanism with the value as the flag, as
`lettering_min_column_mm` already is, and sew the Fremont tagline first.

**L4 — stroke decomposition.** Spike done (`oc.py`, 18 passes plus a second
look); §3 shows it holding on today's polygons. Its output today is a list
of pieces with rails and stitch lines; it needs to emit the **Column
object** instead of stitches, and three cut rules it names: the E/F as
stem plus arms (the twig rule's "cap" today), a bowl paired against its
counter or cut at its extremes (the C and the lower B in §3), and the
compound-piece retry with the 1.6 W yardstick. The literature offers two
cheap alternatives to compare on the same fixtures before committing to
DTW pairing: Goldman's normal-pairing across the skeletal branch and the
chordal-axis sleeve/junction triangulation (shapely's Delaunay is already a
dependency). Pick by the same sheets.

**L5 — one construction engine.** Exists for typed text in JS
(`satinfont.js` `routeGlyph` Euler walk with the last visit sewing satin,
underlay by cap height, `stationPush` per-rail pull comp with the counter
guard, `splitLeg` above 5 mm, `pullShort` on inside bends,
`splitByCrossFloor` to bean under 0.5 mm). Python has partial analogues
bolted onto the skeleton graph (`_euler_stroke_order`,
`satin_rail_comp`, `satin_lettering_split`, `_short_stitch_guard`). The
decision here is where the Column object is consumed. Two options, Kent's:
(a) port the glyph rules into a Python `columns.py` that `stage7_sequence`
calls for lettering lane shapes — one engine per language, the same rules;
(b) serialise Column objects into the plan and let the Studio's font engine
play them back as it plays an `.embf` glyph, which is zero new construction
code but moves lettering stitches out of the service's DST path. (a) keeps
`/export` and the scorecard honest; (b) is the fastest way to see pairs.
Either way the yardstick is the one the route review built: the font's own
word, typed vs traced, same shapes — the gap is construction and should
close to the typed numbers (3 trims, 0.63 concentration on MARINE 80 mm).

**C — halo strands,** independent of the lane: a text-scoped version of
`dissolve_phantom_blends` that assigns a thin region inside a word's box
to the nearer of the word's ink or ground. Measurable on gaulke
(23–30% of text stitches) with no cloth question.

### What this does NOT propose

- Font identification or retyping a logo in a library face (ruled 09-19,
  evidence stands; the survey found no vendor doing it either).
- Learned super-resolution of small text (no fidelity evidence; §4).
- Any flip. Every layer lands default-OFF and is shown as labelled pairs.
- Touching the skeleton model further. It is at its floor; the remaining
  lettering flags on it are polishing the wrong representation.

## 6. Order of work, with what each buys and costs

1. **L4 → Column object + the three cut rules, then L5 option (a) or (b)**
   on the MARINE yardstick and the nine logos, default-OFF, pairs for
   Kent. Buys failure A, the one Kent named first ("Kent picked A first",
   10-05) and the one every pro source agrees on. Costs the biggest build
   (weeks of lane time), and until L3 exists it changes nothing under
   ~5 mm.
2. **L1 one tagger** alongside, because L4 and L2 both need the word model
   and today they would each re-derive it. Cheap, no cloth, re-pins
   fixtures.
3. **L2 wire-up order** (before house angle) rides the priors lane's
   existing default-OFF flag; its pairs are already queued for the sitting.
4. **L3 word-level tier decision**, mechanism only; the 0.8 mm column floor
   waits on the Fremont tagline sew-out (gate 1).
5. **C text-scoped halo dissolve**, any time, independent.

Phase check against `ROADMAP.md`: this is Phase 3 ("right technique,
coherent path": satin-vs-fill placement, fragmentation into far more runs
than a pro uses) work, proposed under Phase 1 with Phase 1's instrument —
the typed-vs-traced yardstick and labelled pairs are how it is judged.
Gate 1 touched only by L3's floor, named as such. Gate 3 untouched. No
raw-agreement claim is made anywhere above (gate 4).

## 7. Caveats

- Seven fixtures are measured on today's engine; the 607 px `art/` gaulke
  copy was still running when this was written and is not in the table.
  Bridge's 8 text-tagged shapes are the 10-05 write-up's "segmentation
  blobs", 4.8 mm tall, not the 2 mm tagline letters, which never become
  regions of their own.
- `MASTER_SCOPE.md` sits 14 words under its 27,000-word budget, so this
  doc is indexed from `.claude/memory/MEMORY.md` and not from the
  dashboard; the next scope refresh should add the one-line pointer.
- The §3 numbers are the spike's own self-check, "not Kent's eye and must
  not be quoted as a quality figure" (its words). The renders are the
  evidence; the table says only that the construction did not regress on
  current polygons.
- The becker band's white letters are not sewn at all today (they are
  `BACKGROUND_ENCLOSED` holes of the band region; the pro sews them as
  white fill under a black satin ring). That is a separate, older defect
  and is not counted in §2's letter tiers.
- `h_mm` for enthusiast reads its 1.6 mm subline because the wordmark's
  members are a house-angle group, not a text cluster — failure E seen
  from the instrument side.
- Patent notes are a summary of claim text read through a search engine,
  for counsel; not legal advice.
