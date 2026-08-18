# Close-out — deep hardening pass, four landed lanes + five build lanes

I re-ran five measurements myself. Everything else below is attributed to the agent that measured it. Nothing was edited or committed.

---

## 1. What is now proven

**Chaining (feat/stitch-chaining @ a63ac1b)**
- The three guards are real and each fails exactly one test, with the exact magnitudes claimed — `_cover_part` defeated → "4.52 mm of link crosses the inside of a shape that only had its outline sewn"; `_laid_cover` defeated → 1.89 mm across a ring's bare material; sewn/laid filter defeated → its own test. Verified twice, independently, by two agents using different methods (scratch archives vs. pytest plugins).
- The run-tier over-promise is genuinely closed: benchmark@90/left_chest `BARE_MM` 0.898 → 0.000 on the shipped probe, `runs` 23 → 19, `jumps` 7 → 11, `trims/1k` 2.63 unchanged. The four refused links became jumps, not trims. Both agents reproduced every digit.
- `logo_alpha` and `logo_whitebg` are **byte-identical** between parent and HEAD — stronger than the report claimed.
- Suite green: **204 passed, 1 warning in 73.03s** (I ran it).

**Contour (feat/contour-fill @ 2009de8)**
- Contour is cheaper than tatami on real artwork: logo_whitebg 2596 → 2263 stitches, DST 8366 → 7364 bytes. Reproduced by two agents at every config tried. (The commit body's "2524 → 2280" reproduces at no config; the test docstring's numbers are the true ones.)
- Contour emits *fewer* sub-1.0 mm steps than the tier it replaces: whitebg 106/2257 vs tatami 307/2590; alpha 273/2853 vs 429/3239. Measured at DST level with a hand-written Tajima parser.
- The dumbbell-vs-bar reach test could not be refuted: bars at 0.41/0.80/1.19/1.20 mm all report `skipped_rings=0` exactly as claimed.

**Push-comp (feat/push-comp @ 57ac804)**
- The directional offset operator is correct to within the DST grid: worst error over 10,512 samples (12 axes × 73 directions × 4 shapes × 3 pulls) is exactly `_COMP_MINOR_MM` = 0.0100 mm, vs. a 0.1 mm grid. A second agent using a marched-face instrument got 0.00548 mm worst. The commit's "0.0023 mm" is understated ~2–4x; the conclusion survives.
- `_grow` is monotone on 2,599 of 2,600 (shape, rotation, pull, axis) combinations; the one failure is a 0.8 × 0.6 mm bar losing 2.2e-04 mm².
- The circularity cut works: with `cfg.satin=True`, DST(dir=off) ≠ DST(dir=on). The flag reaches emitted stitches.

**Appliqué (feat/applique-steps @ a0bb87c)**
- Blast radius is exactly as claimed and better: **80 non-appliqué designs byte-identical, 0 changed**, across all three sha pairs, on two independently built matrices (112 configs each).
- The export tie-in fix is real and non-circular: reverting only `prev = None` in `stitches.py:123` while keeping the export fix makes `plan.stats.stitch_count == sum(raw)` fail at `2242 != 2245`. Six mutations, all caught.
- The C7 correction is right: `tie_run` returns 5 points, `TIE_STITCHES=3`, and the old rule dropped 1 of 5 with distance exactly 0.000000000 in 6 of 6 cases. The prior note's "four landing three" was wrong on both numbers.
- Benchmark table exact on all nine numbers — at `garment_id="hat_front"`, which the report never states.

**law 19 (feat/needle-hole-guard @ 239e42c)**
- The interleave escape hatch is dead, and the direction argument is correct: interleaving *doubles* the sew-order gap, so a sew-order 0.20 implies a true 0.10, never 0.40. Both agents reproduced `sew 0.80 / ratio 2.0 / dRank2 ≈0.98` on a constructed two-pass interleave.
- Our own fill measures as claimed: `FILL_ROW_MM=0.40` → geo 0.400, sew 0.400, coverage 1.00.
- **The three commissioned cap files exist.** I ran `find` — 43 commissioned `.DST` under `scratch_kent/Embroidery Files/`, including all four named. They are invisible from the worktree because `.gitignore:3` is `scratch_*` — the same rule that hides `scratch_corpus`, which the probe *did* read. The "absent from the whole repo tree" claim was a search error, not an absence.
- I measured those cap files with my own pyembroidery-only instrument. The dense objects **cannot be satin and cannot be fans**: traverse spans median 16.0–44.3 mm (max 84.2) against `SATIN_MAX_WIDTH_MM = 5.0` and `MAX_STITCH_MM = 12.1`; 7–15 penetrations per traverse at 2.94–3.47 mm steps (that is `FILL_STITCH_MM`, not a split-satin midpoint); and **both** rail ends wander 31–88 mm along the traverse axis, so neither rail is pinned. They are 2-D boustrophedon area fills.

