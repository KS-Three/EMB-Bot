# The border on the canvas (2026-09-09)

Kent, after item 6 shipped as #437: "Have you completed the interactive
satin border feature? (i.e. clickable satin border on the image right click
add / remove)?" — it did not exist; what existed was the per-shape Border
select in the Digitize panel's rows (`shapeOverrides[sid].border`, contract
v1) and Manual mode's right-click curved node. He picked building it over
quality-review item 7.

- Built on the field's existing right-click tool menu (Kent's 2026-08-13
  call), not a new surface: on a recognised shape the menu grows a shape
  section (name; Add border → `auto` / Remove border → `off`; Use design
  setting → clear). `hitOverlay` for the outline, new
  `shapeOverlay.hitShapeInterior` (smallest containing ring) for the inside.
  Commit through `elupdate` exactly like a boundary drag — undo,
  carry-forward and the idle restitch come free because
  `canonicalShapeEdits` already folds `border`.
- The engine's rule the UI cannot hide: a shape classified as satin never
  gets a border (stage 7). The item's tooltip says so; the panel's select
  has the same limit.
- Process: spec/plan doc first
  (`docs/superpowers/plans/2026-09-09-canvas-border-menu.md`), pure helpers
  with vitest, the Svelte change, an e2e against the live service, and the
  open menu looked at at two widths (COOKBOOK's convention).
- Open for Kent: a second "bean" item, or keep one gesture.
