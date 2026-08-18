# Curve-fidelity tol ladder — 2026-08-17

Task 2 of `docs/superpowers/plans/2026-08-17-shape-fidelity.md`, plus the
outlier chase Kent promoted at the decision gate. Answers: does lowering
`simplify_tol_mm` (default 0.2, `config.py:343`) improve how faithfully the
engine's coverage follows the customer's artwork on the real corpus — and
where does the large residual boundary error actually live?

**Verdict: leave `simplify_tol_mm = 0.2`.** Tighter tolerances buy no
measurable art-fidelity (differences ≤0.04 mm, inside raster noise), cost
+2.6% stitches at 0.10, and 0.05 hard-kills one design. Kent accepted
2026-08-17 and promoted the outlier investigation, whose findings are below.

> **Correction notice:** this doc's first commit (`820fce2`) reported mean
> boundary distances that were ~2–3× inflated on fill-heavy designs by a
> rasterisation artifact in the instrument (pinholes manufactured by 4 px
> paint over the engine's ~3.98 px fill-row advance), and read "worse when
> tighter" from numbers the artifact dominated. The artifact was found the
> same day by the outlier probe, fixed (`artfidelity.PAINT_W_MM = 0.50`),
> and every number here is from the corrected instrument. The
> recommendation survived the correction; its stated reason changed from
> "worse" to "no benefit". `tires_hat_3d`'s "3× degradation at 0.05" in the
> first version was pure artifact — corrected, it is flat (0.267/0.276/0.269).

## Method

Three arms through `prep_both.py` (engine at `73f37da` + this lane's
instrument commits; shipped routing, no forced class; garment from filename),
one pinned worktree, one `PRO_PARITY_OUT` per arm, sequential:
`PRO_PARITY_SIMPLIFY_TOL` ∈ {0.2, 0.1, 0.05} (`c3db6ab`'s harness hook).
Measured with `enginefidelity.py`: engine-vs-art IoU at best shift, symmetric
Hausdorff and mean boundary distance in mm at that alignment. Logs:
`parity_out_ladder/ladder.log`; reproduction: `parity_out_ladder/ladder.ps1`.

**Denominator note:** `gaulke_roofing_hat` FAILS outright at 0.05
(`GEOSException: TopologyException: side location conflict` during prep —
RDP-preserved near-degenerate vertices produce a polygon a downstream
shapely op refuses). All paired numbers are over the **same 14 designs**
in every arm; per-arm CLI means are not comparable and are not quoted.

## Paired results (n = 14, corrected instrument)

| metric | 0.20 (shipped) | 0.10 | 0.05 |
|---|---|---|---|
| mean boundary distance (mm) | 1.169 | 1.146 | 1.126 |
| mean Hausdorff (mm) | 10.43 | 10.30 | 10.10 |
| mean art_iou | **0.802** | 0.797 | 0.797 |
| total real-lane stitches | 127,777 (15) | 131,161 (15) | n/a (14) |
| prep wall time (s) | 367 | 403 | 433 |

Movements are ≤0.04 mm / ≤0.005 IoU — below what the 10 px/mm raster can
support as signal, and per-design directions are mixed (`becker_hat_large`
haus improves 4.7→1.9 at 0.10 while `bridge_hat` worsens 15.5→18.4). Against
that: the 0.05 GEOS kill, +2.6% stitches at 0.10, +18% wall time. RDP sagitta
on real-size curves (~0.1–0.15 mm) sits inside the 0.40 mm thread width —
the same-day synthetic demo that showed visible smoothing at 0.05 was seeing
screen pixels thread would swallow on fabric.

## Where the large Hausdorff actually comes from (outlier chase)

`boundarywhere.py` (committed alongside) renders art vs engine outlines with
the worst-distance points marked. Attribution of every 15–23 mm outlier:

1. **Instrument blind spot — light ink on dark ground** (`hotel_fremont_*`,
   `bridge_*`, worst residuals). `art_mask`'s ink test (alpha, else
   dark-sum < 720) reads a dark logo as SOLID ink, blind to white text and
   details inside it. The engine correctly leaves those white details unsewn;
   their hole edges then measure 15–21 mm from the nearest art boundary (the
   logo's outer border). The renders show it plainly: green art outlines
   exist only at the outer border, red engine outlines trace the interior
   text/details. **Engine behaviour is correct; the instrument cannot see
   light-on-dark artwork ink.** Known limitation, now documented in both
   instruments' terms — a fix (luminance-contrast ink test) is future
   instrument work, not engine work.
2. **Known re-composed layout** (`gaulke_roofing_*`): art_iou 0.25 with
   eng_extra 0.75 and the shift search pinned — the pro re-composed this
   logo; inherited artfidelity limitation, reads low by construction.
3. **Open, minor** (`precision_drone`): one real engine-side column at
   x≈18–19 mm, worst 15.0 mm, unexplained. Small enough to note, not chase.

Net: after correcting the pinhole artifact and accounting for the light-ink
blind spot, **no large-Hausdorff outlier is evidenced engine error**. The
"unsewn enclosed background / displaced elements" hypothesis from this doc's
first version is withdrawn for these designs.

## Decisions and dispositions

1. **`simplify_tol_mm` stays 0.2** (Kent, 2026-08-17). No golden churn, no
   Studio override, no arc-aware refinement on this evidence.
2. The 0.05-arm GEOS invalidity is a latent config-space bug: harmless at
   the shipped default, fatal under any future tol reduction. Noted here;
   not fixed in this lane.
3. Instrument follow-up (future, small): a contrast-based ink test in
   `art_mask` so light-on-dark artwork measures; until then, treat
   `hotel_fremont_*` / `bridge_*` boundary numbers as floors, not readings.

Negative result recorded per house convention — the lever is measured dead,
the outliers are attributed, and nobody has to re-run this to relearn either.
