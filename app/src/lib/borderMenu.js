// The per-shape border decision as the canvas's right-click menu shows it.
//
// One field, two ways in: the Digitize panel's Border select writes
// `element.shapeOverrides[sid].border` ("off" | "auto" | "bean", or absent =
// the design-wide setting), and so does the field's context menu. This
// module is the menu's half: given the shape's override entry and the
// design-wide `params.border`, what does the shape effectively have, and
// which items does the menu offer. Pure, so the decision table is tested
// without a browser or a service.
//
// The engine's vocabulary (digitizer_core/config.py, `border`): "auto" sews a
// satin border on a fill shape wide enough to host a column and a bean run
// where it is not; "bean" the light tier wherever a centreline fits;
// "significant" is "auto" gated to shapes that earn it; "off" (or the null
// "let the class decide", which every non-photo class reads as off) none.
// A shape classified as satin never gets one — the panel's select has the
// same limit, and the item's title says so.

const BORDERED = new Set(["auto", "bean", "significant"]);

// -> { bordered: bool, source: "shape" | "design" }
export function effectiveBorder(entry, designBorder) {
  const own = entry && typeof entry.border === "string" ? entry.border.toLowerCase() : null;
  if (own === "off") return { bordered: false, source: "shape" };
  if (own && BORDERED.has(own)) return { bordered: true, source: "shape" };
  const design = typeof designBorder === "string" ? designBorder.toLowerCase() : null;
  return { bordered: !!design && BORDERED.has(design), source: "design" };
}

export const ADD_TITLE =
  "Satin border where the shape is wide enough for a column, a bean run where it is not. " +
  "A shape sewn as satin gets no border.";

// -> [{ id, label, value, title }] — `value` is what to store in
// shapeOverrides[sid].border (null clears the override).
export function borderMenuItems(entry, designBorder) {
  const eff = effectiveBorder(entry, designBorder);
  const items = eff.bordered
    ? [{ id: "remove", label: "Remove border", value: "off", title: "No border on this shape." }]
    : [{ id: "add", label: "Add border", value: "auto", title: ADD_TITLE }];
  if (eff.source === "shape") {
    items.push({
      id: "design",
      label: "Use design setting",
      value: null,
      title: "Sew whatever the design-wide Border setting says for this shape.",
    });
  }
  return items;
}
