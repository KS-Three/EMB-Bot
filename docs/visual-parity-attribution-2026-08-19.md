# Why ours looks worse than the pro's — attributed, kill-tested, sized (2026-08-19)

Kent asked, looking at the ranking sheet: "the output doesn't look as good as
the professionally digitized logo, why?" This is the answer, produced by two
fan-out passes over the 15-design real-art lane
(`docs/edge-coverage-2026-08-19.md`'s corpus) plus a causal experiment. Every
number below was independently re-derived by a second agent before it is
quoted here — see "Method" for what that means and its limits.

**Bottom line, and it corrects an earlier guess in this session:** the war is
in **framing and small-shape survival**, not stitch planning. Two mechanisms
neither routing nor density nor colour touch — the pipeline routing flat art
into the photo lane, and stage 3 discarding small letterforms — outrank
everything else. A causal experiment (below) that fixed every un-gated
stitch-planning lever at once left the shape gap untouched, confirming this
independently.

---

## Method

Two fleets, same discipline both times: **N agents propose, an equal or
smaller number of skeptics try to kill each proposal**, default assumption is
that a claim overstates until re-derivation proves otherwise.

- **Attribution fleet** (20 agents): one per design (15) reads `art.png` /
  `pro_render.png` / `ours_render.png` plus the raw stitch CSVs and blocks
  JSON for that design, lists every visible difference a customer would
  notice, and must attribute each to a mechanism **with a number from the
  stitch data**, not an impression. 5 skeptics then re-derived the top-ranked
  mechanisms from the raw CSVs independently.
- **Deep-dive fleet** (10 agents): one lane per mechanism, forced to read the
  repo's own prior art first (`MASTER_SCOPE.md` Measured negatives, the
  relevant `docs/*.md`) before proposing a lever, so a rejected idea cannot
  resurface. A skeptic per lane then re-ran at least one cited measurement.
- **Oracle transplant**: a causal experiment, not a study — see §4.

**What survived skepticism is marked; what didn't is corrected inline, not
hidden.** Two of the five deep-dive proposals had their own numbers corrected
by their skeptic (M1, M2 below) — the corrected figure is what's quoted here,
not the original.

**Limits, stated plainly:** this is 15 designs, 3 knockout/low-dpi, all from
one shop's corpus. Severity scores are per-agent 1–5 judgment, summed — a
ranking signal, not a calibrated scale (gate 4: no quality claim on a raw
number). Renderer colour palette is a known artifact and was excluded from
every finding.

---

## 1. Ranked mechanisms, by summed visual damage

| Rank | Mechanism | Severity (summed) | Designs hit | Skeptic verdict |
|---|---|---|---|---|
| 1 | **M10 — flat logos routed into the photo/gradient lane** | 56 | 8 of 15 (10/15 show the routing warning; 8 show visible damage) | CONFIRMED |
| 2 | **M9 — small lettering discarded** | 54 | 10 of 15 | CONFIRMED |
| 3 | **M3 — flat colour / enclosed background not sewn** | 44 | 6 of 15 | CONFIRMED |
| 4 | **M2 — fragmentation (excess trim breaks)** | 42 | 13 of 15 | CONFIRMED, sizing corrected |
| 5 | **M4 — thin fills (tatami under pro density)** | 39 | 10 of 15 | CONFIRMED |
| 6 | M1 — satin/fill misrouting | 31 | 9 of 15 | CONFIRMED lever, sizing corrected |
| 7 | M6 — edge starvation | 16 | 9 of 15 | OVERSTATED — half is M3 in disguise, see §2.6 |
| 8 | M12 — texture/sequencing | 13 | 5 | not deep-dived |
| 9 | M8 — uniform stitch angle | 11 | 5 | not deep-dived |
| 10 | M7 — underlay differences | 11 | 4 | not deep-dived |
| — | M5 — no borders | 3 | 1 | CONFIRMED lever exists, low corpus-wide severity |
| — | 8 one-off `NEW:` mechanisms | 2–4 each | 1 each | not pursued — see §5 |

---

## 2. Each mechanism: what it is, and what lever survived the killer

### 2.1 M10 — flat art routed into the photo pipeline (rank 1)

