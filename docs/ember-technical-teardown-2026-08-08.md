# Ember Design — Technical Teardown

**Target:** `emberdesign.net` / `v2.emberdesign.net` editor-v2
**Date:** 2026-08-08
**Purpose:** competitive analysis for EMB-Bot

Method: static analysis of production JS bundles (~7MB across both apps) + live inspection of the
logged-in editor. Everything below is observed from shipped code or the running app, not inferred
from marketing copy. Marketing claims are labeled as such.

---

## 1. TL;DR

Ember is **two separate Next.js apps**. The public site is a thin shell; the real editor is a
different app embedded in an `<iframe>`. The stitch engine is **client-side** (JS + two
Emscripten/WASM C++ modules) rendering through **PixiJS/WebGL**, with **MobX** for state.

The backend is remarkably thin — an AWS API Gateway doing project CRUD and S3 presigned uploads.
It does **not** generate stitches.

The single exception is auto-digitize: raster→vector tracing is a **server round-trip**
(`POST /api/vectorize` returns SVG), then all stitch generation happens back on the client.

**The headline for EMB-Bot:** Ember's "auto-digitize" is *image tracing* + their normal fill/satin
engine. There is no ML model, no learned stitch prediction, no fabric-aware reasoning anywhere in
the shipped code. That is the opening.

---

## 2. System topology

| Layer | What it is |
|---|---|
| `emberdesign.net` | Next.js App Router shell — marketing, auth, project list, **export/download** |
| `v2.emberdesign.net` | Separate Next.js app — **the entire editor**, loaded in an iframe |
| `v1.emberdesign.net` | Previous generation, still live |
| `wejy3vhtrd.execute-api.us-east-1.amazonaws.com/Stage` | AWS API Gateway, `Authorization: Bearer <token>` |
| `main.drno2am3t089h.amplifyapp.com` | AWS Amplify hosting origin |
| `api.racoons.ai` / `cdn.racoons.ai` | Third-party product analytics |
| Google Analytics | `G-D8E831FL33` |

### The iframe seam

The parent embeds:

```
<iframe src="https://v2.emberdesign.net/editor/{authorId}/{projectId}?new=true"
        allow="clipboard-read; clipboard-write; local-network-access; loopback-network; local-network">
```

No `sandbox` attribute. Handshake is `postMessage` with an `EDITOR_READY` message type.

**Notable split:** the embroidery file codec lives in the **parent** app, not the editor. The iframe
computes stitches; the parent serializes them into machine files and triggers the download. The
`local-network` / `loopback-network` permissions suggest an intent to talk to machines or a local
helper on the LAN.

### Backend API surface (complete)

```
/projects            /projects/           /versions
/upload/image/       /upload/embroidery
/save-urls           /download-url        /finalize
/publish-urls        /publish-finalize    /unpublish
/user/
```

That is the whole thing. Presigned-URL upload pattern (`*-urls` → PUT to S3 → `*-finalize`).
Project CRUD, versioning, publish/share. **No stitch generation endpoint.**

---

## 3. Editor internals

- **Rendering:** PixiJS (WebGL). The canvas lives in the iframe; the parent DOM has zero canvases.
- **State:** MobX.
- **Accessibility:** the editor's a11y tree is *empty* — fully canvas-rendered, no DOM semantics.
- **Compute:** two Emscripten **embind** C++ modules (1.67MB + 2.76MB of glue JS, plus `.wasm`
  binaries). One exposes `Polygon` / `MultiPolygon` types — a geometry kernel doing
  clipping/offsetting. The second module's symbols aren't in the glue; purpose unconfirmed.
- **Web Workers** used for `ImageBitmap` decoding off the main thread.
- **Undo/redo:** command pattern (`executeCommand`, `completeShapes`, `groupShapes`, …).

### Versioned document schema

The project document carries a `version` field with a **migration chain** — observed migrations
stepping v3→v4 and v6→v7, so the format is at v7+. Example: an early single `underlay` object was
migrated into an `underlays[]` array, backfilling `underlayContourCapInset: 2` and
`underlayZigZagCapInset: 2`.

Worth copying. It lets them refactor the stitch model without breaking saved projects.

---

## 4. The stitch data model

Pulled verbatim from the bundles. This is the parameter set EMB-Bot needs to at least match.

### Fill defaults

