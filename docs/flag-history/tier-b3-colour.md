# Flag history: tier B3, colour and palette (folded 2026-11-20)

Twelve switches, all ON by default, folded into the code (the `cfg.X == True` path kept, the
False branch and the `PipelineConfig` field deleted; `docs/flag-audit-2026-11-19.md`). Each
section below is the field's own comment block as it stood in `config.py`, kept for the
evidence and PR pointers. The names are in `RETIRED_FIELDS`, so an old snapshot or a service
request that still sends one is ignored rather than refused.

## `bind_resnap_all_classes`

```
Bind stage 4's thread re-snap to the selected palette on EVERY class,
not only the photo ones. `revalidate_threads`' argmin runs over the whole
chart off the photo route, so a re-snapped shape can pull in a spool the
palette never chose and the operator loads a cone the plan does not name.

Counted 2026-09-06 (`tools/resnap_escape.py`, MASTER_SCOPE 15): across
the corpus the pass adds **34 cones, 25 of them outside the selected
palette, and every escape is on the GRADIENT lane** — screenshot 7,
drone_render 5, bridge_bar 5, golden_tee 4, gaulke 3. All nine
photo-class fixtures add none: the 2026-08-23 binding does its job, and
the lane real customer logo art routes to never got it.

DEFAULT ON since 2026-09-10 (Kent's ruling on the colour bundle): the
escape is on the FLAT lane too once real logos are forced there
(Golden Tee sews 24 cones under a budget of 12; the bind takes 13 off),
so "gradient only" was a count over routed fixtures. At the Studio's 6
it takes 34 cones and 34 stops off six corpus designs. False is the
pre-flip engine byte for byte.
```

## `design_ramp`

```
The design ramp (2026-09-04, Kent's gradient ruling: one region when
the design ramp fits — `design_ramp.py`). ON: a gradient-class design
whose whole-design ramp passes the fit's gate is segmented with the
sweep subtracted and sewn as one set of shade bands. False keeps the
pre-2026-09-04 gradient lane reachable and tested — the same posture
as `rehome_resnapped` above: the repro's drifted-sliver fixture that
`test_thread_revalidate` traces exists only on that lane, because the
sliver is the merge cutting the sweep. Never read on any other class.
```

## `dissolve_phantom_blends`

```
Run that same phantom-blend dissolve on the PHOTO/GRADIENT lane's
merged labels (`stage2_photo_segment.dissolve_phantom_blends`). The
flat lane above has always done it; this lane never has, and a JPEG
logo pays for the gap in cones — `logo_bridge_bar.jpg` sews the
ringing around its black spokes as four grey threads
(`docs/kent-review-2026-09-03.md`). Built and banked OFF by Kent
on 2026-09-04 (two mild negatives, Whale's leftover shards). ON since 2026-10-20, by
Kent's ruling 2026-10-20 on MASTER_SCOPE item 46, read off PR #1003's
pricing (80 mm, left chest): bridge 17,653 -> 15,196 stitches and
89 -> 66 trims, and it cuts the thin grey halo `clip_keep_pieces`
would sew from 19.06 to 3.06 mm²; golden_tee +25 stitches, +3 trims;
drone, chrome, sunset and gaulke identical. The residual is defect
27's own (`0111` Whale shards, cause not established). False is the
pre-flip engine (`tests/conftest.py`'s PRE_FLIP).
```

## `merge_adjacent_same_thread`

