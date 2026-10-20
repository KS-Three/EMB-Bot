// Moves per-letter colour ranges through one text edit.
//
// A range is { startIdx, endIdx, colorRgb } over the text's character
// indices (see src/digitize.js colorForCharIdx). Without this, fixing a typo
// before a coloured word left the indices where they were and the colour
// slid onto the wrong letters — in the preview and in the downloaded file.
//
// A <textarea> input event is one contiguous replacement, so the edit is
// found as the common suffix and prefix of the old and new text. `caret`
// (selectionEnd after the edit) caps the suffix, so typing a letter that
// repeats its neighbour ("Ann" → "Annn") is placed where it was typed.
//
// Rules, chosen to match what a customer expects of a coloured word:
// - text inserted INSIDE a range takes its colour; at either edge it does not;
// - a selection replaced wholesale keeps its colour on the new text;
// - a range whose letters are all deleted is dropped.
export function remapColorRanges(oldText, newText, ranges, caret = null) {
  if (!ranges || !ranges.length || oldText === newText) return ranges || [];
  const a = oldText || "", b = newText || "";
  // Inserted text ends at the caret, so the unchanged suffix starts no
  // earlier than it.
  let maxSuffix = Math.min(a.length, b.length);
  if (caret != null) maxSuffix = Math.min(maxSuffix, b.length - caret);
  let s = 0;
  while (s < maxSuffix && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
  const maxPrefix = Math.min(a.length - s, b.length - s);
  let p = 0;
  while (p < maxPrefix && a[p] === b[p]) p++;
  const oldEnd = a.length - s, newEnd = b.length - s, delta = newEnd - oldEnd;

  const out = [];
  for (const r of ranges) {
    let start, end;
    if (r.startIdx >= oldEnd) start = r.startIdx + delta; // also: insertion exactly at the start edge
    else if (r.startIdx <= p) start = r.startIdx;
    else start = newEnd; // its first letters were deleted
    if (r.endIdx <= p) end = r.endIdx;
    else if (r.endIdx >= oldEnd) end = r.endIdx + delta;
    else end = p; // its last letters were deleted
    if (end > start) out.push({ ...r, startIdx: start, endIdx: end });
  }
  return out;
}
