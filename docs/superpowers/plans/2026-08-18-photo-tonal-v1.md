# Photo/Tonal v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A real photograph uploaded through Studio's "This is a photo" toggle renders with tone — shade-split regions, multi-color tier emission, streamline portraits — instead of N flat posterized patches.

**Architecture:** Fix the color-out wall in stage 7 (read the per-shade thread snap), un-table `split_tonal_regions` for the photo classes, give the photo classes an automatic tier route in `pipeline.py` (today `source_pixels` is `None` for them, so every tonal tier is unreachable), and put one forced-class toggle in Studio. SAM2 gets rebuilt and honestly detected but stays off pending an eyeball A/B.

**Tech Stack:** Python (digitizer_core, pytest via `.venv/Scripts/python -m pytest` — run from `digitizer/`, the working-directory note in digitizer/README.md is binding), Svelte + vitest (app/), no new dependencies.

**Spec:** `docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md`

## Global Constraints

- Flat lane stays byte-for-byte identical — the repo's `flat_lane_byte_identical` test must pass untouched after every task.
- No physical constants change (fill spacing, satin width floors, lock/tie lengths) — ROADMAP hard gate 1.
- Engine tests: `cd digitizer && .venv/Scripts/python -m pytest -q` (offline, ~127+ tests). Studio tests: `cd app && npm test`.
- Every task lands as its own commit on the branch `claude/photo-tonal-v1` (worktree `.claude/worktrees/photo-tonal-v1`); one PR at the end unless a task note says otherwise.
- The acceptance directory `digitizer/testdata/photo/acceptance/` is never committed (Task 0 gitignores it).
- Doc edits follow MASTER_SCOPE.md's own rule: every status claim carries a `(verb date — source)` pointer.

---

### Task 0: Governance and doc truth-up

The decision record must land before code so any parallel session reads the
un-tabling instead of refusing phase-4 work.

**Files:**
- Modify: `ROADMAP.md` (the "## Where we are" section)
- Modify: `MASTER_SCOPE.md` (three stale claims)
- Modify: `.gitignore` (repo root)
- Add (already written, commit them): `docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md`, `docs/superpowers/plans/2026-08-18-photo-tonal-v1.md`

**Interfaces:**
- Produces: the branch + worktree every later task builds on.

- [ ] **Step 1: Create the worktree and branch**

```bash
cd "<repo-root>"
git worktree add .claude/worktrees/photo-tonal-v1 -b claude/photo-tonal-v1
```

- [ ] **Step 2: Edit ROADMAP.md "Where we are"**

Replace the line `**Phase 1 — Foundation.**` with:

```markdown
**Phase 1 — Foundation.** In parallel: **Phase 4 — Finish (tonal)**, un-tabled
by Kent 2026-08-18 (decision record:
`docs/superpowers/plans/2026-08-18-photo-tonal-v1-spec.md`). Phases 2–3 remain
open; phase-4 v1 works around stage 0 with an explicit user override, not by
advancing them.
```

Also change phase 4's line `Tabled by Kent.` to `Un-tabled by Kent 2026-08-18 — v1 in progress.`
Respect the file's own rule: no numbers, no dates elsewhere, 60-line budget — trim if the edit busts it.

- [ ] **Step 3: Fix three stale MASTER_SCOPE.md claims**

1. The gotcha that says "13 photo-plan rows" → 16 rows (0–15), pointer:
   `(confirmed 2026-08-18 — docs/scope/1-auto-digitizing-quality.md:1506 and photo plan §2)`.
2. Wherever the photo segmenter is described as "SLIC+RAG", append
   `(SEEDS since 2026-08-07 — stage2_photo_segment.py:11-27; internal names still slic_*)`.