```
Fold CONSECUTIVE same-thread colour blocks into one (2026-08-28, from
Kent's own owl and his "quality first, then efficiency" ordering).
A stop between two blocks sewing the identical cone makes the operator
cut and re-thread the spool already on the machine. Measured on
testdata/photo/owl_kent.jpg at 100 mm, is_photographic=True: 17 blocks
over 12 spools, and two of the sixteen stops (t46 at blocks 3-4, t12 at
14-15) separate blocks in the SAME thread.
Strictly a bookkeeping merge: nothing is reordered and no stitch moves,
so stage 5's coverage/underlap plan is untouched -- which is what makes
this safe where the NON-adjacent merge (the same cone revisited with
other colours in between, t4 at blocks 0/2/7 on the same run) is not.
That one needs stage 5's `covered_by` to prove no seam moves, and is
deliberately NOT attempted here.
Default ON: the merge is a no-op wherever no two adjacent blocks share a
thread, which is every flat design measured here, so the byte-identical
goldens are unaffected by construction. False keeps the pre-2026-08-28
path reachable and tested rather than dead-by-default, the same posture
`shade_palette_bind` keeps for its own off-path.
Since 2026-10-20 it also covers the seam into the edge cap: a cap block
in the last artwork block's cone sews at the end of that block
(`stage7_sequence._cap_seam_joins`, defect 18's edge_cap route). Same
stitches, same cuts, one stop fewer; False restores the separate block.
```

## `merge_duplicate_cones`

```
One cone, one layer (defect 18, the SECOND spool-revisit mechanism).
Stage 2 quantizes to COLOURS, and two quantized colours can snap to one
physical cone: `drone_render` @ 80 mm declares 21 palette slots holding
only 17 distinct threads, with t16, t308, t119 and t101 each declared
TWICE. Nothing deduped them, so the operator was sent to the rack twice
for one spool and the second visit sewed a fragment late over finished
work — t16 at 46.1% then 40 st at 98.9%, t119 at 77.1% then 60 st at
99.4%. That is the sew-out's own tail pattern by another route.

ON folds each duplicate into the FIRST layer declaring its cone
(`stage3_segment.merge_duplicate_cone_layers`), upstream of stage 5 so
coverage, underlap and every seam derive from the merged order — the
same one-consistent-story argument `rehome_resnapped` and
`borders_last` both make. Downstream repair is NOT equivalent and is
why this exists: `_hoist_same_thread` attempts it after the fact and
correctly declines wherever the moved thread touches what it jumps
over, which on this fixture is most of them.

Pure sequencing — no physical constant enters, gate 1 untouched.
Default ON since Kent's 2026-09-01 ruling, taken with the measured
pass in hand (the same posture and the same call he made for
`borders_last`): on `drone_render` the fold buys two fewer operator
stops, removes both cone revisits, and costs LESS thread —
9486 -> 9321 stitches and 1295 -> 1237 mm of needle-up travel, over
two more but far shorter lifts. It moves whole clusters (a
duplicate's regions sew at its cone's FIRST position instead of
their own), which is why it was measured before being flipped; the
direction itself is forced, since stage 2 orders the palette
largest-area-first and a duplicate's second slot is by construction
the smaller one. Golden blast radius MEASURED at the flip: none —
every non-duplicating fixture is byte-identical and no committed
golden moves. False keeps the pre-fold order reachable and tested
rather than dead-by-default.
tests/test_duplicate_cone_layers.py pins the default and both paths.
```

## `rehome_resnapped`

```
The UPSTREAM half of the same revisit defect (2026-08-31): a region the
pipeline itself re-snapped (`revalidate_threads`) joins the layer that
DECLARES its new cone, before stage 5 plans coverage, so one spool sews
at one position and no after-the-fact disjointness proof is needed —
see `stage4_vectorize.rehome_resnapped_regions` for the three refusals
(stamped re-snaps only, declared cones only, never a step region).
Default ON: a no-op on any design with no re-snap (all four flat-lane
golden fixtures, measured 2026-08-31), so the byte-identical goldens
are unaffected. False keeps the pre-2026-08-31 split reachable and is
the lever the sequencing A/B used — same posture as the two passes
above, which remain downstream as the net for other split sources.
```

## `robust_region_colour`

