---
name: sparse-nodes-studio-2026-11-05
description: PR 2 of sparse smooth nodes shipped: Studio draws/drags/inserts/toggles/deletes nodes on digitized rings, `nodes` in shapeOverrides; seeds measured on real fixtures; PointerEvent.detail is 0
metadata:
  type: project
---

**What shipped (2026-11-05, PR 2 of [[sparse-nodes-spec-2026-11-04]]).** The Studio
shows a selected digitized shape's NODES only (disc = smooth, square = corner),
in the quick drag and in Reshape. `app/src/lib/shapeNodes.js` holds the glue
(`nodesForShape`: stored valid list wins, else seeds; `withNodes`; `spanOfEdge`;
`ringEditOverrides`, moved out of `EmbroideryField.svelte` so it can be unit
tested; `discardPatch`). A node drag / nudge / delete / toggle goes through
`sparseNodes.js` (`moveNodesExact` + `rebuildSpans`), commits ONE `elupdate`
with `shapeOverrides[sid].nodes` beside the polygon. Click on the path (Reshape)
inserts a corner (no rebuild); double-click a node toggles; Alt-drag stays the
soft pull. `nodes` never reaches the wire. Canvas attrs for e2e:
`data-reshape-nodes` (count), `data-reshape-node-px` (Reshape only).

**Seeds on the real fixtures (e2e, 0.5 mm / 35 deg):** red-disc.png (198 mm, 64
vertices 9.7 mm apart) -> **44 smooth**, not the spec's 8-16 (the count follows
ring size at a fixed tolerance; offline 1 mm 32, 2 mm 21, 3 mm 16); two-squares
-> **4 corners** each; holed fixture -> **4 corners shell, 4 corners hole** (hole
has 8 traced vertices; 8 -> 6 after one node moved). Kept 0.5 / 35.

**Traps found:** (1) `PointerEvent.detail` is ALWAYS 0 (pointerdown:0
mousedown:2 click:2 on a double click), so the old `e.detail >= 2`
double-click-edge-insert in `onPointerDown` never ran; the Studio now counts
presses itself (`countPress`, 450 ms / 6 px). The cap `wantsCap` line still
reads `e.detail` (dead, left alone). (2) A rebuilt span is re-flattened at
0.3-1.0 mm, so a node dragged on a sparse ring GROWS it (red-disc 64 -> 108; a
smooth node pulled 18 px on a 5-vertex edge -> 131). (3) A smooth node inserted
between two corners on a straight edge stays straight (collinear tangents, I5):
the spec's "its two spans now carry vertices" only holds once it is pulled off
the line. (4) The element's selection handles overdraw corner nodes: aim from
`data-reshape-node-px`, not from pixels. (5) A click that never moved no
longer commits (quick path used to write an identical override).

**How to apply:** extend nodes through `shapeNodes.js` / `sparseNodes.js`; any
new writer of `boundary_override` / `holes_override` must pass `liveNodes`
(null deletes `nodes`). Add-hole is next (PRODUCT.md), on `ringEditOverrides`.
