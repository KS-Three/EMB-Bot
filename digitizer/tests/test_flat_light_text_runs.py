"""`cfg.flat_light_text_runs` (built OFF 2026-11-07 as a `cfg.extra` key; ON
since that day, Kent's flip "Flat light-text runs", a field now): the gradient
lane's dark-ink carve, run on the flat lane.

`stage0_scale_relative_grad` (ON, #1301) sends Fremont hat flat, and its tan
tagline stopped reading (native word cc 0.903 -> 0.605,
`docs/goldentee-flat-regress-2026-11-07.md`). On the gradient lane the
lightness read (`thin_ink.find_dark_thin_ink`) found the tan strokes, the carve
(`absorbed_dark_ink`) gave them a label block of their own, the pipeline tagged
them `dark_ink`, and `bean_dark_ink` sewed each one as a run along its
skeleton. The flat lane had no such step. ON runs the same read and carve on
the flat quantiser's labels (`thin_ink.carve_flat_dark_ink`).

Contracts:
  * the flag is a field, ON by default and False in PRE_FLIP, gated to the
    flat class;
  * OFF: the flat goldens are byte for byte what they were;
  * a stroke that owns at least half its k-means cluster keeps its label (the
    carve's own survival rule); a nothing-found read returns `q` itself;
  * end to end on a light-ink tagline on a white field: OFF tags nothing
    `dark_ink`; ON tags the letters, gives them bean spines, and every one
    sews run stitches only, none lost.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig, digitize
from digitizer_core.beanletters import BEAN_LETTER_KEY
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stage2_quantize import Quant
from digitizer_core.thin_ink import carve_flat_dark_ink

from .conftest import ENGINE_2026_10_27, FLAT_GOLDEN_MD5, PRE_FLIP, TESTDATA

FLAG = "flat_light_text_runs"
TAN = (196, 168, 120)        # a light tan ink, the tagline's kind of colour


def test_the_flag_is_a_field_and_is_on():
    """Kent's flip 2026-11-07: a field defaulting True; the OFF arm is pinned
    in PRE_FLIP and the dated engine snapshot."""
    assert PipelineConfig().flat_light_text_runs is True
    assert FLAG not in PipelineConfig().extra
    assert PRE_FLIP[FLAG] is False and ENGINE_2026_10_27[FLAG] is False
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert f"and cfg.{FLAG})" in src
    assert 'classification.class_ == "flat" and cfg.keep_dark_thin_strokes' in src


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(FLAT_GOLDEN_MD5))
def test_goldens_are_byte_identical_off(fixture):
    """OFF is the engine as it was. The golden rides the live defaults
    (`test_pins_are_frozen`'s rule 1 exception), so this does too."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == FLAT_GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            sew_enclosed_white=False, flat_light_text_runs=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == FLAT_GOLDEN_MD5[fixture]


def _tagline(path: Path) -> None:
    """A navy page (the background), a white field on it, a black bar (the
    wordmark's ink) and a light tan tagline in a 1 px Hershey pen: eight
    letters of one ink, so k-means gives them one cluster shared with a tan
    rule under them, and no letter owns half of it."""
    h, w = 360, 720
    img = np.full((h, w, 3), (20, 30, 70), np.uint8)
    cv2.rectangle(img, (20, 20), (w - 21, h - 21), (255, 255, 255), -1)
    cv2.rectangle(img, (60, 50), (w - 61, 130), (0, 0, 0), -1)
    cv2.putText(img, "EAT STAY", (150, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.6, TAN, 1, cv2.LINE_AA)
    cv2.rectangle(img, (60, 280), (w - 61, 300), TAN, -1)
    cv2.imwrite(str(path), img[..., ::-1])


def _cfg(on: bool) -> PipelineConfig:
    return PipelineConfig(target_width_mm=90.0, max_colors=6, forced_class="flat",
                          edge_cap="none", flat_light_text_runs=on)


def test_off_the_tagline_is_no_dark_ink(tmp_path):
    art = tmp_path / "tagline.png"
    _tagline(art)
    result = run_stages(str(art), _cfg(False))
    assert not [r for r in result.regions if r.meta.get("dark_ink")]


def test_on_the_tagline_letters_are_dark_ink_and_sew_runs(tmp_path):
    art = tmp_path / "tagline.png"
    _tagline(art)
    cfg = _cfg(True)
    result = run_stages(str(art), cfg)
    letters = [r for r in result.regions if r.meta.get("dark_ink")]
    assert len(letters) >= 6, [r.area_mm2 for r in letters]
    beaned = [r for r in letters if r.meta.get(BEAN_LETTER_KEY)]
    assert len(beaned) >= 6
    plan = plan_stitches(result, cfg)
    lost = {i for wn in plan.warnings if wn.get("code") == "SHAPE_NOT_STITCHED"
            for i in wn.get("ids", ())}
    ids = {r.shape_id for r in beaned}
    assert not lost & ids
    kinds: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id in ids:
            kinds.setdefault(run.shape_id, set()).add(run.kind)
    for r in beaned:
        assert kinds.get(r.shape_id), f"{r.shape_id} sewed nothing"
        assert kinds[r.shape_id] <= {"run", "travel"}, (r.shape_id, kinds[r.shape_id])


class _P:
    """The three Prep fields the carve reads."""
    def __init__(self, rgb, px_per_mm=10.0):
        self.rgb = rgb
        self.bg_mask = np.zeros(rgb.shape[:2], bool)
        self.enclosed_mask = None
        self.px_per_mm = px_per_mm
        self.art_bbox = (0, 0, rgb.shape[1], rgb.shape[0])


def test_nothing_found_returns_q_itself():
    rgb = np.full((80, 80, 3), 255, np.uint8)
    q = Quant(labels=np.zeros((80, 80), np.int32), thread_indices=[0],
              cluster_rgb=np.array([[255.0, 255.0, 255.0]]))
    assert carve_flat_dark_ink(_P(rgb), PipelineConfig(), q) is q


def test_a_stroke_that_owns_its_cluster_keeps_its_label():
    """One tan bar on white, the bar its own k-means cluster: it survives the
    carve's rule (own share 1.0), so `q` comes back unchanged."""
    rgb = np.full((120, 120, 3), 255, np.uint8)
    rgb[40:80, 58:62] = TAN
    labels = np.zeros((120, 120), np.int32)
    labels[40:80, 58:62] = 1
    q = Quant(labels=labels, thread_indices=[0, 1],
              cluster_rgb=np.array([[255.0, 255.0, 255.0], [float(c) for c in TAN]]))
    from digitizer_core.thin_ink import find_dark_thin_ink
    assert find_dark_thin_ink(_P(rgb), PipelineConfig(), np.ones((120, 120), bool)) is not None
    assert carve_flat_dark_ink(_P(rgb), PipelineConfig(), q) is q


def test_strokes_sharing_a_cluster_leave_it_for_the_dark_block():
    """Three tan bars and a tan slab in ONE cluster: each bar holds a small
    share of it, so each leaves for a trailing dark label; the slab stays."""
    rgb = np.full((160, 200, 3), 255, np.uint8)
    labels = np.zeros((160, 200), np.int32)
    for x in (40, 70, 100):
        rgb[30:70, x:x + 4] = TAN
        labels[30:70, x:x + 4] = 1
    rgb[100:150, 20:180] = TAN
    labels[100:150, 20:180] = 1
    q = Quant(labels=labels, thread_indices=[0, 1],
              cluster_rgb=np.array([[255.0, 255.0, 255.0], [float(c) for c in TAN]]))
    out = carve_flat_dark_ink(_P(rgb), PipelineConfig(), q)
    assert out is not q
    assert out.dark_ink_labels and min(out.dark_ink_labels) == 2
    assert len(out.thread_indices) == len(out.cluster_rgb) == 2 + len(out.dark_ink_labels)
    for x in (40, 70, 100):
        assert set(np.unique(out.labels[30:70, x:x + 4])) <= set(out.dark_ink_labels)
    assert set(np.unique(out.labels[100:150, 20:180])) == {1}
    assert (q.labels[30:70, 40:44] == 1).all()          # the input is not written