```
The colour each SLIC+RAG region hands the palette. False: the plain
mean of its pixels, which a big flat region full of drawn-on inclusions
turns into a colour no pixel carries — Bridge Bar's yellow disc
reads (223, 220, 77) for pixels at (251, 235, 65), 12 ΔE00 towards
lime, because the black lettering, bird and rope inside it pull the
mean through their anti-aliased edges; the palette then rightly
picks Limelight for that point and the bound re-snap holds it
(found by #442's test run; DOCTRINE 2026-09-10). True: a robust centre
of the region's Lab pixels (`stage2_photo_segment.ROBUST_REGION_STAT`
names the statistic — the modal mean, the mean over the pixels within
DELTA_E_VISIBLE of the per-channel median, chosen over the median by
`tools/region_colour.py`'s census). Only that one point moves: the
shade-demand buckets and the tonal split keep their means. DEFAULT ON
since 2026-09-10 — built OFF that day (PR #445) and flipped in the PR
after on Kent's ruling over the flip sheet and the Bridge Bar render
(the disc `6031` Limelight → `0501` Sun; the price a synthetic stub's
+3,382 stitches / +29 trims at 12 and drone's 211 mm² orange one
spool step at the Studio's 6). False is the pre-flip engine byte for
byte. Plan: `docs/superpowers/plans/2026-09-10-region-colour.md`.
```

## `snap_region_edges`

```
Make the gradient lane's region edges follow the PIXELS rather than the
SEEDS superpixels they are built from
(`stage2_photo_segment.snap_region_edges`). Measured 2026-09-30 on
Kent's real Instagram file: 148 superpixels straddle the white icon's
edge and 7.6% of the white sews on the wrong side — the jagged ring
and bitten dot — while forced flat sews the same shapes clean. Gradient
class only. Built OFF; ON since 2026-09-30, Kent's flip on renders of his
Instagram file at 80 and 188 mm, `drone_render`, Bridge Bar and the
repro (it moves the region set on every gradient-class design, which
is why it waited on his eye and not on a green suite).
```

## `two_tone_snap`

```
Defect 58: a black-and-white logo sews four to six cones, because thin
strokes on a low-resolution source are mostly anti-alias grey. ON, a
raster `two_tone.detect` reads as two inks (achromatic, two modes, no
grey plateau) is thresholded to those two inks right after stage 1, so
no region ever sees the grey. Per IMAGE, which is why it leaves
`logo_bridge_bar.jpg`'s ringing alone where the per-region stroke rule
did not (DOCTRINE 2026-10-05). ON by default since 2026-10-11, on Kent's
approval of 2026-10-08 ("Fix the roof-line bug, then flip"):
`two_tone.keep_lines` keeps golke's white roof lines (they sewed as one
black mass) and preflight's thread grader reads the snapped raster
(`preflight._two_tone_view`; unsnapped, it blocked White under those
lines). The thread-match/resnap tests whose premise is gaulke's grey
halo, which the snap removes, measure the pre-flip engine through
`tests/conftest.py`'s PRE_FLIP. False is the pre-flip engine.
```

## `white_keyline_art_recipe`

```
`white_keyline_art_recipe` (BUILT OFF 2026-10-26, `white_keyline_art`):
the white-keyline recipe -- `silhouette_underfill`, `sew_enclosed_white`,
`enclosed_white_keyline`, `silhouette_underfill_panels`,
`outline_loop_mitre`, `silhouette_underfill_rim` -- turns ON by itself,
but only on white-keyline art: a dark host round a white field that
outlines letters (MFab's keyline round M-FAB). Kent, 2026-10-26: "Gate to
MFab art first (Recommended)" -- as a default for all art the recipe
damaged four of 20 other paired jobs (Gaulke, Tires, ProSeal, Becker).
Read on the stage-4 regions in `finish_generation`, before the recipe's
first switch acts; it holds on MFab hat and LC and on none of the other
20. ON by default since 2026-10-26, Kent's ruling, verbatim: "Gate to
MFab art first (Recommended)" -- "The recipe turns on by default only
where a dark shape carries white outlines round letters (the panels lane
already detects this). Only MFab changes now." False is the off arm.
Tests: `tests/test_white_keyline_art.py`.
```

## `strip_letterbox`