**dt-first (feat/physics-preflight @ 6677ead)**
- The garment defect is real to six digits: `logo_alpha` 2A/P = 4.997157 vs `logo_whitebg` 5.032691 on the same 10.63 × 9.43 mm block against a 5.0 cap. Same shape sews as 3 satin columns (361 pts) on one artwork and 1 fill (190 pts) on the other. Two agents reproduced it independently with different rasterisers.
- The 21-fixture scoreboard survives a cv2→PIL rasteriser swap on 20 of 21 fixtures. VP90's fixture score is not a rasteriser artifact.
- Nothing is wired in. `grep -rn shape_lens --include=*.py` finds no importer. The commit is two uncollected files.

**Preflight (feat/lettering-underlay @ 3717a64)**
- All 12 guard mutations caught. No dead guard, no untriggerable test.
- The baseline 16-cell grade table reproduces exactly, and the four "after" claims all hold.
- `_FILL_AXIS_MIN` is correctly placed: over 240 real fill runs, |R| min 0.840, so the gate never blinds the instrument to real tatami rows.
- The towel golden failure is provably *not* this lane's: in a tree with zero push-comp and zero chaining code, `logo_whitebg/towel` produces 3445 stitches against a pinned 2888, while the other three goldens match byte-for-byte.

---

## 2. Confirmed broken, still broken — ranked by what it does to a garment

### 1. CRITICAL — chaining sews needle-down thread on bare fabric, on a stock preset, with a green suite
**Lane:** stitch-chaining. **File:** `digitizer/digitizer_core/stage7_sequence.py:138` (`_laid_cover` still returns `p.polygon` whole for the fill and satin tiers).

I built an instrument that shares no code with stage 7, `chain_probe`, or `test_chaining.py`: for every needle-down TRAVEL run, reconstruct the **real sewn path** (`prev_run.points[-1] → link points → next_run.points[0]`), densify at 0.05 mm, and measure distance to the union of every emitted non-travel stitch polyline in the whole design. Bare = further than `COVERAGE_THREAD_W_MM/2 = 0.20 mm` from any thread.

| fixture | chain | links | exposed | sewn path | bare mm | worst clearance |
|---|---|---|---|---|---|---|
| benchmark@90 left_chest | off | 0 | 0 | 0.00 | 0.00 | — |
| benchmark@90 left_chest | **on** | 19 | **12** | 123.22 | **7.55** | **0.3951** |
| benchmark@90 full_back | off | 1 | 0 | 2.99 | 0.00 | 0.0909 |
| benchmark@90 full_back | **on** | 22 | **17** | 123.91 | **16.15** | **1.0572** at (−40.57, 0.07) |
| logo_whitebg@80 | off/on | 11/11 | 3/3 | 92.98 | 0.70 | 0.3069 (identical — chaining is a no-op here) |
| logo_alpha@80 | off | 10 | 1 | 108.73 | 0.10 | 0.2405 |
| logo_alpha@80 | **on** | 17 | **5** | 152.63 | **4.85** | **0.5194** |

`full_back` → `fleece_sweatshirt` (`fabrics.py:63`), a stock preset. **16.15 mm of needle-down thread across 17 links, with one point more than a full millimetre from any thread in the design.** Every millimetre of it is introduced by chaining — the control is zero.

This is *after* the a63ac1b fix. `pytest -q` = 204 passed.

**Why nothing catches it:** the shipped instruments are structurally blind in three ways, all still present at HEAD.
- One-point links are skipped: `tests/test_chaining.py:136,155,449,490` and `tools/chain_probe.py:102,145` all `continue` on `len(run.points) < 2`. I counted them at HEAD: **7 of 19 (37%) on left_chest, 7 of 22 (32%) on full_back**.
- Neither instrument tests the first and last sewn segment — `_link_stitches` returns only the route's interior, so up to `RUN_STITCH_MM = 2.0 mm` at each end is untested. That is why my path length is 123.22 mm where `chain_probe` reports travel = 58.8 mm.
- Cover is polygons, not thread. A satin column does not stitch its whole polygon: 51.06 mm² of ground inside fill/satin polygons on the benchmark lies further than 0.20 mm from that shape's own thread, with a **0.947 mm-deep hole in `Sc4822d79`**, and 5.77 mm of link crosses those holes.

