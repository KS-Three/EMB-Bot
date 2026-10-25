# Silhouette under-fill: the tier census, and the construction it found (2026-10-24)

**Question (L9).** The cross-underlay lane (PR #1033) saw MFab's black band and
Becker's ring sewn as split satin by us and "filled" by the pro, and called it a
TIER decision: which stitch type a shape gets. This measures that on every paired
job, finds it false as a per-shape rule, and builds what the pro actually does,
behind `cfg.silhouette_underfill`, **default OFF** (Kent 2026-10-24: "Build
under-fill, OFF").

## 1. The tier census: no per-shape rule

`tools/tier_census.py` reads every shape of our segmentation against both stitch
files with ONE reader (ours written to DST and read back; shapes mapped into the
pro's frame by `pairframe.register_pair`). Per shape it chains the needle-down
stitches inside it into **crosses** (consecutive stitches on one line), keeps the
**dense** ones (the next cross comes back anti-parallel within 0.9 mm: top
stitching, not underlay or travel), and asks how much of their length lies at
**one angle** (+/- 4 deg). A fill sews one angle; satin turns with its column.
FILL at >= 0.70 at one angle, or >= 0.50 with >= 0.35 of it landing oblique on
the edge (a fill under a satin border); otherwise SATIN, or SPLIT at >= 1.3
stitches per cross; BAR where one angle runs square across a bar (the case
satin and fill cannot be told apart).

**The reader is checked on our side first**, where the plan's run kinds are the
truth: non-lettering 198/213 shapes, kappa 0.827 (all shapes 384/427, 0.668; the
misses are short straight split-satin pieces reading as fill).

**Result, 21 paired jobs, 191 non-lettering shapes** that both files sew densely:

| | agree | kappa |
|---|---|---|
| ours today vs the pro | 121 / 191 | **0.170** |
| best width/area rule ("fill if ribbon width > 2.5 mm and area > 400 mm2") | 123 / 191 | 0.198 |

The best rule moves ONE shape, MFab's black band, on the hat and the LC, and its
threshold sits in a 0.4 mm gap: Becker's ring (2.48 mm, 1,195 mm2) the pro
SATINS, MFab's band (2.86-3.11 mm) he fills. Against any width rule: he satins
Tires' 4.3 mm / 925 mm2 shape and Gaulke's 5.8 mm one (we fill both).
Stroke (2 x the median medial-axis distance) and the inscribed circle do no
better (0.198, 0.179). **Wide and big does not predict his fill.**

Caveats: Google Drive dropped files mid-run, so Bridge comes from the first of
two passes; Machine hat / LC register poorly (IoU 0.43-0.46) and their rows are
weak.

## 2. What he does: read per colour block

The same 0.1 mm thread raster, one pro colour block at a time, over three
pieces of our ring shape: the **ring**, its **holes**, and the **silhouette**
(the ring's outline, holes closed).

| job | ring | his block over ring / holes / silhouette | reading |
|---|---|---|---|
| MFab hat | black band | black: **1.00 / 0.82 / 0.88** | one black fill of the outline; white keyline (block 1) on top |
| MFab LC | black band | black: **1.00 / 0.83 / 0.88** | the same |
| Becker beanie | black ring round white letters | letter colour (blocks 2+4): **0.75 / 1.01 / 0.91** | the letters' fill runs under the ring; the ring is satin on top (blocks 3/5) |
| Hotel Fremont hat | ground round its lettering | ground: 0.91 / - / **0.92** | the ground runs under the letters |
| Hotel Fremont patch | the same | ground: 0.90 / - / **0.90** | the same |
| Precision Drone | ground (a gradient render) | best block 0.39 / - / 0.51 | **no** under-fill; the row against |

So the construction: **a ring whose holes hold other shapes gets its outline
(holes closed) filled once, underneath, in the colour covering most of that
outline (the ring counting for its own colour); the ring and its contents sew on
top.** The colour choice is what separates MFab and Fremont (the ring's colour
covers most: the ring itself becomes the fill, and inner shapes of its colour
merge into it) from Becker (958 mm2 of letters beat a 730 mm2 ring: the largest
letter sews the outline, the other letters merge, the ring sews as it did).

## 3. The build (`cfg.silhouette_underfill`, OFF)

`digitizer_core/silhouette_underfill.py`, one pass in `plan_stitches` right after
`fill_inside_satin_border`, on copies:

- **Ring**: a sewn, auto-tier, non-lettering shape with holes, >= 200 mm2, whose
  holes are at least half covered by sewn shapes lying inside its outline
  (>= 0.9 inside, <= 0.25 on the ring).
- **Host**: the ring, or the largest auto-tier inner shape of the winning colour.
  It gets the fill tier and `meta["silhouette_underfill"]` = the outline, which
  stage 5 reads through the ground-under path bean letters use: the host's
  footprint stays its artwork, so nothing sewn later is clipped by the outline,
  and the holes it covers are not held open.
- **Merged**: auto-tier inner shapes of the host's colour leave the plan. A shape
  with a review tier is never merged and never the host.
- **Layers**: the host's thread layer moves ahead of the ring's and every inner
  colour's.
- **Unsewn stays unsewn**: the outline is cut back off every shape left as garment
  (enclosed background, a review `stitched: false`).

OFF never calls the pass, and the stage-5 hunk reads a key nothing else sets:
`tests/test_silhouette_underfill.py` pins the OFF md5 against origin/main
d184fd68 on two synthetic designs.

## 4. Proof: OFF | ON | pro

Each job digitized once through the Studio's request with `sew_enclosed_white`
and `enclosed_white_keyline` ON (the two flags pending a flip), then
`plan_stitches` with the under-fill OFF and ON (`tools/silhouette_underfill_proof.py`).
Both of ours and the pro's DST go through the same block reader; MFab uses the
committed fixtures `testdata/art/logo_mfab_{hat,lc}.png` (the Drive copy the
census read was unmounted by then).

| job | arm | first fill block: ring / holes | stitches | trims | colour changes | our travel / exposed (mm) |
|---|---|---|---|---|---|---|
| MFab hat | OFF | 1.00 / 0.85 | 18,916 | 81 | 1 | 721 / 17.8 |
| | **ON** | **1.00 / 1.00** | **17,540** | **37** | 2 | **191 / 6.9** |
| | pro | 1.00 / 0.82 | 17,568 | 19 | 4 | - |
| MFab LC | OFF | 0.25 / 0.62 (white first) | 16,542 | 72 | 1 | 404 / 18.5 |
| | **ON** | **1.00 / 1.00** | 16,658 | **44** | 2 | **49 / 8.6** |
| | pro | 1.00 / 0.83 | 15,786 | 20 | 4 | - |
| Becker beanie | OFF | ring 0.19 / holes 0.96 (letters) | 11,501 | 21 | 2 | 498 / 74.6 |
| | **ON** | **1.00 / 1.00** | 13,726 | 20 | 2 | 488 / 54.1 |
| | pro (letter blocks) | 0.75 / 1.01 | 11,411 | 11 | 5 | - |

"Exposed" travel is needle-down travel no later stitch covers. Renders:
`docs/renders/silhouette-underfill-2026-10-24/` (art | OFF | ON | pro, 10 px/mm,
each side in its own frame; `mfab_lc_lower_line_off_on.png` at 20 px/mm), with
each job's `stats.json`.

**Read:**

- **MFab**: ON is the pro's construction: one black body, the white keyline on
  top. Trims 81 -> 37 (hat) and 72 -> 44 (LC) against his 19-20. Stitches land
  on his on the hat (17,540 vs 17,568). The third block is the bean edge cap on
  the black fill's now-open outer edge (1,094-1,190 st): the pro sews a satin
  border there, which `border_by_size` does not add because the host carries the
  fill tier.
- **Becker**: the white fill runs under the ring as his does, and the render barely
  moves (the ring covers it). It costs +2,225 stitches: our under-fill runs about
  2.8 st/mm2 where his letter blocks run about 2.1. That is fill density, a
  gate-1 question, not this flag's.

## 5. Interactions

- **`sew_enclosed_white`**: Becker's letters are sewn only with it, so OFF,
  Becker's ring holds nothing sewn and the pass leaves Becker alone (its satin
  ring untouched). MFab without it: the band's holes are still held by the black
  letters, so the band fills its outline **cut back off the unsewn white
  keyline**, which stays garment.
- **`enclosed_white_keyline`** (#1059) sews the white band as loops whose
  crosses run "on under the thread sewn after it". It puts white first, black on
  top, so the visible white is the art's width. **ON reverses that order: white goes
  ON TOP of black.** That is the pro's order (his keyline block follows his
  black), and on MFab LC it lowers exposed travel 18.5 -> 8.6 mm. But it is the
  reverse of the order #1059 built, and which order ships is Kent's flip.
- **`fill_inside_satin_border`** (OFF) re-tiers bodies inside a satin ring to
  fill BEFORE this pass. Both ON: the bodies are fills either way, and the pass
  still hosts and merges by colour. Its own ring test (`is_satin_candidate` on
  the ring) does not read this flag.
- **`border_by_size`** reads only auto-tier shapes, so a host (fill tier) gets no
  size border: MFab's outer edge is ringed by the bean edge cap, not his satin.
- **Reach at today's defaults** (the census cache, `stitched` as main sews it):
  rings on MFab hat/LC, Fremont hat/patch, Bridge hat/LC and the Drone, each
  hosted by the ring itself. Bridge's pro file was unreachable (Drive
  unmounted), so Bridge is unmeasured; the Drone is the row against.

## 6. What is not here

- No satin border on the under-fill's outer edge (his MFab file has one).
- Becker's under-fill density (gate 1).
- A Studio preview check of Fremont, Bridge and the Drone under ON. They are in
  reach and were not rendered here.
