# Stage 0 photo texture gate — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Photographs of every genre in the Commons corpus classify in stage 0's photo territory; designed graphics do not; the two-ink misroutes leave it; the old tree is one flag away and pinned.

**Architecture:** Two new signals in `stage0_classify` (a scale-normalised texture fraction and a native-resolution two-tone mass) plus a cut-out test on the alpha channel, folded into the existing two-level tree as a second photo route and a veto, behind `cfg.stage0_texture_gate` (default True). The lens tool re-derives the new tree; a new instrument prints the signals and margins over the fixtures and the corpus.

**Tech Stack:** Python 3.12+, numpy, cv2; pytest from `digitizer/` with the repo venv (`.venv/Scripts/python` on Windows, `.venv/bin/python` on Linux).

**Spec:** `docs/superpowers/specs/2026-10-28-stage0-photo-texture-gate-design.md`

## Global Constraints

- Constants, verbatim from the spec: `TEXTURE_NORM_PX = 512`, `TEXTURE_STD_LO = 2.0`, `TEXTURE_STD_HI = 24.0`, `TEXTURE_EDGE_EXCLUDE_PX = 2`, `TEXTURE_PHOTO_MIN = 0.13`, `TEXTURE_MARGIN = 0.06`, `TWO_TONE_BINS = 16`, `TWO_TONE_MAX = 0.90`, `TWO_TONE_MARGIN = 0.06`; cut-out = alpha present and `(alpha <= 127).any()`.
- `UCM_PHOTO_MIN`, `GRAD_VAR_*`, `CONFIDENCE_FLOOR` untouched. With `stage0_texture_gate=False` the class and confidence of every input are byte-identical to today.
- Every md5 or numeric pin of an engine run uses `frozen_cfg(...)` (`tests/test_pins_are_frozen.py`); `tests/engine_2026_10_27.json` gains `"stage0_texture_gate": false`.
- No synthetic fixture calibrates a threshold (ROADMAP gate 2); tests on hand-built arrays check arithmetic only. No quality claim on any number (gate 4). No corpus image, render or HTML is committed.
- CI lint: `flake8 --select=E9,F63,F7,F82` (a name used only in a string annotation still counts).
- Commits end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. A grayscale PNG with an `LA` alpha (2 channels): `_load` must still hand back rgb + alpha, and the cut-out test must read that alpha — Task 2 test.
2. An alpha channel that is fully opaque (every value 255): not a cut-out; the texture route applies — Task 2 test.
3. An image whose foreground is empty or under 25 px (a fully transparent PNG, a 3x3 file): both new signals return 0.0 and the class is `flat`, no exception — Task 2 test.
4. A file smaller than 512 px on its long edge: the texture signal reads it as-is (no upscale) — Task 2 test on `photo/logo_bridge_bar.jpg` (400 px).
5. `forced_class` still skips every signal (the new ones included) — Task 3 test.

---

### Task 1: the flag and the frozen snapshot

**Files:**
- Modify: `digitizer/digitizer_core/config.py` (after `stage0_seed_sweep`, ~line 414)
- Modify: `digitizer/tests/engine_2026_10_27.json`
- Test: `digitizer/tests/test_stage0_texture_gate.py` (new)

**Interfaces:**
- Produces: `PipelineConfig.stage0_texture_gate: bool = True`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_flag_defaults_on():
    assert PipelineConfig().stage0_texture_gate is True

def test_the_frozen_snapshot_holds_the_pre_flip_value():
    assert ENGINE_2026_10_27["stage0_texture_gate"] is False
```

- [ ] **Step 2: Run them**: `python -m pytest tests/test_stage0_texture_gate.py -q` — FAIL (unknown field / KeyError).
- [ ] **Step 3: Add the field** with a comment naming the spec, the three constants it switches, and that OFF is today's tree. Add `"stage0_texture_gate": false` to the snapshot in alphabetical position.
- [ ] **Step 4: Run** the two tests and `tests/test_pins_are_frozen.py -q` — PASS.
- [ ] **Step 5: Commit** `Stage 0: stage0_texture_gate flag (default ON), snapshot holds OFF`.

### Task 2: the two signals and the cut-out test

**Files:**
- Modify: `digitizer/digitizer_core/stage0_classify.py` (new section after `_alpha_softness`)
- Test: `digitizer/tests/test_stage0_texture_gate.py`

**Interfaces:**
- Produces: `_texture_frac(rgb: np.ndarray, fg: np.ndarray) -> float`; `_two_tone_mass(rgb: np.ndarray, fg: np.ndarray) -> float`; `_has_cutout(alpha: np.ndarray | None) -> bool`; the eight constants from Global Constraints.

- [ ] **Step 1: Write the failing tests** (arithmetic on arrays, readings on real fixtures)

```python
def test_texture_frac_is_zero_on_a_flat_field():
    rgb = np.full((300, 400, 3), 120, np.uint8)
    assert s0._texture_frac(rgb, np.ones((300, 400), bool)) == 0.0

