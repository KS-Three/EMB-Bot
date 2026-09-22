# Upload crop — design

*2026-09-22. Kent's call: the customer decides what the subject is, with the
Studio proposing a rectangle. Approved in brainstorm; this is the spec the
implementation plan is written from.*

## 1. The problem, measured

`testdata/photo/screenshot_phone_ui_golke.jpg` at its 80 mm census width sews
**157 regions, 7,986 stitches, 71 trims**. Of that, **47 regions and 1,810
stitches — 24.9% — are phone chrome**: the status bar (`8:35`, `Spotify`, 5G,
a battery icon that sews in green and grey thread), the `Photo` / `Done`
header, four blue toolbar icons and the home-indicator bar. Measured by band
(top 12%, bottom 8% of design height), which deliberately **under**-counts:
the two circular UI buttons sit on the logo's own row — one sews straight
through the word "DIVISION" — and are counted as logo.

**There is a second defect underneath it, and it is the more damaging one.**
The art bbox spans status bar to home indicator, so `target_width_mm = 80`
maps to the *phone screen*, not the logo. The design comes out **80 × 167.3
mm** — a 6.6-inch-tall left-chest placement with the logo as a small band in
an empty field.

Nothing in the pipeline addresses either. `rembg` and SAM2 are both fenced to
`PHOTO_CLASSES = ("photo_subject", "photo_scene")` and this artwork
classifies `gradient`. The Studio's entire current answer is a sentence
telling the customer to go crop it in another program
(`app/src/lib/digitizer.js:1651`).

## 2. Constraints that are forced, not chosen

Both come from measurements already in the repo. Neither is open to taste.

**2.1 The crop must NOT be applied by re-encoding the image in the browser.**
DOCTRINE 2026-09-19/20: the Studio used to POST a 1,200-px 2D-canvas
`toDataURL("image/png")`, and it cost three separate harms — a browser
resample no `cv2` resize reproduces, **premultiplied alpha** (every fully
transparent pixel returns `(0,0,0)`; semi-transparent RGB carries
un-premultiply rounding noise), and a low-quality downscale. Becker went
59 → 175 trims; the tires logo picked up 8 trims its artwork does not have.
Kent paid to remove that on 2026-09-20 by sending the file's own bytes. A
crop implemented as "draw a box, export a cropped PNG" re-introduces all
three. **The original bytes keep going; the crop travels as coordinates.**

**2.2 The coordinates must be normalized fractions, not source pixels.**
`DigitizePanel.imageToSend` prefers the original bytes from IndexedDB but
**falls back to the 1,200-px preview** when the original exceeds the
service's limits (`DigitizePanel.svelte:372`). Pixel coordinates would then
address the wrong raster, silently and only for large uploads. Fractions
survive any resample.

## 3. Data contract

Add to `PipelineConfig`:

```python
# Normalized crop rectangle (x0, y0, x1, y1) as fractions 0..1 of the
# SUBMITTED raster, applied in stage 1 before anything reads the image.
# None = no crop. Fractions rather than pixels because the Studio may send
# either the original file or its 1,200-px preview (see design §2.2).
crop: tuple[float, float, float, float] | None = None
```

`PipelineConfig` already round-trips over HTTP as the `config` JSON of the
existing multipart POST to `/digitize`, so nothing in the service's transport
changes.

**The generation cache is already correct for this, by construction.**
`digitizer_service/jobs.generation_key` hashes every config field *except*
the four `EDIT_KEYS` (`deleted_shape_ids`, `shape_overrides`,
`merge_shape_ids`, `split_shapes`). `crop` is not one of those, so changing
the crop invalidates the stage 0–4 generation exactly as it must, with no new
code. `tests/test_generation_cache.py` pins `EDIT_KEYS`, so a future change
that tried to misfile `crop` as an edit key would fail a test rather than
silently serve a stale generation.

**Validation.** Clamp to `[0, 1]`, require `x1 > x0` and `y1 > y0` after
clamping, and require the cropped region to be **at least 16 px on each
axis** in the submitted raster. 16 px is not a physical constant — it is the
smallest frame the downstream border-flood can read a background from at all
(`_border_ring` uses a 2 px ring, and `_modal_corner_ownership` samples 8 px
corners), so anything smaller fails inside stage 1 with a worse message than
this check gives. A rectangle that fails validation is a caller error, not artwork
damage: raise, and let `digitizer_service/errors.py` map it — that file's map
is an **allowlist** precisely so a message naming the caller's own bad edit
passes through unchanged (see its 2026-09-07 entry). Do not silently fall
back to the full frame; a crop that quietly did not apply is the failure mode
hardest to notice.

## 4. Where it applies

In `stage1_prep.prep()`, immediately after `_load` and **before** everything
else: before the border-flood background detection, before the denoise,
before the resolution-floor upscale, before `art_bbox`.

Consequences, all intended:

- `px_per_mm` derives from the cropped raster, so **`target_width_mm` maps to
  the logo**. This is what fixes the 167.3 mm design; no other approach
  considered in the brainstorm did.
- Background detection sees only the cropped frame, so the page around a
  cropped-out chrome band never enters the decision.
- `Prep.input_px_per_mm` still records what the SOURCE delivered, now for the
  cropped region — which is the honest number for the
  `INPUT_LOW_RESOLUTION` warning, since cropping genuinely reduces the pixels
  available at the target size.

## 5. The proposed rectangle

