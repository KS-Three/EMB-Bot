"""`cfg.lettering_columns_stroke_floor` (built OFF 2026-11-15 as a `cfg.extra` key; ON since
2026-11-16, Kent's flip: "On, the United States is a huge improvement."): under
`thin_floor`, a column that keeps fewer than half its crosses over the floor
is floored whole, as one that keeps fewer than three already is.

The case is Bukit Asam's tagline (`testdata/art/commons_lettering/
bukit_asam_logo_cmyk_01.png`) at 80.4 mm left chest: the y of "beyond". Its
left arm and tail are one curved column, 0.46-0.49 mm across after the rail
inset; four crosses at the join reached the 0.5 mm floor, so the column kept
"three" and dropped the other nine, and the y sewed as an r."""
from shapely import wkt
from shapely.geometry import Polygon

from digitizer_core import columns as C
from digitizer_core import outline_cut as oc
from digitizer_core import shape_memo

# The y as stage 7 hands it to the Column lane (mm, shifted near the origin,
# 4 decimals): 101-point outline, 3.48 mm^2.
Y_BEYOND = wkt.loads(
    "POLYGON ((0.7016 0.2474, 0.7016 0.3746, 0.7440 0.4170, 0.7440 0.5441, 0.7864 0.5865, 0.7864 0.7560, "
    "0.8288 0.7984, 0.8288 0.9679, 0.8712 1.0103, 0.8712 1.1375, 0.9135 1.1799, 0.9135 1.3070, 0.9559 1.3494, "
    "0.9559 1.5189, 0.9983 1.5613, 0.9983 1.6885, 1.0407 1.7308, 1.0407 1.9004, 1.0831 1.9428, 1.0831 2.0699, "
    "1.1255 2.1123, 1.1255 2.2818, 1.1678 2.3242, 1.1678 2.4513, 1.2102 2.4937, 1.2102 2.6209, 1.1678 2.6633, "
    "1.1255 2.7904, 1.0407 2.8752, 1.0407 2.9176, 0.9559 3.0023, 0.9559 3.0447, 0.7016 3.2990, 0.6593 3.2990, "
    "0.5321 3.3838, 0.1507 3.3838, 0.1083 3.4261, 0.1083 3.5957, 0.0659 3.6381, 0.0659 3.7652, 0.8712 3.7652, "
    "0.9559 3.6804, 1.0831 3.6381, 1.4221 3.2990, 1.4221 3.2566, 1.5069 3.1719, 1.5069 3.1295, 1.6764 2.9176, "
    "1.7612 2.7056, 1.8460 2.6209, 1.9307 2.4090, 2.0155 2.3242, 2.1003 2.1123, 2.1850 2.0275, 2.2698 1.8156, "
    "2.3546 1.7308, 2.4393 1.5189, 2.5241 1.4342, 2.6089 1.2222, 2.6936 1.1375, 2.7784 0.9256, 2.8632 0.8408, "
    "2.9903 0.5441, 3.0751 0.4594, 3.1174 0.3322, 3.1598 0.2898, 3.1598 0.2474, 2.5241 0.2474, 2.4817 0.3746, "
    "2.4393 0.4170, 2.3969 0.5441, 2.3122 0.6289, 2.3122 0.6713, 2.1850 0.8832, 2.1426 1.0103, 2.0579 1.0951, "
    "2.0579 1.1375, 2.0155 1.1799, 1.9731 1.3070, 1.7188 1.7732, 1.7188 1.8156, 1.6341 1.9004, 1.5917 1.8580, "
    "1.5917 1.7732, 1.5493 1.7308, 1.5493 1.5613, 1.5069 1.5189, 1.5069 1.3494, 1.4645 1.3070, 1.4645 1.1375, "
    "1.4221 1.0951, 1.4221 0.9679, 1.3798 0.9256, 1.3798 0.7560, 1.3374 0.7137, 1.3374 0.5441, 1.2950 0.5017, "
    "1.2950 0.3322, 1.2526 0.2898, 1.2526 0.2474, 0.7016 0.2474))")
