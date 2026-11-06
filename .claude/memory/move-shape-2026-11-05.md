---
name: move-shape-2026-11-05
description: Move shape: translate one digitized shape (shell, holes, nodes) as a unit; outline live, stitches follow on commit via the normal restitch; ignores the similar tick
metadata:
  type: project
---

**What shipped (2026-11-05).** "Move shape" (popover row after Edit points, or the right-click menu inside a digitized shape) in `EmbroideryField.svelte`: `shapeMove = { elId, shapeId, eb, shell, holes, dx, dy, drag }`. A left press anywhere drags the shape, arrows move it 0.1 mm (Shift 1 mm); Enter / Done / a selection change commits ONE discrete `elupdate`, Esc / Discard dispatches nothing. Spec: `docs/superpowers/specs/2026-11-05-move-shape-design.md`; helpers `translateRing`, `moveShapeOverrides` in `shapeNodes.js` (through `ringEditOverrides`).

**Why:** Kent 2026-11-05: "select a stitch layer or 'body' and move the entire feature, the outline along with the digitized profile." Grilled: stitches are not tagged per shape on the wire, so they do NOT slide live; they regenerate after the commit. The "edit all similar shapes" tick is ignored.

**How to apply:** `boundary_override` always; `holes_override` only when the shape has a hole; `nodes` unchanged (`ringFingerprint` is similarity-invariant, unit-tested). The basis is `editBasis` frozen at entry. Test hooks on the canvas: `data-shape-move`, `data-shape-move-delta` ("dx,dy" mm), `data-shape-move-btns` (Done/Discard centres). E2E (m1)-(m7) in `field-reshape-mode.spec.js`; read fill with STRICT thresholds (black < 14), the outline casing is a translucent grey that moves live. A move may leave the stitch count unchanged, so `restitched()` is the wrong wait: poll the fill bbox. Extends [[reshape-mode-2026-11-03]], [[sparse-nodes-studio-2026-11-05]], [[add-hole-2026-11-05]]; stale-download rule in [[download-stale-guard-2026-10-25]].
