# Logo / graphic-style census — 2026-10-27

**What this is.** Twenty-one logo and graphic ART STYLES the auto-digitizer had
never been run on, one licence-clean Wikimedia Commons sample each, pushed
through the pipeline exactly the way the Studio does (the `left_chest_80`
request from `app/src/lib/fixtures/studio-request.json`, 80 mm, 6-colour cap,
bean edge cap, enclosed white sewn, garment `left_chest` on fabric 235/232/223),
one image per process with a hard kill at 1500 s. The sibling census of
PHOTOGRAPH genres ran the same harness the same day.

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4). SSIM and ΔE are raw agreement figures against the input, not
chance-corrected; preflight grades are the preflight's own opinion; "my read"
is one person looking at an 8 px/mm render. Nothing here is a stage-0
recalibration (gate 2) and nothing was sewn (gate 1). Wall-clock was measured
**under load** — two other digitize runners and a pytest were sharing the
8-core laptop throughout — so read seconds as an upper bound and as RELATIVE
between rows, never as a budget.

No image was committed. The samples, renders, stack dumps and `sheet.html`
live in the session scratchpad and were handed to Kent directly.

## What the repo already covers

From `digitizer/testdata/` (and `app/e2e/fixtures/`), every logo fixture is
the same genre: **clean, flat, spot-colour vector art with Latin lettering**,
mostly customer jobs.

| fixture | what it is |
|---|---|
| `becker_marine_logo.png`, `reference/becker_*` | marine logo, block caps + script, with the professionally digitized DST/PES |
| `art/logo_golke_roofing.png`, `photo/logo_gaulke_roofing.png` | roofing wordmark + house mark |
| `art/logo_hotel_fremont_patch.png`, `photo/logo_hotel_fremont.webp` | slab-serif hotel badge with "1895" |
| `art/logo_mfab_hat.png`, `art/logo_mfab_lc.png` | white-keyline lettering on dark |
| `art/logo_toat_beanie.png`, `art/logo_toat_machine.png` | wordmarks, beanie and machine |
| `logo_script_tires.png` | connected script wordmark |
| `photo/logo_drone_thermal_badge.png`, `photo/summit_badge.png` | round badges with a figure and a ring of text |
| `photo/logo_bridge_bar.jpg`, `photo/logo_golden_tee.jpg` | bar / golf logos with small text |
| `photo/enthusiast_logo.png`, `e2e/enthusiast_logo.png` | shield with star and subline |
| `photo/drone_render.png`, `photo/repro_gradient_white_icon.png` | the ONLY gradient-lane logo inputs: a 3D render and a reproduced gradient icon |
| `photo/screenshot_phone_ui_golke.jpg` | a phone screenshot of a logo |
| `logo_whitebg.png`, `logo_alpha.png`, `bg_uncertain.png`, `black_ground_holes.png`, `ribbon_curve.png`, `photo/gradient_ramp_*.png`, `photo/*_stub.png`, `e2e/two-squares.png`, `red-disc.png`, `contrast-palette.png`, `trace-holes-and-colors.png`, `vector_logo.svg`, `small_text_logo.svg` | synthetic fixtures for one mechanism each |
| `photo/owl_kent.jpg`, `photo/photo_*.png`, `fur_ramp.png` | photographs and photo stubs (the tonal lane) |

MASTER_SCOPE area 1 says the same in one line: *"Low confidence beyond flat
spot-color art."* Nothing in the corpus is a non-Latin script, a
machine-readable code, pixel art, a halftone, a distressed texture, an
outline-only or silhouette-only mark, a neon outline, a wireframe, a 3D or
isometric icon, a heraldic crest with many small charges, an engraving, a
duotone poster, chalk on a board, or an emoji-style flat icon. Those are the
twenty-one below.

## The picks

All from Wikimedia Commons, fetched as the 1600 px thumbnail (or the original
when smaller) through the API, filtered to CC0 / public domain / CC BY /
CC BY-SA by `LicenseShortName`. Attribution per file as Commons gives it.

