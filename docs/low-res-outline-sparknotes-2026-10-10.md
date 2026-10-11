# Low-res outlines — sparknotes for 2026-10-11

One page. Everything here was measured or read on 2026-10-10; the long
versions are linked at the bottom. Nothing is committed, nothing in
`digitizer/`, `src/` or `app/` was changed.

## The question

Would a photo-to-SVG converter in front of the digitizer have given better
outlines, and why did we never use one?

## The answer in four lines

1. **Off-the-shelf tracers: no.** vtracer 0.6.15 and 1.0.0a4, nine settings
   between them, never beat stage 4 by more than 0.02 mm and usually lose.
2. **But the idea behind the question is right.** Low-res outlines are bad
   because stage 4 is handed a hard, stair-stepped mask — not because the
   pixels are too few. Reading the source's soft edge directly is about
   **three times closer** at Becker's resolution.
3. **That fix is ours to build, and small.** It is a marching-squares contour
   on the alpha channel. scikit-image is already a dependency.
4. **A real vector file is still the only way past the pixels.** The SVG
   parser exists, has 41 tests, and nothing calls it.

## The numbers worth remembering

Median distance from the true edge, mm. Thread is 0.4 mm wide.

| Source | Stage 4 today | Best tracer | Coverage read (new) |
|---|---|---|---|
| Alpha-only art, 1.8 px/mm (Becker's class) | 0.09–0.12 | 0.09–0.15 | **0.04–0.05** |
| Alpha-only art, 3 px/mm | 0.06 | 0.05–0.09 | **0.04–0.06** |
| Alpha-only art, 5 px/mm | 0.05 | 0.05 | 0.04–0.05 |
| Multi-colour logo, 1.8 px/mm | 0.11–0.12 | 0.09–0.12 | 0.09–0.10 (drops features) |
| Multi-colour logo, 3 px/mm | 0.06 | 0.06–0.08 | 0.04–0.05 (drops features) |

- A typical customer file — 146 px wide for an 80 mm design — is 1.8 px/mm,
  about 46 DPI. The trade's lowest published floor is 150 DPI.
- On the real Becker file the coverage read gives clean edges in 405 nodes;
  stage 4 gives 1,683–1,897 nodes with spikes.

## Three findings about our own code

- **The Becker spikes are `subpixel_edges_upscaled`.** Off: 0.0 spikes per
  100 mm. On: 7.1. At 1.8 px/mm it also buys no accuracy (worse in three
  cases of four). At 3 px/mm it helps in three of four. Real problem.
- **The curve and sub-pixel work does pay from 3 px/mm up** — 0.033 against
  0.062 mm at 5 px/mm. Not wasted; just aimed above where Becker lives.
- **All three "photo" logos route `gradient` at confidence 1.00**, so the
  flat-lane engineering never touches them. Known (09-17 review, F3);
  reproduced.

## What the rest of the industry does

Nobody claims an algorithmic fix. They ask for 300 DPI, push vector, publish
feature minimums (text 6.35 mm, lines 1.27 mm), simplify what falls under
them, or sell a human redraw. Wilcom and Hatch tell users to regenerate the
bitmap from the vector original. EMB-Bot warns under 4 px/mm (about 102 DPI).

## SVG import — where it really stands

- `parseSVG` fits `buildQualityDesign` mechanically. **Nobody has ever run the
  two together** — the plan's own risk-gate task (Task 6) was never done.
- Known gaps: paint order is lost (same-colour shapes merged, then sorted
  light to dark), overlaps are not resolved (a background rectangle would be
  stitched), hidden elements are stitched, `rgb(100%,0%,0%)` reads as the
  wrong colour, most skips are silent.
- With the digitizer service up, uploads go to the Python path, which cannot
  read SVG. There is an image-free endpoint already, `POST /digitize-manual`,
  that takes millimetre polygons — and no Studio code calls it. It has no
  "auto" technique, so something must choose satin, fill or run per shape.
- No ruling was found putting vector import in or out of launch scope.

## Decisions for Kent

| # | Decision | My read |
|---|---|---|
| 1 | Turn `subpixel_edges_upscaled` off under about 3 px/mm? | Yes — measured: removes the spikes, costs nothing there. Needs a lane and the golden check. |
| 2 | Build the coverage read for alpha-only art? | Yes, as a flagged spike behind its own instrument. Biggest measured gain of the day, smallest build. Cost: strokes under one source pixel vanish. |
| 3 | Take the coverage read to multi-colour art? | Not yet. Prototype is closer where it draws and loses features. Do 2 first. |
| 4 | Wire real SVG import? | Run the never-run risk gate first: real logos through `parseSVG` and `buildQualityDesign`, look at the picture. One session; decides whether it is a week or a month. |
| 5 | Tell customers at upload? | Cheap and the trade all does it: say "will sew soft, send a larger file or a vector" under about 3 px/mm. Thresholds are a proposal, not a standard. |
| 6 | Land these docs? | Five files plus 2.4 MB of renders, uncommitted on the `main` checkout. Your call whether they go up as one PR. |
| 7 | Housekeeping | Duplicate clone `C:\Users\EE-LT-11030\EMB-Bot`, stray `Claude%20Personal` folder, `main` 19 commits behind origin. |

## What could still be wrong

- Two logos and two single-colour cases cut from them. One run each; treat
  gaps under 0.01 mm as nothing.
- Truth is our own segmentation at native resolution.
- The low-res inputs are clean downscales. Real JPEG ringing is not modelled,
  and it will hurt the multi-colour coverage read most.
- No stitches were generated and nothing was sewn. Closer outlines are not
  yet shown to sew better.
- vtracer got nine settings, not a tuning effort. Potrace was not run (GPL).
- Becker and bridge_bar have no truth; they were only pictured.
- The first pass of the head-to-head said "resolution sets the error". That
  was wrong and is corrected in place.

## Where the detail is

- `docs/tracer-head-to-head-2026-10-10.md` — the measurement, with addendum
- `docs/low-res-vectorization-research-2026-10-10.md` — tools, licences, the
  sub-pixel literature
- `docs/low-res-industry-practice-2026-10-10.md` — vendor-stated minimums
- `docs/renders/tracer-head-to-head-2026-10-10/` — pictures, full tables,
  every script. Best two pictures: `becker-real-iso.png`,
  `goldensil-flat-r1.8-iso.png`
