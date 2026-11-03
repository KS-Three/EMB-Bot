---
name: holes-studio-2026-11-03
description: Studio half of contract v1.9 — holes drawn as rings, edited under every node rule, deleted whole, holes_override sent only when a hole was edited; no add-hole yet
metadata:
  type: project
---

PR 4b of the node-reshape spec ([[node-reshape-spec-2026-11-03]]), on the service half in [[holes-override-2026-11-03]].

`reviewFromJob` reads `holes_mm` -> `holesFull`; each hole is a ring tagged `{ id, ring: k, key: "<id>#h<k>" }` and edits under every rule of the spec (3 mm drag, Alt soft, marquee, arrows, Delete, Simplify). All points of one hole selected + Delete, or "Delete hole" in the node menu, removes it (`holes_override: []`). **No add-hole yet.**

**Wire rule:** `ringEditOverrides` (EmbroideryField) writes `boundary_override` only if the SHELL moved and `holes_override` (all current holes) only once a hole was edited; an exterior-only edit stays byte-identical. A hole-only edit sends no `boundary_override`.

**Measured** (real service from the lane, `trace-holes-and-colors.png`): the hole has 8 vertices (corners chamfered, partners 1.4 mm apart), so a 3 mm drag moves the grabbed vertex -2.93 and its partner -1.62, the other six exact; Shift+Left x3 moves exactly one. Deleting the hole: the art's white square then sews (its own shape).

**Why:** Kent 2026-11-03, "edit specific shapes, borders and boundaries very precisely"; before this an outer edit crossing a hole got a server 400.
**How to apply:** a claim of "exactly one vertex" on a digitized ring needs arrows (or a ring with nodes > 3 mm apart); a drag shares.