### 2. CRITICAL — contour leaves a bare core inside ordinary shapes, and `starved` cannot see it
**Lane:** contour-fill. **File:** `digitizer/digitizer_core/stage6_contour.py:109` (`_rings` stops when `_offset` returns nothing; the fabric inside the last surviving ring is never a ring and is never charged to `skipped_area_mm2`).

Two agents built the widest-inscribed-bare-circle instrument independently and agreed to three decimals, including reproducing the commit's own fixture numbers before disagreeing with it:
- `logo_whitebg@80 Sb253ebba` — the repo's primary fixture at its shipped width: contour **0.640 mm** bare radius vs tatami 0.090 mm (7.1x). `Sf5200f3f` 0.509 vs 0.088. `logo_alpha@180` 0.757 vs 0.094.
- Synthetic `star8_0.15`: **1.470 mm bare radius = a 2.94 mm bare disc** with `skipped_area_mm2 = 0.21` and `starved = 0`.
- `starved` fires on **0 of 122** zoo shapes, while firing on the shipped whitebg fixture over 0.51 and 0.64 mm spots. Miscalibrated in both directions.
- Mechanism measured: `buffer(-d, join_style=2, mitre_limit=2.0)` annihilates the interior of a notched shape — on a 10-point star with inradius 10.000, offsets exhaust at 5.60 mm inset instead of 10.00.

Rendered and eyeballed by one agent (`scratchpad/av_real.png`): an empty 1.28 mm core inside the innermost ring, where tatami rows cross the same circle.

### 3. CRITICAL — contour's ring-to-ring transition chord is never containment-tested
**Lane:** contour-fill. **Files:** `stage6_contour.py:227` (`_entry_arc`) / `:373` (`_link`).

`_entry_arc` deliberately *lengthens* the hop to clear `MIN_STITCH_MM` (law 44), and `_link` only tests `chord < MIN_STITCH_MM` and `gap > hard` — never `room.covers`. `_repair` and `_floor_pass` were both instrumented and are clean; the leak is provably in the transition (every escaping chord has a ring start on both ends).

- 23 emitted stitches leave the polygon over 124 shapes × 3 spacings; at the shipped 0.40 mm, 10 fill + 4 underlay.
- Worst verified in isolation: blob50, underlay chord 2.4106 mm long with **1.1008 mm outside the polygon**, midpoint 0.4235 mm outside, both endpoints inside.
- Reproduces on a 15 mm disc with a 0.3 mm hole and on a 0.45 mm neck. The shipped test `test_every_stitch_stays_inside_the_shape` **FAILS verbatim** on both.
- Underlay is 3x worse-exposed: `hard = 2.05 × 1.2 = 2.460 mm` vs 0.820 mm for fill.

The six in-repo fixtures have no hole under ~1 mm and no neck under 0.6 mm. That is the only reason this is green.

### 4. MAJOR — preflight blocks clean work at sizes nobody sampled
**Lane:** lettering-underlay. **File:** `digitizer/digitizer_core/preflight.py`, `_transport_and_content` / `_link_coverage`.

I reproduced this exactly. `bg_uncertain.png`, no chaining tier in the tree (`cfg` has no `chain_links` attribute):

```
104 hat_front  100/A -> 70/C  lmax=3.26  LINK_UNCOVERED severity=block
105 left_chest 100/A -> 70/C  lmax=3.32  block
105 hat_front  100/A -> 70/C  lmax=3.26  block
106 left_chest 100/A -> 70/C  lmax=3.32  block
107 left_chest 100/A -> 70/C  lmax=3.32  block
```
(100–103 and 108–110 are silent. With the artwork passed, 88/B → 58/D.)

The plan at 105/left_chest has **one block, one shape** (`S93573c6d`), and the blocking transport is `TRAVEL run1 shape=S93573c6d pts=73 len=177.48 jump=False` — the fill's own row-skip routing. The message the operator reads is *"3.3 mm of thread crosses bare fabric between shapes."* There are no other shapes.

