---
name: sparse-nodes-spec-2026-11-04
description: Kent 2026-11-04 asked for Ember's few-smooth-nodes reshape on digitized rings; grilled spec (9 rulings), lib PR 1 then Studio PR 2; add-hole in, Knife out
metadata:
  type: project
---

**Kent, 2026-11-04,** after #1237 (bare drag exact, Done / Discard): "It's
better, but it's still not perfect." He asked for Ember Design's way of editing
nodes on photo shapes. Spec: `docs/superpowers/specs/2026-11-04-sparse-smooth-nodes-design.md`.

**The nine rulings, one line each:**
1. Nodes live Studio-side in `shapeOverrides[sid].nodes`, never on the wire.
2. Catmull-Rom through the nodes; a corner node breaks the tangent.
3. Untouched spans keep their original vertices; only spans at a changed node rebuild.
4. Seed by Douglas-Peucker 0.5 mm; corner when the turn exceeds 35 deg.
5. Sparse nodes everywhere; the dense vertex view is gone.
6. Insert is free (a corner on the outline); toggle and delete rebuild.
7. Flatten at 0.05 mm chord error, 0.3-1.0 mm spacing; over 500 points coarsen only the rebuilt spans.
8. Digitized rings only; the hand-drawn lane keeps anchors + handles.
9. Two PRs: lib (`app/src/lib/sparseNodes.js`), then Studio wiring.

Scope ruling the same evening: **add-hole in** (Studio only, after PR 2),
**Knife out** (needs the service to mint shapes with stable ids).

**Why:** a one-vertex exact move on a ring traced at 0.4-1.3 mm is a 1-2 mm
spike; Ember's edge is a curve between a FEW nodes, so one drag is one smooth
edit.

**How to apply:** PR 1 (the lib) and PR 2 (the Studio wiring, 2026-11-05, see
[[sparse-nodes-studio-2026-11-05]]) have both shipped; the Studio imports the lib, never re-implements it. A flat span
(within 0.05 mm of its chord) keeps NO interior vertices however long (the
spec's I5 needs it). Measured on the lib's fixtures: a rounded square at 5 mm
spacing seeds four corners (turns 36 deg, just over the 35 threshold), one per
rounded corner, not zero. See [[node-reshape-spec-2026-11-03]] and
[[ember-reshape-measured-2026-11-04]].
