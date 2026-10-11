# SVG import risk gate — 2026-10-11

The risk gate the SVG import plan set and nobody ran
(`docs/superpowers/plans/2026-07-27-svg-import-and-shapes.md`, Task 6):
real vector art through `EMB.parseSVG` → `EMB.buildQualityDesign`, with a
picture. Measured only. No engine, Studio or service code changed.

## Verdict (two minutes)

**Wiring `parseSVG` as it stands would be a step BACKWARD, so this is about a
month of work, not a week.** Today the Studio already takes an SVG upload: the
browser paints it, then it is traced like any image (`rasterize.js`,
`vector: true`). Because the browser paints first, today's path gets paint
order, hidden layers, colour syntax and strokes right. `parseSVG` gets all
five wrong (table below). Its one real win is the edge. On the one-colour
banner logo it is off by 0.1–0.2 % of the painted area, against 3.4 % / 2.0 %
for today's 480-px offline trace.

**The first blocker is paint order.** A layered logo needs every shape cut
by the shapes painted above it, and the JS engine has no polygon boolean
operations. Until that exists, any logo with a dark shape under a light one
sews wrong. The drawn badge loses its sun and its wave under the navy disc:
**27.7 %** of its area gets the wrong top thread. The backing rectangle is
sewn as well, which comes to **54 %** of its stitches.

Rough price, to sew at least as well as today: hidden elements, colour
syntax and honest warnings about 1–2 days (S). Paint order and overlap
resolution about a week (L in JS; M in Python, which already has shapely).
Strokes 2 days in Python, about a week in JS. Studio wiring plus e2e about a
week. **Fill-only logos with no layering could ship in about a week**, but
that is a narrower product than what customers can upload today.

## Gap table

Each row has a small SVG drawn for it, under
`docs/renders/svg-import-gate-2026-10-11/svg/`, and a picture: what a browser
paints, then what the importer handed over in sew order, then the stitches.
The four numbers are pixel comparisons at 600 px against the browser's own
paint of the same file (method below), as a % of the painted area. They come
from `results.json`. Arm `image` is the Studio's image branch (light-to-dark
sort). Arm `drawn` is `darkOnTop: false`. Arm `today` is what the Studio does
now: rasterize at 480 px, then trace with 4 colours and the background removed.

| # | Gap | Reproduces? | Evidence | Severity for a customer | Fix |
|---|---|---|---|---|---|
| 1 | **Paint order lost.** All shapes of one colour merge into one region, and regions are then sorted light-to-dark. | **Yes** | `gap-1-paint-order`: a cream disc on a navy plate, with a navy dot on the disc. The disc (2,625 stitches) is sewn first and then completely buried under the plate: wrong top thread **26.8 %**. The `drawn` arm still buries the dot (**4.2 %**). Badge: **27.7 %** / **24.3 %**. Today: 0.5 % / 1.0 %. | **High.** A wrong picture on any layered logo. | **L** in JS (needs polygon difference). **M** in Python (shapely). |
| 2 | **Overlaps not resolved; background rect sewn.** | **Yes** | `vector_logo` (the e2e fixture): the white artboard rectangle is **4,906 of 6,918** stitches (71 %). `gap-2`: 8,052 of 12,062 white. Badge: 8,052 of 14,800, with **52.5 %** of its area stitched twice or more; today's lane sews the badge in 6,910. | **High.** Twice the stitches, a stiff "bulletproof" patch, and thread buried under thread. | Overlap: same as row 1. Background drop: **S** once row 1 exists (mirror today's remove-background toggle). |
| 3 | **Hidden elements stitched.** | **Yes, 5 of 5 ways** | `gap-3-hidden`: `display="none"`, `style="display:none"`, `visibility="hidden"`, `opacity="0"` and `fill-opacity="0"` are all sewn in their own thread. Stitched where nothing is painted: **484.7 %** of the painted area. In the badge, a hidden Inkscape layer ("Old version") sews 1,714 green stitches: behind the bars in `image`, on top of them in `drawn`. No warning. | **Medium-high.** Hidden layers are routine in Inkscape and Illustrator files, so old versions get sewn. | **S** |
| 4 | **Colour syntax.** `rgb(100%,0%,0%)` is misread, and others are skipped. | **Yes** | `gap-4-colour-syntax`, 8 legal CSS colours: `rgb(100%,0%,0%)` reads as **#640000** (dark maroon, not red). `hsl()`, `crimson`, `#rrggbbaa`, `currentColor` and `DarkGreen` are **skipped silently**: 62.5 % of the art is not stitched. Only `rgb(0 128 128)` and `#f0f` come through right. Today: all 8 sewn, quantized to the default 4 threads (the 12.5 % wrong is that merge, not a parse). | **Medium.** Illustrator and Inkscape export hex. `currentColor` is the norm in web icon sets. | **S** (percent and hsl parsing, the CSS named-colour table, `color` inheritance) |
| 5 | **Silent skips.** | **Yes** | `gap-5-silent-skips`: a stroked ring, a stroked polyline, the stroke round a filled rectangle, and an embedded `<image>` are all dropped with **no warning**. 52.9 % of the art is missing. The stroke warning only fires when *nothing* in the file has a fill. **The Studio's own favicon** loses its whole "M" mark (a stroke) and sews an 80 mm solid purple tile, again with no warning. | **High.** Outlines, rules and line icons are strokes. The customer gets a confident, wrong result. | Warnings **S**. Stroke support **M** in Python (`shapely` `buffer`), **L** in JS. |
| 6 | **Crash in `parseSVG`?** | **No** | The 9 SVGs in the repo plus 10 malformed inputs threw nothing: empty, non-SVG, `M`-only path, NaN size, unclosed tags, truncated path, a self-referencing `<use>`, a DOCTYPE entity, and `>` inside an attribute. The largest file (328 KB) parsed in 50 ms. A non-SVG input returns zero regions and only the "assuming 100x100" warning, which is misleading but harmless. | — | none needed |

