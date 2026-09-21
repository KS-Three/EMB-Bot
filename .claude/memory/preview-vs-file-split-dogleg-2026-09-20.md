---
name: preview-vs-file-split-dogleg-2026-09-20
description: The previewer matches the .dst on every shipping path; answering that found the split walking an L across diagonals, fixed in all three encoders
metadata:
  type: project
---

**Kent, 2026-09-20: "verify the previewer actually matches the .dst the tool
makes."** It does — and the way to prove it is to take BOTH artifacts from one
run of the real app, never from re-derivation.

**How, so the next session does not rebuild it.** Drive the shipped Studio
headless with Playwright; hook `window.EMB.encodeDST` and `window.fetch` to
capture the design object as the exporter hands it over (the service lane posts
`{design, format, label}` to `/export`, so one fetch hook covers both
encoders); capture the real download; get the drawn geometry by importing
`/src/lib/strands.js` over the Vite dev server IN THE PAGE, which in dev is the
same module instance the app is running. Decode the file with **pystitch**,
never `src/dstimport.js`. That is a black-box check: the app's own picture
against the app's own file.

**Result: exact.** Lettering (browser encoder) 2640/2640 sewn segments,
auto-digitized logo (service/pyembroidery) 2285/2285, logo+lettering at four
colours 2753/2753 — identity orientation 1.000, pixel IoU 1.0000, zero
endpoint residual, thread metres equal. See DOCTRINE 2026-09-20 and
scope-history 2026-09-20 for the tables.

**What it found.** All three encoders split an over-length move by clamping
each axis independently, so the file walked an L where the preview drew a
diagonal — every coordinate, count, extent and bounding box still correct.
3.6 mm off the line on a 30.6 mm diagonal, 14.87 mm on the tool's worst
fixture. Fixed in `src/dst.js`, `src/exp.js`, `src/pes.js` by stepping along
the segment (`splitSteps`, cumulative rounding — `splitTrim` always did it
right, the oversize loop never did).

**The lesson that outlives the bug: a fixture that cannot distinguish two
implementations is not coverage of what they disagree about.** Every
over-length fixture in the repo was AXIS-ALIGNED, and an axis-aligned split is
straight however you clamp it. Same family as
[[stale-diagnostics-and-two-flips-2026-09-13]]'s self-comparing suite.

**Reachability, so nobody re-panics or re-dismisses it.** Not reachable through
lettering: `splitSatin` ON (Kent 2026-09-11) leaves 0 over-record segments on
the monogram the census counts 1,930 on with the flag off. Reachable by
RESIZING an imported or auto-digitized element — `buildImportedDesign`
(`targetWidthMm`) scales stitch coordinates, so the Studio's own logo at 250 mm
had 24 of them and put the file 0.41 mm off the drawn line.

**Kept:** `tools/preview-vs-dst.mjs` + `test/preview-vs-dst.test.js` (skips
without pystitch, fails loud on CI, and asserts its fixtures still REACH the
split). `test/encoder-split.test.js` drives all three encoders' `splitSteps`.

**Two format facts, both no-ops:** a `.dst` carries no thread colours at all
(`threads: []` — the preview shows colour, the file holds stops in order), and
a leading trim at the first record does not read back as a trim, because
pystitch only promotes a jump run that follows a stitch.

Related: [[dst-codec-axis-discrepancy]], [[wide-columns-lettering-2026-09-11]].
