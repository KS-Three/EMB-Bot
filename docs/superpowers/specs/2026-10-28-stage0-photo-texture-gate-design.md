# Stage 0: a texture gate so photographs reach the photo lane — design (2026-10-28)

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4). Readings were taken on the 39-row Commons corpus
(`digitizer/testdata/photo/corpus/corpus.json`, real artwork, 18 photo genres
and 21 logo styles) plus the repo's committed fixtures, on the files as the
corpus tool fetches them (1920-px Commons thumbnails). Nothing synthetic
calibrated anything (gate 2: the corpus IS the real tonal artwork that gate
asked for). Nothing was sewn (gate 1).

## 1. Intent

Kent, 2026-10-27: the digitizer must improve ALL photos, not the ones on hand.
On the corpus baseline (`docs/scoreboards/photo-corpus/baseline-5ff48c5.json`)
stage 0 sent 3 of the 18 photographs to the photo lane; eleven went
`gradient`, three `flat` (faces), one timed out. Three logo rows went
`photo_scene`. This design changes the routing so a photograph of any of the
18 genres reaches photo territory, without sending designed flat/gradient
logos there, and says exactly which rows it cannot separate and why.

## 2. Why a photograph reads as a gradient logo (measured)

`stage0_classify` has one photo gate: `unique_color_mass >= 0.28`. That
statistic is the fraction of foreground pixels whose k=16 quantised label
differs from the 3x3 mode of that quantisation — a **grain detector**. A
photograph that has been downsampled (every Commons thumbnail, most phone
exports, every re-save) has no grain left: neighbouring pixels quantise
together. Fifteen of the eighteen photos read 0.020–0.265 against the 0.28
gate. They fall through to the flat/gradient gate, `gradient_smoothness >=
0.0015`, which any texture crosses (the photos read 0.34–3.7, 200–2500x the
gate), so they come out `gradient` at confidence 1.0.

The three photos that did pass carry grain: `bw_street` 0.372 (film grain),
`snow_highkey` 0.327 (sky noise), `pencil_sketch` 0.299 (paper). The three
logo rows in `photo_scene` pass the same detector on DESIGNED texture:
`arabic_calligraphy` 0.584 (dithered gold), `halftone_dots` 0.581 (the dots),
`vintage_engraved_badge` 0.321 (hatching). This is the DOCTRINE 2026-09-11
`logo_script_tires` mechanism (0.361, flat two-colour script) on more rows.

## 3. What stage 0 can and cannot see

Six of the twenty-one "logo" rows are photographs or scans OF graphics:
`halftone_dots` (a printed portrait photograph), `chalkboard_lettering` (a
photo of a café board), `duotone_poster` (a photo of a framed poster),
`kanji_brush` (ink on crinkled paper), `comic_halftone` (a photo of a printed
poster), `vintage_engraved_badge` (a scan). Twenty candidate pixel statistics
were measured on every row (tone occupancy, colour cells covering 90% of the
foreground, 16-colour quantise residual, component density, local-std bands,
gradient roughness, structure-tensor coherence, spectral slope). A brute-force
search over every two-term axis rule bottoms out at five misses, and every one
is in that set or is a photoreal render with an alpha cut-out (`drone_render`,
`isometric_icon`). **Stage 0 reads the medium, not the subject.** A rule that
excludes photographed graphics excludes photographs.

## 4. The rule

One new signal, one veto, both scale-normalised; today's two gates stay.

**`texture_frac`** — the fraction of foreground pixels, on a raster whose
long edge is resized to 512 px (`cv2.INTER_AREA`, the mask resized the same
way and read as `> 0`; smaller files are read as they are), whose 5x5
luminance standard deviation is at least 2 and under 24 grey levels: neither
flat nor a hard edge. Luminance is `cv2.COLOR_RGB2GRAY` as float32; the
standard deviation is the population one from two `cv2.blur` passes
(`sqrt(max(blur(g*g) - blur(g)^2, 0))`, default reflect border). Under 25
foreground pixels it reads 0.0. A designed graphic is flats and edges;
a photograph is mostly the band between.

| population | min | max |
|---|---|---|
| opaque photographs (18 corpus + `owl_kent`) | 0.245 (`watercolor`) | 0.926 (`oil_painting`) |
| opaque designed graphics (15: corpus + repo logos) | 0.011 | 0.097 (`barcode`) |
| opaque photographed graphics (6, §3) | 0.289 (`comic_halftone`) | 0.968 (`halftone_dots`) |

