# Machine-physics engine change list — audited status

The 17-row engine change list in Part 2 of
[`docs/machine-physics-playbook-2026-07-31.md`](../machine-physics-playbook-2026-07-31.md),
audited row by row against the code on `main`, plus Part 3's worksheet
contract.

**Why this file exists.** The playbook was referenced by NOTHING — a grep over
`MASTER_SCOPE.md`, `DOCTRINE.md`, `ROADMAP.md`, `PRODUCT.md`, `COOKBOOK.md` and
every `docs/scope/*.md` returned zero hits on 2026-09-19. It carries a 17-row
change list with a per-row buildability column, most rows marked "Desk-safe",
and nothing pointed at it. That is why gaps in it get rediscovered by accident
rather than tracked.

**This is a status audit, not a commitment.** No row here is a defect until
Kent says it is. The playbook's own status column ("Desk-safe" vs
"Sew-out-gated") is carried through as the sort key, because it is the column
that says which rows ROADMAP gate 1 actually blocks.

**Method.** Targeted reads of `digitizer/digitizer_core/` (`fabrics.py`,
`machine.py`, `config.py`, `preflight.py`, `warnings_codes.py`,
`stage5_overlap.py`, `stage7_sequence.py`, `stage6_satin.py`),
`app/src/lib/estimate.js` and `src/pdfsheet.js`, after `git fetch --all`.
Nothing was executed. Verdicts are scored against **`origin/main` at
`1ac731cd`** — work parked on an open PR is called out as such, because a
branch is not what ships.

*(audited 2026-09-20 — code read, `origin/main` 1ac731cd)*

---

## Part 2 — the 17 rows

Verdict key: **Built** = shipping and on by default · **Gated** = built,
reachable only behind a default-off flag · **Partial** = some sub-items built,
others absent · **Not built** = no implementation on `main`.

