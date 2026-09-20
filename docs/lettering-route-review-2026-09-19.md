# Should lettering stay trace-as-shape? — a review with evidence (2026-09-19)

Kent asked, the day after ruling it, whether trace-as-shape is the right route
for auto-digitized lettering, and for a review rather than a restatement. This
is that review. Three measurements were made for it; everything else is read
from the code and from the professional's files already in the repo.

**Verdict in one paragraph.** Trace-as-shape is the right *shape source*, and
the only one that keeps the customer's font on real logos: a library-font match
is not available for them (§2). But "trace-as-shape" as built is not enough,
because crispness is decided *after* the shape, by how a letter is turned into
columns — and there the traced route sews the same letterforms with ten times
the trims, near-random cross angles, bloated strokes with halo hooks, and at
large sizes a collapse to tatami (§3), while the font engine sews them as clean
authored columns and the professional sews them as wide satin at one angle
(§4). The recommendation is therefore not "trace *or* text" but **trace the
shape, then construct the letter the way the font engine and the pro do** (§5).

## 1. What the two routes actually are

- **Trace-as-shape.** Each letter is a raster region like any other: stage 4
  polygon → stage 5 pull-compensation growth of the whole polygon (round join,
  *before* decomposition) → stage 6 raster skeleton → `_prune_spurs` →
  `_merge_through_junctions` → satin columns, each with its own smoothed
  perpendicular unless the house angle (`set_lettering_house_angle`) keys the
  word. No stitch rule reads `text_candidate`; it is review metadata
  (`digitizer_service/app.py:659`). Lettering-specific rules that do exist:
  the house angle, hairline stretches as bean runs, `LETTERING_TOO_SMALL`,
  regularization for the rescued door only, `lettering_min_column_mm` (OFF).
- **Convert-to-text.** The Studio hides the traced members (`stitched:false`,
  reversible) and adds a text element seeded from the cluster's bbox: OCR word
  when the cluster's minimum Tesseract confidence clears 55, size from bbox
  height, rotation 0, **font `null`** — the user picks one. A font here is
  `.embf` data: per glyph, hand-digitized satin columns (`railA`/`railB`/
  `rungs`) and construction runs, no outline. The typed glyph then gets the
  engine's lettering rules from `satinfont.js`/`satinplay.js`: underlay by
  measured cap height, pull compensation on the rails with a counter guard,
  split satin above 5 mm, bean runs for hairlines, one Euler walk per
  component (trims only between glyphs). None of these reach a traced glyph.
- **Outline (TrueType) fonts.** `src/fonts.js` can lay out 137 Google fonts
  via opentype.js, but it is deliberately excluded from the Studio
  (`app/src/lib/emb.js:19-27`), there is no font-file upload, and its output
  is ColorRegions for `buildQualityDesign` — the *trace lane*. A customer's own
  TTF would give exact vector outlines and then the same construction problem.

## 2. Is a library-font match available for real logos? No.

`digitizer/tools/`-free measurement (scripts in the scratchpad of the session,
method recorded here so it can be redone): decode all 85 shipped `.embf`
fonts (`src/fontbin.js` in Node), build each glyph's filled shape as the union
of its columns' ribbon polygons (rail A, then rail B reversed — the rails are
corresponded through the rungs, so zipping them point by point twists), and
compare every letter the digitizer tagged as a text-cluster member on the nine
`REAL_ART` logos (174 letters, Studio defaults) against every A-Za-z0-9 glyph
(3,802 with a usable shape) by IoU of bbox-normalised 64×64 masks, best over
the library, y-flip allowed. IoU of normalised masks is the question Kent's
constraint asks: *does the letter look the same?*

| | share of the 174 traced letters |
|---|---|
| best IoU ≥ 0.95 | 13 (7%) |
| best IoU ≥ 0.90 | 19 (11%) |
| best IoU ≥ 0.80 | 62 (36%) |
| median best IoU | 0.753 |

Per logo, median best IoU: becker 0.775 (none ≥ 0.90), enthusiast 0.746
(12%), fremont 0.700 (none), gaulke 0.831 (15%), drone 0.664 (9%), screenshot
0.807 (20%), bridge and golden_tee 0.27 on three letters each.

**Two calibrations say what those numbers mean.** The same letter in a
*different* font scores a median best IoU of **0.928** (p90 1.000, 53% ≥ 0.90):
a 0.9 is what "same letter, wrong font" looks like, so the metric cannot even
tell fonts apart, let alone identify one. And the 19 letters at or above 0.90
are almost all `I`/`l` — a bar matches any bar — plus one `D`. A glyph sent
through a coarse raster round trip scores 0.946 against itself, so a true hit
would sit above 0.94: 13 letters do, and they are the `I`s. **Font
identification against this library is dead on arrival for logos**, and any
"closest font" offer would change the appearance Kent's constraint protects.

## 3. Same letterforms, two constructions

