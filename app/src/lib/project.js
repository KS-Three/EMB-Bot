export function defaultProject() {
  return { garmentId: "left_chest", text: "", fontKey: "geneva_simple", sizeMm: null, colorRgb: [20, 20, 20], underlay: true, mode: "text", nColors: 4, removeBg: true };
}
export function update(project, patch) {
  return { ...project, ...patch };
}