| # | Law | Target | Playbook's own gate | Verdict | Evidence |
|---|---|---|---|---|---|
| 1 | 16, 27 | `fabrics.py` — per-fabric top spacing table + 0.35 mm engine floor | Desk-safe | **Not built** | `Fabric` carries `density_adjust` (a row-spacing MULTIPLIER), not a spacing table. No hard floor anywhere. |
| 2 | 23 | `fabrics.py` — pull comp `base + slope × width` | **Sew-out-gated** | **Not built** | `pull_comp_mm: float`, one scalar per preset. Gate 1 blocks this one for real. |
| 3 | 33 | `fabrics.py` — `assumed_backing` per preset | Desk-safe | **Not built** | No such field. Backing is *inferred from stitch count* in two places instead: `preflight.STITCHES_CUTAWAY_MIN = 25_000` → `STABILIZER_CUTAWAY`, and `src/pdfsheet.js`'s `CUTAWAY_STITCHES` line. That is the law's "declare it, don't hide it", inverted. |
| 4 | 28, 30 | `fabrics.py` — underlay ledger + knockdown on pile | Desk-safe | **Partial** | Ledger EXISTS and is consumed: `fill_underlay` / `satin_underlay` per preset, read at `stage7_sequence.py:1559` and passed as `underlay_style`. Missing: per-preset spacing/inset (`UNDERLAY_ZIGZAG_MM` 2.0, `UNDERLAY_LATTICE_MM` 2.5, `UNDERLAY_INSET_MM` 1.0 are engine-wide), "top spacing relaxes one step when underlay upgrades", and knockdown fill — zero hits repo-wide for knockdown / pile-taming / nap. Terry and fleece say "topping essential" in a `notes` STRING only. |
| 5 | 17, 18 | `machine.py` — `NEEDLE_D`, `SAME_HOLE_R`, MIN_WALK/SATIN/FILL, <0.5 mm filter | Desk-safe | **Partial** | The sub-0.5 mm filter is real and applied across tiers (`if d >= machine.TINY_STITCH_MM` in `stage6_border`/`contour`/`detail`/`fill`). `MIN_STITCH_MM = 1.0` is ONE global floor, not the three per-technique floors (walk 1.5 / satin 1.0 / fill 2.0). No `NEEDLE_D`, no `SAME_HOLE_R` — preflight carries its own unrelated `_SAME_HOLE_QUANTUM_MM = 0.1`. |
| 6 | 36, 38 | `machine.py` — speed model, `TRIM_COST`, thread budget | Desk-safe | **Partial** | `THREAD_LENGTH_FACTOR = 1.35` built. No spm model, no `TRIM_COST`. The only `spm` in the engine is two appliqué-scoped constants (`APPLIQUE_COVER_SPM = 700`, `APPLIQUE_TRIM_HEAVY_SPM = 650`). |
| 7 | 22 | stage 5 — pull comp at penetration ends along the stitch angle | Desk-safe | **Gated** | `stage5_overlap.py:332` `directional = bool(cfg.directional_comp) and pull > 0`; `config.py:934` `directional_comp: bool = False`. The shipped path still dilates uniformly. |
| 8 | 24 | stage 5 — push cutback 0.4 / 0.8 | **Sew-out-gated** | **Gated, and half absent** | `PUSH_CUTBACK_MM = 0.4` exists but is consumed ONLY under the same flag as row 7 (`stage7_sequence.py:1594`, `:1917` — `end_cutback_mm=(machine.PUSH_CUTBACK_MM if cfg.directional_comp else 0.0)`). The 0.8 border-junction value does not exist; `machine.py:484` says so in its own words: *"the border tier does not consume this yet"*. |
| 9 | 26 | stage 5 — overlap angle- and fabric-conditional | Desk-safe defaults; gate the knit value | **Not built** | `config.py:918` `overlap_mm: float = 0.25`, scalar. That default is well under the law's 1.0–2.0 mm parallel-join figure and under its own 0.8 mm "engineered gaps below this close up" line. No forbid-gap rule. |
| 10 | 25 | stage 7 — fill→border adjacency, big-before-small, caps, basting box | Desk-safe | **Partial** | `borders_last: bool = True` — ON, and it is the adjacency half. Big-before-small: zero hits. Basting box: zero hits. Cap ordering: see row 11. |
| 11 | 34 | stage 7 + preflight — cap mode | Desk-safe | **Not built on `main`** | The ordering half is built and parked OFF as `cfg.cap_center_out` on **open PR #529** (`claude/cap-center-out`, `f0371743`) — `git grep cap_center_out origin/main` returns nothing, so it does not ship. The preflight half is absent outright: no cap warning codes, no ~57 mm height warn, no seam-zone detail warn, no sectioned-cap-fill block. (Beware the word: "cap" in this codebase means type cap-height or `EDGE_CAP_*`, never headwear.) |
| 12 | 27 | preflight — per-region coverage map | Warn desk-safe; block sew-out-gated | **Partial** | Built exactly as specced, thresholds included: `COVERAGE_WARN_UNITS = 2.5 ×`, `COVERAGE_BLOCK_UNITS = 3.5 ×` `COVERAGE_FILL_LAYER_UNITS`, surfaced as `DENSITY_STACKED` / `DENSITY_EXTREME`. Missing: auto-oppose stacked fill angles, auto-hole, and the "no holes under objects < 5×5 mm" rule — zero hits for all three. |
| 13 | 17, 35 | preflight — needle-penetration proximity map | Desk-safe | **Built — per the field note, NOT per this row** | `SAME_HOLE_HEAVY` at `SAME_HOLE_RATE_MAX = 0.25`, binned at `_SAME_HOLE_QUANTUM_MM = 0.1`, INFO severity so it never costs score. The row's own "flag pairwise gaps < 0.5 mm" was deliberately NOT built: the playbook's own Field Note (Law 17, 2026-08-01) measured that reading and dismissed it — it *"would condemn every satin column ever sewn, professional ones included"*. The shipped check is the field note's replacement (a rate 2.6× the 9.455% corpus baseline), which is the honest outcome, not a gap. |
| 14 | 35 | preflight — small-text battery | Desk-safe | **Partial** | Built: `LETTERING_TOO_SMALL` at `MIN_LETTER_EXTENT_MM = 4.0` (the law's own floor), `LETTERING_ILLEGIBLE` with `LEGIBILITY_WARN`/`_BLOCK`, and underlay stripped below threshold (`stage7_sequence.py:1913`, `underlay_style="none" if small`). Missing: the counters-under-0.8 mm flag and trims-per-word enforcement — zero hits for both. |
| 15 | 31 | preflight — satin clamps < 1 mm run, > 8 mm split | Desk-safe | **Built, at different numbers — both ways** | Under-width → 3-pass bean run (`HAIRLINE_STROKES_AS_RUN`, `_bean_along`, `BEAN_PASSES = 3`) but at `SATIN_MIN_CROSS_MM = 0.5`, so 0.5–1.0 mm strokes still satin where the law says run. Split at `SPLIT_SATIN_ABOVE_MM = 5.0`, TIGHTER than the law's 8 mm — and corpus-derived (its comment carries the 36-file split-fraction table), so the divergence is evidence-backed, not drift. |
| 16 | 36, 38 | preflight — cost card on every output | Desk-safe | **Partial** | `app/src/lib/estimate.js` gives stitches, thread changes, trims and thread metres; `COLOR_STOPS_HEAVY` fires past `COLOR_STOPS_MAX = 10` (the law's "warn if > needle count"). Missing: estimated runtime and trim cost — both need row 6's speed model first. |
| 17 | 37 | preflight — monotonic smoothness score | Desk-safe | **Partial — built, but not where the row puts it** | The score exists as offline instruments (`tools/edge_smoothness.py`, `curve_fidelity.py`, `edge_wobble.py`, `curve_tiers.py`) and is monotonic with no cutoff, as the law demands. It does NOT reach preflight: no smoothness/roughness/churn code among preflight's 24 codes or `warnings_codes.py`'s 58. `edge_smoothness.py`'s own docstring is the proof — *"`preflight` graded `logo_whitebg` **A 100**"* on a design Kent calls not smooth. |

**Tally: 1 built as specced (13, via the field note's revision), 1 built at
divergent numbers (15), 2 built but gated off (7, 8), 8 partial (4, 5, 6, 10,
12, 14, 16, 17), 5 not built (1, 2, 3, 9, 11).**

### What the buildability column says

Of the **5 not-built rows, only row 2 is blocked by ROADMAP gate 1** — its mm
table is trade folklore with no manufacturer source, and fabric settles it.
Rows **1, 3, 9 and 11 are marked Desk-safe by the playbook itself**: published
values, a declared field, a conditional the law supplies numbers for, and a set
of Melco-sourced cap rules.

The same holds inside the partials. The unbuilt remainders of rows **4, 5, 6,
10, 12, 14, 16 and 17** are desk-safe work — a knockdown pass, named needle
constants, a speed model, two ordering rules, two auto-remedies, two lettering
checks, a runtime figure, and wiring an instrument that already exists to the
output that already ships.

Rows 7 and 8 are the opposite case and should be left alone: both are built and
both are held behind `cfg.directional_comp = False` on purpose, pending
playbook Part 4 tests 1 and 4. **Gate 1 is a refusal, not a preference** — do
not flip them.

---

## Part 3 — the worksheet contract, separately unbuilt

Part 3 says the PDF worksheet "must start carrying the digitizer's assumptions,
per job". `src/pdfsheet.js` today carries placement, hoop, dimensions, stitch
count, colour count, trims, thread metres, and a stabilizer line keyed off
stitch count (`CUTAWAY_STITCHES`).

Missing against the contract:

- assumed backing class and weight (blocked on row 3's `assumed_backing`; today
  it is *guessed from stitch count*, which is the failure the law names)
- topper yes/no
- needle spec (75/11 RG or SES; escalate to 80/12 for metallic)
- tension targets in grams, with the satin-underside 1/3–2/3 check
- the colour-stop → needle map. **DST carries no colour data, so the operator
  hand-maps every stop, every job** — the most concrete operator cost on this
  list
- estimated runtime at 650 spm (blocked on row 6)
- cap jobs: load orientation, ~900 spm, placement 0.5 in above bill

Nothing here is a physical constant, so gate 1 does not reach any of it. The
two real dependencies are internal: rows 3 and 6.

---

## Corrections to the 2026-09-19 pre-read

Five verdicts moved on re-verification. Recorded because four of the five moved
in the direction of *"we have less than we thought"*, which is the direction
that matters.

1. **Row 8 was scored Built; it is Gated, and half of it is absent.**
   `PUSH_CUTBACK_MM = 0.4` exists as a constant, but its only two call sites are
   behind `cfg.directional_comp`, the same flag as row 7 — and the 0.8
   border-junction value was never built. Scoring a constant's existence is not
   scoring its reachability. (Same lesson row 7's own note already records:
   *"I first scored this BUILT off the module docstring — SCORE DEFAULTS, NOT
   PROSE."* Here it was the constant rather than the docstring.)
2. **Row 17 was scored Built as `curve_turn_deg`; that is a different thing.**
   `curve_turn_deg = 15.0` is a stage-4 vertex-refinement threshold on input
   geometry. Law 37 asks for a monotonic smoothness score on the stitch path,
   with no cutoff. The real score exists in `tools/`, and does not reach
   preflight.
3. **Rows 12 and 14 were scored Built; both are Partial.** Each has two
   sub-items with zero implementation (auto-oppose + auto-hole; counters +
   trims-per-word).
4. **Row 4 was scored Not built; it is Partial.** The per-preset underlay ledger
   exists and stage 7 consumes both its fields. Worth noting because
   `fabrics.py:22` still comments `satin_underlay` as *"unused until build step
   4"* — **that comment is stale**, and it is what a grep-only read believes.
5. **Row 11's cap ordering is on an OPEN PR, not on `main`.** PR #529 is open
   and unmerged; `cap_center_out` is absent from `origin/main`. Counting
   unmerged lane work as shipped is the CLAUDE.md rule-8 trap from the other
   direction.

Two smaller ones, neither changing a verdict: `spm` appears in **two** engine
constants, not one (both appliqué-scoped); and the stitch-count stabilizer guess
lives in **preflight as well as** `pdfsheet.js`.
