// The scale bar under the embroidery field: a "10 mm" reference the customer
// can read the design's size off at any zoom. It lives in the zoom bar as an
// HTML element, not on the canvas, for three reasons that all matter: it
// never covers sewable field (DOCTRINE, and e2e/field-chrome.spec.js pins
// that no chrome lands on the canvas), it does not disturb the pixel counts
// the outline and HiDPI specs read straight off the bitmap, and it needs no
// dpr handling of its own -- the renderer's returned `scale` is already in
// CSS px per mm.

// Round lengths a person reads at a glance. 25 rather than 30 because the
// hoops are stated in inches too, and 25 mm is the one that is also
// (nearly) an inch.
const STEPS_MM = [1, 2, 5, 10, 20, 25, 50, 100, 200];

// Picks the longest step that fits in `maxPx` on screen at `pxPerMm`, and
// returns its length in both units. The bar should be as long as it can be
// without competing with the buttons beside it: `maxPx` defaults to 120,
// which is about the width of the zoom bar's three buttons. Falls back to
// the shortest step when even that overflows (a zoom this app does not
// reach), and to null when there is no scale yet -- the empty field before
// a hoop is chosen, or a render that produced no transform.
export function pickScaleBar(pxPerMm, maxPx = 120) {
  if (!(pxPerMm > 0)) return null;
  let mm = STEPS_MM[0];
  for (const step of STEPS_MM) {
    if (step * pxPerMm <= maxPx) mm = step;
    else break;
  }
  return { mm, px: mm * pxPerMm, label: `${mm} mm` };
}