3. Any claim that the owl photo "is not on disk" → note `owl_kent.jpg` is
   committed (PR #126). Also fix the same staleness in
   `docs/sam2-ship-path-brief-2026-08-11.md:110` and
   `docs/scope-digest/photo-classifier.md:49`.

- [ ] **Step 4: Gitignore the acceptance dir**

Append to the repo-root `.gitignore`:

```gitignore
# Local-only acceptance photos (public repo — never publish; spec decision 6)
digitizer/testdata/photo/acceptance/
```

- [ ] **Step 5: Commit**

```bash
git add ROADMAP.md MASTER_SCOPE.md .gitignore docs/superpowers/plans/2026-08-18-photo-tonal-v1*.md docs/sam2-ship-path-brief-2026-08-11.md docs/scope-digest/photo-classifier.md
git commit -m "docs: un-table phase 4 (photo/tonal v1) — decision record, roadmap marker, scope truth-up"
```

---

### Task 1: Stage 7 reads the per-shade thread snap

The color-out wall. `stage6_blend.blend_fill` computes `shade_thread_idx`
(`stage6_blend.py:586`) and per-shade `layer_runs`, then stage 7 sews every
run of the region in `group[0].region.thread_index` — one thread
(`stage7_sequence.py` block assembly near line 1357). After this task, a
region whose runs carry a shade thread sews one StitchBlock **per shade
thread**, ordered dark→light within the region's slot in the existing
sequence (depth order between regions is untouched).

**Files:**
- Modify: `digitizer/digitizer_core/stage6_blend.py` (attach `shade_thread_idx` to the runs it returns)
- Modify: `digitizer/digitizer_core/stage7_sequence.py` (block assembly: group runs by shade thread)
- Test: `digitizer/tests/test_shade_thread_emission.py` (new)

**Interfaces:**
- Consumes: `blend_fill(...)` existing return (layer runs), `StitchBlock(thread_index=..., ...)` as built in stage 7 today.
- Produces: runs may carry `shade_thread_index: int | None = None` (attribute on the run object; `None` = legacy behavior, region thread). Stage 7 contract: within one region's emission, runs are partitioned by `shade_thread_index or region.thread_index` into consecutive StitchBlocks, dark→light by the chart's L*. Task 3's streamline layering relies on exactly this field name.

- [ ] **Step 1: Read the two sites first**

Read `digitizer/digitizer_core/stage6_blend.py:540-710` (where
`shade_thread_idx`/`layer_runs` exist and are dropped) and
`digitizer/digitizer_core/stage7_sequence.py:900-1140` plus `:1300-1380`
(tier dispatch and block assembly) before writing the test — the exact run
type and grouping loop live there, and the test must construct/assert against
the real shapes, not invented ones.

- [ ] **Step 2: Write the failing test**

Job-level, against the real pipeline on the committed ramp fixture — this is
the defect's own repro (4 shades accepted at r²=1.0, sews 2 blocks / 1 color
change today):

```python
# digitizer/tests/test_shade_thread_emission.py
"""A gradient region whose blend tier accepts N shades must sew N color
blocks, not one. Repro of MASTER_SCOPE's 'every shade sews in one thread'
defect: gradient_ramp_linear.png accepts 4 shades and sewed 2 blocks."""
from pathlib import Path
from digitizer_core.pipeline import run_stages
from digitizer_core.config import PipelineConfig

FIXTURE = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "gradient_ramp_linear.png"

def test_accepted_shades_become_color_blocks():
    cfg = PipelineConfig()  # defaults: gradient class routes to blend tier
    result = run_stages(FIXTURE.read_bytes(), cfg)
    # The ramp's blend decomposition accepts 4 shades (measured 2026-08-15,
    # docs/blend-tier-never-fires-2026-08-15.md). Distinct thread indexes
    # across the design's stitch blocks must reflect them.
    distinct = {b.thread_index for b in result.design.blocks}
    assert len(distinct) >= 3, (
        f"4-shade ramp sewed {len(distinct)} thread(s) — shade snap not read")
```

Adjust the import/call shape to whatever `run_stages` actually takes (Step 1
read tells you); the assertion — ≥3 distinct threads on this fixture — is the
contract. If `run_stages` needs bytes+name or a path, match `conftest.py`
fixtures' established call style.