Gate `TEXTURE_PHOTO_MIN = 0.17`, margin 0.07 (the midpoint of 0.097 and
0.245; leave-one-out moves it between 0.16 and 0.21). Width ladder 250–1600
px (PIL LANCZOS, the scale-invariance test's resampler): every photograph
stays at or above 0.245 at every width; every designed graphic stays under
0.10 except `barcode` exported at 640 px or below (0.17–0.31: its bars blur
into texture). That is the one stated limit.

**Opaque files only.** The texture route is consulted only when the file has
no alpha cut-out (no alpha channel, or no pixel with alpha <= 127). A file
with a transparent background is a design-tool export whose boundary the
uploader already decided, and every photoreal render in the corpus is one
(`drone_render`, `isometric_icon`, `heraldic_crest`). Such files take exactly
today's tree, byte-identical — which keeps the `drone_render = gradient` pin
that the classifier's docstring calls load-bearing. A customer's own cut-out
photo (a pet on a transparent PNG) routes as it does today; no regression,
no gain.

**`two_tone_mass`** — the share of foreground pixels in the two best-filled
of sixteen equal luminance bins (`cv2.COLOR_RGB2GRAY` uint8 `// 16`), read at
native resolution on the same foreground the other signals use; 0.0 on an
empty foreground. At or above 0.90 the
file is two inks (arabic 0.978, tires 0.995, barcode 0.974, qr 1.000;
photographs top out at 0.763) and never photo territory, whatever the grain
gate says. Gate `TWO_TONE_MAX = 0.90`, margin 0.06.

**Decision:**

```
cutout     = alpha present and any alpha <= 127
if cutout or not cfg.stage0_texture_gate:
    photo  = unique_color_mass >= 0.28            # today's tree, whole
else:
    two_tone   = two_tone_mass >= 0.90
    by_grain   = unique_color_mass >= 0.28        # today's gate, unchanged
    by_texture = texture_frac >= 0.17
    photo      = (not two_tone) and (by_grain or by_texture)
```

A cut-out file takes the whole of today's tree — veto included — so "byte-
identical for every alpha fixture" is literally true and the pin story has one
branch. The veto is therefore only ever read on opaque files; nothing in the
corpus or the repo tests it on a cut-out.

Inside photo territory the subject/scene split is unchanged
(`gradient_smoothness >= 8.0`); every corpus photograph reads under 8, so all
land `photo_scene`. Outside it the flat/gradient gate is unchanged.

**Confidence**: the photo-gate confidence is, for a photo verdict, the
strongest firing route's gate confidence, capped by the veto's distance from
firing; for a non-photo verdict, the weakest of the non-firing routes, or the
veto's when the veto decided. As today, the overall confidence is the minimum
of that and the inner gate's (`gradient_smoothness` against 8.0 inside photo
territory, 0.0015 outside); `CONFIDENCE_FLOOR` demotion unchanged. Gate
margins: texture 0.07, two-tone 0.06.

**Seed sweep**: `CLASSIFICATION_SEED_UNSTABLE` reports a verdict the k-means
seed could move. When the texture route or the veto decided the verdict, the
grain gate's crossings no longer can, so the warning is withheld on those rows
(the sweep's signals are still reported). Confidence is still never touched
by the sweep.

**Flag**: `PipelineConfig.stage0_texture_gate: bool = True`. OFF restores
today's decision tree exactly (the new signals are still reported). The OFF
arm is pinned on every row whose class moves, through the dated engine
snapshot (`frozen_cfg`), so a later flip cannot move the pin.

## 5. What moves (readings on the corpus files and the repo fixtures)

| row | before | after | route |
|---|---|---|---|
| 15 photographs (architecture, dark_dog, fireworks, flower_macro, food_plate, landscape_lake, night_neon, night_skyline, oil_painting, stained_glass, underwater_reef, watercolor, group_people, sports_action, vintage_sepia) | gradient | photo_scene | texture |
| bw_street, snow_highkey, pencil_sketch | photo_scene | photo_scene | grain + texture |
| `photo/owl_kent.jpg` | gradient | photo_scene | texture |
| arabic_calligraphy | photo_scene | gradient | veto |
| `logo_script_tires.png` | photo_scene | gradient | veto |
| halftone_dots, vintage_engraved_badge | photo_scene | photo_scene | grain + texture (photographs, §3) |
| chalkboard_lettering, duotone_poster, kanji_brush, comic_halftone | gradient | photo_scene | texture (photographs, §3) |
| every other row and fixture (29) | unchanged | unchanged | — |

Downstream, `group_people`, `sports_action`, `vintage_sepia` and
`comic_halftone` still sew FLAT: stage 1.25's face detector re-answers stage 0
under Kent's 2026-09-30 ruling, which this design does not touch. The
`photo_subject` gate's bimodality (DOCTRINE 2026-08-12) is also untouched:
no corpus photograph reaches `photo_subject`.

## 6. Goals, non-goals, anti-goals

Goals: every opaque photograph in the corpus classifies in photo territory;
no designed graphic in the corpus or the repo moves into it; the two
DOCTRINE-recorded two-ink misroutes (tires, arabic) leave it; the rule is
three constants a reader can check against the table above; the OFF arm is
one flag away and pinned.

Non-goals: the flat/gradient gate (PR 6a's scale defect, `color_diversity`),
the subject/scene split, the face route, the cutout's empty-mask guard
(sibling lane), the `max_colors` leak and the `stained_glass` stage-5 hang
(both noted in the census and out of scope here).

Anti-goals: routing by file format or EXIF; a learned classifier; a threshold
sited on synthetic fixtures; any claim that a row sews BETTER in its new lane
— that is Kent's verdict on the side-by-side page.

## 7. Instrument and evidence

`tools/stage0_photo_gate.py` prints the three signals, the decision under
both arms and the margins for every corpus row and fixture, and a width
ladder on request, so the numbers above can be re-read rather than quoted.
The corpus capture at the merge-base and at HEAD, and the side-by-side page,
are the PR's judging evidence; the per-row class table before/after goes in
the PR body.

## 8. Left to the builder

Exact placement of the resize (after the alpha-edge extension, on the same
`rgb`/`fg` the other signals read); the signal names in `signals` and the
debug dump; the lens (`tools/classify_lens.py`) re-derivation and its
self-check; which existing goldens the two-ink veto moves on `tires` and how
each is pinned.