```js
{
  underpath: true,
  selectedFill: { id: "tatami", name: "Tatami", paid: false, stitchPattern: fn },
  handStitchIntensity: 0,
  gradient: null,
  startPoint: null, endPoint: null, center: null,
  underlays: [ { ...tatami, rowSpacing: 1, stitchSpacing: 4, angle: 225, insetMm: 0.4 } ],
  overlay:   { angle: 135, rowSpacing: 0.2, stitchSpacing: 4 }
}
```

Underlay sits 90° off the overlay (225 vs 135) and insets 0.4mm from the edge. Textbook, but note
they ship it as an **array** — multiple underlay passes are a first-class concept.

### Stroke / outline defaults

```js
{
  outlineType: "single",          // also: "satin"
  stitchLength: 1.5, width: 0.4,
  eStitchSettings: { width: 2, stitchLength: 1.5, isFlipped: false },
  satinSettings: {
    width: 2,
    density: 0.32,
    split: { enabled: true, maxWidthMm: 7,
             staggerEnabled: true, staggerCycles: 4, staggerAmountMm: 0.3 },
    underlays: [ { underlayType: "center", density: 1.5 } ]
  }
}
```

Satin auto-splits above **7mm** with a 4-cycle, 0.3mm stagger — that's their long-stitch guard.
Satin underlay defaults to `center` run.

Gradient fill: `{ type: "ramp", start: 0, end: 1, endRowSpacingMm: 1 }` — spacing interpolates
across the shape.

### Fill pattern catalog — 13 total, 6 free / 7 paid

Free: Tatami, Original, Columns, Offset Columns, Triangle, Waves
Paid: Zig-Zag, Spiral, Tornado, Staircase, Hexweave, Heartbeat, Rainfall

Patterns are data, not code — each is a `stitchPattern` function returning
`[{ rowOffsetMm, rowPatternMm }, …]`. A tatami stagger is just
`[{rowOffsetMm: t/4, rowPatternMm:[t]}, {rowOffsetMm: t/2, …}, …]`.

**This is a clean design worth stealing** — new fill patterns become table entries, not new
algorithms.

### Fill geometry

Classic scanline: intersect the polygon with row lines, sort crossings, dedupe within `1e-6`,
pair them into spans. Runs client-side in JS/WASM.

### Validation

Real guardrails with user-facing messages: row spacing > 0, stitch length > 0, gradient end row
spacing > 0, per-underlay checks ("Underlay 2 row spacing must be greater than zero").

### Editor tools

Select, Pan, Measure, Pen/node, **Closed Shape**, **Drawing Blocks** (manual satin columns),
tag/label, Text, alignment, **stitch simulator** (play), preview toggle.
Panels: Layers, ?, Image, Palette, Settings, Info.

---

## 5. Auto-digitize — how it actually works

Gated on `hasActiveSubscription`. Commands: `click-to-stitch`, `auto-digitize-all`,
`convert-to-redwork`, `break-apart-redwork`, `edit-gradient`, `split-svg`.

Pipeline:

1. Client fetches the uploaded image, normalizes it, wraps it in `FormData`.
2. `POST /api/vectorize` (Next.js API route on v2) with the image.
3. Server returns **SVG text**.
4. Client turns SVG paths into shapes, then runs the *normal* fill/satin engine over them.
5. Telemetry: `stitches_generated` with `method: "auto_digitize_all"`.

Error codes: `MISSING_IMAGE`, `INVALID_IMAGE`, `IMAGE_PREP_FAILED`, `VECTORIZE_FAILED`,
`FETCH_FAILED`, `UNKNOWN`.

Auto fill-angle heuristic, verbatim:

```js
let n = 90 * (t >= r);   // bounding-box aspect ratio → 0° or 90°
overlay.angle = n;
underlays[i].angle = (n + OFFSETS[i % OFFSETS.length]) % 360;
```

Fill angle is chosen purely from whether the shape is taller than wide. That is the entire
"intelligence" of their angle selection.

**No ML anywhere.** No ONNX, no TensorFlow, no model weights, no OpenCV, no learned anything —
in either app, initial or lazy chunks. `auto_digitize` = server-side raster trace + the same
deterministic fill engine a manual user would drive.

---

## 6. File format codec

Client-side, in the **parent** app (a lazily-loaded chunk). Reads and writes:

