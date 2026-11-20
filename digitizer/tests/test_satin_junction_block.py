"""`cfg.extra["satin_junction_block"]` (built OFF 2026-11-20): two satin bars of one shape that
stack across a junction are sewn as one wide column (`column_junction.junction_block`)."""
from pathlib import Path

from digitizer_core import stitches
from digitizer_core.column_junction import MIN_STITCHES, junction_block
from digitizer_core.stitches import StitchRun


def _zig(x0, x1, y0, n, pitch=0.4):
    return [((x0, x1)[i % 2], y0 + i * pitch / 2.0) for i in range(2 * n)]


def _run(pts, kind=stitches.SATIN, sid="S"):
    return StitchRun(points=pts, kind=kind, shape_id=sid)


def _xs(run):
    return min(p[0] for p in run.points), max(p[0] for p in run.points)


def test_stacked_bars_become_one_wide_column():
    a = _run(_zig(0.0, 1.8, 0.0, 30))
    b = _run(_zig(1.2, 3.0, 0.0, 30))
    out, n = junction_block([a, b])
    assert n >= MIN_STITCHES
    lo, hi = _xs(out[1])
    assert lo < 0.2 and hi > 2.8                     # B now spans both bars
    assert out[0].points[0] == a.points[0] and out[0].points[-1] == a.points[-1]
    assert len(out[0].points) < len(a.points)         # A's covered stitches are a running path
    assert out[1].kind == stitches.SATIN and len(out[1].points) == len(b.points)


def test_ends_ramp_in_instead_of_stepping():
    a = _run(_zig(0.0, 1.8, 0.0, 30))
    b = _run(_zig(1.2, 3.0, 0.0, 30))
    out, _ = junction_block([a, b])
    first = abs(out[1].points[1][0] - out[1].points[0][0])
    mid = abs(out[1].points[31][0] - out[1].points[30][0])
    assert first < mid


def test_short_lap_stays():
    a = _run(_zig(0.0, 1.8, 0.0, MIN_STITCHES // 2 - 1))
    b = _run(_zig(1.2, 3.0, 0.0, MIN_STITCHES // 2 - 1))
    out, n = junction_block([a, b])
    assert n == 0 and out[0] is a and out[1] is b


def test_same_bar_twice_is_not_ours():
    a = _run(_zig(0.0, 1.8, 0.0, 30))
    b = _run(_zig(0.0, 1.8, 0.0, 30))
    out, n = junction_block([a, b])
    assert n == 0 and out == [a, b]


def test_apart_other_shape_and_non_satin_untouched():
    a = _run(_zig(0.0, 1.8, 0.0, 30))
    far = _run(_zig(6.0, 7.8, 0.0, 30))
    other = _run(_zig(1.2, 3.0, 0.0, 30), sid="T")
    fill = _run(_zig(1.2, 3.0, 0.0, 30), kind=stitches.FILL)
    out, n = junction_block([a, far, other, fill])
    assert n == 0 and out == [a, far, other, fill]


def test_too_wide_a_union_stays():
    a = _run(_zig(0.0, 2.6, 0.0, 30))
    b = _run(_zig(2.0, 4.6, 0.0, 30))              # union 4.6 mm > the 4.4 mm cap
    out, n = junction_block([a, b])
    assert n == 0


def test_flag_is_off_by_default_and_read_from_extra():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("satin_junction_block")
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(encoding="utf-8")
    assert 'get("satin_junction_block")' in src


def test_mfab_hat_on_changes_the_stitches_and_keeps_the_trims():
    from tools import pro_pair as pp
    art = Path(__file__).resolve().parent.parent / "testdata" / "art" / "logo_mfab_hat.png"
    key = "extra.satin_junction_block"
    off = pp.digitize(art, 104.9, "hat_front", {key: False})
    on = pp.digitize(art, 104.9, "hat_front", {key: True})
    assert on.design != off.design
    assert on.plan.stats.trims == off.plan.stats.trims
