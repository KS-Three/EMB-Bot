# External sourcing sweep — libraries and new digitizers, 2026-11-06

Kent asked (11-06, after NVIDIA/auto-ontology came up and was ruled irrelevant —
it is a text-to-SQL layer over data warehouses): *"look on GitHub or other open
source code sites to see if there are any repos that would benefit this project."*

Two sweeps already exist and are NOT repeated here:
[`external-repo-sourcing-2026-09-12.md`](external-repo-sourcing-2026-09-12.md)
(86 candidates, 12 installed and run — fonts, FLIP, routing, tracers) and
[`free-digitizer-survey-2026-11-04.md`](free-digitizer-survey-2026-11-04.md) (40+
digitizers, Tier-1 bench of heatstitch / Nuizu / openstitch). This one asks a
narrower question: **what has appeared or changed since, and which live defect or
measured bottleneck would it serve.** Candidates were chosen from the live defect
list (`MASTER_SCOPE.md`) and the speed memos, not from a keyword crawl.

Legend as before: **[V]** verified against the primary source this session ·
**[M]** measured this session · **[U]** not verified.

## 1. The verdict

**One thing worth adopting, and it is measured: `tesserocr`.** EMB-Bot reads
Tesseract through `pytesseract`, which spawns `tesseract.exe` and round-trips a
PNG per call. In-process, the same read on the same tessdata costs **5 ms instead
of 251 ms** — the eight OCR call sites (lettering tagger, legibility gate,
calibration reader) are the only measured speed lever this sweep found that needs
no new idea. Everything else is a reference to read, a trigger to watch for, or a
DST to bench — the same shape as the two earlier sweeps, and for the same reason:
the engine's gaps are discrimination problems (satin vs fill at kappa 0.387, the
photo lane's merge, the pot's palette), and no library ships a discriminator.

## 2. Verdict table

| Candidate | Licence [V] | Verdict | Serves |
|---|---|---|---|
| `tesserocr` 2.12.0 | MIT | **ADOPT** — measured 45–50x per read | OCR cost in stages 1.25 / 7 and preflight |
| `clipper2-ts` 2.0.1-18 | BSL-1.0 | **PROTOTYPE on trigger** | defect 55's open offset half (`offsetRing`) |
| filum, Lilo, Roidery | GPL-3 / GPL-3 / MIT+Apache-2.0 | **BENCH the DST** (filum, Lilo); Roidery readable | Tier-1 free-digitizer board |
| `bezier-js` 6.1.4 | MIT | **REFERENCE only** (stale since 2024-08) | sparse-node editing math |
| `skan` 0.13 | BSD-3-Clause | **WATCH** | skeleton-graph plumbing, not discrimination |
| RapidOCR | Apache-2.0 code, **Baidu-owned models** | **WATCH** | text LOCATION misses (MFab IN / AND) |
| BiRefNet via rembg | MIT | **Not a repo add** — `photo_prep_background_removal_model` seam exists | photo cut-out keeping 0.01–5.4 % |
| `fit-curve` 0.2.0 | MIT | **REJECT** (2020, and it would move node placement Kent already ruled on) | — |
| kaanyaren/Pantone thread palettes | **none** | **REJECT** (no licence, no provenance, 2 days old) | — |
| Wu / median-cut quantizers | n/a | **REJECT** — nothing on PyPI; `patolette` pre-release + patent note | pot slot swing stays in-house |
| straight-skeleton libs | unverified | **REJECT** — no maintained permissive port; CAT already rejected 09-12 | — |
| tatami.ninja, vektortool, ishaan-skyacres/embroidery, openhoop, EdenBord | none / none / none-vs-GPL / GPL-3 / GPL-3 | **SKIP** | — |

## 3. `tesserocr` — ADOPT, measured

**What it is.** [V] A Cython wrapper over the Tesseract C++ API (sirfz/tesserocr,
2,181 stars, pushed 2026-11-03, MIT). Version 2.12.0 (2026-10-22) ships wheels
that **bundle Tesseract 5.5.3 and Leptonica 1.87** for Windows x64, manylinux and
macOS, CPython 3.9–3.15 including a `cp314` wheel — so the Python 3.14.6 venv on
Kent's box and the 3.12 cloud venv both get a binary wheel. Language data is not
bundled; the API takes a `path=` to any tessdata directory.

