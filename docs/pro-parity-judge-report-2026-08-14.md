# Pro-parity: the five-lane judge report (2026-08-14)

Independent judge over five parallel satin-starburst lanes. Every lane's numbers were
re-measured by the judge from scratch; all five reproduced exactly. Verbatim below.

All runs complete. Here is the verdict.

---

# JUDGE REPORT — satin starburst, five lanes

## 1. Ranked table

| # | Lane | Claimed | **Verified** | Visual verdict (my own renders) | Proof-5 Δ | **Held-out-7 Δ** | New test failures |
|---|------|---------|--------------|--------------------------------|-----------|------------------|-------------------|
| 1 | **D** — route letterforms to one-angle fill | PARTIAL | **PARTIAL, real — but OVERFIT** | Fan **eliminated** at every becker junction I checked, incl. one D under-claimed. Nothing on mfab_lc/fremont. | **+1.76** | **−0.60** (two −5.8/−5.6 regressions) | **0** (verified full suite) |
| 2 | **B** — never build a column on a corner fork | PARTIAL | **PARTIAL, real, narrower** | Fan **eliminated at corner forks while staying satin** — the only lane that does both. Other corners in the same letter still fan. | −0.18 | **+0.08** | 1 (`test_chaining` trim rate, confirmed) |
| 3 | **C** — sew the junction as its own patch | PARTIAL | **WEAK / mostly noise** | Worst point-convergences soften to broad wedges, field stays radial. My fan metric gets **worse on 3 of 5**. | +0.24 | +0.14 | **0** (verified full suite) |
| 4 | **A** — directional cross-section width | NO | **NO — honest negative** | Fan fully intact. | −0.08 | n/m | **7** (golden guards) |
| 5 | **E** — outline rail-pair decomposition | NO | **NO — honest negative, inert by default** | Fan intact; worse on fremont when routed on. | 0.00 (route off) | n/m | 0 |

**Every lane's numeric self-report reproduced exactly in my hands.** No lane inflated its score. Baseline reproduced to the tenth on all five designs (72.9 / 69.7 / 57.7 / 71.5 / 71.6, mean 68.68). That is worth saying after three iterations of over-claiming.

## 2. Independent verification findings