```
Strip letterbox/pillarbox bars from the upload before any ink rule
reads them. See digitizer_core/letterbox.py for the defect: a PHONE
SCREENSHOT of a logo arrives with pure-black bars filling most of the
frame, every ink rule here reads darkness as ink, and the result is a
POLARITY INVERSION -- the engine sews the GROUND in near-white thread
and leaves the logo as negative space. White thread on white cloth, an
unusable file. `photo/logo_gaulke_roofing.png` is exactly that input and
was ranked worst of fourteen by eye
(docs/artfid-eye-agreement-2026-09-11.md).

ON, verified by render 2026-09-11: both text lines legible in black,
mark solid and correctly polarised. Blast radius is one fixture -- the
other 13 tracked fixtures are byte-identical on (route, stitch count).

**DEFAULT ON since 2026-09-14** (Kent: "proceed with all of the
suggestions"). It shipped OFF on 2026-09-11, and the reason was never
caution about the fix: turning it on changes
`photo/logo_gaulke_roofing.png`, and that fixture's PATHOLOGY was
LOAD-BEARING for 13 tests (the entry said 11; the suite had grown).
Flipping it was therefore not a one-line change but a fixture job, and
the rule for that job is DOCTRINE's: re-point each test at something
that still carries the property it is testing, NEVER at whatever the
engine now happens to emit.

What that came to, test by test:

 * `test_preflight.test_a_full_bleed_design_does_not_report_its_own_
   border` KEPT this fixture, and now for a better reason. It used to
   be the corpus's only full-bleed design by ACCIDENT of the bars being
   read as ink; cropped, the white band runs edge to edge on its own
   (`bg_mask` 0.000%, BACKGROUND_ABSENT), which the test now asserts
   rather than assumes. Its bound also moved off a single drifting
   number onto the defect's own signature -- a permanent rim strip
   means non-zero TOTAL uncovered area, and that reads 0.0.
 * `test_enclosed_by_garment` moved to `testdata/black_ground_holes.png`
   (`tools/make_black_ground_fixture.py`), which is letterbox-PROOF by
   construction: its ground is black on all four sides, and a uniform
   border on both axes is a margin this module never strips.
 * The `test_resnap_mask_matches_grader` group moved to
   `photo/logo_bridge_bar.jpg`, and the reason is the one thing a
   spool-ID re-pin would have HIDDEN. On the cropped gaulke the
   phenomenon does not move, it INVERTS: the shipped engine used to
   pick `3971 Silver` here and the flag declined it; after the crop the
   flag CAUSES a Silver pick. Renaming the pinned shape id would have
   made CI green while asserting the opposite of what the guard
   protects. bridge_bar still shows the real thing (OFF picks Silver on
   `S60139fba`, ON moves it to `0108`) and carries no bars, so it
   cannot lose the property to this change.

KNOWN, and NOT fixed by this flip: with the bars gone the band's own
soft shadow edges (a ~12 px 235->216 gradient down each side, measured)
drop border agreement to 0.693, so background detection reports
BACKGROUND_ABSENT and the white ground is still sewn. That is stage 1's
border flood, not letterboxing -- and `preflight.GROUND_SEWN` now
REPORTS it at block severity (79.9% of the stitched area here), which
is what stops the file at the Studio's download confirm.

`strip_letterbox=False` remains the pre-2026-09-14 engine, byte for
byte, and every byte-identical claim in this repo's history was
measured there.
```

## `blend_fallback_underlay`

```
Underlay under a gradient-class design's ordinary fills. Built OFF
2026-10-05; ON since 2026-10-07 by Kent's ruling, because OFF a
gradient-class design sewed every fill with no underlay at all. Measured
when built (six real gradient logos, 80 mm): bare fills 33/33 -> 5/33
for +1.7% stitches, trims 423 -> 421 (Fremont pays +6). On the knit
presets the style is `edge_run`, so a fill gains only its perimeter
walk; the interior pass is a separate gate-1 item (corpus law 26) and
is not changed here. `docs/renders/blend-fallback-underlay-2026-10-05/`.
Stage 7 routes every auto-tier fill of a
design classed "gradient" through `stage6_blend.blend_fill`, which
sewed `underlay_style="none"` on both of its paths and was never handed
the style stage 7 resolves for every other fill tier (the fabric
preset's `fill_underlay`, `underlay_style`, the per-shape override). So
on such a design no fill had any underlay, not even the edge run, and
the three controls did nothing: 10 of 14 real-art fixtures, 100% of
their fill area (`docs/underlay-research-2026-10-05.md` §2).
True: the FALLBACK path — a region that is not a ramp and sews as
full-density tatami, which is nearly every real region — sews the
resolved style. The ramp-band path stays bare on purpose: Wilcom and
mySewnet both say no underlay under a variable-density blend (§4).
No constant is added; the style and its spacings are the ones the flat
lane already sews. False is byte-identical to the engine before it.
`tests/test_blend_fallback_underlay.py`.
```