| Ext | Label | Machine |
|---|---|---|
| pes | PES | Brother |
| pec | PEC | Brother |
| dst | DST | Tajima |
| tbf | TBF | Tajima |
| exp | EXP | Melco |
| jef | JEF | Janome |
| vp3 | VP3 | Pfaff / Viking |
| u01 | U01 | Barudan |
| xxx | XXX | Singer |

Thread objects carry `rgb`, `name`, `brand`, `id`, `catalog`, `simpleColor`, with a full Brother
catalog embedded (RGB + catalog number, e.g. `(255,200,200) "Applique" #64`). The class shape
(`description` / `catalogNumber` / `brand` / `chart`) mirrors **pyembroidery's `EmbThread`** —
this looks like a JS port or close derivation of pyembroidery.

Relevant to your open DST question: this is an independent, shipping, JS-side DST writer you can
diff your bit table against. It's a second reference implementation next to pyembroidery, and it
runs in a browser you can step through. Worth using to settle the axis discrepancy before you
burn a sew-out.

---

## 7. Product, team, pricing

- Founded **2022** by **Cory Ortega** (software engineer, ex-Atlassian, computer graphics) and
  **Robert Guerra** (applied mathematician, iOS). **Matt Jacobson** joined for computational
  geometry and embroidery algorithms. Three people.
- Origin: couldn't find an affordable, beginner-friendly digitizer. Positioning is
  "lower the barrier to entry," free tier, community-driven.
- Has a Buy Me a Coffee page; YouTube reviews frame it as a **free Ink/Stitch alternative**.

### Pricing

**Free — $0:** all digitizing tools, 5 private + 10 published projects, 6 fill patterns, 25 fonts,
3 run types, all export formats, commercial use allowed.

**Pro — $9.99/mo** (yearly available): auto-digitize images, click-to-stitch, custom fonts
(TTF/OTF/TTC), unlimited projects, version history, autosave, 24 fill patterns, gradient fill,
7 run types, automatic redwork, priority support.

Note the marketing says 24 fill patterns; the shipped catalog I can enumerate is 13. Either the
count includes variants, or the page is ahead of the build.

**The monetization line is instructive:** the *manual* tooling is entirely free and unlimited in
capability. They charge for **automation and convenience** — auto-digitize, click-to-stitch,
fancy fills, unlimited storage.

---

## 8. What this means for EMB-Bot

**Where Ember is strong — treat as table stakes:**
- Client-side engine = zero marginal compute cost per design. Their backend is nearly free to run.
- Instant feedback, no round-trip on every parameter change.
- Data-driven fill patterns; multi-underlay arrays; versioned document with migrations.
- 9 export formats, client-side.
- Free tier that is genuinely useful — strong funnel.

**Where they're weak — your opening:**
1. **No ML, and their auto-digitize knows nothing about embroidery.** It traces an image and
   applies defaults. Fill angle is a one-line aspect-ratio check. There's no small-region handling,
   no satin-vs-fill decision, no pull-compensation reasoning, no fabric awareness, no stitch-order
   optimization. "Flat art in, pro out" is exactly the gap they left open.
2. **Vectorize is a server round-trip** — their one scaling cost and latency point.
3. **Tracing quality is their ceiling.** Their own error copy ("Try a different file format or a
   smaller image") admits fragility.
4. **Zero accessibility** — canvas-only, empty a11y tree.
5. **Underlay is defaults-driven,** not derived from geometry or fabric.

**Concrete things to copy:**
- Fill patterns as data (`stitchPattern` returning row offsets/patterns).
- `underlays[]` as an array from day one — they had to migrate to it.
- Versioned document + migration chain.
- Presigned-URL upload flow.
- Free manual tools / paid automation split.

**Strategic read:** matching Ember's editor is a large but well-understood build. Beating them
means the auto-digitize output being *actually sewable* without cleanup. They have deliberately not
gone after that — three people, and their expert is a computational-geometry person, not an ML one.

---

## Appendix — artifacts on disk

Downloaded bundles under the session scratchpad:

```
ember/           parent app chunks (+ lazy/1457.js = the format codec)
ember/v2app/     editor app chunks (+ lazy/, ed/ = editor-route chunks)
```

Notable files: `v2app/ed/editor-page.js` (424KB, command layer + auto-digitize),
`v2app/ed/4191-*.js` (289KB), `v2app/5d5fe377-*.js` + `v2app/6a29ceff-*.js` (WASM glue),
`ember/lazy/1457.js` (format codec + Brother thread chart).
