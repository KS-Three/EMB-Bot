# The day the instruments were the defect

**2026-09-06.** Sixteen PRs, and the through-line is one shape: *a check that
computed the answer and did not say it.* Read this before proposing preflight
work, before quoting a grade, and before building any checker.

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
plausible. The third attempt recorded `HEAD` and `git status` before AND
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
