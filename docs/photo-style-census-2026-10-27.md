# Photo-style census — 2026-10-27

**What this is.** Eighteen PHOTOGRAPH genres the auto-digitizer had never been
run on, one licence-clean Wikimedia Commons sample each, pushed through the
pipeline the way the Studio does (the `left_chest_80` request from
`app/src/lib/fixtures/studio-request.json`: 80 mm, 6-colour cap, bean edge cap,
enclosed white sewn, `detect_photographic` + `faces_route_flat`, garment
`left_chest`), one image per process with a hard kill at 1500 s. The sibling
census of LOGO / graphic styles (`docs/logo-style-census-2026-10-27.md`) ran
the same harness the same day.

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4). SSIM and ΔE are raw agreement figures between an 8 px/mm
`stitchviz` render on fabric 223/232/235 and the input, not chance-corrected;
preflight grades are the preflight's own opinion; "my read" is one person
looking at the render. Nothing here is a stage-0 recalibration (gate 2) and
nothing was sewn (gate 1). Wall-clock was measured **under load**: a pytest
`-n 3`, `bean_census`, the logo census runner and this census's second runner
shared the 8-core laptop throughout, which inflates process time ~2.6x
(memory `digitize-speed-2026-10-26`). Read seconds as an upper bound and as
RELATIVE between rows, never as a budget. "plan s" is `plan_stitches` minus
`finish_generation` from the worker's own stamps.

No image was committed. Samples, renders, stack dumps and `sheet.html` live
in the session scratchpad and were handed to Kent directly.

## What the repo already covers

`digitizer/testdata/photo/` holds one real photograph with a subject on a
plain ground (`owl_kent.jpg`, plus its pale variant), one phone-camera
Instagram original under `acceptance/`, and six engineered photo fixtures that
each isolate one mechanism: `photo_grass_macro`, `photo_dof_meadow`,
`photo_sunset_backlit`, `photo_chrome_specular`, `tight_crop_pale_subject`,
`fur_ramp`, and the two `*_stub` class probes. The 2026-10-12 hairline trial
and the 10-13 cold profile ran on the same owl. Nothing in the corpus is a
full-bleed scene with no subject, a night exposure, a group of faces, a
monochrome or sepia print, a painting or drawing photographed, a high-key
image, an underwater or backlit-glass colour field, or an action shot. Those
are the eighteen below.

## The picks