def test_texture_frac_is_near_one_on_broadband_noise():
    rng = np.random.default_rng(0); rgb = rng.integers(100, 140, (300, 400, 3), np.uint8)
    assert s0._texture_frac(rgb, np.ones((300, 400), bool)) > 0.95

def test_texture_frac_ignores_a_hard_edge():
    rgb = np.zeros((300, 400, 3), np.uint8); rgb[:, 200:] = 255
    assert s0._texture_frac(rgb, np.ones((300, 400), bool)) < 0.03

def test_texture_frac_reads_the_long_edge_down_to_512():
    # 2000 px of noise and the same noise INTER_AREA'd to 512 read within 0.05
def test_texture_frac_reads_a_small_file_as_it_is():
    # photo/logo_bridge_bar.jpg (400 px): the reading equals the reading of the raw array
def test_two_tone_mass_on_ink_and_paper():
    rgb = np.full((100, 100, 3), 250, np.uint8); rgb[20:40] = 10
    assert s0._two_tone_mass(rgb, np.ones((100, 100), bool)) == pytest.approx(1.0)
def test_two_tone_mass_on_a_ramp():
    rgb = np.repeat(np.linspace(0, 255, 256).astype(np.uint8)[None, :, None], 3, 2).repeat(10, 0)
    assert s0._two_tone_mass(rgb, np.ones((10, 256), bool)) == pytest.approx(2 / 16, abs=0.01)
def test_empty_foreground_reads_zero():
    assert s0._texture_frac(rgb, np.zeros((300, 400), bool)) == 0.0 and s0._two_tone_mass(...) == 0.0
@pytest.mark.parametrize("alpha,expected", [(None, False), (np.full((4, 4), 255, np.uint8), False),
                                            (np.array([[255, 0], [255, 255]], np.uint8), True)])
def test_has_cutout(alpha, expected): ...
def test_an_LA_png_hands_its_alpha_to_the_cutout_test(tmp_path):
    # PIL saves mode "LA" 8x8 with one transparent pixel; s0._load -> alpha is not None and _has_cutout
@pytest.mark.parametrize("rel,lo,hi", [("photo/owl_kent.jpg", 0.40, 0.55), ("logo_script_tires.png", 0.0, 0.05),
                                       ("logo_whitebg.png", 0.0, 0.05), ("photo/summit_badge.png", 0.0, 0.10)])
def test_texture_readings_on_real_fixtures(rel, lo, hi): ...
@pytest.mark.parametrize("rel,lo,hi", [("logo_script_tires.png", 0.95, 1.0), ("photo/owl_kent.jpg", 0.30, 0.45)])
def test_two_tone_readings_on_real_fixtures(rel, lo, hi): ...
```

- [ ] **Step 2: Run** — FAIL (no attribute).
- [ ] **Step 3: Implement.** `_texture_frac`: resize `rgb` and `fg` (as uint8, `> 0` after) with `cv2.INTER_AREA` when the long edge exceeds `TEXTURE_NORM_PX`; grey as float32; 5x5 `cv2.blur` of `g` and `g*g`, `sd = sqrt(max(m2 - m*m, 0))`; return `((sd >= LO) & (sd < HI))[fg].mean()`, 0.0 when fewer than 25 fg pixels. `_two_tone_mass`: `cv2.cvtColor(rgb, RGB2GRAY)[fg] // 16`, `np.bincount(minlength=16)`, the two largest counts over the total; 0.0 on empty fg. `_has_cutout`: `alpha is not None and bool((alpha <= 127).any())`.
- [ ] **Step 4: Run** the file — PASS. Record the real-fixture readings in the test docstrings (they are readings, not claims).
- [ ] **Step 5: Commit** `Stage 0: texture_frac, two_tone_mass and the cut-out test (signals only)`.

### Task 3: the decision tree

