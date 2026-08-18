# Shape-Fidelity Knockout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the buildable parts of the three shape-fidelity gaps measured 2026-08-17 (Kent's circled defects on a digitized Instagram icon, reproduced with a controlled gradient-vs-flat twin-glyph experiment): (1) RDP curve coarseness, (4) topology-blind small-shape cleanup, and (2) the stage-0 flat-logo misroute — the last by routing it to its real blocker instead of pretending it is code-shaped.

**Origin evidence (this session, 2026-08-17):** No primitive-shape detection exists anywhere in the pipeline (repo-wide grep: zero Hough/fitEllipse/spline hits) — a circle is a pixel blob, contour-traced then RDP'd. Measured through the real `findContours → approxPolyDP` path at `simplify_tol_mm = 0.2` (`config.py:343`): a 20 mm circle becomes a 20-gon, a 40 mm circle gets 3.9 mm chords. Both a gradient-filled and a **flat single-colour** copy of the same glyph classified `CLASSIFIED_GRADIENT` and took the photo lane. Config override (`forced_class=flat`, `simplify_tol_mm=0.05`) produced visibly smoother curves at unchanged stitch count (3601 vs 3661) on the synthetic glyph — a lever demo, not corpus evidence.

**Architecture:** Instrument-first, per ROADMAP Phase 1 (Foundation — "a yardstick that agrees with Kent's eyes"). No engine default changes without local-corpus measurement, and none land without their golden story resolved in CI. Tasks 1–2 build and use a missing instrument; Task 3 is reproduce-or-close; Task 4 is a disposition document, not code.

**Scope rulings (Kent, this session):**
- Gap 3 (gradient banding) **stays tabled** — reaffirms the 2026-08-16 tabling (`docs/scope-digest/photo-classifier.md:71`, ROADMAP Phase 4). Not in this plan.
- Gap 2 threshold/signal recalibration is **blocked on input, not effort** (`docs/scope-digest/measurement.md:139-140`): the 2026-08-15 stage-0 spec rejected four approaches and left the replacement signal needing 4–5 real customer artworks with genuine tonal content. ROADMAP hard gate 2 bars synthetic substitutes. Task 4 records the blocker and proposes the one mitigation that needs no recalibration.

## Global Constraints

