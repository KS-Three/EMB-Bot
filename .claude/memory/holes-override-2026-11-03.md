---
name: holes-override-2026-11-03
description: Contract v1.9 `shape_overrides[sid].holes_override` (service half, PR 4 of the node-reshape spec): replaces a shape's interior rings, [] = solid, absent = carry-over; Studio half still to build
metadata:
  type: project
---

Kent 2026-11-03, ruling 3 of [[node-reshape-spec-2026-11-03]]: holes get their own
additive key; `boundary_override` stays exterior-only and unchanged.

**What shipped (service only, no `app/`):** `holes_override: [[[x, y], ...], ...]`
in design-centre y-down mm. Present REPLACES the interiors, `[]` makes the shape
solid, absent keeps today's carry-over byte for byte. Alone or beside
`boundary_override`: `Polygon(shell, holes)` from whichever of the pair is present
plus the current geometry for the other. `regions._parse_ring` is the shared
per-ring check (3..500 distinct finite pairs); `app.py` pre-checks each ring
(list, count, finite, simple) for a 400; containment / crossing holes / the
sewability floor run in `apply_shape_edits` and fail the JOB naming
`holes_override`. `r.meta["holes_override"]` rides `match_shape_ids`.

**Cache:** nothing to add in `jobs.py` - `EDIT_KEYS` names the top-level
`shape_overrides`, so the new key already leaves `generation_key` and enters
`content_key`. Tests prove a hole edit hits the generation and forks stay isolated.

**How to apply:** the Studio PR reads `holes_mm`, draws hole rings and emits the key
only when a hole was edited (an exterior-only edit must stay byte-identical on the
wire). Don't send it to an older service: it 400s the key.
