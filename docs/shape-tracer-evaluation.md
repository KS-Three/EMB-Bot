# Shape Tracer — Hands-On Evaluation

Evaluated whether shape-tracer's tracer feature (image → vector shape tracing) is solid enough to port into EMB-Bot's manual digitizing tool. Focus was the tracer only (not the image simplifier feature). Evaluation was hands-on: ran the live app in headless Chromium (Playwright), not just a source read.

## What was run
No build step — static HTML/JS/CSS served via `npx serve .`. Drove the live app end-to-end: clicked through the UI, dragged vertex handles, inserted points by clicking lines, adjusted sliders, and read the actual `editor.contours` state + exported SVG directly from the DOM. Repo left unmodified during testing.

## Test cases & results
- **6 shipped samples** (clean vector shapes: arches, ring+hole, twin circles, curvy swoosh, notch+crumb, overlapping ring) — all traced correctly on first try.
  - Arches: 12 pts/blob, threshold-invariant across 10-200.
  - Loop (ring with hole): outer 28pt + hole 17pt traced as separate editable contours.
  - Swoosh (curvy): 36pt smooth Bezier curve, tracks the concave inner curl well.
  - Bite (notch + separate crumb): correctly split into 3 contours (body / bite-hole / floating crumb).
- **Tolerance slider stress test** (Swoosh): tolerance=0 → 1543 raw jagged points (pixel-stairstep); tolerance=2 (default) → 36 pts, clean; tolerance=10 → 17 pts, visibly over-smoothed (lost a sharp notch). Real, visible smoothness/accuracy tradeoff — the shipped default lands in a good spot.
- **Self-generated noisy/low-contrast test** (mid-gray star on light-gray background + ~5500 random speckle pixels dithered across both background and shape): produced a single clean 13-point contour, with zero spurious noise contours across threshold values 20-80. The `MIN_AREA` speckle-rejection filter in the code works in practice, not just in theory.
- Confirmed the README's stated limitation is real: same-colored touching shapes trace as one merged contour (single background-distance threshold, not full color segmentation).

## Interaction model
Auto-trace on image load / slider change (not click-point-by-point digitizing), then direct manipulation:
- Drag any vertex handle — verified live, point coordinates update and curve reshapes instantly.
- Click on a line to insert a new vertex there — verified, point count incremented exactly at the click location.
- Vertices are plain points on a Catmull-Rom spline with **no per-point tangent/handle control** — dragging a vertex near a corner produces a sharp spike/kink rather than a smooth local bulge.
- Any re-trace (slider drag or button) discards in-progress manual edits and starts over.

## Verdict
The core algorithm (background-distance threshold → marching squares → Douglas-Peucker simplification → Catmull-Rom-as-cubic-Bezier smoothing) is solid in actual observed behavior, not just in code: clean high-contrast shapes trace almost perfectly with very few points, holes and multiple disjoint blobs are handled correctly as separate editable contours, and it's meaningfully robust to noise and low contrast thanks to the speckle-area filter.

For porting into EMB-Bot's manual digitizing tool: the auto-trace-then-adjust interaction model is a good fit as a "starting stitch path" generator, and the drag/insert-vertex editing is functional and responsive. Two gaps worth handling deliberately rather than porting as-is:
1. Same-color touching shapes merge into one contour — a digitizing tool will often need per-region control even when colors touch.
2. Vertex edits are raw points with no tangent handles, so fine curve control near sharp corners is limited.

Neither is a blocker — both are contained, well-understood gaps in an otherwise clean, working prototype.