| genre | file (Commons title) | page | author | licence | original px |
|---|---|---|---|---|---|
| architecture | Münster, Westdeutsche Lotterie -- 2018 -- 0417.jpg | https://commons.wikimedia.org/wiki/File:M%C3%BCnster,_Westdeutsche_Lotterie_--_2018_--_0417.jpg | <span title="German photographe | cc by-sa 4.0 | 6467x4311 |
| bw_street | Street Craftsman in Olinda.jpg | https://commons.wikimedia.org/wiki/File:Street_Craftsman_in_Olinda.jpg | Wilfredor | cc0 | 4288x2848 |
| dark_dog | DSC09611a Search and Rescue Dog, Austrian Red Cross Perchtoldsdorf, 2024-10.jpg | https://commons.wikimedia.org/wiki/File:DSC09611a_Search_and_Rescue_Dog,_Austrian_Red_Cross_Perchtoldsdorf,_2024-10.jpg | Aciarium | cc by 4.0 | 3195x4260 |
| fireworks | Fireworks on New Year's Eve in a small Swabian village (1), brightened.jpg | https://commons.wikimedia.org/wiki/File:Fireworks_on_New_Year%27s_Eve_in_a_small_Swabian_village_(1),_brightened.jpg | Andreas Weith | cc by-sa 4.0 | 6366x3581 |
| flower_macro | Blueten 002 2021 08 23.jpg | https://commons.wikimedia.org/wiki/File:Blueten_002_2021_08_23.jpg | Friedrich Haag | cc by-sa 4.0 | 4007x4007 |
| food_plate | Hamburger and fries at Deliroom Ukkohauki close up.jpg | https://commons.wikimedia.org/wiki/File:Hamburger_and_fries_at_Deliroom_Ukkohauki_close_up.jpg | <a href="//commons.wikimedia.org/w/index | cc by-sa 4.0 | 4608x3456 |
| group_people | 3 barefoot females smiling and sitting on a bench.jpg | https://commons.wikimedia.org/wiki/File:3_barefoot_females_smiling_and_sitting_on_a_bench.jpg | JLS Media | cc by-sa 2.0 | 1067x800 |
| landscape_lake | Zagedan Lakes, Mountain cirque, Caucasus Mountains.jpg | https://commons.wikimedia.org/wiki/File:Zagedan_Lakes,_Mountain_cirque,_Caucasus_Mountains.jpg | Vyacheslav Argenberg | cc by 4.0 | 4912x3264 |
| night_neon | Colorful neon street signs in Kabukichō, Shinjuku, Tokyo.jpg | https://commons.wikimedia.org/wiki/File:Colorful_neon_street_signs_in_Kabukich%C5%8D,_Shinjuku,_Tokyo.jpg | Basile Morin | cc by-sa 4.0 | 6521x4347 |
| night_skyline | Tokyo Tower, Minato City.jpg | https://commons.wikimedia.org/wiki/File:Tokyo_Tower,_Minato_City.jpg | David Kernan | cc by 4.0 | 5991x3370 |
| oil_painting | Oil on Canvas Portrait of Dred Scott (cropped).jpg | https://commons.wikimedia.org/wiki/File:Oil_on_Canvas_Portrait_of_Dred_Scott_(cropped).jpg | Schultze, Louis | public domain | 3495x4321 |
| pencil_sketch | Sketch of woman LCCN2017646868.jpg | https://commons.wikimedia.org/wiki/File:Sketch_of_woman_LCCN2017646868.jpg | Metzner, Adolph, artist | public domain | 6072x7260 |
| snow_highkey | Snow-covered Saint-Charles Cemetery 6.jpg | https://commons.wikimedia.org/wiki/File:Snow-covered_Saint-Charles_Cemetery_6.jpg | <span title="developer analys | cc0 | 8256x5504 |
| sports_action | CINvPGH 2018-04-21 - Thomas Vancaeyezeele (40054762600) (cropped).jpg | https://commons.wikimedia.org/wiki/File:CINvPGH_2018-04-21_-_Thomas_Vancaeyezeele_(40054762600)_(cropped).jpg | Hayden Schiff from Cincinn | cc by 2.0 | 1289x1891 |
| stained_glass | Holy Spirit stained-glass window (Cathedra Petri).jpg | https://commons.wikimedia.org/wiki/File:Holy_Spirit_stained-glass_window_(Cathedra_Petri).jpg | Wilfredor | cc0 | 5097x7625 |
| underwater_reef | Coral reef near Marsa Alam.jpg | https://commons.wikimedia.org/wiki/File:Coral_reef_near_Marsa_Alam.jpg | Thomas Hubauer | cc by-sa 2.0 | 2816x2112 |
| vintage_sepia | Hook family portrait, December 1924 (6596215431).jpg | https://commons.wikimedia.org/wiki/File:Hook_family_portrait,_December_1924_(6596215431).jpg | whatsthatpicture from Hanw | cc by 2.0 | 1161x1600 |
| watercolor | Landscape 1. - abstract colorful watercolor painting on paper - artist Fons Heijnsbroek.jpg | https://commons.wikimedia.org/wiki/File:Landscape_1._-_abstract_colorful_watercolor_painting_on_paper_-_artist_Fons_Heijnsbroek.jpg | Fons Heijnsbroek | cc0 | 7069x5315 |

## Results

