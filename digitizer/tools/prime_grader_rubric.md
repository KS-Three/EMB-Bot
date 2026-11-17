# Prime grader rubric, version 2026-11-17

You are grading machine-embroidery renders the way Kent grades them: by eye,
against the ORIGINAL artwork. Follow this page exactly. It is pinned by sha in
`tools/prime_grader.py`; a changed word is a new dated version.

## What you may and may not open

- Open only the pictures and `kit.json` in the kit folder.
- Do NOT open `_sealed.json` (the computed yardstick's reading), any
  `docs/defect-marks-*` folder (Kent's own marks), or an earlier scorecard,
  until every design is recorded. Your reading must be blind to all three.
- Grade one design at a time. Record it with `prime_grader record` before you
  open the next design's pictures. Do not go back and change a recorded design.

## The pictures, per design

1. `<id>_overview.png`: the original artwork, our render, and (where one
   exists) the professional digitizer's file drawn the same way. The render
   carries a millimetre ruler; x runs right and y runs down from the design's
   top-left corner.
2. `<id>_tile_<name>.png`, the magnifier: one patch of the design at 30 px per
   mm. Left is the same patch of the original (placed by an automatic fit, so
   it can be off by a millimetre or two), right is our render with a ruler in
   design millimetres. Read EVERY tile. Jagged edges, wavy uprights, flat spots
   on curves and stitch direction only show here.
3. `<id>_travel.png`: the render dimmed, with every needle-up move drawn in
   magenta and each colour block numbered in sewing order.

Look at the overview first and decide what the design is supposed to be. Then
read each tile against its patch of the original. Then the travel picture.

## What to judge, in Kent's words

- Lettering must follow the flow of the letter as a pen would write it: "the
  letters follow the rules of penmanship". Stitches that run across a stroke
  the wrong way, or change direction mid-stroke without reason, are a fault.
- Curves are smooth, with no abrupt flat spot. Uprights are straight, not wavy.
  Edges and borders are clean, not stair-stepped or saw-toothed.
- No odd artefacts: a crossover stitch, a blob or pile-up, a stray run.
- Letter shape beats spacing. Counters (the holes in A, B, O, e) stay open.
  Letters do not merge into each other.
- Nothing in the art is missing or broken off; nothing is sewn that the art
  does not have.
- Thread colours match the art. Fabric does not show where the art is solid.
- The professional's file shows what thread can do at this size. Use it to
  tell "impossible at this size" from "we did it badly". Grade OUR render.

## What to write down

A fault is one spot. For each, give:

- `x_mm`, `y_mm`: where, read off the ruler, in design millimetres.
- `what`: one of `pen_flow`, `letter_shape`, `wavy`, `lumpy_curve`, `blob`,
  `stray`, `gap`, `missing`, `extra`, `colour`, `direction`, `stitch_type`,
  `mushed`, `jagged`, `other`.
- `severity`: `ruins` (a customer would reject the piece for this alone),
  `noticeable` (a customer would see it), or `nitpick` (only a digitizer
  would).
- `note`: one plain sentence naming the element and what is wrong with it,
  as against the original ("the top bowl of the B has a flat spot on its right
  side").
- `seen_in`: `overview`, `travel`, or the tile name.

When the same fault repeats (every letter of a word is jagged), pin the two or
three worst and say in the note that it repeats. At most 40 faults a design.

Whole-design ticks, for problems with no single spot: `unrecognizable`,
`too_busy`, `colours_off`, `background_sewn`, `detail_lost`, `not_for_thread`.

## The grade

One of Kent's five, for the design as a customer would receive it:

- **Great**: would ship as is; a professional would be content with it.
- **Good**: ships; a few nitpicks, nothing a customer would notice.
- **Okay**: recognisably right but with noticeable faults; needs a clean-up.
- **Bad**: several noticeable faults or one that ruins a part of it.
- **Terrible**: unreadable, unrecognisable, or not fit to sew.

`reason`: two or three sentences on why that grade, leading with what most
holds it back.

## The verdict file

Write one JSON file per design and record it:

```json
{"item": "L_example", "grade": "Okay", "whole": ["detail_lost"],
 "reason": "…", "tiles_read": ["A1", "A2", "B1"],
 "faults": [{"x_mm": 41.5, "y_mm": 12.0, "what": "jagged",
             "severity": "noticeable", "note": "…", "seen_in": "A2"}]}
```

    python -m tools.prime_grader record --kit KIT --verdict FILE.json

`tiles_read` must name every tile of the design; `record` refuses otherwise.

## What this reading is and is not

It is an instrument reading for the development loop: where to look and what
moved since last night. It is not a quality claim, it does not flip a flag, and
a choice between two close variants stays Kent's.
