---
name: ember-architecture
description: Ember Design (emberdesign.net) architecture teardown — the competitor EMB-Bot targets for parity
metadata: 
  node_type: memory
  type: reference
  originSessionId: dcdbce61-2eb2-453d-b902-e872146175cd
  modified: 2026-08-08T14:35:59.356Z
---

Teardown of Ember Design done 2026-08-08 from production bundles + logged-in editor.

Architecture: two Next.js apps. `emberdesign.net` is a shell (marketing, auth, project list,
**and the embroidery file codec**); the real editor is `v2.emberdesign.net` loaded in an
un-sandboxed `<iframe>` at `/editor/{authorId}/{projectId}`, handshake via `postMessage`
`EDITOR_READY`. Editor = PixiJS/WebGL + MobX + two Emscripten embind WASM modules (one exposes
Polygon/MultiPolygon geometry kernel). Backend is a thin AWS API Gateway
(`wejy3vhtrd.execute-api.us-east-1.amazonaws.com/Stage`, Bearer auth) doing only project CRUD,
versions, and presigned S3 upload/publish — **no stitch generation server-side**.

Auto-digitize (Pro-gated) = `POST /api/vectorize` returns SVG, then the client runs its normal
fill/satin engine. **No ML anywhere** — no ONNX/TF/OpenCV/weights. Fill angle heuristic is literally
`90 * (height >= width)`. That gap is EMB-Bot's opening, per [[emb-bot-digitizer]].

Their client-side codec writes pes/pec/dst/tbf/exp/jef/vp3/u01/xxx and its thread class mirrors
pyembroidery's `EmbThread` — usable as a second reference implementation to settle
[[dst-codec-axis-discrepancy]] in a steppable browser debugger instead of a sew-out.

Design ideas worth copying: fill patterns as data (`stitchPattern` → row offsets/patterns, 13
patterns 6 free/7 paid), `underlays[]` as an array from day one, versioned project document with a
migration chain (at v7+). Pricing: free manual tools / $9.99-mo Pro for automation.

Full report was written to the session scratchpad as `ember-teardown.md`.
