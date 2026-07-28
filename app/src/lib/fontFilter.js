// Pure font-list filtering for the browser dialog. Kept out of the component
// so it's unit-testable without DOM.
export function filterFonts(fonts, query, group) {
  const q = (query || "").trim().toLowerCase();
  return (fonts || []).filter((f) => {
    if (group && group !== "All" && f.group !== group) return false;
    if (!q) return true;
    return f.name.toLowerCase().includes(q) || f.key.toLowerCase().includes(q);
  });
}

// Recommended size band from the authored size. Multipliers are a starting
// point per the spec — validate against real stitch-outs before trusting.
export function sizeBand(sizeMm) {
  if (!(sizeMm > 0)) return null;
  return { min: Math.round(sizeMm * 0.75), max: Math.round(sizeMm * 2.0) };
}
