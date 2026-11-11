# Letter-fault reader vs Kent's pins: shown above chance, on a thin margin (2026-11-11)

**Verdict: shown, by the pre-registered rule, n = 14 pins on 6 logos.** At
3.0 mm, the reader has a flag near 9 of Kent's 14 "letters close up, merge
or can't be read" pins (0.64). The same flags land near 0.24 of random points
on the stitched area. The difference is +0.40 (kappa 0.53), and its 95%
item-bootstrap interval is **[+0.08, +0.57]**. The lower bound is above 0,
which is the rule written before the run. Strength AUC, pin-weighted over
items, is 0.66 (0.5 = chance).

**How much weight it bears: little.** Three of the six items carry it.
Leave any one of Bridge, Fremont or MFab out and the interval's lower bound
drops to -0.03. The 2.0 mm sensitivity row crosses 0 ([-0.09, +0.44]). This
is one sitting by one person, on one tree (`950855bf`). Read it as "worth a
second sitting", not "an instrument for Kent's eye". It is not a quality
claim (ROADMAP gate 4).

Fixed before the run, in its own commit (`71ef90ef`):
[`defect-marks-2026-11-10/letter-reader-preregistration.md`](defect-marks-2026-11-10/letter-reader-preregistration.md).
That commit fixed the pin rule, the flag rules and every constant, the radius,
both nulls and the verdict rule. The pins are in `letter-reader-pins.json`
and the full scored output in `letter-reader-score.json`, both in that
folder. No picture is committed.

## What was built

- **Pin rule:** `fault_reader_harness.select_letter_pins`, beside the edge
  rule. The note decides and the kind is a hint: a closure word ("spacing",
  "merg", "hole", "intersect", ...) or a read word on a letter. One pin is
  shared with the edge reader, and the rule says why: Gaulke 3 names both
  faults. Result: 14 pins on 6 logos. `--fault letters` on the harness CLI;
  the edge list is byte-identical.