- [ ] **Step 3: Run it, verify it fails on the count**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_shade_thread_emission.py -q
```
Expected: FAIL with 1 or 2 distinct threads, NOT an import/attribute error.

- [ ] **Step 4: Implement**

In `stage6_blend.py`: where layer runs are built per shade (the loop that owns
`shade_thread_idx[i]`), stamp each run: `run.shade_thread_index = shade_thread_idx[i]`
(add the field to the run dataclass with default `None` if it is a dataclass;
if runs are a shared type from another module, add the optional field there).

In `stage7_sequence.py` block assembly: where the code currently does
`thread = chart_for(cfg)[group[0].region.thread_index]` and appends one
`StitchBlock`, partition `ordered` by
`getattr(run, "shade_thread_index", None) or group[0].region.thread_index`,
sort the partitions dark→light by chart L*, and append one StitchBlock per
partition, preserving run order inside each. Runs with `None` (every
non-blend tier today) collapse to the single legacy block — byte-identical
for them by construction.

- [ ] **Step 5: Run the new test + the full engine suite**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_shade_thread_emission.py -q && .venv/Scripts/python -m pytest -q
```
Expected: new test PASS; suite green **including `flat_lane_byte_identical`**.
If any snapshot/parity test asserts exact block counts on gradient fixtures,
read its docstring before touching it — update only counts that the defect
itself pinned, and say so in the commit message.

- [ ] **Step 6: Commit**

```bash
git add digitizer/digitizer_core/stage6_blend.py digitizer/digitizer_core/stage7_sequence.py digitizer/tests/test_shade_thread_emission.py
git commit -m "fix(engine): stage 7 sews blend shades in their snapped threads"
```

---

### Task 2: Un-table split_tonal_regions for the photo classes

`config.py:649` has `split_tonal_regions: bool = False`, gates
`TONAL_SPLIT_MIN_AREA_MM2=150.0` / `TONAL_SPLIT_MIN_DELTAE=18.0`, implemented
in `stage2_photo_segment.py:1267`. Kent's ruling: default ON for
`photo_subject`/`photo_scene` only. `gradient` keeps the blend tier;
`flat` never sees stage2_photo_segment at all.

**Files:**
- Modify: `digitizer/digitizer_core/pipeline.py` (resolve the effective flag per class where stage2_photo_segment is invoked, `pipeline.py:303-308`)
- Modify: `digitizer/digitizer_core/config.py` (docstring only: record the per-class default)
- Test: `digitizer/tests/test_split_tonal_default.py` (new)