The decisive experiment removes the shape source from the question: take a
library font's own letterforms, sew them once through the font engine (typed)
and once by rasterising the identical shapes and digitizing them as artwork
(traced). `manga_impact`, "MARINE", Studio defaults (`max_colors=6`,
`left_chest`), raster at 12 px/mm with a 4× anti-alias downscale — a good
upload. Renders: `docs/renders/lettering-route-2026-09-19/`.

| | typed, 80 mm | traced, 80 mm | typed, 127 mm | traced, 127 mm |
|---|---|---|---|---|
| stitches | 1,782 | 2,461 | 3,115 | 9,645 |
| trims | 3 | **41** | 4 | 30 |
| columns / shapes | 44 columns | 10 regions: 6 letters + 4 halo pieces | 44 columns | 15 regions |
| letters sewn as | satin | 7 satin, 1 fill | satin (split) | **1 satin, 14 fill** |
| cross-angle concentration (`pro_angles.py`, 1.0 = one angle) | 0.63 | **0.23** (20 coherent runs of 46) | 0.59 | **0.10** |

What the renders show at 80 mm: the typed letters are clean columns with sharp
diagonal cuts; the traced letters are heavier, their edges lumpy, and every
letter carries hook-shaped bean runs around it — the anti-alias halo quantised
to its own thin region and rescued as line art (four extra regions). At 127 mm
the traced route's strokes pass the 5.0 mm satin cap and 14 of 15 letters fall
to tatami: flat, heavy, three times the stitches, and not what a professional
does (the pro's Becker files carry 7-23% of columns over 5 mm and satin every
MARINE letter; the browser lettering engine splits, never fills — Kent's
2026-09-11 ruling). The traced route at 80 mm scatters its cross angles across
0-180° at a concentration of 0.23, the class the 2026-08-26 letterform study
called "statistically indistinguishable from random" on Becker (pro 6/7 letters
within ±20° of one angle).

None of this is the tracing. The sub-pixel edge read that landed on 2026-09-18
puts the polygon on the letter's edge; the raster here is 12 px/mm and the
polygon is not the problem. It is what stage 5 and stage 6 do with a polygon
they do not know is a letter.

## 4. What the professional does (already measured in this repo)

`docs/kent-review-2026-09-03.md`, `.claude/memory/letterform-fidelity-2026-08-26.md`,
`.claude/memory/pro-files-refute-scale-limit-2026-09-03.md`: the pro's Becker
file satins all six MARINE letters (ours tatami five at 100 mm), at one
near-horizontal cross (modal 2°, 6 of 7 letter runs within ±20°; ours 9 of 43),
turning an E's arms into short wide columns; the pro's Fremont file widens
0.24-0.56 mm strokes to 0.82-0.90 mm columns so THE, EST 1895 and the tagline
sew legibly at 92.5 mm where we sew beans. The pro traces the customer's
letterforms by hand and *constructs* them as columns; nobody retypes a logo in
a stock font.

## 5. Recommendation

1. **Keep trace-as-shape as the shape source.** It is the only route that
   keeps the customer's font on real logos, and the shape itself is now
   accurate. Do not build font identification (§2); keep Convert-to-text as
   the manual escape hatch it already is, for a customer who *wants* a plain
   tagline retyped in a library face.
2. **Give a traced letter the font engine's construction.** The gap in §3 is
   exactly the list of rules a typed glyph gets and a traced one does not.
   In the order they buy the most, each as a measured flag:
   - **Split, never fill, for lettering over the cap** — the browser engine's
     rule, applied on the traced path when the region is a text-cluster
     member: a wide letter stroke is a split-satin column, not tatami (the
     127 mm collapse; `wide_columns` raised the cap and let the emitter
     self-cross, which is why the construction has to be split-satin, not a
     higher cap).
   - **Pull compensation on the rails after decomposition** (`satin_rail_comp`
     exists, OFF; the skeleton read off the artwork, not the grown polygon) —
     the corner rounding and sealed slots of mechanism #1.
   - **A cap-arm classifier for `_prune_spurs`** — the dropped N foot,
     mechanism #2.
   - **One house angle per word, held** — built (`set_lettering_house_angle`);
     verify it fires on these fixtures, since it groups by `_lettering_groups`
     and fails open.
   - **No halo hooks** — the anti-alias halo of a letter must not become a
     rescued line-art region; the 80 mm run made four of them at Studio
     defaults. This is a phantom-blend / thin-ink interaction, measurable on
     this fixture.
3. **Bring-your-own-font-file is a later, real option** for customers who have
   their brand TTF: exact outlines instead of a trace. It pays off only after
   item 2, because its letters would go through the same construction.
4. **A hybrid worth one spike later, not now:** use the OCR character and a
   library glyph's *column topology* as a template to decompose the traced
   letter (shape-context alignment already exists in `shapecontext.py`). It
   could give the pro's stroke order on the customer's shape, but a template
   whose stroke structure differs from the customer's letter (single- vs
   double-storey `a`) would be worse than the raster skeleton.

*(measured 2026-09-19: renders and the traced input under
`docs/renders/lettering-route-2026-09-19/`; the font-engine DSTs were made with
`tools/run-lettering.mjs`, the angle readings with
`tools/letterform_fidelity/pro_angles.py`)*
