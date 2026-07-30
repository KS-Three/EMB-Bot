# Digitizer Step 8 — The Service (localhost FastAPI + universal export adapter)

Blueprint: Kent's Auto-Digitizing Engine Blueprint v2.1 + the v2.2 amendments
(2026-07-29). Builds on steps 1, 3 and 4 (`2abb876`).

## Why this step now

Steps 1–4 made the engine produce professional stitches. Nothing can *reach*
it: it is a Python library on a laptop and the product is a browser app. Step 8
is the seam. It also collapses market-launch item #1 (harden PES, add JEF),
because pyembroidery writes 19 formats and every EMB-Bot design — text,
imported, or digitized — can go out through one adapter.

## Scope

In scope:

1. **Thread-brand seam.** `/digitize` honours EMB-Bot's brand preference
   instead of hardcoding Isacord (pinned rider, 2026-07-29). Charts for all 68
   policy-allowed brands, brand ids identical to the browser's.
2. **The browser adapter** (`adapter.py`) — `StitchPlan` ⇄ EMB-Bot `Design`.
   This is where the y-axis flip lives, and nowhere else.
3. **`POST /digitize`** — async job, content-hash cache, artwork in, a `Design`
   out.
4. **`GET /jobs/{id}`** — poll.
5. **`POST /export`** — the universal adapter: any EMB-Bot `Design` in, any
   pyembroidery format out.
6. **`GET /health`** — is the engine there, what can it do.
7. Localhost-only posture, with the shared-secret seam built but off.

Explicitly NOT in scope: SAM 2 (step 2), the stitch processor, preflight
scoring (step 9), the EMB-Bot review UI (step 10), hosting, auth beyond the
token seam, GPU.

## The axis decision (the load-bearing one)

There is an unresolved disagreement in this project: EMB-Bot's `src/dst.js`
puts x in the high nibble of a DST record and y in the low nibble; pyembroidery
and the published Tajima table do the opposite. Evidence favours pyembroidery
(a professionally digitized third-party hat file reads as landscape 101.9 ×
62.1 mm through pyembroidery and as portrait through `decodeDST`), but Kent has
**sewn** browser-written DSTs on his Tajima, so something reconciles it on real
hardware and nobody has run the sew-out that would settle it.

The naive integration — service writes DST, browser reads it with `decodeDST` —
walks straight into this. It would return every digitized design transposed.

**So no DST crosses the service→browser boundary.**

`/digitize` returns a `Design` in the browser engine's own contract:
`{stitches:[{x,y,type}], colors:[{r,g,b,name}], widthMM, heightMM}`, integer
0.1 mm units, **+y UP**. Studio then treats a digitized result exactly like a
lettering or imported design — preview, combine, resize, and export all work
unchanged — and if it wants a baked DST for offline persistence (amendment 4)
it bakes it with its own encoder, which round-trips with its own decoder.

Consequences, all good:

- The codec disagreement cannot corrupt the integration path, because the
  disputed format is not on it.
- The y-flip is one function with a golden test, not a convention smeared
  across two languages.
- Step 10 becomes wiring. The adapter it was supposed to own is built here.

`/export` still writes real machine files, in pyembroidery's standard
convention, and says so: `/health` reports each format's convention and the
export response carries it. DST stays available there (the digitizer's own
direct-to-machine path from step 3 uses it) but **Studio's DST default remains
the browser encoder** — that is the path with sew-out evidence behind it. The
formats step 8 exists to unlock, PES and JEF, have no competing implementation
and so no conflict.

Do not "resolve" this by transposing coordinates to match the browser. That
buries a disputed convention one layer deeper. It gets resolved by a sew-out.

## Thread charts

`tools/palettes/*.gpl` (68 files, 0.97 MB) is already the policy-filtered set.
`tools/gen_charts.py` parses them into `digitizer_core/chart_data/*.json` plus
an `index.json`, re-applying the software-company exclusion by filename so a
wholesale re-copy from upstream cannot reintroduce a competitor's brand.

Brand ids **must** equal the browser's, because Studio sends its stored
`embstudio:threadPalette` preference straight to `/digitize`. The id rule
(`InkStitch Foo Bar.gpl` → `foo-bar`, with four legacy overrides) is mirrored
from `tools/build-threads.mjs` — and mirroring is not trusted: a test asserts
the Python brand-id set and each brand's colour count equal
`app/src/lib/threadBrandsIndex.js`. That test is the guard against the two
parsers drifting.

`threads.py` grows a `Chart` object (threads + precomputed Lab + nearest/snap),
`load_chart(brand_id)` behind an LRU cache, and `chart_for(cfg)`. Every call
site that reads the global `CHART` already receives `cfg`, so the change is
mechanical. `CHART` stays as the eagerly-loaded default so existing imports and
goldens are untouched.

