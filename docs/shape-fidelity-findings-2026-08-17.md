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

### What it is worth on the real corpus (measured 2026-08-17, post-fix)

Both lanes of all 15 real-artwork designs, re-prepped with the fix in the
tree and diffed byte-for-byte against the pre-fix run:

| | |
|---|---|
| `bridge_hat` | 8,244 → 8,400 stitches (+156) |
| `precision_drone` | 6,523 → 6,552 stitches (+29) |
| the other 13 | **byte-identical** |

**The discriminator is NOT the image class.** Ten of the fifteen classify
gradient/photo and only two changed, so "gradient art benefits" — an
intuition this session briefly published — is wrong. Zero of five flat
designs changed, so the gradient lane is necessary but nowhere near
sufficient.

It is not the *number* of small regions either. Traced through
`_chained_small_regions`, counting how many sub-floor regions each design
has and how many the chain rescues:

| design | small regions | rescued by chain |
|---|---|---|
| `bridge_hat` | 199 | **34** |
| `precision_drone` | 71 | **5** |
| `tires_hat_3d` | **791** | 0 |
| `mfab_hat` | 25 | 0 |
| `hotel_fremont_hat` | 10 | 0 |
| `becker_hat_large` | 0 | 0 |

`tires_hat_3d` has four times more sub-floor regions than `bridge_hat` and
gains nothing. The predictor is whether those regions are **mutually
adjacent and together clear the floor** — a fragmented *structure* — versus
isolated speckle scattered across the design. Speckle is correctly still
absorbed; only connected structure is rescued. That is the behaviour the fix
was designed for, and the corpus confirms it discriminates rather than
blanket-rescuing.

Practical read: this recovers real content on ~13% of the current corpus and
provably touches nothing else. It is insurance against silent data loss whose
value rises with fragmented artwork, not a general quality win.

Landed: `digitizer/tests/test_ring_absorb.py` — landed red as `xfail(strict)`
and the xfail removed when the fix made it green, so it is now a regression
guard. **Fix implemented as `_chained_small_regions`** (`stage3_segment.py`),
after two rejected designs worth recording:

- **Rejected — same-layer chaining.** The first attempt only chained regions
  sharing a thread. A banded ring alternates colours, so every arc's
  neighbours are the OTHER colour: the rule saw 84 isolated crumbs and
  chained nothing. Chain adjacency is a question about geometry, not about
  which thread a fragment landed on.
- **Rejected — merging the chain into one region.** Unioning the members
  would sew one colour over another. The shipped fix *rescues* instead: each
  fragment survives as its own region with its colour intact, and stage 4
  still re-tests every one against its own real-geometry floor.
- **Shipped:** size-test connected chains of sub-floor regions against the
  same `cfg.min_detail_mm`-derived floor; a chain that clears it is kept
  as-is. No new thresholds, per `plans-engine.md:17` — the same bar, applied
  to the structure instead of to each crumb of it.

## Next session — two things, in order

**1. Run the full digitizer suite before anything else.** It is the one piece
of verification this lane still owes. Started 2026-08-17, starved by a
concurrent corpus run, killed unfinished — so it has never completed against
the fix.

```
cd digitizer && .venv/Scripts/python -m pytest -q     # ~21 min on an idle machine
```

Judge it against this worktree's recorded baseline at `73f37da`: **8
environmental failures** — 3 Linux-captured goldens
(`flat_lane_byte_identical` and `stage2_photo_segment` on
`photo/enthusiast_logo.png`, `pushcomp` on `logo_whitebg.png-towel`) and 5
needing a `tesseract` binary this machine lacks. Not against zero. Anything
beyond those 8 is this lane's doing. Golden movement is plausible and not
automatically wrong — the fix deliberately changes which regions survive
segmentation — but it is Kent's call, and goldens re-capture on Linux CI,
never Windows.

Do not run it alongside a corpus prep. The two starve each other: the same
suite took 21 minutes alone and was still unfinished after 50 minutes sharing
four CPUs with `prep_both.py`.

**2. New evidence bearing on the tabled gradient work — Kent's call, not a
reopening.** Gradient/tonal work is Phase 4 and Kent re-affirmed the tabling
on 2026-08-17 (`docs/scope-digest/photo-classifier.md:71`, ROADMAP Phase 4).
Nothing here changes that ruling. But the ring-absorb result added a fact the
ruling was made without:

The only two designs the fix recovered content on — `bridge_hat` and
`precision_drone` — are the two whose artwork is photographic. That is
mechanically consistent rather than coincidental: quantisation is what
shatters a smooth structure into a chain of sub-floor fragments, and
fragmentation is precisely the condition the fix rescues. So gradient
artwork is where silent structural loss concentrates.

The honest bound on that claim: 10 of 15 designs classify gradient/photo and
only 2 moved, so "gradient" is necessary but far from sufficient — see the
adjacency table above for what actually predicts a gain. This is one more
input to a decision that is Kent's, not an argument to un-table.

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