| style | file (Commons title) | page | author | licence | size |
|---|---|---|---|---|---|
| arabic_calligraphy | Official emblem of the Abu al-Rub clan. Gold Arabic calligraphy (أبو الرب) flanked by laurel branches, used by the family association in Zarqa, Jordan.png | https://commons.wikimedia.org/wiki/File:Official_emblem_of_the_Abu_al-Rub_clan._Gold_Arabic_calligraphy_(%D8%A3%D8%A8%D9%88_%D8%A7%D9%84%D8%B1%D8%A8)_flanked_by_laurel_branches,_used_by_the_family_association_in_Zarqa,_Jordan.png | Aja20197 | cc0 | 1024x1024 png |
| barcode | Codbar EAN abc.png | https://commons.wikimedia.org/wiki/File:Codbar_EAN_abc.png | Papy77 at <a href="https://en.wikipedia.org/wiki/f | public domain | 812x251 png |
| chalkboard_lettering | Cartelera escrita con gis en pizarrón en cafetería de la colonia Obrera, en la Ciudad de México, D.F. 03.jpg | https://commons.wikimedia.org/wiki/File:Cartelera_escrita_con_gis_en_pizarr%C3%B3n_en_cafeter%C3%ADa_de_la_colonia_Obrera,_en_la_Ciudad_de_M%C3%A9xico,_D.F._03.jpg | Correogsk | cc by-sa 4.0 | 1600x1200 jpg |
| comic_halftone | Needed LCCN2015648048.jpg | https://commons.wikimedia.org/wiki/File:Needed_LCCN2015648048.jpg | Yanker Poster Collection | public domain | 5472x7018 jpg |
| devanagari_logo | BHU Logo with Tagline Hindi Banaras Hindu University.png | https://commons.wikimedia.org/wiki/File:BHU_Logo_with_Tagline_Hindi_Banaras_Hindu_University.png | Banaras Hindu University | public domain | 983x544 png |
| distressed_grunge | TM Logo grunge mit typo.png | https://commons.wikimedia.org/wiki/File:TM_Logo_grunge_mit_typo.png |  | cc by-sa 4.0 | 2429x2390 png |
| duotone_poster | Exhibition - WPA Federal Art Project LCCN98513179.jpg | https://commons.wikimedia.org/wiki/File:Exhibition_-_WPA_Federal_Art_Project_LCCN98513179.jpg | Work Projects Administration Poster Collection | public domain | 2794x4096 jpg |
| flat_emoji_icon | 4rd Bison 512.png | https://commons.wikimedia.org/wiki/File:4rd_Bison_512.png | XanSurnamehere | cc by 4.0 | 512x512 png |
| gradient_mascot | Linux mascot tux.png | https://commons.wikimedia.org/wiki/File:Linux_mascot_tux.png | OpenClipart-Vectors from Pixabay. Based on Tux des | cc0 | 1057x1280 png |
| halftone_dots | Portrait of S. Ringer. Wellcome M0010501 (crop) (halftone filtered).jpg | https://commons.wikimedia.org/wiki/File:Portrait_of_S._Ringer._Wellcome_M0010501_(crop)_(halftone_filtered).jpg |  | cc by 4.0 | 3793x5276 jpg |
| heraldic_crest | Carniola coat of arms.png | https://commons.wikimedia.org/wiki/File:Carniola_coat_of_arms.png |  | cc by-sa 3.0 | 585x703 png |
| isometric_icon | 3d-iso-color.png | https://commons.wikimedia.org/wiki/File:3d-iso-color.png | Vijay Verma | cc0 | 2400x2400 png |
| kanji_brush | Aruku no kanji.jpg | https://commons.wikimedia.org/wiki/File:Aruku_no_kanji.jpg |  | public domain | 910x888 jpg |
| kanji_seal | Chinese seal (zhuwen).png | https://commons.wikimedia.org/wiki/File:Chinese_seal_(zhuwen).png | d/k | public domain | 500x500 png |
| low_poly | Dolphin triangle mesh.png | https://commons.wikimedia.org/wiki/File:Dolphin_triangle_mesh.png | en:User:Chrschn | public domain | 634x391 png |
| neon_outline_sign | RADIKAL NEON LOGO REGISTERED (1) (2).png | https://commons.wikimedia.org/wiki/File:RADIKAL_NEON_LOGO_REGISTERED_(1)_(2).png | Radikal Group Limited | cc by 3.0 | 600x309 png |
| outline_lineart_logo | Ambigram logo Eye for blind child.png | https://commons.wikimedia.org/wiki/File:Ambigram_logo_Eye_for_blind_child.png | Basile Morin | cc by-sa 4.0 | 6000x4000 png |
| pixel_art_sprite | Fido character from Don't Buy This.png | https://commons.wikimedia.org/wiki/File:Fido_character_from_Don%27t_Buy_This.png | Firebird Software, S. Wilson, J.D. Woodcock | public domain | 1768x1248 png |
| qr_code | QR code Wikimedia Commons (URL).png | https://commons.wikimedia.org/wiki/File:QR_code_Wikimedia_Commons_(URL).png | http://goqr.me/ | public domain | 1000x1000 png |
| silhouette_logo | Logo of LutskZoopark.jpg | https://commons.wikimedia.org/wiki/File:Logo_of_LutskZoopark.jpg | Arteki | cc by-sa 4.0 | 1280x1280 jpg |
| vintage_engraved_badge | Nikolaes Heinsius the Elder, Poemata (Elzevier 1653), Druckermarke.jpg | https://commons.wikimedia.org/wiki/File:Nikolaes_Heinsius_the_Elder,_Poemata_(Elzevier_1653),_Druckermarke.jpg | Scanned by Aristeas (Roman Eisele). Book printed b | public domain | 1531x1158 jpg |

