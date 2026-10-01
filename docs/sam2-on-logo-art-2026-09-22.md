# SAM2 as an automatic region former for LOGO art — measured, refuted

*2026-09-22. Kent: "I would think SAM 2 would have the ability to do much
better than what it is now." Measured on all nine `REAL_ART` logos, both
lanes. **It does not — and the pipeline's own exclusion comment was right.**
The session's real findings are the three defects the renders exposed on the
way past, in §4.*

---

## 0. The verdict, up front

SAM2's automatic mask generator, on this repo's nine real logos, returns
**0–8 masks at the shipped `points_per_side=12`** and **4–25 at `32`**,
against a shipped region former that produces **17–164**. It fails in two
visible ways, and *neither* is a confidence problem — `predicted_iou` sits at
**0.88–0.99** throughout. SAM2 is sure; it simply does not see a logo as a
scene of objects.

1. **Finds essentially nothing** — `drone` 0.6% of pixels covered,
   `screenshot` **0.0%** (zero masks), `fremont` 0.9%, `enthusiast` 3.8%.
2. **Segments the BACKGROUND as the object** — `tires` 90.6%, `golden_tee`
   88.8%, `bridge` 96.5%. The high "coverage" numbers are a backdrop
   rectangle, not artwork. Rendering is the only thing that separates these
   two cases from each other; the coverage number alone reads like success.

Going 12 → 32 costs **5× runtime** (23–28 s → 114–135 s per image, CPU) and
does not change the verdict.

**`digitizer_core/pipeline.py`'s own comment predicted this** and should be
left exactly as it stands:

> "gradient" is deliberately excluded even though it routes to
> `photo_segment` too: a smooth ramp has no distinct objects for an instance
> segmenter to find

The measurement widens that from "gradient" to **flat logo art generally**.

**This does NOT touch the photo lane.** SAM2 stays the right tool for a
photograph — a subject on a background is exactly the instance-segmentation
problem it was trained for, and Kent's 2026-08-11 owl ("drastically better at
the photo recognition portion") is not contradicted by anything here. The
refutation is scoped to *logo art*, which is the lane SAM2 was already
fenced out of.

## 1. The numbers

Shipped arm = `build_generation()`, the real stages 0–4. SAM2 arm = the same
`sam2_worker.py` the seam calls, in the isolated venv, on the source artwork
composited over white, downscaled by `_downscale_for_sam2` exactly as
`sam2_segment_seam` does, with `min_mask_region_area` on the same formula.

| fixture | class | src px/mm | shipped regions | masks @12 | cov @12 | masks @32 | cov @32 | iou med |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| becker | `flat` | **1.46** | 17 | 7 | 9.5% | 15 | 15.9% | 0.94 / 0.92 |
| tires | `photo_scene` | 19.81 | 6 | 2 | **90.6%** | 4 | 92.1% | 0.97 / 0.95 |
| enthusiast | `flat` | 17.50 | 31 | 3 | 3.8% | 5 | 6.9% | 0.92 / 0.92 |
| fremont | `gradient` | 27.03 | 164 | 3 | 0.9% | 15 | 6.9% | 0.89 / 0.90 |
| bridge | `gradient` | **5.00** | 83 | 6 | **96.5%** | 16 | 98.1% | 0.94 / 0.93 |
| golden_tee | `gradient` | 27.41 | 37 | 1 | **88.8%** | 5 | 90.6% | 0.99 / 0.94 |
| gaulke | `gradient` | 16.05 | 53 | 8 | 80.6% | 21 | 99.2% | 0.88 / 0.90 |
| drone | `gradient` | 19.20 | 114 | 3 | **0.6%** | 25 | 3.3% | 0.96 / 0.93 |
| screenshot | `gradient` | 12.75 | 157 | **0** | **0.0%** | 7 | 1.6% | — / 0.92 |

Read `cov` with §0 in hand: a high number is the *backdrop*, a low one is
*nothing found*. Neither is a usable decomposition.

## 2. Two harness bugs found and fixed mid-probe — both instructive

**v1 fed SAM2 `Prep.rgb`.** For an alpha cutout that is a flat block of ONE
colour: becker's prepped raster measures `uniq_colors=1, mean=32.7`, its shape
living entirely in alpha, exactly as `Prep`'s own docstring warns
(*"`becker_marine_logo.png` is black everywhere, shape entirely in alpha"*).
SAM2 returned one mask covering everything — the correct answer to a blank
rectangle — and v1 reported it as a model result. **A segmenter that returns
one confident mask looks identical to a segmenter handed a blank image.**
v2 composites the source over white instead.