# Commons Bukit's e at 85.1 mm hat (same art, shifted near the origin, 4
# decimals): 85-point outline, one counter, 3.52 mm^2.
E_HAT = wkt.loads(
    "POLYGON ((1.9366 0.5814, 1.8917 0.6263, 1.7123 0.6263, 1.6674 0.6711, 1.5777 0.6711, 1.4431 0.7608, "
    "1.3085 0.8057, 0.9496 1.1646, 0.9496 1.2094, 0.8599 1.2992, 0.8599 1.3440, 0.7702 1.4786, 0.7702 1.5683, "
    "0.7253 1.6132, 0.7253 1.7029, 0.6805 1.7478, 0.6805 1.9721, 0.6356 2.0169, 0.6356 2.4207, 0.6805 2.4655, "
    "0.6805 2.6001, 0.7253 2.6450, 0.7253 2.7347, 0.7702 2.7795, 0.7702 2.8244, 1.0394 3.0936, 1.0842 3.0936, "
    "1.2188 3.1833, 1.3085 3.1833, 1.3534 3.2281, 1.4880 3.2281, 1.5328 3.2730, 1.9814 3.2730, 2.0263 3.2281, "
    "2.2506 3.2281, 2.2954 3.1833, 2.5197 3.1384, 2.5646 3.0936, 2.5646 2.9590, 2.6095 2.9141, 2.6095 2.7347, "
    "2.6543 2.6898, 2.6543 2.6001, 2.6095 2.6450, 2.5197 2.6450, 2.4749 2.6898, 2.3852 2.6898, 2.3403 2.7347, "
    "2.1609 2.7347, 2.1160 2.7795, 1.6225 2.7795, 1.5777 2.7347, 1.4431 2.6898, 1.3085 2.5552, 1.3085 2.5104, "
    "1.2188 2.3758, 1.2188 2.2412, 1.2637 2.1964, 1.6674 2.1964, 1.7123 2.1515, 1.9814 2.1515, 2.0263 2.1066, "
    "2.2057 2.1066, 2.2506 2.0618, 2.3403 2.0618, 2.5646 1.9272, 2.6095 1.9272, 2.8338 1.7029, 2.8786 1.5683, "
    "2.9235 1.5235, 2.9235 1.3440, 2.9683 1.2992, 2.9683 1.2543, 2.9235 1.2094, 2.9235 1.0300, 2.8786 0.9851, "
    "2.8786 0.9403, 2.6543 0.7160, 2.6095 0.7160, 2.5646 0.6711, 2.4749 0.6711, 2.4300 0.6263, 2.2954 0.6263, "
    "2.2506 0.5814, 1.9366 0.5814), "
    "(1.9814 1.0749, 2.0263 1.0300, 2.1160 1.0300, 2.1609 1.0749, 2.2057 1.0749, 2.3403 1.2094, 2.3403 1.3889, "
    "2.1160 1.6132, 2.0263 1.6132, 1.9814 1.6580, 1.8917 1.6580, 1.8468 1.7029, 1.5777 1.7029, 1.5328 1.7478, "
    "1.3982 1.7478, 1.3534 1.7029, 1.3534 1.5683, 1.4880 1.3889, 1.4880 1.3440, 1.7571 1.1197, 1.8020 1.1197, "
    "1.8468 1.0749, 1.9814 1.0749))")
# stage 7's call for it (the shipped engine's lettering knobs)
KW = dict(trim_at_mm=3.0, spacing_mm=0.4, split_above_mm=None, pull_mm=0.3, pull_floor_mm=1.5,
          underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
          small_bold=True, short_columns=True, corner_fold=True, corner_fold_apex_side=True,
          inside_stagger=True, inside_connectors=True, edge_walk=True)


def _sew(poly, on: bool, judged: bool = True, **kw):
    # main's plan-wide scopes (Kent's 2026-11-15 flips) round the flag;
    # `judged=False` is the floored sew alone, before `_stroke_floor_judged`
    with C.ring_floor_scope(True), oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), \
            oc.fold_cap_flared_scope(True), C.stroke_floor_scope(on):
        token = C._STROKE_JUDGING.set(None if judged else [])
        try:
            return C.lettering_columns_shape(poly, "x", **{**KW, **kw})
        finally:
            C._STROKE_JUDGING.reset(token)


def _pts(runs):
    return [r.points for r in runs]


def test_config_default_is_on_and_false_is_the_old_engine():
    # ON since 2026-11-16 (Kent: "On, the United States is a huge improvement.");
    # the ambient scope outside a plan stays False, so a bare call is the old lane
    from digitizer_core.config import PipelineConfig
    from tests.conftest import PRE_FLIP
    assert PipelineConfig().lettering_columns_stroke_floor is True
    assert PRE_FLIP["lettering_columns_stroke_floor"] is False
    assert PipelineConfig(**{"lettering_columns_stroke_floor": False}).lettering_columns_stroke_floor is False
    assert C._STROKE_FLOOR.get() is False and C._STROKE_JUDGING.get() is None
    assert ("columns", "_STROKE_FLOOR") in shape_memo._AMBIENT
    assert ("columns", "_STROKE_JUDGING") in shape_memo._INERT