**Why it matters here.** The digitizer calls `pytesseract.image_to_data` from
eight sites: `textcluster.py` (5, the glyph tagger at `--psm 10` and the
word reads), `legibility.py` (2, the OCR-confidence gate) and
`calibration/reader.py` (1). Each call spawns `tesseract.exe`, writes a PNG,
parses TSV. The 2026-10-26 speed memo got 2.3–2.8x on preflight by batching those
spawns 4 at a time; that is a workaround for process start-up, not a fix.

**[M] Measured this session** — `becker_chest_small_beckers_logo_lc_2_a.jpg`
cut into 48 tiles (W/8 × H/6, standing in for per-glyph crops), same
`C:\Program Files\Tesseract-OCR\tessdata`, `OMP_THREAD_LIMIT=1`, one warm read
discarded, laptop otherwise idle. Script: scratchpad `time_ocr.py` (not kept —
30 lines, reproduced from this table in minutes).

| psm | pytesseract (subprocess) | tesserocr (in-process, one `PyTessBaseAPI`) | ratio |
|---|---|---|---|
| 10 (single glyph) | 12.06 s / 48 = **251 ms per read** | 0.25 s / 48 = **5 ms per read** | 48x |
| 7 (single line) | 8.86 s / 48 = **185 ms per read** | 0.21 s / 48 = **4 ms per read** | 42x |

On the one tile that held a clean glyph ("4") both engines read it at 93 vs 94
confidence. The other tiles cut through letters and read as noise in both, so
text agreement across the set (13/48) says nothing about accuracy — it says the
tiles are garbage. A proper accuracy check is the lettering board's cc column,
below.

**The catch, and it is real: a third Tesseract version.** Kent's box runs 5.4.0,
CI's `apt tesseract-ocr` is 5.3.4 (`COOKBOOK.md`), and the wheel bundles 5.5.3.
Every OCR-derived number — the lettering board's cc, legibility confidences, the
`glyph_ocr` tags — will move by some amount on the switch, in both environments
at once (which is the one good side: box and CI finally read with the SAME
engine). So the adoption is: swap the eight sites behind one helper that holds a
per-thread `PyTessBaseAPI` (the GIL is released during `Recognize`; one API per
worker, which is exactly what `_one_tesseract_thread()` already assumes), run the
lettering board (`--compare`) before and after, re-pin the OCR goldens, and keep
`pytesseract` as the fallback when the wheel is absent. Half a day plus the
re-pin. **Nothing here touches a ROADMAP gate.**

**[M] ADOPTED 2026-11-06, same PR as this doc.** `digitizer_core/ocr.py` holds
the one `PyTessBaseAPI` per thread; the eight sites call it; `EMB_OCR_ENGINE=
pytesseract` is the before/after lever. What the switch measured on Kent's box:

- *Full digitizer suite* (1 h 51 m, `-n auto`, box loaded by two other sessions):
  7,214 passed. Red: the two named goldens (`enthusiast_logo` flat-lane and
  stage-2; `test_pushcomp` passed), eight `test_tools_help` 30 s timeouts that
  pass alone (279/279), and three MFab under-fill tests
  (`test_underfill_small_size` 60/113.5, `test_underfill_untagged_riders` 113.5)
  that fail the SAME way with `EMB_OCR_ENGINE=pytesseract` — grade C under the
  B floor, the riders list — with the failing sweep width moving 113.5 ↔ 100.8
  between engines. Box-level, not the engine; CI arbitrates.
- *Lettering board, old engine → new, 41 pairs at the pro's size* (two caches,
  since digitization itself reads OCR in the glyph tagger): columns, stitches,
  trims inside letters, satin width and rail wobble **identical in every band**.
  Only the reading figures moved: word-legibility cc ALL <4 +0.96 → +0.88, all
  of it one precision_drone word (1/1, +1.00 → 0.00); 4–6, 6–10 and 10+ within
  0.01; reach ALL +0.01 to +0.07 octaves. Meta: `tesseract v5.5.3 (tesserocr
  2.12.0, in-process)` against `v5.4.0 (pytesseract, subprocess)`.
- No golden on the box needed a re-pin. CI's first run with the wheel (5.5.3
  replacing apt's 5.3.4) is the other half of that check.

## 4. `clipper2-ts` — PROTOTYPE on trigger

