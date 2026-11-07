# #1301 attribution: which switch moves each wrong-way tripwire row (2026-11-07)

Measurement only. `digitizer_core/` is untouched and no default changes.

## Question

PR #1301 turned three defaults ON (Kent, 2026-11-06/07):

- `stage0_scale_relative_grad`: stage 0 splits flat from gradient on a scale-relative read.
- `flat_page_fringe_soft_ramp` and `flat_ramp_blend_dissolve`, together "the cure": the flat lane's fringe cure.

The tripwire capture afterwards (run 42403074224, main 66964cc9) moved 52 of 111 baselines. Held re-seed PR #1316 lists the wrong-way rows. This doc finds which switch owns each one.

## Method

- **The tripwire's own measure path.** `tools.tripwire.measure(runs, [slug], with_words, kent_dir)`, the call the nightly's `check` makes, runs one job at a time on main d40b2cd3 (clean tree). d40b2cd3 is 66964cc9 plus #1310 and #1312, neither of which touches the engine.
- **Arms.** A driver wraps `tools.pro_pair.digitize` so the arm's flags ride the request dict. These are top-level `PipelineConfig` fields that the service's `_parse_config` accepts, the same route the Studio's request takes.
  - **on**: shipped defaults.
  - **s0off**: `stage0_scale_relative_grad` False.
  - **cureoff**: both cure flags False.
  - **alloff**: all three False.
  - **rampoff** and **dissolveoff**: toat_beanie only, where the cure moved anything. Each turns off one cure flag.