def test_the_beyond_y_sews_its_left_arm_and_tail():
    runs_off, rep_off = _sew(Y_BEYOND, False, text_lean_deg=14.8025)
    runs_on, rep_on = _sew(Y_BEYOND, True, text_lean_deg=14.8025)
    # off: the left arm and tail's column keeps 4 of 13 crosses; 10 dropped
    assert rep_off["thin_crosses"] == 10 and "stroke_floored" not in rep_off
    assert rep_on["thin_crosses"] == 0 and rep_on["stroke_floored"] == 1
    assert rep_on["stroke_floor_kept"] == 1                            # the judge kept it
    assert C.satin_cover(runs_off, Y_BEYOND) < 0.6                     # 0.55: an r
    assert C.satin_cover(runs_on, Y_BEYOND) > 0.95                     # 0.995: the y
    # more new thread inside the letter than outside it (`HANDBACK_RULE`'s "net")
    assert C.handback_wins(runs_off, runs_on, Y_BEYOND, rule="net")


def test_a_floored_sew_that_sews_worse_is_refused():
    # Commons Bukit's e at 85.1 mm hat: floored, its first cut cleared the
    # small-bold cover bar and was kept over the resimplified one, and the
    # column round its mouth laid an underlay chord over bare cloth. Cover
    # 0.92 -> 0.98, spill 0.40 -> 0.55: the judge sews it as it was.
    kw = dict(pull_mm=0.4, text_lean_deg=12.7644)
    runs_off, rep_off = _sew(E_HAT, False, **kw)
    runs_raw, rep_raw = _sew(E_HAT, True, judged=False, **kw)
    runs_on, rep_on = _sew(E_HAT, True, **kw)
    assert rep_off["resimplified"] == 1 and "resimplified" not in rep_raw
    assert rep_raw["stroke_floored"] == 1 and _pts(runs_raw) != _pts(runs_off)
    assert not C.handback_wins(runs_off, runs_raw, E_HAT, rule="net")
    assert _pts(runs_on) == _pts(runs_off) and "stroke_floor_kept" not in rep_on


def test_a_column_that_keeps_most_crosses_still_drops_its_thin_tip():
    # a stroke with a pointed end: three tip crosses under the floor, the
    # rest over it -- the fan tip `thin_floor` drops on purpose
    taper = Polygon([(0, 0), (0.6, 0), (0.6, 2.6), (0.3, 3.6), (0, 2.6)])
    runs_off, rep_off = _sew(taper, False)
    runs_on, rep_on = _sew(taper, True)
    assert rep_off["thin_crosses"] == 3
    assert _pts(runs_on) == _pts(runs_off)
    assert "stroke_floored" not in rep_on


def test_a_sew_the_floor_never_reaches_is_sewn_once(monkeypatch):
    # nothing recorded, the floored sew is the unfloored one: no second sew
    calls = []
    real = C.lettering_columns_shape

    def counted(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(C, "lettering_columns_shape", counted)
    taper = Polygon([(0, 0), (0.6, 0), (0.6, 2.6), (0.3, 3.6), (0, 2.6)])
    with C.stroke_floor_scope(True):
        counted(taper, "x", **KW)
    flat = len(calls)
    calls.clear()
    counted(taper, "x", **KW)
    assert flat == len(calls) + 1          # the judge's one floored sew, and no unfloored one


def test_a_stroke_floored_far_past_its_width_is_refused():
    # a 4 mm wedge narrowing from 0.7 to 0.2 mm: floored, its thin end sews
    # at 0.5 mm, over twice its drawn width -- more new thread outside the
    # wedge than inside it, so the judge keeps OFF's drop
    wedge = Polygon([(0, 0), (0.7, 0), (0.45, 4.0), (0.25, 4.0)])
    runs_off, rep_off = _sew(wedge, False)
    runs_raw, rep_raw = _sew(wedge, True, judged=False)
    runs_on, rep_on = _sew(wedge, True)
    assert rep_off["thin_crosses"] > 0 and "floored" not in rep_off
    assert rep_raw["thin_crosses"] == 0 and rep_raw["stroke_floored"] == 1
    assert not C.handback_wins(runs_off, runs_raw, wedge, rule="net")
    assert _pts(runs_on) == _pts(runs_off) and "stroke_floor_kept" not in rep_on
