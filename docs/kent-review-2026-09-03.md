# Three logos in thread — the render pass for Kent's review, 2026-09-03

Kent, 2026-09-03: *"provide me a rendering of 3 digitized images, and i will
provide feedback of what needs to be worked on."* This file is the record of
what he was shown, pinned well enough to reproduce, with room at the bottom
for his notes verbatim. `docs/yardstick-vs-kents-eye-2026-08-28.md` ends on
"settling it needs fresh per-design verdicts on CURRENT output" — this is
that output.

## What was rendered, and how

- **Engine:** `main` at `ede3550` (after PR #336), the Python digitizer's
  `digitize()` called directly — no service, no Studio — with **the Studio's
  own defaults** (`app/src/lib/project.js` `DEFAULT_DIGITIZE_PARAMS`):
  `max_colors=6, satin=True, detail_layer=False, edge_cap="none"`, border
  and fill angle omitted (absent-means-auto), garment and width per row.
- **Render:** `digitizer_core/stitchviz.render_design` at 12 px/mm, the
  same lit-filament model `preview.js` draws in the Studio. It shows where
  thread lands and how much cloth it covers, and nothing about tension,
  pull, nap or push — the docstring's own caveat, repeated here because a
  render is not a sew-out (ROADMAP gate 1).
- **Side-by-side sheets:** artwork on the left scaled to the same
  millimetres as the render on the right, so a feature can be compared at
  the size it would sew. Crops are 3× (36 px/mm) of the same render.
- Machine files (DST/PES) were written through pystitch, the `/export`
  convention (CLAUDE.md footgun 1), and kept out of the repo.

| fixture | width, garment | source density | stitches | colours | trims | jumps | thread | coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `becker_marine_logo.png` | 100 mm, left chest | **1.5 px/mm** (146 px wide) | 6,459 | 1 | 37 | 0 | 16.96 m | 0.42 |
| `photo/logo_hotel_fremont.webp` | 92.5 mm, patch | 27.1 px/mm | 9,990 | 3 | 104 | 116 | 14.83 m | 0.63 |
| `photo/logo_bridge_bar.jpg` | 80 mm, left chest | 5.0 px/mm | 10,885 | **13** | 106 | 14 | 22.35 m | 0.40 |

Becker and Fremont are stitch-for-stitch the numbers of the 2026-09-03
render pass in `docs/design-review-fine-lettering-2026-09-03.md` §11
(6,459 / 37 and 9,990 / 104), so those two are the same output Kent has
already seen at 1× — this pass adds the artwork beside them and the crops.
Bridge Bar has not been rendered for him since his 2026-08-27 note.

Two more were rendered the same way and are in the session, not committed —
`enthusiast_logo.png` 80 mm (2,349 st, 2 colours, 21 trims) and
`logo_golden_tee.jpg` 80 mm (6,512 st, 14 colours, 59 trims) — available on
request.

## Where I looked before sending (Claude's read, not Kent's)

Listed so his notes can confirm, contradict or ignore them. Each line names
the crop that shows it.

### Becker Marine — `renders/kent-review-2026-09-03/becker_marine_*.jpg`

- The source is **146 pixels wide for a 100 mm design** — one and a half
  pixels per millimetre of stitching. Every edge in the render is the
  raster's staircase at that scale; the "jaged" edges he named on 08-27 are
  not separable from the artwork's resolution on this fixture. A higher-res
  Becker source would change this render more than any engine change.
- **The C's counter** (`crop_C`): the black infill inside the C sews as a
  satin blob, a satin column and a run joining them — three pieces where the
  art has one shape. On 08-27 he called it "completely lost"; it is now
  partly there, and fragmented.
- **The N** (`crop_N`): a run stitch lies ON TOP of the finished tatami — a
  vertical one down the left stem and a diagonal across the right half.
  Fill travel under cover (defect 21, default ON) was meant to bury exactly
  this; on the N it did not. Same tone as the fill, so it may vanish on
  cloth — a sew-out question, but visible on screen.
- MARINE's tatami rows read as rows; the letter edges are stepped.

### Hotel Fremont — `renders/kent-review-2026-09-03/hotel_fremont_*.jpg`

- **EAT | STAY | PLAY is still not there** (`crop_bottom`) — the bottom of
  the hexagon holds rope fragments and a stray white bean rectangle where the
  words were. His 08-27 note stands unchanged.
- **EST 1895 is gone** (`crop_top`) either side of the Wisconsin shape,
  which does sew (without its star).
- **THE reads "T H C"** at 3× — the E's top and bottom arms sew as bean runs
  (defect 24's fix), its middle arm does not. §11 of the fine-lettering
  review says it "reads THE"; at this scale the middle arm is absent in that
  document's own after-crop too. A reading, not a measurement.
- **The rope border** is a chain of tan chunks with gaps — 136 separate
  chevrons in the art (defect 6) and still "intermittently in and out".
- The patch's white ground fills the whole hexagon and out past the banner
  ends, as a patch would; the fill's row texture is visible on screen.

### Bridge Bar — `renders/kent-review-2026-09-03/bridge_bar_*.jpg`

- **13 thread colours on a four-colour logo.** The JPEG's compression halos
  around the black spokes become their own spools — Cobblestone, Saturn
  Grey, Silver, Sterling — and sew as grey and white outlines along every
  spoke (`crop_spoke_top`). A 400 px JPEG classifies `gradient`.
- **`max_colors` is not a cap on the gradient lane.** The pipeline's own
  default is 12 (`config.py`), the Studio sends 6, and this design sews
  **18 colours at 12 and 13 at 6**. The Studio's slider says "Colors
  (max 6)" and the design arrives with 13. Golden Tee behaves the same,
  15 → 14. **Mechanism corrected in the review below** (this line and PR
  #337's body first blamed stage 2's per-population enforcement, which is
  the FLAT lane's quantizer and not what runs here): on the gradient lane
  the photo palette selects `max_colors + PALETTE_OVERFLOW_K` = 9, and the
  re-snap after outline drift adds four spools the list never named — both
  already in the record (scope #6.1 and defect 15).
- **BAR & RESTAURANT is gone** (`crop_text`) — teal blobs and a black blob
  sit where the letters and the ampersand were. On 08-27 "Restaurant was
  dropped completely"; BAR was already blobs then too — measured below on
  the 08-27 engine, so this is not a regression (an earlier draft of this
  line implied one).
- **Exposed yellow travel** crosses the yellow fill in straight lines
  (`crop_text`, `crop_script`). Same colour as the ground it crosses, so it
  may not show on cloth; it shows here.
- **"Bridge"** (`crop_script`) is legible but heavy — the counters of B, d
  and g are part-filled and the letters run together.

## Review — what is wrong, measured, and whether the record agrees (Claude, same day)

Kent's second ask, verbatim: *"review the renderings, determine what is wrong with
the digitized photos and see if your findings align with the .md information."*
Everything below is measured on the same three plans as the renders (pickled
`digitize()` output), not read off the pictures, and each finding ends with the
record it was checked against. Instruments: `tools/dropped_elements.py --detail`,
`tools/fill_exposure.exposure(plan)`, `tools/edge_smoothness.py`, stroke widths
from a distance transform on the artwork at the design's px/mm, the
professional's PES files in `Embroidery Files.zip` (repo root — they were there
all along) decoded with pystitch and drawn by the same renderer, `main` before
PR #282 (`d6b7a6e`, the state Kent's 08-27 notes describe) in a worktree, and
`forced_class="flat"` runs. Sheets: `renders/kent-review-2026-09-03/*_pro_vs_ours.jpg`
and `*_gradient_vs_flat.jpg`.

### Hotel Fremont — nothing is dropped; the small text is sewn illegibly, and the pro proves it need not be

1. **Not dropped.** `dropped_elements`: 3 regions, 4.2 mm², **0.2%** of the art.
   The tagline is five tan regions — `Sbe6c9978` 8.6 mm², `Sca9d5ea0` 5.1,
   `Sac264dc6` 3.6, `S30b4f308` 2.5, `S2666889d` 0.9 — each sewn as two to
   seven satin bits plus runs; EST is `Sdf7cf574` (9.0 mm², 5 satin runs + 1
   run), 1895 is `S863edab0` (10.8 mm², 16 satin runs). Those are the tan
   blobs in `crop_top` and `crop_bottom`.
2. **Why they are blobs.** Stage 0 classes the badge `gradient`, so stage 2 is
   SLIC: 945 superpixels → 58 → 50 regions, 10 details under 1.5 mm absorbed.
   Measured in the art at 27 px/mm, EAT | STAY | PLAY is 3.4–5.0 mm tall with
   0.38–0.56 mm strokes and THE is 3.1 mm with 0.24–0.28 mm strokes; a
   superpixel segmenter cannot hold a stroke that thin, and what survives is
   then sewn under the 0.5 mm cross floor as bean runs and satin bits.
3. **The pro sews all three, legibly, at the same 92.5 mm.** Decoded from the
   pro's PES: 15,458 stitches, 53 trims, 9 blocks (White, Black, Light Brown,
   White, Flesh Pink, Black, White, Black, Light Brown). The gold lettering
   block (1,090 st) has a median stitch of **0.82 mm** inside the tagline band
   and THE's black block **0.90 mm** — satin columns of roughly 0.8–0.9 mm,
   two to three times the art's stroke. The pro widened the strokes to a
   sewable column; we keep the art's width and sew a bean.
4. **THE reads "T H C".** The E is `S3ddcec6c` (3.7 mm²): one 6.6 mm satin run
   and one 15.1 mm bean run. Its middle arm is about 1 mm long, under the
   three-station spine the hairline rule needs, so it does not sew.
5. **The rope** is 21 tan regions (128 satin runs, 28 trims in the 0862 block).
   The pro does not digitize the chevrons at all: its rope is one continuous
   satin band of about 1.7 mm (block 2, 762 st, median stitch 1.72 mm).
6. **Exposed fill travel:** 9 runs, **59.6 of 185 mm (32%)** lie over fill
   already sewn, with `fill_travel_under_cover` ON.
7. **The flat lane today** (`forced_class="flat"`): 8,757 st, 73 trims, 3
   colours, 33 regions. HOTEL FREMONT and THE unchanged, the tagline sews as
   "A  A P A" fragments, and EST 1895 and the rope are dropped outright
   (`DROPPED_SMALL_SHAPES`). Cleaner ground, more lost — not the fix either.
8. The pro's pink outer band is a merrow-edge simulation for a patch, not in
   the art; not a defect of ours.

**Against the record.**

| claim | where | verdict |
|---|---|---|
| THE and the tagline exist as `stitched: true` shapes, 2–5 mm² | scope #1, Fremont findings item 1 | **confirmed** — same shape ids today |
| "a genuine physical-scale limitation … nothing new to build" | same item | **contradicted** by the pro's file: same size, legible, 0.8 mm satin |
| rope sews as ~21 disconnected fragments | same doc, item 2 | **confirmed** — 21 |
| forced flat is worse: "2 colors, no counters, a crushed mass" | same doc, item 3 | **stale** — today 3 colours, counters intact; still loses rope and EST 1895 |
| "after, the arms sew as bean runs and it reads THE" | design review §11 | **contradicted** — T H C, in that doc's own after-crop |
| defect 24: bean vs dropped bar is card block 5's question | MASTER_SCOPE | the pro's answer is a third option, widen to satin — evidence for the card |
| defect 6: the art is ~136 chevrons | MASTER_SCOPE | **confirmed**; the pro's construction shows the target |
| defect 21: fill travel under cover FIXED | MASTER_SCOPE | **reduced, not gone** — 32% still exposed here |
| Kent 08-27: tagline lost, EST dropped, THE incomplete, rope in and out | kent-review-08-27 | all four still true to the eye; "not dropped" is a fact about regions, not about reading |
| `dropped_elements` "works" | kent-eye-vs-instruments memory | **gap**: 0.2% on a design whose small text is unreadable — it cannot see sewn-but-illegible |

### Becker Marine — the fixture is the staircase; the C is a satin-decomposition loss; MARINE is fill where the pro satins

1. **1.46 px/mm.** The fixture is 146 px wide for a 100 mm design: one pixel is
   0.68 mm. Stage 1 upscales it to its 4 px/mm floor (`px_per_mm` reads 4.00 in
   the result) and `INPUT_LOW_RESOLUTION` never fires, because the warning
   only fires when the capped upscale cannot reach the floor — `min_px_per_mm`
   4.0 with `upscale_cap` 4.0 means any source above 1.0 px/mm passes in
   silence — so nothing tells the user the source was 146 px. `edge_smoothness` reads ragged
   0.186 mm, perimeter ×1.02, measured against that same raster, so it
   cannot see it either. The pro's file (95.7 × 58.3 mm, 11,274 st, 52 trims,
   Black/Gray/Black/Gray) has smooth edges — it came from better art. A
   higher-resolution Becker source is a bigger lever on this render than any
   engine change, and Kent's 08-27 "jaged" was partly a verdict on the file.
2. **The C's infill.** `dropped_elements`: 42 mm² at the C (18.2 + 10.0 + 7.5 +
   6.4, each 1–2% sewn), 114 mm² and 6.4% lost overall. The counter is not
   its own region: it is part of the 1,022 mm² outline region `S92a90056`
   (satin route, 24 satin runs), and satin decomposition covers the ribbon
   and leaves the attached blob — the mechanism in
   `.claude/memory/satin-extremity-drop-and-coverage-check.md`. Today a blob
   and a column sew there; the rest is bare.
