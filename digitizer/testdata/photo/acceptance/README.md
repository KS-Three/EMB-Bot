# Acceptance photos

Drop 3-5 real portrait/pet photos here, at roughly 5x7-hoop scale (the size
they'd actually be digitized at) -- JPEG, PNG, WebP, or TIFF.

This directory is gitignored (this README is the one deliberate exception,
via the negation line in the repo-root `.gitignore`) -- nothing dropped
here is ever committed or leaves the machine.

Run `.venv/Scripts/python tools/acceptance_ab.py` (from `digitizer/`, with
the digitizer service running) to build the A/B contact sheet.

## And the stage-0 boundary is waiting on this directory (2026-09-11)

Kent's call, item 1 of the 2026-09-08 quality review: **drop 3-5 real TONAL
artworks here and the flat/gradient boundary can be sited.** Not photographs
of people this time — artwork whose ART carried genuine tonal content:

* the ORIGINAL of the Instagram icon (the committed
  `photo/repro_gradient_white_icon.png` is a synthetic reproduction and is
  barred from siting anything);
* airbrushed or shaded logos, photo patches, badges with real ramps;
* anything a customer sent whose art has a real sweep in it.

The requirement is on the ARTWORK, not the stitch file: the `Embroidery
Files` folder holds 45 DST and 16 PES against only 7 artworks, so more jobs
likely have art elsewhere in the business files.

Then, from `digitizer/`:

```
.venv/Scripts/python tools/color_diversity.py --foreground bbox
```

It picks anything here up automatically, labels it real/tonal, prints the
margin (flat max, tonal min, the gap) and then either sites the boundary or
says exactly what it still lacks. **Say `--foreground bbox`**: that is the
definition the 2026-08-15 spec's own table used, and the other one
(`engine`) answers a different question — the two disagree by an order of
magnitude on a JPEG. Why, and what the corpus reads today:
`docs/stage0-signal-decision-2026-09-11.md`.

Nothing dropped here is ever committed or leaves the machine.

