# Flat edges and the outline-redraw flip: two follow-ups to the jag-source trace (2026-11-14)

Follows `docs/jag-source-2026-11-13.md` (PR #1479, merged). The Director asked
for two things:

1. finish the case for flipping `outline_redraw_k = 0.75`, across every
   upscaled pro job;
2. take the larger share of Kent's smooth-edge pins, the satin construction
   (d): 14 pins where a satin should form a flat edge or a square corner.

Instrument readings, n = 1 per design, one laptop; not quality claims
(ROADMAP gate 4). Pictures are under `digitizer/eye_pairs_out/jag-source-1113/`
in the primary checkout (gitignored): `flip/sheets*/` for part 1 and
`flat-ends/` for part 2.

## 1. `outline_redraw_k = 0.75` on every upscaled pro job

OFF and ON on the same tree for each job (#1479's head; the first three rows
are #1479's own pairs, on 7ad9c124 + the change). Columns:
- roughness: `curve_fidelity`, in degrees;
- wobble: the satin tier's `edge_wobble` std, in mm;
- bare: mm2 of OFF art no thread covers;
- exposed travel: mm of needle-down travel with no other stitching within
  0.3 mm, i.e. thread on bare fabric;
- long joins: count and mm of single stitches over 6 mm that join two runs
  with no jump, trim or travel run.

| job (source px/mm) | stitches | trims | roughness deg | satin wobble mm | bare mm2 | exposed travel mm | long joins (n, mm) |
|---|---|---|---|---|---|---|---|
| becker_hat_large (1.42) | 16289 -> 16072 | 12 -> 16 | 8.30 -> **5.25** | 0.144 -> 0.145 | 3.35 -> 2.05 | 0.0 -> 0.0 | 3, 62.8 -> 4, 91.5 |
| becker_lc_large (1.52) | 14951 -> 14567 | 13 -> 15 | 9.27 -> **6.23** | 0.134 -> 0.131 | 2.7 -> 3.02 | 0.0 -> 0.0 | 2, 51.1 -> 2, 53.3 |
| becker_hat_small (1.9) | 10576 -> 10268 | 12 -> 12 | 11.16 -> **8.31** | 0.128 -> 0.133 | 0.99 -> 1.33 | 0.0 -> 0.0 | 1, 13.7 -> 1, 15.2 |
| becker_chest_small (1.9) | 10339 -> 10085 | 12 -> 11 | 9.89 -> **7.10** | 0.127 -> 0.132 | 0.96 -> 1.31 | 0.0 -> 0.0 | 1, 13.7 -> 1, 15.2 |
| becker_beanie (1.82) | 13902 -> 13641 | 16 -> 14 | 10.52 -> **7.43** | 0.130 -> 0.128 | 0.11 -> 0.18 | 0.0 -> 0.0 | 1, 14.5 -> 1, 15.7 |
| bridge_hat (4.41) | 8569 -> 8501 | 12 -> 9 | 6.78 -> **6.11** | 0.092 -> 0.093 | 0.0 -> 0.01 | 0.0 -> 0.0 | 0, 0.0 -> 0, 0.0 |
| bridge_lc (3.64) | 10998 -> 11011 | 13 -> 12 | 6.57 -> **5.45** | 0.087 -> 0.086 | 0.0 -> 0.0 | 0.0 -> 0.0 | 0, 0.0 -> 0, 0.0 |
| mfab_hat (3.85) | 20849 -> 20834 | 17 -> 21 | 7.11 -> **6.81** | 0.088 -> 0.087 | 0.0 -> 0.0 | 0.0 -> 0.0 | 2, 76.0 -> 2, 66.0 |
| mfab_lc (3.9) | 17897 -> 17893 | 20 -> 21 | 6.36 -> **5.39** | 0.093 -> 0.089 | 0.0 -> 0.0 | 0.0 -> 0.0 | 2, 55.9 -> 2, 78.7 |
| toat_machine_hat (4.06) | 18970 -> 18869 | 22 -> 23 | 4.02 -> **3.75** | 0.066 -> 0.068 | 0.0 -> 0.0 | 0.0 -> 0.0 | 0, 0.0 -> 0, 0.0 |
| toat_machine_beanie (4.48) | 18399 -> 18205 | 21 -> 22 | 3.56 -> **3.12** | 0.059 -> 0.056 | 0.0 -> 0.0 | 0.0 -> 0.0 | 0, 0.0 -> 0, 0.0 |
| toat_beanie (4.5) | 18472 -> 18139 | 24 -> 22 | 4.13 -> **3.73** | 0.066 -> 0.064 | 0.0 -> 0.0 | 0.0 -> 0.0 | 0, 0.0 -> 0, 0.0 |

**Reading.**
- Roughness falls on every upscaled job, 0.3-3.0 degrees.
- Roughness falls most on Becker, whose source pixel is largest: 2.8-3.1
  degrees at every size.
- Exposed travel is 0 everywhere, both arms.
- Bare fabric inside the art is 0 on every non-Becker job. On Becker it
  falls at hat-large (3.35 -> 2.05 mm2) and rises 0.07-0.35 mm2 at the
  other four sizes: small, but the one reading that goes the wrong way.
- Trims move -2 to +4.
- Satin wobble is flat.
- The jobs at their own resolution (Drone, Golden Tee: 12.3 and 23.3 px/mm)
  are byte-identical by construction (#1479's md5 controls).

**Becker's "+24 mm of bare travel" in #1479 was my metric's error.** It
counted travel under the black border (sewn later) as bare. Measured as
travel with no other stitching within 0.3 mm, it is 0 OFF and 0 ON on every
job.

**What the visible line beside Becker's border really is, and it is a
stage-7 fault worth a line of its own.** It is a single 23.6 mm stitch,
needle down, between two fill runs of the black border region
(`S92f2350b`), with no jump, no trim and no travel run: the adapter writes
the next run's first point straight after the last. OFF has the same fault
elsewhere on the same shape: a 37.5 mm diagonal across the B and the C, the
line visible in OFF's render. Over the table it shows only where stage 7
chains a shape's own fill sections. Becker has 1-4 per size, 13.7-91.5 mm;
MFab 2 per size, 51-79 mm; none elsewhere. The redraw only moves where the
join lands (Becker hat large 3 -> 4 joins, 62.8 -> 91.5 mm; MFab hat 76 ->
66 mm). It needs its own fix in stage 7's chaining (a trim, or a travel
inside the shape, for any join over the machine's stitch-length limit). It
is not part of the flip question.

## 2. Flat edges and square corners: the 14 satin-end pins

Read pin by pin, at 90-110 px/mm, with our runs coloured one by one and
their needle points drawn, beside the art and the pro's needles where his
file covers the spot (`flat-ends/zoom/`). At all 14 pins the art and the
stage-4 polygon are straight and square. The fault is in how the satin meets
the edge.

| mechanism | pins | what the needles show |
|---|---:|---|
| **the column's END lies on the flat edge, and its last crosses fan or turn onto it** (the mitre, `_fan_ends`, a serif sewn as the stem's terminal fan) | **6** | Becker #10, #11: MARINE stems' crosses tilt 15 degrees, so the flat letter top is the column's end, and every cross near it is 15-20 degrees off it; thread BODIES draw the top. The pro sews a band along the top with crosses square to it, and thread ENDS draw it. k_line #4: the I's serif is sewn as the stem's fan. and_pizza #4: the & stroke's V terminal fans. ProSeal #2: the last three crosses fan at the corner, where the pro keeps them parallel and clips each on the slanted face (his end points on the face line within 0.02 mm, ours 0.17). Gaulke #2: oblique cross ends at the gap, which pull also narrows. |
| **two Column pieces butt at an acute joint on the flat edge** | **5** | and_pizza #2, #3 (the Z's bottom-left joint), #19, #20 (the top joints): the diagonal's end crosses slant into the joint, leaving a notch, or poke 0.35-0.5 mm past the edge (#3: one travel penetration). Jakarta #8: the A's leg ends with slanted crosses below the foot's last cross. |
| **the cap: the last cross parallel to the end stops short** | **2** | and_pizza #1 (the I's bottom-right corner: last cross 0.9 mm short of the rail), k_line #5 (the bar's top-right corner: last full cross 0.4 mm before the end, then a short one) |
| short-stitch guard pulling alternate ends back | 0 | not seen at any pin |
| butt end handed to a FILL edge | 0 | the joints above are column to column |
| matches the pro | 1 | Fremont #3: the H's satin ends round off exactly as the pro's do |

No mechanism holds a majority. The largest is the end that fans or turns
onto a flat face (6 of 14), and it is not one geometry: a tilted stem's
end, a serif, a V terminal, a block's slanted end. The pro answers them two
different ways:
- a long flat end nearly parallel to the crosses (Becker's letter tops)
  becomes a separate band whose crosses are square to the edge;
- a slanted end (ProSeal) keeps its crosses parallel and clips each one on
  the face.

The second contradicts the existing fan rule, which `_fan_ends` read off the
pro's Becker E arms (crosses falling under the floor at the tip sewed
bare). Neither answer is a tolerance: each is a construction choice in
`outline_cut`.

**A measured negative, not shipped: snapping end points onto the edge
line.** The first idea was that the ends merely scatter about the edge, and
a pass moving every satin end within 0.45 mm of a straight art edge onto its
edge's median line (at most 0.35 mm, along its own cross) moved 246-2,121
points per design. It changed the pinned spots by 0.000-0.016 mm of
scatter: the ends were already collinear, at k_line #4 all seven at +0.19 mm.
What draws the edge at these pins is the turned crosses' bodies, not where
their ends land. Not built.

### An existing OFF flag cures the joints: `lettering_columns_apex_cut`

Built 2026-10-25 and left OFF. "Where two strokes meet at an acute tip ...
the tip sews as ONE column whose crosses span both strokes", read off the
pro's DSTs. A Z's two corners are exactly such tips. ON, on and_pizza
(`flat-ends/apex/`):
- #2 and #3 (the Z's bottom): the joint's slanted ends and the stitch that
  poked 0.35-0.5 mm below the edge are gone. The bottom is one straight row
  of thread ends.
- #19 and #20 (the Z tops): the notch at the joint is gone. The top is one
  straight row of ends at a constant 0.15 mm above the art.
- #4 (the &'s V terminal): unchanged.
- Whole design: both Zs read square-cornered and flat. The rest is
  unchanged except one small stub at the second Z's top-left corner.
  2454 -> 2539 stitches.

Elsewhere `apex_cut` changes no pinned spot:
- Jakarta: byte-identical. The A's leg-to-foot joint is not an acute tip.
- k_line (3372 -> 3341 stitches): #4 unchanged.
- Becker (16289 -> 16320): #10 and #11 unchanged.

Whole-design views show no regression: Becker's M's V and N diagonal sew a
little cleaner, and k_line changes only at the K's V
(`flat-ends/sheets/B_*`, `C_*`). **So an existing OFF flag cures 4 of the
14 pins, every Z joint, and it is simply not on.** Flipping it is Kent's
call. It was built 2026-10-25 for renders and has not been flipped since.

### What does not cure the rest

The skeleton tier's end flags, all OFF, tried together on ProSeal and
Gaulke: `satin_free_end_chord_aim` + `satin_cap_skew_inset` +
`satin_junction_square`. Neither pinned spot moves (ProSeal 6434 -> 6424
stitches elsewhere).

### What is left, and whose it is

| pins | what it needs | where |
|---|---|---|
| Becker #10, #11 | MARINE's crosses run within 15-20 deg of the letters' flat tops and feet. The pro sews those letters with crosses near-vertical throughout (`sheets/E_*`, and the whole-design sheets), so every top and foot is a row of thread ends | the stitch angle chosen for a line of lettering, not an end rule (house angle / Column-lane tier choice: another lane's) |
| k_line #4 | the I's serif sewn as its own short column, not as the stem's fan | Column lane: `satin_slab_serifs` does this for the skeleton tier only |
| ProSeal #2, and_pizza #4 | a slanted end clipped on its face instead of fanned (the pro's ProSeal end: penetrations on the face line within 0.02 mm) | Column lane / skeleton `_fan_ends` -- contradicts the pro reading `_fan_ends` was built on (Becker's E arms), so it needs a per-face rule, not a flip |
| Jakarta #8 | the A's leg ending on its foot without crosses slanting past it | Column lane joint (not an apex) |
| and_pizza #1, k_line #5 | the last cross reaching a square corner when the end is a few degrees off square (under `MITRE_MIN_DEG`, so neither `_cap_square_ends` nor the mitre takes it) | Column lane end |
| Gaulke #2 | the white gap held open (pull narrows it) | pull / gap, not an end |

Each is a separate construction change of 1-2 pins. None is a majority, and
the largest share is Becker's two pins, which are an angle choice. No
engine change is shipped in this PR.