Compounding: the raster predicate under-reports length on 22/48 configs, median 1.50x, max 9.68x, worst absolute 1.67 mm — an error larger than the margin the threshold rests on. And preflight is **1.94x slower** than the preflight that shipped (2250 → 4355 ms over 48 plans), paid on every design.

### 5. MAJOR — the dt-first recommendation is worse than the shipped rule at main's actual cap
**Lane:** physics-preflight. **File:** `digitizer/tools/shape_lens.py`.

I ran the ablation myself. `main:digitizer_core/machine.py:57` has `SATIN_MAX_WIDTH_MM = 3.0`; the worktree has 5.0.

```
--cap 3.0    TP FP TN FN
  ribbon      8  3  9  1   wrong 4/21
  VAR         8  0 12  1   wrong 1/21
  VP90        4  1 11  5   wrong 5/21   <- the recommendation
  VP90 misses: C_STROKE 3 wall, T_SHAPE 3 wall, WEDGE 1->5 over 30,
               WEDGE 2->4 over 30, BAR 40x4.8   (all five are FN)
```

The tool's own header prints *"FN (fill where satin was right) is the expensive direction."* The recommendation trades 2 FPs for 4 FNs and breaks two archetypes `test_satin.py` already pins. The safety sentence in the report, in commit 6677ead's message, and in two source docstrings — *"Pure tightening — cannot create fill-where-satin-was-right"* — is logically inverted: `VP90 = ribbon AND regular AND p90<=cap` is a strict subset of ribbon, so TP can only fall and FN can only rise.

Not wired in, so this is "do not land," not "the garment is broken."

### 6. MAJOR — appliqué breaks colour contiguity, and on one fixture the feature does not exist
**Lane:** applique-steps. **File:** `digitizer/digitizer_core/stage6_applique.py:970-972`.

- `ribbon_curve.png`: `applique=True` produces a **byte-identical DST** to `applique=False`, in all four garments and both modes. By house rule 4 the feature does not exist there. Corroborated at 12 mm target width where 5 of 5 `logo_whitebg` pieces and 1 of 1 `ribbon_curve` piece fall through.
- Thread 1305 is sewn, abandoned for 2905, then picked up again: block sequence goes from 5 contiguous thread runs to 6. With appliqué off the same shape is grouped *into* the single 1305 block. Fragmentation got worse in 8 of 32 appliqué designs. No test asserts thread-run contiguity, so this is invisible to the 234.
- The docstring says *"stage 7 groups it exactly as it would have if the tier had never looked at it."* Refuted by the block sequence.

### 7. MAJOR — `APPLIQUE_PIECES_OVERLAP` goes silent on the case that matters
**Lane:** applique-steps. Same file.

Two pieces, a 40×40 mm square that survives and a 2.5 mm ribbon that falls through, intersecting over 100.00 mm². Before: `APPLIQUE_PIECES_OVERLAP → 1`. After: `→ 0`. The operator loses the warning that a plain satin is being sewn on top of a live appliqué's cover. The control (two big overlapping pieces) still warns, so the counter itself is intact.

### 8. MAJOR — push-comp's headline defect is halved, not fixed, and the docstrings still claim it is fixed
**Lane:** push-comp. **Files:** `stage6_fill.py:45` (`principal_angle_deg`), `:397` (`center_run`), `stage5_overlap.py:232`.

- The simplify took the angle residual from 43.01° to **20.93°**, not to 0. On a hexagon it is 41.96°. The shipped isotropic path's own error is 10°, so the "fix" is **worse than what it replaces** on every rectangle and hexagon tested. Two agents measured this independently and got the same 20.93°.
- Root cause is upstream and one line: `principal_angle_deg` double-counts the closing duplicate vertex at `stage6_fill.py:52`. Re-running the identical moment sum on `coords[:-1]` returns 0.00 / 0.00 / 26.20 / 45.00 exactly against the current 10.90 / 2.54 / 37.10 / 55.90. This wrong number now drives both the fill rows *and* the compensation direction.
- Reachable only via `cfg.underlay_style='center_run'` — no shipped fabric preset uses it as `fill_underlay`. Latent, but the commit message calls it *"a live wrong answer, not a latent one."*
- `assert X or True` at `tests/test_pushcomp.py:230` carries zero bits, and it is the line whose comment claims to guard exactly this.