**Interfaces:**
- Consumes: `classification.class_` (stage 0 verdict, or Task 4's forced class), `cfg.split_tonal_regions`.
- Produces: rule `effective_split = cfg.split_tonal_regions or classification.class_ in ("photo_subject", "photo_scene")`. The config field stays the explicit override for gradient/experiments; `False` + photo class still splits.

- [ ] **Step 1: Write the failing test**

```python
# digitizer/tests/test_split_tonal_default.py
"""Spec decision 2 (2026-08-18): photo classes split tonal regions by
default; gradient and flat do not. The flag stays an explicit opt-in for
non-photo classes."""
from digitizer_core.pipeline import effective_split_tonal
from digitizer_core.config import PipelineConfig

def test_photo_classes_split_by_default():
    cfg = PipelineConfig()
    assert effective_split_tonal(cfg, "photo_subject") is True
    assert effective_split_tonal(cfg, "photo_scene") is True

def test_gradient_and_flat_do_not_split_by_default():
    cfg = PipelineConfig()
    assert effective_split_tonal(cfg, "gradient") is False
    assert effective_split_tonal(cfg, "flat") is False

def test_explicit_flag_still_wins_everywhere():
    cfg = PipelineConfig(split_tonal_regions=True)
    assert effective_split_tonal(cfg, "gradient") is True
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_split_tonal_default.py -q
```
Expected: FAIL — `effective_split_tonal` does not exist.

- [ ] **Step 3: Implement**

In `pipeline.py`, next to the stage-2 dispatch:

```python
def effective_split_tonal(cfg, class_: str) -> bool:
    """Spec 2026-08-18 decision 2: photo classes carry tone via upstream
    splitting by default; the config flag remains the explicit override for
    every other class (gradient keeps the blend tier as its tonal carrier)."""
    return bool(cfg.split_tonal_regions) or class_ in ("photo_subject", "photo_scene")
```

and pass `effective_split_tonal(cfg, classification.class_)` into
`stage2_photo_segment` where `cfg.split_tonal_regions` is read today (thread
the boolean as an argument — do not mutate `cfg`, jobs cache on it).

- [ ] **Step 4: Run new test + suite**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_split_tonal_default.py -q && .venv/Scripts/python -m pytest -q
```
Expected: all green; the existing split_tonal tests (find them with
`grep -rn "split_tonal" tests/`) keep passing — they set the flag explicitly.

- [ ] **Step 5: Commit**

```bash
git add digitizer/digitizer_core/pipeline.py digitizer/digitizer_core/config.py digitizer/tests/test_split_tonal_default.py
git commit -m "feat(engine): photo classes split tonal regions by default (spec decision 2)"
```

---

### Task 3: Automatic tier route for the photo classes

Today `pipeline.py:456-485` builds `source_pixels` only for `gradient` or an
explicit caller opt-in — the comment says "automatic photo routing is a later
slice". This is that slice. Ruling (spec decision 3): `photo_subject` →
`fill_technique="streamline"` + `detail_layer=True` when faces were detected;
`photo_scene` → tatami with split regions (Task 2 already provides tone).
Explicit caller config always wins.

**Files:**
- Modify: `digitizer/digitizer_core/pipeline.py:456-490`
- Modify: `digitizer/digitizer_core/warnings_codes.py` (one new code)
- Test: `digitizer/tests/test_photo_auto_route.py` (new)

**Interfaces:**
- Consumes: `classification.class_`, `cfg.fill_technique` (None/"tatami" = unset), `cfg.detail_layer`, face results from stage 1.5 (`detect_faces_seam` — read `pipeline.py:169-252` for the variable that holds them), `SourcePixels`, Task 1's shade-block emission (streamline's dark→light layers sew in their own threads through it).
- Produces: warning code `PHOTO_AUTO_TIER = "photo_auto_tier"` emitted with the chosen tier so the Studio panel can say what happened; the routing function `auto_photo_tier(cfg, class_, faces_present) -> str | None` returning the effective fill_technique (`None` = leave untouched).

- [ ] **Step 1: Write the failing test**

```python
# digitizer/tests/test_photo_auto_route.py
"""Spec decision 3 (2026-08-18): the automatic tier map for photo classes.
photo_subject -> streamline (+ detail layer with faces); photo_scene ->
tatami+split; explicit caller choice always wins."""
from digitizer_core.pipeline import auto_photo_tier
from digitizer_core.config import PipelineConfig

def test_photo_subject_defaults_to_streamline():
    assert auto_photo_tier(PipelineConfig(), "photo_subject", faces_present=False) == "streamline"

def test_photo_scene_defaults_to_tatami():
    # None = leave fill_technique alone; scene tone comes from split regions.
    assert auto_photo_tier(PipelineConfig(), "photo_scene", faces_present=False) is None

def test_explicit_caller_choice_wins():
    cfg = PipelineConfig(fill_technique="meander_tonal")
    assert auto_photo_tier(cfg, "photo_subject", faces_present=False) is None

def test_gradient_and_flat_untouched():
    assert auto_photo_tier(PipelineConfig(), "gradient", faces_present=False) is None
    assert auto_photo_tier(PipelineConfig(), "flat", faces_present=False) is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_photo_auto_route.py -q
```
Expected: FAIL — `auto_photo_tier` not defined.

- [ ] **Step 3: Implement**

```python
def auto_photo_tier(cfg, class_: str, faces_present: bool) -> str | None:
    """Spec 2026-08-18 decision 3 — the automatic photo tier map. Returns the
    fill_technique to apply, or None to leave the caller's config untouched.
    Only fires when the caller did NOT choose a technique themselves."""
    explicit = (cfg.fill_technique or "tatami").lower() != "tatami" or cfg.detail_layer
    if explicit or class_ != "photo_subject":
        return None
    return "streamline"
```

Wire it in the `source_pixels` gate block (`pipeline.py:456-485`): when it
returns `"streamline"`, treat the design as if the caller had set
`fill_technique="streamline"` (thread an effective-technique local through the
same `want_tonal` logic — again, do not mutate `cfg`), set `detail_layer`
effective-on when `faces_present`, extend the `source_pixels` construction to
photo classes, and append `PHOTO_AUTO_TIER` with the tier name to the job
warnings. `photo_scene` needs `source_pixels` only if the blend tier is to see
scene ramps — leave scenes off `want_tonal` for v1 (tone arrives via Task 2's
splitting), which keeps their cost flat.

- [ ] **Step 4: Run new test + suite + one live smoke**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_photo_auto_route.py -q && .venv/Scripts/python -m pytest -q
```
Then live (service running):

```bash
cd digitizer && .venv/Scripts/python -c "import json,urllib.request; print('service reachable')"
```
POST `testdata/photo/owl_kent.jpg` with `{"forced_class":"photo_subject"}`
(reuse the probe script pattern from
`debug_out/probe_photo_20260818/`'s `_index.json` runs) and confirm the
response warnings include `photo_auto_tier: streamline` and stitch blocks
carry >1 distinct thread. Save the response JSON to `debug_out/` for the PR.

- [ ] **Step 5: Commit**

```bash
git add digitizer/digitizer_core/pipeline.py digitizer/digitizer_core/warnings_codes.py digitizer/tests/test_photo_auto_route.py
git commit -m "feat(engine): automatic tier route for photo classes (streamline portraits)"
```

---

### Task 4: Studio "This is a photo" toggle

Lane entry v1 (spec decision 4): a checkbox on the digitized element's panel
that sends `forced_class: "photo_subject"` in the digitize config — the exact
field the 2026-08-18 probe used successfully. No classifier work.

**Files:**
- Modify: `app/src/lib/digitizer.js` (config builder: include `forced_class` when the element sets it — find the function that assembles the `/digitize` config from `DEFAULT_DIGITIZE_PARAMS`, near the `startDigitize` plumbing at `digitizer.js:959-1005`)
- Modify: `app/src/lib/project.js` (`defaultDigitizedElement`: add `isPhoto: false`)
- Modify: `app/src/ui/DigitizePanel.svelte` (the checkbox, next to the existing params; re-digitize on change follows the panel's existing param-change convention — read `DigitizePanel.svelte:130-230` first)
- Test: `app/src/lib/digitizer.spec.js` (extend — it already stubs the wire with injected fetch)

**Interfaces:**
- Consumes: Task 3's `PHOTO_AUTO_TIER` warning (the panel's existing warning translation table in `digitizer.js` gets one entry: `photo_auto_tier` → "Rendered as a photo (thread-paint)."), the service's `forced_class` config field.
- Produces: element field `isPhoto: boolean` (persisted like every other digitize param); config field `forced_class: "photo_subject"` present iff `isPhoto`.

- [ ] **Step 1: Write the failing vitest**

```js
// append to app/src/lib/digitizer.spec.js
import { describe, it, expect } from "vitest";

describe("isPhoto forced class (spec 2026-08-18 decision 4)", () => {
  it("includes forced_class photo_subject when the element is marked as a photo", async () => {
    const { buildDigitizeConfig } = await import("./digitizer.js");
    const el = { isPhoto: true };
    expect(buildDigitizeConfig(el).forced_class).toBe("photo_subject");
  });
  it("omits forced_class entirely when not marked", async () => {
    const { buildDigitizeConfig } = await import("./digitizer.js");
    expect("forced_class" in buildDigitizeConfig({ isPhoto: false })).toBe(false);
  });
});
```

`buildDigitizeConfig` is the name IF no config-assembly function exists yet —
first grep `digitizer.js` for where `startDigitize`'s `config` argument is
built (likely in `DigitizePanel.svelte`'s `runDigitize`); if assembly lives in
the panel, extract it into `digitizer.js` as `buildDigitizeConfig(el)` so it
is testable, and have the panel call it. The spec asserts the extracted
function; adjust the element-shape argument to match what the panel actually
passes.

- [ ] **Step 2: Run to verify failure**

```bash
cd app && npx vitest run src/lib/digitizer.spec.js
```
Expected: the two new tests FAIL (function or field missing); the existing
digitizer.spec tests stay green.

- [ ] **Step 3: Implement**

- `project.js` `defaultDigitizedElement`: add `isPhoto: false` alongside the
  other digitize params so it persists and survives reload.
- `digitizer.js`: `buildDigitizeConfig(el)` spreads the existing params and
  adds `forced_class: "photo_subject"` only when `el.isPhoto`; add the
  warning-translation entry for `photo_auto_tier`.
- `DigitizePanel.svelte`: checkbox labeled **"This is a photo"** with helper
  text "Renders with thread-paint shading instead of flat color regions.",
  bound to the element's `isPhoto` via the panel's existing `elupdate` patch
  convention; changing it re-digitizes exactly like the other param controls
  (mirror how `nColors`/`fill angle` changes trigger `runDigitize` at
  `DigitizePanel.svelte:172-220`).

- [ ] **Step 4: Run Studio suite**

```bash
cd app && npm test
```
Expected: green. Then live smoke in the browser: toggle on a digitized
element with the service up → network shows `/digitize` with
`forced_class`, panel shows the auto-tier warning text.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/digitizer.js app/src/lib/digitizer.spec.js app/src/lib/project.js app/src/ui/DigitizePanel.svelte
git commit -m "feat(studio): 'This is a photo' toggle forces photo_subject (spec decision 4)"
```

---

### Task 5: SAM2 — honest detection, sane timeout, rebuilt venv

The availability check (`sam2_segmentation_unavailable_reason()`) only tests
that `python.exe` exists, so the current husk venv (1.2 MB, no `Lib/`, no
`pyvenv.cfg`) reads as available and every attempt dies at runtime with
"worker exited 106". Timeout is 90 s against a measured 156 s cold start.
Default stays OFF (spec decision 5).

**Files:**
- Modify: `digitizer/digitizer_core/stage2_sam2_segment.py` (or wherever `sam2_segmentation_unavailable_reason` lives — grep for it)
- Modify: `digitizer/digitizer_core/config.py:267` (`photo_segment_sam2_timeout_s`: 90 → 240, with a comment citing the 156 s measured cold start)
- Test: `digitizer/tests/test_sam2_availability.py` (new)
- No commit: the venv rebuild itself (machine state, not repo state)

**Interfaces:**
- Consumes: `digitizer/sam2_isolated/` venv layout, the checkpoint cache at `~/.cache/sam2/sam2.1_hiera_tiny.pt`.
- Produces: `sam2_segmentation_unavailable_reason(venv_dir: Path) -> str | None` that returns a human-readable reason when `pyvenv.cfg` or `Lib/site-packages` is missing — so the pipeline emits `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` *before* wasting a subprocess spawn, with a reason that names the missing piece.

- [ ] **Step 1: Write the failing test**

```python
# digitizer/tests/test_sam2_availability.py
"""The availability probe must catch a husk venv (Scripts/ stubs present,
no Lib/, no pyvenv.cfg) BEFORE the subprocess attempt — the 2026-08-18 probe
showed exactly that husk reading as 'available' then dying with exit 106."""
from pathlib import Path
from digitizer_core.stage2_sam2_segment import sam2_segmentation_unavailable_reason

def test_husk_venv_is_reported_unavailable(tmp_path: Path):
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "python.exe").write_bytes(b"stub")
    reason = sam2_segmentation_unavailable_reason(venv)
    assert reason is not None and "pyvenv.cfg" in reason

def test_complete_venv_is_available(tmp_path: Path):
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "python.exe").write_bytes(b"stub")
    (venv / "pyvenv.cfg").write_text("home = x")
    (venv / "Lib" / "site-packages").mkdir(parents=True)
    assert sam2_segmentation_unavailable_reason(venv) is None
```

Match the real function's current signature — if it takes no argument and
resolves the venv path itself, add the optional `venv_dir` parameter
defaulting to the resolved path, so the test can point it at `tmp_path`.

- [ ] **Step 2: Run to verify failure**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_sam2_availability.py -q
```
Expected: first test FAILS (husk currently reads available).

- [ ] **Step 3: Implement the check + timeout**

Extend the reason function: after the `python.exe` check, verify
`(venv_dir / "pyvenv.cfg").is_file()` and `(venv_dir / "Lib" / "site-packages").is_dir()`,
returning e.g. `"sam2 venv incomplete: pyvenv.cfg missing (rebuild per sam2_isolated/README.md)"`.
Change the timeout default at `config.py:267` to `240.0` with the comment
`# measured 156 s cold start 2026-08-11; 90 s guaranteed a first-job timeout`.

- [ ] **Step 4: Run tests, then rebuild the venv (machine step)**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_sam2_availability.py -q && .venv/Scripts/python -m pytest -q
```
Then follow `digitizer/sam2_isolated/README.md` to rebuild the venv (torch +
sam2, ~1 GB; the 156 MB checkpoint is already cached). Verify:

```bash
cd digitizer && .venv/Scripts/python -c "from digitizer_core.stage2_sam2_segment import sam2_segmentation_unavailable_reason as r; print(r() or 'AVAILABLE')"
```
Expected: `AVAILABLE`. Then one live job on `owl_kent.jpg` with
`{"forced_class":"photo_subject","photo_prep":true,"photo_segment_sam2":true}`
must return warning `PHOTO_SAM2_SEGMENTED` (not `..._UNAVAILABLE`). Save the
response JSON to `debug_out/`.

- [ ] **Step 5: Commit (code only — venv is machine state)**

```bash
git add digitizer/digitizer_core/stage2_sam2_segment.py digitizer/digitizer_core/config.py digitizer/tests/test_sam2_availability.py
git commit -m "fix(engine): SAM2 availability check catches husk venvs; timeout covers measured cold start"
```

---

### Task 6: Acceptance A/B harness

The eyeball loop (spec decisions 1, 5, 6). A script that takes every image in
the gitignored acceptance dir, runs it through classical and (if available)
SAM2 segmentation with the auto route on, and writes a side-by-side contact
sheet Kent can judge. No scorecard numbers on the sheet — the metric is
explicitly non-authoritative here; stitch/trim/thread counts only.

**Files:**
- Create: `digitizer/tools/acceptance_ab.py`
- Create: `digitizer/testdata/photo/acceptance/README.md` (committed — the dir's only committed file, explaining what to drop here; use `!acceptance/README.md` gitignore negation)
- Modify: `.gitignore` (the negation line)
- Test: `digitizer/tests/test_acceptance_ab.py` (harness logic only, no service)

**Interfaces:**
- Consumes: the running service (`POST /digitize`, `GET /jobs/{id}` — same wire the probe scripts used), Tasks 2–5 in place.
- Produces: `digitizer/debug_out/acceptance_<UTCdate>/contact_sheet.html` + per-run job JSONs; exit code 0 with a printed table (file, variant, regions, threads, stitches, trims, warnings, seconds).

- [ ] **Step 1: Write the failing test for the harness's pure parts**

```python
# digitizer/tests/test_acceptance_ab.py
"""The A/B harness's pure logic: variant matrix and sheet rows. The wire
calls are the probe scripts' pattern and are exercised live, not here."""
from digitizer_core.tools_acceptance import variant_matrix, sheet_row

def test_variant_matrix_without_sam2_is_classical_only():
    assert variant_matrix(sam2_available=False) == [
        {"tag": "classical", "config": {"forced_class": "photo_subject"}},
    ]

def test_variant_matrix_with_sam2_adds_the_ab_arm():
    m = variant_matrix(sam2_available=True)
    assert {"tag": "sam2", "config": {"forced_class": "photo_subject",
            "photo_prep": True, "photo_segment_sam2": True}} in m and len(m) == 2

def test_sheet_row_carries_counts_not_scores():
    row = sheet_row("dog.jpg", "classical",
                    {"shapes": 30, "stitches": 12000, "trims": 40,
                     "threads": 9, "warnings": ["photo_auto_tier"], "wall_s": 14.2})
    assert "score" not in row and row["threads"] == 9
```

Put the pure logic in `digitizer/digitizer_core/tools_acceptance.py` so it is
importable by tests; `tools/acceptance_ab.py` is the thin CLI over it.

- [ ] **Step 2: Run to verify failure**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_acceptance_ab.py -q
```
Expected: FAIL — module missing.

- [ ] **Step 3: Implement**

`digitizer_core/tools_acceptance.py`: `variant_matrix(sam2_available)` and
`sheet_row(...)` exactly as the tests pin. `tools/acceptance_ab.py`: argparse
(`--dir`, default `testdata/photo/acceptance`; `--service`, default
`http://127.0.0.1:8721`), for each image × variant POST /digitize, poll
`/jobs/{id}` (reuse the probe script's poll loop from the scratchpad pattern —
plain urllib, no new deps), collect `sheet_row`s, render
`contact_sheet.html` — one `<tr>` per image, one `<td>` per variant holding
the service's SVG proof (`format: "svg"` export or the job's preview payload —
read `digitizer_service/app.py` for which the response already carries) plus
the counts line. Print the table to stdout too.

