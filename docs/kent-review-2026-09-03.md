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
  **18 colours at 12 and 13 at 6**: stage 2 enforces the cap per population,
  not on the combined total (`stage2_quantize.py`, the comment above the
  enforcement). The Studio's slider says "Colors (max 6)" and the design
  arrives with 13. Golden Tee behaves the same, 15 → 14. Whether that is a
  defect or the lane's intended behaviour is Kent's call; it is recorded
  here because a customer reads the label.
- **BAR & RESTAURANT is gone** (`crop_text`) — teal blobs and a black blob
  sit where the letters and the ampersand were. On 08-27 "Restaurant was
  dropped completely"; now BAR went with it.
- **Exposed yellow travel** crosses the yellow fill in straight lines
  (`crop_text`, `crop_script`). Same colour as the ground it crosses, so it
  may not show on cloth; it shows here.
- **"Bridge"** (`crop_script`) is legible but heavy — the counters of B, d
  and g are part-filled and the letters run together.

## Kent's notes

*(verbatim, as given — to be filled in when he answers)*
