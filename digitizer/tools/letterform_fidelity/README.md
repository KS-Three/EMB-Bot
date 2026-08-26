# Letterform fidelity — the measurement kit

The scripts that produced the 2026-08-26 letterform investigation
(`.claude/memory/letterform-fidelity-2026-08-26.md`). They are kept because the
*numbers* in that write-up are worthless without the means to re-derive them,
and because the investigation's central lesson is that **the instrument this
project already had could not see the defect.**

## Why this exists at all

Bare-fabric coverage — the metric every earlier letter check used — scores
THERMAL's `H` at **1.9% bare**, i.e. "fine". The `H` is visibly deformed.
Coverage cannot see a tilted column, a rounded corner, or a scalloped edge,
because thread is present in all three cases; it is just in the wrong place.

`s11_iou.py` scores the alternative: IoU of the actually-sewn thread (buffered
at the 0.4 mm thread width) against the artwork letter. Design-wide mean over
20 letters was **0.587** on the shipped pipeline.

**Treat that number as SCREENING, not a verdict.** It saturates on small
letters — `DRONE`'s `E` scores 0.534 against a thread-width ceiling of 0.580
while sewing as a visible "L". Per ROADMAP gate 4, it is a direct geometric
measure rather than an agreement rate, so it needs no chance correction — but
do not put a quality claim on it until it can separate a tilted column from a
covered one.

## Running them

From `digitizer/`, with the venv. Outputs land in `$LF_OUT` (default `./out`
beside the scripts, gitignored). `s1_cap.py` must run first — everything else
reads its pickle.

```bash
cd digitizer
.venv/bin/python tools/letterform_fidelity/s1_cap.py     # digitize + capture (required first)
.venv/bin/python tools/letterform_fidelity/s12_stroke.py # stroke widths per letter
```

| Script | What it answers |
|---|---|
| `s1_cap.py` | Digitize `testdata/photo/drone_render.png`, pickle regions + blocks |
| `s2_map.py` | Map blocks to letters |
| `s3_cov.py` | Per-region bare fabric |
| `s4_band.py` | Text-band isolation |
| `s5_letters.py` | Per-letter bare + spill + bare-blob locations |
| `s6_pull0.py` | The `pull_comp_mm = 0` **diagnostic control** (see warning) |
| `s7_cmp.py` | Shipped vs control, per letter |
| `s8_draw.py` | Polygon draw helpers |
| `s9_overlay.py` | Stage-4 polygon over source pixels (proves stage 4 is clean) |
| `s10_viz.py` / `s13_viz0.py` | `stitchviz` crops, shipped / control |
| `s11_iou.py` | **Shape fidelity** — thread-vs-artwork IoU |
| `s12_stroke.py` | Stroke width and cap height per letter |
| `s14_fig.py` | The four-strip before/after figure |

Verified portable and reproducing on 2026-08-26 after being lifted out of a
session scratchpad: `s1_cap.py` → `design_class gradient, regions 74, blocks
24`; `s12_stroke.py` → `DRONE E` 0.551 mm stroke at 2.91 mm cap height.

## The one warning

`s6_pull0.py` sets `pull_comp_mm = 0`. That is a **diagnostic control, never a
proposal.** Pull compensation is a physical constant: it exists so the sewn
edge lands on the artwork after the fabric relaxes, and what it should be is
**ROADMAP gate 1 — settled by a sew-out, not by geometry.** The control is
there to attribute a defect to stage 5, nothing more. Do not read "fidelity
improves at pull=0" as "reduce pull compensation".
