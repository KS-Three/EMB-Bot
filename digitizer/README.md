# digitizer-core

Auto-digitizing engine for Fritsch's Stitches: flat artwork in, machine-ready
embroidery out. Python, independently testable, independently sellable — see
`docs/superpowers/plans/2026-07-29-digitizer-step1-skeleton.md` for the plan
this implements and the blueprint it comes from.

**Status: build step 1 of 11 — stages 1–4 only.** No stitches are generated
yet. What exists: artwork → background-masked, thread-snapped, segmented,
vectorized regions in millimetres. Stitch planning (fill/satin/underlay),
the stitch processor, the FastAPI service, and EMB-Bot integration are later
steps.

## Setup

```
cd digitizer
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Windows
```

## Run

```
.venv/Scripts/python -m pytest -q                   # 28 tests, all offline
```

Digitize one image and dump per-stage debug PNGs:

```python
from pathlib import Path
from digitizer_core import run_stages, PipelineConfig

result = run_stages(
    "testdata/logo_whitebg.png",
    PipelineConfig(target_width_mm=80.0, debug_dir=Path("debug_out/demo")),
)
for r in result.regions:
    print(r.shape_id, r.thread_number, round(r.area_mm2, 1), "mm2")
print(result.warnings)
```

`debug_out/demo/` then holds `stage1_bg.png`, `stage2_labels.png`,
`stage2_snapped.png`, `stage3_regions.png`, `stage4_vectors.png` — the visual
record for judging pipeline behavior by eye.

Run pytest via `python -m pytest` (not the `pytest` script) so the working
directory lands on `sys.path` and `digitizer_core` imports without an install.

## Conventions that other code depends on

| Thing | Convention |
|---|---|
| Image arrays | **RGB** uint8 (cv2 loads BGR; converted at the door) |
| Color math | CIELAB via `skimage.color.rgb2lab` on float RGB in [0,1] — never cv2's 8-bit Lab |
| Thread matching | **CIEDE2000** (perceptual). Euclidean Lab is used only for cluster merging and the anti-alias blend test, which need a metric geometry |
| Output space | millimetres, floats, origin at the **artwork bbox center**, **y-axis DOWN** |
| `bg_mask` | `True` means background — never stitched |
| Warnings | `{"code": ENUM, "message": str, ...}` — UI switches on codes, never prose |

**y-axis:** the contract is y-down (screen convention). EMB-Bot's own engine
is +y **up**, so the browser adapter (build step 10) owns that flip.
`test_coordinates_are_y_down_and_centered` is what makes a silent mirror
there detectable.

## Determinism

The classical path is the determinism reference: same bytes in, same shape
IDs, areas, and warnings out (`test_two_runs_of_the_same_input_are_identical`).
This is why stage 2 ships its own seeded k-means instead of `cv2.kmeans`
(whose RNG behavior across versions/thread counts is not ours to control),
and why `opencv-python-headless` is **exact-pinned** in `pyproject.toml` — a
minor bump can change clustering and silently invalidate the goldens. Bump it
deliberately, then re-check the fixtures.

Shape IDs have two mechanisms because one is not enough: a content-derived
hash labels new shapes, and `match_shape_ids()` carries IDs forward across a
regeneration by geometry matching. The service round-trips
`deleted_shape_ids`, and hashing alone churns when a value crosses a
quantization boundary — measured, not theoretical.

## Fixtures

`testdata/*.png` are generated, not found art (no licensing questions, known
geometry, so tests assert exact structure). Regenerate with
`.venv/Scripts/python tools/make_test_logo.py`. Each element earns its place:
a blob, a ring (hole preservation), a ~2 mm bar (satin candidate), touching
different-color rectangles, a sub-sewable patch (absorb path), an isolated
sub-sewable dot (drop path), anti-aliased edges throughout.

`tools/gen_isacord.py` generates the 398-color Isacord chart from the repo's
palette data. Thread numbers and RGB values are factual manufacturer data;
Isacord is a trademark of the Amann Group, used only to identify the thread
line.

## License policy

Permissive dependencies only — MIT / BSD / Apache-2.0 / zlib. **No GPL or
AGPL, ever**; LGPL only as dynamically-linked binaries, which is why the
build uses `opencv-python-headless` (standard `opencv-python` wheels bundle
LGPL FFmpeg). Ink/Stitch (GPL-3.0) may be *read* to learn algorithms; no code
or data files are copied from it.