3. **MARINE.** M, A, R, N, E (164–211 mm², 2.6–3.2 mm strokes) route to
   tatami; only the I (75 mm²) is satin. The pro satins all six letters. Defect
   5's "the mix nearly matches the pro's" does not hold inside this word: five
   of six differ. The classifier sees a multi-stroke letter as one irregular
   region; the pro decomposes it into columns.
4. **The letter bodies.** BECKER's white bodies are 40% of the design and
   sew as holes (`BACKGROUND_ENCLOSED`, 7 areas). The pro fills them — black in
   the file, on both the white and the black garment simulation. A product
   decision, and the toggle exists; recorded because the pro's answer is
   "sew them".
5. **The N.** Exposed fill travel: 5 runs, **55.8 of 148 mm (38%)**, the fix
   ON; the run across the N in `crop_N` is one of them.
6. **vs 08-27** (`d6b7a6e`): 6,620 st / 35 trims then, 6,459 / 37 now; no
   visible change.

**Against the record:** Kent 08-27 "C infill completely lost" and
`ARTWORK_UNCOVERED` 18.8 mm² — **confirmed**, mechanism named; "jaged" —
**re-attributed** in part to the fixture's 1.5 px/mm; defect 5 — a
counter-example to "mix matches"; defect 21 — residual, as on Fremont;
defect 22's 20 px/mm gate — consistent (no curve refinement at 1.5 px/mm)
and beside the point next to the source.

