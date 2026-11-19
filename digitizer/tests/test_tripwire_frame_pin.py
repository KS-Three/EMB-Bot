"""The tripwire's frame pin (Kent 2026-11-15, "Pin tripwire frame (Recommended)"; built
OFF), on real data: becker_hat_small with `lettering_columns_corner_fold_apex_side` OFF
and ON, read against the pro's committed DST in `testdata/reference/`.

Why: `scorecard.register` hill-climbs solid IoU on a flat plateau, and the fold's 0.1 mm
of extra thread at the E lands it 0.2 mm elsewhere; the 2 mm cell grid moves with it and
the tripwire read stitch-type kappa 0.557 -> 0.518 (CI) for a fold whose own effect, in
one frame, is -0.008 (docs/corner-fold-kappa-2026-11-15.md). Pinned, both arms are read
in one frame.

Reads only files under digitizer/ (the pro DST is byte-identical to the zip's member), so
this is not a wire test (tools/ci_wire_tests.py). One build, one finish, two plans: the
fold acts only in the plan (10,223 vs 10,364 stitches, as the full digitizes measured).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

DIGITIZER = Path(__file__).resolve().parents[1]
JOB = "becker_hat_small"
PRO = DIGITIZER / "testdata" / "reference" / "becker_hat_small_beckers_logo_hat_2_a.dst"
FLAG = "lettering_columns_corner_fold_apex_side"
#: The one-frame figures measured for this pair were -0.008 (stitch type) and +0.008
#: (direction); the own-registration swing was -0.054. Pinned must read on the first scale.
ONE_FRAME = 0.015


@pytest.fixture(scope="module")
def arms(tmp_path_factory):
    from digitizer_core import PipelineConfig
    from digitizer_core.export import write_dst
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_baseline as pb
    from tools import pro_pair

    garment, width, art, *_ = pb.JOBS[JOB]
    data = (DIGITIZER / "testdata" / art.partition(":")[2]).read_bytes()

    from tests.conftest import MARINE_MATCH_2026_11_19_OFF

    def cfg(on, marine_match=False):
        p = _parse_config(json.dumps(pro_pair.request(width, garment, None)))
        p[FLAG] = on
        if not marine_match:
            # the columns as they were when this pair was measured: the four MARINE-match fields (ON since Kent's
            # 2026-11-19 flip) butt the E at 76.5 mm instead of folding it, so the fold flag would move nothing
            p.update(MARINE_MATCH_2026_11_19_OFF)
        return PipelineConfig(**p)

    off, on = cfg(False), cfg(True)
    gen = build_generation(_decode(data), off, exif_source=data)
    result = finish_generation(gen.fork(), off)
    root = tmp_path_factory.mktemp("frame_pin")
    out = {}
    for name, c in (("off", off), ("on", on)):
        plan = plan_stitches(result, c)
        work = root / name / JOB
        work.mkdir(parents=True)
        dst = root / name / "ours.dst"
        write_dst(plan, dst)
        pb.write_side(work, "pro", PRO)
        pb.write_side(work, "ours", dst)
        out[name] = work
        out[name + "_stitches"] = plan.stats.stitch_count
    # under today's defaults (block_butt_small ON) the fold flag changes nothing on this pair
    out["default_off_stitches"] = plan_stitches(result, cfg(False, True)).stats.stitch_count
    out["default_on_stitches"] = plan_stitches(result, cfg(True, True)).stats.stitch_count
    return out


def _score(work, frame=None):
    from tools.pro_parity import scorecard
    return scorecard.score_design(work) if frame is None else scorecard.score_design(work, frame=frame)


def _pin(score):
    return {k: score["detail"]["frame"][k] for k in ("dx", "dy", "x0", "y0")}


def test_the_fold_moves_this_pair_as_the_arms_measured(arms):
    # the arms are the pre-flip columns (`MARINE_MATCH_2026_11_19_OFF`): the fold sews the E's corners
    assert arms["on_stitches"] > arms["off_stitches"]


def test_under_the_defaults_the_e_is_butted_and_the_fold_flag_moves_nothing(arms):
    """Kent 2026-11-19, "Flip all four ON (Recommended)", told `block_butt_small` undoes his 11-14 E fold at
    76.5-79.8 mm too: this E (3.46 mm a stroke) is a stem and three butted arms under the defaults, so the
    fold flag, ON or OFF, sews the same thing. The assertion above is the fold as built (the PRE_FLIP arm)."""
    assert arms["default_on_stitches"] == arms["default_off_stitches"]


def test_with_no_frame_the_score_is_the_original_path(arms):
    plain = _score(arms["off"])
    recorded = _score(arms["off"], frame={})
    assert "frame" not in plain["detail"]
    assert recorded["detail"].pop("frame")["source"] == "registered"
    assert recorded == plain


@pytest.mark.parametrize("arm", ["off", "on"])
def test_an_unchanged_design_reads_byte_identically_at_its_own_pin(arms, arm):
    """The pin is stored rounded (3 decimals). Read back on the same design it must give
    exactly what the capture read, not a re-cut by float noise: precision_drone read 0.373
    recorded and 0.359 pinned on one DST and one frame before `SAME_MM` (2026-11-15)."""
    rec = _score(arms[arm], frame={})
    pinned = _score(arms[arm], frame=_pin(rec))
    assert pinned["detail"]["frame"]["source"] == "pinned"
    assert pinned["parts"] == rec["parts"]
    assert pinned["detail"]["chance_floor"] == rec["detail"]["chance_floor"]


def test_pinned_the_fold_reads_on_the_one_frame_scale(arms):
    off = _score(arms["off"], frame={})
    on_fresh = _score(arms["on"])
    on_pinned = _score(arms["on"], frame=_pin(off))
    f = on_pinned["detail"]["frame"]
    assert f["source"] == "pinned", f
    why = (f"off {off['parts']['sttype']}/{off['parts']['direction']}, "
           f"on pinned {on_pinned['parts']['sttype']}/{on_pinned['parts']['direction']}, "
           f"on fresh {on_fresh['parts']['sttype']}/{on_fresh['parts']['direction']} "
           f"at {on_fresh['detail']['registration_mm']} vs {off['detail']['registration_mm']}")
    assert abs(on_pinned["parts"]["sttype"] - off["parts"]["sttype"]) <= ONE_FRAME, why
    assert abs(on_pinned["parts"]["direction"] - off["parts"]["direction"]) <= ONE_FRAME, why


def test_the_pinned_frame_keeps_the_pins_grid_origin(arms):
    off = _score(arms["off"], frame={})
    on = _score(arms["on"], frame=_pin(off))
    from tools.pro_parity.scorecard import CELL
    for k in ("x0", "y0"):
        steps = (off["detail"]["frame"][k] - on["detail"]["frame"][k]) / CELL
        assert abs(steps - round(steps)) < 1e-6, (k, steps)


def test_a_design_that_really_moved_re_registers(arms, tmp_path):
    off = _score(arms["off"], frame={})
    moved = tmp_path / JOB
    shutil.copytree(arms["on"], moved)
    csv = moved / "ours_stitches.csv"
    lines = csv.read_text().splitlines()
    out = [lines[0]]
    for ln in lines[1:]:
        b, r, t, j, x, y = ln.split(",")
        out.append(f"{b},{r},{t},{j},{float(x) + 3.0:.2f},{y}")     # the whole design 3 mm right
    csv.write_text("\n".join(out) + "\n")
    pinned = _score(moved, frame=_pin(off))
    fresh = _score(moved)
    assert pinned["detail"]["frame"]["source"] == "re-registered", pinned["detail"]["frame"]
    assert pinned["parts"] == fresh["parts"]


def test_pinned_bounds_steps_out_by_whole_cells_and_never_clips():
    from tools.pro_parity.scorecard import CELL, pinned_bounds
    assert pinned_bounds((-40.0, -30.0, 40.0, 30.0), -41.0, -31.0) == (-41.0, -31.0, 40.0, 30.0)
    x0, y0, _x1, _y1 = pinned_bounds((-45.3, -30.0, 40.0, 30.0), -41.0, -31.0)
    assert x0 <= -45.3 and ((-41.0 - x0) / CELL).is_integer() and y0 == -31.0
    # a pin stored rounded is the natural origin, kept as its exact float, never stepped out
    nat = -39.7 - 1e-12
    assert pinned_bounds((nat, -41.05, 40.0, 30.0), -39.7, -41.05)[:2] == (nat, -41.05)
