# Tonal engineering pass — measurements (2026-08-22)

The photo/tonal v1 spec (`docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md`)
names four evidence-driven engineering items "inside the build". This pass
measured all four on committed real artwork in a cloud container and landed
the two the evidence supported. Instrument scripts ran against `run_stages` /
`classify_ribbon` / `detect_ramp_detail` directly; per-region dumps are
reproducible from the commands quoted inline.

## 1. Blend r² floor retune — WRONG KNOB; the speckle gate binds. Parked.

`RAMP_R2_MIN = 0.5` was suspected as the reason the blend tier decomposes
nothing real (the 2026-08-18 probe: 0/27 owl regions, best 0.481). Measured
across 288 regions of six committed real/synthetic fixtures
(`detect_ramp_detail` per stage-4 region, source pixels built the pipeline's
own way):

| verdict | regions |
|---|---|
| `low_r2` | 231 |
| `speckled` | 41 |
| `few_samples` | 13 |
| ACCEPT | 3 (both synthetic ramps + one 12 mm² golden-tee patch) |

- The floor has almost nothing behind it: only **4 real regions sit in
  [0.45, 0.50)** and 7 more in [0.40, 0.45). Lowering it buys a dozen
  borderline regions at most.
- **The speckle gate (`RAMP_SPECKLE_MAX = 0.35`) blocks 41 of the 42 real
  regions that clear the floor**, including nine substantial drone_render
  patches (14–32 mm², r² 0.57–0.92) and one owl region (8.2 mm², 0.59).
  Real-photo texture carries local variance a synthetic ramp does not, so
  the gate — tuned on synthetic ramps vs. flat noise — rejects exactly the
  regions whose global structure the model explains at 0.75–0.99.

**Why parked rather than landed:** admitting those regions changes visible
stitch output on gradient-class designs — the call is Kent's eyes, which is
what the acceptance A/B loop exists for. The candidate change, when the
eyeball loop takes it up: skip or soften the speckle check when r² is high
(a ramp explaining 90 % of variance is well represented by 3–5 shade bands
regardless of fine texture), or measure speckle on the fit's residual.

## 2. Palette-drift resnap — ALREADY SHIPPED; verified firing. Closed.

The spec's "palette-drift resnap" exists as
`stage4_vectorize.revalidate_threads` (fix #6.3, landed 2026-08-11),
emitting `THREAD_RESNAPPED_AFTER_DRIFT`. Verified live on the photo route
(owl, `forced_class="photo_subject"` through the real service): **17 shapes
re-snapped, worst per-region dE00 26.04 → 13.4**. Nothing to build; the
spec item predates confirmation that the existing pass covers the photo
route.

## 3. Sub-mm satin → run, photo lane only — LANDED.

Live defect 2's gated fix, as `docs/dt-first-verdict-2026-08-11.md` §4
proposed and `docs/satin-gate-attribution-2026-08-16.md` §7 constrained —
with §4's own landing conditions consciously superseded, not skipped: its
suggested 0.8/1.0/1.2 sweep "against the corpus scorecard" is barred twice
over (gate 1 owns the constant's value; spec decision 1 rules the scorecard
non-authoritative for tonal work), and its "sew-out of a handful before the
default flips" is phase-5 territory under the sew-out-accepted-as-is
ruling. Do not re-derive that sweep as owed work — the retune waits on
cloth, full stop. What replaces those conditions: the acceptance A/B should
include at least one sub-mm-hairline photo so the floor's visible effect
passes Kent's eyes.

- `classify_ribbon` gains a `photo_width_floor` verdict: a shape that
  EARNED satin (including via the promoted-ribbon path) whose **doubled p90
  medial width < 1.0 mm** reroutes when `design_class` is a photo class.
  The constant is Law 31's printed number **adopted verbatim, not swept** —
  ROADMAP gate 1 names the satin width floor a fabric question, so its
  value is a citation, not a calibration.
- Stage 7's auto ladder makes one `classify_ribbon` call (identical
  computation to the old `is_satin_candidate` bool) and sends
  `photo_width_floor` shapes to `run_outline` on the artwork polygon — the
  same rescue path and no-compensation reasoning tiny shapes already use.
  Stage 5 follows automatically (`is_satin_candidate` wraps the same
  verdict), matching the treatment an explicit `tier:"run"` override gets.
