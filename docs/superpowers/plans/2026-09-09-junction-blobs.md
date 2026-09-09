# The junction blob as its own column — item 5, PR 3

**Status: MEASURED OUT 2026-09-09, before a line of engine code. Kent's
pick after #435 was "the junction blob sewn as one column with the arms
ending on it (the pro's A apex), plus a junction-aware width statistic".
The instrument built to size it (`tools/junction_blobs.py`) and a
calibration against the pro's own sewn file say neither has a defect under
it. What ships is the instrument, the calibration, and the correction.**

## 0. What governs this

- **Instrument first; a measured negative is a deliverable** (DOCTRINE,
  the serif half of PR 2 the same day).
- **No quality claim on a raw number** (ROADMAP gate 4): a layer count at a
  junction means nothing until the pro's file has been read at the same
  junction.
- **The junction cover** (`satin_patch_junctions`, PR 2) already sews what
  a junction leaves BARE. This PR was about what the arms leave
  over-stacked or mis-shaped.

## 1. The premise

#434's render read MARINE's A apex and R join as clumps: the corner cap of
one Goldman member sweeping 5–6 mm crosses over the square the other
member also covers. The pro's A apex is one horizontal column with the
legs ending under it. So: find each junction's BLOB, sew it as one column
along its own axis, end the arms on it; and read the classifier's width off
the arms alone, since the DT's p90 over-reads a bold letter by its
junctions.

## 2. What the instrument found

`tools/junction_blobs.py`: per junction cluster, the node's medial radius
against its arms' own half-widths, the arm count, what
`_merge_through_junctions` did at each arm (weld / corner / tuck / end /
dropped fork), the blob — the union of the medial balls between the node
and each arm's exit, where the ball is no bigger than the arm's own — and
inside it the thread's coverage LAYERS (`preflight._coverage_map`'s units),
its bare fraction and the seam pairs seated there; per shape the DT p90
over the arms alone against the full skeleton's.

- **A bold letter at 17 mm is mostly junction.** MARINE at 100 mm: 45–90%
  of every letter's skeleton pixels sit inside a junction blob; the node
  balls are 3.4–4.4 mm in radius on 2.2–3.2 mm arms, and an arm between two
  junctions never settles to a corridor of its own. The blob renders
  (`docs/renders/junction-blobs-2026-09-09/`) are discs the size of the
  apex, not the slab the pro sews. The pro's decomposition is the FONT's
  strokes, which no geometry of the raster blob recovers.
- **Our junctions are under-stacked against the pro, not over.** Aligned on
  the whole design's stitch box (ours 99.9 × 62.6 mm, the pro's 95.7 ×
  58.3), coverage layers inside MARINE's letters read ours mean 1.2–1.6 /
  p95 2.4–3.4 / max 3.8–5.2 against the pro's mean 1.8–2.8 / p95 4.1–6.0 /
  max 5.5–11.6; inside every one of the 18 junction blobs the pro's p95
  (3.7–7.3) and max (5.6–11.6) exceed ours (1.8–3.8; 2.2–5.2). Whole
  design: ours p50 2.40 / p95 3.40 / max 5.24, the pro's 2.36 / 4.80 /
  18.46. The second angle agrees: the pro sews MARINE with **4,287
  penetrations and 12,109 mm of thread** (scaled to our size) against our
  3,076 and 7,642 — 58% more thread. The clumps in the render are crosses
  meeting at angles over LESS thread than the pro lays there; a column
  added over the blob would add layers the pro's file says are fine, to fix
  a look the pro's file also has.
- **The arm-only width statistic reads the leftovers.** It flips exactly
  one verdict in the corpus — MARINE's M at 100 mm, 7.34 → 5.67 mm, which
  would then pass the 6.5 mm ceiling — and on drone's wing `S0bae4b0d` it
  reads 9.36 → **1.08** because 83% of that shape's skeleton is blob: a
  9 mm blob passed as a hairline. Four Becker shapes at 80 mm "clear a cap"
  on the arms alone and are already satin. Not a classifier input.
- **What the census does say is a defect is bare blobs**: Fremont's band
  under `wide_columns` has 15 blobs at least a quarter bare, Becker 80 mm
  five — the junction cover's job (PR 2), already measured.

The alignment caveat, stated: the pro's grid reads 26–32% bare inside our
M and E polygons, so the pro's letters sit 1–2 mm off ours; the per-letter
and whole-band figures survive that, the per-blob ones are indicative.

## 3. What ships

`tools/junction_blobs.py` (the census, `--render`), `tools/pro_layers.py`
(coverage layers and thread of a reference file against ours in one
frame), the renders, and the corrections in DOCTRINE. No engine flag.

## 4. What is Kent's

Whether item 5 continues at all, and where the thread-density gap
(the pro's +58% in the letters: denser spacing and zigzag underlay under
lettering) belongs — it is Law 27/50 territory and a sew-out question,
not a decomposition one — or whether the next build goes to item 6 or 7.
