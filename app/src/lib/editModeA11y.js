// Keyboard and screen-reader contract for the three canvas edit modes: Move
// shape, Reshape mode ("Edit points") and Add hole. Their pointer chrome (the
// Done / Discard / cross buttons) is painted on the canvas, which a keyboard
// or a screen reader cannot reach. This module is the words and the key
// arithmetic behind the DOM bar that mirrors it. Pure: no DOM, no Svelte.
// No customer-visible warning text: every string here is a control name or a
// status the user asked for by entering the mode.

export const HOLE_KEY_STEP_MM = 1;
export const HOLE_KEY_STEP_COARSE_MM = 5;

// state: { move: bool, reshape: bool, holePoints: number|null }
// -> null when no mode is on, else { mode, label, hint, buttons: [{ id, label, disabled? }] }
export function editModeBar(state) {
  const s = state || {};
  if (s.holePoints != null) {
    const n = s.holePoints;
    return {
      mode: "hole",
      label: "Add hole",
      hint: "Arrow keys move the cursor (Shift: 5 mm), Space places a point, Enter closes the hole, Backspace removes the last point, Escape cancels.",
      buttons: [
        { id: "holeClose", label: "Close hole", disabled: n < 3 },
        { id: "holeUndo", label: "Remove last point", disabled: n < 1 },
        { id: "holeCancel", label: "Cancel hole", disabled: false },
      ],
    };
  }
  if (s.move) {
    return {
      mode: "move",
      label: "Move shape",
      hint: "Arrow keys move the shape 0.1 mm (Shift: 1 mm). Enter finishes, Escape cancels.",
      buttons: [
        { id: "moveDone", label: "Finish moving shape", disabled: false },
        { id: "moveCancel", label: "Cancel move", disabled: false },
      ],
    };
  }
  if (s.reshape) {
    return {
      mode: "reshape",
      label: "Edit points",
      hint: "Click or marquee points, arrow keys move selected points 0.1 mm (Shift: 1 mm), Delete removes them. Enter or Escape leaves the mode.",
      buttons: [
        { id: "reshapeDone", label: "Done editing points", disabled: false },
        { id: "reshapeDiscard", label: "Discard point edits", disabled: false },
      ],
    };
  }
  return null;
}

// What a screen reader hears when a mode starts or ends.
export const MODE_SAYS = {
  moveEnter: "Moving shape. Arrow keys move it, Enter finishes, Escape cancels.",
  moveDone: "Shape move finished.",
  moveCancel: "Shape move cancelled.",
  reshapeEnter: "Editing points. Enter or Escape leaves the mode.",
  reshapeDone: "Finished editing points.",
  reshapeDiscard: "Point edits discarded.",
  holeEnter: "Adding a hole. Arrow keys move the cursor, Space places a point, Enter closes the hole, Escape cancels.",
  holeClosed: "Hole added.",
  holeCancel: "Hole cancelled.",
  holeNeedThree: "A hole needs at least three points.",
};

export function holePointPhrase(n, xMm, yMm) {
  return `Point ${n} placed at ${xMm.toFixed(1)}, ${yMm.toFixed(1)} mm`;
}

// Mean of a ring's vertices, [[x, y], ...] -> [x, y] (a cursor's start).
export function ringCentre(ring) {
  if (!ring || !ring.length) return [0, 0];
  let x = 0, y = 0;
  for (const p of ring) { x += p[0]; y += p[1]; }
  return [x / ring.length, y / ring.length];
}

// An arrow key on the hole cursor, in field mm (+y up). null for any other key.
export function stepHoleCursor(cursor, key, shift) {
  const k = shift ? HOLE_KEY_STEP_COARSE_MM : HOLE_KEY_STEP_MM;
  const [x, y] = cursor;
  if (key === "ArrowLeft") return [x - k, y];
  if (key === "ArrowRight") return [x + k, y];
  if (key === "ArrowUp") return [x, y + k];
  if (key === "ArrowDown") return [x, y - k];
  return null;
}
