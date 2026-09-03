# The pro's own files were in the zip, and they refute the scale-limit story — 2026-09-03

Read before calling any small lettering "too small to sew", before quoting
`dropped_elements`, and before judging Becker's or Bridge Bar's edges.

## The pro's DST/PES are in the repo root

`Embroidery Files.zip` holds the professional's DST/PES/EMB for Hotel Fremont
(Hotel Patch, Hotel Hat), Becker Marine (four sizes), Golden Tee, Gaulke,
Precision Drone, Tires, MFAB — not just the JPG simulations an earlier grep
found. `pystitch.read()` decodes them; flip y and they render through
`stitchviz.render_design` beside ours. Nobody had done this for Fremont.

## What the Fremont file says

At the same 92.5 mm the pro sews THE, EST 1895 and EAT | STAY | PLAY legibly:
gold block 1,090 st, median stitch **0.82 mm** in the tagline band, THE's black
block **0.90 mm** — satin columns 2–3× the art's 0.25–0.55 mm strokes. The rope
is one continuous ~1.7 mm satin band, not 136 chevrons. 15,458 st, 53 trims,
9 blocks with colour revisits. Ours: 9,990 / 104 / 3.

So scope #1's Fremont item 1 ("genuine physical-scale limitation … nothing new
to build") was wrong in its second half and is corrected. Our failure is
SLIC on a badge (945 superpixels, 0.4–0.6 mm strokes become blobs; tagline =
five tan regions of 0.9–8.6 mm²) plus the width policy (bean under the 0.5 mm
floor instead of widening to a column). `forced_class="flat"` today is no
longer the "crushed mass" the doc describes (3 colours, counters intact) but
drops the rope and EST 1895 outright — not the fix either.

## Instruments that could not see it

- `dropped_elements` reads **0.2%** on Fremont — it sees sewn-but-illegible as
  covered. Kent says "completely lost". Both are right; the instrument needs a
  legibility reading before its count is quoted against his eye.
- `edge_smoothness` measures against the raster; on Becker's **146 px** fixture
  (1.46 px/mm, one pixel = 0.68 mm) the raster IS the staircase. Stage 1
  upscales to its 4 px/mm floor and `INPUT_LOW_RESOLUTION` never fires (it
  only fires when the capped upscale misses the floor). Bridge Bar is a 400 px
  JPEG with margins: 3.5 px/mm, 0.54 mm strokes = 1.9 px — no lane can read
  it, and the 08-27 engine gives identical blobs. Report px/mm before blaming
  the engine.

## Smaller measured facts

- Bridge Bar's 13 colours = photo palette 6 + `PALETTE_OVERFLOW_K` 3, then the
  re-snap escape (defect 15) adds four — NOT stage 2's per-population cap,
  which is the flat lane (PR #337's body says per-population; wrong). Blocks
  6–12 sew JPEG halos: 29% of stitches, 50% of trims, 7 of 13 colour changes.
- `fill_travel_under_cover` ON still leaves 32–39% of fill-phase travel
  exposed on all three (Becker's N run is one). "FIXED" in MASTER_SCOPE now
  says residual.
- Becker's C infill: 42 mm² at 1–2% sewn; the counter is part of the outline
  satin region and satin decomposition leaves the blob. MARINE: five of six
  letters tatami where the pro satins all six (2.6–3.2 mm strokes).
- Becker's white letter bodies (40%) sew as holes; the pro fills them.

Full record with sheets: `docs/kent-review-2026-09-03.md`.