## Notes the test bundle (`tests/conftest.py` `PRE_FLIP`) carried, removed with the pins

### `strip_letterbox`

```
`strip_letterbox` joined the flipped set 2026-09-14, and is in PRE_FLIP for
exactly the reason stated above: a test pricing one flag alone must measure
against the engine its measurement was made on. Every arm in the resnap and
thread-match files was measured on `photo/logo_gaulke_roofing.png` WITH its
letterbox bars — 16.1 px/mm, the 247-vs-54 px footprint, the 63.6 dE00
Silver — and cropping the bars changes the raster those numbers describe.

This is NOT a way of dodging the re-point work. The distinction that
settles it: those tests are about the COLOUR flags, and `strip_letterbox`
is orthogonal to every one of them, so pinning it here keeps each test
measuring the thing it is named for, on the pixels it measured. The tests
that are genuinely ABOUT the crop (`test_letterbox`, the full-bleed guard,
`test_enclosed_by_garment`) do not use PRE_FLIP and were re-pointed
properly instead.

Measured before choosing this: no single fixture in the corpus reproduces
gaulke's uncropped severity on BOTH axes the resnap premise asserts.
`photo/logo_bridge_bar.jpg` has the footprint inflation (raw 229 px vs
grader 39, ratio 5.87 against the test's `> 3`) but not the bimodality
(26 dark pixels against `> 50`, because it decodes at 4.0 px/mm);
`photo/screenshot_phone_ui_golke.jpg` has the bimodality (92 dark / 102
light at 12.75 px/mm) but not the ratio (2.20). Splitting one premise
across two fixtures to keep a number green would have been the
fit-to-output move this repo's doctrine warns about.
```

### `snap_region_edges`

```
`snap_region_edges` joined the flipped set 2026-09-30 (Kent's flip on
renders of his Instagram icon, drone, Bridge Bar and the repro), for the
reason every entry above gives. ON, a gradient-lane region's edge follows
the pixels instead of the SEEDS superpixels, which removes exactly the
slivers and halo fragments the colour files use as their PREMISE -- the
resnap's Silver-on-near-black shape, the drifted sliver, the repeated cone
-- so an arm measured before that day was measured with them present.
Measured at the flip: left ON, 26 tests across 13 files moved, and in the
files that read this dict every one was a premise assert ("fixture drift",
"should be there to lose"), not the flag under test getting worse. The
test that is ABOUT the snap is `tests/test_snap_region_edges.py`.
```

### `two_tone_snap`

```
`two_tone_snap` joined the flipped set 2026-10-11 (defect 58, Kent's
approval 2026-10-08), for the reason every entry above gives. ON, a
black-and-white raster is thresholded to its two inks before any region
exists, so gaulke's grey halo -- the Silver `3971` escape, the 0.58 mm²
shard, the enclosed `4174` that the resnap and thread-match files take as
their PREMISE -- is never segmented at all. The test that is ABOUT the snap
is `tests/test_two_tone.py`.
```

### `dissolve_phantom_blends`

```
The photo lane's phantom-blend dissolve (defect 27; Kent banked it OFF
2026-09-04 and flipped it ON 2026-10-20, MASTER_SCOPE item 46, on PR
#1003's pricing): a merged label that is mostly boundary and a blend of its
two sides folds into the nearer side, so a JPEG's halo cones are never
planned. False is the pre-flip engine, with every halo shard the colour
files take as their premise. The tests ABOUT it are
`tests/test_phantom_blend_photo.py`.
```

