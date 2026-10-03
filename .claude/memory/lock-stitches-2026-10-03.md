---
name: lock-stitches-2026-10-03
description: "2026-10-03 — `ties` (lock stitches) built OFF for the shape builder too, one `applyTies` for both JS builders; the 09-14 lettering lock had a leg of 0.8 PIXELS (0.1 to 0.5 mm) and doubled a needle hole; how that hid and how to measure a length"
metadata:
  type: project
---

# Lock stitches, both JS builders — 2026-10-03

**What was open.** Quality review 2026-09-08 §4: the browser engine locked no
cut. Lettering got `ties` on 09-14 (built OFF). `buildQualityDesign` (manual
draw, basic shapes, SVG import, the flatten lane) had nothing.

**What scoping it found.** Measured on the stitch file, the lettering lock
was not what its doc said:

- **Its leg was 0.8 pixels.** `tieRun` used `TIE_STITCH_MM` in the caller's
  units and was handed px. All 85 fonts: median 0.30 mm on four letters,
  0.10 mm on eighteen, longest 0.57, some 0.00. Not one of 17,668 locks
  reached 0.75 mm.
- **Its tie-in doubled a needle hole**: it sat in front of the run's first
  stitch (Python sews at, inner, at, inner and then the run).

Both latent: flag off, no caller.

**What is built (OFF).** `applyTies(stitches, spans)` in `src/digitize.js`,
one post-pass for both builders on the finished stream (DST units, leg 8). A
thread is the records between two cuts (`trim`, `color`); a `jump` is not a
cut. Locked on its first and last PENETRATION, laid toward the next stitch,
or (a lone stitch beside a float) back along the row it closed. A thread
that goes down in one place gets none. Spans are remapped and a lock stays
in its anchor's span. Cost: lettering +3.3% to +8.0% stitches (unchanged
from 09-14), shapes about +1%. Doc: `docs/lock-stitches-2026-10-03.md`.
Tool: `tools/lock-stitch-census.mjs`.

**Its own audit failed the rule twice.** "Two stitch records in a row" put
6.1% of shape tie-offs up-thread from the cut (worst 371 mm): a short row
after a float is one record. Then a lock laid along a float went 0.8 mm into
a hole (285 of 37,082). Both only with `fillColumns` off. Kept as Python has
it and left for the flip: on shapes one lock in five is under 0.3 mm.

**Why:** Kent's flip ("Waiting on Kent" 23), and a sew-out card candidate:
the 0.8 mm and three legs are `machine.py`'s and unsewn there too.

**How to apply:**

- Assert a length on cloth in the OUTPUT's units, at two resolutions. Every
  09-14 tie test checked counts, boxes and "no longer move", all true of a
  lock a fraction of the size. `test_machine_wire.py` guards a constant's
  VALUE, never its unit at the call site.
- Second px-for-mm in one week (the first: `fillColumns`' edge-run inset).
  Grep for a `_MM` constant used next to a px variable.
- Find inserted records by DIFF against the stream without them. A pattern
  ("a, b, a, b") also matches a font's own triple run.
- Scoping a second half means measuring the first half. The lettering port
  was merged, tested and documented, and wrong.
- State a rule about thread in terms of thread, not of records, and measure
  a new flag with the OTHER flags off. A fix is a new rule: audit it again.

Related: [[fill-columns-2026-10-03]], [[check-shipped-before-building-2026-09-29]].