- **Reader:** `digitizer/tools/letter_fault_reader.py`. It compares
  TOPOLOGY one thread colour at a time: the artwork the design was traced
  from (stage 1's raster, nearest spool per pixel, `bg_mask` = unsewn)
  against our own render of the stored design (each filament drawn exactly,
  in sew order, no anti-alias). Both sit on the render's 12 px/mm grid,
  registered through the plan's frame (dev runs: best shift within 2 px). It
  flags three things:
  - **counter lost:** an art hole that the thread does not keep open, or
    keeps at under half its width;
  - **join:** two art shapes whose thread runs continuously across the line
    midway between them, past one filament's width;
  - **bay closed:** a thread hole where the art has none (the mouth of an
    S or E shut).

  It borrows the half-a-thread, 25%-overlap and 0.12 mm² numbers from
  `glyph_read`'s counter rule. It re-runs every job and refuses an item
  unless the stitches match the stored design; all 11 matched.
- **Why not an existing reading:** `glyph_read`'s per-glyph counters
  (behind `cfg.preflight_glyph_metric`) and `ARTWORK_ELEMENT_DROPPED` both
  say *how many*, not *where*. The first sees only text-tagged words, and
  neither sees two shapes joined.

## Per item, 3.0 mm

| item | pins | flags | hit | chance (area) | chance (edge band) | AUC area |
|---|---|---|---|---|---|---|
| `L_bridge_hat` | 6 | 21 | 5/6 | 0.26 | 0.00 | 0.77 |
| `L_gaulke_roofing_hat` | 3 | 17 | 1/3 | 0.16 | 0.13 | 0.56 |
| `L_hotel_fremont_hat` | 2 | 249 | 2/2 | 0.43 | 0.02 | 0.59 |
| `L_mfab_hat` | 1 | 30 | 1/1 | 0.17 | 0.00 | 0.94 |
| `L_proseal_hat` | 1 | 82 | 0/1 | 0.29 | 0.25 | 0.36 |
| `L_toat_beanie` | 1 | 9 | 0/1 | 0.06 | 0.00 | 0.47 |
| no relevant pin: Becker, Drone, Tires, Golden Tee, TOAT machine | 0 | 0, 157, 0, 7, 5 | - | - | - | - |

Pooled, 14 pins:

| radius | hit | chance (area) | diff | 95% CI | chance (edge band) | 95% CI |
|---|---|---|---|---|---|---|
| **3.0 (verdict)** | **0.64** | **0.24** | **+0.40** | **[+0.08, +0.57]** | 0.05 | [+0.14, +0.84] |
| 2.0 | 0.36 | 0.13 | +0.22 | [-0.09, +0.44] | 0.03 | [-0.07, +0.58] |
| 5.0 | 0.79 | 0.45 | +0.33 | [+0.11, +0.52] | 0.21 | [+0.22, +0.77] |

The pre-registration called the **edge-band null** the stronger claim. It
is not one here, so none is made. That null draws points within 1 mm of
bare fabric, and on these hats most lettering sits inside a sewn field (the
Bridge disc, the MFab and TOAT badges). Chance there is near 0, and beating
it says nothing about letters. It is reported because the page said it would be.

Leave one item out (stitched-area null, 3.0 mm; exploratory, not the
verdict):

| left out | pins | hit | chance | 95% CI |
|---|---|---|---|---|
| Bridge | 8 | 0.50 | 0.23 | [-0.03, +0.56] |
| Gaulke | 11 | 0.73 | 0.27 | [+0.03, +0.62] |
| Fremont | 12 | 0.58 | 0.21 | [-0.03, +0.57] |
| MFab | 13 | 0.62 | 0.25 | [-0.03, +0.54] |
| ProSeal | 13 | 0.69 | 0.24 | [+0.18, +0.62] |
| TOAT beanie | 13 | 0.69 | 0.26 | [+0.10, +0.62] |

## What hit, and by which rule

Each line gives the kind and distance of the nearest flag to the pin:

- Bridge 9 "cannot read the e": counter lost, 0.4 mm. Bridge 5 "can't tell
  this is an &": counter lost, 0.9 mm. Bridge 12 "N and T merged": **join**,
  1.4 mm. Bridge 10 "no space between the body ... and the dot": bay closed,
  2.5 mm.
- Bridge 6 "B and R merge": the hit is the B's **lost counter**, 1.2 mm away.
  No join was flagged between B and R. The reader hit the letter, not the
  merge Kent named.
- Fremont 1 "the A is hard to read": counter lost, 0.3 mm. Fremont 2 "too
  fine print to read": bay closed, 2.0 mm. Fremont has 249 flags, so its
  chance is 0.43.
- Gaulke 2 "not enough spacing between the E": bay closed, 2.1 mm.
- MFab 10 "can't read the G, no spacing": bay closed, 2.6 mm.

## What it missed

- **Both S pins** (Gaulke 6, nearest flag 7.8 mm; ProSeal 2, 5.2 mm): "no
  spacing between the curves". When the bay is filled solid, the thread
  leaves no hole and no topology changes. A topology reader cannot see this
  by construction; it needs a negative-space reading, the kind
  `glyph_read`'s `space` makes.
- **Bridge 2** "the B is missing the two center holes", 5.7 mm. That B has no
  flag at all. Unread here: whether the art at this size still shows those
  holes at half a thread.
- **Gaulke 3** "white spacing not apparent", 4.4 mm.
- **TOAT beanie 4** "the T intersects the border", 3.2 mm: just outside the
  radius, and no join was flagged.

## Its strongest flags that Kent never pinned

- Precision Drone: 157 flags, the strongest joins 9.5 and 6.0 mm wide. The
  item has no letter pin. Kent graded it Terrible and wrote "too hard to
  identify all of the issues". The art is shaded, breaks into about 2,000
  colour pieces, and the reader reads that noise too.
- MFab: two bays 6.4 to 6.5 mm wide, at (83.6, 14.5) and (62.2, 18.8). These
  are too large for letter bays, so most likely thread closing the keyline
  or a large interior.
- ProSeal: joins up to 3.7 mm wide along the bottom row (y about 64 mm, the
  small text). He pinned none there for this fault. His edge pin 4 ("the M
  is jagged") sits on the same row.
- Bridge: a 3.7 mm join at (34.7, 47.8), near the wheel, which he pinned for
  other reasons (pins 4, 7).
- A crossing that joins several pairs is listed once per pair (Gaulke's
  (57.0, 30.6) appears 3 times). This changes no hit, but it inflates the
  flag counts.

## How to use this

- **Do not ship it as a metric, a preflight finding, or a gate yet.** The
  margin is three items wide, and he has made one sitting.
- The next step is a **replication**: a second defect-marks sitting on new
  designs, with the same reader and constants, scored blind to this result.
  If it holds, `counter lost` and `join` are candidate instruments for the
  "letters merge" part of his eye.
- The S/E bay misses say what a second letter reader would add: the
  negative-space ridge reading. It would be a new reader with its own
  pre-registration, not a change to this one.

## Reproduce

From a lane's `digitizer/`, with `--tree` set to the primary checkout on
`950855bf` (the kit's tree). Set `EMB_SCRATCH_KENT` and `EMB_BRIDGE_PRO`
when running from a lane:

    python -m tools.letter_fault_reader run --pro-run <primary>/digitizer/eye_pairs_out/defect-marks-1110/pro_run \
        --out <primary>/digitizer/eye_pairs_out/defect-marks-1110/letter_reader --tree <primary>/digitizer
    python -m tools.fault_reader_harness score --fault letters \
        --marks ../docs/defect-marks-2026-11-10/marks.json \
        --flags <primary>/digitizer/eye_pairs_out/defect-marks-1110/letter_reader \
        --json ../docs/defect-marks-2026-11-10/letter-reader-score.json

The run was not timed; Fremont and Drone are the slow re-runs.