`acceptance/README.md`: three lines — what to drop here (3–5 real
portrait/pet photos, 5×7-hoop scale), the privacy rule (dir is gitignored;
never commit), and the run command.

- [ ] **Step 4: Run tests + live smoke on owl_kent.jpg**

```bash
cd digitizer && .venv/Scripts/python -m pytest tests/test_acceptance_ab.py -q && .venv/Scripts/python -m pytest -q
```
Live: copy `testdata/photo/owl_kent.jpg` into the acceptance dir, run
`.venv/Scripts/python tools/acceptance_ab.py`, open the contact sheet, confirm
two variants render (Task 5 made SAM2 available). Delete the copy after.

- [ ] **Step 5: Commit**

```bash
git add digitizer/digitizer_core/tools_acceptance.py digitizer/tools/acceptance_ab.py digitizer/tests/test_acceptance_ab.py digitizer/testdata/photo/acceptance/README.md .gitignore
git commit -m "feat(tools): acceptance A/B contact sheet for the phase-4 eyeball loop"
```

---

## Self-review (done at authoring time)

- **Spec coverage:** decision 1 → Task 6 (+Kent's photos, out of band); 2 → Tasks 1, 2; 3 → Task 3; 4 → Task 4; 5 → Task 5 + Task 6's A/B arm; 6 → Task 0 step 4 + Task 6's README negation; 7 → Task 0. Engineering items (r² retune, palette drift, satin gating, trim thrash) are deliberately NOT tasks here — they get their own evidence-driven pass after the eyeball loop exposes which ones bind. Flat-lane identity guarded in every task's suite run.
- **Placeholder scan:** the "adjust to the real signature" notes in Tasks 1, 4, 5 are read-first instructions with the contract pinned by the test — not TBDs; each names the exact file/lines to read.
- **Type consistency:** `shade_thread_index` (Task 1) is the field Task 3's streamline layering rides; `effective_split_tonal(cfg, class_)` (Task 2) and `auto_photo_tier(cfg, class_, faces_present)` (Task 3) both live in `pipeline.py`; `buildDigitizeConfig(el)` (Task 4) matches the panel-extraction note; `forced_class` string literal is identical in Tasks 3, 4, 5, 6.

## Sequencing and risk

Tasks 0→1→2→3 are strictly ordered (3 needs 1's multi-thread emission and 2's
splitting). 4 and 5 are independent of each other, both need 3's warning code
only for polish (4) and nothing (5) — they can run in parallel after 3.
6 needs everything. Biggest unknown: Task 1's block-assembly refactor touching
chaining/tie logic (`_chain`, `_apply_ties`) — if partitioning by shade breaks
the chain-link accounting, stop and re-read the chaining test's docstring
before adapting anything (systematic-debugging rules apply).

Acceptance photos: Kent supplies 3–5 real portrait/pet photos into the
acceptance dir when Task 6 lands. **The phase-4 v1 exit is Kent approving a
contact sheet, nothing else.**