Four of the twenty-one are PHOTOGRAPHS of the style rather than the graphic
itself, because Commons had no licence-clean graphic for the term:
`chalkboard_lettering` (a café board, angled), `kanji_brush` (ink on paper),
`duotone_poster` and `comic_halftone` (both scanned WPA posters; the second is
a halftone-printed photo poster, not a comic panel — no licence-clean comic
panel came up). `halftone_dots` is a photo portrait put through a halftone
filter, which is the dot-screen case exactly. Styles with NO licence-clean
hit after four search passes: none — every term found something, but
"comic-book halftone panel" and "gradient-mesh vector mascot" are
approximations (a halftone poster; a flat-shaded Tux).

## How each was run

`worker.py` (the sibling's) calls the service's own sequence in one fresh
process per image: `_decode_bounded` → `build_generation` →
`finish_generation` → `plan_stitches` → `plan_to_design` → `run_preflight`,
with the `left_chest_80` config verbatim and `faulthandler` dumping every
thread's stack to stderr every 120 s. `run_direct.py` kills a process at
1500 s; none hit it (the longest, the halftone poster, took 1270 s). Renders
are `stitchviz.render_design` at 8 px/mm on the garment colour; grades and
block codes are the preflight's; "lane" is `stage0_classify.classify` run
again on the file (the pipeline's own `CLASSIFIED_*` warning agreed in every
row). SSIM is luminance SSIM between the input resized to the sewn frame
and the render — a RAW agreement number, kept only because the sibling's
table has it; it ranks nothing here (the grunge logo scores 0.041 and
`neon` 0.693 for the same reason: how much of the input is background).

## Ranked

Ranked by my read of the render first (recognisable → partly → not), then
by how much went wrong inside the tier. Every column is an instrument
reading. "threads / stops" is distinct threads in the design against the
number of colour stops the machine sees; the Studio's cap is 6 threads.

| # | style | my read | lane (conf) | s under load | stitches | trims | threads / stops (cap 6) | size mm | grade | block codes | SSIM (raw) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `neon_outline_sign` | **recognisable** | flat (1.0) | 18 | 2,718 | 5 | 3 / 3 | 79.9×40.0 | B 76 | — | 0.693 |
| 2 | `devanagari_logo` | **recognisable** | gradient (1.0) | 43 | 6,267 | 21 | 3 / 3 | 80.2×44.3 | B 88 | — | 0.632 |
| 3 | `flat_emoji_icon` | **recognisable** | gradient (0.85) | 61 | 18,548 | 10 | 4 / 6 | 80.6×91.5 | B 76 | — | 0.193 |
| 4 | `kanji_seal` | **recognisable** | flat (1.0) | 179 | 29,005 | 72 | 2 / 2 | 80.4×80.3 | B 88 | — | 0.211 |
| 5 | `pixel_art_sprite` | **recognisable** | flat (1.0) | 86 | 11,375 | 23 | 2 / 3 | 80.6×57.0 | A 100 | — | 0.048 |
| 6 | `silhouette_logo` | **recognisable** | gradient (1.0) | 192 | 22,532 | 22 | 5 / 5 | 80.3×80.4 | D 52 | — | 0.37 |
| 7 | `arabic_calligraphy` | **recognisable** | photo_scene (1.0) | 123 | 5,276 | 22 | 1 / 1 | 79.7×59.5 | D 46 | THREAD_MATCH_POOR | 0.565 |
| 8 | `gradient_mascot` | **recognisable** | gradient (1.0) | 70 | 24,498 | 10 | 4 / 5 | 80.3×97.3 | D 58 | GROUND_SEWN | 0.307 |
| 9 | `outline_lineart_logo` | **recognisable** | gradient (1.0) | 267 | 14,012 | 43 | 3 / 3 | 79.2×46.0 | B 88 | — | 0.288 |
| 10 | `heraldic_crest` | **partly** | gradient (1.0) | 810 | 38,647 | 160 | 6 / 10 | 80.6×101.2 | D 52 | — | 0.304 |
| 11 | `kanji_brush` | **partly** | gradient (1.0) | 243 | 16,319 | 123 | 6 / 10 | 80.5×78.2 | C 64 | — | 0.598 |
| 12 | `low_poly` | **partly** | gradient (1.0) | 151 | 13,344 | 62 | 6 / 6 | 80.5×49.5 | F 0 | THREAD_MATCH_POOR | 0.579 |
| 13 | `isometric_icon` | **partly** | gradient (1.0) | 114 | 11,700 | 19 | 7 / 9 | 80.6×51.2 | F 4 | THREAD_MATCH_POOR | 0.023 |
| 14 | `duotone_poster` | **partly** | gradient (1.0) | 446 | 40,315 | 79 | 7 / 8 | 79.6×120.7 | F 28 | — | 0.253 |
| 15 | `comic_halftone` | **partly** | gradient (1.0) | 1270 | 57,878 | 214 | 6 / 8 | 77.7×99.8 | F 28 | — | 0.124 |
| 16 | `qr_code` | **not** | flat (1.0) | 202 | 32,851 | 86 | 2 / 4 | 80.5×80.5 | D 46 | GROUND_SEWN | 0.171 |
| 17 | `barcode` | **not** | gradient (0.93) | 46 | 1,418 | 34 | 2 / 3 | 39.5×18.4 | B 76 | — | 0.152 |
| 18 | `distressed_grunge` | **not** | gradient (1.0) | 167 | 16,770 | 35 | 2 / 2 | 80.6×80.5 | A 100 | — | 0.041 |
| 19 | `vintage_engraved_badge` | **not** | photo_scene (0.76) | 928 | 27,002 | 162 | 3 / 6 | 78.0×58.4 | B 76 | — | 0.131 |
| 20 | `halftone_dots` | **not** | photo_scene (0.92) | 334 | 7,227 | 37 | 6 / 10 | 45.0×78.3 | D 46 | THREAD_MATCH_POOR | 0.129 |
| 21 | `chalkboard_lettering` | **not** | gradient (1.0) | 99 | 3,274 | 14 | 6 / 6 | 37.9×34.4 | F 22 | THREAD_MATCH_POOR | 0.136 |

Per-row notes (what the render shows, in my words):

1. **`neon_outline_sign`** — flat lane, 18 s; "Radikal" and "neon." each one satin column per pen stroke, tube width kept; 2 colours; blue thread match flagged; 2 openings kept open
2. **`devanagari_logo`** — both lines legible (blue headline, grey tagline); routed gradient at 1.0 on a flat PNG; one counter of yu sewn white; 3/12 satin shapes under readable size; 43 s
3. **`flat_emoji_icon`** — clean: 6 colours, outlines bordered, horn/eye/hand all present; routed gradient (0.85) though the art is flat; THREAD_MATCH_POOR warns on the two browns
4. **`kanji_seal`** — 500 px red seal-script PNG: flat lane, every stroke a red satin column, counters sewn white (sew_enclosed_white) so it reads as a stamp; 29k st / 449 per cm2 at 80 mm; 9/51 satin shapes under readable; plan_stitches 150 s of 179
5. **`pixel_art_sprite`** — yellow-on-black sprite: black ground removed so the sprite is a yellow silhouette; stair-steps kept as satin teeth; inner black pixels become holes, 4 enclosed white sewn; A/100
6. **`silhouette_logo`** — JPEG logo routed gradient; bear + ring + Cyrillic lettering all present and legible at 80 mm; 7/16 satin shapes under readable size; density stacked 312 mm2 (ring under lettering); 192 s
7. **`arabic_calligraphy`** — 1024 px gold-on-white PNG routed PHOTO_SCENE at conf 1.0 -> rembg + CLAHE + bilateral prep, then ONE Olive thread (block THREAD_MATCH_POOR on 9/11 shapes); calligraphy and both laurels intact, legible; 85 s of 123 in build_generation (rembg)
8. **`gradient_mascot`** — flat-shaded Tux PNG routed gradient; body/belly/beak/feet all present, outlines bordered; pupils LOST (eyes are white ovals); GROUND_SEWN block fires on the black body because stage 1 read black as the art's background (BACKGROUND_UNCERTAIN) -- a false block on a dark-bodied mascot; density stacked 550 mm2
9. **`outline_lineart_logo`** — 6000x4000 B/W PNG routed GRADIENT at conf 1.0 (26 anti-alias halo colours dissolved); build_generation 135 s of 267; black ring + letters satin, white interior filled (sew_enclosed_white) at 385 st/cm2 = 14k stitches for a line-art mark; 16 letters sewn as bean runs (SMALL_LETTERING_AS_BEAN) yet render shows satin letters legible
10. **`heraldic_crest`** — 585x703 PNG, 60 regions -> cap to 6 threads (7 picked, COLOR_CAP_APPLIED), 10 colour stops; eagle, crowns, crescents, shield and mantling all placed; the eagle's feather detail and the small charges merge into one blue mass, white mantling highlights sewn as white over blue; 160 trims (106 inside shapes), 38.6k st at 474/cm2, 101 mm tall at 80 wide; 724 s of 810 in plan_stitches (stage6_fill travel_path / _reorder_for_cover / keyline _satin_loop in the dumps)
11. **`kanji_brush`** — PHOTO of brush ink on creased paper routed gradient: the character is there in two blacks (ink texture split into black + dark), but the paper's creases were segmented and sewn as ~31 grey run/satin patches around it; 123 trims (7.5/1k), 23/50 satin shapes under readable; no "paper is background" verdict (BACKGROUND_UNCERTAIN)
12. **`low_poly`** — dolphin silhouette reads, facets sewn as 5 flat greys (blend lane found no ramp in 40 shapes), wireframe lines gone, dark holes where small facets dropped; F = one THREAD_MATCH_POOR block (Smoky on 34%); 60 same-thread pairs kept apart; density peak 14.9 layers
13. **`isometric_icon`** — 3D-rendered pill icon with soft shading: blend lane found no ramp (5 shapes), so each shaded face is one flat thread; 7 DISTINCT threads in the design against max_colors 6 (6 palette + enclosed white), 9 stops; two THREAD_MATCH_POOR blocks (F/4) on the shaded faces; shapes read as pills but the isometric depth is gone
14. **`duotone_poster`** — scanned WPA poster (tan, orange, dark brown): lettering legible in satin (FEDERAL ART PROJECT / EXHIBITION / 50 BEACON ST), but the poster's ONE big element, the orange disc, is MISSING -- 8 threads capped to 6, THREAD_RESNAPPED_AFTER_DRIFT worst dE00 34.8, disc folded into the tan ground; whole sheet incl. frame sewn edge to edge, 120.7 mm tall, 40.3k st at 420/cm2; 446 s (build_generation 223 s); LETTERING_ILLEGIBLE on one cluster
15. **`comic_halftone`** — scanned halftone-print poster (two portraits + NEEDED): a FACE was detected so FACE_ROUTED_FLAT forced the flat route over a gradient classification; NEEDED legible (N's diagonal dropped, LETTERING_ILLEGIBLE on 2 of 3 clusters), the two halftone portraits sew as grey texture blobs (165 shapes as runs, 119 unbordered); 57.9k st at 746/cm2 over 77.7 x 99.8 mm, 214 trims, 30% of satin stitches under the 1 mm needle minimum (STITCHES_TOO_SHORT), 2164 mm2 stacked past 6.7 layers; 1270 s, 905 of them in plan_stitches (dumps spread over stage5_overlap, stage6 fill/satin/border, textcluster OCR) -- 230 s under the 1500 s kill
16. **`qr_code`** — white ground sewn as one 59% fill (GROUND_SEWN block); 10 black shapes 864 mm2 dropped at the colour clip (SHAPE_NOT_STITCHED); 89 in-shape lifts; finder squares survive as bean outlines; 32.9k st at 507/cm2
17. **`barcode`** — routed gradient at conf 0.93 (JPEG-free PNG!); 58 sub-1.5 mm bars dropped + 36 absorbed; design collapsed to 39.5 x 18.4 mm; edge cap +52% over budget; digits sewn as blobs
18. **`distressed_grunge`** — white gear on BLACK with black inner ring + TM monogram + ring text: ground removed, and the black ring/monogram (same ink as the ground) went with it (BACKGROUND_UNCERTAIN "reached deep inside a shape"); gear body sews as one white fill, TOWER survives as blobs, MACHINE mostly gone; preflight A/100 with no ARTWORK_UNCOVERED, no dropped-element finding; routed gradient 1.0, build_generation 101 s of 167
19. **`vintage_engraved_badge`** — 1653 Elzevier printer's mark (fine cross-hatching): routed PHOTO_SCENE at 0.76 -> rembg removed 42% -> 59% (the hermit figure went with it), CLAHE + bilateral; 209 regions -> 2 threads; the hatching reads as one black mass with white blobs where the lighter hatch survived, 187 planned shapes left unsewn, 86 as runs, 174 absorbed; only the NON SOLUS banner is legible; 162 trims (6/1k), 27k st at 593/cm2; 928 s (build_generation 277, plan_stitches 578) -- the slowest input after the crest
20. **`halftone_dots`** — halftone-filtered portrait JPEG routed PHOTO_SCENE 0.92: rembg "subject cutout" removed 91% of an edge-to-edge image, leaving a head and four scraps at 45 x 78 mm; 8 threads capped to 6 with 10 stops; THREAD_MATCH_POOR block; the dot screen itself never reaches a shape -- bilateral at 15 px kills it first
21. **`chalkboard_lettering`** — phone JPEG of a cafe chalkboard (EXIF SAMSUNG -> PHOTO_DETECTED): rembg removed 90% and kept one corner of the board; 37.9 x 34.4 mm of black fill, a pink rim and grey smudges, no letter survives; 33% of satin stitches under 1 mm; F/22

Tally: **8 recognisable, 7 partly, 6 not.** Lane routing across the 21:
`flat` 4, `gradient` 14, `photo_scene` 3. Every one of the 14
gradient-routed designs ended with `BLEND_NO_REGIONS_DECOMPOSED` (zero ramps
found), so the gradient lane bought nothing but time on these inputs.

## What needs resolving

Numbered, each with the evidence (file, number, stage) and the kind of
problem. The kind is my classification, not a ruling; several items are
Kent's scope calls before they are anyone's defect.

1. **Flat vector logos route to `gradient` (and two to `photo_scene`) —
   routing.** 14 of 21 inputs went `gradient`, among them pure flat PNGs:
   `outline_lineart_logo` (black and white, conf 1.0 — 26 anti-alias halo
   colours were dissolved as "blends"), `devanagari_logo` (1.0),
   `distressed_grunge` (1.0), `heraldic_crest` (1.0), `flat_emoji_icon`
   (0.85), `barcode` (0.93, a 2-colour PNG). Two flat PNGs went
   `photo_scene`: `arabic_calligraphy` at conf **1.0** and the scanned
   engraving at 0.76, which runs rembg + CLAHE + bilateral on art that has
   no photograph in it. The visible cost is time (`build_generation` 100–277 s
   on those rows against 2–25 s on the four `flat` rows) and, on the two
   `photo_scene` rows, rembg's cutout (item 2). The corpus's own flat logos
   route `flat`; these do not because `unique_color_mass` reads anti-aliased
   edges on large PNGs and JPEG ringing as colour mass. **Gate 2 applies:
   this is a reading of where the boundary sits on 21 new files, not a
   recalibration; the fixtures that would site it are still the tonal
   artworks "Waiting on Kent" since 2026-09-11.**

2. **rembg's subject cutout erases graphics that have no subject —
   segmentation, on the photo route.** `halftone_dots`: background fraction
   0% → **91%**, output 45 × 78 mm (a head and four scraps).
   `chalkboard_lettering`: 0% → **90%**, output 37.9 × 34.4 mm, no letter
   left. `vintage_engraved_badge`: 42% → 59%, the hermit figure went with it.
   `arabic_calligraphy` survived (88% → 89%) only because its background
   really is white. `PHOTO_BACKGROUND_REMOVED` is the only trace; nothing
   warns that nine-tenths of the artwork left. A photograph OF lettering or
   OF a print is not a subject photo, and the route has no way to say so.

3. **Ink the same colour as the removed ground is removed with it, and
   preflight grades the result A/100 — segmentation + preflight.**
   `distressed_grunge`: white gear on black with a black inner ring, a black
   "TM" monogram and "TOWER MACHINE" in black; stage 1 removed the black
   ground and the ring, monogram and most of MACHINE went with it
   (`BACKGROUND_UNCERTAIN` "reached deep inside a shape" is the only
   signal). Preflight: **A 100**, no `ARTWORK_UNCOVERED`, because that check
   is scoped to shapes the design already sews (MASTER_SCOPE area 1 says
   exactly this; `black_ground_holes.png` is the existing fixture for the
   same mechanism). The one-colour monogram-on-dark badge is a common
   customer genre; this is the row I would show Kent first.

4. **Whole elements drop at the colour clip and the thread re-snap, and the
   grade does not move — preflight.** `qr_code`: `SHAPE_NOT_STITCHED` — 10
   shapes, **864 mm²**, largest 181.5 mm², "disappeared while being fitted
   against neighbouring colors" (stage 5). `duotone_poster`: the poster's
   one big element, the orange disc, is gone — `THREAD_RESNAPPED_AFTER_DRIFT`
   worst **dE00 34.8**, then `COLOR_CAP_APPLIED` folded it into the tan
   ground; the grade (F 28) comes from thread-match and lettering warnings,
   not from the missing disc. `gradient_mascot` lost both pupils with no
   finding at all. Same blind spot as item 3 seen from the other side: the
   pipeline knows (it wrote the warning) but preflight does not read its own
   `SHAPE_NOT_STITCHED` / re-snap warnings as a dropped-element finding.

5. **Enclosed white sews as a SEVENTH thread above the 6-thread cap, and
   colour stops run to 10 — colour cap.** `isometric_icon`: palette capped
   to 6, design has **7 distinct threads** (6 + `0015 White` from
   `sew_enclosed_white`) and 9 stops; `duotone_poster` 7 / 8 the same way.
   Stops: `heraldic_crest` 6 threads / **10 stops**, `kanji_brush` 6 / 10,
   `halftone_dots` 6 / 10, `comic_halftone` 6 / 8 — each revisit is a colour
   change on the machine the cap was meant to bound. `COLOR_CAP_APPLIED`
   fired on crest, isometric, duotone and halftone; `max_colors` bounds the
   palette, not the design.

6. **Stage 6/7 planning time scales with region count, past the Studio's
   600 s wait — speed.** `plan_stitches` alone: `comic_halftone` **905 s**,
   `heraldic_crest` **724 s**, `vintage_engraved_badge` 578 s,
   `duotone_poster` 135 s; whole-job 1270 / 810 / 928 / 446 s. Stack dumps
   every 120 s (`tally.py`) land in `stage6_fill.travel_path`,
   `_reorder_for_cover`, `_row_spans`, `stage6_border._exact_cross` /
   `_satin_loop` (keyline), `stage6_satin.walk`, `stage5_overlap
   .resolve_overlaps` and `textcluster._ocr_glyph_guess` — no single hot
   frame, the count of shapes is the cost (crest 60 regions, engraving 209,
   comic 165 run-sized shapes). All under load (two other runners + pytest
   on 8 cores), so divide by something between 1 and 2.6 (memory
   `digitize-speed-2026-10-26`); three of the four would still exceed the
   service's 600 s job timeout, and the Studio now waits exactly that long
   (`studio-wait-600`). The sibling's photo census hit the same wall.

7. **Machine-readable codes do not survive — segmentation, and a scope
   call.** `qr_code`: the white ground sews as one 59% fill
   (`GROUND_SEWN` block, correct), 864 mm² of black modules dropped (item
   4), 32,851 stitches at 507/cm², finder squares reduced to bean outlines;
   not scannable, not even module-accurate. `barcode`: 58 bars under 1.5 mm
   dropped and 36 absorbed (`DROPPED_SMALL_SHAPES` / `ABSORBED_SMALL_SHAPES`
   at stage 4's 1.5 mm floor), the design collapsed from the requested 80 mm
   to **39.5 × 18.4 mm**, edge cap +52% over budget — and preflight **B 76**.
   An EAN-13 at 80 mm has 0.84 mm modules, so the 1.5 mm floor is the whole
   story; a QR at 80 mm with 29 modules is 2.8 mm per module and still
   failed, so there it is the clip. PRODUCT.md has no ruling on codes; Kent
   decides whether these are a defect or a "we don't sew codes" message.

8. **`GROUND_SEWN` blocks a dark-bodied mascot — preflight (false block).**
   `gradient_mascot` (Tux, transparent PNG): stage 1 read the black body as
   the artwork's own background (`BACKGROUND_UNCERTAIN`), so preflight
   blocks the design because "the biggest shape is the same colour as the
   artwork's background, 48% of the stitching". The render is one of the
   eight cleanest. The same rule is RIGHT on `qr_code`; the difference is
   whether stage 1's background verdict was right, and preflight trusts it.

9. **`THREAD_MATCH_POOR` sets the grade on shaded and off-chart colours —
   preflight / colour.** It is the block on `low_poly` (F 0: Smoky on
   34% of the design), `isometric_icon` (F 4: two blocks), `halftone_dots`,
   `chalkboard_lettering` and `arabic_calligraphy` (D 46: one Olive thread
   for gold on 9 of 11 shapes). On the 3D-shaded icon the "shape colour" is
   a shaded face that no single thread matches by construction; the finding
   is accurate and unhelpful. Whether gold calligraphy should block on
   Isacord's nearest olive is a chart question, not a pipeline one.

10. **Texture is not shapes: halftone screens, cross-hatching and brush
    texture become masses or confetti — segmentation, and a scope call.**
    `vintage_engraved_badge`: 209 regions → 2 threads, 187 shapes left
    unsewn, 86 as runs, 174 absorbed; the hatching is one black mass with
    white blobs. `comic_halftone`: 165 shapes as runs, 119 unbordered,
    57,878 stitches at **746/cm²**, 30% of satin stitches under the 1 mm
    needle minimum, 2,164 mm² stacked past 6.7 layers. `kanji_brush`: the
    paper's creases sewed as ~31 grey patches around the character (123
    trims). `low_poly`: the wireframe vanished, facets became five flat greys.
    A dot screen or a hatch is a TONE the artist drew with marks; the
    pipeline sews the marks. Nothing in PRODUCT.md says the product takes
    engravings or comic panels; if it does not, the right output is a
    message, not 57k stitches.

11. **Many-element art is trim-heavy inside shapes — trim economy.**
    `heraldic_crest` 160 trims, **106 inside shapes**; `comic_halftone` 214;
    `vintage_engraved_badge` 162 (101 between shapes); `kanji_brush` 123
    (7.5/1k); `qr_code` 89 in-shape lifts. Same family as memory
    `in-piece-cuts-2026-10-25` (fill sections and satin splits), at a scale
    the corpus logos never reach.

12. **Enclosed white on a stamp or a line-art mark multiplies stitch count —
    colour / scope.** `kanji_seal` 29,005 stitches at 449/cm² and
    `outline_lineart_logo` 14,012 at 385/cm² are each a two-colour mark
    where the white counters / interior sew as fill under
    `sew_enclosed_white: true` (the Studio's default request). On the seal it
    makes the render read as a stamp impression (arguably right); on the
    80 mm line-art eye it is 10k stitches of white where a customer would
    expect fabric. Kent's 10-27 "every job" ruling made the white recipe a
    plain default; this is what it does to outline-only art.

### What came out clean

For the record, because a census that only lists failures misleads: the
neon script sign (18 s, one satin column per pen stroke, both colours),
the Devanagari two-line logo (both lines legible), the flat emoji icon,
the red seal-script stamp, the pixel-art sprite (stair-steps kept as satin
teeth), the Cyrillic silhouette badge and the Arabic calligraphy all read
at 80 mm with every element present. Non-Latin scripts were not the problem
anyone might have guessed: the Column lane and `script_strokes` handled
Devanagari, Arabic, Cyrillic and seal script without a Latin assumption
showing.

### Top three, if only three

1. Items 3 + 4 — dropped elements that preflight grades A: the grunge
   monogram, the duotone disc, the QR modules. Preflight blind spot, real
   customer genre.
2. Item 2 — rembg on the photo route erasing 90% of a photographed graphic
   with no finding. Routing/segmentation.
3. Item 6 — planning time on many-region art (3 of 21 over the Studio's
   600 s even allowing for load). Speed.

Item 1 (flat art routed `gradient`) is the most frequent reading but the
cheapest in outcome on these files; it is listed first because it decides
which stages the other items run through.

## Files handed to Kent (not committed)

Session scratchpad: `logos/` (21 inputs + `manifest.json`),
`inputs_montage.png`, `results/<style>.json` + `.stderr.txt` (stack dumps),
`renders/<style>.png`, `sheet.html` (input beside render beside readings, one
file, 15 MB of data URIs), `summary.json`, `reads.md`, and the harness copies
under `scripts/` (`fetch_logos.py`, `worker.py`, `run_direct.py`,
`analyse.py`, `findings.py`, `tally.py`, `montage.py`).

## Where these 21 inputs went

They are the `kind: "logo"` rows of the standing corpus
(`digitizer/testdata/photo/corpus/corpus.json`, list committed, images
fetched by `python -m tools.photo_corpus fetch`, never committed). A photo
or graphic PR captures them at the merge-base and at HEAD and hands Kent
the side-by-side page (COOKBOOK "Judging a photo PR across all genres");
his verdicts are filed under `docs/scoreboards/photo-corpus/`. The readings
above are the `main` baseline those pages diff against.