### Bridge Bar — resolution-bound text, and a third of the stitches on JPEG artefacts

1. **3.5 px/mm.** The 400 px JPEG has white margins; the art is 282 px across
   for 80 mm. The blue lettering is 5 mm tall with 0.54 mm strokes — 1.9
   pixels. Neither lane recovers it: the shipped route sews six teal blobs
   (40 of the 104 mm² of blue ink) and paints the rest in the ground yellow —
   `dropped_elements` 289 mm² (11.4%) "lost", with its biggest rows along the
   bottom arc all "100% sewn, dE 36–41", i.e. sewn in the wrong colour. Forced
   flat: 8 colours, the text still blobs. **The 08-27 engine gives the same
   blobs** — not a regression.
2. **13 colours, by documented mechanisms.** `PHOTO_PALETTE_SELECTED` picks 9 =
   `max_colors` 6 + `PALETTE_OVERFLOW_K` 3 (scope #6.1's soft cap), then
   `THREAD_RESNAPPED_AFTER_DRIFT` / `PALETTE_THREAD_MISMATCH` add four spools
   the list never named (0182, 0501, 0713, 1375, 3971) — defect 15's re-snap
   escape, here on a gradient logo. Not per-population enforcement; that
   correction is above.
3. **What the extra spools sew: the JPEG.** Ringing around the black spokes
   and the yellow/black boundary becomes 0108 Cobblestone (24 runs, 874 mm),
   0111 Whale (16 runs), 0145 Skylight (14 regions of 0.2–2.1 mm², each a
   6–44 mm run), 3971 Silver, 0182 Saturn Grey, 0465 Umber, 6031 Limelight;
   shade drift adds a second yellow (0713, 478 st) and a second black (1375,
   838 st). Blocks 6–12 together: **3,131 stitches (29%), 53 trims (50%), 7
   of the 13 colour changes** on artefacts and text remnants. **Not in any
   doc.**
4. **Exposed fill travel:** 8 runs, **75.8 of 194 mm (39%)**, in the fill's own
   yellow.
5. **"Bridge"** is one 223 mm² region with 4 holes (the art has five counters;
   one absorbed at `min_detail_mm` 1.5), eight satin runs — heavy, intact.

**Against the record:** Kent 08-27 "Restaurant dropped" — **confirmed** and
root-caused to input resolution; "BRIDGE should be cleaner" — ragged
0.148 mm, mid-spread; the halo spools — **new**; the colour count — documented
mechanisms, and the Studio's "Colors (max 6)" is still not what the customer
gets; defect 2 (the sub-mm satin floor barred on the gradient lane) — the spoke
halos are exactly what that floor would catch.

### What this changes about what to do next

- **Stop calling Fremont's small text a physical limit.** The pro's file in
  the zip sews it at 0.8 mm satin. The gap is segmentation (SLIC on a badge)
  plus width policy (bean under 0.5 mm instead of widening), and it is ours.
- **Report the source density up front.** 1.5 and 3.5 px/mm decided two of
  these three renders before the engine ran, and the low-resolution warning
  did not fire on either. Whether the Studio should say "146 px for 100 mm"
  is Kent's call.
- **`dropped_elements` needs a legibility reading**, or it will keep scoring
  a design Kent calls "completely lost" at 0.2%.
- **Defect 21 is a reduction.** A third of fill travel is still exposed on all
  three; the word FIXED in MASTER_SCOPE should carry that.
- **Two doc lines corrected in this PR:** scope #1's Fremont item 1 now points
  at the pro file; design review §11 now says T H C.

## Kent's notes

*(verbatim, as given — to be filled in when he answers)*
