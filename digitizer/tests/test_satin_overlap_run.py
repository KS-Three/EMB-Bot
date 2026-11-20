"""`cfg.extra["satin_overlap_run"]` (built OFF 2026-11-19): a satin stretch lying wholly under
later satin of the same shape is sewn as running stitch (`column_overlap.overlap_run`)."""
from pathlib import Path


from digitizer_core import stitches
from digitizer_core.column_overlap import MIN_STITCHES, overlap_run
from digitizer_core.stitches import StitchRun


def _zig(x0, x1, y0, n, pitch=0.4, w=1.8):
    pts = []
    for i in range(n):
        y = y0 + i * pitch
        pts += [(x0, y), (x1, y + pitch / 2)] if i % 2 == 0 else [(x1, y), (x0, y + pitch / 2)]
    return pts


def _run(pts, kind=stitches.SATIN):
    return StitchRun(points=pts, kind=kind, shape_id="S")


def test_stretch_under_later_satin_becomes_run():
    under = _run(_zig(0, 1.8, 0, 30))
    over = _run(_zig(0, 1.8, 0, 30))
    out, n = overlap_run([under, over])
    assert n > 0
    assert len(out[0].points) < len(under.points)
    assert out[1] is over                       # the visible layer is untouched
    assert out[0].kind == stitches.SATIN and out[0].shape_id == "S"
    assert out[0].points[0] == under.points[0]


def test_two_runs_on_each_other_cannot_both_go():
    a = _run(_zig(0, 1.8, 0, 30))
    b = _run(_zig(0, 1.8, 0, 30))
    out, _ = overlap_run([a, b])
    assert out[1].points == b.points            # the last one always stays


def test_short_lap_stays():
    a = _run(_zig(0, 1.8, 0, MIN_STITCHES // 2 - 1))
    b = _run(_zig(0, 1.8, 0, MIN_STITCHES // 2 - 1))
    out, n = overlap_run([a, b])
    assert n == 0 and out[0] is a


def test_apart_and_non_satin_untouched():
    a = _run(_zig(0, 1.8, 0, 30))
    b = _run(_zig(5, 6.8, 0, 30))
    f = _run(_zig(0, 1.8, 0, 30), kind=stitches.FILL)
    out, n = overlap_run([a, b, f])
    assert n == 0 and out == [a, b, f]


def test_config_default_is_on_and_pre_flip_is_off():
    # ON since 2026-11-19 (Kent 2026-11-19, shown the OFF | ON review pack: "satin_overlap_run (Recommended), outline_loop_split_shared, through_last, e_top_arm + top_slab")
    from digitizer_core import PipelineConfig
    from tests.conftest import PRE_FLIP
    assert PipelineConfig().satin_overlap_run is True
    assert PRE_FLIP["satin_overlap_run"] is False
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(encoding="utf-8")
    assert "cfg.satin_overlap_run" in src


def test_mfab_hat_on_sews_fewer_stitches_and_keeps_the_trims():
    from tools import pro_pair as pp
    art = Path(__file__).resolve().parent.parent / "testdata" / "art" / "logo_mfab_hat.png"
    off = pp.digitize(art, 104.9, "hat_front", {"satin_overlap_run": False})
    on = pp.digitize(art, 104.9, "hat_front")
    assert on.plan.stats.stitch_count < off.plan.stats.stitch_count
    assert on.plan.stats.trims == off.plan.stats.trims
