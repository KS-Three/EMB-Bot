# Shape-fidelity findings — Tasks 3 & 4 — 2026-08-17

Companion to `docs/superpowers/plans/2026-08-17-shape-fidelity.md` (Tasks 3–4)
and `docs/curve-fidelity-ladder-2026-08-17.md` (Tasks 1–2). Three verdicts.

## 1. Dot-fusion defect — WITHDRAWN (fixture's fault, engine faithful)

Kent's third circled defect: the Instagram glyph's dot fuses into the frame
corner, in every lane at every tolerance. Pinned by region-ownership probe
(`run_stages` + point-in-polygon on dot centre / gap midpoint / frame stroke):
dot, gap and frame are **one polygon** in both the photo lane and forced-flat
— identical region sets, so the merge is upstream of lane divergence.

Then the source pixels convicted the fixture: at the corner-arc pinch the
synthetic glyph's dot sits **2 clean pixels (0.41 mm)** from the frame's
inner edge, and the anti-aliased halo pixel between them passes the ink
threshold (row-scan: sums 373/667/**765 765**/576/373 across the "gap").
The artwork is genuinely connected in ink terms; the engine segmented what
the pixels say. Kent's real icon PNG very likely carries the same
source-pixel bridge (downloaded logos are anti-aliased and the real mark's
corner clearance is tight) — verifiable against his file on request.

No engine change. The user-facing lesson is already in the Studio's upload
copy: sharp, non-anti-aliased edges digitise best.

## 2. Fragmented-ring absorb — CONFIRMED, worst-case total

The plan's reproduce-or-close attempt reproduced, dramatically. Fixture: a
40 mm checkered ring, 1.2 mm wide, 84 alternating-colour arc segments of
~1.80 mm² each — every segment under the 2.25 mm² floor
(`cfg.min_detail_mm²`), every segment's halo neighbour another doomed
segment. This is the shape a gradient ring takes after quantisation bands it.

Result: **zero sewn regions.** 172 mm² of fully-visible artwork annihilated
by chained absorption; the run reports only advisory `ABSORBED_SMALL_SHAPES`
and `EMPTY_THREAD_LAYER`. `resolve_small_regions`' size test is
individually-per-region and blind to the union: 84 mutually-adjacent
"details" forming one connected 172 mm² structure are not detail.

Landed: `digitizer/tests/test_ring_absorb.py`, xfail `strict=True` per the
scale-invariance precedent — the test going green IS the fix's acceptance
criterion. **Fix design pending Kent** (engine change, so it waits):

- **(a) Chain-merge before the size test** (recommended): union
  mutually-adjacent sub-floor regions first; if the union clears the floor,
  keep it (merging 84 segments into one colour is acceptable; losing the
  annulus is not). Localised to `resolve_small_regions`, no new thresholds —
  the floor stays `cfg.min_detail_mm`-derived per `plans-engine.md:17`.
- (b) Cap total absorbed area per connected structure and stop absorbing
  past it. Simpler, but picks an arbitrary cap — a new threshold, which (a)
  avoids.

## 3. Gap 2 (stage-0 flat-logo misroute) — disposition, no code

The fix path exists and is not code-shaped today. The 2026-08-15 spec
(`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`)
measured and rejected four approaches; its replacement signal (scale-invariant
distinct-colour count) is sited on a boundary that needs **4–5 real customer
artworks with genuine tonal content** — ground truth today is 6 flat + 1
gradient, and one positive cannot site a boundary. ROADMAP hard gate 2 bars
synthetic substitutes (this session's twin-glyph experiment is admissible as
a demonstration, not as calibration evidence). The acceptance instrument is
already landed and waiting: `test_classifier_scale_invariance.py`, 6 passed /
7 xfailed strict. **Getting more real customer artwork remains the
highest-leverage non-code action** (`conventions-memory.md:85`).

Mitigation available without recalibration — proposed, not built: a Studio
**"this is flat art" override** feeding `forced_class=flat`. User-supplied
ground truth, not a stage-0 change, so hard gate 2 is not implicated.
Measured upside on the misrouted set: **+4.85 mean, 8 better / 1 worse / 1
unchanged** (`photo-classifier.md:11`). Two required cautions in any
implementation: forcing flat on *textured* logo art makes it worse (k-means
shatters texture — `scope-history.md:30`), so the control's copy must scope
it to flat-colour art; and `hotel_fremont_hat` (−4.3, labelled flat,
unexplained) stands as the open counterexample. PRODUCT.md scope call —
Kent decides, separately from this lane.