**What works:** a one-colour logo with counters. `real-3-banner-two-words`
(an arched banner outline plus two block-letter words, 11 counters, written
the way Illustrator exports it, with `<style>` classes and compound paths)
imports with every counter. Against the browser it scores 0 % wrong, 0.1 %
extra and 0.2 % missing. It also survives Illustrator's prologue: XML
declaration, generator comment, `enable-background`, `xml:space`.

## Pictures

All under `docs/renders/svg-import-gate-2026-10-11/`. Each JPEG is three
panels with a caption: sew order, stitches per thread, warnings and the four
numbers.

- `real-4-badge-multicolour.jpg`: the headline. The navy disc covers the sun and
  the wave, and the hidden green layer is sewn. Beside it,
  `real-4-badge-multicolour-today.jpg` shows today's lane getting the stack
  right.
- `favicon.jpg`: the Studio's own icon loses its mark without a word.
- `gap-1-paint-order.jpg` and `-drawn.jpg`: the paint-order loss, in both sort
  orders.
- `gap-2-background-and-overlap.jpg`, `vector_logo.jpg`: the background
  rectangle sewn.
- `gap-3-hidden.jpg`, `gap-4-colour-syntax.jpg`, `gap-5-silent-skips.jpg`.
- `real-3-banner-two-words.jpg` and `-today.jpg`: the success case. Exact edges
  against a 480-px trace.
- `*-today.jpg`: today's lane for each file.

## The service side: what an auto chooser would need from an SVG

`POST /digitize-manual` takes millimetre polygons with holes and a required
`technique` per shape: `satin`, `fill` or `run`, with no `auto`. It rejects
self-intersecting polygons with a 400. A chooser for SVG input would need three
things from each element. **First, fill or stroke.** A stroke hands over its
centreline and its width (`stroke-width` times the transform's scale) for free:
satin along the path when the width falls in the satin band, run or bean
below about 1 mm. That is information a trace never has. **Second, for a
fill, a width measured at the final size.** The Python side already has the
reader: `stage6_satin.classify_ribbon(poly, max_width_mm)` takes a shapely
polygon in mm and returns ribbon width, aspect and the distance-transform
regularity gates the auto pipeline uses. It has to run after the design is
scaled to its target width, because the same shape is satin at 50 mm and fill
at 150 mm. **Third, polygons that are already clean.** Paint order must be
resolved first (row 1). Overlapping or self-intersecting compound paths (font
outlines often have them) need a `make_valid` / union, or the endpoint refuses
them. A non-uniform transform scale makes a stroke's width vary along its
length; that should be warned, not guessed. Nothing here was built.

## Two things found on the way (not import bugs)

1. **Today's offline lane drops a pure-black mark on transparency.**
   `knockoutBackground` (`src/quantize.js`) samples the corner pixel's RGB and
   ignores its alpha. A transparent corner reads as (0,0,0) from a canvas, so
   with "remove background" on (the default) every near-black opaque pixel is
   knocked out. This was measured directly. A 69 px black square on a
   transparent 480×137 canvas leaves an empty palette for #000000 and #141414,
   while #231F20 and red survive. `gap-3-hidden` has no `-today.jpg` for this
   reason: today's lane stitched nothing. This affects the Studio's JS image
   lane, not the service path. Not chased further.
2. **A block "T" sews as satin and loses its left arm in BOTH lanes**
   (`zoom-banner-T-parsesvg.jpg`, `zoom-banner-T-today.jpg`; the "S" also
   breaks up in the traced lane). This is the engine's satin walk on a branched
   glyph, not the importer. Not chased.

## Method and limits

- Harness: `node tools/svg-import-gate.mjs --playwright <path to playwright>`.
  Without arguments it runs the set above. It builds exactly the Studio's
  image-branch options (`app/src/lib/generate.js`: left_chest, its fabric,
  `satinMaxWidthMm` 3, underlay, `fillColumns`), with `targetWidthMm` 80 so
  every file sews at the same size. Re-run on 2026-10-11, the output was
  identical.
- The four numbers compare the importer's polygons, stacked in sew order,
  against Chromium's paint of the same SVG in the same frame (600 px wide,
  alpha > 128, colour distance > 60). "Top thread" ignores gaps between
  stitch rows, so the numbers measure order and coverage, not density.
  Anti-aliased edges set a noise floor of about 0.1–0.3 % (vector_logo 0.2 %).
- In the `today` arm, "missing" includes the background the lane removes on
  purpose (vector_logo 67.8 %, gap-2 62.6 %, badge 56.2 %). There that is the
  right answer, not a defect.
- The `today` arm is the Studio's **offline JS** lane at 480 px. With the
  digitizer service up, an SVG upload is rasterized and sent to Python
  instead. That path was not run here, and its edges will be closer than
  480 px.
- Real logos: the e2e fixture and the favicon are the only real SVGs in the
  repo. The other two "real" files were drawn for this gate, and no client
  art was added. Becker's layout was mirrored, not its artwork.
- Nothing was sewn.
