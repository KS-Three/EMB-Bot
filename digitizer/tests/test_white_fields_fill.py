"""`cfg.sew_enclosed_white_fields_fill` (2026-10-25, built OFF): a white field
that `sew_enclosed_white` sews is never a letter.

Becker's white BECKER faces carry the word's text tag, so with
`sew_enclosed_white` ON stage 7 sewed each one as a Column-lane letter --
8.4x the digitize time on Becker at 100 mm, and not the pro's construction
(a 22 deg tatami under the outline). ON, the face leaves the lane and the
tier ladder takes it; a fill sews at `machine.WHITE_FIELD_FILL_ANGLE_DEG`.
"""
from __future__ import annotations

import hashlib
import json
import math

from shapely.geometry import Polygon

from digitizer_core import columns, machine, stage7_sequence as s7, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from tests.conftest import TESTDATA, own_thread_only

#: a 16 x 24 mm face, the size of Becker's smaller white BECKER faces
FACE = Polygon([(0, 0), (16, 0), (16, 24), (0, 24)])
TAGS = {"text_candidate": True, "lettering_group": True, "text_cluster_id": "TC1"}


def _face(**meta) -> Region:
    return Region(shape_id="Sface", polygon=FACE, thread_index=0, thread_number="0015",
                  area_mm2=FACE.area, source="test",
                  meta={"layer": 0, "stitched": True, **TAGS, **meta})


def _plan(region: Region, **cfg_kw):
    """-> (runs, how many times the Column lane was entered)."""
    calls = []
    real = s7.lettering_columns_shape

    def spy(*a, **k):
        calls.append(1)
        return real(*a, **k)
    s7.lettering_columns_shape = own_thread_only(spy, real)
    try:
        blocks, _w = s7.sequence([PlannedRegion(region=region, polygon=region.polygon, sew_index=0)],
                                 fabric_for_garment("hat_front"), PipelineConfig(**cfg_kw))
    finally:
        s7.lettering_columns_shape = real
    return [r for b in blocks for r in b.runs], len(calls)


def _row_angles(runs) -> list[float]:
    """Undirected angle of every fill stitch over 2 mm (the rows)."""
    out = []
    for r in runs:
        if r.kind != stitches.FILL:
            continue
        for a, b in zip(r.points, r.points[1:]):
            if math.dist(a, b) >= 2.0:
                out.append(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0)
    return out


def test_flag_default_is_off():
    assert PipelineConfig().sew_enclosed_white_fields_fill is False
    assert machine.WHITE_FIELD_FILL_ANGLE_DEG == 22.0


def test_is_lettering_drops_only_a_sewn_white_field():
    cfg = PipelineConfig(sew_enclosed_white_fields_fill=True)
    assert columns.is_lettering(_face(), cfg)                               # a letter
    assert not columns.is_lettering(_face(sew_enclosed_white="field"), cfg)
    assert columns.is_lettering(_face(sew_enclosed_white="field"), PipelineConfig())  # OFF


def test_off_the_face_is_a_column_letter():
    _runs, lane = _plan(_face(sew_enclosed_white="field"))
    assert lane == 1


def test_on_the_face_leaves_the_lane_and_fills_at_the_pros_angle():
    runs, lane = _plan(_face(sew_enclosed_white="field"), sew_enclosed_white_fields_fill=True)
    assert lane == 0
    angles = _row_angles(runs)
    assert len(angles) > 50, "a 16 x 24 mm face must sew as a fill"
    off = [min(abs(a - machine.WHITE_FIELD_FILL_ANGLE_DEG) % 180.0,
               180.0 - abs(a - machine.WHITE_FIELD_FILL_ANGLE_DEG) % 180.0) for a in angles]
    assert sorted(off)[len(off) // 2] < 3.0, sorted(off)[len(off) // 2]


def test_on_a_letter_without_the_option_is_untouched():
    a, lane_a = _plan(_face())
    b, lane_b = _plan(_face(), sew_enclosed_white_fields_fill=True)
    assert lane_a == lane_b == 1
    assert [r.points for r in a] == [r.points for r in b]


def test_on_without_sew_enclosed_white_is_byte_identical():
    def md5(**kw):
        _r, plan = digitize(TESTDATA / "logo_whitebg.png", PipelineConfig(target_width_mm=80.0, **kw))
        c = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
             for _, r in plan.iter_runs() for x, y in r.points]
        return hashlib.md5(json.dumps(c).encode()).hexdigest()
    assert md5() == md5(sew_enclosed_white_fields_fill=True)
