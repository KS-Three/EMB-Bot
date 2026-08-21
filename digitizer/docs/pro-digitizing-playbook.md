# The professional digitizing playbook — measured, not guessed

Every law below is a measurement over real production stitch files, not an
opinion. Corpus: 39 DSTs, 410,163 stitches — Kent's three commissioned designs
(PRECISION DRON HAT, HOTEL FREMONT, beckers logo hat) plus 36 free designs
from embroideres.com studied under `tools/study_pro.py` (per-file) and
`tools/census_pro.py` (corpus-wide, phase-level). Re-run both before arguing
with any number here.

## The laws

**1. A satin element is one needle-down run: center walk, underlay if earned,
column.** The dominant element recipe is `R.S` (center run, then column) with
`R.Z.S` when the column is wide. Multi-stroke lettering chains
`R.S.R.S.R.S...` — position along the web, sew the column, move on — with the
needle down throughout. Runs of 180–880 stitches; trims only between
components. Median 0.8 trims per 1,000 stitches (range 0.1–4.1).

**2. Zigzag underlay is earned at ~2–2.5 mm column width.** Columns WITH a
zigzag phase under them: median width 2.71 mm (p10 1.13, p90 5.15). WITHOUT:
median 1.33 (p90 2.51). The crossover sits between 2.0 and 2.5 mm.
(`SATIN_ZIGZAG_ABOVE_MM = 2.5` — empirically confirmed.)

**3. Corners are sewn through, not split: 1,436 in-run corner events vs 18
splits.** The turn spreads across roughly one column width — gradual spokes,
outside rail fanning, inside protected by short stitches. Splitting is
reserved for folds past ~90°.

**4. Satin density is 0.40–0.51 mm on the rails, and the OUTER rail holds it
on curves.** Nominal 0.40–0.42 in every lettering file measured.

**5. Columns run to 5 mm wide** (beckers median 4.22, max 5.10; little-romeo
3.4/4.2) — always over underlay per law 2.

**6. Locks are universal and tiny.** Nearly every run tail ends in a tie-off
cluster; lock stitches measure median **0.45 mm** (p90 1.21) — noticeably
shorter than our `TIE_STITCH_MM = 0.8`. Open sew-out question: tighten ours?

**7. Fills: 2.0–3.4 mm stitches (median ~2.6), row spacing ~0.20 mm effective
in dense branded fills, 0.32–0.65 in lighter work, stagger irregular —
never a rigid cycle.** Whether 0.20 is one dense pass or two interleaved
0.40 passes is undecided; it halves or keeps our stitch counts, so it is a
sew-out decision.

**8. Running/travel stitches: median 2.02 mm** across 218k measured stitches.
Ours emit at 2.5 (`TRAVEL_STITCH_MM`, `UNDERLAY_STITCH_MM`) — slightly long
against practice; candidate tune, low risk.

**9. Script strokes CROSS as overlapping complete columns.** No junction
negotiation where a letter's loop crosses itself — both strokes sew whole,
one over the other. (A five-point star's center is five crossing strokes,
not a skeleton-weld puzzle.)

**10. Sketch style is a technique tier of its own**: whole designs of layered
running-stitch passes (corgi, snowman, rose files — 6 runs, 12k stitches,
1 trim). Nothing in our engine emits it; parked as a possible "small text /
light art" rendering mode.

## Border laws (`tools/border_pro.py`, 39 files)

**11. A border column is THINNER than a lettering column.** 18 satin borders
found: width median **1.40 mm** (p10 0.78, p90 2.98) against 2.21 mm median
for satin generally. An outline is a line, not a stroke of letterform weight —
sewing a border at lettering width is a large part of why our outlines read
heavy.

**12. Border density is slightly looser: median 0.45 mm** (p90 0.64) against
0.40–0.42 for lettering columns. A border rides over an edge that already has
coverage under it, so it does not need lettering density.

**13. Every border found is a CLOSED LOOP** (18/18). A border is generated
from a perimeter path, sewn as one continuous circuit — not assembled from
per-side strokes with joins. Our skeleton-derived strokes have no equivalent
concept.

**14. Bean / triple run is the light-outline technique.** 14 found:
**2.75 passes** median (p90 3.27 — i.e. a true triple run: forward, back,
forward) at **0.73 mm** stitch length (p10 0.67, p90 1.87). Used for detail
outlines and sketch-tier work where a satin border would be too heavy.

**Instrument limit, stated plainly:** the over-a-fill border detector fired
**zero** times, yet the Hotel Fremont renders visibly show a satin border
sewn over a fill edge. The detector needs a fill-classified run earlier in
the same colour block with an overlapping bbox, and Fremont's fill classifies
as a single run. So the seam-coverage OFFSET — how far a border's centreline
sits from the fill edge — remains **unmeasured**. Do not invent a number for
it; fix the detector or measure it by hand from the render before building
border-over-fill.

## Engine mapping (captured on the since-deleted `feat/satin-rails` branch)

> The statuses in this table are a **snapshot from that branch**, not live
> state. The branch no longer exists, so nothing here has been re-checked
> against `main` — re-verify any row before relying on it, and read
> `MASTER_SCOPE.md` for current status. *(noted 2026-08-21 — branch absent
> from `git branch -a`)*

| Law | Mechanism | Status |
|---|---|---|
| 1 | graph travel + needle-down links + per-stroke underlay→column | built, fingerprint 27 runs / 7 short jumps |
| 2 | `SATIN_ZIGZAG_ABOVE_MM = 2.5` | built, confirmed by census |
| 3 | `_round_corners` + splitter demoted to 90° | built, 0 spraying crosses |
| 4 | interpolated-station outer-rail refinement | built, outer p95 0.47 |
| 5 | `SATIN_MAX_WIDTH_MM = 5.0` | built (browser engine still 3.0) |
| 6 | `_apply_ties` at every trim | built; stitch LENGTH open (0.8 vs 0.45) |
| 7 | `FILL_STITCH_MM = 3.0`; row 0.40 pending interleave answer | partial |
| 8 | 2.5 → 2.0 candidate | not changed |
| 9 | weld pairs through crossings | partial — X handled, overlap semantics not |
| 10 | — | not built |
| 11 | `machine.BORDER_WIDTH_MM` 1.40 | built — measured 1.42 mm median on output |
| 12 | `machine.BORDER_DENSITY_MM` 0.45 | built — measured 0.45 mm median on output |
| 13 | `stage6_border.border_runs`, one circuit per ring | built — `cfg.border="auto"`, OFF by default |
| 14 | `BEAN_PASSES` 3 @ `BEAN_STITCH_MM` 0.73 | built — `cfg.border="bean"`, or auto's fallback |

Laws 11–14 are built but **off by default**, and that is a measured choice
rather than caution: our tatami fill ends both row ends on the shape's edge by
construction, so there is no ragged edge for a border to cover, and the corpus
shows a plain majority of fills going unbordered (18 borders against 21 fill
elements and 150 satin elements in the same 19 files). The seam OFFSET below
is still unmeasured, so `BORDER_SEAM_OFFSET_MM` is pinned at 0.0 — the
boundary condition, not a guess.

## Known limits of the instruments

- Phase census labels fill rows as `R` (row ends are the only reversals);
  fill-specific numbers come from `study_pro.py`'s per-run fill stats, not
  the phase census.
- Element grouping is bbox-overlap within a color block; nested distinct
  elements can merge.
- **The parity trap** (cost three wrong conclusions in one day): emitted
  satin alternates (A,B),(B,A). Never slice stitch lists at fixed parity;
  reconstruct rails pairwise, or measure two-apart distances.
