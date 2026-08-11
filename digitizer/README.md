# digitizer-core

Auto-digitizing engine for Fritsch's Stitches: flat artwork in, machine-ready
embroidery out. Python, independently testable, independently sellable — see
`docs/superpowers/plans/2026-07-29-digitizer-step1-skeleton.md` for the plan
this implements and the blueprint it comes from.

**Status: build steps 1, 3, 4 and 8 of 11 — stages 1–7, fill + satin, and the
service.** Artwork goes in and a sewable design comes out: background-masked,
thread-snapped, segmented and vectorized (step 1); sew-ordered, underlapped,
filled with underlay, sequenced with lock stitches, and exported (step 3);
ribbons — lettering, borders, thin strokes — sewn as satin columns along their
medial axis (step 4); and all of it reachable over HTTP, in the thread brand
the shop actually stocks, with machine files in nine formats (step 8).
`SHAPE_TOO_THIN_TO_FILL` means "thin but not stroke-like enough for satin":
compact slivers worth review-screen eyes.

SAM 2 segmentation (step 2) was deferred by Kent in favour of steps 3–4 — the
`Segmenter` seam means it drops in later without touching stitch code.
Preflight scoring (step 9, `digitizer_core/preflight.py`) and the EMB-Bot
review UI (step 10, `app/src/ui/DigitizePanel.svelte`) are both built too —
this paragraph used to list them as "still to come," which was stale. See
`docs/superpowers/plans/2026-07-30-digitizer-step4-satin.md` for the satin
design and `2026-07-30-digitizer-step8-service.md` for the service.

## Setup

```
cd digitizer
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"     # Windows
```

`textcluster.py`'s OCR-confidence quality gate needs the `tesseract-ocr`
system binary — a separate, non-pip install, the same reason `rembg_isolated/`
needs a model download step. Unlike `rembg`, this one wheel (`pytesseract`,
already in `dependencies` above) has no numpy/numba conflict with the shared
venv (its own deps are just `packaging` and `Pillow`, both already pulled in
transitively — confirmed via `pip show pytesseract` before it was added), so
it stays in the shared `digitizer/.venv` unisolated:

```
sudo apt-get install -y tesseract-ocr    # Debian/Ubuntu, incl. CI
brew install tesseract                   # macOS
```

Without it, `regularize_text_clusters`'s OCR gate degrades to a documented
no-op (`_ocr_confidence` returns `None`, the gate fails open) — the rest of
the pipeline, including the rest of text-cluster regularization, is
unaffected. Both `tesseract-ocr` and `pytesseract` are Apache-2.0. See
`textcluster.py`'s module docstring ("OCR-confidence quality gate") for what
this gate does and why the decoded text it reads is never touched, only a
confidence number.
`textcluster.py`'s OCR-suggested-text pass (Studio "Convert to text") needs
the system `tesseract-ocr` binary — a separate, non-pip install
(`pytesseract` is just a thin wrapper). `apt-get install tesseract-ocr` /
`brew install tesseract` / the Windows installer at
https://github.com/UB-Mannheim/tesseract/wiki. Missing it does not break the
pipeline — every OCR call fails open (see `textcluster.py`'s
`_ocr_glyph_guess`) — it just means every tagged member's OCR fields read
`None`, same as a below-threshold read, and Studio's "Convert to text" seed
always falls back to an empty textarea.

The optional SAM2 region former for photo-classified designs
(`cfg.photo_segment_sam2`) needs its own isolated venv plus a downloaded
checkpoint — `digitizer/sam2_isolated/README.md` has the build steps, the
disk budget and the by-hand sanity check. It is off by default and, without
it built, degrades to the classical SLIC+RAG region former with a
`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` warning — the job still completes and
nothing else in the pipeline changes.

## Run

