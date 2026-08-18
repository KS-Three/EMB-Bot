# Measurement-Debt Knockout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close five open measurement debts: (1) verify the satin-promotion gain with corrected kappa, (2) diagnose the `bridge_lc`/`hotel_fremont_hat` paired regressions, (3) truth-up the stale pooled-THREAD_MATCH_POOR doc text, (4) install a baseline-recapture cadence rule, (5) build the segmentation-alignment probe and draft its spec.

**Architecture:** No engine code changes anywhere in this plan. Tasks 1–2 and 5 build/run *instruments* (`digitizer/tools/pro_parity/`) against pinned worktrees; tasks 3–4 are documentation corrections backed by fresh verification runs. Task 5's deliverable is a probe + findings doc + draft spec for Kent — explicitly NOT an implementation.

**Tech Stack:** Python 3 (digitizer `.venv`), existing pro-parity toolchain (`prep_both.py`, `scorecard.py`, `gateprobe.py`), git worktrees.

## Global Constraints

- **Public repo.** Do not introduce any client name, artwork, or stitch file not already committed. The design slugs used below (`becker_*`, `bridge_*`, `hotel_fremont_*`, `mfab_*`, …) already appear in committed docs — using the slugs is fine; committing new files from `G:/My Drive/EMB-Bot/Embroidery Files` or `scratch_kent/` is NOT.
- **Measure in a pinned worktree** (ROADMAP advisory ordering). Never measure against a drifting checkout.
- **Worktrees have no `.venv`.** Always invoke the primary checkout's interpreter — `<repo-root>/digitizer/.venv/Scripts/python.exe` — with `cwd` inside the worktree's `digitizer/`, and verify module resolution before trusting any number (Task 1 step 2 shows how). The pro-parity scripts insert their own file's parents onto `sys.path`, so running the *worktree's copy* of the script resolves the *worktree's* `digitizer_core`.
- **Never pipe pytest (or any run) to `tail`** — you get tail's exit code.
- Corpus asset root: `PRO_PARITY_ROOT="G:/My Drive/EMB-Bot/Embroidery Files"` (prep_both.py's documented default; reading from Drive is fine, only live repos are banned there).
- **Branch routing:** Tasks 1–2 commit to `claude/satin-gate-attribution` (they are that branch's own unmet acceptance criterion — the promotion commit `45d817a` is NOT in main). Tasks 3–5 commit to a new lane `claude/measurement-debt` cut from `origin/main` (`d96f9ff`).
- **ROADMAP hard gate 4:** no quality claim on a raw agreement number anywhere in any doc this plan touches.
- Only Kent advances phases or merges; every task ends at a commit on its lane, not a merge.

---

### Task 1: Corrected-kappa verification of the satin promotion (item 1)

The satin-routing spec (`docs/superpowers/specs/2026-08-16-satin-routing-gate-attribution-design.md` §4) set "corrected kappa from `scorecard.py`'s `parts["sttype"]` must rise" as the primary acceptance bar and barred raw agreement. The published figures (corpus mean 45.8→48.1, agreement 55.4%→58.9%) were never checked against that bar — `MASTER_SCOPE.md:102-109` carries the caveat. This task runs the check.

`scorecard.py` already computes everything needed: each design's `score.json` carries `parts.sttype` (chance-corrected, i.e. Cohen's kappa), `parts_raw.sttype` (raw agreement), and `detail.chance_floor.sttype` (the design's own chance floor). "Before" = `origin/main` (`d96f9ff`); "after" = `claude/satin-gate-attribution` head (`2729ea5`, contains promotion commit `45d817a`).

**Files:**
- Create: `digitizer/tools/pro_parity/kappacheck.py` (comparison instrument, committed — reusable for every future promotion)
- Modify: `MASTER_SCOPE.md:102-109` (resolve the caveat with the measured verdict)
- Modify: `docs/satin-gate-attribution-2026-08-16.md` (append a §9 with the corrected numbers)

**Interfaces:**
- Consumes: `score.json` files written by `scorecard.py` (`{"score", "parts": {"sttype": float, ...}, "parts_raw": {...}, "detail": {"chance_floor": {"sttype": float, ...}}}`)
- Produces: `kappacheck.py <before_dir> <after_dir>` printing a per-design table and corpus means; Task 2 reuses both prepped run directories.

- [ ] **Step 1: Create the two pinned worktrees**

```powershell
cd <repo-root>
git worktree add .claude/worktrees/kappa-before d96f9ff
git worktree add .claude/worktrees/kappa-after 2729ea5
```

- [ ] **Step 2: Verify module resolution hits each worktree's own `digitizer_core`**

```powershell
$py = "<repo-root>/digitizer/.venv/Scripts/python.exe"
cd <repo-root>\.claude\worktrees\kappa-before\digitizer
& $py -c "import digitizer_core; print(digitizer_core.__file__)"
```

Expected: a path under `.claude\worktrees\kappa-before\`. Repeat for `kappa-after`. If either prints the primary checkout's path, STOP — fix `cwd`/`PYTHONPATH` before running anything else.

- [ ] **Step 3: Run prep_both + scorecard in each worktree (background, CONCURRENT — the two legs are fully independent: separate worktrees, separate out dirs, shared corpus is read-only)**

For each `$wt` of `kappa-before`, `kappa-after` (from that worktree's `digitizer/` directory, `$py` as above — the out path DERIVES from `$wt`; never hardcode one leg's path into the other, or the second run destroys the first):

```powershell
$wt = "kappa-before"   # or "kappa-after"
$env:PRO_PARITY_ROOT = "G:/My Drive/EMB-Bot/Embroidery Files"
$env:PRO_PARITY_OUT  = "<repo-root>/.claude/worktrees/$wt/parity_out"
$env:PRO_PARITY_FORCED_CLASS = "flat"
& $py tools/pro_parity/prep_both.py
& $py tools/pro_parity/scorecard.py (Get-ChildItem "$env:PRO_PARITY_OUT/real" -Directory).FullName
```

Expected: 15 design dirs under `<out>/real/`, each with `score.json`. If a run dies partway (crash, sleep, Drive hiccup): do NOT re-run all 15 — `prep_both.py` takes positional slug args to prep only the missing designs, and its manifest write merges into an existing `manifest.json` (built for exactly this). Re-invoke with only the missing slugs. `PRO_PARITY_FORCED_CLASS=flat` matches the attribution run exactly (14 of 15 labelled flat by Kent; 10 of 15 otherwise misroute to the photo lane — `docs/satin-gate-attribution-2026-08-16.md` §1).

- [ ] **Step 4: Sanity-pin the reproduction before comparing**

The after-run's plain corpus mean must reproduce ≈48.1 and the before-run ≈45.8 (`scorecard.py` prints the summary table). If they do not, STOP and diagnose the environment difference first (systematic-debugging skill) — comparing kappas across a non-reproducing rerun attributes environment drift to the promotion.

- [x] **Step 5: `kappacheck.py` — EXISTS ON DISK, do not rewrite from this plan**

The file was created (and subsequently review-hardened: argv/usage guard, empty-shared-set exit, None-safe floor formatting) at `digitizer/tools/pro_parity/kappacheck.py` during execution. The disk copy is canonical; this plan intentionally carries no source for it to prevent a plan-following worker from regressing the hardened version. Normative contract only: it reads each design dir's `score.json` keys `parts.sttype` (corrected kappa), `parts_raw.sttype`, `detail.chance_floor.sttype`, `score`; compares only designs present in BOTH runs (naming excluded ones); prints per-design table + corpus mean kappa/score deltas + a verdict line ("KAPPA ROSE — gain is real" / "KAPPA DID NOT RISE — published gain is the floor moving").

- [ ] **Step 6: Smoke-test the instrument on fabricated dirs before the real read**

```powershell
$t = "C:/Users/EE-LT-~1/AppData/Local/Temp/claude/kappacheck-smoke"
New-Item -ItemType Directory -Force "$t/b/x", "$t/a/x" | Out-Null
'{"score": 40.0, "parts": {"sttype": 0.10}, "parts_raw": {"sttype": 0.55}, "detail": {"chance_floor": {"sttype": 0.50}}}' | Set-Content "$t/b/x/score.json"
'{"score": 43.0, "parts": {"sttype": 0.20}, "parts_raw": {"sttype": 0.60}, "detail": {"chance_floor": {"sttype": 0.50}}}' | Set-Content "$t/a/x/score.json"
& $py digitizer/tools/pro_parity/kappacheck.py "$t/b" "$t/a"
```

Expected: one row for `x`, `dkappa +0.100`, verdict "KAPPA ROSE".

- [ ] **Step 7: Run it on the real before/after dirs and record the verdict**

```powershell
& $py digitizer/tools/pro_parity/kappacheck.py `
  "<repo-root>/.claude/worktrees/kappa-before/parity_out/real" `
  "<repo-root>/.claude/worktrees/kappa-after/parity_out/real"
```

Paste the full table into the session log. Both outcomes are acceptable results — "kappa fell" is a finding, not a failure.

- [ ] **Step 8: Update the two docs with the measured verdict**

- `docs/satin-gate-attribution-2026-08-16.md`: append `## 9. Corrected kappa (the spec's actual acceptance bar)` with the table and verdict. If kappa did NOT rise, §9 must say the headline +2.3 is unestablished and the promotion needs re-judging — do not soften it.
- `MASTER_SCOPE.md:102-109`: replace the "Short task, not yet run" caveat with the verdict and a `(measured <date> — kappacheck vs d96f9ff)` pointer. WARNING: the file sits at exactly 800/800 lines — this edit must be net-negative (the caveat block being replaced is 8 lines; the verdict should be shorter), or lines must be freed elsewhere in the same edit. Verify `wc -l` ≤ 800 before committing.

- [ ] **Step 9: Commit (on `claude/satin-gate-attribution`)**

```powershell
git add digitizer/tools/pro_parity/kappacheck.py docs/satin-gate-attribution-2026-08-16.md MASTER_SCOPE.md
git commit -m "measure: corrected-kappa verdict on the satin promotion (spec 2026-08-16 §4 acceptance)"
```

---

### Task 2: Diagnose the paired same-artwork-opposite-outcome regressions (item 3)

`bridge_lc` lost 2.8 (sttype 0.23→0.15) from the same promotion that gained its sibling `bridge_hat` +1.4; `hotel_fremont_hat` showed the same pattern in the stage-0 work (−4.3 forced flat, sibling fine). Hypothesis on record (`docs/satin-gate-attribution-2026-08-16.md` §6): part of each delta is *which pro file we are compared against* — siblings share artwork but are scored against different professional digitizations (hat = Richardson 112 cap front, lc = left chest, Hotel Fremont's second file is a twill patch — `prep_both.py` DESIGNS table). This is a diagnosis task: the deliverable is a findings doc, not a fix.

**Files:**
- Create: `docs/paired-regression-diagnosis-2026-08-<day>.md`
- Modify: `MASTER_SCOPE.md` (only if the artifact is confirmed — one sentence in live defect 5 noting per-design deltas carry reference-file variance)

**Interfaces:**
- Consumes: Task 1's two prepped run dirs (`kappa-before`/`kappa-after` `parity_out/real/bridge_lc`, `bridge_hat`), `gateprobe.py --csv`, `scorecard.py --explain`.
- Produces: a named mechanism for the regression pair, or a documented dead end with the evidence that killed the hypothesis.

- [ ] **Step 1: Pull the component-level story for the pair**

```powershell
& $py tools/pro_parity/scorecard.py --explain `
  "$after/real/bridge_lc" "$after/real/bridge_hat"
```

(`$after` = the kappa-after `parity_out`; run from `kappa-after/digitizer`.) Record which components differ between siblings and whether `bridge_lc`'s loss is concentrated in `sttype` (expected: yes, 0.23→0.15).

- [ ] **Step 2: Identify the shapes the promotion flipped — run over ALL 15 designs at once (the full-corpus run costs minutes and step 4 needs the hotel_fremont pair anyway)**

```powershell
& $py tools/pro_parity/gateprobe.py --features --csv corpus_after.csv `
  (Get-ChildItem "$after/real" -Directory).FullName
cd ..\..\kappa-before\digitizer
& $py tools/pro_parity/gateprobe.py --features --csv corpus_before.csv `
  (Get-ChildItem "$before/real" -Directory).FullName
```

In the CSVs: a *flipped* shape has `reason == "promoted_ribbon"` in the after run (gateprobe re-runs `classify_ribbon` live, so the before-worktree's copy has no promotion path — its verdicts are the shipped gates). For every flipped shape record `(design, shape_id, pro_dominant, pro_satin_cells, pro_fill_cells)`.

- [ ] **Step 3: Test the hypothesis directly**

The hypothesis predicts: the SAME artwork shape (same geometry, matched by area/position across the two siblings' `ours_regions.json`) flips to satin in both, and lands on ground `bridge_hat`'s pro sewed as satin (`pro_dominant == "satin"` → gain) but `bridge_lc`'s pro sewed as fill (`pro_dominant == "fill"` → the leak driving 0.23→0.15). Build the pairing with a throwaway script in the scratchpad (match shapes across siblings by `area_mm2` within 5% after scaling by design bbox ratio; the artwork is identical so the region decomposition should correspond ~1:1 — if it does not, that itself is a finding: same art, different segmentation, record it).

- Hypothesis CONFIRMED if ≥ half of `bridge_lc`'s flipped-shape pro-fill cells sit on shapes whose `bridge_hat` twin is pro-satin.
- Hypothesis KILLED if `bridge_lc`'s flipped shapes are pro-fill in BOTH siblings (then the promotion is genuinely wrong on those shapes and the regression is real signal — record which feature values (`explained`, `elongation`) let them through).

- [ ] **Step 4: Repeat the confirmed/killed test for `hotel_fremont_hat` vs its sibling** using the same full-corpus CSVs from step 2 (no new probe runs needed).

- [ ] **Step 5: Write the findings doc**

`docs/paired-regression-diagnosis-2026-08-<day>.md`, structured like the attribution doc: verdict up front, method, per-shape evidence table, and the consequence — if confirmed, the honest statement is "per-design deltas on sibling pairs carry ±N points of reference-file variance; corpus-level deltas remain valid because siblings average out". Compute N from the measured pair.

- [ ] **Step 6: Update MASTER_SCOPE live defect 5 (one sentence, only if confirmed) and commit**

```powershell
git add docs/paired-regression-diagnosis-*.md MASTER_SCOPE.md
git commit -m "measure: bridge_lc/hotel_fremont paired-regression mechanism"
```

---

### Task 3: Truth-up the stale pooled-THREAD_MATCH_POOR text (item 4)

The complaint this plan item started from is already fixed in code: `619e9ad "fix: score THREAD_MATCH_POOR per region, not per pooled thread median"` landed 2026-08-11 (`preflight.py:46-55` documents the per-region instrument and both pooling failures), and the baseline was recaptured under the per-region yardstick (`307e69d`). What remains stale is the *doc*: `docs/scope/1-auto-digitizing-quality.md:286-297` still describes the pooled behaviour as a live "gap worth a future look".

**Branch:** `claude/measurement-debt` (cut from `origin/main` — this and Tasks 4–5 are main-lane doc/instrument work, independent of the satin branch).

**Files:**
- Modify: `docs/scope/1-auto-digitizing-quality.md:286-297`
- Verify (read-only): `digitizer/testdata/corpus_scorecard_baseline.json`, `digitizer/digitizer_core/preflight.py:46-55`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks consume.

- [ ] **Step 1: Cut the lane**

```powershell
cd <repo-root>
git worktree add .claude/worktrees/measurement-debt -b claude/measurement-debt d96f9ff
```

- [ ] **Step 2: Verify what the current baseline actually says** — read `drone_render` and `summit_badge` entries in `digitizer/testdata/corpus_scorecard_baseline.json` (grade, `THREAD_MATCH_POOR` finding count, `thread_worst_delta_e`) at `d96f9ff`. These are the post-per-region numbers; quote them, do not re-derive from the pre-fix doc text.

- [ ] **Step 3: Append the correction** (scope docs are correction-by-append, matching the file's own existing "Correction:" pattern — do not rewrite the historical paragraphs):

After line 297's paragraph, add:

```markdown
**Update 2026-08-<day>: the pooled-vs-per-region gap described above is
CLOSED.** `619e9ad` (2026-08-11) rescored `THREAD_MATCH_POOR` per region —
each thread is judged by its WORST region's per-pixel CIEDE2000 median,
never a pooled per-thread median (`preflight.py`, `_thread_match_findings`;
both measured pooling failures are documented on `_region_color_errors`).
The corpus baseline was recaptured under the per-region yardstick in
`307e69d`. Current baseline reads for the two designs this section
discusses: <quote the step-2 numbers with grades and finding counts>.
The paragraphs above stand as the record of why the change was needed.
```

- [ ] **Step 4: Sweep for other stale copies of the claim**

```powershell
git grep -n "pooled" -- "*.md" | Select-String -NotMatch "scope-history"
```

Fix any other doc that still presents pooling as current behaviour (append-only docs in `docs/` get a dated correction line, same pattern; `scope-history.md` is append-only history — leave it).

- [ ] **Step 5: Commit**

```powershell
git add docs/
git commit -m "docs(scope): pooled THREAD_MATCH_POOR gap closed by 619e9ad — truth-up stale text"
```

---

### Task 4: Baseline-recapture cadence rule (item 6)

`docs/scope/1-auto-digitizing-quality.md:276-284`: the corpus baseline sat unrefreshed through ~15 digitizer commits, so recapture `821d066` folded undiagnosed drift into the new baseline and the doc misattributed it to noise. The fix is a *procedure with a tripwire*, not more process: stamp the baseline with its capture commit, and make the recapture procedure demand drift attribution.

**Files:**
- Modify: `COOKBOOK.md` (the "Running things" section — add the recapture procedure)
- Investigate first: whatever script/test currently captures and consumes `digitizer/testdata/corpus_scorecard_baseline.json`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing other tasks consume.

- [ ] **Step 1: Find the capture path and the consumer**

```powershell
git grep -ln "corpus_scorecard_baseline" -- "*.py" "*.yml"
```

Read what turns up (capture script + consuming test/CI). Establish *why* 15 commits of drift stayed silent — expected answer: the baseline is compared only when a test runs against it and the comparison tolerates or ignores sub-threshold movement, or the capture is manual-only. Record the actual mechanism in the commit message; do not guess it in the doc.

- [ ] **Step 2: Add the capture-commit stamp if the format lacks one**

If `corpus_scorecard_baseline.json` does not already record its capture commit: modify the capture script (found in step 1) to write `{"captured_at_commit": "<git rev-parse HEAD>", "captured_date": "<ISO date>"}` at the top level, alongside the existing content — and regenerate nothing yet (stamping happens naturally at the next legitimate recapture; a stamp-only regeneration would itself fold in drift, the exact failure this task exists to stop).

- [ ] **Step 3: Write the COOKBOOK rule** (in "Running things", beside the existing golden-recapture guidance):

```markdown
### Recapturing `corpus_scorecard_baseline.json`

The baseline once sat unrefreshed through ~15 digitizer commits; the next
recapture folded all of that undiagnosed drift into itself and the change
was misread as noise (docs/scope/1-auto-digitizing-quality.md, the 821d066
correction). Two rules stop a repeat:

1. **Recapture is diff-then-capture, never capture-blind.** Before writing
   the new baseline, run the scorecard at HEAD against the OLD baseline and
   attribute every fixture that moved — to your change, or to a named
   earlier commit, or explicitly as "undiagnosed drift" — in the recapture
   commit's message. An unattributed mover blocks the recapture.
2. **Staleness is measured, not remembered.** The baseline records
   `captured_at_commit`. If `git log --oneline <captured_at_commit>..HEAD
   -- digitizer/digitizer_core` shows landed pipeline commits, any grade
   comparison against the baseline is comparing against a stale ruler —
   say so wherever the comparison is quoted.
```

- [ ] **Step 4: Run the consumer test found in step 1 to confirm nothing changed behaviourally** (stamp code is capture-time only). Run the single test file, not the 7–11 min suite:

```powershell
cd digitizer
& .venv/Scripts/python -m pytest -q tests/<consumer_test_found_in_step_1>.py
```

Expected: same pass/fail set as before the change (check COOKBOOK "Running things" for the known-failing list before reading red as regression).

- [ ] **Step 5: Commit**

```powershell
git add COOKBOOK.md digitizer/
git commit -m "process: baseline recapture is diff-then-capture, and the baseline knows its own commit"
```

---

### Task 5: Segmentation-alignment probe + draft spec (item 7)

The largest measured headroom with no owner: an oracle knowing the pro's per-shape answer scores 76.6% stitch-type agreement vs our 55.4%, and 48.1% of graded cells sit in shapes under 75% one pro type — our regions straddle the pro's satin/fill boundaries (`docs/satin-gate-attribution-2026-08-16.md` §4, MASTER_SCOPE live defect 5 remainder). Before anyone designs a fix, measure *what kind* of straddling it is — the dominant pattern decides the mechanism. Deliverable: probe + findings doc + draft spec for Kent. NOT an implementation; this is engine-track Phase 3 territory and the ROADMAP ordering is advisory-only, so the spec proposes, Kent disposes.

**Files:**
- Create: `digitizer/tools/pro_parity/splitprobe.py`
- Create: `docs/segmentation-alignment-<date>.md` (findings)
- Create: `docs/superpowers/specs/<date>-segmentation-alignment-design.md` (draft spec, marked DRAFT — awaiting Kent)

**Interfaces:**
- Consumes: Task 1's `kappa-after` prepped dirs (`ours_regions.json` + the scorecard cell machinery — same join `gateprobe.py` uses: `scorecard.load_side`, `register`, `cell_stats`, and gateprobe's `_cells_of`).
- Produces: per-shape straddle classification CSV; the findings doc's pattern distribution.

- [ ] **Step 1: Write the straddle-pattern classifier core with a unit test first**

The one piece of real logic is classifying a shape's pro-type cell layout into patterns. Everything else is reuse of the gateprobe join. Patterns:

- `ring`: pro-satin cells form a boundary band around a pro-fill core (the classic "pro satins the outline, fills the body" — if dominant, the fix is *border-satin generation on our existing regions*, not segmentation surgery)
- `split`: pro types partition the shape into 2+ compact sub-areas side by side (fix would be *region splitting at an artwork-visible boundary*)
- `speckle`: neither — mixed at cell scale (likely registration/cell noise; not actionable at region level)

Test file `digitizer/tests/test_splitprobe.py`:

```python
import numpy as np

from tools.pro_parity.splitprobe import classify_straddle

# Cell grids: 1 = pro satin, 2 = pro fill, -1 = outside the shape.


def _grid(rows):
    return np.array(rows, dtype=int)


def test_ring_of_satin_around_fill_core_reads_ring():
    g = _grid([[1, 1, 1, 1, 1],
               [1, 2, 2, 2, 1],
               [1, 2, 2, 2, 1],
               [1, 2, 2, 2, 1],
               [1, 1, 1, 1, 1]])
    assert classify_straddle(g) == "ring"


def test_side_by_side_partition_reads_split():
    g = _grid([[1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2],
               [1, 1, 2, 2, 2]])
    assert classify_straddle(g) == "split"


def test_checkerboard_reads_speckle():
    g = _grid([[1, 2, 1, 2],
               [2, 1, 2, 1],
               [1, 2, 1, 2],
               [2, 1, 2, 1]])
    assert classify_straddle(g) == "speckle"


def test_pure_shape_reads_pure():
    g = _grid([[2, 2], [2, 2]])
    assert classify_straddle(g) == "pure"


def test_outside_cells_are_ignored():
    g = _grid([[-1, 1, 1, -1],
               [1, 2, 2, 1],
               [-1, 1, 1, -1]])
    assert classify_straddle(g) == "ring"
```

- [ ] **Step 2: Run the test, verify it fails with `ModuleNotFoundError`/`ImportError`**

```powershell
cd digitizer
& .venv/Scripts/python -m pytest -q tests/test_splitprobe.py
```

- [ ] **Step 3: Implement `classify_straddle` + the probe shell in `splitprobe.py`**

```python
#!/usr/bin/env python
"""What KIND of satin/fill straddling caps the oracle at 76.6%?

48.1% of graded cells sit in shapes under 75% one pro type (attribution doc
§4). The dominant straddle PATTERN decides the fix: `ring` (pro satins a
border around a fill body) is solved by border-satin generation on our
existing regions; `split` needs region splitting at an artwork boundary;
`speckle` is cell-scale noise no region change can chase. Instrument, not
engine code — same join as gateprobe.py.

Usage: splitprobe.py [--csv out.csv] <prepped-design-dir>...
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

PURITY = 0.75           # attribution doc §4's own threshold; strictly-greater,
                        # so a shape at exactly 75% one type still counts as
                        # straddled (matches "under 75% one type" being the
                        # straddle population)
RING_SHARE = 0.8        # ring = border band dominated by one type AND interior
                        # dominated by a DIFFERENT type, each at ≥ this share.
                        # Both bands must be decisive: a side-by-side split also
                        # puts its minority partly on the border, but never
                        # dominates BOTH bands with different types.
SPLIT_COMPONENTS_MAX = 2  # a clean partition is 1-2 blobs per type, not many


def classify_straddle(grid: np.ndarray) -> str:
    """Classify one shape's pro-type cell grid.

    `grid`: int cells, -1 outside the shape, else scorecard type codes
    (0 run, 1 satin, 2 fill). Returns "pure" | "ring" | "split" | "speckle".
    """
    inside = grid >= 0
    vals, counts = np.unique(grid[inside], return_counts=True)
    if len(vals) == 0:
        return "pure"
    if counts.max() / counts.sum() > PURITY:
        return "pure"

    # Border band: inside cells with an outside/edge 4-neighbour.
    pad = np.pad(inside, 1, constant_values=False)
    interior = (pad[:-2, 1:-1] & pad[2:, 1:-1]
                & pad[1:-1, :-2] & pad[1:-1, 2:]) & inside
    border = inside & ~interior
    # Ring: the border band belongs to one type, the interior to another —
    # "pro satins the outline and fills the body". Judged on band dominance,
    # NOT on where the minority sits: the ring type can be the MAJORITY of
    # the whole shape (a 5x5 shape with a satin ring is 16 satin / 9 fill).
    if border.any() and interior.any():
        bvals, bcounts = np.unique(grid[border], return_counts=True)
        ivals, icounts = np.unique(grid[interior], return_counts=True)
        b_dom = bvals[np.argmax(bcounts)]
        i_dom = ivals[np.argmax(icounts)]
        if (b_dom != i_dom
                and bcounts.max() / bcounts.sum() >= RING_SHARE
                and icounts.max() / icounts.sum() >= RING_SHARE):
            return "ring"

    # Split: each present type forms few connected components.
    try:
        from scipy.ndimage import label
    except ImportError:
        return "speckle"  # scipy is in the digitizer venv; bare env degrades
    for v in vals:
        _, n = label((grid == v) & inside)
        if n > SPLIT_COMPONENTS_MAX:
            return "speckle"
    return "split"
```

The probe shell (same file, below the classifier) reuses gateprobe's join verbatim: `scorecard.load_side` both sides, `register`, `cell_stats`, then for each region in `ours_regions.json` build the shape's local grid from the pro type map over `_cells_of`-style centre-in-polygon cells (import `_cells_of` from `gateprobe`), classify, and emit per-shape rows `(design, shape_id, area_mm2, cells, purity, pattern)` plus a summary: cells and shapes per pattern, and the headroom each pattern accounts for (pattern's straddled-shape cells / total graded cells).

- [ ] **Step 4: Run the unit test, verify all 5 pass**

```powershell
& .venv/Scripts/python -m pytest -q tests/test_splitprobe.py
```

- [ ] **Step 5: Run the probe over the after-run corpus and write the findings doc**

```powershell
& $py tools/pro_parity/splitprobe.py --csv straddle.csv `
  (Get-ChildItem "<kappa-after>/parity_out/real" -Directory).FullName
```

`docs/segmentation-alignment-<date>.md`, attribution-doc structure: verdict up front (which pattern dominates, by cells), population/method (one paragraph, pointing at gateprobe's join), the distribution table, and the per-pattern headroom bound. Include the disconfirming check: if `speckle` dominates, say plainly that region-level work cannot recover this headroom and the spec below should NOT be built.

- [ ] **Step 6: Draft the spec, gated on the measured distribution**

`docs/superpowers/specs/<date>-segmentation-alignment-design.md`, header `**Status: DRAFT — awaiting Kent. Phase 3 territory; nothing here is scheduled.**` Contents: the measured pattern distribution; the proposed mechanism FOR THE DOMINANT PATTERN ONLY (ring → border-satin generation sized off the pro's measured band width distribution from the probe CSV; split → boundary detection restricted to artwork-visible edges, citing where the straddled shapes' boundaries sit in the artwork); acceptance criteria in corrected-kappa terms (Task 1's `kappacheck.py` is the instrument, per ROADMAP hard gate 4); and an explicit non-goal list (no engine change until Kent schedules it, no default flips, no synthetic fixtures per hard gate 2's spirit).

- [ ] **Step 7: Commit**

```powershell
git add digitizer/tools/pro_parity/splitprobe.py digitizer/tests/test_splitprobe.py docs/
git commit -m "measure: straddle-pattern probe — what kind of segmentation misalignment caps the oracle"
```

---

## Cleanup

- [ ] After Kent has seen the results: remove the two measurement worktrees (`git worktree remove .claude/worktrees/kappa-before` / `kappa-after`). NOT before — Tasks 2 and 5 read their run dirs, and the standing rule is never to delete under `.claude/worktrees/` without checking `git worktree list` first.

## Self-Review (done at planning time)

- **Spec coverage:** item 1 → Task 1; item 3 → Task 2; item 4 → Task 3 (shrunk: code already fixed by `619e9ad`, residue is docs); item 6 → Task 4; item 7 → Task 5. All five covered.
- **Placeholder scan:** `<day>`/`<date>` in file names are execution-date fills, resolved by the calendar, not by judgment. Task 4 steps 2/4 name their unknowns ("found in step 1") because step 1 is an investigation whose output feeds them — the procedure is concrete either way.
- **Type consistency:** `kappacheck.py` consumes exactly the keys `scorecard.py:863-867` writes (`parts.sttype`, `parts_raw.sttype`, `detail.chance_floor`); `splitprobe.py` consumes gateprobe's `_cells_of` and scorecard's `load_side`/`register`/`cell_stats`, all verified present at the cited lines; grid codes match `scorecard` cell type codes (0 run / 1 satin / 2 fill) via `gateprobe.TYPE_NAMES`.