### 9. MINOR but structural — the headline numbers are not reproducible off this machine
- Every chaining headline is measured on `<user-home>\Downloads\enthusiast enterprises logo.png`. I confirmed the file exists — **on Kent's Downloads folder, outside the repo.** `find` in the worktree returns nothing.
- Preflight's "5 artworks / 80 configurations" is 4 committed PNGs plus `scratch_flat.png` (5,876 bytes, Jul 30, repo root, gitignored by `.gitignore:3`). All 6 of the density-gate leaks are on that file. The report's two sweeps don't even share a fixture set or size set.

---

## 3. Contradictions between reports — and who was right

**C1 — chaining: how much link is really on bare fabric, and how bare.**
Agent A: *"8.14 → 6.09 mm; worst after-point 0.4050 mm."* Agent B: *"worst realized clearance is 0.272 mm; no link on any fixture entered a pocket."*
**I measured it. A was right and understated; B was wrong.** Worst clearance on left_chest is **0.3951 mm** — close to A's 0.4050. B measured travel-run *vertices* only, which is exactly the sub-path the code never sews as written. And **neither agent ran `full_back`**, where the worst clearance is **1.0572 mm** and 16.15 mm of link is exposed. B's "no link entered a pocket" is the single most dangerous sentence in the dossier.

**C2 — preflight: is clean work silent?**
Agent A reproduced *zero* differences across 48 configs and marked SOUND_WITH_CAVEATS. Agent B found a block-severity firing band and marked NOT_SOUND.
**I measured it. B is right.** A sampled 4 sizes {30, 50, 80, 120}; the firing band is 4 mm wide at 104–107. A's grid could not have found it. This is the case for sweeping the size axis at ≤1 mm, not at four spot values.

**C3 — dt-first: SOUND_WITH_CAVEATS vs NOT_SOUND.**
Both agents agree the safety claim is inverted. They diverge on whether that sinks the recommendation.
**I measured it. NOT_SOUND is correct.** At main's actual cap of 3.0 the recommended arm scores 5/21 against the shipped rule's 4/21, and all five new misses are FNs. Agent A ran the ablation only at the worktree's 5.0. `VAR` alone scores 1/21 at cap 3.0 — if a term ships, it is the variance term, not the pair.

**C4 — chain-cover: is `_ring_points`' rewrite load-bearing or dead?**
Agent A: *"reverting it to the old polygon-only walker passes the entire suite and reproduces byte-identical probe output on all four fixtures — by house rule 4 this part of the change does not yet exist."* Agent B: *"at 20 mm the coverage fix ALONE would have refused 7 of 10 links; the undocumented waypoint expansion rescues them."*
**Both are right, at different widths, and that is worse than either framing.** The change is output-neutral at every width anyone tested and load-bearing at 20 mm. It also costs ~2.75 s of a 4.72 s benchmark on 193 exactly-duplicate waypoints whose removal is plan-identical. Neither the commit message nor the report states a runtime number.

**C5 — law 19: what are the freebie corpus's dense patches?**
Agent A: *bimodal — dense fills at 0.188–0.231 and open fills at 0.373–0.683.* Agent B: *305 of 333 (92%) dense corpus patches are column-like by a pinned-rail test calibrated on constructed fans; only 2 are unambiguous 2-D fills.*
**I could not settle this.** My own patch segmentation used a global-mean angle fit and produced pitch values (0.044–0.114 mm) I do not trust and will not offer against theirs. But B's instrument is the only one calibrated to separate a *fan* from a tatami fill, and A's `span > 12 mm` filter excludes satin without excluding fans. **I weight B on the freebies.** Both agree on the caps, which is what the decision rides on.

**C6 — law 19: how many cap patches are genuine fills?**
Agent A: all four cap files are dense fills at 0.182–0.192. Agent B: of 35 dense cap patches, FILL 12, COLUMN 9, ambiguous 14, fill pitch 0.161–0.193.
**B is the more conservative and the more defensible.** My structural measurement supports B's classification exercise: rows 16–84 mm wide with both rails wandering 31–88 mm cannot be satin *or* fan. The disagreement is about how many, not about whether.

**C7 — contour escapes: real artwork or zoo only?**
Agent A reproduced escapes on constructed discs and necks. Agent B ran a 124-shape zoo (23 escapes) but attributed 100% of *real-artwork* escapes to the satin tier's underlay, 0 to contour-filled shapes.
**Not a contradiction — same mechanism, different fixtures.** The real artwork is clean because none of the four committed fixtures has a hole under ~1 mm. Both agree the shipped containment test fails verbatim on shapes that do.

