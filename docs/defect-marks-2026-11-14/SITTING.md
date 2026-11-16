# defect-marks-1114: the photo subject-recall sitting, scored (2026-11-15)

Kent graded all 14 items of the kit on 2026-11-14/15. His word when he
finished was "Done." His marks are `marks.json` in this folder, a byte copy of
the live checkout's `digitizer/eye_pairs_out/defect-marks-1114/marks.json`
(sha256 `4b9949de…aaef`, 6,909 bytes; the original is unedited). Scoring
followed `subject-recall-preregistration.md` (commit `34bc7177`) using
`score_sitting.py`, which reads `rows.json` (the `subject_edge_recall`
readings, computed only after he finished) and writes `score.json`. The page
never showed the metric or the preflight grade. Every number below is an
instrument reading or Kent's own answer (ROADMAP gate 4).

## Result: NO VERDICT, the GOOD class did not fill

**14 LOST, 0 GOOD, 0 MIDDLE.** He ticked "Too much detail lost" on all 14,
"Can't tell what it is" on 11, and graded 11 Terrible, 2 Bad and 1 Okay
(`dark_dog`). The pre-registration needs at least 4 LOST and 4 GOOD for any
verdict. With no GOOD item there is no Somers' D, no kappa and no interval to
report, and none is reported. **Pre-registered outcome: "no verdict: class
not filled".** `subject_edge_recall` stays exactly as it is, a preflight
metric only.

| item | Kent | his ticks | `subject_edge_recall` | below 0.90 |
|---|---|---|---|---|
| `P_night_skyline` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.559 | yes |
| `P_flower_macro` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.714 | yes |
| `P_fireworks` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.772 | yes |
| `P_snow_highkey` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.792 | yes |
| `P_dark_dog` | Okay | detail_lost, not_for_thread | 0.805 | yes |
| `P_underwater_reef` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.808 | yes |
| `P_watercolor` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.810 | yes |
| `P_oil_painting` | Bad | detail_lost, not_for_thread, too_busy | 0.823 | yes |
| `P_food_plate` | Terrible | detail_lost, not_for_thread, unrecognizable | 0.860 | yes |
| `P_vintage_sepia` | Bad | detail_lost, not_for_thread, too_busy | 0.860 | yes |
| `P_pencil_sketch` | Terrible | detail_lost, not_for_thread, unrecognizable | 0.879 | yes |
| **`P_toadstool_dof_meadow`** | Terrible | detail_lost, too_busy, unrecognizable | **0.940** | **no** |
| `P_group_people` | Terrible | detail_lost, not_for_thread, too_busy, unrecognizable | 0.915 | no |
| `P_sports_action` | Terrible | colours_off, detail_lost, not_for_thread, too_busy, unrecognizable | 0.968 | no |

**The toadstool is a miss, as the pre-registration said it would record.**
Kent marked it LOST ("The mushroom is missing", "The mushroom doesn't have a
stem/base", "The mushrooms don't even look like mushrooms"). It reads 0.940,
at or above the 0.90 cut-off, so the reading did not flag the photo that
started this. Two face-routed photos are missed the same way
(`group_people` 0.915, `sports_action` 0.968).

**The other reported lines.** There are no MIDDLE items. Taking the photo-lane
items alone (dropping the 3 face-routed flat ones) also gives 11 LOST and 0
GOOD, so again no verdict.

**Kent's note on `P_watercolor`:** "Remove this one from the graded list, it's
not anything that would ever be embroidered." The pre-registration has no
rule for removing an item, so the table keeps it. Without it the counts are
13 LOST and 0 GOOD, with the same outcome.

## Kent's ruling (2026-11-15)

Relayed by the foreman, verbatim: **"Park it, metric only (Recommended)"**.

- The result is recorded as no verdict.
- `subject_edge_recall` stays a preflight metric only: no finding, no grade
  cost, nothing the customer sees.
- It is re-sat only once the photo lane produces photos he would call Good.
- He ruled out a photo-grade cap study, a new sitting now, and dropping the
  metric.
- His `P_watercolor` note ("Remove this one from the graded list") is
  recorded above and only reported as a count. Nothing was removed.

## Exploratory (not pre-registered, decides nothing)

- **Preflight's grade against Kent's, on the same renders.** For each item
  the kit stored the yardstick's grade, but the page never showed it. It gave
  A 100 to `pencil_sketch` (Kent: Terrible) and B 76 to six more he called
  Terrible or Bad: `food_plate`, `flower_macro`, `underwater_reef`,
  `watercolor`, `oil_painting` and the toadstool. It gave C 64 to
  `night_skyline` (Terrible). The rest got D or F. On 8 of these 14
  detail-lost photos the yardstick says C or better.
- **Across both photo sittings, Kent has graded no photo Good.** The 11-10
  sitting had 4 corpus photos, all Terrible. This one had 14: 11 Terrible,
  2 Bad, 1 Okay. That is 17 of the corpus's 18 photos (`stained_glass` timed
  out) plus the toadstool: 18 photos at 80 mm on the left chest, none Good. A "kept the subject /
  lost the subject" reading cannot be tested on this lane while it produces
  no photo he calls Good, because the GOOD class cannot fill. The problem
  sits upstream of any preflight check.
- **`dark_dog`**, the cut-out portrait and the only Okay, read 0.805, below
  the cut-off. Kent: "It looks good if a squint, but the details are lacking".
  His pins mark the collar, the nose tip, the ears and a bean outline.