```
.venv/Scripts/python -m pytest -q                   # 127 tests, all offline
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

## The service (build step 8)

```
.venv/Scripts/python -m pip install -e ".[service,dev]"
.venv/Scripts/python -m digitizer_service          # 127.0.0.1:8721
```

| Route | Does |
|---|---|
| `GET /health` | Is it running, which brands, which formats, what limits |
| `POST /digitize` | Artwork + config → a job id (202). Multipart: `image`, `config` |
| `GET /jobs/{id}` | `queued`/`running`/`done`/`error`; when done, `design` + `review` + `stats` |
| `POST /export` | Any EMB-Bot design + a format → the machine file |

`/digitize` returns an EMB-Bot **`Design`**, not a stitch file — see the DST
codec finding below for why that matters. `review` is the shapes-and-threads
half a review screen edits; `design` is the sewable half.

Resubmitting an identical request returns the finished job immediately: results
are keyed by sha256(artwork) + config, which is what makes a review screen's
"change one parameter" loop usable. Digitizing runs one at a time.

`config` accepts any `PipelineConfig` field except `debug_dir`, including
`thread_brand` — Studio's stored brand preference resolves here because the ids
are generated to match `app/src/lib/threadBrandsIndex.js` exactly, and a test
asserts they still do. An unknown brand is rejected rather than quietly
substituted, because the operator buys the cone the palette names.

Posture: binds loopback, no auth. Set `EMBBOT_SERVICE_TOKEN` and every route but
`/health` requires `X-EMBBOT-Token` — throw that switch before this listens on
anything but localhost.

Regenerate the thread charts after changing `tools/palettes/`:

```
.venv/Scripts/python tools/gen_charts.py
```

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
is +y **up**, so `adapter.py` owns that flip and is the only place one happens.
`test_coordinates_are_y_down_and_centered` makes a silent mirror in the
pipeline detectable; `tests/test_adapter.py` does the same for the boundary.

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
made on a theory would be reckless. Resolving it needs a sew-out or a third
opinion (any machine or viewer that is not either of these two
implementations).

**Build step 8 routes around it rather than betting on an answer.** The service
hands the browser a `Design` — the same structure `buildLetteringDesign`
produces — not a DST, so the disputed format never crosses the boundary and a
digitized design cannot arrive transposed. Studio bakes its own DST with its
own encoder if it wants one, which round-trips with its own decoder. Machine
files from `/export` are written by pyembroidery in the standard convention and
every response says so in `X-Stitch-Convention`; for DST specifically, Studio's
own encoder stays the default for lettering/manual designs, the one with sewn
evidence behind it, while projects made entirely of auto-digitized elements now
route through this service's `/export` instead. PES and JEF, the formats the
service exists to unlock, have no competing implementation and no conflict.

DST verification on this side still goes through pyembroidery, never through
the browser codec.

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

**Every shape starts where the needle already is.** `stitch_shape` and
`satin_shape` take a `start_near` point: the fill picks its first column
nearest it, a closed underlay edge walk begins at the nearest point of its own
ring, the fill then picks up from wherever the underlay finished, and satin
orders its strokes nearest-first. Stage 7 therefore settles the ORDER before
the geometry exists — on the distance from the needle to the sewing polygon,
which is the honest proxy for the hop. Generating first and ordering on the
result made every shape begin at its own top-left corner: on a row of tall
shapes the needle finished each one at the bottom and flew back to the top of
the next, 41 mm a time. A color also starts at an extreme of its group rather
than in the middle of it, because nearest-neighbour from the middle strands the
far end and pays for it with one long haul at the finish.

**Penetrations are staggered, and the stagger does not march.** Every row's
stitches are offset by a quarter of a stitch length, realigning every fourth
row. Which quarter matters as much as the size: taking them in order (0, 1, 2,
3) moves every penetration the same distance sideways as the rows step down, so
the holes line up along a diagonal — the channel tilted, not removed. The slots
come from the bit-reversal of the row index instead, so 4 staggers run
(0, 2, 1, 3) and no three rows in a row share a slope.
`stage6_penetrations.png` is the view that shows it.

**No stitch along a row is shorter than the needle minimum.** The interior grid
is anchored globally, so its first point inside a row lands an arbitrary
fraction of a stitch past the edge; keeping it whenever it merely cleared the
tiny-stitch floor put two penetrations tenths of a millimetre apart. An
interior penetration has to clear `MIN_STITCH_MM` against both neighbours or it
is skipped, and `split_long_moves` subdivides whatever gap that leaves. A whole
ROW shorter than the minimum still sews — at a tapering tip the only
alternative is to give up the edge.

**Satin for ribbons** (`stage6_satin.py`). Shapes whose ribbon width
(2·area/perimeter) is ≤ 5 mm and whose length is ≥ 3× that width sew as zigzag
columns perpendicular to a medial-axis spine, not as fill — the single
technique that most separates professional output from hobby output.
Classification runs on the ARTWORK polygon so fabric choice can never flip a
logo's structure; sewing runs on the stage-5 compensated one. The skeleton walk
stops at junction nodes and consumes pixels exactly once; collinear arms weld
into through-strokes (a T is a bar plus a yielding stem, never two half-bars);
free ends are first walked back OUT of the cap corner the medial axis runs into
— a flat cap's skeleton forks toward its corners, and crosses built on what
pruning leaves behind pivot on one needle hole and fan across the cap — then
extended to the cap edge, finishing with a square-end terminal cross;
`medial_axis(rng=0)` is REQUIRED — unseeded it is nondeterministic and the same
artwork digitizes differently run to run.

The satin numbers and structure follow a 19-file study of professionally
digitized DSTs (`tools/study_pro.py`, 2026-07-30; Kent's three commissioned
files plus sixteen from embroideres.com's free library, ~230k stitches):

- **Rails are parallel offsets** of the spine at a median-filtered, smoothed
  width profile — never independent per-sample ray hits, which is what made
  columns spray.
- **Corners sew THROUGH, in-run.** Corpus census: 1,436 corner events inside
  a continuing run, 18 splits. `_round_corners` spreads each apex over about
  one column width so the crosses fan gradually (the pro spoke pattern);
  `_split_sharp_corners` still exists but only fires past 90°.
- **Columns run to 5 mm wide** (was 3) — little-romeo runs 3.4/4.2, beckers
  4.2/5.1 — and anything past 2.5 mm forces zigzag underlay
  (`SATIN_ZIGZAG_ABOVE_MM`); wide corpus satin always shows support passes.
  The browser engine still classifies at 3 mm; the divergence is deliberate
  and Python-only until its own sew-out.
- **Between strokes the needle travels the unsewn skeleton web**
  (`_build_travel_graph` / `_graph_travel`): needle-down running along spines
  whose columns sew later and cover the leg — the corpus trick behind
  740-stitch runs and 0.8 trims per 1000. Legs over already-sewn strokes are
  forbidden (they would show); disconnected components still jump/trim with
  the same explicit decision as before, oriented to start at the end nearer
  the needle.

Two things the fill does that look wrong until you know why: row ends always
land exactly on the shape boundary (that is what makes an edge crisp, and the
0.4 mm row turn between them is a legitimate stitch, so the tiny-stitch filter
must not touch fill paths), and lock stitches only ever reach *into* a shape,
never past the point they tie at — ties laid symmetrically put a whisker of
thread outside the artwork, which the first smoke run duly produced.

## Open questions the renders cannot settle

Three things the stitch-quality review measured but did not change, because
each is a trade Kent has to see sewn rather than one a debug PNG can decide.

**Satin on a curve is under-dense on the outside.** Crosses are spaced along
the SPINE, but the thread lands on the RAILS, and on a bend the outer rail runs
further than the spine by (half-width x angle turned). Measured on a tight ring:
0.59 mm between outer penetrations against the 0.4 mm target, 47% short. Spacing
by the outer rail instead fixes that (outer starvation 0.26 mm -> 0.20 mm) but
drives the INNER rail straight into the short-stitch guard's 0.3 mm threshold,
where every other penetration is pulled off the rail — on a moderate ring that
made the inside edge worse (0.18 mm -> 0.30 mm) than it started. Which reads
worse on fabric is a sew-out question.

**The trim distance is 3.0 mm and almost every hop exceeds it.** On eight
filled letters, seven of the eight hops between letters are 4-13 mm — the
letter spacing itself — so each one is cut. That is Kent's "too many trims",
and the number lives in the fabric presets, which mirror `src/fabrics.js`
exactly. Moving it moves it for the browser engine too, and where a Tajima
should stop jumping and start cutting is his call.

**Fill angle is per shape, from the polygon's vertices.** Each region gets its
own principal axis, so a word of filled letters comes out a patchwork of
angles, and the axis is computed from the vertex cloud rather than the area —
`approxPolyDP` puts vertices where curvature is, not where the shape is.
`cfg.fill_angle_deg` already forces one angle on everything. Which default
Kent wants — per shape, per color, or one for the design — is a look, not a bug.

## Determinism

The classical path is the determinism reference: same bytes in, same shape
IDs, areas, and warnings out (`test_two_runs_of_the_same_input_are_identical`).
Stitch planning is deterministic on top of it: the same regions planned twice
produce byte-identical DST (`test_planning_the_same_regions_twice_gives_the_same_file`).
This is why stage 2 ships its own seeded k-means instead of `cv2.kmeans`
(whose RNG behavior across versions/thread counts is not ours to control),
and why `opencv-contrib-python-headless` is **exact-pinned** in `pyproject.toml` — a
minor bump can change clustering and silently invalidate the goldens. Bump it
deliberately, then re-check the fixtures.

Shape IDs have two mechanisms because one is not enough: a content-derived
hash labels new shapes, and `match_shape_ids()` carries IDs forward across a
regeneration by geometry matching. The service round-trips
`deleted_shape_ids` and per-shape `shape_overrides` (recolor, tier, fill
angle, border, sew layer — the shape-layers contract v1, applied by
`regions.apply_shape_edits`), and hashing alone churns when a value crosses a
quantization boundary — measured, not theoretical.

## Fixtures

`testdata/*.png` are generated, not found art (no licensing questions, known
geometry, so tests assert exact structure). Regenerate with
`.venv/Scripts/python tools/make_test_logo.py`. Each element earns its place:
a blob, a ring (hole preservation), a ~2 mm bar (satin candidate), touching
different-color rectangles, a sub-sewable patch (absorb path), an isolated
sub-sewable dot (drop path), anti-aliased edges throughout.
`ribbon_curve.png` is a second file for one job the flat logo cannot do: its
only ribbon is a straight bar, whose medial axis has no cap corner to run into,
so the satin cap defect had nowhere to show.

`tools/gen_charts.py` generates `chart_data/` — 68 manufacturer charts, 19,857
colors — from the repo's `tools/palettes/*.gpl`. Thread numbers and RGB values
are factual manufacturer data; each brand name is a trademark of its
manufacturer, used only to identify the thread line. The generator re-applies
the no-embroidery-software-companies policy by filename, so re-copying the
upstream palette set wholesale cannot quietly reintroduce a competitor's brand.

## License policy

Permissive dependencies only — MIT / BSD / Apache-2.0 / zlib. **No GPL or
AGPL, ever**; LGPL only as dynamically-linked binaries, which is why the
build uses `opencv-contrib-python-headless` (the non-headless `opencv-python`
/ `opencv-contrib-python` wheels bundle LGPL FFmpeg). Ink/Stitch (GPL-3.0) may be *read* to learn algorithms; no code
or data files are copied from it.