[V] Native TypeScript port of Angus Johnson's Clipper2 (countertype/clipper2-ts,
BSL-1.0, 42 stars, npm 2.0.1-18 of 2026-07-04, zero dependencies, repo pushed
2026-11-06). Its README claims 194/195 of the reference polygon tests pass, the
one failure shared with the C# reference. Offsetting is `inflatePaths`; it runs on
`Number`, so coordinates must be scaled to integers (mm × 1000 is plenty).

**Where it would go.** The BROWSER engine's `offsetRing` in `src/digitize.js:581`
is home-rolled; defects 54 and 55 were both wedge artefacts from it, and defect 55
still says *"the offset is not [cured], so saved shapes keep theirs."* Shapely
does this job in Python; the browser has nothing equivalent.

**Why not now.** The engine is copied, not imported (`ENGINE_FILES` in
`app/scripts/copy-engine.mjs`): a dependency means vendoring a built single-file
bundle into `src/` and `ENGINE_FILES`, under the no-module-system rule. That is a
day, and it buys nothing until an offset bug the `distinctCorners` fix did not
catch shows up. **Trigger:** the next wedge, spike or self-intersection traced to
`offsetRing`. Then this, not another special case.

## 5. New digitizers since the 11-04 survey

The 11-04 survey's conclusion stands — *no free tool beats ours, none compares to a
pro file, GPL/no-licence engines are bench-the-DST-only.* Five engines appeared
or moved in the four weeks since; `gh api` figures as of 2026-11-06.

| Repo | Licence [V] | Stars / pushed | What it is | Verdict |
|---|---|---|---|---|
| **benkl/filum** | GPL-3.0-or-later (ports Ink/Stitch) | 1 / 2026-11-06 (created 11-04) | Rust→WASM port of Ink/Stitch's engine + auto-digitize (Logo / Patch / Line art / Photo presets), knockdown, stitch-order optimisation, 134 Ink/Stitch fonts, Tauri desktop; DST/PES/JEF/EXP/VP3/XXX/U01 | **Bench its DST when a release exists** — the first way to run Ink/Stitch's full engine on a raster without Inkscape. Clean-room: never read the source. |
| **Kadwood/lilo** | GPL-3.0 | 3 / 2026-10-05 (created 10-03) | Tauri + TS; rules: <1 mm → run, ≤~7 mm → satin from the STRAIGHT SKELETON, else tatami + underlay; Brother thread snap; vtracer + image-q under it | Stalled after two days. Rules identical to heatstitch's; bench only if it revives. |
| **lork-fork/Roidery** | **MIT OR Apache-2.0** | 13 / 2026-10-20 (created 10-14) | Pure Rust, Illustrator-style; Image Trace → tatami shapes, "Convert to Satin" along centreline; 8 writers; no release, build from source (Rust ≥1.95), 12 commits | The ONLY permissive engine in the field — readable. But 12 commits of a vector editor; nothing in it is ahead of `columns.py`. Reference, not bench. |
| theanam/tatami.ninja | **none** (no LICENSE file = all rights reserved) | 2 / 2026-10-17 | Browser TS digitizer on Clipper; SVG → fills / runs / satin borders; photo stitch and cross stitch from a picture | Skip. |
| ishaan-skyacres/embroidery | README says GPL-3.0-or-later; GitHub reads none | 0 / 2026-10-13 | Vector-only (SVG/AI/EPS/PDF → DST) for a Poolin EOC06; classifier <1.5 mm run, ≤7 mm satin, blobs ≤10 mm satin-fill, else tatami 30° apart; Claude-built, single branch | Skip — vector input, and the same width table everyone copies. |
| EvenDog/openhoop, jcontrerasf/EdenBord, ljuokr/vektortool, linker2k/myembro | GPL-3 / GPL-3 / none / GPL-3 | 6, 1, 1, 0 | Swift Mac app, Rust JEF editor, HTML tracer, Android PES viewer | Skip. |

**The pattern worth recording:** every 2026 entrant uses the SAME width table
(run under 1–1.5 mm, satin to 7 mm, fill above) and none measures against a
professional file. heatstitch scored sttype kappa 0.13 against the pro with that
table on 11-04; ours scored 0.38. A sixth copy of the table is not a competitor.
What filum adds that the others do not is Ink/Stitch's post-processing (knockdown,
order optimisation, hidden-stitch removal), which is why its DST is worth a row on
the free-digitizer board and the rest are not.

## 6. Watched, with the trigger named