**v1 reported only mask COUNT and uncovered fraction.** Those two numbers make
`tires` (backdrop-as-object, 86.8% uncovered in v1's framing) and `drone`
(found nothing) look like the same result. They are opposite failures. v2
records `predicted_iou` / `stability_score` and, more to the point, **renders
the label map** — which is what actually separated them.

## 3. Why the fence is wider than it looks

`PHOTO_CLASSES = ('photo_subject', 'photo_scene')` (`config.py:18`), and
`pipeline.py:585` gates the seam on `is_photographic()`. Stage 0 on the nine:

- `flat` — becker, enthusiast
- `photo_scene` — tires
- `gradient` — fremont, bridge, golden_tee, gaulke, drone, screenshot

**Six of nine are `gradient`.** SAM2 could reach exactly one real logo
(`tires`) before this probe, and **none of the three Kent called "both bad"**
on 2026-09-18 (enthusiast `flat`, drone and screenshot `gradient`). Anyone
reading "SAM2 is merged and reachable" in MASTER_SCOPE should read it as
*reachable on photographs*, not on Kent's commercial work.

There is a supported override, no patching needed: `cfg.is_photographic=True`
wins over the class gate by design (`config.py`'s own contract). It was not
needed here — the probe calls the worker directly.

## 4. What the probe actually found — the part worth acting on

None of these is about SAM2. All three came out of looking at the renders.

**4.1 `screenshot` sews the phone UI.** 157 regions, and the render shows why:
the status bar (`8:35`, `Spotify`, 5G, battery), the `Photo` / `Done` chrome,
the entire bottom toolbar and the home-indicator bar are all being formed as
regions. The logo is a minority of the design. Nothing isolates the subject on
the `gradient` lane — rembg is gated to photo classes, same fence as SAM2.
This is a plain product defect and it is visible at a glance.

**4.2 becker is a 146×91 thumbnail.** `px_per_mm = 1.46` at its 100 mm census
width; stage 1 Lanczos-upscales to 403×251 = 4.00 px/mm, **half** the 8 px/mm
floor that `docs/classifier-cliff-is-input-resolution-2026-09-16.md` measured
as the cure for the satin/fill size cliff (span 0.402 → 0.031). becker is the
fixture most of this repo's parity work is measured against. `bridge` (400×400,
5.00 px/mm) is the only other one under the floor; the remaining seven are
12.75–27.41 px/mm, so **resolution is a becker-and-bridge problem, not a
corpus-wide one** — a conclusion this probe nearly got wrong by generalising
from the first fixture it printed.

**4.3 Region formation on `drone` is GOOD.** The shipped panel reproduces the
badge, the drone, the treeline and all three lines of lettering faithfully at
114 regions. Kent called drone "both bad" on 2026-09-18 — whatever is wrong
there, **it is not region formation**, and a segmenter swap could not have
fixed it. Same for `tires` at 6 regions: a clean, correct script.

## 5. Where SAM2 would actually earn its keep

Automatic mask generation is SAM2's *weakest* mode and the only one measured
here. Its strength is **prompted** segmentation — one click, one high-quality
mask — and the per-mask confidence above (0.88–0.99 even on artwork it barely
engages with) is consistent with that.

The Studio already has the surface for it: the review UI's shape-layers
contract carries `boundary_override`, `merge_shape_ids` and `split_shapes`.
"Click the shape you want separated" is a product feature SAM2 is genuinely
good at, on a machine where the venv is already built. **Not proposed here,
not costed, and it would need its own brainstorm** — recorded so the refutation
above is not mistaken for "SAM2 is useless to this project."

## 6. Reproducing

Throwaway harness, scratchpad-only, deliberately not committed (a spike's
output is an answer). The isolated venv **was a husk** when this started —
`Scripts/` shims and `share/` present, `Lib/site-packages` and `pyvenv.cfg`
both gone, so `sam2_segmentation_unavailable_reason()` returned *"pyvenv.cfg
missing"* and every photo job since roughly 2026-08-14 had been silently
falling back to classical SLIC+RAG, exactly as designed. Rebuilt per
`sam2_isolated/README.md`: torch 2.14.0+cpu / torchvision 0.29.0+cpu from
PyTorch's CPU index, `sam2` from Meta's GitHub with `SAM2_BUILD_CUDA=0`,
`opencv-python-headless`. The old husk is parked at
`sam2_isolated/venv.husk-2026-09-22`.

**Licence, settled from the file on disk rather than a Hub tag** (the
BiRefNet trap in CLAUDE.md): `sam_2-1.0.dist-info/METADATA` reads
`License: Apache 2.0` and ships its own `LICENSE`, whose text is the Apache
License 2.0. Note for anyone checking the Hub instead — `facebook/sam2.1-hiera-tiny`
carries the `apache-2.0` *tag* but `hf_fs find --name *LICENSE*` returns
**zero entries**, so the Hub could not have settled this.

**SAM 3 is not a candidate here** and does not need re-checking: 859.9M
parameters against SAM2-tiny's 39.0M (22×) on a CPU-only box where SAM2
already costs +15–30 s per image, and it is **gated** with `license:other`
against SAM2's Apache-2.0. *(checked 2026-09-22 via `hub_repo_details`)*