- **The gate is the photo classes and nothing wider, and the class
  measurement is why:** `drone_render`/`summit_badge` — where the 19
  sub-mm-satin corpus regions live — classify **gradient** under default
  routing, and so do 6 of the 7 real customer logos where the reroute is
  disproved (61/64 of their sub-1.0 mm satins are pro-correct). No
  class-level gate can separate those two populations today; the photo
  lane — reachable via the "This is a photo" toggle — is the one lane
  where the defect population is reachable and the disproof population
  effectively is not. The 7th logo IS the edge, and it was measured, not
  assumed: `logo_script_tires.png` misroutes to `photo_scene` (the known
  stage-0 bug its fixture exists to pin) — and produces **zero**
  `photo_width_floor` verdicts there (6 regions, none earned-satin under
  the floor), so even the one disproof member inside the gate is
  untouched. Two hedges stay on record: stage 0 flips routing with export
  resolution on 13/30 corpus images, so "not reachable" holds at measured
  resolutions rather than by construction, and the failure direction if a
  flat logo ever does slip in is soft — a hairline sews as a bean run
  (lighter look) instead of satin, never the snag/perforation direction.

**Measured on the photo route** (forced `photo_subject`, committed
fixtures), two populations the independent audit insisted be kept apart:

- **Sub-floor verdicts** (`classify_ribbon` over every region): drone_render
  29, summit_badge 24, owl_kent 5 — 58, columns 0.23–0.97 mm.
- **Emitted-stitch reroutes** (shapes whose plan actually changes):
  drone_render **18**, summit_badge **9**, owl_kent **2** — **29**. Of the
  other 29 verdicts, 8 are never-sewn regions and 21 already sewed as
  outline runs via the 2.25 mm² area rescue — the floor and the rescue
  agree there, which is corroboration, not double-counting.

The stitch-geometry audit (independent re-measure against pre-change
modules loaded from git blobs) confirmed: all 29 rerouted shapes sewed
satin before the change (17 with a median SEWN cross under 1.0 mm; stage
5's pull comp widened the rest — the classifier reads the artwork width,
deliberately, same as the satin call itself); every rerouted shape's run
now traces the artwork outline at 0.0000 mm deviation; the boundary
straddles the floor on real data (highest floored value 0.966 mm, lowest
kept-satin 1.003 mm); on clean synthetic bars the DT metric over-reads
geometric width by ~+0.19 mm, so the effective geometric floor is ~0.83 mm
— conservative in the keep-satin direction. Flat and gradient lanes: true
default routes byte-identical pre vs. post, and the full suite reproduces
the documented 3-failure golden set exactly.

**What stays open:** the default-routing manifestation. Under stage 0's
current verdicts drone/summit sew their sub-mm satin unchanged — fixing
that needs the content discrimination stage 0 lacks, which is phase-2
framing work, not a wider gate here.

## 4. Sequencing trim thrash — measured; no gate-clear lever. Parked.

Owl through the photo route at HEAD (with item 3 landed): 49 blocks over 28
distinct threads — **21 thread revisits** (12 threads sew in 2–5 separate
blocks; 48 machine color stops against a 27-stop minimum) — and **121 of
215 trims are intra-shape** (the top blocks: 164 runs / 4 shapes / 22
trims; 70 runs / 1 shape / 17 trims).

- The revisits are `depth_sort_layers` doing what it is designed to do
  (background→foreground, dark→light, details last). Reordering trades
  depth correctness for stops — quality-visible, so it belongs to the
  eyeball loop, with the **48-stops-per-portrait** number put in front of
  Kent as an acceptance criterion in its own right.
- The intra-shape bulk is the same class defect 6 attributes and
  `chain_links` (gate-1 frozen, permanently) is the measured lever for;
  every gate-clear alternative measured ≤9 % there. Nothing new to land.

## Also fixed on the way: SAM2 prewarm cached truncated checkpoints

Twice in this container, `sam2_worker.py --prewarm tiny` reported
"checkpoint cached" after the proxy ended the stream early — 136.9 MB and
140.8 MB of a 156.0 MB file — because urllib surfaces early close as
ordinary EOF and the only guard was `size > 0`. Every later SAM2 job then
died with torch's "failed finding central directory", i.e. the exact
poisoned-cache outcome the function's docstring promises never happens.
`_ensure_checkpoint` now enforces the server's Content-Length
(`tests/test_sam2_prewarm.py`); with the complete checkpoint, the isolated
venv runs real jobs in this container (`PHOTO_SAM2_SEGMENTED`, 84 regions
on the owl A/B).