| genre | class (conf) | route | rembg kept | wall s | plan s | stitches | trims | stops / threads | palette cap | re-snapped | size mm | st/cm² | grade | SSIM | ΔE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| architecture | gradient (1.0) | gradient | – | 671 | 259 | 19766 | 109 | 14 / 6 | 10→6 | 19 | 81x54 | 455 | F 0 | 0.413 | 10.0 |
| bw_street | photo_scene (1.0) | photo_scene | 31% (bg 0→69%) | 316 | 149 | 11862 | 53 | 9 / 5 | – | 2 | 73x43 | 374 | F 4 | 0.14 | 35.0 |
| dark_dog | gradient (1.0) | – | – | killed 1500 | – | – | – | – | – | – | – | – | – | – | – |
| fireworks | gradient (1.0) | gradient | – | 962 | 802 | 25362 | 99 | 11 / 6 | 9→6 | 31 | 81x46 | 690 | F 0 | 0.175 | 13.4 |
| flower_macro | gradient (1.0) | gradient | – | 506 | 320 | 32873 | 63 | 15 / 13 | 8→6 | 23 | 81x81 | 505 | F 0 | 0.332 | 13.6 |
| food_plate | gradient (1.0) | gradient | – | 1040 | 758 | 33173 | 95 | 15 / 8 | 15→6 | 47 | 81x61 | 679 | F 0 | 0.201 | 18.2 |
| group_people | gradient (1.0) | FACE_ROUTED_FLAT | – | 646 | 562 | 41836 | 232 | 10 / 6 | – | 49 | 80x60 | 859 | F 0 | 0.189 | 14.8 |
| landscape_lake | gradient (0.74) | gradient | – | 1240 | 1083 | 36053 | 165 | 16 / 6 | 11→6 | 26 | 81x54 | 831 | F 0 | 0.124 | 15.3 |
| night_neon | gradient (1.0) | – | – | killed 1500 | – | – | – | – | – | – | – | – | – | – | – |
| night_skyline | gradient (1.0) | gradient | – | 403 | 182 | 14314 | 81 | 14 / 8 | 11→6 | 37 | 81x46 | 389 | F 0 | 0.276 | 11.7 |
| oil_painting | gradient (0.93) | gradient | – | 568 | 285 | 34005 | 55 | 8 / 6 | 8→6 | 3 | 81x100 | 422 | F 0 | 0.338 | 10.1 |
| pencil_sketch | photo_scene (0.62) | photo_scene | 0% (bg 16→100%) | 290 | 0 | 211 | 4 | 4 / 3 | – | 0 | 56x85 | 4 | B 88 | 0.765 | 14.3 |
| snow_highkey | photo_scene (0.79) | photo_scene | 0% (bg 0→100%) | 118 | 0 | 0 | 0 | 0 / 0 | – | 0 | 0x0 | 0 | A 100 | 0.018 | 40.6 |
| sports_action | gradient (1.0) | FACE_ROUTED_FLAT | – | 812 | 673 | 59784 | 130 | 9 / 6 | – | 1 | 80x118 | 630 | F 0 | 0.213 | 14.2 |
| stained_glass | gradient (0.59) | – | – | killed 1500 | – | – | – | – | – | – | – | – | – | – | – |
| underwater_reef | gradient (1.0) | gradient | – | 448 | 220 | 29005 | 187 | 13 / 6 | 10→6 | 17 | 81x61 | 594 | F 0 | 0.301 | 15.0 |
| vintage_sepia | gradient (1.0) | FACE_ROUTED_FLAT | – | 344 | 255 | 53353 | 112 | 5 / 5 | – | 1 | 80x111 | 598 | F 28 | 0.327 | 9.5 |
| watercolor | gradient (1.0) | gradient | – | 1234 | 1083 | 24433 | 117 | 11 / 7 | 11→6 | 6 | 80x60 | 507 | F 0 | 0.313 | 25.7 |

## Ranking

One person's read of the 8 px/mm render, tie-broken by the readings. "Legible"
means the subject can be named from the render alone; nothing here was sewn.
Fifteen designs, three kills.

