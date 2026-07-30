# digitizer-core

Auto-digitizing engine for Fritsch's Stitches: flat artwork in, machine-ready
embroidery out. Python, independently testable, independently sellable — see
`docs/superpowers/plans/2026-07-29-digitizer-step1-skeleton.md` for the plan
this implements and the blueprint it comes from.

**Status: build steps 1, 3 and 4 of 11 — stages 1–7, fill + satin.** Artwork
goes in and a sewable DST comes out: background-masked, thread-snapped,
segmented and vectorized (step 1); sew-ordered, underlapped, filled with
underlay, sequenced with lock stitches, and exported (step 3); and ribbons —
lettering, borders, thin strokes — sewn as satin columns along their medial
axis (step 4). `SHAPE_TOO_THIN_TO_FILL` now means "thin but not stroke-like
enough for satin": compact slivers worth review-screen eyes.

SAM 2 segmentation (step 2) was deferred by Kent in favour of steps 3–4 — the
`Segmenter` seam means it drops in later without touching stitch code. Still
to come: the stitch processor, the FastAPI service (step 8) and EMB-Bot
integration (step 10). See
`docs/superpowers/plans/2026-07-30-digitizer-step4-satin.md` for the satin
design and the eleven defects found and pinned while building it.

## Setup

```
cd digitizer
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Windows
```

## Run

```
.venv/Scripts/python -m pytest -q                   # 68 tests, all offline
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

Digitize all the way to a machine file:

```python
from digitizer_core import PipelineConfig, digitize, write_dst

result, plan = digitize(
    "testdata/logo_whitebg.png",
    PipelineConfig(target_width_mm=80.0, garment_id="hat_front",
                   debug_dir=Path("debug_out/demo")),
)
print(plan.stats.stitch_count, "stitches,", len(plan.blocks), "colors")
write_dst(plan, "out.dst")
```

That adds `stage5_sewgeometry.png` (sewing shapes after underlap and pull
compensation, numbered in sew order), `stage6_stitches.png` (every stitch in
thread color; travel thin, needle-up moves magenta) and
`stage6_penetrations.png` (needle holes only — the view that shows whether the
stagger is working and whether edges are crisp).

`run_stages` and `plan_stitches` are separate on purpose: stages 1–4 are the
expensive half and answer "what shapes, in what threads", while stages 5–7 are
cheap (~0.8 s for a 13,000-stitch logo) and answer "how does a machine sew
that". The service re-plans after every parameter tweak without re-running the
first half.

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
| Machine limits | `machine.py` only — no stitch length, density or tie constant lives anywhere else |
| Fabric presets | Mirror `src/fabrics.js` exactly; move a value in both or in neither |
| `StitchRun.jump` / `.trim` | Properties of the run being moved TO, since that is the run whose first stitch has to be reached |

**y-axis:** the contract is y-down (screen convention). EMB-Bot's own engine
is +y **up**, so the browser adapter (build step 10) owns that flip.
`test_coordinates_are_y_down_and_centered` is what makes a silent mirror
there detectable.

pyembroidery's stitch space is also y-down, so `export.py` scales mm to 0.1 mm
units and does nothing else. That was measured, not assumed — see below.

## Open finding: the browser engine's DST codec disagrees with the standard

While verifying export orientation (2026-07-29), a professionally digitized
third-party file (`Downloads/Other/2024/beckers logo hat.DST`) was decoded two
ways. Through pyembroidery it renders upright and correctly proportioned at
101.9 × 62.1 mm. Through EMB-Bot's own `src/dstimport.js` the same file comes
out 62.1 × 101.9 mm — rotated a quarter turn.

The cause is in the bit-weight table. `src/dst.js` puts x in the high nibble of
each record byte and y in the low nibble; pyembroidery (and the published
Tajima table) do the opposite. Both EMB-Bot's encoder and its decoder use the
same table, so the browser engine round-trips its own files perfectly and the
disagreement only shows against other software. Reading an EMB-Bot-written DST
back through pyembroidery reproduces it: a 127 × 43.4 mm hat design reports as
43.4 × 127.0 mm.

This has NOT been changed. Kent has sewn EMB-Bot files on his Tajima, so
something reconciles this on real hardware, and rotating every design he has
made on a theory would be reckless. What it means for this package: DST
verification goes through pyembroidery, never through the browser codec, and
build step 10's adapter needs its own round-trip golden rather than an
assumption. Resolving it needs a sew-out or a third opinion (any machine or
viewer that is not either of these two implementations).

## Stitch planning: what makes it look professional

Three decisions carry most of the quality, and each has a test named after the
defect it prevents.

**Sew order decides underlap direction, so it is settled first.** Threads sew
largest-area-first (stage 2 already orders them that way), then each region is
extended underneath the regions that sew *after* it and forbidden from growing
back over the ones already down. Reverse those two and the seam sits proud of
where the artwork put it. Pull compensation grows the free edges by the fabric
preset's amount; it is uniform, where true pull comp acts perpendicular to the
stitch direction only, and that matches the browser engine until sew-outs say
otherwise.

**Rows are cut into monotone columns before anything is sewn.** A column is a
run of consecutive rows that each contribute exactly one span; forks (the top of
a ring splitting around its hole) end the column and start new ones.
Boustrophedon inside a column is then exact, and every awkward move becomes an
explicit travel decision instead of a stitch flung across a counter. Travel
prefers a straight run, falls back to following the shape's own inset edge, and
lifts the needle only when the detour would exceed `max(20 mm, 4x direct)` —
past that, running travel back over finished fill shows worse than a trim does.

**Penetrations are staggered.** Every row's stitches are offset by a quarter of
a stitch length, realigning every fourth row. Without it the needle holes line
up into visible channels; `stage6_penetrations.png` is the view that shows it.

**Satin for ribbons** (`stage6_satin.py`). Shapes whose ribbon width
(2·area/perimeter) is ≤ 3 mm and whose length is ≥ 3× that width sew as zigzag
columns perpendicular to a medial-axis spine, not as fill — the single
technique that most separates professional output from hobby output.
Classification runs on the ARTWORK polygon so fabric choice can never flip a
logo's structure; sewing runs on the stage-5 compensated one. The skeleton walk
stops at junction nodes and consumes pixels exactly once; collinear arms weld
into through-strokes (a T is a bar plus a yielding stem, never two half-bars);
free ends extend to the cap edge and finish with a square-end terminal cross;
`medial_axis(rng=0)` is REQUIRED — unseeded it is nondeterministic and the same
artwork digitizes differently run to run. Every consecutive pair of runs is
linked with an explicit jump/trim decision and oriented to start at the end
nearer the needle; on the drone-logo benchmark that halved the trim count.

Two things the fill does that look wrong until you know why: row ends always
land exactly on the shape boundary (that is what makes an edge crisp, and the
0.4 mm row turn between them is a legitimate stitch, so the tiny-stitch filter
must not touch fill paths), and lock stitches only ever reach *into* a shape,
never past the point they tie at — ties laid symmetrically put a whisker of
thread outside the artwork, which the first smoke run duly produced.

## Determinism

The classical path is the determinism reference: same bytes in, same shape
IDs, areas, and warnings out (`test_two_runs_of_the_same_input_are_identical`).
Stitch planning is deterministic on top of it: the same regions planned twice
produce byte-identical DST (`test_planning_the_same_regions_twice_gives_the_same_file`).
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
