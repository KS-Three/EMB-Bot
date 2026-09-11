# Pro Overlay Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put EMB-Bot's stitches and the professional's on one registered canvas per design, beside a per-element table of how each side laid its thread, so a craft difference can be pointed at, built behind a flag, and re-overlaid in one command.

**Architecture:** Three new modules under `digitizer/tools/pro_parity/` — `pairframe.py` (load a prepped design pair, register ours onto the pro with one uniform scale, a y-flip search and a translation search; everything downstream shares its frame), `overlay.py` (renders both sides through `stitchviz`, tints, masks, flicker pair, crops, per-thread, `--flag` re-digitize arms) and `diff.py` (one set of readers pointed at two machine files; per-region craft rows; ink-split shape rows; `catalogue.md` + `diff.json`). Two small additions to existing code: `adapter.pattern_to_design` (the inverse of `design_to_pattern`) and a committed-fixture fallback in `prep_both`. No engine change.

**Tech Stack:** Python 3.12+ (Kent's venv is 3.14.6), numpy, OpenCV 5, shapely 2.1, scikit-image 0.26 (`deltaE_ciede2000`), pystitch ≥ 1.0.1, pytest. Existing readers reused: `scorecard.register/raster/solid/cell_stats/bounds/shifted/to_segs`, `design_direction.pro_segs/doubled_mean`, `satin_columns.measure/passes_from_file`, `row_pitch_union.union_pitch`, `census_pro._phases`, `preflight._coverage_map`, `junction_blobs._Runs/coverage_in`, `thin_strokes.parse_flags`, `stitchviz.render_design`, `adapter.plan_to_design/design_bbox_units`, `export.write_dst`.

**Spec:** `docs/superpowers/specs/2026-09-09-pro-overlay-loop-design.md`

## Global Constraints

- Run every Python command from `digitizer/` with `.venv/Scripts/python` (a junction to the primary checkout's venv exists in this worktree; `cwd` shadows the editable install, verified 2026-09-09). Always `python -m pytest`; never pipe pytest to `tail`.
- No engine change in this lane. Nothing under `digitizer_core/` changes except `adapter.py` (one additive function). Goldens must not move: `python -m pytest -q tests/test_flat_lane_golden.py tests/test_photo_lane_golden.py` stays as it is on `main` (its three known reds are `test_pushcomp`, `test_flat_lane_byte_identical`, `test_stage2_photo_segment` — a FOURTH is a regression).
- The loop emits no score and no ranking (ROADMAP gate 4). Tolerances in `diff.py` are display thresholds and say so in a comment.
- `study_pro.classify` is never pointed at our own file (its 0.7 mm floor). Tier on BOTH sides is read by the same scale-free rule in `diff.py` (`satin_columns.measure` share, then `union_pitch`), and our engine's intended tier is a separate `tier_planned` column from `ours_regions.json`.
- Prep output directories are never committed. Renders that carry a finding go under `docs/renders/pro-overlay-<date>/`.
- Registration is one uniform scale + a y-flip search + translation. No rotation, no per-axis stretch. IoU is written to every output.
- Coordinates: pystitch files are mm y-DOWN once divided by 10 (`prep_all.decode`, `satin_columns.passes_from_file`). `ours.dst` in a prep dir is written from the plan (mm y-down) by `export.write_dst`, so reading it back gives the plan's own coordinates; `ours_regions.json` WKT is in that same frame. The `Design` dict `stitchviz` renders is 0.1 mm units y-UP (`adapter._u`). Every conversion in this plan is one of those two.
- Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. PRs open ready-for-review with auto-merge armed.
- Git in this worktree: plain commands only, run from the worktree root (the session guard refuses computed command names and `$(...)` around git).

---

## File Structure

| file | responsibility |
|---|---|
| `digitizer/digitizer_core/adapter.py` (modify) | `pattern_to_design(pattern, name, transform_mm=None, fallback_colors=None)` — pystitch pattern → `Design` dict, the inverse of `design_to_pattern` |
| `digitizer/tools/pro_parity/prep_both.py` (modify) | `ART_FALLBACK` map consulted when `find_file(art_rel)` misses; manifest records the source used |
| `digitizer/tools/pro_parity/prep_all.py` (modify) | `parity_config(width_mm, garment_id, **extra)` extracted from `run_ours`; `write_regions(res, outdir)` extracted from `run_ours` |
| `digitizer/tools/pro_parity/pairframe.py` (new) | `Pair` (paths, regions, art, manifest entry), `load_pair(dir)`, `Reg` (scale, flip_y, dx, dy, iou; `apply_xy`, `matrix`), `register_pair(pro_path, ours_path)`, `Frame` (pixel mapping shared by renders and masks), `design_for(path, reg, colors)`, `pin_frame(design, bounds)`, `flags_dir(pair, flags)`, `redigitize(pair, flags)` |
| `digitizer/tools/pro_parity/overlay.py` (new) | `render_pair(pair, reg, px_per_mm, crop=None)` → renders + masks; `tint`, `write_overlay_set(...)`; `by_thread(...)`; CLI with `--dir/--slug --flag --against --crop --crop-name --by-thread` |
| `digitizer/tools/pro_parity/diff.py` (new) | `assign_passes(passes, polys)`, per-region readers, `region_rows(pair, reg)`, `design_rows(...)`, `shape_rows(pair, reg, frame, masks)`, `flag_rows(rows)`, `write_catalogue(...)`; CLI |
| `digitizer/tests/proloop_synth.py` (new, not a test) | synthetic pattern builders shared by the two test files: `satin_pass`, `fill_passes`, `write_pattern`, `make_prep_dir` |
| `digitizer/tests/test_pattern_to_design.py` (new) | round trip plan → pattern → design |
| `digitizer/tests/test_pro_parity_prep.py` (modify) | `ART_FALLBACK`, `parity_config`, `write_regions` |
| `digitizer/tests/test_pro_overlay.py` (new) | registration identity/axis, frame pin, masks, overlay set, crop, by-thread, flag arm, smoke (overlay half) |
| `digitizer/tests/test_pro_diff.py` (new) | tier, width, readers agree, shape tags, catalogue, smoke (diff half) |
| `docs/pro-overlay-first-run-<date>.md`, `docs/renders/pro-overlay-<date>/` (new, Task 13) | the first three catalogues and sheets |

---

### Task 1: `adapter.pattern_to_design` — the inverse of `design_to_pattern`

**Files:**
- Modify: `digitizer/digitizer_core/adapter.py` (after `design_to_pattern`, ~line 220)
- Test: `digitizer/tests/test_pattern_to_design.py`

**Interfaces:**
- Consumes: `adapter.plan_to_design(plan)`, `adapter.design_to_pattern(design)`, pystitch command constants.
- Produces: `pattern_to_design(pattern: pystitch.EmbPattern, name: str = "Reference", transform_mm: Callable[[float, float], tuple[float, float]] | None = None, fallback_colors: list[tuple[int, int, int]] | None = None) -> dict`. Record types are the `Design` contract (`stitch`/`jump`/`trim`/`color`/`end`); units 0.1 mm y-UP; `transform_mm` is applied in the FILE frame (mm, y-down) before the unit flip. `colors` come from `pattern.threadlist`; when the file carries none, or every thread is black (a DST), the `fallback_colors` cycle fills them, one per block.

- [ ] **Step 1: Write the failing round-trip test**

```python
# digitizer/tests/test_pattern_to_design.py
"""`adapter.pattern_to_design` is the inverse of `design_to_pattern`.

The overlay loop renders a professional's machine file through the same
`stitchviz` model the Studio draws, so the file has to become a `Design`
dict exactly the way our own plans do — same record types, same y-up units,
same colour list — or the two sides of an overlay are drawn by two rules.
"""
from __future__ import annotations

import pystitch
import pytest

from digitizer_core.adapter import (design_to_pattern, pattern_to_design,
                                    plan_to_design)
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun


def _plan() -> StitchPlan:
    a = StitchBlock(thread_index=0, thread_number="0010", rgb=(200, 20, 20), runs=[
        StitchRun(points=[(0.0, 0.0), (2.0, 0.0), (2.0, 1.5)], kind="satin"),
        StitchRun(points=[(5.0, 5.0), (7.0, 5.0)], kind="fill", jump=True, trim=True),
    ])
    b = StitchBlock(thread_index=1, thread_number="0020", rgb=(20, 20, 200), runs=[
        StitchRun(points=[(1.0, 8.0), (1.0, 9.0), (3.0, 9.0)], kind="run"),
    ])
    return StitchPlan(blocks=[a, b], palette=[])


def test_round_trip_records_and_colours():
    design = plan_to_design(_plan())
    back = pattern_to_design(design_to_pattern(design))
    want = [(s["x"], s["y"], s["type"]) for s in design["stitches"]]
    got = [(s["x"], s["y"], s["type"]) for s in back["stitches"]]
    assert got == want
    assert [(c["r"], c["g"], c["b"]) for c in back["colors"]] == [(200, 20, 20), (20, 20, 200)]
    assert back["stitchCount"] == design["stitchCount"]


def test_transform_is_applied_in_the_file_frame_before_the_flip():
    design = plan_to_design(_plan())
    pat = design_to_pattern(design)
    moved = pattern_to_design(pat, transform_mm=lambda x, y: (x + 10.0, y * 2.0))
    first = next(s for s in moved["stitches"] if s["type"] == "stitch")
    # plan point (0,0) mm -> file (0,0) -> transform (10, 0) -> units (100, -0)
    assert (first["x"], first["y"]) == (100, 0)
    last_sewn = [s for s in moved["stitches"] if s["type"] == "stitch"][-1]
    # plan point (3,9) mm y-down -> file (3,9) -> (13, 18) -> units (130, -180)
    assert (last_sewn["x"], last_sewn["y"]) == (130, -180)


def test_black_dst_threads_take_the_fallback_cycle():
    pat = pystitch.EmbPattern()
    for _ in range(2):
        t = pystitch.EmbThread()
        t.set_color(0, 0, 0)
        pat.add_thread(t)
    pat.add_stitch_absolute(pystitch.STITCH, 0, 0)
    pat.add_stitch_absolute(pystitch.STITCH, 10, 0)
    pat.add_stitch_absolute(pystitch.COLOR_CHANGE, 10, 0)
    pat.add_stitch_absolute(pystitch.STITCH, 10, 10)
    pat.add_stitch_absolute(pystitch.STITCH, 20, 10)
    pat.end()
    d = pattern_to_design(pat, fallback_colors=[(40, 40, 40), (150, 150, 150)])
    assert [(c["r"], c["g"], c["b"]) for c in d["colors"]] == [(40, 40, 40), (150, 150, 150)]
    assert [s["type"] for s in d["stitches"]] == ["stitch", "stitch", "color", "stitch", "stitch", "end"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pattern_to_design.py -q`
Expected: `ImportError: cannot import name 'pattern_to_design'`

- [ ] **Step 3: Implement `pattern_to_design`**

Append to `digitizer/digitizer_core/adapter.py` after `design_to_pattern`:

```python
def pattern_to_design(pattern: pystitch.EmbPattern, name: str = "Reference",
                      transform_mm=None, fallback_colors=None) -> dict:
    """pystitch pattern -> EMB-Bot `Design`, the inverse of `design_to_pattern`.

    A professional's machine file rendered through `stitchviz` has to be the
    same kind of object our own plans become, or an overlay draws its two
    sides by two rules. Coordinates: the file is 0.1 mm y-DOWN; the Design
    is 0.1 mm y-UP (`_u`'s one flip). `transform_mm(x_mm, y_mm)` is applied
    in the FILE frame before that flip, which is where a registration lives.

    Colours come from the file's thread list. A DST carries none (every
    thread reads black), so `fallback_colors` — one per block, cycled — fills
    the list; blocks are counted from the colour-change records.
    """
    stitches: list[dict] = []
    for x, y, cmd in pattern.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.END:
            break
        xm, ym = x / UNITS_PER_MM, y / UNITS_PER_MM
        if transform_mm is not None:
            xm, ym = transform_mm(xm, ym)
        ux, uy = _u(xm, ym)
        if c == pystitch.STITCH:
            kind = STITCH
        elif c == pystitch.JUMP:
            kind = JUMP
        elif c == pystitch.TRIM:
            kind = TRIM
        elif c in (pystitch.COLOR_CHANGE, pystitch.STOP):
            kind = COLOR
        else:
            continue          # SEQUIN / NEEDLE_SET / ...: no thread, no travel we draw
        stitches.append({"x": ux, "y": uy, "type": kind})
    stitches.append({"x": 0, "y": 0, "type": END})

    n_blocks = 1 + sum(1 for s in stitches if s["type"] == COLOR)
    colors: list[dict] = []
    for t in pattern.threadlist:
        colors.append({"r": int(t.get_red()), "g": int(t.get_green()), "b": int(t.get_blue()),
                       "name": str(getattr(t, "description", "") or "")})
    if fallback_colors and (not colors or all((c["r"], c["g"], c["b"]) == (0, 0, 0) for c in colors)):
        colors = []
    while len(colors) < n_blocks and fallback_colors:
        r, g, b = fallback_colors[len(colors) % len(fallback_colors)]
        colors.append({"r": int(r), "g": int(g), "b": int(b), "name": ""})
    if not colors:
        colors = [{"r": 0, "g": 0, "b": 0, "name": ""}]

    design = {
        "stitches": stitches,
        "colors": colors,
        "stitchCount": sum(1 for s in stitches if s["type"] == STITCH),
        "colorCount": len(colors),
        "name": name,
    }
    w_mm, h_mm = design_size_mm(design)
    design["widthMM"] = round(w_mm, 3)
    design["heightMM"] = round(h_mm, 3)
    return design
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pattern_to_design.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add digitizer/digitizer_core/adapter.py digitizer/tests/test_pattern_to_design.py
git commit -m "adapter.pattern_to_design: a machine file as a Design dict, the inverse of design_to_pattern" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: `prep_both.ART_FALLBACK` — committed logos when the Drive is not mounted

**Files:**
- Modify: `digitizer/tools/pro_parity/prep_both.py` (after `DESIGNS`, and in `prep_one` at the `art_src = prep_all.find_file(art_rel)` line)
- Test: `digitizer/tests/test_pro_parity_prep.py` (append)

**Interfaces:**
- Produces: `ART_FALLBACK: dict[str, Path]` keyed by slug; `resolve_art(slug, art_rel) -> Path` (raises `FileNotFoundError(art_rel)` when neither source exists). `prep_one` calls `resolve_art`; the manifest entry's `art_prep.art_source` (already written by `real_art.prepare`) shows which file was used.

- [ ] **Step 1: Write the failing test**

Open `digitizer/tests/test_pro_parity_prep.py`, look at its existing import block (it loads `prep_all`/`prep_both` via `importlib.util.spec_from_file_location` — copy that pattern for `prep_both` if the file only loads `prep_all`), then append:

```python
def test_art_fallback_resolves_committed_logo_when_drive_art_is_missing(tmp_path, monkeypatch):
    pb = _load("prep_both")            # the module loader this file already uses
    monkeypatch.setattr(pb.prep_all, "ROOT", tmp_path)       # nothing under it
    p = pb.resolve_art("becker_hat_large", "Becker Marine/Becker Marine Logo.png")
    assert p.name == "becker_marine_logo.png" and p.exists()
    with pytest.raises(FileNotFoundError):
        pb.resolve_art("mfab_hat", "MFAB/MFab Logo.png")     # no committed MFab art


def test_art_fallback_prefers_the_drive_file_when_present(tmp_path, monkeypatch):
    pb = _load("prep_both")
    (tmp_path / "Becker Marine").mkdir()
    drive = tmp_path / "Becker Marine" / "Becker Marine Logo.png"
    drive.write_bytes(b"not a png, but present")
    monkeypatch.setattr(pb.prep_all, "ROOT", tmp_path)
    assert pb.resolve_art("becker_hat_large", "Becker Marine/Becker Marine Logo.png") == drive
```

If the file has no `_load` helper, add one at the top matching how it loads `prep_all`:

```python
def _load(name):
    spec = importlib.util.spec_from_file_location(
        f"pro_parity_{name}", Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_parity_prep.py -q -k art_fallback`
Expected: `AttributeError: module ... has no attribute 'resolve_art'`

- [ ] **Step 3: Implement**

In `prep_both.py`, after the `DESIGNS` list:

```python
# The customer artwork Kent supplied on 2026-08-15 lives on the Drive under
# these names; the same files are committed as fixtures. When the Drive is not
# mounted (`G:/` absent on Kent's machine, 2026-09-09) the committed copy is
# used and the manifest's `art_prep.art_source` says so. MFab has no committed
# art and stays Drive-only.
_TESTDATA = Path(__file__).resolve().parents[2] / "testdata"
ART_FALLBACK = {
    "becker_hat_large": _TESTDATA / "becker_marine_logo.png",
    "becker_lc_large": _TESTDATA / "becker_marine_logo.png",
    "becker_hat_small": _TESTDATA / "becker_marine_logo.png",
    "becker_lc_small": _TESTDATA / "becker_marine_logo.png",
    "becker_beanie": _TESTDATA / "becker_marine_logo.png",
    "gaulke_roofing_hat": _TESTDATA / "photo" / "logo_gaulke_roofing.png",
    "gaulke_roofing_lc": _TESTDATA / "photo" / "logo_gaulke_roofing.png",
    "hotel_fremont_hat": _TESTDATA / "photo" / "logo_hotel_fremont.webp",
    "hotel_fremont_patch": _TESTDATA / "photo" / "logo_hotel_fremont.webp",
    "precision_drone": _TESTDATA / "photo" / "drone_render.png",
    "tires_hat_3d": _TESTDATA / "logo_script_tires.png",
    "bridge_hat": _TESTDATA / "photo" / "logo_bridge_bar.jpg",
    "bridge_lc": _TESTDATA / "photo" / "logo_bridge_bar.jpg",
}


def resolve_art(slug: str, art_rel: str) -> Path:
    """The customer's artwork: the Drive file if it is there, else the
    committed fixture for this slug, else FileNotFoundError(art_rel)."""
    p = prep_all.find_file(art_rel)
    if p is not None:
        return Path(p)
    fb = ART_FALLBACK.get(slug)
    if fb is not None and fb.exists():
        return fb
    raise FileNotFoundError(art_rel)
```

Check the slug names against `DESIGNS` (the two `becker_*_small` slugs are whatever `DESIGNS` calls them — copy the exact strings). In `prep_one`, replace

```python
    art_src = prep_all.find_file(art_rel)
    if art_src is None:
        raise FileNotFoundError(art_rel)
```
with
```python
    art_src = resolve_art(slug, art_rel)
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_parity_prep.py -q`
Expected: all pass, including the two new ones.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/prep_both.py digitizer/tests/test_pro_parity_prep.py
git commit -m "prep_both: committed logos as the artwork fallback when the Drive is not mounted" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: `prep_all.parity_config` and `write_regions` — the harness's config and region file, callable on their own

**Files:**
- Modify: `digitizer/tools/pro_parity/prep_all.py` (`run_ours`, lines ~612–780)
- Test: `digitizer/tests/test_pro_parity_prep.py` (append)

**Interfaces:**
- Produces: `parity_config(width_mm: float, garment_id: str | None = None, **extra) -> PipelineConfig` — exactly the config `run_ours` builds (garment, `PRO_PARITY_FORCED_CLASS`, `PRO_PARITY_SIMPLIFY_TOL`, `fill_density_boost=True` when the field exists, `target_width_mm=round(width_mm, 1)`), with `extra` applied last as `setattr`s; `write_regions(res, outdir: Path) -> Path` writes `ours_regions.json` in the existing schema (`shape_id, area_mm2, thread, tier, bounds, wkt`). `run_ours` calls both, so its output is byte-identical to before.

- [ ] **Step 1: Write the failing tests**

```python
def test_parity_config_matches_run_ours_and_applies_extra(monkeypatch):
    pa = _load("prep_all")
    monkeypatch.delenv("PRO_PARITY_FORCED_CLASS", raising=False)
    monkeypatch.delenv("PRO_PARITY_SIMPLIFY_TOL", raising=False)
    cfg = pa.parity_config(95.66, "hat_front", keep_thin_strokes=True)
    assert cfg.target_width_mm == 95.7
    assert cfg.garment_id == "hat_front"
    assert cfg.keep_thin_strokes is True
    if "fill_density_boost" in type(cfg).__dataclass_fields__:
        assert cfg.fill_density_boost is True
    with pytest.raises(TypeError):
        pa.parity_config(80.0, None, not_a_field=1)


def test_write_regions_schema(tmp_path):
    pa = _load("prep_all")
    from types import SimpleNamespace
    from shapely.geometry import box
    r = SimpleNamespace(shape_id="S1", area_mm2=12.34, thread_number="0010",
                        meta={"tier": "satin"}, polygon=box(0, 0, 3, 4))
    out = pa.write_regions(SimpleNamespace(regions=[r]), tmp_path)
    rows = json.loads(out.read_text())
    assert rows == [{"shape_id": "S1", "area_mm2": 12.3, "thread": "0010", "tier": "satin",
                     "bounds": [0.0, 0.0, 3.0, 4.0],
                     "wkt": "POLYGON ((3.000 0.000, 3.000 4.000, 0.000 4.000, 0.000 0.000, 3.000 0.000))"}]
```

(If the WKT string differs only in vertex order, assert on `shapely.wkt.loads(rows[0]["wkt"]).equals(box(0,0,3,4))` instead of the literal.)

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_parity_prep.py -q -k "parity_config or write_regions"`
Expected: `AttributeError ... parity_config`

- [ ] **Step 3: Extract the two functions**

In `prep_all.py`, above `run_ours`:

```python
def parity_config(width_mm, garment_id=None, **extra):
    """The PipelineConfig every parity run is measured with. `extra` is applied
    LAST, by name, and an unknown name raises rather than becoming a stray
    attribute nothing reads (the fill_density_boost lesson of 2026-08-15)."""
    cfg = PipelineConfig()
    cfg.garment_id = garment_id
    forced = os.environ.get("PRO_PARITY_FORCED_CLASS")
    if forced:
        if forced not in CLASSES:
            sys.exit(f"PRO_PARITY_FORCED_CLASS={forced!r} is not a class. "
                     f"Valid: {', '.join(CLASSES)}")
        cfg.forced_class = forced
    tol = os.environ.get("PRO_PARITY_SIMPLIFY_TOL")
    if tol is not None:
        if "simplify_tol_mm" not in PipelineConfig.__dataclass_fields__:
            raise RuntimeError("PRO_PARITY_SIMPLIFY_TOL set but PipelineConfig "
                               "has no simplify_tol_mm field on this tree")
        try:
            tol_mm = float(tol)
        except ValueError:
            raise RuntimeError(f"PRO_PARITY_SIMPLIFY_TOL={tol!r} is not a number") from None
        if not (0.0 < tol_mm <= 1.0):
            raise RuntimeError(f"PRO_PARITY_SIMPLIFY_TOL={tol_mm} out of range (0, 1.0]")
        cfg.simplify_tol_mm = tol_mm
        print(f"  simplify_tol_mm={tol_mm} (requested; stage 4 floors eps at 0.5 px, "
              f"so low-res art may realize coarser)", flush=True)
    if "fill_density_boost" in PipelineConfig.__dataclass_fields__:
        cfg.fill_density_boost = True
    else:
        print("  WARNING: PipelineConfig has no `fill_density_boost` field on this tree — "
              "measuring the shipped default, NOT the boosted fill every pro-parity number "
              "before 2026-08-15 was measured with.", flush=True)
    cfg.target_width_mm = round(width_mm, 1)
    for k, v in extra.items():
        if k not in PipelineConfig.__dataclass_fields__:
            raise TypeError(f"PipelineConfig has no field {k!r}")
        setattr(cfg, k, v)
    return cfg


def write_regions(res, outdir):
    """`ours_regions.json`: the ARTWORK polygon stage 7 classifies on, per
    region, so a probe can re-ask the classifier's question without re-running
    stages 0-4. Rounded to 3 dp (sub-micron precision on mm is noise)."""
    regions = [{"shape_id": r.shape_id, "area_mm2": round(r.area_mm2, 1),
                "thread": r.thread_number, "tier": r.meta.get("tier"),
                "bounds": [round(v, 1) for v in r.polygon.bounds],
                "wkt": shapely.wkt.dumps(r.polygon, rounding_precision=3)}
               for r in res.regions]
    p = Path(outdir) / "ours_regions.json"
    p.write_text(json.dumps(regions, indent=1))
    return p
```

Then in `run_ours`: delete the config-building block (from `cfg = PipelineConfig()` through `cfg.target_width_mm = round(width_mm, 1)`) and replace with `cfg = parity_config(width_mm, garment_id)`; delete the `regions = [...]`/`(outdir / "ours_regions.json").write_text(...)` block and replace with `write_regions(res, outdir)`. Move the comments that explain WHY (the fill_density_boost story, the stray-attribute story) onto the new function rather than deleting them.

- [ ] **Step 4: Run the prep tests and the existing harness tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_parity_prep.py tests/test_pro_parity_scorecard.py tests/test_scorecard_surface.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/prep_all.py digitizer/tests/test_pro_parity_prep.py
git commit -m "prep_all: parity_config and write_regions extracted from run_ours, so a flag arm builds the same config" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Synthetic builders — `tests/proloop_synth.py`

**Files:**
- Create: `digitizer/tests/proloop_synth.py` (imported by tests, not collected)

**Interfaces:**
- Produces: `satin_pass(x0, y0, length, width, pitch=0.4, angle_deg=0.0) -> list[(x, y)]` (zigzag across a column: crosses alternate rails; scale-free detector reads it as satin); `fill_passes(x0, y0, w, h, row=0.4, stitch=3.0) -> list[list[(x, y)]]` (parallel rows, one pass per row, serpentine); `write_pattern(path, blocks: list[tuple[tuple[int,int,int], list[list[(x,y)]]]]) -> Path` (pystitch DST/PES by extension; a TRIM before every pass after the first in a block, a COLOR_CHANGE between blocks); `transform_passes(passes, scale=1.0, flip_y=False, dx=0.0, dy=0.0)`; `make_prep_dir(root, slug, pro_blocks, ours_blocks, regions, art_ink_boxes_mm, width_mm, garment_id="left_chest") -> Path` — lays out `<root>/real/<slug>/` with `pro.pes`, `ours.dst`, `ours_regions.json`, `ours_blocks.json`, `pro_blocks.json`, `art.png`, and `<root>/real/manifest.json` carrying `{"slug", "file", "garment_id", "pro": {"width_mm"}}` — everything `pairframe.load_pair` reads.

- [ ] **Step 1: Write the module**

```python
# digitizer/tests/proloop_synth.py
"""Synthetic stitch geometry for the pro-overlay loop's tests.

Everything is built by hand — no engine call — so a test can say exactly
what each side sewed. Coordinates are mm in the FILE frame (y-down), the
frame `satin_columns.passes_from_file` and `prep_all.decode` read.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pystitch
from PIL import Image
from shapely.geometry import box
import shapely.wkt


def satin_pass(x0, y0, length, width, pitch=0.4, angle_deg=0.0):
    """A zigzag column: rails `width` apart, crosses every `pitch` along
    `length`, the column's axis at `angle_deg`. Points alternate rails."""
    ca, sa = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    nx, ny = -sa, ca                       # rail normal
    pts = []
    n = max(3, int(length / pitch))
    for i in range(n + 1):
        t = i * pitch
        side = 1 if i % 2 == 0 else -1
        px = x0 + t * ca + side * (width / 2) * nx
        py = y0 + t * sa + side * (width / 2) * ny
        pts.append((round(px, 3), round(py, 3)))
    return pts


def fill_passes(x0, y0, w, h, row=0.4, stitch=3.0):
    """Tatami rows across a w x h box, serpentine, one pass per row."""
    passes = []
    rows = max(3, int(h / row))
    for r in range(rows + 1):
        y = y0 + r * row
        xs = np.arange(x0, x0 + w + 1e-9, stitch).tolist()
        if xs[-1] < x0 + w:
            xs.append(x0 + w)
        if r % 2:
            xs = xs[::-1]
        passes.append([(round(x, 3), round(y, 3)) for x in xs])
    return passes


def transform_passes(passes, scale=1.0, flip_y=False, dx=0.0, dy=0.0):
    fy = -1.0 if flip_y else 1.0
    return [[(x * scale + dx, y * fy * scale + dy) for x, y in p] for p in passes]


def write_pattern(path, blocks):
    """`blocks`: [((r,g,b), [pass, pass, ...]), ...]. A TRIM before every pass
    after the first of a block; a COLOR_CHANGE between blocks. Units 0.1 mm."""
    pat = pystitch.EmbPattern()
    for rgb, _ in blocks:
        t = pystitch.EmbThread()
        t.set_color(*rgb)
        pat.add_thread(t)
    for bi, (_rgb, passes) in enumerate(blocks):
        if bi:
            x, y = passes[0][0] if passes and passes[0] else (0, 0)
            pat.add_stitch_absolute(pystitch.COLOR_CHANGE, int(round(x * 10)), int(round(y * 10)))
        for pi, pts in enumerate(passes):
            if pi:
                lx, ly = passes[pi - 1][-1]
                pat.add_stitch_absolute(pystitch.TRIM, int(round(lx * 10)), int(round(ly * 10)))
                pat.add_stitch_absolute(pystitch.JUMP, int(round(pts[0][0] * 10)), int(round(pts[0][1] * 10)))
            for x, y in pts:
                pat.add_stitch_absolute(pystitch.STITCH, int(round(x * 10)), int(round(y * 10)))
    pat.end()
    path = Path(path)
    if path.suffix.lower() == ".pes":
        pystitch.write_pes(pat, str(path))
    else:
        pystitch.write_dst(pat, str(path))
    return path


def make_prep_dir(root, slug, pro_blocks, ours_blocks, regions, art_ink_boxes_mm,
                  width_mm, garment_id="left_chest", art_px_per_mm=10.0):
    """A `<root>/real/<slug>/` directory shaped like `prep_both`'s output.

    `regions`: [(shape_id, tier, shapely polygon in OURS frame)].
    `art_ink_boxes_mm`: [(x0, y0, x1, y1)] in OURS frame; the art is drawn
    black-on-transparent at `art_px_per_mm` over the ours stitch extents.
    """
    d = Path(root) / "real" / slug
    d.mkdir(parents=True, exist_ok=True)
    pro = write_pattern(d / "pro.pes", pro_blocks)
    write_pattern(d / "ours.dst", ours_blocks)
    (d / "ours_regions.json").write_text(json.dumps([
        {"shape_id": sid, "area_mm2": round(poly.area, 1), "thread": "0010", "tier": tier,
         "bounds": [round(v, 1) for v in poly.bounds],
         "wkt": shapely.wkt.dumps(poly, rounding_precision=3)}
        for sid, tier, poly in regions], indent=1))
    (d / "ours_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(rgb)} for i, (rgb, _) in enumerate(ours_blocks)]))
    (d / "pro_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(rgb)} for i, (rgb, _) in enumerate(pro_blocks)]))
    # art: the ink boxes over ours' stitch extents, alpha where ink is
    pts = [p for _rgb, passes in ours_blocks for ps in passes for p in ps]
    ox0, oy0 = min(p[0] for p in pts), min(p[1] for p in pts)
    ox1, oy1 = max(p[0] for p in pts), max(p[1] for p in pts)
    W = max(8, int(round((ox1 - ox0) * art_px_per_mm)) + 1)
    H = max(8, int(round((oy1 - oy0) * art_px_per_mm)) + 1)
    a = np.zeros((H, W, 4), np.uint8)
    for bx0, by0, bx1, by1 in art_ink_boxes_mm:
        c0, r0 = int((bx0 - ox0) * art_px_per_mm), int((by0 - oy0) * art_px_per_mm)
        c1, r1 = int((bx1 - ox0) * art_px_per_mm), int((by1 - oy0) * art_px_per_mm)
        a[max(0, r0):min(H, r1), max(0, c0):min(W, c1)] = (0, 0, 0, 255)
    Image.fromarray(a, "RGBA").save(d / "art.png")
    man = Path(root) / "real" / "manifest.json"
    entries = json.loads(man.read_text()) if man.exists() else []
    entries = [e for e in entries if e.get("slug") != slug]
    entries.append({"slug": slug, "file": str(pro), "garment_id": garment_id,
                    "pro": {"width_mm": width_mm}, "ok": True})
    man.write_text(json.dumps(entries, indent=1))
    return d
```

- [ ] **Step 2: Smoke it by hand**

Run: `cd digitizer && .venv/Scripts/python -c "import sys; sys.path.insert(0,'tests'); import proloop_synth as s, tempfile, pathlib; d=s.make_prep_dir(tempfile.mkdtemp(),'t',[((0,0,0),[s.satin_pass(0,0,10,2)])],[((0,0,0),[s.satin_pass(0,0,10,2)])],[],[(0,0,10,2)],10.0); print(sorted(p.name for p in d.iterdir()))"`
Expected: `['art.png', 'ours.dst', 'ours_blocks.json', 'ours_regions.json', 'pro.pes', 'pro_blocks.json']`

- [ ] **Step 3: Commit**

```bash
git add digitizer/tests/proloop_synth.py
git commit -m "tests: synthetic stitch builders for the pro-overlay loop" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: `pairframe.py` — load a pair, register ours onto the pro

**Files:**
- Create: `digitizer/tools/pro_parity/pairframe.py`
- Test: `digitizer/tests/test_pro_overlay.py` (registration half)

**Interfaces:**
- Consumes: `scorecard.register/bounds/shifted/to_segs`, `design_direction.pro_segs` (as the file reader — it takes `(path, flip_y)` and returns scorecard segs `(x0,y0,x1,y1,len,block,trimmed)`), `adapter.pattern_to_design`, `adapter.design_bbox_units`, `prep_all.GREYS`.
- Produces:
  - `@dataclass Pair: slug, dir: Path, pro_path: Path, ours_path: Path, regions: list[dict], art: Path, garment_id: str | None, width_mm: float, pro_rgb: list[tuple], ours_rgb: list[tuple]`
  - `load_pair(dir: Path) -> Pair` — `dir` is `<out>/real/<slug>` (or `<out>/real/<slug>/flags/<hash>` — then regions/blocks/`ours.dst` come from that subdir and the pro from the parent's manifest). `pro_path` from `manifest.json["file"]` beside `dir`'s lane root; when that path is absent but a `pro.pes`/`pro.dst` sits in `dir` (synthetic), use it. `width_mm` = pro stitch x-extent (what prep sized ours to).
  - `@dataclass Reg: scale: float, flip_y: bool, dx: float, dy: float, iou: float` with `apply_xy(x, y) -> (x', y')` and `matrix() -> [a, b, d, e, xoff, yoff]` for `shapely.affinity.affine_transform`, and `as_dict()`.
  - `file_segs(path, flip_y=False)` = `design_direction.pro_segs`.
  - `scale_segs(segs, s)`; `centre(segs) -> (cx, cy)`; `x_extent(segs) -> float`.
  - `register_pair(pro_path, ours_path) -> Reg` — scale = pro x-extent / ours x-extent; for `flip_y` in `(False, True)`: scale ours, centre on the pro, `scorecard.register`; keep the higher IoU.

- [ ] **Step 1: Write the failing tests**

```python
# digitizer/tests/test_pro_overlay.py
"""The pro-overlay loop: registration, the shared frame, and the overlay set.

Spec: docs/superpowers/specs/2026-09-09-pro-overlay-loop-design.md §3-§4.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                       # proloop_synth
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "tools" / "pro_parity"))

import proloop_synth as synth                        # noqa: E402
import pairframe                                     # noqa: E402


def _design_blocks(offset=(0.0, 0.0)):
    """An asymmetric design: an L of two satin columns and a fill slab."""
    ox, oy = offset
    return [((200, 30, 30), [synth.satin_pass(ox + 0, oy + 0, 20, 2.0),
                             synth.satin_pass(ox + 0, oy + 0, 12, 2.0, angle_deg=90)]),
            ((30, 30, 200), [*synth.fill_passes(ox + 6, oy + 6, 10, 6)])]


def test_register_identity_under_shift_scale_and_flip(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, scale=0.95, flip_y=True, dx=7.3, dy=-4.1)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "ident", pro, ours, [], [(0, 0, 20, 12)], 19.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    assert reg.iou >= 0.95
    assert abs(reg.scale - 0.95) < 0.02
    assert reg.flip_y is True


def test_register_reports_no_flip_when_none_is_needed(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, dx=3.0, dy=2.0)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "noflip", pro, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    assert reg.iou >= 0.95 and reg.flip_y is False
    x, y = reg.apply_xy(0.0, 0.0)
    assert abs(x - 3.0) < 0.3 and abs(y - 2.0) < 0.3


def test_load_pair_reads_manifest_regions_and_colours(tmp_path):
    from shapely.geometry import box
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "lp", ours, ours,
                            [("S1", "satin", box(-1, -1, 21, 1))], [(0, 0, 20, 2)], 20.0,
                            garment_id="hat_front")
    pair = pairframe.load_pair(d)
    assert pair.slug == "lp" and pair.garment_id == "hat_front"
    assert pair.pro_path.name == "pro.pes" and pair.ours_path.name == "ours.dst"
    assert [r["shape_id"] for r in pair.regions] == ["S1"]
    assert pair.pro_rgb == [(200, 30, 30), (30, 30, 200)]
    assert 19.0 < pair.width_mm < 21.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q`
Expected: `ModuleNotFoundError: No module named 'pairframe'`

- [ ] **Step 3: Write `pairframe.py`**

```python
# digitizer/tools/pro_parity/pairframe.py
"""One prepped design pair — the professional's file and ours — in ONE frame.

`overlay.py` draws and `diff.py` measures; both read the pair through this
module so a pixel in the overlay and a row in the catalogue are the same
registration. Registration is: one uniform scale (the pro's stitch width
over ours — never per-axis, an aspect mismatch is a finding), a y-flip
search (both are tried, the better IoU wins, and the result SAYS which), and
`scorecard.register`'s translation search. No rotation: a registration that
could absorb a redesign would hide it (Gaulke's re-composed layout is the
known case, and it is meant to fail loudly).

Frames: machine files are mm y-DOWN once divided by 10 (`prep_all.decode`,
`satin_columns.passes_from_file`); `ours.dst` was written from the plan, so
reading it back gives plan coordinates, the frame `ours_regions.json` is in.
The `Design` dict `stitchviz` draws is 0.1 mm y-UP; `Frame` below is the one
place that mapping lives, so renders and masks agree pixel for pixel.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pystitch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import scorecard as sc                                              # noqa: E402
from design_direction import pro_segs as file_segs                  # noqa: E402
from prep_all import GREYS                                          # noqa: E402
from digitizer_core.adapter import (design_bbox_units, pattern_to_design,  # noqa: E402
                                    UNITS_PER_MM)


@dataclass
class Pair:
    slug: str
    dir: Path
    pro_path: Path
    ours_path: Path
    regions: list
    art: Path
    garment_id: str | None
    width_mm: float
    pro_rgb: list
    ours_rgb: list


@dataclass
class Reg:
    scale: float
    flip_y: bool
    dx: float
    dy: float
    iou: float

    def apply_xy(self, x: float, y: float) -> tuple[float, float]:
        fy = -1.0 if self.flip_y else 1.0
        return self.scale * x + self.dx, self.scale * fy * y + self.dy

    def matrix(self) -> list[float]:
        """shapely.affinity.affine_transform's [a, b, d, e, xoff, yoff]."""
        fy = -1.0 if self.flip_y else 1.0
        return [self.scale, 0.0, 0.0, self.scale * fy, self.dx, self.dy]

    def as_dict(self) -> dict:
        d = asdict(self)
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def _lane_root(d: Path) -> Path:
    """`<out>/real/<slug>` or `<out>/real/<slug>/flags/<hash>` -> `<out>/real`."""
    d = Path(d).resolve()
    if d.parent.name == "flags":
        return d.parents[2]
    return d.parent


def _slug(d: Path) -> str:
    d = Path(d).resolve()
    return d.parents[1].name if d.parent.name == "flags" else d.name


def _rgbs(path: Path) -> list:
    try:
        return [tuple(b["rgb"]) for b in json.loads(Path(path).read_text())]
    except Exception:
        return []


def load_pair(d: Path) -> Pair:
    d = Path(d).resolve()
    slug = _slug(d)
    root = _lane_root(d)
    base = root / slug
    entry = {}
    man = root / "manifest.json"
    if man.exists():
        for e in json.loads(man.read_text()):
            if e.get("slug") == slug:
                entry = e
    pro = Path(entry["file"]) if entry.get("file") and Path(entry["file"]).exists() else None
    if pro is None:
        for n in ("pro.pes", "pro.dst", "pro.PES", "pro.DST"):
            if (base / n).exists():
                pro = base / n
                break
    if pro is None:
        raise FileNotFoundError(f"no pro file for {slug}: manifest {man} has no readable `file` "
                                f"and {base} holds no pro.pes/pro.dst")
    ours = d / "ours.dst"
    if not ours.exists():
        raise FileNotFoundError(f"{ours} — prep this design first (prep_both.py {slug})")
    regions = json.loads((d / "ours_regions.json").read_text()) if (d / "ours_regions.json").exists() else []
    segs = file_segs(pro, False)
    return Pair(slug=slug, dir=d, pro_path=pro, ours_path=ours, regions=regions,
                art=base / "art.png", garment_id=entry.get("garment_id"),
                width_mm=x_extent(segs), pro_rgb=_rgbs(base / "pro_blocks.json"),
                ours_rgb=_rgbs(d / "ours_blocks.json"))


# ------------------------------------------------------------ registration
def x_extent(segs) -> float:
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    return (max(xs) - min(xs)) if xs else 0.0


def centre(segs) -> tuple[float, float]:
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    ys = [s[1] for s in segs] + [s[3] for s in segs]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def scale_segs(segs, s: float):
    return [(x0 * s, y0 * s, x1 * s, y1 * s, d * s, b, t) for (x0, y0, x1, y1, d, b, t) in segs]


def register_pair(pro_path: Path, ours_path: Path) -> Reg:
    pro = file_segs(Path(pro_path), False)
    if not pro:
        raise ValueError(f"{pro_path}: no stitches")
    best = None
    for flip in (False, True):
        ours = file_segs(Path(ours_path), flip)
        if not ours:
            raise ValueError(f"{ours_path}: no stitches")
        s = x_extent(pro) / max(x_extent(ours), 1e-9)
        ours_s = scale_segs(ours, s)
        pcx, pcy = centre(pro)
        ocx, ocy = centre(ours_s)
        dx, dy = pcx - ocx, pcy - ocy
        ours_c = sc.shifted(ours_s, dx, dy)
        bb = sc.bounds(pro, ours_c)
        rdx, rdy, iou = sc.register(pro, ours_c, bb)
        cand = Reg(scale=s, flip_y=flip, dx=dx + rdx, dy=dy + rdy, iou=float(iou))
        if best is None or cand.iou > best.iou:
            best = cand
    return best


# ------------------------------------------------------------------- frame
@dataclass
class Frame:
    """`render_design`'s pixel mapping, made explicit so masks and renders
    agree: px = (X - x0_mm + pad) * ppm, py = (Y + y1_mm + pad) * ppm for a
    file-frame point (X, Y) in mm y-down, where (x0, y1) are the pinned
    Design bounds in units (y-up)."""
    x0_units: int
    x1_units: int
    y0_units: int
    y1_units: int
    pad_mm: float
    ppm: float

    @property
    def size(self) -> tuple[int, int]:
        w = max(8, int(((self.x1_units - self.x0_units) / UNITS_PER_MM + 2 * self.pad_mm) * self.ppm))
        h = max(8, int(((self.y1_units - self.y0_units) / UNITS_PER_MM + 2 * self.pad_mm) * self.ppm))
        return w, h

    def to_px(self, X: float, Y: float) -> tuple[float, float]:
        return ((X - self.x0_units / UNITS_PER_MM + self.pad_mm) * self.ppm,
                (Y + self.y1_units / UNITS_PER_MM + self.pad_mm) * self.ppm)

    def mm_to_px_affine(self) -> np.ndarray:
        """2x3 matrix taking file-frame mm (X, Y) to frame pixels."""
        return np.array([[self.ppm, 0.0, (-self.x0_units / UNITS_PER_MM + self.pad_mm) * self.ppm],
                         [0.0, self.ppm, (self.y1_units / UNITS_PER_MM + self.pad_mm) * self.ppm]])

    @property
    def bounds_units(self):
        return (self.x0_units, self.x1_units, self.y0_units, self.y1_units)


def design_for(path: Path, reg: Reg | None, colors: list | None, name: str) -> dict:
    """A machine file as a Design dict, `reg` applied (ours) or not (pro)."""
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    fb = colors or list(GREYS)
    t = (lambda x, y: reg.apply_xy(x, y)) if reg is not None else None
    return pattern_to_design(pat, name=name, transform_mm=t, fallback_colors=fb)


def pin_frame(design: dict, bounds_units) -> dict:
    """Two jump records at the frame corners: `stitchviz._bounds` counts
    jumps and `render_design` draws nothing for them, so both sides of a
    pair render on identical canvases without touching the renderer."""
    x0, x1, y0, y1 = bounds_units
    d = dict(design)
    d["stitches"] = list(design["stitches"]) + [
        {"x": int(x0), "y": int(y0), "type": "jump"},
        {"x": int(x1), "y": int(y1), "type": "jump"},
    ]
    return d


def frame_for(designs: list, ppm: float, pad_mm: float = 2.0,
              crop_mm: tuple | None = None) -> Frame:
    """The union frame of several designs, or a crop window (file-frame mm,
    x0 y0 x1 y1, y-down) at `ppm`."""
    if crop_mm is not None:
        cx0, cy0, cx1, cy1 = crop_mm
        return Frame(int(round(cx0 * UNITS_PER_MM)), int(round(cx1 * UNITS_PER_MM)),
                     int(round(-cy1 * UNITS_PER_MM)), int(round(-cy0 * UNITS_PER_MM)), 0.0, ppm)
    boxes = [design_bbox_units(d) for d in designs]
    return Frame(min(b[0] for b in boxes), max(b[1] for b in boxes),
                 min(b[2] for b in boxes), max(b[3] for b in boxes), pad_mm, ppm)


# -------------------------------------------------------------- flag arms
def flags_hash(flags: dict) -> str:
    key = json.dumps(sorted(flags.items()), default=str)
    return hashlib.sha1(key.encode()).hexdigest()[:8]


def flags_dir(pair: Pair, flags: dict) -> Path:
    base = pair.dir if pair.dir.parent.name != "flags" else pair.dir.parents[1]
    return base / "flags" / flags_hash(flags)
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q`
Expected: `3 passed`. If `test_register_identity...` reports `flip_y is False` with IoU ≥ 0.95, the L-shape is too symmetric under the flip — lengthen the vertical arm to 16 mm and re-run; the point of the asymmetric fixture is that only one flip registers.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/pairframe.py digitizer/tests/test_pro_overlay.py
git commit -m "pro_parity/pairframe: one frame for a design pair — load, register (scale + flip search + shift), pin" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: `overlay.py` — renders, masks, the overlay set

**Files:**
- Create: `digitizer/tools/pro_parity/overlay.py`
- Test: `digitizer/tests/test_pro_overlay.py` (append)

**Interfaces:**
- Consumes: `pairframe.load_pair/register_pair/design_for/pin_frame/frame_for/Frame`, `stitchviz.render_design`.
- Produces:
  - `render_side(design, frame) -> np.ndarray` (BGR on white, `lit=True`).
  - `thread_mask(img) -> np.ndarray[bool]` (any channel < 250).
  - `tint(img, rgb) -> np.ndarray` — thread pixels take `rgb * (0.35 + 0.65 * L)`, fabric stays white.
  - `render_pair(pair, reg, ppm=12.0, crop_mm=None, only_pro_block=None, only_ours_blocks=None) -> dict` with keys `frame, pro, ours, pro_mask, ours_mask, overlay, pro_only, ours_only`.
  - `write_overlay_set(out_dir, r, title, suffix="") -> list[Path]` writing `overlay{suffix}.png`, `pro_only{suffix}.png`, `ours_only{suffix}.png`, `flicker_pro{suffix}.png`, `flicker_ours{suffix}.png`; the title line is drawn along the top of `overlay` with `cv2.putText`.
  - `PRO_TINT = (255, 0, 255)`, `OURS_TINT = (0, 200, 255)` (RGB).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_pro_overlay.py`)

```python
import overlay                                       # noqa: E402  (add beside `import pairframe`)


def test_masks_agree_with_renders_and_overlap_reads_dark(tmp_path):
    ours = _design_blocks()
    pro = [(rgb, synth.transform_passes(p, dx=2.0, dy=0.0)) for rgb, p in ours]
    d = synth.make_prep_dir(tmp_path, "ov", pro, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg, ppm=12.0)
    assert r["pro"].shape == r["ours"].shape == r["overlay"].shape
    assert r["pro_mask"].any() and r["ours_mask"].any()
    both = r["pro_mask"] & r["ours_mask"]
    assert both.sum() > 0.8 * r["pro_mask"].sum()            # registered: most thread overlaps
    assert r["overlay"][both].mean() < 120                    # multiply of two tints is dark
    assert not (r["pro_only"] & r["ours_only"]).any() if isinstance(r["pro_only"], np.ndarray) and r["pro_only"].dtype == bool else True
    # pro_only image: magenta where pro-only, near-white elsewhere except the grey ghost
    po = r["pro_only_img"]
    assert po.shape == r["pro"].shape


def test_write_overlay_set_writes_five_files(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "ws", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    files = overlay.write_overlay_set(d / "overlay", r, title="ws 20.0 mm")
    assert sorted(p.name for p in files) == sorted([
        "overlay.png", "pro_only.png", "ours_only.png", "flicker_pro.png", "flicker_ours.png"])
    a = cv2.imread(str(d / "overlay" / "flicker_pro.png"))
    b = cv2.imread(str(d / "overlay" / "flicker_ours.png"))
    assert a.shape == b.shape
```

Adjust the first test's `pro_only` assertion to the final key names once written: `render_pair` returns boolean masks `pro_only`/`ours_only` AND images `pro_only_img`/`ours_only_img`. Keep the assertion `not (r["pro_only"] & r["ours_only"]).any()`.

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q -k "masks or write_overlay"`
Expected: `ModuleNotFoundError: No module named 'overlay'`

- [ ] **Step 3: Write `overlay.py`** (library half; the CLI comes in Task 8)

```python
# digitizer/tools/pro_parity/overlay.py
"""Ours over the pro's, registered, on one canvas.

Pro in magenta, ours in cyan, overlap dark (multiply) — the convention every
print-registration viewer uses, so a misregistered edge reads as a coloured
fringe and an agreed one as black. Both sides go through
`stitchviz.render_design`, the Studio's lit-filament model, so what is
compared is what the product shows. Masks are taken FROM the renders
(thread pixel != fabric), so the diff masks and the picture agree by
construction. Spec §4.

    python tools/pro_parity/overlay.py --dir <out>/real/<slug>
    python tools/pro_parity/overlay.py --dir ... --crop 10 -5 40 15 --crop-name marine
    python tools/pro_parity/overlay.py --dir ... --by-thread
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true --against baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import pairframe as pf                                        # noqa: E402
from digitizer_core.stitchviz import render_design            # noqa: E402

WHITE = (255, 255, 255)
PRO_TINT = (255, 0, 255)      # RGB magenta
OURS_TINT = (0, 200, 255)     # RGB cyan
GHOST = 225                   # grey of the other side's silhouette on the *_only sheets
DEFAULT_PPM = 12.0
CROP_PPM = 36.0


def render_side(design: dict, frame: pf.Frame) -> np.ndarray:
    d = pf.pin_frame(design, frame.bounds_units)
    return render_design(d, px_per_mm=frame.ppm, fabric_bgr=WHITE, pad_mm=frame.pad_mm, lit=True)


def thread_mask(img: np.ndarray) -> np.ndarray:
    return np.any(img < 250, axis=2)


def tint(img: np.ndarray, rgb: tuple) -> np.ndarray:
    """Thread pixels take the tint, keeping the filament shading as a
    brightness ramp (0.35..1.0 of the tint); fabric stays white."""
    m = thread_mask(img)
    L = img.astype(np.float32).mean(axis=2) / 255.0
    out = np.full_like(img, 255)
    bgr = (rgb[2], rgb[1], rgb[0])
    for c in range(3):
        ch = out[..., c]
        ch[m] = np.clip(bgr[c] * (0.35 + 0.65 * L[m]), 0, 255).astype(np.uint8)
    return out


def _only_sheet(only: np.ndarray, other: np.ndarray, rgb: tuple) -> np.ndarray:
    out = np.full(only.shape + (3,), 255, np.uint8)
    out[other] = GHOST
    out[only] = (rgb[2], rgb[1], rgb[0])
    return out


def _restrict(design: dict, blocks: set | None) -> dict:
    """The design's stitches limited to the given block indices (colour
    records kept so colours still advance)."""
    if blocks is None:
        return design
    keep, bi = [], 0
    for s in design["stitches"]:
        if s["type"] == "color":
            bi += 1
            keep.append(s)
        elif s["type"] in ("jump", "trim", "end") or bi in blocks:
            keep.append(s)
    return dict(design, stitches=keep)


def render_pair(pair: pf.Pair, reg: pf.Reg, ppm: float = DEFAULT_PPM, crop_mm=None,
                only_pro_block: int | None = None, only_ours_blocks: set | None = None,
                ours_path: Path | None = None, ours_rgb: list | None = None) -> dict:
    pro_d = pf.design_for(pair.pro_path, None, pair.pro_rgb, f"{pair.slug} pro")
    ours_d = pf.design_for(ours_path or pair.ours_path, reg, ours_rgb or pair.ours_rgb, f"{pair.slug} ours")
    pro_d = _restrict(pro_d, {only_pro_block} if only_pro_block is not None else None)
    ours_d = _restrict(ours_d, only_ours_blocks)
    frame = pf.frame_for([pro_d, ours_d], ppm, crop_mm=crop_mm)
    pro = render_side(pro_d, frame)
    ours = render_side(ours_d, frame)
    pm, om = thread_mask(pro), thread_mask(ours)
    pt, ot = tint(pro, PRO_TINT), tint(ours, OURS_TINT)
    over = (pt.astype(np.float32) * ot.astype(np.float32) / 255.0).astype(np.uint8)
    return {"frame": frame, "pro": pro, "ours": ours, "pro_mask": pm, "ours_mask": om,
            "overlay": over, "pro_only": pm & ~om, "ours_only": om & ~pm,
            "pro_only_img": _only_sheet(pm & ~om, om, PRO_TINT),
            "ours_only_img": _only_sheet(om & ~pm, pm, OURS_TINT)}


def _titled(img: np.ndarray, title: str) -> np.ndarray:
    bar = np.full((22, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, title, (6, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def write_overlay_set(out_dir: Path, r: dict, title: str, suffix: str = "") -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        f"overlay{suffix}.png": _titled(r["overlay"], title),
        f"pro_only{suffix}.png": _titled(r["pro_only_img"], title + "  PRO ONLY"),
        f"ours_only{suffix}.png": _titled(r["ours_only_img"], title + "  OURS ONLY"),
        f"flicker_pro{suffix}.png": r["pro"],
        f"flicker_ours{suffix}.png": r["ours"],
    }
    written = []
    for name, img in files.items():
        p = out_dir / name
        cv2.imwrite(str(p), img)
        written.append(p)
    return written


def title_for(pair: pf.Pair, reg: pf.Reg, extra: str = "") -> str:
    return (f"{pair.slug} {pair.width_mm:.1f} mm  iou {reg.iou:.2f}  scale {reg.scale:.3f}"
            f"{'  flipY' if reg.flip_y else ''}{('  ' + extra) if extra else ''}")
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q`
Expected: `5 passed`. Open `<tmp>/ws/overlay/overlay.png` once by hand (`explorer <path>`) and confirm: magenta and cyan fringes only where the two designs differ, black where they coincide, the title bar legible.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/overlay.py digitizer/tests/test_pro_overlay.py
git commit -m "pro_parity/overlay: registered tinted overlay, pro-only/ours-only masks, flicker pair" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: `--crop` and `--by-thread`

**Files:**
- Modify: `digitizer/tools/pro_parity/overlay.py`
- Test: `digitizer/tests/test_pro_overlay.py` (append)

**Interfaces:**
- Produces: `crop_set(pair, reg, out_dir, crop_mm, name, ppm=CROP_PPM, **kw) -> list[Path]` (same five files with suffix `_crop_<name>`); `match_blocks(pro_rgb, ours_rgb, max_de=12.0) -> dict[int, list[int]]` (pro block → our blocks whose CIEDE2000 distance is within `max_de`, nearest first); `by_thread(pair, reg, out_dir, ppm=DEFAULT_PPM) -> list[Path]` writing `by_thread/<k>_<rrggbb>.png`, each an overlay of pro block k against its matched our blocks, title naming unmatched blocks.

- [ ] **Step 1: Write the failing tests**

```python
def test_crop_set_renders_the_window_at_36_ppm(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "cr", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    files = overlay.crop_set(pair, reg, d / "overlay", (0.0, -2.0, 10.0, 3.0), "arm")
    assert {p.name for p in files} == {"overlay_crop_arm.png", "pro_only_crop_arm.png",
                                       "ours_only_crop_arm.png", "flicker_pro_crop_arm.png",
                                       "flicker_ours_crop_arm.png"}
    img = cv2.imread(str(d / "overlay" / "flicker_pro_crop_arm.png"))
    assert abs(img.shape[1] - 10.0 * 36) <= 2 and abs(img.shape[0] - 5.0 * 36) <= 2


def test_match_blocks_by_ciede2000():
    m = overlay.match_blocks([(200, 30, 30), (30, 30, 200)], [(205, 28, 35), (20, 200, 20), (25, 35, 190)])
    assert m == {0: [0], 1: [2]}
    assert overlay.match_blocks([(0, 0, 0)], [(255, 255, 255)]) == {0: []}


def test_by_thread_writes_one_sheet_per_pro_block(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "bt", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    files = overlay.by_thread(pair, reg, d / "overlay")
    assert [p.name for p in files] == ["0_c81e1e.png", "1_1e1ec8.png"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q -k "crop or match_blocks or by_thread"`
Expected: `AttributeError: module 'overlay' has no attribute 'crop_set'`

- [ ] **Step 3: Implement**

Append to `overlay.py`:

```python
from skimage.color import deltaE_ciede2000                    # noqa: E402  (top of file)
from digitizer_core.threads import rgb_to_lab                 # noqa: E402  (top of file)


def crop_set(pair, reg, out_dir, crop_mm, name, ppm=CROP_PPM, **kw):
    r = render_pair(pair, reg, ppm=ppm, crop_mm=crop_mm, **kw)
    x0, y0, x1, y1 = crop_mm
    return write_overlay_set(out_dir, r, title_for(pair, reg, f"crop {x0:g},{y0:g}..{x1:g},{y1:g} mm"),
                             suffix=f"_crop_{name}")


def match_blocks(pro_rgb, ours_rgb, max_de: float = 12.0) -> dict:
    """pro block index -> our block indices within `max_de` CIEDE2000, nearest
    first. Chart-free: two RGBs straight to CIELAB, the module `threads.py`
    keeps as the one colour space."""
    if not pro_rgb or not ours_rgb:
        return {i: [] for i in range(len(pro_rgb))}
    pl = rgb_to_lab(np.array(pro_rgb, dtype=np.float64))
    ol = rgb_to_lab(np.array(ours_rgb, dtype=np.float64))
    out = {}
    for i in range(len(pro_rgb)):
        de = deltaE_ciede2000(np.repeat(pl[i:i + 1], len(ol), axis=0), ol)
        order = [int(j) for j in np.argsort(de) if de[j] <= max_de]
        out[i] = order
    return out


def by_thread(pair, reg, out_dir, ppm=DEFAULT_PPM) -> list:
    out_dir = Path(out_dir) / "by_thread"
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = match_blocks(pair.pro_rgb, pair.ours_rgb)
    written = []
    for k, rgb in enumerate(pair.pro_rgb):
        ours_blocks = set(matches.get(k, []))
        r = render_pair(pair, reg, ppm=ppm, only_pro_block=k,
                        only_ours_blocks=ours_blocks if ours_blocks else set())
        hexname = "%02x%02x%02x" % tuple(int(v) for v in rgb)
        extra = f"pro block {k} #{hexname} vs ours {sorted(ours_blocks) or 'NONE within 12 dE'}"
        p = out_dir / f"{k}_{hexname}.png"
        cv2.imwrite(str(p), _titled(r["overlay"], title_for(pair, reg, extra)))
        written.append(p)
    return written
```

The `frame_for(..., crop_mm=...)` path in `pairframe` gives the crop window in units with `pad_mm=0.0`, so the flicker image is `(x1-x0)*ppm` wide; `render_design` adds `max(8, int(...))` — the `±2 px` in the test covers rounding.

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/overlay.py digitizer/tests/test_pro_overlay.py
git commit -m "overlay: --crop windows at 36 px/mm and per-thread sheets matched by CIEDE2000" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: `--flag` re-digitize arms, `--against`, and the CLI

**Files:**
- Modify: `digitizer/tools/pro_parity/pairframe.py` (add `redigitize`)
- Modify: `digitizer/tools/pro_parity/overlay.py` (add `main`)
- Test: `digitizer/tests/test_pro_overlay.py` (append)

**Interfaces:**
- Produces:
  - `pairframe.redigitize(pair, flags: dict) -> Path` — runs `digitize(pair.art, prep_all.parity_config(pair.width_mm, pair.garment_id, **flags))`, writes `ours.dst` (`export.write_dst`), `ours_regions.json` (`prep_all.write_regions`), `ours_blocks.json` (`[{"block", "rgb"}]`) and `flags.json` under `flags_dir(pair, flags)`; returns that dir; skips the run when `ours.dst` already exists there (the cache).
  - `overlay.main(argv) -> int` — `--dir` or `--slug` (with `PRO_PARITY_OUT`), `--flag NAME[=VALUE]` (repeatable), `--against HASH|baseline`, `--crop x0 y0 x1 y1`, `--crop-name`, `--by-thread`, `--ppm`. Writes `<dir>/overlay/` (or `<flagdir>/overlay/`), prints the title line and the files written. With `--against`, the "pro" side is the named arm (`baseline` = the prep dir's own `ours.dst`) and the "ours" side the `--flag` arm, title says `OURS <a> vs OURS <b>`.

- [ ] **Step 1: Write the failing tests**

```python
def test_redigitize_writes_a_cached_arm(tmp_path, monkeypatch):
    """Uses a REAL fixture through the engine once (~5 s on the 400 px bar):
    the arm dir carries ours.dst + regions + flags.json and a second call
    does not re-run."""
    import shutil
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.export import write_dst
    art = HERE.parent / "testdata" / "logo_whitebg.png"
    d = tmp_path / "real" / "wb"
    d.mkdir(parents=True)
    _res, plan = digitize(art, PipelineConfig(target_width_mm=40.0))
    write_dst(plan, d / "ours.dst")
    shutil.copy(d / "ours.dst", d / "pro.dst")          # the pro is ours; only the arm matters here
    (d / "ours_regions.json").write_text("[]")
    (d / "ours_blocks.json").write_text("[]")
    (d / "pro_blocks.json").write_text("[]")
    shutil.copy(art, d / "art.png")
    (tmp_path / "real" / "manifest.json").write_text(json.dumps(
        [{"slug": "wb", "file": str(d / "pro.dst"), "garment_id": "left_chest"}]))
    pair = pairframe.load_pair(d)
    calls = []
    real = pairframe.digitize
    monkeypatch.setattr(pairframe, "digitize", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    arm = pairframe.redigitize(pair, {"curve_turn_deg": 0})
    assert (arm / "ours.dst").exists() and (arm / "ours_regions.json").exists()
    assert json.loads((arm / "flags.json").read_text()) == {"curve_turn_deg": 0}
    pairframe.redigitize(pair, {"curve_turn_deg": 0})
    assert len(calls) == 1
    arm_pair = pairframe.load_pair(arm)
    assert arm_pair.pro_path == pair.pro_path and arm_pair.ours_path == arm / "ours.dst"


def test_cli_writes_the_overlay_dir(tmp_path):
    ours = _design_blocks()
    d = synth.make_prep_dir(tmp_path, "cli", ours, ours, [], [(0, 0, 20, 12)], 20.0)
    assert overlay.main(["--dir", str(d)]) == 0
    assert (d / "overlay" / "overlay.png").exists()
    assert overlay.main(["--dir", str(d), "--crop", "0", "-2", "10", "3", "--crop-name", "arm"]) == 0
    assert (d / "overlay" / "overlay_crop_arm.png").exists()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q -k "redigitize or cli"`
Expected: `AttributeError ... redigitize` / `... main`

- [ ] **Step 3: Implement `redigitize` in `pairframe.py`**

Add imports near the top: `from digitizer_core import digitize`, `from digitizer_core.export import write_dst`, `import prep_all` (already importing `GREYS` from it — change to `import prep_all` and use `prep_all.GREYS`). Then:

```python
def redigitize(pair: Pair, flags: dict) -> Path:
    """Ours again, under `flags`, into `flags/<hash>/` beside the prep dir.
    Cached: an arm that already has `ours.dst` is not re-run — delete the
    directory to force it."""
    arm = flags_dir(pair, flags)
    if (arm / "ours.dst").exists():
        return arm
    arm.mkdir(parents=True, exist_ok=True)
    cfg = prep_all.parity_config(pair.width_mm, pair.garment_id, **flags)
    res, plan = digitize(pair.art, cfg)
    write_dst(plan, arm / "ours.dst")
    prep_all.write_regions(res, arm)
    (arm / "ours_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(b.rgb)} for i, b in enumerate(plan.blocks)], indent=1))
    (arm / "flags.json").write_text(json.dumps(flags, indent=1, default=str))
    return arm
```

- [ ] **Step 4: Implement `main` in `overlay.py`**

```python
from thin_strokes import parse_flags                          # noqa: E402  (top of file)


def _resolve_dir(a) -> Path:
    if a.dir:
        return Path(a.dir)
    import os
    out = os.environ.get("PRO_PARITY_OUT")
    if not (a.slug and out):
        raise SystemExit("--dir <out>/real/<slug>, or --slug with PRO_PARITY_OUT set")
    return Path(out) / "real" / a.slug


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir")
    ap.add_argument("--slug")
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--against", default=None,
                    help="overlay two of OUR arms: 'baseline' or a flags hash, against the --flag arm")
    ap.add_argument("--crop", type=float, nargs=4, default=None, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--crop-name", default="crop")
    ap.add_argument("--by-thread", action="store_true")
    ap.add_argument("--ppm", type=float, default=DEFAULT_PPM)
    a = ap.parse_args(argv)

    pair = pf.load_pair(_resolve_dir(a))
    flags = parse_flags(a.flag)
    suffix = ""
    if flags:
        arm = pf.redigitize(pair, flags)
        pair = pf.load_pair(arm)
        suffix = "_" + "_".join(f"{k}-{v}" for k, v in sorted(flags.items()))
    reg = pf.register_pair(pair.pro_path, pair.ours_path)
    out = pair.dir / "overlay"
    extra = ""
    kw = {}
    if a.against:
        base = pf.load_pair(pf._lane_root(pair.dir) / pair.slug) if a.against == "baseline" \
            else pf.load_pair(pf._lane_root(pair.dir) / pair.slug / "flags" / a.against)
        # the "pro" side becomes the other arm: register against it instead
        reg = pf.register_pair(base.ours_path, pair.ours_path)
        pair = pf.Pair(**{**pair.__dict__, "pro_path": base.ours_path, "pro_rgb": base.ours_rgb})
        extra = f"OURS {a.against} (magenta) vs OURS {suffix.strip('_') or 'baseline'} (cyan)"
    title = title_for(pair, reg, extra)
    print(title)
    written = []
    if a.crop:
        written += crop_set(pair, reg, out, tuple(a.crop), a.crop_name, ppm=CROP_PPM, **kw)
    else:
        r = render_pair(pair, reg, ppm=a.ppm, **kw)
        written += write_overlay_set(out, r, title, suffix=suffix)
        if a.by_thread:
            written += by_thread(pair, reg, out, ppm=a.ppm)
    (out / f"registration{suffix}.json").write_text(json.dumps(reg.as_dict(), indent=1))
    for p in written:
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q`
Expected: `10 passed` (the redigitize test takes a few seconds — note its time in the PR body).

- [ ] **Step 6: Commit**

```bash
git add digitizer/tools/pro_parity/pairframe.py digitizer/tools/pro_parity/overlay.py digitizer/tests/test_pro_overlay.py
git commit -m "overlay CLI: --flag arms re-digitized and cached, --against for ours-vs-ours, --crop, --by-thread" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Smoke on committed data (overlay half) and PR 2

**Files:**
- Test: `digitizer/tests/test_pro_overlay.py` (append, session fixture)

**Interfaces:**
- Produces: a session-scoped fixture `becker_pair(tmp_path_factory)` that builds `<tmp>/real/becker_smoke/` from `testdata/reference/becker_hat_polo_large_beckers_logolc.dst` (pro) and `testdata/becker_marine_logo.png` (art) by calling `prep_all.run_ours(art, width_mm, outdir, garment_id="left_chest")` ONCE and writing a manifest — reused by `test_pro_diff.py` via `conftest`? No: keep it in this file and import it from `test_pro_diff.py` (`from test_pro_overlay import becker_pair`), pytest resolves fixtures imported into a module.

- [ ] **Step 1: Write the fixture and the smoke test**

```python
@pytest.fixture(scope="session")
def becker_pair(tmp_path_factory):
    """The committed Becker pair, prepped once for the session (one engine
    run, ~45 s on Kent's machine on 2026-09-09). CI-runnable: no corpus."""
    import time
    import prep_all
    root = tmp_path_factory.mktemp("proloop") / "real"
    d = root / "becker_smoke"
    d.mkdir(parents=True)
    pro = HERE.parent / "testdata" / "reference" / "becker_hat_polo_large_beckers_logolc.dst"
    art = HERE.parent / "testdata" / "becker_marine_logo.png"
    blocks, breaks, threads, bounds, jumps, trims = prep_all.decode(pro)
    width = bounds[2] - bounds[0]
    (d / "pro_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(threads[i % len(threads)])} for i in range(len(blocks))]))
    import shutil
    shutil.copy(art, d / "art.png")
    t0 = time.time()
    prep_all.run_ours(d / "art.png", width, d, garment_id="left_chest")
    (root / "manifest.json").write_text(json.dumps(
        [{"slug": "becker_smoke", "file": str(pro), "garment_id": "left_chest",
          "pro": {"width_mm": width}, "ok": True, "seconds": round(time.time() - t0, 1)}]))
    return pairframe.load_pair(d)


def test_smoke_becker_overlay(becker_pair):
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    assert reg.iou > 0.5, reg
    assert 0.9 < reg.scale < 1.1
    files = overlay.write_overlay_set(becker_pair.dir / "overlay",
                                      overlay.render_pair(becker_pair, reg),
                                      overlay.title_for(becker_pair, reg))
    assert len(files) == 5 and all(p.stat().st_size > 1000 for p in files)
```

- [ ] **Step 2: Run it, and time it**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q --durations=3`
Expected: `11 passed`; the fixture's setup time printed. If the whole file exceeds 60 s, add the smoke test's node id to the CI deselect list in `.github/workflows/python-package-conda.yml` with a comment naming the measured time — measure, do not assume (spec §7 item 7).

- [ ] **Step 3: Look at the real overlay once**

Run: `cd digitizer && .venv/Scripts/python -c "import sys; sys.path[:0]=['tests','tools','tools/pro_parity']; ..."` is awkward — instead run the CLI on the fixture dir the test left behind (pytest prints the base temp dir with `--basetemp`): `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_overlay.py -q -k smoke --basetemp=../../.pytest_smoke` then `.venv/Scripts/python tools/pro_parity/overlay.py --dir ../../.pytest_smoke/proloop0/real/becker_smoke --by-thread` and open `overlay/overlay.png`. Confirm by eye: BECKER's outline registered (black), the pro's filled letter bodies magenta, MARINE's tatami cyan-over-magenta. Delete `.pytest_smoke` afterwards.

- [ ] **Step 4: Run the whole digitizer suite once, then open PR 2**

Run: `cd digitizer && .venv/Scripts/python -m pytest -q -n auto` (10–25 min). Expected: the three known goldens red on this machine and nothing else; collection ≥ 2,198 + the new tests.

Then from the worktree root:

```bash
git push -u origin claude/pro-overlay-loop
gh pr create --title "Pro overlay loop, PRs 1-2: harness fallback, pattern_to_design, pairframe, overlay.py" --body-file <(printf '%s\n' "Spec: docs/superpowers/specs/2026-09-09-pro-overlay-loop-design.md; plan: docs/superpowers/plans/2026-09-09-pro-overlay-loop.md, Tasks 1-9." "" "What: adapter.pattern_to_design (inverse of design_to_pattern); prep_both.ART_FALLBACK (committed logos when the Drive is not mounted); prep_all.parity_config/write_regions extracted; tools/pro_parity/pairframe.py (load, register: scale + flip search + shift); tools/pro_parity/overlay.py (tinted overlay, masks, flicker, crops, by-thread, --flag arms, --against)." "" "Measured: test file times, smoke fixture seconds, full-suite result (three known reds only)." "" "No engine change. Goldens untouched." "" "🤖 Generated with [Claude Code](https://claude.com/claude-code)')
```

(Write the body to a file first if process substitution is refused: `printf ... > /tmp/body.md; gh pr create --body-file /tmp/body.md`.) Mark ready-for-review and arm auto-merge while `mergeable_state` is `blocked` (CLAUDE.md).

---

### Task 10: `diff.py` — pass assignment and the per-region craft readers

**Files:**
- Create: `digitizer/tools/pro_parity/diff.py`
- Test: `digitizer/tests/test_pro_diff.py`

**Interfaces:**
- Consumes: `pairframe.*`, `satin_columns.measure/passes_from_file`, `row_pitch_union.union_pitch`, `census_pro._phases`, `scorecard.cell_stats/bounds`, `design_direction.doubled_mean`, `preflight._coverage_map`, `junction_blobs._Runs/coverage_in`, `stitches.StitchRun`, `shapely.affinity.affine_transform`, `shapely.contains_xy`.
- Produces:
  - `passes_of(path, transform=None) -> list[list[(x,y)]]` (file passes, transformed in mm).
  - `assign_passes(passes, polys: list[(shape_id, Polygon)], share=0.6, buffer_mm=0.3) -> (dict[shape_id, list[int]], list[int])` — pass index lists per region, and the residual (unassigned) pass indices. A pass goes to the region containing ≥ `share` of its points (polygon buffered by `buffer_mm`); ties to the larger share.
  - `tier_of(passes) -> str` — `"satin"` when `satin_columns.measure(passes)["share"] >= 0.5`, else `"fill"` when `union_pitch(segments(passes))` returns rows ≥ 3, else `"run"`; `"none"` for no passes.
  - `width_of(passes) -> (p50, p90)`, `pitch_of(passes) -> float | None`, `recipe_of(passes) -> str` (per pass `_phases` tokens joined by `.`, then passes joined by ` | `, capped at 6 passes with `…`), `direction_in(ang_map, bb, poly) -> (deg | None, R)`, `layers_in(grid, origin, poly) -> (p50, p95)`, `density_of(passes, area_mm2) -> float`, `trims_in(passes) -> int` (number of passes = lifts landing inside).
  - `region_rows(pair, reg) -> list[dict]` — one dict per region with `shape_id, area_mm2, tier_planned, pro: {...}, ours: {...}` where each side dict has `tier, width_p50, width_p90, direction_deg, direction_R, pitch_mm, recipe, layers_p50, layers_p95, density, stitches, trims`; plus `residual: {"pro_passes": n, "pro_mm": mm, "ours_passes": n, "ours_mm": mm}` returned alongside as the second element of a tuple `(rows, residual)`.

- [ ] **Step 1: Write the failing tests**

```python
# digitizer/tests/test_pro_diff.py
"""The catalogue: one set of readers, pointed at two files.

Spec §5. Tier is read by the same scale-free rule on both sides
(`satin_columns` share, then `union_pitch` rows); `study_pro.classify` is
never pointed at ours (its 0.7 mm floor).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "tools" / "pro_parity"))

import proloop_synth as synth                        # noqa: E402
import pairframe                                     # noqa: E402
import diff as pdiff                                 # noqa: E402
from test_pro_overlay import becker_pair             # noqa: E402,F401  (session fixture)


def _two_regions(ours_tier_b="satin", pro_tier_b="fill", width_b=2.0):
    """Region A: satin on both sides. Region B: satin ours, `pro_tier_b` pro."""
    a_ours = synth.satin_pass(0, 0, 20, 2.0)
    a_pro = synth.satin_pass(0, 0, 20, 2.0)
    b_ours = [synth.satin_pass(0, 10, 20, 2.0)] if ours_tier_b == "satin" else synth.fill_passes(0, 9, 20, 2.0)
    b_pro = [synth.satin_pass(0, 10, 20, width_b)] if pro_tier_b == "satin" else synth.fill_passes(0, 9, 20, 2.0)
    ours = [((0, 0, 0), [a_ours, *b_ours])]
    pro = [((0, 0, 0), [a_pro, *b_pro])]
    regions = [("A", "satin", box(-0.5, -1.5, 20.5, 1.5)), ("B", "satin", box(-0.5, 8.5, 20.5, 11.5))]
    return pro, ours, regions


def test_tier_disagreement_shows_on_one_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="fill")
    d = synth.make_prep_dir(tmp_path, "tier", pro, ours, regions, [(0, -1, 20, 1), (0, 9, 20, 11)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = pdiff.region_rows(pair, reg)
    by = {r["shape_id"]: r for r in rows}
    assert by["A"]["ours"]["tier"] == "satin" and by["A"]["pro"]["tier"] == "satin"
    assert by["B"]["ours"]["tier"] == "satin" and by["B"]["pro"]["tier"] == "fill"
    assert by["B"]["tier_planned"] == "satin"
    assert residual["pro_passes"] == 0 and residual["ours_passes"] == 0


def test_width_difference_is_a_width_row_not_a_tier_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="satin", width_b=2.6)
    d = synth.make_prep_dir(tmp_path, "width", pro, ours, regions, [(0, -1, 20, 1), (0, 9, 20, 11)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, _ = pdiff.region_rows(pair, reg)
    b = next(r for r in rows if r["shape_id"] == "B")
    assert b["ours"]["tier"] == b["pro"]["tier"] == "satin"
    assert abs(b["ours"]["width_p50"] - 2.0) < 0.15 and abs(b["pro"]["width_p50"] - 2.6) < 0.15


def test_readers_agree_between_plan_and_file(becker_pair):
    """`passes_from_file` on ours.dst measures what `passes_from_plan` would:
    the DST round trip does not move a column width (spec §7 test 6)."""
    from satin_columns import measure, passes_from_file
    from digitizer_core import PipelineConfig, digitize
    import prep_all
    cfg = prep_all.parity_config(becker_pair.width_mm, "left_chest")
    _res, plan = digitize(becker_pair.art, cfg)
    from satin_columns import passes_from_plan
    a = measure(passes_from_plan(plan))
    b = measure(passes_from_file(becker_pair.ours_path))
    assert abs(a["median_mm"] - b["median_mm"]) < 0.05
    assert abs(a["share"] - b["share"]) < 0.02
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py -q -k "tier or width"`
Expected: `ModuleNotFoundError: No module named 'diff'`

- [ ] **Step 3: Write `diff.py` (readers and `region_rows`)**

```python
# digitizer/tools/pro_parity/diff.py
"""The catalogue: what differs between our stitches and the pro's, per element.

One set of readers pointed at two machine files — `ours.dst` (written from
the plan by prep) and the pro's — in the frame `pairframe` registered. Per
our region: tier, column width, direction, row pitch, underlay recipe,
coverage layers, density, stitches, trims, each side beside the other. Then
design-level counts, then the SHAPE rows (Task 11), tagged so a dropped
element (ours), a pro's redesign (Kent's call) and sewn background (ours)
never share a bucket. No score anywhere: tolerances below are DISPLAY
thresholds that decide which rows sort first, and say so. Spec §5.

Tier is the same scale-free rule on both sides — `satin_columns`' crossing
share, then `row_pitch_union`'s rows — because `study_pro.classify` cannot
see a column under 0.7 mm and would call our hairline satin "other". Our
engine's INTENDED tier is `tier_planned`, from `ours_regions.json`.

    python tools/pro_parity/diff.py --dir <out>/real/<slug> [--flag NAME[=VALUE] ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.affinity import affine_transform
from shapely.geometry import Polygon
import shapely.wkt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import pairframe as pf                                                  # noqa: E402
import scorecard as sc                                                  # noqa: E402
from census_pro import _phases                                          # noqa: E402
from design_direction import doubled_mean                               # noqa: E402
from junction_blobs import _Runs, coverage_in                           # noqa: E402
from row_pitch_union import union_pitch                                 # noqa: E402
from satin_columns import measure as satin_measure, passes_from_file    # noqa: E402
from digitizer_core.preflight import _coverage_map                      # noqa: E402
from digitizer_core.stitches import StitchRun                           # noqa: E402

ASSIGN_SHARE = 0.6      # a pass belongs to the region holding this share of its points
ASSIGN_BUFFER_MM = 0.3  # pull comp + half a thread
LAYER_CELL_MM = 0.25
# Display thresholds — NOT a score. A row whose two sides differ by more than
# these sorts first in the catalogue; nothing is summed or weighted.
TOL_WIDTH_MM, TOL_WIDTH_FRAC = 0.3, 0.25
TOL_DIRECTION_DEG = 15.0
TOL_PITCH_FRAC = 0.25
TOL_LAYERS = 1.0


# ------------------------------------------------------------------ passes
def passes_of(path: Path, transform=None):
    passes = passes_from_file(Path(path))
    if transform is None:
        return passes
    return [[transform(x, y) for x, y in p] for p in passes]


def segments(passes):
    return [(p[i], p[i + 1]) for p in passes for i in range(len(p) - 1)]


def length_mm(passes) -> float:
    return sum(math.dist(p[i], p[i + 1]) for p in passes for i in range(len(p) - 1))


def region_polys(pair: pf.Pair, reg: pf.Reg):
    """Our region polygons in the PRO frame (mm y-down)."""
    out = []
    for r in pair.regions:
        poly = shapely.wkt.loads(r["wkt"])
        out.append((r["shape_id"], affine_transform(poly, reg.matrix())))
    return out


def assign_passes(passes, polys, share=ASSIGN_SHARE, buffer_mm=ASSIGN_BUFFER_MM):
    buffered = [(sid, poly.buffer(buffer_mm)) for sid, poly in polys]
    per = {sid: [] for sid, _ in polys}
    residual = []
    for i, pts in enumerate(passes):
        if not pts:
            continue
        xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
        best, best_share = None, 0.0
        for sid, poly in buffered:
            bx0, by0, bx1, by1 = poly.bounds
            if xs.max() < bx0 or xs.min() > bx1 or ys.max() < by0 or ys.min() > by1:
                continue
            inside = shapely.contains_xy(poly, xs, ys).mean()
            if inside > best_share:
                best, best_share = sid, float(inside)
        if best is not None and best_share >= share:
            per[best].append(i)
        else:
            residual.append(i)
    return per, residual


# ----------------------------------------------------------------- readers
def tier_of(passes) -> str:
    if not passes:
        return "none"
    m = satin_measure(passes)
    if m["share"] >= 0.5:
        return "satin"
    p = union_pitch(segments(passes))
    if p is not None and p["rows"] >= 3:
        return "fill"
    return "run"


def width_of(passes):
    m = satin_measure(passes) if passes else {"median_mm": None, "p90_mm": None}
    return m["median_mm"], m["p90_mm"]


def pitch_of(passes):
    p = union_pitch(segments(passes)) if passes else None
    return None if p is None else p["pitch_mm"]


def recipe_of(passes, cap: int = 6) -> str:
    toks = []
    for pts in passes[:cap]:
        toks.append(".".join(t for t, _n, _l in _phases(pts)))
    if len(passes) > cap:
        toks.append("…")
    return " | ".join(toks)


def direction_map(passes, bb):
    segs = [(a[0], a[1], b[0], b[1], math.dist(a, b), 0, False) for a, b in segments(passes)]
    ang, _typ, _tot = sc.cell_stats(segs, bb)
    return ang


def direction_in(ang_map, bb, poly):
    x0, y0, _x1, _y1 = bb
    vals = []
    H, W = ang_map.shape
    for i in range(H):
        for j in range(W):
            if np.isnan(ang_map[i, j]):
                continue
            cx, cy = x0 + (j + 0.5) * sc.CELL, y0 + (i + 0.5) * sc.CELL
            if poly.covers(shapely.geometry.Point(cx, cy)):
                vals.append(math.degrees(ang_map[i, j]) % 180.0)
    if not vals:
        return None, 0.0
    modal, r = doubled_mean(vals, [1.0] * len(vals))
    return (None if modal is None else round(modal, 1)), round(r, 3)


def coverage_grid(passes):
    runs = [StitchRun(points=list(p), kind="satin", shape_id="x") for p in passes if len(p) >= 2]
    return _coverage_map(_Runs(runs), cell_mm=LAYER_CELL_MM) if runs else None


def layers_in(grid_origin, poly):
    if grid_origin is None:
        return 0.0, 0.0
    grid, origin = grid_origin
    c = coverage_in(poly, grid, origin, LAYER_CELL_MM)
    return round(c["mean"], 2), round(c["p95"], 2)


def side_stats(passes, poly, ang_map, bb, cov):
    p50, p90 = width_of(passes)
    deg, r = direction_in(ang_map, bb, poly)
    l50, l95 = layers_in(cov, poly)
    area = max(poly.area, 1e-9)
    return {
        "tier": tier_of(passes),
        "width_p50": None if p50 is None else round(p50, 2),
        "width_p90": None if p90 is None else round(p90, 2),
        "direction_deg": deg, "direction_R": r,
        "pitch_mm": (None if pitch_of(passes) is None else round(pitch_of(passes), 3)),
        "recipe": recipe_of(passes),
        "layers_p50": l50, "layers_p95": l95,
        "density": round(length_mm(passes) / area, 2),
        "stitches": sum(len(p) for p in passes),
        "trims": len(passes),
    }


def region_rows(pair: pf.Pair, reg: pf.Reg):
    pro = passes_of(pair.pro_path)
    ours = passes_of(pair.ours_path, reg.apply_xy)
    polys = region_polys(pair, reg)
    pro_by, pro_res = assign_passes(pro, polys)
    our_by, our_res = assign_passes(ours, polys)
    allsegs = [(a[0], a[1], b[0], b[1], math.dist(a, b), 0, False) for a, b in segments(pro + ours)]
    bb = sc.bounds(allsegs)
    pro_ang = direction_map(pro, bb)
    our_ang = direction_map(ours, bb)
    pro_cov = coverage_grid(pro)
    our_cov = coverage_grid(ours)
    planned = {r["shape_id"]: r.get("tier") for r in pair.regions}
    rows = []
    for sid, poly in polys:
        pp = [pro[i] for i in pro_by[sid]]
        op = [ours[i] for i in our_by[sid]]
        rows.append({
            "shape_id": sid, "area_mm2": round(poly.area, 1), "tier_planned": planned.get(sid),
            "pro": side_stats(pp, poly, pro_ang, bb, pro_cov),
            "ours": side_stats(op, poly, our_ang, bb, our_cov),
        })
    residual = {"pro_passes": len(pro_res), "pro_mm": round(length_mm([pro[i] for i in pro_res]), 1),
                "ours_passes": len(our_res), "ours_mm": round(length_mm([ours[i] for i in our_res]), 1)}
    return rows, residual
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py -q`
Expected: `3 passed` (the third uses the session Becker fixture; it re-digitizes once more — about 45 s; if `median_mm` differs by more than 0.05, the DST quantisation to 0.1 mm is showing on hairline columns: loosen to 0.1 mm and record the measured difference in the test's docstring rather than in the tolerance alone).

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/diff.py digitizer/tests/test_pro_diff.py
git commit -m "pro_parity/diff: pass assignment and per-region craft readers on both files" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: Shape rows — the three tags from the ink split

**Files:**
- Modify: `digitizer/tools/pro_parity/diff.py`
- Test: `digitizer/tests/test_pro_diff.py` (append)

**Interfaces:**
- Consumes: `overlay.render_pair` masks and `Frame`, `pairframe.Reg`, `art.png`.
- Produces:
  - `ink_mask_in_frame(pair, reg, frame) -> np.ndarray[bool]` — the art's ink (alpha > 16 where alpha exists, else RGB sum < 720, the `real_art.prepare` rule) warped into the overlay frame: art px → ours mm (ink bbox onto our stitch extents, per axis), → pro mm (`reg.matrix()`), → frame px (`frame.mm_to_px_affine()`), composed as one 2×3 affine for `cv2.warpAffine` (nearest).
  - `shape_rows(pair, reg, r: dict, dust_mm2=2.0) -> list[dict]` — components of `pro_only & ink` → `dropped`, `pro_only & ~ink` → `redesign`, `ours_only & ~ink` → `background`, `ours_only & ink` → `redesign` (pro left art unsewn); each row `{tag, area_mm2, centre_mm: [x, y], nearest_region, crop: "--crop x0 y0 x1 y1"}`; components under `dust_mm2` summed into one `{tag, "dust": True, area_mm2, count}` row per tag.

- [ ] **Step 1: Write the failing test**

```python
import overlay                                       # noqa: E402  (beside `import diff as pdiff`)


def test_shape_tags_split_by_ink(tmp_path):
    """A pro-only bar over ink -> dropped; a pro-only bar over bare art ->
    redesign; an ours-only bar over bare art -> background."""
    common = synth.satin_pass(0, 0, 20, 2.0)
    pro = [((0, 0, 0), [common,
                        synth.satin_pass(0, 8, 10, 2.0),      # over ink: we dropped it
                        synth.satin_pass(0, 16, 10, 2.0)])]   # no ink: the pro added it
    ours = [((0, 0, 0), [common,
                         synth.satin_pass(0, 24, 10, 2.0)])]  # no ink: we sewed ground
    regions = [("A", "satin", box(-0.5, -1.5, 20.5, 1.5))]
    ink = [(0, -1, 20, 1), (0, 7, 10, 9)]
    d = synth.make_prep_dir(tmp_path, "tags", pro, ours, regions, ink, 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    r = overlay.render_pair(pair, reg)
    rows = pdiff.shape_rows(pair, reg, r)
    tags = sorted((x["tag"], round(x["centre_mm"][1])) for x in rows if not x.get("dust"))
    assert tags == [("background", 24), ("dropped", 8), ("redesign", 16)]
    for x in rows:
        if not x.get("dust"):
            assert 15 < x["area_mm2"] < 30 and x["nearest_region"] == "A" and x["crop"].startswith("--crop ")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py -q -k shape_tags`
Expected: `AttributeError: module 'diff' has no attribute 'shape_rows'`

- [ ] **Step 3: Implement**

Append to `diff.py`:

```python
import cv2                                            # noqa: E402  (top of file)
from PIL import Image                                 # noqa: E402  (top of file)


def _art_ink(pair: pf.Pair):
    im = Image.open(pair.art).convert("RGBA")
    a = np.asarray(im)
    alpha = a[..., 3]
    if alpha.min() < 255:
        ink = alpha > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    if not len(xs):
        return ink, (0, 0, ink.shape[1], ink.shape[0])
    return ink, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _ours_extent_mm(pair: pf.Pair):
    pts = [q for p in passes_from_file(pair.ours_path) for q in p]
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _compose(*mats):
    """2x3 affines, applied left to right, composed into one 2x3."""
    M = np.eye(3)
    for m in mats:
        m3 = np.vstack([np.asarray(m, dtype=np.float64), [0, 0, 1]])
        M = m3 @ M
    return M[:2]


def ink_mask_in_frame(pair: pf.Pair, reg: pf.Reg, frame: pf.Frame) -> np.ndarray:
    ink, (ix0, iy0, ix1, iy1) = _art_ink(pair)
    ox0, oy0, ox1, oy1 = _ours_extent_mm(pair)
    sx = (ox1 - ox0) / max(ix1 - ix0, 1)
    sy = (oy1 - oy0) / max(iy1 - iy0, 1)
    art_to_ours = np.array([[sx, 0.0, ox0 - ix0 * sx], [0.0, sy, oy0 - iy0 * sy]])
    a, b, d, e, xoff, yoff = reg.matrix()
    ours_to_pro = np.array([[a, b, xoff], [d, e, yoff]])
    M = _compose(art_to_ours, ours_to_pro, frame.mm_to_px_affine())
    W, H = frame.size
    warped = cv2.warpAffine(ink.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST, borderValue=0)
    return warped > 0


def _components(mask: np.ndarray, frame: pf.Frame, dust_mm2: float):
    n, lab, stats, cents = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    px_area = 1.0 / (frame.ppm ** 2)
    big, dust_area, dust_n = [], 0.0, 0
    for k in range(1, n):
        area = stats[k, cv2.CC_STAT_AREA] * px_area
        if area < dust_mm2:
            dust_area += area; dust_n += 1
            continue
        cx, cy = cents[k]
        X = cx / frame.ppm + frame.x0_units / 10.0 - frame.pad_mm
        Y = cy / frame.ppm - frame.y1_units / 10.0 - frame.pad_mm
        x, y, w, h = stats[k, cv2.CC_STAT_LEFT], stats[k, cv2.CC_STAT_TOP], stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT]
        bx0 = x / frame.ppm + frame.x0_units / 10.0 - frame.pad_mm
        by0 = y / frame.ppm - frame.y1_units / 10.0 - frame.pad_mm
        big.append({"area_mm2": round(area, 1), "centre_mm": [round(X, 1), round(Y, 1)],
                    "bbox_mm": [round(bx0, 1), round(by0, 1), round(bx0 + w / frame.ppm, 1), round(by0 + h / frame.ppm, 1)]})
    return big, dust_area, dust_n


def shape_rows(pair: pf.Pair, reg: pf.Reg, r: dict, dust_mm2: float = 2.0) -> list:
    frame = r["frame"]
    ink = ink_mask_in_frame(pair, reg, frame)
    polys = region_polys(pair, reg)
    buckets = [("dropped", r["pro_only"] & ink), ("redesign", r["pro_only"] & ~ink),
               ("background", r["ours_only"] & ~ink), ("redesign", r["ours_only"] & ink)]
    rows = []
    for tag, mask in buckets:
        big, dust_area, dust_n = _components(mask, frame, dust_mm2)
        for c in big:
            pt = shapely.geometry.Point(c["centre_mm"])
            nearest = min(polys, key=lambda sp: sp[1].distance(pt))[0] if polys else None
            x0, y0, x1, y1 = c["bbox_mm"]
            m = 1.0
            rows.append({"tag": tag, **c, "nearest_region": nearest,
                         "crop": f"--crop {x0 - m:.1f} {y0 - m:.1f} {x1 + m:.1f} {y1 + m:.1f}"})
        if dust_n:
            rows.append({"tag": tag, "dust": True, "area_mm2": round(dust_area, 1), "count": dust_n})
    rows.sort(key=lambda x: (x.get("dust", False), -x["area_mm2"]))
    return rows
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py -q -k shape_tags`
Expected: `1 passed`. If a tag lands wrong, print `ink.sum()` and the three masks' sums from the test: the usual cause is the art→ours affine's y (art rows increase downward; ours mm y-down; both agree, no flip in that leg).

- [ ] **Step 5: Commit**

```bash
git add digitizer/tools/pro_parity/diff.py digitizer/tests/test_pro_diff.py
git commit -m "diff: shape rows split by the art's ink — dropped / redesign / background" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: Flagging, `catalogue.md`, `diff.json`, the CLI, and the diff smoke

**Files:**
- Modify: `digitizer/tools/pro_parity/diff.py`
- Test: `digitizer/tests/test_pro_diff.py` (append)

**Interfaces:**
- Produces:
  - `flag_row(row) -> list[str]` — the columns on which the two sides differ past the display thresholds: `tier` (differs and neither is `none`), `width` (both present and `|Δ| > TOL_WIDTH_MM and > TOL_WIDTH_FRAC·pro`), `direction` (both present, angular distance mod 180 > `TOL_DIRECTION_DEG`, and both `R ≥ 0.5`), `pitch` (both present, `|Δ| > TOL_PITCH_FRAC·pro`), `layers` (`|Δp50| > TOL_LAYERS`). Density is never flagged.
  - `design_rows(pair, reg, pro_passes, our_passes) -> dict` — `{stitches, trims (= passes), blocks, cones (distinct rgb), sew_order}` per side; `sew_order` is the block sequence with the region holding most of each block's thread.
  - `write_catalogue(pair, reg, rows, residual, design, shapes, out_dir) -> (Path, Path)` writing `catalogue.md` and `diff.json`; the markdown has: title with `iou`/`scale`/`flip`; **Flagged** table (rows with any flag, most flags first, then area); **All regions** table; **Design**; **Residual**; **Shape rows — Kent's call** (`redesign`) and **Shape rows — ours** (`dropped`, `background`).
  - `main(argv) -> int` — `--dir/--slug`, `--flag`, `--ppm`; prints one line per flagged row: `slug  S<id>  tier: ours satin / pro fill  width: 2.0 / 2.6`.

- [ ] **Step 1: Write the failing tests**

```python
def test_flag_row_rules():
    row = {"shape_id": "X", "pro": {"tier": "satin", "width_p50": 2.6, "direction_deg": 20.0, "direction_R": 0.9,
                                    "pitch_mm": None, "layers_p50": 1.1},
           "ours": {"tier": "satin", "width_p50": 2.0, "direction_deg": 22.0, "direction_R": 0.9,
                    "pitch_mm": None, "layers_p50": 1.0}}
    assert pdiff.flag_row(row) == ["width"]
    row["ours"]["tier"] = "fill"
    row["ours"]["direction_deg"] = 80.0
    assert pdiff.flag_row(row) == ["tier", "width", "direction"]
    row["pro"]["tier"] = "none"
    assert "tier" not in pdiff.flag_row(row)


def test_catalogue_and_json_written(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="fill")
    d = synth.make_prep_dir(tmp_path, "cat", pro, ours, regions, [(0, -1, 20, 1), (0, 9, 20, 11)], 20.0)
    assert pdiff.main(["--dir", str(d)]) == 0
    md = (d / "catalogue.md").read_text(encoding="utf-8")
    js = json.loads((d / "diff.json").read_text())
    assert "## Flagged" in md and "| B |" in md and "Kent's call" in md
    assert js["registration"]["iou"] > 0.9
    assert [r["shape_id"] for r in js["flagged"]] == ["B"]
    assert js["flagged"][0]["flags"] == ["tier"]


def test_smoke_becker_diff(becker_pair):
    reg = pairframe.register_pair(becker_pair.pro_path, becker_pair.ours_path)
    rows, residual = pdiff.region_rows(becker_pair, reg)
    assert len(rows) == len(becker_pair.regions) > 5
    r = overlay.render_pair(becker_pair, reg)
    shapes = pdiff.shape_rows(becker_pair, reg, r)
    md, js = pdiff.write_catalogue(becker_pair, reg, rows, residual,
                                   pdiff.design_rows(becker_pair, reg), shapes, becker_pair.dir)
    assert md.exists() and js.exists()
    tags = {s["tag"] for s in shapes}
    assert "redesign" in tags        # BECKER's filled bodies (spec §8)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py -q -k "flag_row or catalogue"`
Expected: `AttributeError ... flag_row`

- [ ] **Step 3: Implement**

Append to `diff.py`:

```python
def _ang_dist(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def flag_row(row: dict) -> list:
    p, o = row["pro"], row["ours"]
    flags = []
    if p["tier"] != o["tier"] and "none" not in (p["tier"], o["tier"]):
        flags.append("tier")
    if p.get("width_p50") is not None and o.get("width_p50") is not None:
        d = abs(p["width_p50"] - o["width_p50"])
        if d > TOL_WIDTH_MM and d > TOL_WIDTH_FRAC * p["width_p50"]:
            flags.append("width")
    if (p.get("direction_deg") is not None and o.get("direction_deg") is not None
            and p.get("direction_R", 0) >= 0.5 and o.get("direction_R", 0) >= 0.5
            and _ang_dist(p["direction_deg"], o["direction_deg"]) > TOL_DIRECTION_DEG):
        flags.append("direction")
    if p.get("pitch_mm") is not None and o.get("pitch_mm") is not None:
        if abs(p["pitch_mm"] - o["pitch_mm"]) > TOL_PITCH_FRAC * p["pitch_mm"]:
            flags.append("pitch")
    if abs(p.get("layers_p50", 0) - o.get("layers_p50", 0)) > TOL_LAYERS:
        flags.append("layers")
    return flags


def _blocks_of(path: Path, transform=None):
    """Passes per colour block of a machine file, same split rule as passes_of."""
    import pystitch
    pat = pystitch.read(str(path))
    blocks, cur, bi = {}, [], 0
    rgb = [(t.get_red(), t.get_green(), t.get_blue()) for t in pat.threadlist]
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            p = (x / 10.0, y / 10.0)
            cur.append(transform(*p) if transform else p)
            continue
        if len(cur) >= 3:
            blocks.setdefault(bi, []).append(cur)
        cur = []
        if cmd in (pystitch.COLOR_CHANGE, pystitch.STOP):
            bi += 1
    if len(cur) >= 3:
        blocks.setdefault(bi, []).append(cur)
    return blocks, rgb


def design_rows(pair: pf.Pair, reg: pf.Reg) -> dict:
    polys = region_polys(pair, reg)
    out = {}
    for side, path, tr, rgbs in (("pro", pair.pro_path, None, pair.pro_rgb),
                                 ("ours", pair.ours_path, reg.apply_xy, pair.ours_rgb)):
        blocks, file_rgb = _blocks_of(path, tr)
        rgb = rgbs or file_rgb
        order = []
        for bi in sorted(blocks):
            per, _res = assign_passes(blocks[bi], polys)
            top = max(per.items(), key=lambda kv: length_mm([blocks[bi][i] for i in kv[1]]), default=(None, []))
            order.append({"block": bi, "rgb": list(rgb[bi]) if bi < len(rgb) else None,
                          "mm": round(length_mm(blocks[bi]), 1), "mostly": top[0]})
        passes = [p for b in blocks.values() for p in b]
        out[side] = {"stitches": sum(len(p) for p in passes), "trims": len(passes),
                     "blocks": len(blocks), "cones": len({tuple(r) for r in rgb[:max(len(blocks), 1)]}),
                     "sew_order": order}
    return out


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _row_line(row, flags):
    p, o = row["pro"], row["ours"]
    cells = [row["shape_id"], _fmt(row["area_mm2"]), ",".join(flags) or "",
             f"{o['tier']} / {p['tier']}" + (f" (planned {row['tier_planned']})" if row.get("tier_planned") else ""),
             f"{_fmt(o['width_p50'])} / {_fmt(p['width_p50'])}",
             f"{_fmt(o['direction_deg'])} / {_fmt(p['direction_deg'])}",
             f"{_fmt(o['pitch_mm'])} / {_fmt(p['pitch_mm'])}",
             f"{_fmt(o['layers_p50'])} / {_fmt(p['layers_p50'])}",
             f"{_fmt(o['density'])} / {_fmt(p['density'])}",
             f"{o['trims']} / {p['trims']}",
             f"`{o['recipe'][:40]}` / `{p['recipe'][:40]}`"]
    return "| " + " | ".join(cells) + " |"


_HEAD = ("| region | mm² | flags | tier ours / pro | width p50 | direction | pitch | layers | density | trims | recipe |\n"
         "|---|---:|---|---|---|---|---|---|---|---|---|")


def write_catalogue(pair, reg, rows, residual, design, shapes, out_dir):
    out_dir = Path(out_dir)
    flagged = [(r, flag_row(r)) for r in rows]
    flagged = [(r, f) for r, f in flagged if f]
    flagged.sort(key=lambda rf: (-len(rf[1]), -rf[0]["area_mm2"]))
    lines = [f"# {pair.slug} — ours vs pro, {pair.width_mm:.1f} mm",
             f"registration iou {reg.iou:.3f}, scale {reg.scale:.3f}, flip_y {reg.flip_y}, "
             f"shift ({reg.dx:.1f}, {reg.dy:.1f}) mm. Tolerances are display thresholds, not a score.", ""]
    if reg.iou < 0.5:
        lines += ["**Registration is unreliable (iou < 0.5): read the shape rows as indicative only.**", ""]
    lines += ["## Flagged", "", _HEAD] + [_row_line(r, f) for r, f in flagged] + [""]
    lines += ["## All regions", "", _HEAD] + [_row_line(r, flag_row(r)) for r in rows] + [""]
    lines += ["## Design", "", "| | ours | pro |", "|---|---:|---:|"]
    for k in ("stitches", "trims", "blocks", "cones"):
        lines.append(f"| {k} | {design['ours'][k]} | {design['pro'][k]} |")
    lines += ["", "sew order ours: " + " → ".join(f"{b['block']}({b['mostly']})" for b in design["ours"]["sew_order"]),
              "sew order pro: " + " → ".join(f"{b['block']}({b['mostly']})" for b in design["pro"]["sew_order"]), ""]
    lines += ["## Residual (passes assigned to no region)", "",
              f"pro {residual['pro_passes']} passes / {residual['pro_mm']} mm; "
              f"ours {residual['ours_passes']} passes / {residual['ours_mm']} mm", ""]
    kent = [s for s in shapes if s["tag"] == "redesign"]
    ours_rows = [s for s in shapes if s["tag"] in ("dropped", "background")]
    def shape_table(items):
        t = ["| tag | mm² | centre | nearest region | crop |", "|---|---:|---|---|---|"]
        for s in items:
            if s.get("dust"):
                t.append(f"| {s['tag']} (dust) | {s['area_mm2']} | {s['count']} pieces | | |")
            else:
                t.append(f"| {s['tag']} | {s['area_mm2']} | {s['centre_mm']} | {s['nearest_region']} | `{s['crop']}` |")
        return t
    lines += ["## Shape rows — Kent's call (the pro departed from the artwork)", ""] + shape_table(kent) + [""]
    lines += ["## Shape rows — ours (dropped elements, sewn background)", ""] + shape_table(ours_rows) + [""]
    md = out_dir / "catalogue.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    js = out_dir / "diff.json"
    js.write_text(json.dumps({"slug": pair.slug, "width_mm": pair.width_mm, "registration": reg.as_dict(),
                              "flagged": [dict(r, flags=f) for r, f in flagged], "regions": rows,
                              "residual": residual, "design": design, "shapes": shapes}, indent=1, default=str))
    return md, js


def main(argv=None) -> int:
    import overlay
    from thin_strokes import parse_flags
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir")
    ap.add_argument("--slug")
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--ppm", type=float, default=overlay.DEFAULT_PPM)
    a = ap.parse_args(argv)
    pair = pf.load_pair(overlay._resolve_dir(a))
    flags = parse_flags(a.flag)
    if flags:
        pair = pf.load_pair(pf.redigitize(pair, flags))
    reg = pf.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = region_rows(pair, reg)
    r = overlay.render_pair(pair, reg, ppm=a.ppm)
    shapes = shape_rows(pair, reg, r)
    md, js = write_catalogue(pair, reg, rows, residual, design_rows(pair, reg), shapes, pair.dir)
    print(f"{pair.slug}  iou {reg.iou:.2f}  scale {reg.scale:.3f}  → {md}")
    for row in rows:
        f = flag_row(row)
        if f:
            p, o = row["pro"], row["ours"]
            bits = []
            if "tier" in f: bits.append(f"tier: ours {o['tier']} / pro {p['tier']}")
            if "width" in f: bits.append(f"width: {_fmt(o['width_p50'])} / {_fmt(p['width_p50'])}")
            if "direction" in f: bits.append(f"direction: {_fmt(o['direction_deg'])} / {_fmt(p['direction_deg'])}")
            if "pitch" in f: bits.append(f"pitch: {_fmt(o['pitch_mm'])} / {_fmt(p['pitch_mm'])}")
            if "layers" in f: bits.append(f"layers: {_fmt(o['layers_p50'])} / {_fmt(p['layers_p50'])}")
            print(f"  {row['shape_id']:>12}  " + "   ".join(bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_pro_diff.py tests/test_pro_overlay.py -q --durations=5`
Expected: all pass; note the durations. Open the Becker smoke `catalogue.md` once and read the Flagged table against spec §8's expectations (MARINE rows `tier: ours fill / pro satin`; a `redesign` shape row at BECKER's letter bodies).

- [ ] **Step 5: Full suite, then PR 3**

Run: `cd digitizer && .venv/Scripts/python -m pytest -q -n auto`. Expected: the three known reds only.

```bash
git add digitizer/tools/pro_parity/diff.py digitizer/tests/test_pro_diff.py
git commit -m "diff: flagged rows, design rows, catalogue.md + diff.json, CLI; Becker smoke" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push
```

Open PR 3 the way PR 2 was opened (title `Pro overlay loop, PR 3: diff.py — the craft/shape catalogue`), body naming the spec, plan Tasks 10–12, the measured test times and the full-suite result. Ready-for-review, auto-merge armed.

---

### Task 13: The first run — three designs, renders, the doc, the status lines

**Files:**
- Create: `docs/pro-overlay-first-run-<date>.md`, `docs/renders/pro-overlay-<date>/` (the `overlay.png`, `pro_only.png`, `ours_only.png` and any crops per design; not the prep dirs)
- Modify: `MASTER_SCOPE.md` ("Evaluation corpus & harness" cross-cutting entry, one paragraph; stay under the 800-line budget — `python tools/scope_budget.py` says where to reclaim), `DOCTRINE.md` (one entry: the three-tag rule and why density is never flagged), `COOKBOOK.md` (a "Running things" pointer: the three commands), `.claude/memory/MEMORY.md` (one index line) + a memory file for the run's findings.

- [ ] **Step 1: Prep the three designs in a pinned worktree**

From the worktree root (this lane, at its current commit — record the SHA):

```bash
git rev-parse --short HEAD
```

Then, in PowerShell or bash, with `C` a scratch corpus root that holds `scratch_kent/Embroidery Files`' contents (the pro files; the art now resolves through `ART_FALLBACK`):

```bash
cd digitizer
PRO_PARITY_ROOT="C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/scratch_kent/Embroidery Files" PRO_PARITY_OUT="C:/Users/EE-LT-11030/AppData/Local/Temp/claude/proloop-firstrun" .venv/Scripts/python tools/pro_parity/prep_both.py becker_lc_large becker_hat_large hotel_fremont_patch
```

Expected: `3/3 designs prepped, both lanes`; ~45 s, ~45 s, ~175 s (2026-09-09 measurements).

- [ ] **Step 2: Overlay and diff each**

```bash
for s in becker_lc_large becker_hat_large hotel_fremont_patch; do .venv/Scripts/python tools/pro_parity/overlay.py --dir "C:/Users/EE-LT-11030/AppData/Local/Temp/claude/proloop-firstrun/real/$s" --by-thread; .venv/Scripts/python tools/pro_parity/diff.py --dir "C:/Users/EE-LT-11030/AppData/Local/Temp/claude/proloop-firstrun/real/$s"; done
```

Read each `catalogue.md`. For every flagged row that names a letter or element Kent has reviewed before (MARINE, the BECKER outline, Fremont's THE / EST 1895 / tagline / rope), make a crop with the row's own `--crop` line and `--crop-name <element>`.

- [ ] **Step 3: Write the first-run doc**

`docs/pro-overlay-first-run-<date>.md`, in this shape (no ranking, no score):

```markdown
# Pro overlay loop — first run (<date>)

Engine: `claude/pro-overlay-loop` at `<sha>` (origin/main `<sha>` + this lane). Prep: real lane, `prep_both.py <slugs>`, corpus root `scratch_kent/Embroidery Files`, art via `ART_FALLBACK`. Commands at the bottom.

## Becker LC large — 95.7 mm, left_chest
registration iou <x>, scale <x>, flip <bool>. Sheet: `docs/renders/pro-overlay-<date>/becker_lc_large_overlay.png`.

### Flagged craft rows
<the Flagged table, verbatim from catalogue.md>

### Shape rows — Kent's call
<the redesign rows>

### Shape rows — ours
<dropped / background rows>

## Becker hat large — 101.9 mm, hat_front
...
## Hotel Fremont patch — 92.5 mm, patch
...

## Against the record
One line per spec §8 expectation: confirmed / refuted / not visible, with the row that says so.

## Commands
<the exact prep/overlay/diff lines>
```

Copy `overlay.png`, `pro_only.png`, `ours_only.png`, `by_thread/*.png` and every crop into `docs/renders/pro-overlay-<date>/<slug>_<name>.png`. Keep the total under ~10 MB (the 09-09 render dirs are the precedent).

- [ ] **Step 4: Status lines**

- `MASTER_SCOPE.md` → "Evaluation corpus & harness": one paragraph — the loop exists, the three commands, the three designs' iou, and that it emits no score; `(measured <date> — docs/pro-overlay-first-run-<date>.md)`. Run `cd digitizer && .venv/Scripts/python tools/scope_budget.py` and `python -m pytest tests/test_scope_budget.py -q`.
- `DOCTRINE.md` → one entry under the standing rulings: the three-tag rule (`dropped` / `background` are ours, `redesign` is Kent's) and "density is reported, never flagged — `FILL_ROW_MM` is ruled".
- `COOKBOOK.md` → "Running things": the three commands and the `ART_FALLBACK` note.
- Memory: `.claude/memory/pro-overlay-first-run-<date>.md` (what the first three catalogues said, in five bullets) and its index line in `MEMORY.md` (under 200 characters).

- [ ] **Step 5: Verify docs, commit, PR 4**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_scope_budget.py tests/test_doc_paths.py -q` (whichever doc-path checker the repo has — `tools/doc_claims.py` if no test) — the new doc's paths must resolve.

```bash
git add docs/pro-overlay-first-run-*.md docs/renders/pro-overlay-*/ MASTER_SCOPE.md DOCTRINE.md COOKBOOK.md .claude/memory/
git commit -m "Pro overlay loop: first run on Becker LC, Becker hat, Fremont patch — catalogues, sheets, status" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
git push
```

Open PR 4 (title `Pro overlay loop, PR 4: first run — three catalogues and sheets`), body listing per design the flagged craft rows in one line each and the `redesign` rows under "Kent's call". Ready-for-review, auto-merge armed. Then end the turn with `AskUserQuestion` putting the flagged craft rows to Kent as the options for the first mechanism to build — with, per option, the row's two values, the mechanism that already exists behind a flag if one does (`cfg.wide_columns`, `cfg.design_angle`, `cfg.satin_per_stroke`, `cfg.keep_thin_strokes`, `cfg.lettering_min_column_mm`), and its gate.

---

## Self-review

**Spec coverage.** §1 goal → Tasks 5–13. §2 inputs + `ART_FALLBACK` + Bridge Bar note → Task 2 (Bridge Bar: no task, by design — `pull-corpus` when its turn comes). §3 registration (uniform scale, flip search, shift, iou on every output, iou < 0.5 warning) → Task 5 + Task 12's catalogue header. §4 overlay files, tints, multiply, crops, by-thread, `--flag`, `--against` → Tasks 6–8. §5 readers on both files, per-region columns, tolerances, design rows, three-tag shape rows, dust, outputs, stdout → Tasks 10–12. The spec's wording "our tier comes from the plan" is met by `tier_planned`; the comparable `tier` column uses one scale-free rule on both sides (Global Constraints) — a deliberate refinement, stated in `diff.py`'s docstring. §6 loop → the CLIs. §7 tests 1–8 → Task 5 (1, 2), Task 10 (3, 4, 6), Task 11 (5), Task 9 + 12 (7), Task 2 (8). §8 first run → Task 13. §9 risks: Gaulke/iou → Task 12 header; residual reported → Task 10; runtime → cached arms (Task 8).

**Placeholders.** `<date>`/`<sha>` in Task 13 are values the executor fills from the run itself, not unknowns. No "TBD"/"similar to".

**Type consistency.** `Reg.apply_xy(x, y)` and `reg.matrix()` used in Tasks 6, 10, 11, 12 match Task 5. `render_pair` returns the keys Tasks 11–12 read (`frame`, `pro_only`, `ours_only`, masks). `pairframe.Frame.mm_to_px_affine()`/`size`/`x0_units`/`y1_units`/`pad_mm`/`ppm` used in Task 11 match Task 5. `passes_from_file` returns lists of `(x, y)` tuples in mm — `passes_of` transforms them with `reg.apply_xy`. `prep_all.parity_config(width_mm, garment_id, **extra)` and `write_regions(res, outdir)` (Task 3) are what `redigitize` (Task 8) and the tests call. `overlay._resolve_dir` is reused by `diff.main` (Task 12) — it is module-level in Task 8. `pairframe.load_pair` accepts an arm dir (`flags/<hash>`) — `_lane_root`/`_slug` (Task 5) handle it, and the arm dir contains `ours.dst`, `ours_regions.json`, `ours_blocks.json` (Task 8).