| rank | genre | my read | the reading that decides it |
|---|---|---|---|
| 1 | flower_macro | legible: petals, centre, stem; cleanest fill | SSIM 0.332, 63 trims, but 13 cones from a 6 cap (item 3) |
| 2 | oil_painting | legible portrait silhouette, face reads at arm's length | SSIM 0.338, ΔE 10.1, 55 trims — fewest trims of the full-bleed rows |
| 3 | watercolor | the painted shapes reproduce; the paper correctly became fabric | 1234 s (1083 planning), 7 cones from a 6 cap, ΔE 25.7 is the dropped paper |
| 4 | sports_action | legible player, ball and banner letters | 59,784 stitches / 130 trims at 80 × 118 mm (item 7) |
| 5 | landscape_lake | legible: peaks, lake, meadow, posterised to 6 | 36,053 st, 165 trims, 1240 s wall (item 5) |
| 6 | vintage_sepia | frame and four figures read; every face is lost | 53,353 st on 4 cones at 80 × 111 mm, flat lane (item 7) |
| 7 | architecture | legible window rows, flat and dark | SSIM 0.413 (highest), 14 stops on 6 cones (item 4) |
| 8 | group_people | three figures readable, busy | 41,836 st, 232 trims — most trims of the run (item 7) |
| 9 | bw_street | the craftsman reads; the street is gone | cutout kept 31% of a `photo_scene` (item 1) |
| 10 | underwater_reef | coral texture, no subject to name | 187 trims on 29,005 st; same bytes from two runs 115 s apart |
| 11 | fireworks | one burst reads, rest black field | 962 s, 802 s of it planning |
| 12 | night_skyline | tower lost; dark field with specks | SSIM 0.276 but 8 cones from a 6 cap |
| 13 | food_plate | unreadable colour blocks | ΔE 18.2, 15 stops, 1040 s |
| 14 | pencil_sketch | two marks on a blank hoop | cutout removed 100%, 211 stitches, preflight B 88 (items 1, 2) |
| 15 | snow_highkey | empty | cutout removed 100%, 0 stitches, preflight A 100 (items 1, 2) |
| — | night_neon | no design | killed at 1500 s in stage 6/7 |
| — | dark_dog | no design | killed at 1500 s in stage 7 (`column_lean`) after ~480 s of build |
| — | stained_glass | no design | killed at 1500 s; 6 of 12 sampler dumps inside `resolve_overlaps` (stage 5), OCR ran on the window |

Pattern across the fifteen: a single subject on a quiet ground (flower,
portrait, painting) survives the 6-cone posterise; a scene whose meaning is
in texture or small bright detail (skyline, fireworks, food, reef) does not;
faces push a whole scene onto the flat lane at 40–60k stitches; and a pale
or line-art image can vanish entirely through the cutout.


## What needs resolving

Ordered by how much of the eighteen it touches, then by how wrong the
customer-facing answer is. Every figure is a reading from this run.

1. **The subject cutout can eat the whole picture and nothing notices.**
   `snow_highkey` (photo_scene 0.79) came back with the background fraction
   going 0% → 100%; `pencil_sketch` (photo_scene 0.62) 16% → 100%. The
   cutout block in `pipeline.py` (~610–660) treats only a `None` return as
   failure, so a mask that removes every pixel is accepted, stage 2 finds 0
   regions and the design is 0 × 0 mm with 0 stitches (snow) or 211
   stitches over 4 st/cm² (sketch). `bw_street` is the softer form: a
   street SCENE cut down to the craftsman, 69% of the frame removed,
   coverage 0.454, ΔE 35. A cutout that removes more than some fraction of
   the frame on a `photo_scene` input should be refused and the full frame
   kept.

2. **Preflight grades an EMPTY design A 100.** `snow_highkey`'s 0-stitch
   design has no findings at all; `pencil_sketch`'s 211 stitches grade
   B 88. There is no empty- or near-empty-design finding in
   `preflight.py` (scoring at ~3975–4020 is 100 minus deductions, and
   nothing deducts for coverage 0.000). `ARTWORK_UNCOVERED` exists but
   fires as `info` (architecture, coverage 0.998). A customer would see a
   green card over a blank hoop. Needs a `block` when sewn coverage of the
   artwork is under a floor.