**Method.** Fresh `PRO_PARITY_OUT` per lane; `prep_all.py` + `scorecard.py` run by me from each worktree at the stated commit (all five exist, all trees clean, module resolution confirmed to hit the worktree's `digitizer_core`, not the editable install). I wrote my own stitch-segment renderer and my own **fan detector** — a pivot is a 0.45 mm cell touched by ≥7 stitch segments spanning >55° — reading only `ours_stitches.csv`, i.e. no lane's code.

**Calibrating the fan metric against the pro** (this matters — the pro is not zero):

| design | PRO | base | B | C | **D** |
|---|---|---|---|---|---|
| becker_lc_large | 91 | 259 | 255 | 232 | **64** |
| becker_hat_large | 77 | 141 | 126 | 201 | **85** |
| becker_chest_small | 112 | 193 | 249 | 177 | **73** |
| mfab_lc | 372 | 236 | 306 | 311 | 272 |
| hotel_fremont_patch | 387 | 187 | 183 | 197 | 187 |

On the three designs where the pro is fan-free, **D lands at or below the pro's own pivot count**. C and B do not move it (C goes backwards on hat). On mfab_lc and fremont the pro scores higher than we do — the metric is meaningless there, which is itself the finding that those two designs' problem is not the fan.

**What I actually saw.** At becker_lc_large (−4.1, −19.5) the baseline is a textbook ~50-stitch cone converging on one needle hole. **D**: uniform parallel rows, nothing converging. **B**: also gone — replaced by a clean parallel satin column, which is the more professionally correct outcome. **C**: the point is broken up but the whole area is still radial. Same story at becker_hat_large (−19.0, −17.8) and becker_chest_small (−12.1, −19.3). At a *second* chest_small corner, B still fans and D is clean. On **mfab_lc all three lanes are visually indistinguishable from baseline** — heavy spray everywhere. `hotel_fremont_patch` under D is byte-identical (identical scores and identical pivot counts, 187/1610).

**The decisive finding — D does not generalize.** I scored seven corpus designs no lane tuned on:

| design | base | **D** | Δ |
|---|---|---|---|
| tires_hat_3d | 53.5 | 53.5 | 0 |
| golf_hat | 69.3 | 76.3 | +7.0 |
| precision_drone | 62.4 | 59.8 | −2.6 |
| mfab_hat | 76.5 | 75.7 | −0.8 |
| **machine_lc** | 80.4 | **74.6** | **−5.8** |
| becker_beanie | 70.5 | 74.1 | +3.6 |
| **gaulke_roofing_lc** | 79.2 | **73.6** | **−5.6** |
| **mean** | **70.26** | **69.66** | **−0.60** |

B is +0.08 and C is +0.14 on the same seven, with no design worse than −0.9. **D is the only lane that regresses on held-out work, and it regresses hard.**

I traced both regressions. `machine_lc` pro block 0 is `len_p50 3.52 mm` over 4003 mm² — that is **satin**, and D fills it (`typ` 0.82→0.67); my render shows D making that script wordmark *more legible* while sewing the wrong technique. `gaulke_roofing_lc` loses `dir` 0.60→0.48 and `typ` 0.77→0.56 to the fixed 20°. Reading the code confirms the mechanism: `prefers_letter_fill` is **not text-aware at all** — it is "any auto-tier satin candidate with ≥3 skeleton strokes and ≥2.2 mm width", filled at a global constant `LETTER_FILL_ANGLE_DEG = 20.0`, `letter_fill: bool = True` by default.

I then tested whether the angle is the lever: `EMB_LETTERFILL_MODE=auto` (per-shape principal angle) scores **worse on both sets** (proof-5 69.2, held-out 68.8). **The angle is not the problem; the tier decision is.** D also costs +23–31 % stitches (becker_lc 12548→15474 against the pro's 11274 — we now overshoot the pro by 37 %) at 0.20 mm single-direction pitch, which D itself flags as sew-out-gated for pucker.

**Test claims, all confirmed by my own runs to completion (no piping to tail).** Baseline `c91ab60`: **7 failed / 1135 passed** — 5 tesseract/OCR + 2 `photo/enthusiast_logo.png` goldens. Lane **D**: 7 failed / 1140 passed, byte-identical failure set → **zero new**. Lane **C**: 7 failed / 1137 passed → **zero new**. Targeted golden+chaining subset: **A** 9 failures vs baseline's 2 in that subset → **7 new, as A reported**; **B** 3 → **1 new** (`test_chaining_cuts_the_benchmark_fixtures_trim_rate`), as B reported; **E** 2 → **inert**, and E's six score components match baseline exactly.

## 3. Recommendation

**Land B. Do not land D as a default. Do not land A, C, or E.**

- **Land lane B (`3897895`)** after fixing its one new failure. It is the only change that removes a real family of starbursts *while keeping the element satin*, it is +0.08 on held-out with no design worse than −0.5, and it breaks no golden. Its −0.18 on the proof set is almost entirely `und` (columns now reach the artwork edge and carry more centre-run underlay) — a cost, not a defect. Conditions: (a) resolve `test_chaining` 4.55 vs the 4.1 ceiling rather than re-baselining it; (b) a judge must sign off on B's edit to the pinned `test_a_stem_crossing_three_junctions_welds_into_one_stroke` selector — assertions unchanged, but it is a pinned fixture and that is Kent's call; (c) B's `_FORK_NODE_MULT = 1.7` bound is measured to sit between populations that *touch* below 2 mm stroke width, so expect misclassification on tagline-scale text.

- **Keep D's module, flip `letter_fill` to `False` by default.** D is the largest genuine defect removal anyone produced and its corpus measurement (pro direction-coherence R = 0.53–0.98 vs our 0.07–0.34) is the most valuable finding in the whole set — but shipping it on by default trades a +1.76 on five tuned designs for a −0.60 and two ~6-point regressions on seven untuned ones. That is the classic overfit this review exists to catch.

- **B and D are genuinely complementary, and orthogonal in the code**: B is satin *geometry* in `stage6_satin`, D is *tier routing* in `stage7_sequence`. They can stack. But stack them only after D's rule is made discriminative — see below.

- **C is not worth landing as a whole.** +0.24 is inside noise, my fan metric worsens on 3 of 5, and it makes satin shapes emit fill runs (it already broke two tests on that alone; anything downstream grouping by `shape_id` is exposed). **However, C's part (1) — reading arm direction from *outside* the junction blob instead of over 5 skeleton pixels — is separable, mechanistically sound, and I did not isolate it.** Extract it and measure it alone on 12 designs; it may stack with B for free.

## 4. What the next iteration should attack

The missing piece is a **discriminator for satin-vs-fill per element**, keyed on what the pro actually did — D proved the corpus answers this (direction coherence R per region) and then threw the measurement away in favour of a 3-stroke/2.2 mm proxy that fires on script wordmarks the pro satins. Build the rule on the measurement, not the proxy, and validate on ≥12 designs, not 5.

Second lead, unmeasured: A's arithmetic that the fan is **inner-rail collapse at spine curvature**, R ≈ 1.2 w, because `_round_corners` spreads a turn over a window of `k = round(half_mm / spacing)` — about *one* half-width. Spreading over ~3 would take the inner-advance ratio from 0.09 to ~0.56. Nobody implemented it.

Nobody touched small text. `hotel_fremont_patch` and mfab's tagline/"4" are unchanged in all five lanes; fremont's problem is upstream art reconstruction merging letters into blobs, not satin.

## 5. What the five collectively RULE OUT (new)

1. **The starburst is not a width-measurement error.** Proven twice by opposite methods: A measured that `field.half_at` **never binds** (the `floors[i]*1.6+0.2` cap never engages; junction anchors read 2.10–2.16 mm against a 1.75 mm shape half-width — no inflated anchor, no wedge), and E supplied a *perfect* junction-immune width via outline rail-pairing and the design still fanned. **The brief's stated root cause is wrong.**
2. **Outline rail-pair decomposition cannot cover a letterform** — 57 % area coverage; loosening gates to a physically unsewable 9 mm reach / 120° opposition still reaches only 74.9 %. Structural, not tuning.
3. **Per-stroke directional fill is dead.** Pro direction vs our stroke tangent deviates 44–52°; implemented, it scores below both flat fill *and* the satin baseline on 4 of 5.
4. **No junction radius / arm-half-width ratio can classify a junction as a blob** — a right-angle meeting of equal ribbons is intrinsically √2 wider, so a clean T and a bold corner measure the same. Coverage, not size.
5. **Trimming arms back** to make room for a junction element: measured, no help.
6. **Recursing rail-pairing on the residual**: measured, worse than one round.
7. **A single global letterform fill angle is not the lever** (my own test): per-shape principal angle is *worse* than the 20° constant on both the tuned and held-out sets. The loss is `typ`, i.e. the tier choice.
8. **Filling everything** (D's 0.0 mm width floor) costs 2–3 points on fremont and mfab — the width floor is load-bearing, which is itself evidence the rule is a proxy rather than a principle.

Artifacts of this review: renders and logs under `/tmp/claude-0/-home-user-EMB-Bot/b97ff48d-88c2-507a-bc61-93cec7183437/scratchpad/JUDGE/` — `fanmetric.py`, `jrender.py`, `z1_lc.png`, `z2_hat.png`, `z4_chest.png`, `z5_machine.png`, `z6_B.png`, `z9_B_new.png`, and `logs/pytest_{base,laneC,laneD}.log`.