**Files:**
- Modify: `digitizer/digitizer_core/stage0_classify.py` (`classify`, the module docstring's Decision paragraph, `_CEILING_COPY` untouched)
- Test: `digitizer/tests/test_stage0_texture_gate.py`, `digitizer/tests/test_stage0_classify.py`

**Interfaces:**
- Produces: `signals` gains `texture_frac`, `two_tone_mass`, `cutout_alpha` (bool); `decide_photo(ucm, texture, two_tone, cutout, gate_on) -> tuple[bool, float, str]` as a module function the lens can import: (is_photo, photo_gate_conf, route) where route is one of `grain`, `texture`, `grain+texture`, `veto`, `none`, `legacy` (cut-out or gate off). The seed-sweep warning is appended only when route is `grain`, `none` or `legacy`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("rel,on,off", [
    ("photo/owl_kent.jpg", "photo_scene", "gradient"),
    ("logo_script_tires.png", "gradient", "photo_scene"),
    ("photo/drone_render.png", "gradient", "gradient"),
    ("photo/enthusiast_logo.png", "flat", "flat"),
    ("photo/summit_badge.png", "gradient", "gradient"),
    ("photo/fur_ramp.png", "photo_scene", "photo_scene"),
    ("logo_whitebg.png", "flat", "flat"),
])
def test_class_under_both_arms(rel, on, off):
    assert classify(p, cfg(stage0_texture_gate=True)).class_ == on
    assert classify(p, cfg(stage0_texture_gate=False)).class_ == off

def test_off_arm_is_byte_identical_to_the_old_tree_on_every_fixture():
    # for every png/jpg/webp under testdata/ and testdata/photo/: OFF class + confidence == values
    # computed by a local copy of the old two-gate decision from the reported ucm/grad signals
def test_the_signals_are_reported_under_both_arms(): ...  # keys present, cutout_alpha is bool
def test_forced_class_reports_no_signals(): ...
def test_a_photo_verdict_by_texture_carries_the_texture_gate_confidence():
    r = classify(owl, cfg()); assert r.confidence == pytest.approx(min(1.0, 0.5 + 0.5 * abs(r.signals["texture_frac"] - 0.17) / 0.07))
def test_the_veto_decides_tires_confidence():
    # confidence == min(two-tone gate conf, gradient gate conf)
def test_a_cutout_file_takes_the_whole_old_tree():
    # drone_render ON: class, confidence and route == 'legacy'; OFF identical
def test_seed_sweep_warning_is_withheld_when_texture_decided(monkeypatch):
    # owl_kent with stage0_seed_sweep=4: no CLASSIFICATION_SEED_UNSTABLE even if crossings are forced to 2
def test_debug_dump_lists_the_new_signals(tmp_path): ...
```

Also: add `photo/owl_kent.jpg` to `test_same_input_classified_twice_is_identical`'s parametrisation in `test_stage0_classify.py`.

- [ ] **Step 2: Run** — FAIL.
- [ ] **Step 3: Implement** per the spec's decision block and confidence rule. `decide_photo` returns `(is_photo, conf)`; `classify` calls it, then the unchanged inner gates. Signals computed once, always reported. Update the module docstring: "Decision" paragraph gains the second route and the veto; "Real-fixture note" gains one sentence on why cut-outs keep the old tree (the drone).
- [ ] **Step 4: Run** `tests/test_stage0_texture_gate.py tests/test_stage0_classify.py tests/test_stage0_signal_origin.py tests/test_classifier_scale_invariance.py -q` — PASS (the xfail set unchanged: no `XPASS(strict)`).
- [ ] **Step 5: Commit** `Stage 0: texture route + two-ink veto, cut-outs keep the old tree (flag ON)`.

### Task 4: the lens

**Files:**
- Modify: `digitizer/tools/classify_lens.py` (`Thresholds`, `SWEEP_FIELDS`, `decide`, `measure`, `print_table`, the breakpoint helpers for the new signals)
- Test: `digitizer/tests/test_classify_lens.py`

**Interfaces:**
- Consumes: `signals["texture_frac"]`, `["two_tone_mass"]`, `["cutout_alpha"]`; the eight constants.
- Produces: `decide(ucm, grad, texture, two_tone, cutout, th, gate_on=True) -> Decision`; `Thresholds` gains `texture_photo_min, texture_margin, two_tone_max, two_tone_margin`.

- [ ] **Step 1: Write the failing tests**: the existing self-check (lens == engine on every fixture) with the new signature; `test_sweeping_texture_photo_min_moves_owl_kent` (at 0.5 the owl reads gradient); `test_gate_off_reproduces_the_old_tree`.
- [ ] **Step 2: Run** — FAIL (TypeError).
- [ ] **Step 3: Implement**; `nearest_flip` gains the texture and two-tone signals (cutout fixtures report the texture flip as `n/a`).
- [ ] **Step 4: Run** `tests/test_classify_lens.py -q` — PASS; `PYTHONPATH=. python tools/classify_lens.py` prints without error.
- [ ] **Step 5: Commit** `classify_lens: re-derive the texture route and the two-ink veto`.

### Task 5: the instrument

**Files:**
- Create: `digitizer/tools/stage0_photo_gate.py`
- Test: `digitizer/tests/test_stage0_photo_gate.py`

**Interfaces:**
- Produces: `rows(paths: list[Path], cfg) -> list[dict]` (slug, kind, alpha, the three signals, ucm, grad, class ON, class OFF, route); `margins(rows) -> dict` (photo min / graphic max of `texture_frac`, two-tone max of photos / min of graphics); `ladder(path, widths) -> dict`; CLI `python -m tools.stage0_photo_gate [--corpus DIR] [--ladder] [--json]`.

- [ ] **Step 1: Write the failing tests**: `rows` on three fixtures restates `classify`'s class in the ON column (the shipped-answer rule, DOCTRINE 2026-09-11); `margins` of a hand-built row list; `ladder` on `logo_whitebg.png` returns one reading per width below the native width and `None` above.
- [ ] **Step 2: Run** — FAIL. **Step 3: Implement** (corpus rows read `testdata/photo/corpus/corpus.json` and the gitignored images when present; kind from the corpus, `fixture` otherwise). **Step 4: Run** — PASS; run the CLI once on the corpus and keep its table for the PR body. **Step 5: Commit** `tools/stage0_photo_gate: the photo-gate readings and margins`.

### Task 6: the suite, and the pins the veto moves

**Files:**
- Modify: whichever test files go red (expected: `tires`- and `owl_kent`-driven goldens)

- [ ] **Step 1: Run** the whole digitizer suite in the background: `python -m pytest -q -n auto > suite.log 2>&1; echo "EXIT=$?" >> suite.log` (budget: ~10 min on Kent's box, ~45 in a cloud container; never pipe to `tail`).
- [ ] **Step 2: Read** the log. The three named goldens (`test_pushcomp`, `test_flat_lane_byte_identical`, `test_stage2_photo_segment`) are expected red on Windows. Every other red is attributed: a pin of an engine run that moved because its fixture changed lane gets `frozen_cfg(...)` (the OFF arm) with a one-line comment naming this flip; a test that is ABOUT the shipped default gets the new reading with the reason.
- [ ] **Step 3: Run** the fixed files — PASS. **Step 4: Commit** `Stage 0 flip: pin the OFF arm where tires/owl goldens moved`.

### Task 7: the record

**Files:**
- Modify: `DOCTRINE.md` (one entry, under the stage-0 entries), `MASTER_SCOPE.md` (the sentence that says stage 0's colour signals cannot separate a photograph — now dated and superseded), `.claude/memory/MEMORY.md` + a new note `.claude/memory/stage0-texture-gate-2026-10-28.md`
- Test: `digitizer/tests/test_memory_budget.py`, `digitizer/tests/test_scope_budget.py`

- [ ] **Step 1: Write** the DOCTRINE entry: the grain-detector finding, the medium-not-subject finding with the six rows, the rule's three numbers and the barcode limit — under 400 words. The memory note: what a session does differently (OFF arm, the instrument, the photographed-graphics residue). **Step 2: Run** the two budget tests — PASS. **Step 3: Commit** `Docs: stage 0's photo gate was a grain detector (DOCTRINE, memory)`.

### Task 8: capture, side by side, PR

- [ ] **Step 1:** HEAD capture in the background from the worktree: `python -m tools.photo_corpus capture --label head-<sha7> --photos <corpus>` with the rembg venv junctioned as the base capture had it. **Step 2:** `python -m tools.photo_corpus sxs --before corpus_runs/base-a71fd5c --after corpus_runs/head-<sha7>`; `summary` for the head run goes under `docs/scoreboards/photo-corpus/` only if the director asks (the baseline there is main's). **Step 3:** PR body: cause, rule, the per-row class table before/after from both runs, `fidelity_cc` per row (readings), the six photographed-graphic rows named, the barcode limit, the OFF flag, where the sxs HTML is (local path; served by the `corpus-sxs` launch entry). **Step 4:** push, open ready-for-review, arm auto-merge while `mergeable_state` is `blocked`; bind the PR with `ccd_pr`.