**C8 — contour short stitches.**
A: min fill step 0.4677 mm on a hole sweep, 3 at or under `TINY_STITCH_MM`. B: min fill step **0.1574 mm** at the shipped 0.40 spacing over the zoo, 165 of 46,530 fill steps under 1.0 mm.
**Not contradictory; B's is worse.** Both agree `assert min(steps) > machine.TINY_STITCH_MM` fails off the fixture set, and the fixture's own margin is 0.0746 mm (15%).

---

## 4. Claimed but not measured

> "Pure tightening — cannot create fill-where-satin-was-right." *(dt-first report; `shape_lens.py:247-250`, `:266-267`; commit 6677ead)*
Inverted. Measured false at cap 3.0 and on a bar at exactly the cap.

> "no shape that sews correctly today can start sewing worse" *(`shape_lens.py:266`)*
Same sentence, same refutation.

> "a shape handed back keeps its original position and stage 7 groups it exactly as it would have if the tier had never looked at it" *(`stage6_applique.py:970-972`)*
Refuted by the block sequence: 5 contiguous thread runs → 6.

> "Deliberately the same measurement as check_gates' finding and not a second copy of the threshold: the two cannot disagree" *(`stage6_applique.py:423-427`)*
They are two textual copies of the same expression with no structural link. Simulated drift (predicate floor 1.0 → 0.4, no source edited) produces a shape sewn by **nobody**, with no warning naming the loss.

> "decided by the same `is_satin_candidate` call ... stage 7 uses, so the two cannot disagree" *(`stage5_overlap.py:130-134`)*
Stage 5 calls it bare; stage 7 gates on `cfg.satin and is_satin_candidate(...)`. With `cfg.satin=False`, DST(dir=off) == DST(dir=on) — the flag is a silent no-op and the fill angle is re-derived from the compensated polygon, the exact circularity the lane exists to cut.

> "LINK_COVER_TOL_MM = half a thread width, so buffering a *path* by it yields **exactly** the ribbon that path lays."
"Exactly" is asserted. It holds only if laid thread is exactly 0.40 mm and the needle line is its centre. A 3-pass bean run's passes do not coincide. **This is a sew-out question and it is upstream of every coverage number in the dossier.**

> "It carries 1.8–2.3 thread layers, matching the calibrated satin reading of 2.02, not the tatami reading of 1.02." *(law 19 doc §2)*
`coverage == 0.40/pitch` algebraically. The doc's own calibration prints tatami@0.20 → 2.03 and zigzag@0.40 → 2.02 — indistinguishable to 0.5%. The 1.02 is tatami@0.40, which is the conclusion, not the alternative.

> "There is no cluster at 0.20-with-coverage-1.0, which is what 'fills are 0.20 single pass' would require." *(law 19 doc §3, its clinching test)*
Mathematically impossible under the doc's own definition of coverage. Absence of it is evidence of nothing.

> "study_pro measures same-rail satin density on these same files ... by a completely different code path" *(law 19 doc §2)*
`study_pro.py:236` filters to runs `classify()` already labelled satin. Same file is not the same object.

> "Runtime on the largest artwork 6570 ms → 298 ms." *(preflight commit)*
Two versions of the new code. Against the preflight that shipped it is **1.94x slower**. Neither endpoint of the quoted pair exists in any committed tree.

> "worst clearance to nearest stitch 0.463 mm → 0.169 mm" *(chain-cover report)*
No committed code computes clearance. Not reproducible under 12 readings by one agent, nor under mine. My most faithful reading gives 0.4940 → 0.2719 mm (vertices) or 0.6791 → 0.3951 mm (real sewn path). Same direction, wrong digits, and the "under the 0.37 mm floor" argument then has 0.10 mm of margin, not 0.20.

> "the 0.37 mm inter-stitch interstice floor"
Contradicted by a 0.947 mm hole in a satin column on the very fixture the number came from.

> "tatami 0.913–0.991, contour 0.003–0.270, nothing between" *(preflight report + shipped test docstring)*
Contour spans 0.002–1.000; 21 of 72 contour configs beat the 0.6 gate. Tatami measures 0.935–0.994, not 0.913–0.991.

> "every arm gets monotonically worse as the trim grows" *(dt-first doc:100-107, bolded)*
The table directly under it prints R1 = 3/21 at both trim 0 and trim R.