3. **"Colors (max 6)" is kept at stage 4 and broken by stage 6.**
   `enforce_color_cap` runs after the re-snap (`pipeline.py` ~922) and its
   warning says 8 → 6 on `flower_macro`, 15 → 6 on `food_plate`, 11 → 6 on
   `night_skyline`, 11 → 6 on `watercolor`. The sewn designs load 13, 8, 8
   and 7 cones (the cap holds on the other seven gradient rows). On
   `flower_macro` seven of the extra cones carry ONE shape each and
   0.01–0.08 m of thread each, and one shape (`Sbea7df80`) is sewn in five
   different cones — the gradient lane's blend tier adds layers in cones
   the cap never admitted. `_cap_tonal_layers` (`cfg.tonal_split_layer_cap`)
   only runs under `effective_split_tonal`, i.e. photo classes, so the
   gradient lane has no post-stage-4 cap at all. This is the second half of
   MASTER_SCOPE 15: `bind_resnap_all_classes` (ON since 09-10) closed the
   re-snap escape, and `tools/resnap_escape.py` counts only that half.
   Each stray cone is a full colour change for a sliver.
   **Re-read 2026-10-29 (`tools/cone_escape.py`):** `_cap_tonal_layers` caps
   fill LAYERS, not colours, and was never the hole. Two mechanisms: the
   "Sew white areas" recolour after the cap (both leaks on main, isometric_icon
   and watercolor: 6 artwork cones + White) and the blend tier's chart-wide
   band snap on the gradient lane (these four rows, forced gradient:
   13 / 8 / 8 / 9). `cfg.color_cap_sewn` (built OFF) closes both; the flip is
   Kent's. Spec: `docs/superpowers/specs/2026-10-29-colour-cap-sewn-design.md`.

4. **Colour revisits double the stops.** Blocks (stops) against distinct
   cones: architecture 14 / 6, landscape_lake 16 / 6, night_skyline 14 / 8,
   food_plate 15 / 8, flower_macro 15 / 13, group_people 10 / 6.
   `COLOR_STOPS_HEAVY` fires on architecture. Some revisiting is layering
   the pro also does (memory `buried-walk-2026-10-26`: his Drone metre is
   layering plus colour revisits), so this is a reading to compare against
   a pro photo file, not yet a defect — and no pro photo file exists in the
   corpus to compare against.

