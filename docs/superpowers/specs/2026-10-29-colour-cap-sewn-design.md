# The colour cap holds on the SEWN design — design (2026-10-29)

**Every number here is an instrument reading, not a quality claim** (ROADMAP
gate 4: the fidelity figure quoted is the chance-corrected `fidelity_cc`).
Nothing was sewn (gate 1); nothing in stage 0 moves (gate 2). Readings are
from `digitizer/testdata/photo/corpus/` rows and the repo's fixtures at the
Studio's request (80 mm, left chest, `max_colors` 6, "Sew white areas" ticked
white), the config `tools.fremont_triage.studio_request` builds.

## 1. The promise and where it broke

"Colors (max 6)" is a pricing promise: a cone is a spool to buy and, on a
single-needle machine, a re-thread. `enforce_color_cap` (ON since 2026-09-10)
makes it true at stage 4, over the REGIONS, after the palette, the re-snap
and the rehome. The photo-style census of 2026-10-27 (item 3) found the sewn
designs loading 13 / 8 / 8 / 7 cones against the 6 the warning promised.

Attributing every block thread of a leaking design to its source
(`tools/cone_escape.py`, this PR's instrument) finds **two mechanisms, and the census named only one
of them — and misnamed the second's cure:**

1. **The "Sew white areas" recolour runs AFTER the cap.** `apply_enclosed_white`
   (`finish_generation`) recolours every enclosed field it sews to
   `sew_enclosed_rgb`'s nearest chart thread, White `0015`. The cap had ranked
   those regions under the thread they wore at stage 4 (isometric_icon: the
   near-white `0020`, which the cap evicted into Burnt Orange `1312`), and the
   recolour then put White on them regardless. Six artwork cones + White = 7.
   This is BOTH leaks on today's main: `isometric_icon` (gradient lane, 7/6)
   and `watercolor` (photo lane, 7/6 — four enclosed fields, 3,503 stitches,
   7.4 m of White).
2. **The gradient lane's blend tier snaps each shade band to the whole
   ~400-spool chart.** `stage6_blend.blend_fill` and `design_shade_scheme`
   call `chart.nearest_index` with no palette; `_shade_blocks` then sews each
   band in its own block. The photo lane's shade path IS bound
   (`shade_palette_bind`, ON since 2026-08-24) but stage 7 gates that bind on
   `is_photographic`, so a gradient design never gets it. Forced to the
   gradient lane today: `flower_macro` 13 cones (7 strays, every one a band of
   1–2 shapes carrying 8.7–57 mm of thread, each a full colour change);
   `night_skyline` 8 (2 strays of 5.8 m each — real bands, not slivers).
   On the repo's fixtures at the Studio's request: `logo_golden_tee` 9
   (strays of 4.7, 10.4 and 17.0 mm), `summit_badge` 9 (strays of 2.3,
   6.0 and 10.5 m — real bands), `drone_render` 7 (mechanism 1: White on one
   enclosed field). `gradient_ramp_linear`, `gradient_ramp_radial` and
   `repro_gradient_white_icon` load 5 cones from one or two regions and are
   UNDER the budget; they are the designs the bind below must not touch.
   The census blamed `_cap_tonal_layers` / `cfg.tonal_split_layer_cap` for
   this hole. That function caps fill LAYERS (defect 20's density ceiling),
   not colours; it was never a colour cap on any lane.

Every other thread-assigning path after stage 4 was read and is accounted
for: the hairline strands bind to the design's block threads already
(`strand_blocks(allowed_threads=...)`); the edge cap sews a thread the design
loads (`_cap_thread`); appliqué, detail spokes, silhouette under-fill, the
keyline band and the clip pieces use a region's own thread; a review
recolour and a manual shape are the customer's stated colours. Two paths
pick a chart thread of their own: the detail layer (`stage6_detail.
detail_runs`, Studio sends it OFF) and the beanie knockdown (the GARMENT's
colour, `knockdown.py`, beanie only — a cone by design, Kent's 10-21 flip).

## 2. The change: `cfg.color_cap_sewn` (built OFF)

One flag, two seams, OFF byte-identical on every lane:

1. **A second cap pass over the final regions**, at the end of
   `finish_generation`'s recolours (after `apply_enclosed_white` and the
   garment rule, before `compact_layers`), same `enforce_color_cap`, ranking
   by `meta["stitched"]` (resolved by then) instead of the stage-4 enclosed
   heuristic, with a PROTECTED set that always keeps its slot and counts
   against the budget: the threads of review recolours
   (`shape_overrides[*].thread_index`, "a stated recolor still wins") and the
   sew-white thread when any area sews under the tick (the customer named
   that colour). Artwork then competes for the remaining slots; a dropped
   artwork cone lands on its nearest kept thread (CIEDE2000, the dark-ink
   rule included), exactly as at stage 4. Protected threads alone at or over
   the budget keep only themselves: the customer's stated colours ARE the
   budget then. The stage-4 pass is unchanged and still runs first.
2. **A fold over the BLOCKS** (`stage7_sequence.fold_stray_cones`), run on
   the artwork blocks before the adjacent-same-thread merge and once more
   over the finished list (the detail layer picks its cone after the artwork
   pass). The cones the plan loads past the regions' — blend bands,
   layered-streamline shades, the detail layer — are not bound band by band:
   a bind would strip every shade from a one-region gradient ramp that sews
   five cones under a cap of six. The fold spends the budget first: the
   regions' cones keep their slots, the strays fill the slots left, the most
   thread first, and only the remaining strays are recoloured in place to
   their nearest kept cone (CIEDE2000). Sew order, stitches, cuts and ties
   are untouched; a plan at or under the budget comes back the same list.
   `COLOR_CAP_APPLIED` is emitted once per design (the plan's count
   supersedes the regions').

NOT in this change: the knockdown's garment cone (a design decision of its
own), the edge cap and the hairline strands (they sew loaded cones already),
and any Studio copy.

## 3. The decision that is Kent's

Whether the white the customer ticks counts against "Colors (max 6)".
Protected (built): artwork gets 5 when white sews. Competing by area: white
can lose its slot and the ticked areas sew in another thread — the tick's
promise breaks silently. Not counted (today): 7 cones against a label that
says 6. The options and their costs go to him with the readings in §4.

## 4. Readings — fixtures and forced-gradient rows, OFF → ON

`tools/cone_escape.py`, Studio request, cap 6; `blocks` = colour stops. The
fold moves no stitch; the one-to-nine-stitch drift on five rows is the
adjacent-same-thread merge joining a folded block to its neighbour (ties at
the seam) and the second region pass regrouping a few shapes. Fidelity per
corpus row (`fidelity_cc`, OFF and ON) is in the PR body's capture table.

| fixture | class | colours OFF → ON | stops OFF → ON | stitches OFF → ON | what folded |
|---|---|---|---|---|---|
| isometric_icon | gradient | 7 → 6 | 9 → 8 | 11,056 → 11,056 | 1 artwork cone (3 shapes), White kept |
| drone_render | gradient | 7 → 6 | 11 → 11 | 18,678 → 18,678 | 1 artwork cone (6 shapes), White kept |
| watercolor | photo_scene | 7 → 6 | 7 → 7 | 18,745 → 18,750 | 1 artwork cone (22 small shapes), White kept |
| logo_golden_tee | gradient | 9 → 6 | 12 → 10 | 12,003 → 11,999 | 3 bands, 28.8 mm in all |
| summit_badge | gradient | 9 → 6 | 11 → 8 | 27,782 → 27,782 | 3 bands, 18.8 m in all |
| gradient_ramp_linear | gradient | 5 → 5 | 5 → 5 | identical | nothing (under budget) |
| repro_gradient_white_icon | gradient | 5 → 5 | 5 → 5 | identical | nothing (under budget) |
| flower_macro (forced gradient) | gradient | 13 → 6 | 14 → 8 | 30,723 → 30,715 | 7 bands, 251 mm |
| food_plate (forced gradient) | gradient | 8 → 6 | 14 → 12 | 33,551 → 33,553 | 2 bands, 508 mm |
| night_skyline (forced gradient) | gradient | 8 → 6 | 11 → 9 | 13,247 → 13,256 | 2 bands, 11.6 m |
| underwater_reef (forced gradient) | gradient | 9 → 6 | 13 → 10 | 28,454 → 28,452 | 3 bands, 214 mm |

The cost of a fold is where the folded thread is substantial: summit_badge
(18.8 m of band thread recoloured to kept cones) and night_skyline (11.6 m)
lose shading steps; Golden Tee, flower_macro, food_plate and underwater_reef
fold slivers that were each a colour change. Renders of both arms for
summit_badge, Golden Tee and night_skyline accompany the flip question.

## 5. The 39-row corpus, OFF (main 6a031424) → ON (this branch, `--set color_cap_sewn=true`)

`python -m tools.photo_corpus capture`, 2 procs, Studio request. **Two rows
move, 37 are byte-identical** (md5 of the design's stitch stream, colours and
blocks): `isometric_icon` 7 → 6 cones at identical stitches and trims
(11,053 / 20), `watercolor` 7 → 6 at 18,725 → 18,729 stitches, 42 → 44 trims,
`fidelity_cc` −1.659 → −1.667. Every other row loads the same cones it did —
on today's routing the photographs take the photo lane, whose shade bind
already holds, and no logo row carries blend bands past the budget. The
forced-gradient readings in §4 are what the lane would do if routing sent a
photograph there again. `comic_halftone` needed a 2,400 s timeout on this
laptop (1,862 s alone); it was captured OFF on this branch's tree, which is
main's engine byte for byte with the flag off.