Computed **client-side, in JS, from the preview canvas the app already
builds**. That is a display-only use of the canvas and does not violate §2.1,
which is about what gets *sent*. No new service endpoint and no round-trip
before the customer sees a suggestion.

Algorithm — the dominant ink cluster, not the bbox of all ink:

1. Ink mask: pixels differing from the frame's background (the border-derived
   colour, matching stage 1's own border-flood premise).
2. Dilate by ~**4 mm at design scale** so the glyphs and marks of one logo
   merge into a single blob.
3. Connected components; rank by the **real ink** each blob contains, not the
   dilated blob's own area — dilation inflates a scatter of specks more than
   a solid mark.
4. Bbox of the winner, plus ~**2 mm** margin, expressed as fractions.

**Why not the bbox of all non-background ink:** on the screenshot that spans
status bar to home indicator — the whole screen — which is useless on the one
case the feature exists for.

**Measured on all nine `REAL_ART` logos** (prototype, throwaway, in the
brainstorm; the shipped version is the same four operations in JS):

| fixture | proposed (w × h) | area | outcome |
|---|---|---:|---|
| becker | 1.00 × 1.00 | 1.00 | no-op |
| enthusiast | 1.00 × 1.00 | 1.00 | no-op |
| fremont | 1.00 × 1.00 | 1.00 | no-op |
| gaulke | 1.00 × 1.00 | 1.00 | no-op |
| golden_tee | 0.92 × 0.78 | 0.72 | trims dead space |
| bridge | 0.80 × 0.80 | 0.64 | trims dead space |
| tires | 0.77 × 0.55 | 0.43 | trims white page |
| drone | 0.57 × 0.89 | 0.51 | trims grey backdrop |
| **screenshot** | **0.98 × 0.27** | **0.27** | **chrome gone** |

Checked by render, not by the numbers: nothing is cut on any of the nine. The
screenshot rect frames the truck and both lines of type and excludes status
bar and toolbar entirely; drone's frames badge, all three lines of type and
the target icon; tires' frames the whole script. The four no-ops are artwork
that already fills its frame.

The proposal is **always a visible, draggable suggestion and never applied
silently.** That is what separates it from the auto-detect approach Kent
rejected: when the heuristic is wrong it is wrong in front of the customer,
who can drag it.

## 6. UI

Inline in `DigitizePanel`, drawn on the preview already shown there — no
modal, no new route, no mandatory interstitial for the customer whose
proposal is simply correct.

**Carve the crop surface into its own child component.** `DigitizePanel` is
already large and this adds pointer-drag state; growing that file further is
the wrong direction. The child owns the rect, the drag handles and the
"use whole image" reset, and emits the normalized rect upward.

Required affordances:

- The rect pre-set to the proposal, with drag handles on corners and edges.
- A permanent, discoverable reset to the whole image — a customer whose
  proposal is a wrong no-op must still be able to find the tool.
- The rect persists with the element (alongside `sourceFile`) so re-running a
  digitize does not lose it.

## 7. Tests

**Python**
- Crop applied in `stage1_prep`: a known rect yields the expected raster
  extent and `px_per_mm`.
- Validation: out-of-range, inverted and degenerate rects raise, and the
  service maps the error to a sentence naming the caller's own input.
- Crop is part of the generation identity: two jobs differing only in `crop`
  do not share a cached generation. Extends `tests/test_generation_cache.py`.
- Crop × resolution floor: a crop that pushes a design under
  `min_px_per_mm` upscales and warns `INPUT_LOW_RESOLUTION`.
- Crop × alpha cutout: cropping an alpha-cutout logo does not disturb
  `native_alpha` / `Prep.upscale` bookkeeping.

**JS**
- The proposal algorithm against fixtures, including the screenshot (must
  exclude both chrome bands) and a clean logo (must return the full frame).
- Rect → config serialization: fractions, clamped, absent when uncropped.

**Corpus regression**
- The four no-op logos must come out **byte-identical** with `crop=None`.
  This is the guard that the feature is inert where it should be.

## 8. The risk that must be measured, not reasoned about

**Cropping changes `px_per_mm`, and `px_per_mm` against `cfg.min_px_per_mm`
is the gate for `alpha_edge_extend_upscaled_only`**
(`alpha_edge.upscale_expected`, called at `alpha_edge.py:107`). So a crop can
flip `alpha_edge_extend`'s behaviour on a design as a side effect of framing
— a flag Kent flipped ON on 2026-09-20 specifically *because* it was gated to
the under-floor regime.

The same coupling, from the other direction, is what made the resolution-floor
raise a bad idea on 2026-09-22 (see the SUPERSEDED addendum on
`docs/classifier-cliff-is-input-resolution-2026-09-16.md`). It is a real
interaction, it is not obvious from either file, and the plan must include a
measurement of it on an alpha cutout crossing the floor — not an argument
about it.

## 9. Non-goals

- **No automatic cropping.** The engine never crops without the customer
  seeing and accepting a rectangle. Kent rejected auto-detect explicitly.
- **No chrome/screenshot detection.** Nothing classifies an upload as a
  screenshot. The proposal is generic dominant-ink framing that happens to
  handle screenshots well.
- **Not a rotation, perspective or freeform selection tool.** An
  axis-aligned rectangle only.
- **Does not widen the `PHOTO_CLASSES` fence.** `rembg` and SAM2 stay where
  they are; this is a spatial crop, not background removal.
- **Does not address the UI button inside the logo's own bbox.** No
  rectangle can exclude it. If it matters, it is a review-UI shape deletion,
  which already exists.