**What a customer would see:** whole regions rendered as sparse diagonal
hatching or dither instead of solid fill — `tires_hat_3d`'s entire "ires"
letter body, `gaulke_roofing_hat`'s sun disc, both read as see-through
scribble. On `gaulke_roofing_lc`, the white background block lays **94.7% of
its thread on non-ink background** — the classifier decided flat vector art
was a photograph.

**Verified trigger:** not low dpi. `hotel_fremont_hat` misroutes at 686 dpi.
The audit's attribution is anti-aliasing / JPEG ringing / alpha-edge noise
manufacturing intermediate tones that read as gradient — **10 of 15** real
designs carry the `CLASSIFIED_GRADIENT` / `PHOTO_SEGMENT_REGION_COUNT` /
`PHOTO_PALETTE_SELECTED` warning trio, matching
`docs/classifier-misroutes-real-logos-2026-08-15.md` exactly.

**This is ROADMAP engine-track item 2 (Framing).** Its exit condition: "the
same artwork routes the same way at any export resolution, and real logos
reach the lane their content actually is."

**Settled by the war-dive fleet (§6): gate 2's precondition is NOT met.**
PR #177 (`photo-tonal-v1`, merged) was checked file-by-file in both
checkouts — its only testdata change is one gitignored, empty
`acceptance/README.md`. No committed tonal artwork exists. Stage-0
recalibration stays blocked until Kent drops 4–5 real tonal customer files via
the pull-corpus path. **But a lever exists that does not need that
artwork** — see §6.

### 2.2 M9 — small lettering discarded (rank 2)

**What a customer would see:** sub-4mm text reduced to scratch marks or
vanishing entirely. `hotel_fremont_patch`'s "EST", "1895", "THE", and the
"EAT | STAY | PLAY" tagline — the pro sews all four as crisp small lettering
(70–444mm of thread per element); ours retains **0–27%** of that thread.
`precision_drone`'s "AND DRONE" is gone.

**Verified mechanism:** stage 3's absorb/drop-below-sewable-area path.
`ABSORBED_SMALL_SHAPES` fires; `hotel_fremont_patch` alone absorbs 14 regions
under 5 mm² (40 mm² total). These regions die before stage 7's run-tier
rescue ever sees them — they're gone by the time the rescue logic runs.

**No lever proposed yet.** This mechanism was only crowned #2 by the
attribution fleet *after* the first deep-dive round launched — a war dive on
M10+M9 together is queued as the next fleet (see "Next" below), tasked with
finding the exact threshold that kills these regions and what the pro actually
does at that scale (measured, not assumed to be micro-satin).

### 2.3 M3 — flat colour, enclosed background unsewn (rank 3)

**What a customer would see:** every Becker design sews in **one colour**
against the pro's 2–3; letter counters and banner fields carry **1–4% of the
pro's thread density** (e.g. `becker_hat_small` counters 0.23–0.32 mm/mm² vs
pro's 7.29–8.26). `precision_drone`'s drone — the subject of the design — is
invisible, absorbed into one flat dark fill.

**Confirmed lever, already shipped as code in this session (§3).** The
`enclosed_colour_unknown` flag has existed since defect-1 work but had zero
production readers — it was computed and never surfaced. The killer verified:
one setter (`stage4_vectorize.py:466`), zero readers, before this session's
fix. Measured worth: **+8.0 score per Becker-class design**, and the killer
independently reproduced the enclosed-area numbers on 5 of 6 named designs.

**Ceiling, stated honestly by the killer:** this fixes the *warning-followed*
path only — a user who sees the flag and recolors. The automatic path (no user
action) stays bare. The deferred garment-colour question is untouched.

### 2.4 M2 — fragmentation (rank 4)

**What a customer would see:** the pro's rope border sewn as **one continuous
run of 1,294mm**; ours as **196 separate runs, median 3.9mm each** — reads as
scattered pencil scribble instead of a solid band. Present on 13 of 15
designs, the most widespread mechanism found.

**Lever, and the correction that matters:** `_graph_travel`'s cursor-side snap
(`stage6_satin.py:2145`, call site `:2355`) fails when the needle's actual
position — often a millimetre or two off the stroke web after a cap extension
— can't snap within a strict 0.8mm tolerance, killing the whole walk and
forcing a trim. The original sizing claimed **~1,409 declined breaks**; the
killer re-ran the real 15-design lane and got **1,098 trim breaks vs the pro's
162 (6.78x)**, and sized the actual fix at converting **~47 breaks (−4.3%)**,
*no design worse*. One factual correction the killer also caught: the proposal
claimed all five Becker designs show zero successful travel walks —
`becker_beanie` shows 1 success in 38 calls, not zero.