- **`skan`** — [V] BSD-3, 153 stars, pushed 2026-10-26. Skeleton → graph with
  per-branch pixel-exact lengths and junction typing. EMB-Bot already walks
  skeletons with networkx (`_graph_travel`, `thin_strokes`, `classify_ribbon`),
  and DOCTRINE records that spur pruning collapses compact shapes — the library
  would swap plumbing, not add a discriminator. **Trigger:** a skeleton-graph bug
  that costs a session; then compare, don't rewrite.
- **RapidOCR** — [V] code Apache-2.0 (RapidAI/RapidOCR); the README states the
  OCR models' copyright is Baidu's (PaddleOCR lineage), so model terms need the
  `hf-hub-check` kind of read before anything ships. Its DB text DETECTOR finds
  words in logo art where tesseract's psm sweeps do not; it would serve text
  location, not recognition. Pulls in `onnxruntime`. **Trigger:** the tagger's
  remaining misses (MFab's IN and AND N, 10-25 memo) proving to be location, not
  classification.
- **`bezier-js`** — [V] MIT, 1,873 stars, but last pushed 2024-08-04 with 67 open
  issues and an npm release from 2023. `sparseNodes.js` already has `bezierAt`,
  `flattenSpan`, `insertNodeOnPath`; what bezier-js has that it lacks is an exact
  `project()` (closest point on curve) and `split()`. Read the algorithm if
  insert-on-path ever needs sub-pixel accuracy; do not vendor a stale package.
- **BiRefNet** — [V] MIT (ZhengPeng7). Not a repo add: `config.py:796` already
  documents `birefnet-general-lite` as the quality tier behind
  `photo_prep_background_removal_model`. The 10-28 cut-out memo measured
  isnet keeping 0.01–5.4 % of scenes; flipping the existing knob is a flag
  experiment, not sourcing.

## 7. Confirmed empty — do not repeat

- **PyPI colour quantizers.** No Wu / minimum-variance quantizer on PyPI;
  `patolette` is C/Python, not released, slow by its own README and carries a
  patent warning for commercial use. Stage 2 keeps its own k-means on purpose
  (determinism, `stage2_quantize.py` docstring) — the pot slot swing is a palette
  question for OUR code.
- **Straight-skeleton libraries.** `polyskel` and its ladybug fork carry
  all-rights-reserved copyright lines; `weighted-straight-skeleton` wraps CGAL
  (GPL) in WASM; no 2026 activity anywhere. Lilo uses one — under GPL.
- **Thread-colour chart data.** kaanyaren/Pantone (9,149 rows across Madeira /
  Durak / Pantone, CIEDE2000 matching) has no licence and no stated source; chart
  data scraped from manufacturers is exactly what a public repo should not vendor.
  `threads.py` already carries Isacord and Madeira.
- **GitHub `embroidery` topic, sorted by update.** 20 repos touched in the first
  week of November; all are in §5 or are cross-stitch / pattern tools.

## 8. Kent's decision queue

1. ~~**`tesserocr`**~~ — **done** (Kent 11-06 "Adopt tesserocr + PR"; §3 has the
   before/after). Open from it: if CI's first run under the wheel moves an OCR
   golden, re-pin it in that PR, not a follow-up.
2. **filum on the free-digitizer board** — add a Tier-1 row when it publishes a
   release (bench the DST only; GPL clean-room)? An hour with
   `bench_free_digitizers.py`.
3. **`clipper2-ts`** — agree the trigger (next `offsetRing` artefact), or
   prototype now?

## Sources

tesserocr: https://pypi.org/project/tesserocr/ · https://github.com/sirfz/tesserocr ·
clipper2-ts: https://www.npmjs.com/package/clipper2-ts · https://github.com/countertype/clipper2-ts ·
bezier-js: https://github.com/Pomax/bezierjs · https://pomax.github.io/bezierjs/ ·
fit-curve: https://www.npmjs.com/package/fit-curve · skan: https://github.com/jni/skan ·
RapidOCR: https://github.com/RapidAI/RapidOCR · filum: https://github.com/benkl/filum ·
Lilo: https://github.com/Kadwood/lilo · Roidery: https://github.com/lork-fork/Roidery ·
tatami.ninja: https://github.com/theanam/tatami.ninja · https://github.com/ishaan-skyacres/embroidery ·
https://github.com/kaanyaren/Pantone · https://github.com/big-nacho/patolette ·
https://pypi.org/project/ladybug-geometry-polyskel/ · https://github.com/topics/embroidery?o=desc&s=updated
