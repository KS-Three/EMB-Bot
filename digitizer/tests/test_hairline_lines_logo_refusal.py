"""The gradient supplement's LOGO refusal (`cfg.hairline_lines_logo_refusal`,
default OFF, 2026-10-15; `stage6_hairline_lines.logo_line_test`).

#942's supplement (`cfg.hairline_lines_gradient`, OFF) sews the line detail
of rendered art on three corpus logos. With this flag on, a line the
supplement would sew is also refused when it lies mostly along a shape's
edge, or when the ground beside it (on a common 4 px/mm grid) is flat or a
pattern of hard lines. Every number is a property of the file, not of cloth
(ROADMAP gate 1); measured in `tools/hairline_logo_refusal.py`.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_hairline_lines import (
    LOGO_KEYS, SUPPLEMENT_KEYS, logo_line_test, strand_blocks, supplement_test)
from tests.test_hairline_lines import _md5
from tests.test_hairline_lines_chain import _pair
from tests.test_hairline_lines_chain import _sp as _pair_sp
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

SUPP = dict(hairline=True, hairline_from_lines=True, hairline_lines_strand_test=True,
            hairline_lines_gradient=True)
ALL = dict(SUPP, hairline_lines_logo_refusal=True)
LINE = [(0.0, -10.0), (0.0, 10.0)]          # mm, a vertical line through the middle


# --- OFF is byte-identical ---------------------------------------------------------

def test_the_flag_defaults_off():
    assert PipelineConfig().hairline_lines_logo_refusal is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: the flag without the supplement is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_lines_logo_refusal=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


def _runs_md5(blocks) -> str:
    pts = [[t, r.kind, r.jump, r.trim, [[round(x, 4), round(y, 4)] for x, y in r.points]]
           for t, runs in blocks for r in runs]
    return hashlib.md5(json.dumps(pts).encode()).hexdigest()


def _pair_blocks(cfg):
    sp = _pair_sp(_pair(40))
    return strand_blocks(sp, cfg, entry=None, trim_at_mm=machine.TRIM_AT_MM,
                         allowed_threads=[0], refuse=supplement_test([], set(), sp, cfg))


# The supplement ON, logo refusal OFF, on the two drawn strands of
# `test_hairline_lines_chain._pair(40)`: #942's path, read with origin/main's
# `digitizer_core` (a17d4355..35c50609) and pinned here.
PAIR_SUPPLEMENT_MD5 = "9321904438503b6d4cf4edd97c4d54bb"


def test_the_supplement_without_the_refusal_is_pinned():
    blocks, rep = _pair_blocks(PipelineConfig(**SUPP))
    assert rep["strands"] == 2
    assert not any(k in rep for k in LOGO_KEYS)
    assert _runs_md5(blocks) == PAIR_SUPPLEMENT_MD5


def test_the_keys_follow_the_flag():
    sp = _pair_sp(_pair(40))
    assert supplement_test([], set(), sp, PipelineConfig(**SUPP)).keys == SUPPLEMENT_KEYS
    assert supplement_test([], set(), sp, PipelineConfig(**ALL)).keys == SUPPLEMENT_KEYS + LOGO_KEYS


# --- the three rules, on synthetic ground -------------------------------------------

def _ground(kind: str) -> SourcePixels:
    """A 40 x 40 mm raster at 8 px/mm, origin in the middle: `flat` grey,
    `texture` grey with per-pixel noise (a photo's grain), `hatch`
    alternating 2 px dark and light columns (an engraving)."""
    img = np.full((320, 320, 3), 128, np.uint8)
    if kind == "texture":
        rng = np.random.default_rng(7)
        img = np.clip(128 + rng.normal(0, 25, (320, 320, 1)), 0, 255).astype(np.uint8)
        img = np.repeat(img, 3, axis=2)
    elif kind == "hatch":
        img[:, (np.arange(320) // 2) % 2 == 0] = 30
        img[:, (np.arange(320) // 2) % 2 == 1] = 220
        img = np.ascontiguousarray(img.transpose(1, 0, 2))     # horizontal hatching
    return SourcePixels(rgb=img, px_per_mm=8.0, origin_px=(160.0, 160.0))


def test_a_line_on_textured_ground_is_kept():
    assert logo_line_test([], _ground("texture"))(LINE) is None


def test_a_line_on_flat_ground_is_refused():
    assert logo_line_test([], _ground("flat"))(LINE) == "refused_logo_flat"


def test_a_line_in_a_pattern_of_lines_is_refused():
    assert logo_line_test([], _ground("hatch"))(LINE) == "refused_logo_pattern"


def test_a_line_along_a_shape_edge_is_refused_even_on_texture():
    sp = _ground("texture")
    assert logo_line_test([box(0.0, -15.0, 10.0, 15.0)], sp)(LINE) == "refused_logo_edge"
    # A shape whose edge is 1 mm off the line does not count.
    assert logo_line_test([box(1.0, -15.0, 10.0, 15.0)], sp)(LINE) is None


def test_the_refusal_is_counted_and_the_strands_are_not_sewn():
    """The drawn pair sits on flat ground: drawn line art, refused."""
    blocks, rep = _pair_blocks(PipelineConfig(**ALL))
    assert rep["strands"] == 0 and blocks == []
    assert sum(rep["refused_logo_flat"].values()) == 2
    assert sum(rep["refused_logo_edge"].values()) == 0


# --- the pipeline: drawn hair on gradient --------------------------------------------

@pytest.fixture(scope="module")
def drawn():
    base = dict(target_width_mm=80.0)
    result = run_stages(TESTDATA / "synthetic" / "hair_strands.png", PipelineConfig(**base))
    assert result.design_class == "gradient"
    return {name: plan_stitches(result, PipelineConfig(**base, **kw)) for name, kw in {
        "region": dict(hairline=True), "supp": SUPP, "refuse": ALL}.items()}


def test_on_drawn_hair_the_refusal_changes_nothing(drawn):
    """The supplement sews nothing on drawn hair (#942), so there is nothing
    for the refusal to take: all three plans are one plan, byte for byte."""
    assert _md5(drawn["refuse"]) == _md5(drawn["supp"]) == _md5(drawn["region"])
    w = next(w for w in drawn["refuse"].warnings
             if w["code"] == "HAIRLINE_TIER_SEWN" and w.get("source") == "lines_gradient")
    assert w["strands"] == 0 and all(k in w for k in LOGO_KEYS)