**This is a secondary lever, and the doc says so plainly:** `chain_links`
(blocked on the sew-out, gate 3) and the pro's float-over-trim policy
(`trim_at_mm`, gate 1) own roughly 950 of the 1,098 breaks. The snap fix is
real, small, and already shipped as code (§3).

### 2.5 M4 — thin fills (rank 5)

**What a customer would see:** fabric visibly showing through fills — every
hatched letter on `tires_hat_3d` starved to a third of the pro's thread;
`mfab_lc`'s letter limbs show white gaps.

**Confirmed, and it has a clean signature the killer specifically validated:**
our own satin blocks measure 5.5–6.8 mm/mm² — *indistinguishable* from the
pro's fills. The starvation is tatami-specific, exactly Law 19's prediction
(pro density convention counts same-direction rows; our tatami is ~2x light
by that convention). **Gate 1 blocks the fix** — `fill_row_mm` is a physical
constant, sew-out-gated. The oracle transplant's arm 4 (§4) rendered what the
fix would look like without shipping it.

### 2.6 M1 — satin/fill misrouting (rank 6, was my initial top guess)

Ranked 6th by verified visual damage, not 1st as I predicted before the
fleets ran — worth stating since I was wrong.

**Lever, corrected by the killer:** per-stroke mixed emission (one shape,
satin strokes + fill remainder, using the shipped classifier constants inside
`extract_strokes`'s own decomposition — no new thresholds). Sizing on 415
touched shapes: pooled cell Cohen's kappa **0.137 → 0.185**. **The killer
caught a real error in the original framing**: the proposal quoted "1,409 of
4,708 pro-satin cells declined" as the post-promotion residual; that number
used a filtered numerator over an unfiltered denominator. The correct,
apples-to-apples figure is **2,143/4,708 = 45.5%**, barely moved from the
pre-promotion 46.6% — the shipped promotion's real gain was the kappa
improvement, not a reduction in declined-cell mass. The lever still holds
(OVERSTATED, not REFUTED) — the corrected kappa gain is real and reproduced
byte-identical by the killer.

### 2.7 M6 — edge starvation (rank 7, this branch's own prior finding)

The killer's finding here is the sharpest correction of the day: **21 of the
44 "starved" shapes from `docs/edge-coverage-2026-08-19.md` are deliberate
enclosed-background knockouts** (`stitched=False`, `BACKGROUND_ENCLOSED`) —
the same mechanism as M3, correctly *not* sewn, not a defect. Independently
reproduced on `becker_chest_small`: the full pipeline re-run matched the
recorded 4,556 stitches exactly, and the tail shapes were confirmed
`enclosed_background=True, stitched=False`.

**The remaining 22 shapes (~116mm of bare arc) are real** — intra-satin
coverage loss where `report["empty"]=False`, so stage 7's rescue never fires
even though a real gap exists. **Important prior art the killer caught:**
"satin residual repair" is **not** untried. `docs/pro-parity-lane-reports-2026-08-14.md`
§C already built and shipped-then-unlanded a corridor-difference residual
patcher, judged not worth landing on an instrument later found to be blind to
bare fabric. Any future work here must cite that lane and reuse its landed
lessons (shape-id suffix convention, sew-patch-immediately-after-column, or
trims/1k blows the 4.1 ceiling) rather than re-derive them.

### 2.8 M5 — no borders

Confirmed lever exists (§3, already shipped): the two law-41 constants
(`BORDER_WIDTH_MM` 1.40→1.70, `BORDER_DENSITY_MM` 0.45→0.40) were adjudicated
and never applied. Low corpus-wide severity (sev 3, 1 design) because
`cfg.border` stays off by default — law 39 still governs that call. The
killer additionally found a predictor for *which* shapes the pro borders:
tatami fills at MCC 0.707 (131 columns measured), while satin-classified
shapes almost never get one (4/45, all decorative rings) — a genuine new
finding, not yet built into anything.

### 2.9 One-off `NEW:` mechanisms

Eight single-design findings the catalog had no id for — satin zigzag pitch on
a 3D-puff design, low-dpi contour quantization, silhouette overshoot, a
gradient-palette letterform fracture on `precision_drone`. Each scored 2–4,
one design apiece. Not pursued; listed so nobody re-discovers them from
scratch. Full text in the workflow journal (see "Where the raw data lives").

---

## 3. What shipped today

Three CONFIRMED, low-risk levers were implemented on branch
`claude/quick-wins` (cut from `origin/main`, TDD, full suite green at the
known 3-Windows-golden baseline, reviewed):

1. `_graph_travel` cursor-side snap retry (M2) — converts an estimated ~47 of
   1,098 trim breaks; unverified until re-measured in a pinned worktree.
2. `enclosed_colour_unknown` wired service → wire → Studio's Layers panel
   (M3) — surfaces an existing flag through the already-shipped restore path;
   no default changed, no engine behaviour changed.
3. Law-41 border constants applied (M5) — `BORDER_WIDTH_MM` 1.70,
   `BORDER_DENSITY_MM` 0.40; dormant, since `cfg.border` still defaults off.

None of the three touch a ROADMAP hard gate. None flips a default. Full
detail, PR link, and verification status: see the branch's own commits.

## 4. The oracle transplant — a causal check, not another study

Separately from the two fan-outs, three designs were rendered through four
cumulative arms — stock, +the pro's own per-shape satin/fill verdict forced
in, +enclosed background on, +2x fill density (a probe, not a setting; gate 1
blocks shipping it) — to see causally how much of the visual gap the
un-gated/probeable levers actually close.

**Result: coverage closes, shape does not.** `becker_chest_small`'s total
thread reached **100% of the pro's** (arm 4 / pro = 1.00) with all three
levers stacked, and the letterforms were still visibly wrong — mushy strokes,
crossing satin directions. `precision_drone` only reached 52% because most of
its area is satin, which `fill_row_mm` doesn't touch. **This independently
confirms §1's ranking**: the top two mechanisms (M10, M9) happen in stages
0–3, before any stitch is planned, and no stitch-planning lever can reach
them. Also worth noting for future probes: pushing density past matching the
pro's total does not keep helping — the render rewards more thread
indefinitely, but preflight's own coverage-stack thresholds
(`COVERAGE_WARN_UNITS` 2.5 / `COVERAGE_BLOCK_UNITS` 3.5) say cloth does not.

## 5. Next

Superseded by §6 — the war-dive fleet landed the same session. M10 and M9 are
no longer lever-less.

## 6. War dive — M10 and M9 both have real levers, and they must ship together

A second deep-dive pair, same discipline (proposal, then a skeptic whose
default is to kill it), targeted specifically at the two mechanisms §1–§2
ranked highest with no lever yet.

### 6.1 M10 — gradient-lane retreat (CONFIRMED, sizing needs a rerun)

**The lever does not need stage-0 recalibration, and does not need tonal
artwork.** `stage6_blend.detect_design_ramp_angle` already computes a best-of-6
r² fit — a measure of whether a "gradient"-classified design actually has
global tonal structure — and already discards it after extracting an angle.
The lever: expose that r², and when it's below the *existing, already-
calibrated* `DESIGN_RAMP_R2_MIN` (0.4, set 2026-08-03), dispatch the design
down the flat lane's ordinary path instead of the blend lane. Stage 0's
classifier is untouched, byte-for-byte — the retreat happens one stage later,
using an instrument that already exists for a different purpose.

**Separation is real:** the ten misrouted designs (six unique artworks —
becker's hat/lc pairs share art) read r² 0.003–0.325; the corpus's actual
gradient fixtures read 0.915–0.999. Nearest miss (bridge, 0.325) sits well
clear of the nearest true-ramp reading (0.835). **Scale-invariant** — the
killer's own resample sweep (0.5×/1×/2× LANCZOS) found zero decision flips
and ≤0.05 r² drift, which is the exact resolution-dependence that killed all
four prior stage-0 attempts, confirmed absent here.

**What's NOT yet true, per the killer's correction:** the sizing (+4.85 mean,
corpus 42.5→~45.7) is a **pre-#177 estimate** — measured 2026-08-15, before
`photo-tonal-v1` reworked `pipeline.py` and stage 7 substantially. It needs a
rerun on current `main` before it's quotable. And this is narrower than
ROADMAP item 2's full exit condition: it fixes gradient-vs-flat routing
outcome invariance, but **stage 0 itself stays resolution-broken** — a design
can still be pushed into `photo_scene` at low enough resolution, which this
lever doesn't touch.

**Two costs that need your explicit sign-off, not mine:**
- `hotel_fremont_hat` scores **−4.3** under the retreat. Its byte-identical
  sibling `hotel_fremont_patch` gains **+8.1** on the same fix — the delta is
  a property of which pro reference file each one is scored against, not the
  artwork, and the deep-dive doc states plainly that no in-engine rule can
  split two identical files differently.
- `precision_drone` — the only artwork in this corpus with genuine
  ground-truth tonal content — also retreats (r² 0.13–0.31), because the
  blend tier has never actually shaded any of its 26 regions anyway (0/26,
  `blend-tier-never-fires-2026-08-15.md`). Retreating it costs nothing today
  but is a bigger philosophical call: it's this corpus's one piece of
  evidence for gate 2 ever unblocking, and this lever routes around needing
  it rather than exercising it.

### 6.2 M9 — text-line exemption, and why it cannot ship alone (CONFIRMED)

**The lever:** in `stage3_segment.resolve_small_regions`, group sub-floor
regions into candidate text lines (≥3 members, consistent height, aligned
baseline, tight horizontal chaining) *before* the absorb pass runs. Members
that clear the run tier's *existing, unchanged* floors
(`RUN_MIN_AREA_MM2=0.16`, `RUN_MIN_LOOP_MM=2.2`) skip absorption and reach
`stage4_vectorize`'s rescue path — which already exists, is already wired to
stage 7's run-outline route, and has simply never received these regions
because they die one stage earlier.

**The sequencing trap the killer found, independently reproduced:** on
`hotel_fremont_hat` forced flat *without* this exemption, `resolve_small_
regions` absorbs all 462 sub-floor regions and rescues zero — **the entire tan
layer, letters and rope border both, drops to 0mm of thread.** That means
**shipping M10's routing fix alone would make this specific defect worse**,
not better. M9 is not an independent nice-to-have next to M10 — it is the
mandatory second half of the same change, and the two must land together or
not at all.

**With both:** 142 regions exempted, 131 rescued as bean-run outlines,
tagline recovers to 381mm of 614mm pro thread (62%), "EST 1895" to 102mm of
414mm (25%) — legible outline text where there was previously nothing, still
short of the pro's micro-satin fill (a separate, later lever). Cost: **+23%
stitches, an extra colour block, more trims** — working against the M2
fragmentation defect this same corpus already carries at 3.1× the pro's rate.

**Standalone value, as things ship today (gradient-routed, no M10 fix):**
small — about +89mm on hotel's tagline (~7% of the missing thread).
`precision_drone` sees zero effect standalone; its letters are destroyed
further upstream, not by this absorb path.

### 6.3 What this means for sequencing

Two real, gate-clean levers exist for the two top-ranked mechanisms. Neither
needs a sew-out, a stage-0 change, or a default flip. But they are coupled —
M9 must land with or before M10's routing change — and M10's sizing needs a
post-#177 rerun before it's a number anyone can act on. Both carry a named
cost on a specific design that only Kent can decide to accept.

Full proposals and kill-audits: workflow run `wf_bd182562-e42`,
`<session dir>/subagents/workflows/wf_bd182562-e42/journal.jsonl`.

## Where the raw data lives

- Attribution fleet (20 agents): workflow run `wf_0db1cd06-96e`, journal at
  `<session dir>/subagents/workflows/wf_0db1cd06-96e/journal.jsonl` — one
  `"result"` line per agent, full per-design differences list with every cited
  number.
- Deep-dive fleet (10 agents): `wf_6551a83c-853/journal.jsonl`, same format —
  full proposal + kill-audit per mechanism, including everything summarized
  in §2 above with the exact re-derivation commands the killers ran.
- Oracle transplant (4 agents): `wf_6abe7399-bcf/journal.jsonl`; rendered arms
  and the sheet itself under a scratch directory outside the repo (not
  committed — regenerate from the rig if needed, `rig.py` in that same
  scratch tree).
- These journals live under Claude Code's session directory, not in this
  repo. They will not survive a session cleanup. If this attribution is ever
  needed again in detail beyond what's summarized here, re-run the fleets —
  the prompts are reconstructable from this doc's method section.