- **Machine.** Kent's Windows laptop. OCR is `tesseract v5.5.3 (tesserocr 2.12.0, in-process)`, the same reader string as the Linux capture.
- **Compare arms with each other.** The ledger is Linux. As it turned out, the Windows "on" arm matches the Linux capture to within 6 stitches and 0.1 mm on every row below, and "alloff" matches the Linux nightly at 688996bf (run 42376195077, before #1301) exactly. That includes Fremont's word cc of 0.903.
- **Diagnostics** come from `scorecard.score_design` on the same score directory: stage-0 class, shared solid cells, registration, and the unclamped direction kappa.

## Per-row, per-arm table

Old = ledger baseline (#1267, 3306880c). New = capture at 66964cc9. **Bold** = the arm value that moves away from the "on" value.

| job | figure | ledger old | capture new | on | s0off | cureoff | alloff | verdict |
|---|---|---|---|---|---|---|---|---|
| goldentee_hat | stitches | 11,018 | 13,509 | 13,515 | **11,018** | 13,515 | **11,018** | stage 0 |
| goldentee_hat | trims | 25 | 39 | 39 | **25** | 39 | **25** | stage 0 |
| goldentee_hat | hops | 42 | 68 | 68 | **42** | 68 | **42** | stage 0 |
| goldentee_hat | needle-up mm | 536.3 | 644.5 | 644.6 | **536.3** | 644.6 | **536.3** | stage 0 |
| hotel_fremont_hat | word cc | 1.00 | 0.605 | 0.605 | **0.903** | 0.605 | **0.903** | 1.00 -> 0.903 reader (#1277); 0.903 -> 0.605 stage 0 |
| toat_beanie | direction kappa | 0.388 | 0.000 | 0.000 | **0.388** | **0.394** | **0.388** | stage 0 route + `flat_page_fringe_soft_ramp`, together |
| gaulke_roofing_hat | trims | 30 | 32 | 32 | **30** | 32 | **30** | stage 0 |
| gaulke_roofing_hat | stitch-type kappa (chance) | 0.139 | 0.115 | 0.115 (0.837) | **0.139** (0.842) | 0.115 | **0.139** | stage 0 |
| gaulke_roofing_hat | needle-up mm | 371.5 | 396.6 | 396.6 | **371.5** | 396.6 | **371.5** | stage 0 |
| hotel_fremont_patch | trims | 20 | 24 | 24 | **20** | 24 | **20** | stage 0 |
| mfab_lc | needle-up mm | 345.2 | 389.3 | 389.3 | **345.2** | 389.3 | **345.2** | stage 0 |

### Other figures on the same jobs (right-way moves, same owner)

| job | figure | on | s0off = alloff | cureoff |
|---|---|---|---|---|
| goldentee_hat | stitch-type kappa (chance) | 0.868 (0.615) | 0.828 (0.620) | = on |
| goldentee_hat | direction kappa | 0.311 | 0.241 | = on |
| hotel_fremont_hat | trims / hops | 22 / 139 | 25 / 175 | = on |
| hotel_fremont_hat | stitch-type kappa (chance) | 0.575 (0.476) | 0.533 (0.435) | = on |
| hotel_fremont_patch | hops / needle-up mm | 149 / 467.3 | 175 / 475.9 | = on |
| hotel_fremont_patch | stitch-type kappa (chance) | 0.545 (0.468) | 0.518 (0.426) | = on |
| mfab_lc | hops / stitches | 26 / 17,848 | 31 / 18,092 | = on |
| mfab_lc | stitch-type kappa (chance) | 0.585 (0.490) | 0.566 (0.487) | = on |

### toat_beanie, the cure split

| arm | stage-0 class | regions | stitches | trims | hops | needle-up mm | stitch-type kappa (chance) | direction kappa | unclamped | shared cells | registration mm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| on | flat | 70 | 18,410 | 22 | 34 | 240.0 | 0.388 (0.550) | 0.000 | -0.292 | 899 | (0, 0.75) |
| dissolveoff | flat | 70 | 18,410 | 22 | 34 | 240.0 | 0.388 (0.550) | 0.000 | -0.292 | 899 | (0, 0.75) |
| rampoff | flat | 80 | 18,205 | 23 | 35 | 342.9 | 0.390 (0.556) | 0.394 | 0.394 | 894 | (0, 0.5) |
| cureoff | flat | 80 | 18,205 | 23 | 35 | 342.9 | 0.390 (0.556) | 0.394 | 0.394 | 894 | (0, 0.5) |
| s0off | gradient | 54 | 18,253 | 20 | 34 | 310.7 | 0.395 (0.551) | 0.388 | 0.388 | 899 | (0, 0.75) |
| alloff | gradient | 54 | 18,253 | 20 | 34 | 310.7 | 0.395 (0.551) | 0.388 | 0.388 | 899 | (0, 0.75) |

`flat_ramp_blend_dissolve` changes nothing here. `flat_page_fringe_soft_ramp` alone moves toat_beanie: it drops 10 regions, cuts needle-up by 103 mm (the right way), and takes direction kappa from 0.394 to 0.000. It moves anything only on a design that stage 0 now sends flat. On the gradient route (s0off) it changes nothing.

## Is toat_beanie's direction kappa 0.000 real?

**Yes. It is a real score, clamped at the chance floor, not a measurement that failed.**

`tools/pro_parity/scorecard.py` (`score_design`, `chance_correct`) can return 0 in two ways:

1. **No shared solid cell** (`both.any()` False). Then direction AND stitch type are both set to 0.0 and `shared_cells` is 0. This is the "could not compute" case, and it always zeroes stitch type too.
2. **Agreement at or below chance.** `chance_correct` returns `max(0, (observed - 0.5) / 0.5)`, so anything worse than a random angle reads exactly 0.

toat_beanie is case 2. The default arm has 899 shared cells, a nonzero stitch-type kappa (0.388), and an unclamped direction kappa of -0.292. Its fill directions now disagree with the pro's more often than random angles would.

The same clamp already applied before #1301 on two rows that read 0.000 in every arm, so their 0.000 is real too: hotel_fremont_hat (unclamped -0.38 to -0.39) and mfab_lc (-0.31). A direction kappa this far BELOW chance is systematic, close to perpendicular, not noise. It may be worth one look at whether satin columns and the pro's fills are being compared on the same axis convention. Not investigated here.

## Verdicts, one line per row

- **goldentee_hat stitches, trims, hops, needle-up**: `stage0_scale_relative_grad`. It routes Golden Tee flat (38 -> 92 regions, 9 -> 7 colours). The cure does nothing here.
- **hotel_fremont_hat word cc**: two causes. 1.00 -> 0.903 is the OCR reader switch (#1277); the Linux nightly at 688996bf, before #1301, already read 0.903. 0.903 -> 0.605 is `stage0_scale_relative_grad`. The cure does nothing here.
- **toat_beanie direction kappa**: `flat_page_fringe_soft_ramp`, which only acts because `stage0_scale_relative_grad` now routes toat_beanie flat. Neither switch alone does it. The score is real (unclamped -0.292).
- **gaulke_roofing_hat trims, stitch-type kappa, needle-up**: `stage0_scale_relative_grad`. The kappa moves 0.024 against a 0.84 chance floor, where there is little room. The cure does nothing here.
- **hotel_fremont_patch trims**: `stage0_scale_relative_grad`, with hops 175 -> 149 the right way. The cure does nothing here.
- **mfab_lc needle-up**: `stage0_scale_relative_grad`, with hops 31 -> 26 and stitch-type kappa up the right way. The cure does nothing here.
- **No row is owned by another merge.** On every job, alloff equals the Linux nightly at 688996bf figure for figure. Nothing else merged between 688996bf and 66964cc9 moves these six jobs.

## Decisions for Kent

1. **Re-seed as is (merge #1316).**
   - Delivers: the nightly goes green tonight, and every new baseline is a move this doc traces to a switch you turned on deliberately.
   - Cost: none in work.
   - Catch: Golden Tee's +2,491 stitches and +14 trims, Fremont hat's word cc of 0.605, and toat_beanie's direction 0.000 become the floor. A later fix shows up as a right-way move, never as a red night.
2. **Re-seed, but keep the old baselines on the 11 rows above.**
   - Delivers: the nightly stays red on exactly those rows until each is fixed or accepted.
   - Cost: a hand-edited ledger. The capture tool cannot produce it, so the next capture overwrites it.
   - Catch: the rows are already fully attributed, so a red nightly no longer carries new information. It does train people to read past red, which is what hides a real regression later.
3. **Fix lane before any re-seed.** Start with Fremont hat word cc and Golden Tee, then the toat_beanie ramp interaction.
   - Delivers: a chance to keep #1301's right-way moves (Fremont hops -36, stitch-type kappa up on four jobs, toat needle-up -71 mm) without the wrong-way ones, for example a stage-0 or ramp guard.
   - Cost: one or more engine lanes, plus a sitting to rule on them.
   - Catch: the nightly stays red the whole time, and any guard is a new default-OFF flag that needs its own flip ruling.

**My pick: 1 plus a fix lane.** Re-seed now, because every wrong-way row has a known owner and the tripwire has already done its job of naming them. Then open a fix lane for the two figures a customer would notice: Fremont hat lettering legibility (0.903 -> 0.605) and Golden Tee's stitch and trim rise. Both come from the stage-0 route alone. Option 2 keeps the nightly red with nothing new to say. Option 3 keeps it red for as long as the fix takes.

## Reproduce

The driver lives outside the repo: a 70-line wrapper around `tools.tripwire.measure` with `tools.pro_pair.digitize` patched to merge the arm's flags into its `extra`. To reproduce without it, call `tools.pro_pair.digitize(art, width, garment, {"stage0_scale_relative_grad": False})` per arm, then `tools.pro_baseline.measure`. These are the same three calls `tripwire.measure` makes. Each digitize took 13-77 s here, run one at a time.
