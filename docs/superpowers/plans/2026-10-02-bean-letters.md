# Bean Letters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Small traced lettering whose ink strokes are under a line sews as bean runs along the skeleton of the SOURCE INK, behind a config number that is OFF by default.

**Architecture:** `finish_generation` reads the ink once per text cluster (`ink_path.py`), decides per weight group, and writes the bean paths onto each member's `meta["bean_letter_spines"]`. Stage 7 only reads that key: one early branch in `stitch_one` hands the spines to `stage6_beanletter.bean_letter`, and `_sews_satin` answers False for the same shapes. Nothing in stages 0-5 moves.

**Tech Stack:** Python 3, numpy, OpenCV, scikit-image `skeletonize`, shapely; pytest. Studio: Svelte + vitest.

**Spec:** `docs/superpowers/specs/2026-10-02-bean-letters-design.md`

## Global Constraints

- `cfg.bean_letter_max_stroke_mm: float | None = None`. `None` is today's engine byte for byte. Intended flip value 1.0; the flip is Kent's, on stitch renders.
- No new physical constant except that line. Bean runs use `machine.BEAN_PASSES` and `machine.BEAN_STITCH_MM`.
- Bean-letter runs are `stitches.RUN`, never `SATIN`.
- The repo is PUBLIC: no new client artwork. Tests use synthetic rasters and the fixtures already committed.
- One heavy Python job at a time; `pytest -n 4`, never `-n auto`. Goldens re-pin on Linux only.
- No quality claim on a raw agreement number (ROADMAP gate 4).

## Deviation from the spec, stated

The spec groups a cluster's members into LINES of text. This plan groups them by STROKE WEIGHT instead (a two-means split of per-letter ink width, taken only when both groups hold at least three members and sit on opposite sides of the line). Reason: bridge's words run on an arc and Golke's word gaps equal its line gap, so a geometric line splitter has no clean rule; weight is the quantity the decision is about. Same outcome on the four measured logos. The spec is amended in Task 6.

## Review Focus

1. A white-background file (the spike never read ink there): the ground is the file's own white, read from pixels, not from the background mask. Test in Task 1.
2. A cutout whose letters sit on transparency: inkness is the foreground mask. Test in Task 1.
3. A member whose ink skeleton is empty or shorter than the run floor: it must fall through to today's ladder, never sew nothing. Test in Task 3.
4. A review-screen `tier` set by the user on a bean letter: the user's tier wins. Test in Task 3.
5. Two letters fused in one region: ink is assigned to the nearest member, so a neighbour's stroke is not sewn twice. Test in Task 1.

---

### Task 1: `ink_path.py` — inkness, per-member width and skeleton paths

**Files:** Create `digitizer/digitizer_core/ink_path.py`; Test `digitizer/tests/test_ink_path.py`.

**Interfaces — Produces:**
- `read_cluster_ink(p: Prep, members: list[Region]) -> list[MemberInk]`, one per member, same order.
- `@dataclass MemberInk: stroke_mm: float | None; spines: list[list[tuple[float, float]]]` — spines in design mm (stage 4's frame, `legibility._plan_frame`).
- Constants `INK_UPSCALE = 3`, `INK_THRESHOLD = 0.55`, `INK_REACH_MM = 0.35`, `INK_GROUND_CLEAR_MM = 0.8`, `INK_MIN_BRANCH_MM = 0.6`.

Steps: failing tests first (`_letter_e` drawn at 3.5 px/mm with a 0.5 mm counter keeps three arms; white-background and cutout variants read the same width within 0.15 mm; two touching bars give each member one spine), run to see `ModuleNotFoundError`, implement, run green, commit.

### Task 2: `stage6_beanletter.py` — spines to bean runs

**Files:** Create `digitizer/digitizer_core/stage6_beanletter.py`; Test `digitizer/tests/test_bean_letter.py`.

**Interfaces — Consumes** `MemberInk.spines`. **Produces**
`bean_letter(spines, shape_id, *, entry, trim_at_mm) -> tuple[list[StitchRun], dict]`; report keys `loops, jumps, empty, too_thin, arcs, yielded, strokes` (run_outline's contract plus `strokes`).

Tests: only `stitches.RUN`; an L of two spines meeting at a corner sews with no trim; entry nearest the needle; a spine under `RUN_MIN_LOOP_MM / 2` is skipped and an all-short input reports `empty`.

### Task 3: decision, config, tagging and dispatch

**Files:** Modify `config.py` (field after `satin_lettering_split`), `pipeline.py` (`finish_generation`, after `apply_stitch_widths`), `stage7_sequence.py` (`_sews_satin`, `stitch_one`, the counters, the warning), `warnings_codes.py` (`SMALL_LETTERING_AS_BEAN`); Create `digitizer/digitizer_core/beanletters.py` (`tag_bean_letters(regions, p, cfg) -> int`, `weight_groups(widths, line_mm)`); Test `digitizer/tests/test_bean_letters_pipeline.py`.

Tests: default is `None` and tags nothing; `weight_groups` both sides of the line and the three-member rule; bridge at 1.0 tags its clustered teal members, they sew as `RUN`, `LETTERING_TOO_SMALL` does not name them, `SMALL_LETTERING_AS_BEAN` carries the count; a member with `tier: "satin"` stays satin; OFF plan equals the plan with the field absent (stitch-for-stitch).

### Task 4: Studio — the quiet note

**Files:** Modify `app/src/lib/digitizer.js` (`WARNING_TEXT`), `app/src/lib/digitizer.spec.js` (tripwire list, and a test that the code is not in `ATTENTION_WARNINGS`).

### Task 5: instrument — `tools/bean_letters.py`

Renders the four logos OFF beside ON as stitches (`stitchviz.render_jpeg_bytes` over the plan's design dict, as `tools/legibility.py` does) and prints per-logo stitches, trims and the legibility score. Writes to a directory argument.

### Task 6: records

Amend the spec's "Design" to weight groups; add the MASTER_SCOPE area-2 line and the scope-history entry with the Task 5 numbers; open the PR ready for review with auto-merge armed.