## Service shape

Single-worker `ThreadPoolExecutor`. The pipeline is CPU-bound and takes tens of
seconds; running two at once on a laptop makes both slower and neither
finishes, so requests queue.

`POST /digitize` (multipart: `image` + `config` JSON) → `202 {job_id, cached}`.
The cache key is sha256(image bytes) + the canonical JSON of the resolved
config. A hit returns the finished job immediately — this is what makes the
review screen's "change one parameter" loop bearable, and what amendment 3
asked for.

`GET /jobs/{id}` → `{state, design?, review?, warnings, stats, error?}` where
state is `queued|running|done|error`. `review` is the shapes-and-threads half a
review screen edits; `design` is the sewable half.

Limits, because this accepts an upload: 12 MB request cap, 40 MP pixel cap
(stage 1 upscales, and a huge input turns a 44 s job into minutes), 32-entry
result cache with oldest-out eviction so a long session cannot grow unbounded.

`POST /export` (JSON: `design`, `format`, optional `label`) → the file bytes.
Stateless, synchronous, fast — it is a format conversion, not a digitize.

Posture: binds 127.0.0.1. If `EMBBOT_SERVICE_TOKEN` is set, every route except
`/health` requires it in `X-EMBBOT-Token`; unset (the localhost default) means
no check. CORS allows `http://localhost:*` and `http://127.0.0.1:*` only — not
`null`, which would be every `file://` page on the machine.

## Verification

Smoke-test before writing tests. That ordering has found 5, 4 and 11 real
defects in steps 1, 3 and 4 respectively, all of which the tests written
afterwards would have happily pinned as correct behaviour.

Goldens that must exist on day one:

- **Axis round-trip**: a `StitchPlan` with a known asymmetric point → `Design`
  → back → same geometry, and the y sign provably inverted between them.
- **Orientation**: a plan that is wider than it is tall stays wider than it is
  tall through the adapter, and through `/export` read back by pyembroidery.
- **Cross-language brand ids**: Python chart index == the browser's.
- **Design contract**: `/digitize` output validates against the same shape
  `buildLetteringDesign` produces (types, units, colour records).

## What was built, and what it found

Done: chart seam (68 brands, ids verified equal to the browser's), `adapter.py`,
all four routes, 55 new tests (68 → 123 green).

Defects found by smoking before writing tests — the fourth time in four steps
that ordering has paid:

1. `OrderedDict.move_to_end` was passed the `Job` rather than its id, so every
   `/jobs/{id}` poll raised `TypeError: unhashable type`. The route had no test
   yet; it would have been written against the broken behaviour.
2. The first run of a design emitted no jump, leaving the encoder to synthesize
   the opening travel out of an oversized delta. `buildQualityDesign` emits it
   unconditionally; now so does the adapter.
3. `widthMM`/`heightMM` came from the plan rather than the records actually
   emitted, so a design could report a size its own stitches did not span.
4. `MAX_PIXELS` was declared and never checked. It now runs at submit time, off
   a single decode whose array is handed to the pipeline rather than decoded
   twice.
5. `stats.trims` over-reported by one on every design: the plan marks the first
   run of each colour block trimmed, but the first block has no thread to cut
   yet. A fifth of the total on a five-colour design. Service stats now count
   the delivered design.

Performance (`resolve_small_regions`, found by profiling a real logo): matching
a sliver's one-pixel halo against a neighbour ANDed two full masks together,
which on a 654-sliver logo was thousands of whole-image scans — two thirds of
stages 1-4. Windowed to the sliver's own bounding box, with a bbox-overlap
rejection and a carry-forward of the absorbing region's box as it grows.
**7.03 s → 3.12 s on a real logo, output byte-identical** (fingerprinted
before/after across shape ids, areas, centroids, warnings and every stitch
coordinate). k-means now dominates what remains, and is left alone: it is
inherently the expensive part and touching it moves cluster goldens.

## Follow-ups this step deliberately did not take

- **Poor-match warning when a brand has no close colour.** Switching brands is
  honest — every match verified as genuinely nearest — but Madeira Rayon's
  closest purple to the test artwork is ΔE 12.2, an obviously different colour,
  and nothing says so. It belongs with step 9's preflight scoring where it can
  be weighed against everything else rather than becoming another warning users
  learn to scroll past. Worth doing before the brand picker reaches the UI.
- **The DST convention still needs a sew-out.** Unchanged by this step, and now
  routed around rather than resolved.
- Progress reporting per stage (`/jobs` returns queued/running/done only).
