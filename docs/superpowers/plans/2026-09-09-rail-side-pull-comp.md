# Rail-side pull compensation for satin, with corners kept — item 6

**Status: BUILT 2026-09-09, Kent's pick after #436. One flag,
`cfg.satin_rail_comp`, DEFAULT OFF. Off is byte-identical to `main` on
every corpus fixture but two, and those two move by the tracer defect the
build found and fixed (§2b), not by the flag. §4 has each prediction
against its result; §7 the decisions.**

## 0. What already governs this — read before changing the plan

- **Gate 1.** The AMOUNT of pull compensation is a physical constant
  (`Fabric.pull_comp_mm`, per preset) and stays exactly what it is. This
  PR moves WHERE it is applied, from the polygon to the rails; nothing here
  changes a number a sew-out owns.
- **The letterform study** (`.claude/memory/letterform-fidelity-2026-08-26.md`,
  #1): stage 5's `poly.buffer(pull)` with shapely's round join puts a
  0.3 mm arc on every convex corner (PRECISION N: 11 vertices → 130),
  narrows every exterior concavity by 2 × pull (THERMAL E's arm slots
  0.936 → 0.336 mm; DRONE E sealed), and the skeleton is then taken from
  that grown polygon — the arms weld before satin ever sees them. The
  pull = 0 control read fidelity 0.587 → 0.747 and is a diagnostic, not a
  proposal.
- **The exterior-notch guard** (`docs/exterior-notch-guard-2026-08-28.md`),
  Kent's hold 2026-08-28: holding the notches open on the POLYGON split
  shapes and redded the chaining benchmark (3.8 → 6.4 trims/1k). Rail-side
  compensation splits nothing: the polygon the skeleton sees is the
  artwork, and the widening happens on the rails the emitter already
  places.
- **The JS engine already does this** (`src/satinplay.js` `stationPush`,
  `src/satin.js`): each station's rails move outward by the pull, with a
  counter guard that holds back the BOLD weight — not the pull — where a
  facing rail is within the gap. Note, recorded here because the
  instrument turned it up: the JS applies `pullCompMm / 2` per rail (the
  preset number is the column's total widening) while stage 5 buffers by
  `pull` per side (the column widens by 2 × pull). Same preset numbers,
  two meanings. This PR keeps the PYTHON meaning so the flag moves only
  where the compensation lands, not how much; which meaning the sew-out
  supports is gate 1's question and is put to Kent in §8.
- **Push comp** (Law 24, `PUSH_CUTBACK_MM`, `cfg.directional_comp` OFF):
  stage 7's end cutback is `pull + PUSH` because the isotropic buffer also
  lengthened the column at its caps. On the artwork polygon the caps are
  not lengthened, so under the flag the cutback owes only PUSH.
- **Goldens re-capture on ubuntu-latest with the pre-change proof** — off
  is byte-identical, so none move in this PR.

## 1. The gap

A satin column's rails are placed on a polygon that was grown by the pull
before the skeleton was taken. The growth is the right amount in the wrong
place: it rounds the corners the caps should be square to, seals the slots
between an E's arms so its skeleton welds them, and its arcs feed
`_split_sharp_corners` and `_corner_forks` a shape the artwork does not
have. The emitter then compensates nothing itself.

## 2. The design

`cfg.satin_rail_comp` (DEFAULT OFF):

- **Stage 5**: a region the satin tier will take (the same call
  `_comp_axis` already makes for directional comp, so compensation cannot
  flip a tier) keeps its ARTWORK polygon — no `_grow` — while the underlap
  tongue, the earlier-layer clip and the hole hold apply as they do today.
  Fills grow exactly as before. `PlannedRegion.satin_tier` carries the
  verdict.
- **Stage 7 → `satin_shape` → `satin_stroke` → `_rail_points`**: a new
  `rail_comp_mm` (the fabric's `pull_comp_mm` when the flag is on and the
  region is satin tier, else 0.0). After every station's rails are placed
  and refined, each rail moves OUTWARD along the cross by `rail_comp_mm`
  — the same per-rail amount stage 5's buffer gave it. The underlay's
  rails ride the same push, so the support stays under the column.
- **The hole guard**: a rail whose outward direction crosses an interior
  ring pushes only as far as keeps the counter at `cfg.min_detail_mm`
  across — the rail-side twin of stage 5's hole hold, which exists because
  a counter that closes is lost artwork. Exterior slots take the full pull
  on both sides, as the polygon growth gave them: on the fabric the pull
  reopens them, and the skeleton that sews them no longer sees them
  sealed. (The JS guard's floor is for the bold weight; there is no weight
  here.)
- **The end cutback** under `directional_comp` becomes `PUSH_CUTBACK_MM`
  alone for a rail-compensated shape.

### 2a. What the build added to the design (measured, 2026-09-09)

- **Every threshold the field feeds is restated in sewn terms.** The
  artwork's distance transform reads a pull narrower than the grown
  polygon's did, so a threshold that was stated in half-widths and read the
  grown DT now sits a pull low: the corridor cap (`floors × 1.6 + 0.2`),
  the ceiling on what sews, the junction tuck, the underlay's oversize
  check, the zigzag-underlay width decision (read raw, ENTHUSIAST's 3 mm
  columns lost 80% of their underlay), and `extract_strokes`' three length
  thresholds — spur pruning, the stub filter, the cluster radius
  (`half_extra_mm`). Each is `+ pull` where it reads the artwork and
  `− pull` where it caps the pre-push rail; 0.0 is byte-identical.
- **Every pushed cross is pushed, the pinched ones included.** With crosses
  under 0.5 mm left alone, THERMAL's T lost 16% of its stitches and
  Becker's `S4a0bffb0` 42% — on the grown polygon those were 0.9 mm
  crosses the drop rule kept.
- **The underlay runs to the caps** under the flag (`_stroke_underlay`):
  the raw skeleton stops half a width short, the grown polygon's corner
  twigs used to carry it there by accident, and the hop from underlay end
  to column cap otherwise crossed the sew-vs-trim bound on every
  single-stroke Becker letter (36 → 42 trims). `poly_link` is the artwork
  grown by `0.1 + pull`, what it always was.
- **Which polygon to skeletonise was measured both ways** — see §4c. The
  flag skeletonises the ARTWORK (the design above); the grown-polygon
  skeleton with artwork rails was built the same day and is the safer
  decomposition. Kent's call, §7.

### 2b. The tracer defect the build found (fixed, on by default)

`stage6_satin._skeleton_edges` walked a junction's own three-pixel clique
straight back to the node (a 3 px self-loop that consumed an arm's first
pixel) and dead-ended on the filler pixel of a filled L-corner, and the
chain beyond either was re-emitted by the leftover pass as 1–3 px free/free
fragments that `extract_strokes` keeps (both ends free) and `satin_stroke`
extends to both caps. ENTHUSIAST's H under the flag sewed its left stem
FIVE times (coverage peak 4.7 → 9.27 layers). A scan of the tracer's own
output against its mask (`scratchpad/railcomp/strand_scan.py`, 10 fixtures)
found the same two cases with the flag OFF on Becker (4 shapes), drone (6),
enthusiast (5) and gaulke (1), harmless there only because
`_cluster_junctions` drops the loop and the fillers happened to sit where
nothing needed them. Fixed by two rules that fire only on those cases
(`tests/test_skeleton_tracer.py`, the H's own pixels): the first step out
of a node prefers a pixel that does not touch the node; a dead end off a
node steps back and takes the other way. OFF, it moves drone's `S60de6f78`
(43 → 45 stitches, two stranded arms) and every ENTHUSIAST satin shape by
+2 stitches in total — through the house angle (`textcluster` composes the
tracer without the cluster pass, so the loop's three pixels had been voting:
1.4445° → 1.4757°). The browser engine's `skeletonEdges`, which the port
was faithful to, still has both cases.

## 3. Instrument first — `tools/rail_comp.py`

Per satin-tier shape at the design's fabric pull: vertices artwork →
grown (the arc vertices), the exterior concavities the growth seals
(closing minus artwork: count and area), the stroke graph on the artwork
against the grown polygon (strokes, junction nodes, welds), and the thread's
IoU against the artwork grown by the pull (the compensation's target in
the file) and against the artwork itself (the 2026-08-26 number).
`--compare` runs OFF/ON for the same, plus stitches, trims and preflight's
coverage and uncovered.

## 4. What it should move — predictions against results (measured 2026-09-09)

`tools/rail_comp.py --compare` at the design's own pull (0.3 mm, pique),
OFF → ON. OFF already carries the tracer fix (§2b).

| fixture | stitches | trims | coverage_max | uncovered total / worst | IoU vs target | IoU vs artwork | sewn outside the artwork |
|---|---|---|---|---|---|---|---|
| ENTHUSIAST 93 mm (12 satin shapes) | 3162 → 3266 (+3.3%) | 26 → 22 | 4.70 → 4.44 | 0.0 / 2.0 → 0.0 / 0.0 | 0.876 → **0.897** | 0.715 → 0.743 | 147.5 → 0.0 mm² |
| Becker 80 mm (8) | 5592 → 5095 (−8.9%) | 36 → 40 | 4.72 → 4.31 | 9.0 → 10.5 (the band, `Sead76620`) | 0.887 → 0.884 | 0.766 → 0.795 | 322.2 → 0.0 |
| drone 80 mm (43) | 16131 → 16014 (−0.7%) | 96 → 83 | 7.02 → 7.10 | 0.0 / 0.5 → 0.0 / 0.0 | 0.797 → **0.838** | 0.606 → 0.564 | 298.8 → 0.8 |
| Fremont 92.5 mm (19) | 9893 → 10004 (+1.1%) | 46 → 45 | 5.72 → 5.93 | 0.0 → 0.0 | 0.675 → **0.836** (score 64 → 76) | 0.702 → 0.492 | 4.5 → 0.0 |

- **THERMAL's E sews its three arms as three columns ON** — held: on the
  artwork the E skeletonises into 4 strokes (2 on the grown polygon), its
  slots 0.936 mm instead of 0.336. The instrument counts the sealed slots
  per design: ENTHUSIAST 2 shapes / 0.5 mm², Becker 1 / 0.1.
- **PRECISION's N loses its corner arcs** — held: vertices 21 → 152 on the
  grown polygon, 21 on the artwork; drone's 43 satin shapes 495 → 4,425
  vertices grown, Fremont's 19 835 → 3,293.
- **IoU against the compensated target rises on every lettering fixture**
  — three of four. ENTHUSIAST +0.021 (10 of 12 letters up), drone +0.041,
  Fremont +0.161; Becker −0.003 (the three small letters −0.02 each; the
  A, `Sff8aab95`, +0.004). Per drone letter: DRONE E 0.646 → 0.861,
  THERMAL A 0.810 → 0.901, THERMAL E 0.860 → 0.880, PRECISION N 0.890 →
  0.898; DRONE O 0.848 → 0.795, THERMAL H 0.889 → 0.882 and THERMAL T
  0.888 → 0.884 down. Fremont's seven lettering shapes all rise, 0.599–
  0.777 → 0.826–0.882.
- **IoU against the artwork rises toward the 0.747 control** — on the two
  bold fixtures (ENTHUSIAST 0.743, Becker 0.795) and FALLS on the two small
  ones (drone 0.564, Fremont 0.492): a 1 mm stroke sews 1.6 mm wide under
  a 0.3 mm pull on each rail, and that number penalises exactly the
  compensation the flag lands. Read `iou_target`; the artwork one is kept
  for continuity with 2026-08-26.
- **Stitches within ±3%, trims unchanged, coverage and uncovered within
  noise, byte-identical OFF** — wrong on every clause but coverage.
  Stitches −8.9% on Becker (caps end AT the artwork instead of a pull
  past it, the push is across the column, not along it — physically right
  and the reason the end cutback owes only the push). Trims move both ways
  (−4, +4, −13, −1): the artwork's skeleton decomposes each letter
  differently — see §4c. Becker's band is 1.5 mm² barer. OFF is not
  byte-identical on two fixtures, by the tracer fix alone (§2b).

### 4c. Which polygon to skeletonise — both measured

The design skeletonises the artwork. Its cost showed on Becker's A: the
growth had been SMOOTHING the outline as a side effect, and the artwork's
stair-stepped edges (a 146 × 91 px source at 80 mm) grow a branch at every
step — 7 strokes for the default's 3, a wedge column across the left leg,
+4 trims on the design. The alternative — skeletonise the grown polygon
exactly as the default does and read only the rails, caps and corners off
the artwork — was built and measured the same day (a one-line difference
at the `extract_strokes` call, plus dropping the sewn-terms offsets of
§2a, since the field is then already the grown one):

| fixture | artwork skeleton (the flag) | grown skeleton |
|---|---|---|
| ENTHUSIAST: stitches / trims / coverage / worst bare / IoU target | 3266 / 22 / 4.44 / 0.0 / **0.897** | 2947 / 24 / 4.52 / 2.0 / 0.877 |
| Becker: same | 5095 / 40 / 4.31 / 10.5 / 0.884 | 5435 / **34** / 4.25 / **5.8** / **0.891** |
| drone: same | 16014 / **83** / 7.10 / 0.0 / **0.838** | 15890 / 90 / 6.92 / 0.5 / 0.829 |
| Fremont: same | 10004 / **45** / 5.93 / 0.0 / **0.836** | 9935 / 50 / 5.86 / 0.0 / 0.813 |

Most of the fidelity lives in the RAILS: the grown skeleton keeps the
default's decomposition and still takes drone to 0.829 and Fremont to
0.813. The artwork skeleton wins the IoU on three fixtures of four and the
trims on three, and is the item as specified; the grown one wins Becker
outright (trims, bare, IoU) and is the safer decomposition. A closing-and-
opening of the artwork at the pull (outline features narrower than 2 ×
pull removed, size kept) was tried as a third way and does NOT recover the
default's decomposition (the A: 6 strokes). The two designs are one line
apart; §7.

## 5. What must not regress, with its fixture — measured

- The flat-lane goldens and pushcomp pins — OFF byte-identical on whitebg,
  alpha, ribbon, Becker, Fremont, gaulke, sunset, meadow (HEAD against the
  working tree, `scratchpad/railcomp/byte_identity.sh`); drone and
  ENTHUSIAST move by the tracer fix as §2b says. The ENTHUSIAST flat-lane
  golden is the platform red CI deselects, so nothing in CI sees it move.
- The T fixture's tuck, the E fixture's flush corner (`test_satin.py`) —
  pass, OFF byte-identical.
- The chaining benchmark (`test_chaining`, OFF) — passes; ON, ENTHUSIAST's
  trims 26 → 22 on the compare (a different configuration from the
  benchmark's, so no /1k figure is claimed against its 4.1).
- Under the flag: `tests/test_rail_comp.py` (7 — default off; the bar's
  rails a pull outside the artwork with caps AT the artwork; the counter
  guard on a 2 mm and an 8 mm hole; the end cutback owes only the push and
  lands the end station where the default does; the wordmark sews nothing
  outside the artwork but the underlap tongue; widened lettering keeps its
  compensated column; `_push_rails` on a pinched cross and a directionless
  one).

## 6. Size and staging

| PR | content | size | gate |
|---|---|---|---|
| this | the flag, both stages, the hole guard, the instrument, the letter fixtures measured | ~250 lines + tests | none — the amount is untouched; flipping is Kent's on the render |

## 7. Decisions for Kent

- **Which polygon the flag skeletonises** (§4c): the artwork (shipped: the
  item as specified, IoU up on three fixtures of four, Becker's A into 7
  strokes) or the grown polygon (the default's decomposition, Becker
  outright better, ENTHUSIAST flat). One line either way.
- Flip `satin_rail_comp` ON by default — after a sew-out, since where the
  pull lands is what the fabric answers to; every satin golden re-captures.
- The 2× disagreement between the engines on what `pull_comp_mm` means
  (per rail in Python, total in JS) — a sew-out of one preset settles it.