---

## 5. The sew-out queue

Everything below is blocked on thread meeting cloth, not on more analysis. Four hoopings settle nine open decisions.

**Hooping 1 — density and the bare core.** One cap front, one colour, four small blocks of the same shape (use `logo_whitebg Sb253ebba`, the shape both contour agents measured):
1. tatami @ `FILL_ROW_MM = 0.40` — control
2. tatami @ 0.20 — law 19's arm, but run it on a **cap-style logo fill**, not an area fill
3. contour @ 0.40 — the shape with the measured 0.640 mm bare core
4. contour @ 0.20

Settles: law 19 (is 0.19 right for our thread/stabiliser, or is it those digitizers' house style?); whether a 0.64 mm bare core reads on cloth; whether `starved` should be re-specified as a bare-radius threshold and what that radius is; and whether contour's cleaner edge is worth its core at all.

**Hooping 2 — does a link show?** Two panels, the benchmark logo, no other change:
1. `chain_links=False` on `full_back` — control
2. `chain_links=True` on `left_chest` — worst clearance 0.395 mm, 7.55 mm exposed over 12 links
3. `chain_links=True` on `full_back` — worst clearance **1.057 mm**, 16.15 mm exposed over 17 links

Settles: the single most important unknown in the dossier — at what clearance does a needle-down float become visible on fleece? That number *is* `LINK_COVER_TOL_MM`, and right now it is a nominal thread spec, not a measurement. It also settles whether preflight's `trim_at_mm = 3.0` block threshold points the right way, and whether the chaining lane ships at all.

**Hooping 3 — the tie-in.** Any panel, two blocks, appliqué placement runs only:
1. `a0bb87c` — the restored 5th penetration, whose first strike lands at **exactly 0.000 mm** from the previous hole
2. `e287771` — 4 penetrations, first strike 0.8 mm away

Settles: whether an anchor whose first strike re-enters the hole it just left grips better or worse. Currently unproven in both directions, and only one direction is named in the commit. `machine.py:128` documents a "one full same-hole radius clear" concern for the satin case — this is the same physics.

**Hooping 4 — satin vs fill at the knife edge.** One panel, small blocks:
1. the 10.63 × 9.43 mm logo block as 3 satin columns (361 pts) vs as tatami (190 pts)
2. `C_STROKE` 3 mm wall and `T_SHAPE` 3 mm wall, each sewn both ways
3. `BAR 40×5.0` — a bar sitting exactly at the cap — both ways

Settles: is a 0.0355 mm difference in 2A/P visible at all? Is FN really the expensive direction, and by how much? Are `SQUARE 4x4` and `BAR 40x5.2` — the two arguable fixture truths that decide three arms' scores — adjudicated correctly?

Hoopings 1 and 4 can share a panel if the cap front has room; both are small shapes.

---

## 6. What I would do next

**Nothing in this dossier should land on `feat/satin-rails` before item 1.** Chaining is the only defect here that puts visible thread on bare fabric, on a stock garment preset, with a 204-green suite and two instruments that structurally cannot see it. Merging anything else first just makes it harder to attribute.

**1. Rebuild the chaining coverage instrument, then re-run the acceptance test and expect it red.**
Three changes, all in `tools/chain_probe.py` and `tests/test_chaining.py`: include one-point links (37% of the benchmark's links today); test the *real* sewn path `prev_run.points[-1] → link → next_run.points[0]`; and measure against emitted thread for **all** tiers, not polygons for fill/satin. Mine is ~50 lines and lives in the scratchpad at `.../closeout/bare.py`. Add `full_back` to `CASES` — the whole lane was validated on `left_chest` and `full_back` is 2x worse. This is the cheapest high-value work in the dossier and it converts a false green into a real signal.

**2. Then decide chaining's fate on evidence.** Either apply `_laid_cover`'s own thesis ("cover is where the thread lands, not where the shape is") to the fill and satin tiers too, or accept a link only where measured clearance is under a threshold set by Hooping 2 and let the rest be jumps. Note the cost of refusing: the chain-cover data shows jumps 7 → 11 with **trims unchanged**. A refused link costs a needle-up move, not a thread cut. That is a cheap fallback.

**3. Do not land contour.** Three independent problems — a 7x-worse bare core on the repo's own primary fixture, an escape chord that is never containment-tested, and a `starved` gate that fires on 0.51 mm and stays silent on 1.49 mm — and none of the three is visible to the shipped tests. The first thing to build is the widest-inscribed-bare-circle instrument as the *definition* of `starved`; both agents built it, it reproduces the module's own numbers on the fixtures the commit cites, and it disagrees everywhere else. Then add a `room.covers` test to the transition chord in `_link` before `_entry_arc`'s lengthening is trusted. Everything else in that lane is downstream of those two.

**4. Preflight: drop `LINK_UNCOVERED` from `block` to `warn` today, before anything else.** As shipped it refuses clean artwork at four widths I found in a ten-value sweep, on a design with one shape, for a fill's own travel. Then two real fixes: bucket TRAVEL by shape-id continuity so a within-shape travel is not called a between-shape link; and replace the disk-stamp predicate with exact point-to-segment distance (measured error up to 9.68x, worst absolute 1.67 mm, larger than the margin the threshold rests on). Separately, the 1.94x cost regression is paid on every design and needs justifying or reverting.

**5. dt-first: do not land VP90.** If a term ships it is `VAR` alone — 1/21 at cap 3.0 against the shipped rule's 4/21, and it survived every attack both agents threw at it, including a serrated-boundary attack designed to break it. Before that: add a fixture at *exactly* the cap, add a margin term absorbing the measured +0.100 mm raster bias (`2*p90 <= cap` is really `true_width <= cap − 0.1`), re-score at cap 3.0 with truths re-adjudicated at 3.0, and sweep p70/p80/p95. Delete the three copies of the inverted safety sentence regardless of what ships.

**6. Reopen law 19.** The doc's REFUTED verdict is built on a corpus that excludes the four files the law was written from, and those files are on disk. The correct state is *two* populations: freebie script/lettering files where the 0.20 reading is a satin half-step (the report is right), and commissioned cap logos with genuine 2-D area fills at 0.161–0.193 mm (the report is wrong). Do **not** change `FILL_ROW_MM` on analysis — it goes on Hooping 1's card, with the 0.20 arm run against a cap-style logo fill.

**7. Land push-comp, with edits.** The operator is correct to within the DST grid and the circularity cut works. But fix `principal_angle_deg` first — dropping the closing duplicate vertex at `stage6_fill.py:52` is one line and removes a measured 10.9° error that is now upstream of both the fill rows *and* the compensation direction. Then delete the angle claim from the commit message and the two docstrings, delete `assert X or True`, and either make `_comp_axis` gate on `cfg.satin` like stage 7 does or stop claiming the two cannot disagree.

**8. Land appliqué.** Its defects are warnings, colour order, and three false numbers in shipped docstrings — not thread on fabric, and the 80-design byte-identical blast-radius result is the strongest evidence in the dossier. Fix the "four frame-outs" in `stage6_applique.py:415` and `test_applique.py:695` (it is 3), add the thread-contiguity assertion over `plan.blocks`, and restore `APPLIQUE_PIECES_OVERLAP` for the fallen-through-over-live case.

**9. Commit the benchmark artwork, or stop quoting it.** Every headline number in the chaining lane is measured on a PNG in a Downloads folder. No other machine can re-derive any of it. Same for `scratch_flat.png` in preflight's sweep — either commit it as a fixture or state that the "5 artworks" is 4.

---

## What I did not establish

- I did not re-run four of the six suites. I ran `feat/stitch-chaining` (**204 passed, 1 warning, 73.03s** at `a63ac1b`). The other tallies are each reproduced twice by independent agents and I take them.
- **Nothing was sewn.** Every number above, mine included, is geometry.
- My cap-file **pitch** numbers (0.044–0.114 mm) are unreliable — my patch segmentation is a global-mean angle fit over a whole run, which interleaves sub-patches at different angles and collapses the median gap. I confirmed the *structural* claim (traverse width, penetration spacing, both rails wandering) and defer to the two agents' per-patch fits for the 0.161–0.193 figure.
- I did not measure whether the 1.057 mm float on `full_back` is covered by an *earlier* colour — my instrument measures distance to every non-travel stitch in the design regardless of order, so 1.057 mm is distance to any thread at all. It is bare fabric.
- I did not verify the applique or preflight integration-sandbox numbers; that sandbox no longer exists as an artifact.
- I did not touch the `satin-rails` worktree or `feat/satin-rails`. It is still at `62fea6e`. I edited and committed nothing anywhere.