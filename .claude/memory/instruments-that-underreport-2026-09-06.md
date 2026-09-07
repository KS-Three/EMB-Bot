# The day the instruments were the defect

**2026-09-06.** Twenty-two PRs over the day (#363-#386), and the through-line
of the first sixteen is one shape: *a check that computed the answer and did
not say it.* Part two below is the second half of the day and a different
shape: *a number that stopped being true, and nothing noticing.* Read this
before proposing preflight work, before quoting a grade, and — especially —
**before building a checker**, because part two is largely about the class that
defeats one.

## The load-bearing finding: the score SATURATES

`run_preflight` prints `max(0, 100 - 30*blocks - 12*warns)`. Measured with the
new `tools/floor_depth.py`: **12 of the corpus's 52 design/garment combos sit
on exactly 0, with true scores from −272 to −38** — a 234-point spread behind
one printed value.

**`screenshot_phone_ui_golke` must clear 312 points, about ELEVEN blocking
findings, before its grade moves one letter.** `drone_render` 228 (~8);
the shallowest, `summit_badge` and `bridge_bar`, 78 (~3).

This is the missing half of a claim made three times this session and half-
wrong each time. `cfg.revalidate_small_shapes` fixes a **32.7 → 1.4 ΔE00**
thread error and moves no grade — partly because `THREAD_MATCH_POOR` judges
per THREAD on its worst patch (disagreement 1), and partly because the design
is hundreds of points under water. It also explains the exception:
`dissolve_phantom_blends` moves `gaulke_roofing` **F 0 → C 64** because gaulke
grades **F 4**, shallow rather than floored, so its improvement had somewhere
to go.

**On a floored design the grade is not evidence in either direction.** Quote
the metric that moved, or the render. `report["metrics"]["raw_score"]` now
carries the unclamped value so a scorecard diff can see it — but it is **inert
until the baseline is recaptured** (`_metric_deltas` intersects key sets).
Un-clamping the grade re-bases the whole scorecard and stays Kent's.

## Four checks that knew the answer and did not say it

- `THREAD_MATCH_POOR` computed the best already-loaded spool **only on the
  photo route**, so on the gradient lane — where all seven F fixtures and six
  of seven real customer logos live — it said *"pick a closer thread"* without
  consulting the design's own cone list. **5 of 24 blocking findings name a
  spool the design already loads**, including both of the F-wall's headline
  numbers: gaulke's 63.6 ΔE00 sits 58.6 from a loaded `1375`.
- It also never said how big the condemned shape was (0.58 mm² and 1,648 mm²
  read identically).
- `COLOR_STOPS_HEAVY` said *"Merge similar colors"* without naming a pair. On
  `logo_bridge_bar` the closest two are **1.8 ΔE00** apart, below
  `DELTA_E_VISIBLE`.
- `doc_claims` reported a clean bill without saying what it had examined.

**When a field's ABSENCE is a signal, widening where it appears breaks a
contract nobody wrote down.** `excess_delta_e` being None meant "judged on
raw"; a test asserted it and looked like a test to relax. It was not — the
payload now states `yardstick: "excess" | "raw"` outright.

## Measuring killed four builds and corrected a fifth

Do this before writing code, every time. It was right five times out of five.

| proposed | what the measurement said |
|---|---|
| ambiguous-line branch in `doc_claims` | never fires — 33 flag mentions, none ambiguous |
| extend the duplicate-cone fold | the cause is **already priced** by `cfg.bind_resnap_all_classes` |
| a doc file-PATH checker | **373 references, 0 stale** — paths here are right or deliberately historical |
| drop two slow byte-identity tests | saved **13s**, not the 380s `--durations` attributed |
| test-count checker (built) | first run's six "drifts" were **all false** — read the matches, not the count |

## Two traps that cost real time

**A long benchmark and an active worktree cannot share a machine.** Two
`--dist loadfile` measurements were thrown away because I edited the tree
while they ran; pytest reads it at COLLECTION, so an edit between two runs of
a pair silently re-bases the comparison. It shows as a passed count differing
by exactly the tests you added — easy to skim past when the wall-clock looks
plausible.

**Hit again 2026-09-07, in a shape this paragraph does not name, and it is
the worse one.** The edit was not a new FILE: `tests/test_scope_budget.py` was
already collected with three tests when three more were appended to it. The
run finished clean and reported **1993 passed** against the previous 1990 —
`+3`, exactly and plausibly "the new file" — while the three tests written
after collection were simply not in it. No error, no skip, and a total that
is *arithmetically consistent with what you intended*, which is the one case
a careful reader does not look at twice. Settled by PREDICTION: if 1993 was
1990 plus the first three only, a clean re-run must read **1996**, and it did
(3 failed, 1996 passed, 8 skipped, 7 xfailed). **Appending to an
already-collected file is the version with no tell at all. Do not touch the
tree during a full run; if you did, re-run.** The third attempt recorded `HEAD` and `git status` before AND
after. Result at CI's two workers: **23m53s → 22m27s, 5.8%**, not taken
because `loadfile` floors wall-clock at the slowest single FILE.

**`--durations` under xdist lies about shared caches.** `lru_cache` is
per-process; a run-count plugin showed `test_bind_resnap_all_classes.py` doing
**20 real pipeline runs for 8 distinct cases** (`screenshot(False)` computed on
three workers). A duration is that test's share of a bill several workers each
pay anyway.

## Left open, deliberately

- **The blend-band half of the third revisit mechanism.** `region_blobs` sews
  `0182` in two blocks that are each a gradient band of a *different* parent;
  bands are built in stage 6, long after the fold, and `bind_resnap_all_classes`
  does not touch it. One synthetic fixture; any fix is a sequencing change.
- **Four flag decisions**, now consolidated in
  `docs/pending-flag-decisions-2026-09-06.md` with what each buys, costs and
  risks — and which are gate-blocked rather than waiting.

---

## Part two: the same day, six more PRs, and what a checker cannot catch

The entry above stops at PR #379. The day ran to **#386**. The second half
found a different shape: not a check withholding what it knew, but a NUMBER
that stopped being true and nothing noticing.

### Four documentation defects, and only ONE was catchable by a checker

This is the part worth carrying forward, because the instinct after finding a
doc defect is to build a checker for it, and three of these four defeat that
instinct on structure rather than on effort.

| # | the defect | catchable? |
|---|---|---|
| 1 | a finding emits a payload field its `extra:` comment does not name | **YES** — `tests/test_finding_extra_documented.py` (#379) ast-parses the call and requires the field in the comment |
| 2 | `DigitizePanel.svelte` justified a button by quoting a message as ending *"Enlarging helps"* when it ended *"Enlarging helps BUT DOES NOT FULLY CLEAR IT … Remove or simplify"* | **NO** |
| 3 | `_coverage_findings` named `COVERAGE_WARN_UNITS`/`COVERAGE_BLOCK_UNITS` and gave their values as "2.5 and 3.5" when they evaluate to 6.67 and 9.33 | **NO** |
| 4 | `_same_hole_findings` says *"our benchmark is 9.8%"*, which the same ruling made ~2.7% | **NO** |

**Why each of the three defeats a checker, specifically:**

- **#2 is a TRUTHFUL SUBSTRING.** "Enlarging helps" really does appear in the
  source string. A fidelity check passes. The failure is a truncation that
  inverts the sentence — a reading problem, not a parsing one. And partial
  quotes in comments are legitimate and everywhere, so a checker that flagged
  them would flag almost every comment in the repo.
- **#3 names the constants but gives their values in a DIFFERENT FORM.**
  `doc_claims`' `_CONST` regex wants `NAME = <number>`; this is
  "`NAME` / `NAME` — 2.5 and 3.5" across an em-dash, and 2.5/3.5 are true as
  MULTIPLES (`2.5 * COVERAGE_FILL_LAYER_UNITS`). Both numbers are real; only
  the relationship is missing.
- **#4 names no constant at all.** It is a measured baseline in prose.

**So: do not build a fifth checker for this class.** `doc_claims.py` covers
what it can (`cfg.<flag>` defaults, `NAME = <number>`, documented test counts)
and #379 closed the payload-comment gap. What is left needs a reader.

### The habit that WOULD have caught #3 and #4, and it is not a checker

Both came from one ruling: `FILL_ROW_MM` 0.40 → 0.15 on 2026-09-03. `machine.py`
documents that change in twenty lines and warns in as many words —
*"every coverage number recorded before this date is in the old base and is
2.67x smaller than the same stack reads today"* — and **it did not save the
file next door.** Five statements were still in the old base three days later
(four coverage, one same-hole).

**When a constant's VALUE changes, grep the repo for the old literal.** That is
the practice. It is cheap, it is not a checker, and it would have found all
five in one pass.

Related, and the reason #4 matters beyond tidiness: the same-hole RATE is a
ratio whose denominator moved. A/B'd at both row pitches, penetrations grew
**×1.17–2.30** while repeat points moved ×0.98–1.15 (28 against 28 on
`logo_whitebg` — the same integer) and **`max_strikes` was identical on all
four fixtures**. The check went quiet across the whole corpus with the fabric
struck in exactly the same places. **Its silence is not evidence that anything
improved** — ROADMAP gate 4, arriving somewhere nobody had connected it to.

### Two of preflight's checks cannot be exercised by the corpus AT ALL

`DENSITY_STACKED` fires on **0 of 52** design/garment combos; `SAME_HOLE_HEAVY`
on **0 of 26**. Six fixtures carry a coverage PEAK over the warn level and every
one yields 0.0 mm² of qualifying patch, because `_COVERAGE_MIN_PATCH_MM2` is
doing all the work — as designed.

**Consequences, both directions:** a corpus A/B proves nothing about either
check, so their silence is not evidence the corpus is clean; and their
synthetic `_stacked(n)` / bounce plans are their ONLY test coverage, so do not
delete them as redundant.

### The four locationless findings are done

`STITCHES_TOO_SHORT`, `TRIM_HEAVY`, `DENSITY_STACKED`, `SAME_HOLE_HEAVY` all
now emit WHERE. Two carried a measurement that changed the advice:

- **`TRIM_HEAVY` was pointing at the wrong end of the design.** 866 corpus
  trims split **53% inside a shape / 47% between**, and the majority flips per
  design — in-shape dominant on 11 fixtures, between-shape on 11. Its one
  remedy ("merge or remove the smallest shapes") was right about half the time.
  **Not a discovery**: MASTER_SCOPE defect 6 has said "69% intra-shape" since
  2026-08-21. The repo knew; the instrument did not report.
- **`STITCHES_TOO_SHORT` never fires alone** (0 of 26) but only 66% of its
  short steps sit in a shape `LETTERING_TOO_SMALL` named — the rest are
  sewable columns (1.1–3.2 mm median) with a narrow waist. Redundant as a
  signal, not as a location. **Do not delete either check to dedupe them.**

### Two numbers that were simply wrong, and are now measured

- **The Studio's "Make it bigger" button clears `STITCHES_TOO_SHORT` on 1 of
  10** fixtures in one press (4 of 10 in two), and makes it **worse on 3** —
  `photo_dof_meadow` 0.36 → 0.58 → 0.71. The satin shape count rises on every
  fixture. The button is left in place; the numbers now sit beside it.
- **CI's `digitizer` job runs 10–42 minutes, not 12–18.** 220 jobs from the
  Actions API; the old figure was true when written and now holds for half.
  **Concurrency is refuted** (the 41.8-minute worst case ran with zero others
  in flight) and suite growth cannot carry it (the same test count lands at
  19.6 or 34.5 min). What is left is the runner, which nothing logged — the
  job now echoes `nproc`.

### And defect 16's last open half is priced, not built

Every surviving duplicate cone is **7 to 11 blocks apart — none adjacent** — so
"each merge is FREE (the cone is already loaded)" prices the thread and not the
sequence. The open blend-band half is **one GENERATED fixture**
(`region_blobs`, three Gaussian blobs); no client artwork in the corpus
produces one. `tools/cone_revisits.py` re-measures it after any sequencing
change.