- **Public repo.** No new client artwork, customer names, or third-party stitch files. Slugs already committed are fine.
- **Branch:** everything here commits to `claude/shape-fidelity` (worktree `.claude/worktrees/shape-fidelity`, cut from `origin/main` `73f37da`). Only Kent merges.
- **Worktrees have no `.venv`.** Invoke the primary checkout's interpreter — `C:/Users/EE-LT-11030/Personal/EMB-Bot/digitizer/.venv/Scripts/python.exe` — with cwd inside the worktree's `digitizer/`, and verify `digitizer_core.__file__` resolves into the worktree before trusting any number.
- **Measure in a pinned worktree** (three baselines died mid-run on 2026-08-15 — `docs/scope-digest/measurement.md:123-125`). One `PRO_PARITY_OUT` per measurement arm; parallel runs corrupt without it (`measurement.md:112`).
- **Corpus root:** `PRO_PARITY_ROOT` defaults to `G:/My Drive/EMB-Bot/Embroidery Files` (`prep_both.py:40`); `PRO_PARITY_OUT` is required (KeyError if unset). Drive via `prep_both.py`, not `prep_all.py` (its defaults are dead sandbox paths; its DESIGNS list still carries the macOS colon form — `prep_both.py`'s underscore list is the one to use).
- **ROADMAP hard gate 4:** no quality claim on a raw agreement number, anywhere, in any doc this plan touches.
- **Goldens re-capture on Linux CI, never Windows** (ROADMAP standing item). Any default change that churns goldens lands with its CI recapture, or does not land.
- **Never pipe pytest (or any run) to `tail`.**
- The scorecard's `coverage` is agreement with the **pro's stitches**, chance-corrected since 2026-08-14. It contains **no outline-fidelity component** (`scorecard.py:103-104` WEIGHTS: coverage/direction/sttype/density/underlay/travel). Do not cite scorecard movement as curve-fidelity evidence in either direction.
- If quoting misroute counts: MASTER_SCOPE says "six of the seven logos", the handoff says "10 of 15" — `measurement.md:162-163` says reconcile before quoting either. Prefer citing the invariance test's own fixture set.

---

### Task 1: Engine-side art-fidelity instrument (`digitizer/tools/pro_parity/enginefidelity.py`)

The measurement gap is explicit in the digests: whole-design IoU barely moves for visible defects, `gaulke_roofing_lc` scores 79.8 as an illegible smear, and the open need is "coverage measured against the artwork, not the pro's stitches" (`docs/scope-digest/measurement.md:8-12,37-38`). `artfidelity.py` already does art-vs-**pro** (best-shift IoU, `pro_extra`, `art_missed`; cv2/numpy/PIL only, no engine import, 10 px/mm, 0.40 mm thread, ±4 mm shift search). This task builds its engine-side twin so curve-fidelity changes have a number.

**Files:**
- New: `digitizer/tools/pro_parity/enginefidelity.py`
- New: `digitizer/tests/test_enginefidelity.py` (metric core only — pure functions on arrays, no corpus dependency)

**Steps:**
- [ ] TDD the metric core: rasterize engine stitches (same 10 px/mm, 0.40 mm thread constants as `artfidelity.py`) and compute, per design: `art_iou` (best-shift), `engine_extra` (engine cover the art doesn't ask for), `art_missed` (art ink the engine left unsewn), and **boundary Hausdorff / mean-contour-distance in mm** between the art mask outline and the engine cover outline — the number RDP coarseness actually moves. Failing tests first, on synthetic masks with hand-computable answers (offset squares, ring vs 20-gon ring).
- [ ] CLI mirroring `artfidelity.py`: consume `<OUT>/real/<slug>/` dirs (engine stitches CSV + `art.png` as `prep_both.py` lays them out — confirm exact engine-side filename from `prep_all.py` before coding, do not guess).
- [ ] Reuse `artfidelity.py`'s shift-search; inherit its known limit (shift pins at boundary on re-composed layouts — Gaulke reads low by construction). Document it in the module docstring.
- [ ] Run on ≥10 designs from the local corpus; run twice; numbers identical (the `selfconsistency.py` precedent). Commit instrument + tests + a five-line usage note in the module docstring.

**Acceptance:** metric tests green; two identical corpus runs; no engine code touched.

### Task 2: Curve-fidelity ladder — measure, then let Kent pick the lever

**Blocked by Task 1.** Three arms on the local corpus, one pinned worktree, one `PRO_PARITY_OUT` per arm: `simplify_tol_mm ∈ {0.2 (baseline), 0.1, 0.05}` via the service/pipeline config override (client-settable, no code change).

Prior art that bounds the design space (`docs/scope-digest/scope-areas.md:53-54`, `competitors.md:58`): size-proportional tolerance is investigated and CLOSED (Ember's floor is coarser than our default; both call sites already realize constant-mm deviation by construction — that is deliberate). Wholesale Catmull-Rom smoothing was rejected for corner overshoot. So the candidate levers are: (a) lower the constant default, (b) leave the default and have the Studio send a tighter value for logo-class requests, (c) post-RDP arc-aware refinement that preserves corners — (c) is new code and only on the table if the ladder shows the constant alone can't get there.

**Steps:**
- [ ] Verify module resolution (worktree `digitizer_core`), then run the three arms. Capture per-design: `enginefidelity` metrics, stitch count, trims, `size_mm`, wall time.
- [ ] Findings doc `docs/curve-fidelity-ladder-2026-08-17.md`: per-arm deltas, mm-boundary-distance improvement vs stitch-count/trim cost, and the golden-churn blast radius of a default change (which goldens move, judged in CI only). No raw-agreement numbers.
- [ ] Present Kent the decision: change default (+ CI golden recapture) / Studio-sent override / pursue (c). **Stop here — do not implement the chosen lever inside this task.**

**Acceptance:** findings doc committed with all three arms' numbers; decision presented; no default changed.

### Task 3: Gap 4 — reproduce-or-close, plus pin the dot-fusion defect

The digests show the absorb path is already guarded (enclosed-mask protection from the "A"-counter case, `stage3_segment.py:102-139`; `small_shape_rescue`; the 2,787 mm² silent drop was a fixed `make_valid` bug). The claim "absorb turns quantize-fragmented rings lumpy" is currently **theory**. And Kent's third circled defect — the dot fusing into the frame corner — survived every lane and tolerance, mechanism unpinned.

**Steps:**
- [ ] Pin the dot fusion first (cheap): from the existing `job-insta_flat_tuned.json` in this session's scratchpad (regenerate via service if absent — synthetic glyph, committable), determine whether dot+frame arrive as ONE region (merged upstream in quantize/segment — real defect, find the merge) or TWO shapes joined by same-thread travel (by-design link; `LINK_COVER_TOL_MM` is sew-out-gated — hard gate 1 — so do not touch the constant; if the link is the defect, the fix conversation is about sequencing/trim policy, separately).
- [ ] Attempt the ring repro through the real stage2→stage3 path: adversarial px/mm and colour placement so quantization fragments a ring into sub-2.25 mm² arc slivers with a non-ring neighbour sharing the halo. Use `whichshape.py` to interrogate ownership.
- [ ] If reproduced: failing test in `digitizer/tests/`, then the minimal guarded fix (absorb target choice should prefer a same-parent-shape neighbour before a foreign one), constants untouched — all floors stay derived from `cfg.min_detail_mm` (`docs/scope-digest/plans-engine.md:17`).
- [ ] If not reproducible: close it honestly — a short note in the findings doc withdrawing the claim, citing the guards that prevent it. A withdrawn defect is a result.

**Acceptance:** dot-fusion mechanism named with evidence; ring claim either has a failing-then-passing test or a written withdrawal.

### Task 4: Gap 2 disposition — write the blocker down, propose the no-recalibration mitigation

No threshold or signal code in this task. The 2026-08-15 spec is the authority: four approaches rejected (§5, `photo-classifier.md:23-26`), replacement signal (3-bit colour count, invariant across a 14× sweep) blocked on 4–5 real tonal artworks; the landed `test_classifier_scale_invariance.py` (6 passed / 7 xfailed strict) is the acceptance instrument; recalibrate on real art, validate on fixtures — never the inversion.

**Steps:**
- [ ] Add the disposition to the findings doc: gap 2's fix path exists, is designed, and waits on artwork — "getting more real customer artwork is the highest-leverage non-code action" (`conventions-memory.md:85`). Nothing in this plan advances it by code.
- [ ] Propose (not build) the mitigation that needs no recalibration: a Studio-side **"this is flat art" override** feeding `forced_class=flat` — user-supplied ground truth, not a stage-0 change, so hard gate 2 is not implicated. Measured upside on the misrouted set: +4.85 mean, 8 better / 1 worse / 1 unchanged (`photo-classifier.md:11`). Required caution in the same note: forcing flat on **textured** logo art makes it worse (k-means shatters texture — `scope-history.md:30`), so the control's copy must scope it to flat-colour art, and `hotel_fremont_hat` (−4.3, labelled flat, unexplained) goes in as the open counterexample. This is a PRODUCT.md scope call — Kent decides, separately from this plan.

**Acceptance:** disposition + mitigation proposal committed in the findings doc; no engine code changed; decision explicitly left with Kent.

---

## Execution notes

- Task order: 1 → 2 → 3 → 4; 3 can interleave after 1 if the ladder runs long (arms are ~13 designs × 3 configs of engine time).
- Python baseline for this worktree was captured before any edit (known-failure set per COOKBOOK "Running things"); judge regressions against that set, not against zero.
- The primary checkout is serving Kent's live dev servers — engine edits happen in this worktree only.
