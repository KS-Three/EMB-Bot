# Where the scorecard disagrees with the sewn result

**Phase 1's exit condition** (ROADMAP): *"on real customer designs, the
metric's ranking agrees with Kent's visual ranking, and nothing he judges
better ever scores worse."* That is a claim about disagreements, and nothing
was collecting them — each one was recorded where it was found, in whatever
entry happened to surface it.

This is the list. **Every row is a measurement made on this corpus, with the
instrument that produced it named**, so the gate can be argued from evidence
rather than from impression. It is not a complaint about preflight: five of
the six are consequences of deliberate, documented choices.

Assembled 2026-09-06 from that day's work. **Append to it; do not curate it.**

---

## 1. A 32.7 → 1.4 ΔE00 thread fix moves no grade and no block

`cfg.revalidate_small_shapes` re-snaps `S43831dcd` on
`screenshot_phone_ui_golke` from `0111 Whale` (32.7 ΔE00 over artwork the
check reads as 252,252,252) to `0015 White` (**1.4**). The shape sews — 24
stitches. The design's worst thread error falls **33.0 → 21.2**.

**Grade: unchanged. `THREAD_MATCH_POOR` blocks: unchanged.**

*Why:* the check is per THREAD, on that thread's worst patch. `0111 Whale`
still sews a 182-grey shard, so the block stands and six fixed shards are
invisible to the grade.

**Stated precisely, because the first draft of this row overreached.** It is
not that the harness cannot express the change: `corpus_scorecard.diff`
captures `report["metrics"]` and `_metric_deltas` reports any move past
`_METRIC_NOISE_FRAC` (5%), so 33.0 → 21.2 (−36%) *does* appear in a diff. What
does not move is the **grade** — the number that gets quoted, that gates
"do not sew", and that a scorecard recapture is argued from. The disagreement
is between the metric that moved and the verdict that did not.

`digitizer/tools/revalidate_floor.py`, `tools/thread_color_render.py`,
`docs/renders/small-shape-resnap-2026-09-06/`. *(measured 2026-09-06)*

## 2. The metric prefers a tier off, on a question it cannot see

Photo tonal splitting, default against `split_tonal_regions=False`: **four of
nine photo-class fixtures score HIGHER with the tier OFF, none lower**
(`chrome_specular` C 64 → B 88, `dof_meadow` D 52 → B 88, `scene_stub`
B 76 → A 100, `sunset_backlit` B 76 → A 100), at **−16.4%** of the photo
lane's thread.

**The scorecard has no tonal-gradation instrument.** It scores density,
coverage, trims and thread-to-artwork ΔE00. A photo sewn in 3 cones instead of
5 can score better and look flatter, and no number here distinguishes those.

This is the sharpest case, because the tier is Kent's ratified spec decision 2:
**the metric ranks a deliberate quality decision backwards.**

`digitizer/tools/tonal_split_ab.py`. *(measured 2026-09-06)*

## 3. A 0.02% shard and a 53% field produce the same verdict

`THREAD_MATCH_POOR` has **no area floor**. Across the seven F-grade fixtures,
25 blocking findings; the worst shape behind each measures **min 0.58 mm²,
p50 3.17, max 1,648.5 — 12 of the 23 measurable ones under 5 mm².**

- `gaulke_roofing` / `3971`: 63.6 ΔE on **0.58 mm², 0.02%** of the design
- `drone_render` / `0020`: 14.1 ΔE on **1,648.5 mm², 53.6%**

Both emit `block` — "do not sew". Every sibling check has a floor
(`_uncovered_findings` 5.0 mm², `_lettering_findings` 4.0 mm). *(measured
2026-09-06)*

## 4. Two yardsticks, and the lane real logo art uses is the harsher one

`_thread_match_findings` scores the **photo** route on excess over the best
loaded spool — adopted 2026-08-24 because raw distance *"condemned work that
was already optimal … every photo job graded F / do not sew."* Every other
route keeps raw distance, and **all seven F-grade fixtures are `gradient`**,
which is where six of the seven real customer logos route.

Under excess, **four of the seven clear every block**: `golden_tee` D 52,
`drone_render` D 40, `region_blobs` B 88, `summit_badge` D 52 — all from F 0.
Their assignments are already optimal and raw distance condemns them anyway.

Whether the gradient lane *should* get the excess yardstick is a product call
(a logo's palette can be changed; a photograph's cannot), which is why this is
listed as a disagreement and not filed as a fix. *(measured 2026-09-06)*

