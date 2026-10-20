"""The strand test's hair-mass exemption (`cfg.hairline_lines_strand_mass`,
default OFF, 2026-10-15; `stage6_hairline_lines.is_hair_mass`).

#897's strand test refuses any stack of parallel lines, so a mane, and
#882's own 8-strand synthetic, read as barring. With this flag on too, a
stack whose members pass the ridge test themselves is kept as hair; the
owl's breast barring, which stacks thin bars with wide ones, stays refused.
Every number is a property of the file, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import json
from dataclasses import replace

import cv2
import pytest

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_hairline_lines import extract_strands, strand_blocks
from tests.test_hairline_lines import _md5
from tests.test_hairline_lines_strand_test import (OWL, _bars, _ground, _sewable, _sp,
                                                   _strands, _zones)
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5
from tools.hairline_strand_mass import (dark_runs, drawn_kept, mane_image, s882_image,
                                        syn_cfg)

LINES = dict(hairline=True, hairline_from_lines=True)
TEST = dict(LINES, hairline_lines_strand_test=True)
MASS = dict(TEST, hairline_lines_strand_mass=True)

# Plan md5s of the two paths this flag must not touch, measured on
# origin/main a8292f6c (before this flag existed), photo lane, 30 mm:
# #882's 8-strand synthetic and the drawn mane, strand test OFF and ON.
PINS = {"s882_lines": "37789a45fa1dac14c3ce6d824dc2ad9c",
        "s882_test": "243da399287cf82a3dc3bd3c377e26af",
        "mane_lines": "ef3237060f81b7a89354453c59973c7b",
        "mane_test": "55a49676e2978699eda271eacd833047"}
# The two bean-letter holds (`bean_letter_counter_hold_mm` 0.25 and
# `bean_letter_bay_hold` 0.2, ON by default since 2026-10-15, Kent's flip)
# reach the drawn mane's strands through the bean tagger and move its stream
# (`mane_lines` read `1e5338e4...` with them on; the s882 synthetic did not
# move). The PINS are main's streams before this flag OR the holds existed,
# and the holds are not this file's subject, so both are pinned OFF here.
# The same goes for the two item-46 flips (Kent, 2026-10-20):
# `dissolve_phantom_blends` and `clip_keep_pieces` move the drawn mane's
# `mane_lines` stream too (`451c0177...` with them on, CI 2026-10-20), and
# the PINS predate both.
HOLDS_OFF = dict(bean_letter_counter_hold_mm=None, bean_letter_bay_hold=None,
                 dissolve_phantom_blends=False, clip_keep_pieces=False)


def _syn_cfg(arm: str, width_mm: float) -> PipelineConfig:
    return replace(syn_cfg(arm, width_mm), **HOLDS_OFF)


def _warning(plan) -> dict:
    return [w for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN"][0]


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    """Both synthetics through the photo lane at 30 mm, one `run_stages`
    each, a plan per arm."""
    out = {}
    for name, make in (("s882", s882_image), ("mane", mane_image)):
        img, drawn = make()
        src = tmp_path_factory.mktemp(name) / f"{name}.png"
        cv2.imwrite(str(src), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        result = run_stages(src, _syn_cfg("lines", 30.0))
        sp = result.source_pixels
        out[name] = {"drawn": [[sp.to_mm(x, y) for x, y in p] for p in drawn]}
        for arm in ("lines", "test", "mass"):
            out[name][arm] = plan_stitches(result, _syn_cfg(arm, 30.0))
        out[name]["mass_alone"] = plan_stitches(result, PipelineConfig(
            target_width_mm=30.0, forced_class="photo_scene", photo_prep=False, **LINES,
            hairline_lines_strand_mass=True, **HOLDS_OFF))
    return out


# --- OFF is byte-identical ---------------------------------------------------

def test_the_flag_defaults_off():
    assert PipelineConfig().hairline_lines_strand_mass is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: the flag without the line route is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_lines_strand_mass=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


def test_the_line_route_and_the_strand_test_keep_mains_md5(synth):
    """Strand test OFF (with and without this flag) and strand test ON
    without it give the plans `main` gave before the flag existed."""
    for name in ("s882", "mane"):
        assert _md5(synth[name]["lines"]) == PINS[f"{name}_lines"]
        assert _md5(synth[name]["mass_alone"]) == PINS[f"{name}_lines"]
        assert _md5(synth[name]["test"]) == PINS[f"{name}_test"]
        assert "exempt_mass" not in _warning(synth[name]["test"])


def test_off_the_census_and_strands_are_unchanged():
    """Strand test on, this flag off: no `exempt_mass`, no `mass` key."""
    sp = _sp(_bars(_strands(_ground())))
    strands, census = extract_strands(sp, PipelineConfig(**TEST))
    assert set(census) == {"found", "refused_no_ridge", "refused_bar"}
    assert all("mass" not in s for s in strands)


# --- the exemption -----------------------------------------------------------

def test_882s_synthetic_is_kept(synth):
    """#882's 8 strands: the strand test refuses 6, the exemption keeps
    them all, and the plan is the strand test OFF plan, byte for byte."""
    s = synth["s882"]
    assert len(dark_runs(s["test"])) <= 2
    assert _md5(s["mass"]) == _md5(s["lines"])
    assert drawn_kept(s["drawn"], dark_runs(s["mass"])) == 8
    w = _warning(s["mass"])
    assert w["exempt_mass"]["dark"] >= 6 and w["refused_bar"]["dark"] == 0


def test_a_mane_is_kept(synth):
    """The drawn mane (28 strands 1.0 mm apart, varied length): the strand
    test keeps almost none; with the exemption at least 90% of the dark
    strands the route sews with the test off are sewn, and of the drawn
    strands it covers at least 90% of what the route covers with the test
    off. The light lines between the strands (the ground) stay refused."""
    m = synth["mane"]
    off, test, on = (dark_runs(m[a]) for a in ("lines", "test", "mass"))
    kept = {a: drawn_kept(m["drawn"], r) for a, r in (("lines", off), ("test", test),
                                                      ("mass", on))}
    assert kept["test"] <= 2
    assert len(on) >= 0.9 * len(off)
    assert kept["mass"] >= 0.9 * kept["lines"]
    w = _warning(m["mass"])
    assert w["exempt_mass"]["light"] == 0
    assert w["sewn_by_polarity"]["light"] == 0


def _barred(thick_px: int):
    """Thirteen parallel bars 2.5 mm apart, alternately `thick_px` wide and
    a thin 2 px: the thin bars stack with WIDE ones, as on a barred breast."""
    img = _ground()
    for i, y in enumerate(range(40, 281, 20)):
        cv2.line(img, (30, y), (290, y + 8), (40, 35, 30), thick_px if i % 2 == 0 else 2,
                 cv2.LINE_AA)
    return img


def test_thin_bars_stacked_with_wide_bars_stay_refused():
    """The barring case: every thin bar's stack holds wide bars, which the
    ridge test refuses, so nothing is exempted and nothing is sewn."""
    sp = _sp(_barred(6))
    test, ct = extract_strands(sp, PipelineConfig(**TEST))
    mass, cm = extract_strands(sp, PipelineConfig(**MASS))
    assert ct["refused_bar"]["dark"] >= 5
    assert cm["exempt_mass"] == {"dark": 0, "light": 0}
    assert cm["refused_bar"] == ct["refused_bar"]
    assert _sewable(mass) == _sewable(test) == []


def test_a_uniform_stack_of_thin_lines_now_reads_as_hair():
    """The trade, pinned: #897's six evenly spaced thin bars are a stack of
    strands to this test (nothing tells them from #882's synthetic), so the
    exemption keeps them. Only a stack with wide members stays a bar."""
    sp = _sp(_bars(_ground()))
    mass, cm = extract_strands(sp, PipelineConfig(**MASS))
    assert cm["refused_bar"]["dark"] == 0
    assert len(_sewable(mass)) >= 5 and all(s["mass"] for s in _sewable(mass))


def test_lone_strands_are_untouched():
    """No stack in the picture: the sewn blocks are the strand test's."""
    sp = _sp(_strands(_ground()))
    kw = dict(entry=None, trim_at_mm=machine.TRIM_AT_MM, allowed_threads=[0], block_wt={})
    t_blocks, t_rep = strand_blocks(sp, PipelineConfig(**TEST), **kw)
    m_blocks, m_rep = strand_blocks(sp, PipelineConfig(**MASS), **kw)
    assert m_rep["exempt_mass"] == {"dark": 0, "light": 0}

    def pts(blocks):
        return [(t, [r.points for r in runs]) for t, runs in blocks]
    assert pts(m_blocks) == pts(t_blocks)


# --- the owl ------------------------------------------------------------------

def test_owl_breast_and_bristles_hold():
    """owl_kent, #897's route (`classical`, 40 wt, 127 mm): the exemption
    takes no breast strand back (15 of 31, #897's done-test) and leaves the
    5 bristles; the fringe count it does take back is reported, not gated."""
    base = dict(target_width_mm=127.0, forced_class="photo_subject", photo_prep=False)
    sp = run_stages(OWL, PipelineConfig(**base, **LINES)).source_pixels
    test = _zones(sp, extract_strands(sp, PipelineConfig(**base, **TEST))[0])
    mass_strands, census = extract_strands(sp, PipelineConfig(**base, **MASS))
    mass = _zones(sp, mass_strands)
    assert test["breast"] == 15 and mass["breast"] <= 15
    assert mass["beak_bristles"] == test["beak_bristles"] == 5
    assert mass["elsewhere"] >= test["elsewhere"]
    assert census["exempt_mass"]["dark"] == 0