5. **Planning time, not segmentation, is the wall now.** Three of
   eighteen were killed at 1500 s (`night_neon`, `dark_dog`,
   `stained_glass`), seven more ran past the service's 600 s ceiling
   (landscape_lake 1240, watercolor 1234, food_plate 1040, fireworks 962,
   sports_action 812, architecture 671, group_people 646).
   `build_generation` took 59–252 s on every finished row (the RAG fast
   path from #1157 is in); stages 5–7 took 60–88% of wall on the gradient
   inputs (landscape 1083 of 1240, watercolor 1083 of 1234). The 120 s
   sampler dumps spread across `best_fill_angle_deg` / `_row_spans`, the
   `travel_path` family (`_order_cost_walk`, `_reorder_for_fewer_cuts`),
   `keyline_runs`, `resolve_overlaps`, `silhouette_underfill`, and stage 7's
   `column_lean` / `_sewn_linear_cover` — no single hotspot, except
   `stained_glass`, where 6 of 12 dumps sat in `resolve_overlaps` (stage
   5) and the text tagger ran OCR on a church window. Divide by the ~2.6x
   load factor and landscape_lake is still ~480 s. A photo input of
   200–600 regions is a different workload from a 20-shape logo and has no
   speed lane.

6. **The service reports a long job dead while still computing it.**
   `digitizer_service/jobs.py`: `JOB_TIMEOUT_S = 600.0`; `_expire_locked`
   (line 263) marks a RUNNING job `TIMED_OUT` lazily on READ, but the
   single-worker ThreadPool keeps running it, so the next upload queues
   behind a job the Studio has already been told failed. Every row above
   600 s here would present in the Studio as "stopped waiting" and then
   jam the following job for up to 15 more minutes. Fix is a real cancel
   or a worker that checks the deadline between stages.
   **Fixed 2026-10-30** (`digitizer_core/deadline.py`, memory
   `service-timeout-cancel-2026-10-30`): the worker arms a deadline the
   pipeline checks at every stage seam and per shape in stage 7; the next
   upload waited 497.9 s behind a dead `night_skyline` before, 10.5 s after.

7. **Faces route FLAT, and a crowd or an action shot flat is 40–60k
   stitches.** `group_people` (three faces): 41,836 stitches, 232 trims,
   859 st/cm² at 80 × 60 mm. `sports_action` (one face, full body):
   59,784 stitches, 130 trims, 80 × 118 mm. `vintage_sepia` (a 1924 family
   portrait): 53,353 stitches, 112 trims, 80 × 111 mm on 4 cones. DOCTRINE
   2026-09-30 "A face sews FLAT" was ruled on portraits; `faces_route_flat`
   has no face-size or stitch-budget gate, so a small face in a scene drags
   the whole scene onto the flat lane. Needs a minimum face fraction of the
   frame, or a stitch-budget readout the Studio shows before the download.

8. **No EXIF on real uploads, so detection is faces or nothing.** Commons
   thumbnails strip EXIF, as do screenshots, messaging apps and most
   re-saves; `exif_camera` fired on 0 of 18. Only the two face inputs were
   detected photographic; the other sixteen routed by stage 0 alone
   (14 gradient, 3 photo_scene via UCM) and never got `is_photographic`'s
   depth sequencing and palette bind (MASTER_SCOPE 15). Kent held the EXIF
   change on 10-27 (memory `upload-full-res-2026-10-27`); this records what
   that costs on scenes without faces.

9. **Preflight F on every photo, so grades cannot rank them.** Fifteen
   finished designs: thirteen grade F, and eleven of those score exactly 0
   from unclamped raw scores of −38 to −158 (`metrics["raw_score"]`, which
   nothing reads). The deductions are `THREAD_MATCH_POOR` blocks — 2 to 7
   per design, one per cone the chart cannot match — plus `GROUND_SEWN` on
   architecture, night_skyline and oil_painting. `GROUND_SEWN` blocks a
   full-bleed photo by definition (the ground IS the picture), and
   `THREAD_MATCH_POOR` fires on every blended photo colour. The only
   non-zero F is `vintage_sepia` (28, no blocks, 4 cones), and the two
   passes are the empty designs. A photo lane needs either a different
   rubric or a declared full-bleed mode that drops `GROUND_SEWN` and scores
   thread match once per design.

10. **No in-repo fidelity instrument for a full-bleed photo.**
    `artfidelity_self` refuses full-bleed inputs, so the SSIM and ΔE
    columns above come from an ad hoc script in the scratchpad. Until one
    lands in `tools/`, every photo-lane claim is a render and an eyeball.

## What the sibling logo census adds

`docs/logo-style-census-2026-10-27.md` (same harness, same day): 21
graphic styles, 8 recognisable / 7 partly / 6 not, 12 numbered items. Its
top three, all instrument readings: (1) elements dropped with the ground
that preflight still grades A/B (grunge monogram, duotone disc, QR modules;
`ARTWORK_UNCOVERED` is scoped to sewn shapes), (2) rembg on the photo route
erasing 90% of a photographed graphic with only `PHOTO_BACKGROUND_REMOVED`
to show for it, (3) planning time on many-region art (3 of 21 over the
Studio's 600 s). Items 1 and 2 are the same two blockers as items 2 and 7
above, seen from the graphic side; the harness, the timeout and the
preflight rubric findings apply to both. Its 21 inputs are the corpus's
`kind: "logo"` rows (four of them are photographs OF a graphic:
chalkboard_lettering, kanji_brush, duotone_poster, comic_halftone, kept on
purpose: a phone photo of a sign is a photo Kent's customers send).

## The standing scorecard this census became

Kent, on the montage: "it's as if this digitize was only building tools to
improve the photos we had on hand. This digitizer needs to be building tools
that help and improve ALL photos." His pick for what to look at on a photo
PR: a side-by-side he can mark better or worse. That is
`digitizer/tools/photo_corpus.py` (COOKBOOK "Judging a photo PR across all
genres"): these 18 inputs plus the logo census's 21 are the committed corpus
list (39 rows) (`digitizer/testdata/photo/corpus/corpus.json`, images fetched locally,
never committed), `capture` digitizes them at two trees, `sxs` builds the
page, and Kent's exported verdicts are filed under
`docs/scoreboards/photo-corpus/`. The `main` baseline's instrument numbers
sit beside them as `baseline-<sha>.json`.

## Reproducing

Worker: one process per image, `build_generation(pixels, cfg,
exif_source=data)` → `finish_generation(gen.fork(), cfg)` → `plan_stitches`
→ `plan_to_design` → `run_preflight(result, plan, cfg, image=pixels)`, with
`faulthandler.dump_traceback_later(120, repeat=True)` as the sampler and a
1500 s kill from the runner. Config is the Studio's `left_chest_80` request
verbatim. Scripts and every input's licence line are in the session
scratchpad's `scripts/` and `photos/manifest.json`; nothing was added to
the repo but this file.
