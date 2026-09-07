# Where the scorecard disagrees with the sewn result

**Phase 1's exit condition** (ROADMAP): *"on real customer designs, the
metric's ranking agrees with Kent's visual ranking, and nothing he judges
better ever scores worse."* That is a claim about disagreements, and nothing
was collecting them — each one was recorded where it was found, in whatever
entry happened to surface it.

This is the list. **Every row is a measurement made on this corpus, with the
instrument that produced it named**, so the gate can be argued from evidence
rather than from impression. It is not a complaint about preflight: five of
the seven are consequences of deliberate, documented choices, one is fixed,
and one (row 7) was retracted the day after it was written when the engine
under it turned out to have a bug.

Assembled 2026-09-06 from that day's work. **Append to it; do not curate it** —
a retracted row stays, marked, because the retraction is itself a measurement.

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

**The practical half is fixed (2026-09-06).** `report["metrics"]` now carries
**`raw_score`**, the unclamped value, so `corpus_scorecard.diff` reports an
improvement to a floored design instead of losing it — `screenshot` reads
`score=0, raw_score=-272`. No grade, score or finding moves; un-clamping the
GRADE would re-base the scorecard and is still a product call. Inert until the
scorecard baseline is recaptured (`_metric_deltas` intersects key sets), which
is also why it cannot disturb an existing diff.

## 7. It preferred a design that dropped its ink — and then the ink came back

**This row is RETRACTED as a disagreement (2026-09-07), and kept because the
retraction is the finding.** It read, on 2026-09-06, that `logo_gaulke_roofing`
scored C 64 under `dissolve_phantom_blends` while loading no thread darker than
L\* 82, and F 16 under `bind_resnap_all_classes`, the one arm that loaded
`0020 Black` — the metric preferring a design that had dropped its ink.

**Both C 64 rows were produced by a bug in the flag, not by the metric.**
`dissolve_phantom_blends` was reading `~base_valid` as "the page" when
`base_valid` already has ENCLOSED pixels removed, so gaulke's black lettering
— inside a white label, on a black canvas — read as bordering the page and was
deleted rather than recoloured (50.3 mm², the 21.0 mm² wordmark included). Fixed
in #380; the trail is in `docs/flip-sheet-2026-09-06.md`.

On the fixed tree the metric ranks gaulke **correctly**:

| arm | darkest cone | grade |
|---|---:|---|
| off, `halo`, `resnap_small`, `satin_stroke`, `satin_patch` | `1375 Dark Charcoal`, L\* 15.9 | F 4 |
| `bind_resnap_all_classes`, all five | `0020 Black`, **L\* 0.0** | **F 16** |

Every arm that loads real Black grades HIGHER than every arm that does not.
That is agreement.

**The mechanism the row asserted is still true, and is now untestable on this
corpus.** `THREAD_MATCH_POOR` is driven by each thread's worst patch
(`preflight.py` module docstring), so a cone that is never loaded cannot carry
a poor match — deleting it deletes the finding. But swept across all seven
arms × 26 fixtures on the fixed tree, **ten (arm, fixture) pairs remove a cone
and not one of them scores higher**; all ten sit on fixtures scoring exactly 0
in both arms, where the grade is saturated and cannot express a preference in
either direction.

**So row 6 is why row 7 can no longer be measured.** The floor swallows the
question. That interaction is the durable finding here, and it is worth more
than the row it replaces: two entries on this list are not independent, and
un-clamping the grade (row 6's open half) is what would make this one testable.

The practical rule is unchanged and was always the useful part: **on a fixture
where a flag removes a cone, the grade is not evidence of anything and the cone
list is.** It is what caught the bug above.

`digitizer/tools/flip_sheet.py`, `docs/flip-sheet-2026-09-06.md`.
*(measured 2026-09-06, retracted on re-measurement 2026-09-07)*

---

## What this list is not

**Not an argument that the scorecard is bad.** Rows 3–5 are small; rows 1, 2
and 6 are the load-bearing ones (6 is the mechanism under 1), and both say the
same thing in different words: *the metric has no term for the thing the change
improved.* That is the gap phase 1 names, and it will not close by tuning
thresholds.

**Not a to-do list.** Two of the seven (3 and 4) are product calls that re-base
the scorecard for at least four fixtures — and half of 4 turned out not to be
one, and is fixed. One (5) is fixed. One (7) is retracted. The other three are
measurements waiting for a yardstick that can hold them.

**Not proof that a row keeps standing.** Row 7 held for one day. It was a real
measurement, correctly reported, on an engine with a bug in it — and the row
itself is what found the bug. **A row here is evidence about the tree it was
measured on, and the tree moves.** That is the argument for `head` being
recorded in every `flip_sheet.py` row from 2026-09-07 on, and for re-measuring
a row before quoting it at a gate.

**The honest use of it:** before claiming a digitizing change improved
quality, check whether it lands in one of these shapes. If it does, the
grade is not evidence either way, and the render is.
