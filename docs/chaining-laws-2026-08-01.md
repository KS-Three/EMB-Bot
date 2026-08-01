# Chaining laws — how professionals get from one shape to the next

Laws 59-62, mined from 434 inter-element transitions across the 36-file
professional corpus (273 needle-down links, 161 trims). Measured, not
surveyed: every number below is a percentile over real transitions parsed out
of shipping DST files.

Provenance: **[M]** measured on the corpus this session. Status: **Desk-safe**
unless noted.

---

## Law 59 — Gap distance is NOT the decision variable. [M] Desk-safe.

This is the finding, and it overturns the assumption our engine is built on.
The fraction of transitions sewn as needle-down links, bucketed by gap:

| gap | n | linked | trimmed |
|---|---|---|---|
| 0–2 mm | 49 | **75.5%** | 24.5% |
| 2–4 mm | 74 | **56.8%** | 43.2% |
| 4–6 mm | 52 | **67.3%** | 32.7% |
| 6–8 mm | 35 | **65.7%** | 34.3% |
| 8–12 mm | 58 | **67.2%** | 32.8% |
| 12–20 mm | 71 | **73.2%** | 26.8% |
| 20–40 mm | 62 | **56.5%** | 43.5% |
| 40 mm+ | 33 | 30.3% | **69.7%** |

The curve is **flat** from 0 to 40 mm — professionals link roughly two thirds
of transitions regardless of distance — and only past **40 mm** does trimming
take over. Linked gaps: median **7.83 mm**, p75 15.0, p90 **27.6**, max 61.7.

Our engine trims at `fabric.trim_at_mm`, which is **3.0–4.0 mm**. At 8 mm a
professional links about two times in three; we trim every time. That single
threshold is the whole trims/1k gap (benchmark 8.4 against the corpus's
0.1–4.1 band), and it is a one-line change gated on the rest of these laws.

The 2–4 mm dip to 56.8% is real and worth noting: very short gaps between
*different* elements often mean the elements abut, where a link would show.
Distance alone does not decide it — which is Law 60.

## Law 60 — Links are routed to be COVERED, not to be short. [M] Desk-safe.

Routing of the 273 needle-down links, by what the link runs under:

| routing | n |
|---|---|
| under the next element | 67 |
| baseline, under the next element | 18 |
| serpentine run network (not a point-to-point hop) | 16 |
| tucks under an element sewn later | 15 |
| under the destination element | 10 |
| rides on top of previously-sewn work | 9 |

At least **110 of 273** are explicitly described as passing beneath something
that sews later. The professional move is not "travel the shortest path and
hope"; it is "route where a future element will bury the thread." That is why
they can link at 27 mm without a visible float — the float is not visible.

Consequence for us: a link is only legal where it will be covered, or where it
rides existing stitching. `stage5_overlap` already computes exactly this
knowledge — `later[L]`, the union of everything that sews after the current
layer, which it uses for underlap and (since the border tier) for
`visible_geom`. The chaining decision has the geometry it needs already
computed; it just never asked.

## Law 61 — Link run stitch length is 1.96 mm. [M] Desk-safe.

Median **1.96 mm**, p10 1.20, p90 2.48. This independently confirms the
earlier census figure of 2.02 mm and settles the open tuning item: our
travel/running stitch is 2.5 mm, above the professional p90. Move to 2.0.

## Law 62 — A link is short in stitches even when long in millimetres. [M]

Median **7 stitches**, p90 36. A 7-stitch link at 1.96 mm covers ~14 mm, which
matches the gap distribution. Links are cheap: the median link costs seven
stitches against a trim's 2–3 seconds of machine time plus a lock at each end.

---

## Engine mapping

| Law | Change | Where | Risk |
|---|---|---|---|
| 59 | Raise the link/trim threshold far above `trim_at_mm`; make distance a weak input | `stage7_sequence` | Floats if Law 60 is not implemented WITH it |
| 60 | A link is legal when its path lies under `later[L]` or over already-sewn geometry; otherwise trim | `stage7` reading stage 5's `later` | The real work |
| 61 | Travel/running stitch 2.5 → 2.0 mm | `machine.py` + browser mirror | Golden movement, must be declared |
| 62 | Budget links by stitch count, not distance | `stage7` | Low |

**Laws 59 and 60 must ship together.** Raising the threshold alone converts
trims into visible floats on bare fabric — strictly worse than the trims. The
coverage test is what makes the long links safe, and it is the reason
professionals can do this at all.