**Half of this was not a product call, and is fixed (2026-09-06).** The
*scoring* question above stands. But the same gate also suppressed the SEARCH,
so off the photo route the finding never checked the design's own cone list
before saying *"pick a closer thread."* Of the F-wall's **24 blocking
findings, 5 name a spool the design already loads** — `gaulke_roofing`'s 63.6
ΔE00 sits 58.6 from a loaded `1375 Dark Charcoal`, `screenshot`'s 33.0 sits
32.4 from a loaded `0015 White`. Those are the two numbers this very list
quotes elsewhere. The finding now names them on every route, with no severity
or grade moving anywhere, and the payload states `yardstick` so a reader can
still tell what judged it. **What remains a disagreement is only whether the
gradient lane should be JUDGED on excess** — which is the part that would
re-base the scorecard, and is Kent's.
`digitizer/tools/spool_remedy.py`. *(measured 2026-09-06)*

## 5. It scored the colour of regions that never sew

Until 2026-09-06 `_region_color_errors` built a row for every region including
`enclosed_background` ones — unstitched by default, and their colour is the
background's. Worth one finding across the whole matrix once fixed
(`gaulke_roofing` F 0 → F 4), so the effect was small — but the class is not:
**a metric that scores unsewn geometry cannot rank sewn results.**

The sibling `_uncovered_findings` had applied the right denominator since
2026-09-04, quoting `SHAPES_LEFT_UNSEWN`. *(measured 2026-09-06)*

## 6. The score saturates, and twelve combos sit on the floor

`run_preflight` scores `max(0, 100 - 30*blocks - 12*warns)`. The clamp is
deliberate — a negative grade means nothing to an operator — but a saturated
metric cannot rank the designs sitting on it.

**12 of the 52 design/garment combos land on exactly 0**, and their unclamped
scores run **-272 to -38 — a 234-point spread behind one printed value.**
Points that must be cleared before F -> D (40) shows *anything*:

| fixture | needs | ≈ blocking findings |
|---|---:|---:|
| `screenshot_phone_ui_golke` | 312 | 11 |
| `drone_render` | 228 | 8 |
| `logo_golden_tee` | 156 | 6 |
| `region_blobs` | 96 | 4 |
| `logo_bridge_bar` | 90 / 78 | 3 |
| `summit_badge` | 78 | 3 |

**This is the mechanism under row 1.** `cfg.revalidate_small_shapes` fixing a
32.7 -> 1.4 ΔE00 thread error moves no grade partly because the check is per
THREAD — and partly because the design is 312 points under water. It also
explains the one case that DOES move: `dissolve_phantom_blends` takes
`gaulke_roofing` F 0 -> C 64 because gaulke is the shallow one, at F 4 rather
than floored.

So on a floored design the grade is not evidence either way, and the render
is — which is row 1's advice, now with the number that says why.

`digitizer/tools/floor_depth.py`. *(measured 2026-09-06)*

## 7. It prefers a design that dropped its ink

The first six rows are the metric failing to SEE an improvement. This one is
the metric preferring a regression, and it was found by measuring cones
instead of grades (`digitizer/tools/flip_sheet.py`, `docs/flip-sheet-2026-09-06.md`).

`logo_gaulke_roofing` is black lettering on a white label. Four arms:

| arm | darkest cone | grade |
|---|---:|---|
| off | `1375 Dark Charcoal`, **L\* 15.9**, 288 st | F 4 |
| `dissolve_phantom_blends` | `0145 Skylight`, L\* 85.7 | **C 64** |
| `bind_resnap_all_classes` | `0020 Black`, **L\* 0.0** | F 16 |
| all five parked flags | `3971 Silver`, L\* 82.0 | **C 64** |

**The two best grades load no thread darker than L\* 82 for lettering on a
white ground. The only arm that loads Black grades second-worst.**

*Why:* `THREAD_MATCH_POOR` grades per thread on that thread's worst patch, so
deleting the dark cone deletes the thread that was scoring badly — you cannot
have a poor thread match on a thread you never loaded.

The practical consequence is in row 1's terms: on a fixture where a flag
removes a cone, the grade is not evidence of anything, and the cone list is.
*(measured 2026-09-06)*

---

## What this list is not

**Not an argument that the scorecard is bad.** Rows 3–5 are small; rows 1, 2
and 6 are the load-bearing ones (6 is the mechanism under 1), and both say the same thing in different words:
*the metric has no term for the thing the change improved.* That is the gap
phase 1 names, and it will not close by tuning thresholds.

**Not a to-do list.** Two of the six (3 and 4) are product calls that re-base
the scorecard for at least four fixtures — and half of 4 turned out not to be
one, and is fixed. One (5) is fixed. The other three are measurements waiting
for a yardstick that can hold them.

**The honest use of it:** before claiming a digitizing change improved
quality, check whether it lands in one of these five shapes. If it does, the
grade is not evidence either way, and the render is.
