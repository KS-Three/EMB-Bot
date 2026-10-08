---
name: fill-columns-float-pictures-2026-10-08
description: "Kent's standing ask when he flipped fillColumns on the image lane — the next 10 digitized images shown to him carry an off/on float picture; count kept here"
metadata:
  node_type: memory
  type: feedback
---

**Kent, 2026-10-08**, flipping `fillColumns` ON for the Studio's image lane
(PR #673) despite +10.4% stitches on real logos: *"Flip it on - but any
digitized image you show me (for lets say the next 10 images) show me what
the float did, or didn't do."*

**How to apply:** whenever you show Kent a digitized image (a render, a
sheet, a before/after of a logo), also show the `fillColumns` off/on float
picture for the same art:

    node tools/fill-columns-image-sheet.mjs <image.png> [out.svg] [--colors N] [--garment id]

Red = a float leaving the fill (over 0.8 mm outside every drawn shape);
the caption counts floats, cuts and stitches both ways. Headless Chromium
hangs on "waiting for fonts" rendering the SVG to PNG in a cloud container:
swap `font-family` to `sans-serif`, `setContent` it, and fall back to CDP
`Page.captureScreenshot`.

**Lane caveat:** `fillColumns` is the BROWSER engine's (`generate.js`, image
lane = digitizer service offline). The Python service's "digitized" lane has
its own `_columns` and is not changed by this flag — say which lane an image
came from when you show the picture.

**Count (update this line each time; stop after 10):**
1. 2026-10-08 — `becker_marine_logo.png`, left chest, 4 colours: floats
   leaving the fill 1,113 (13,084 mm) → 0; cuts 14 → 11; stitches 8,137 →
   9,621 (+18.2%). Shown in the session that opened PR #673.
