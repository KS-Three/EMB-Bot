"""tools/script_flow: does a script word's satin turn smoothly -- one reader for
any DST (2026-10-26, Kent: "the cursive needs to flow").

Satin columns written straight into a DST: one whose crosses turn steadily
round a quarter circle, one whose crosses jump 30 deg halfway, and two columns
sewn end to end that hand over at the same angle or turned 80 deg. (The DST's
0.1 mm grid alone moves a cross a few degrees; the reader's line is 15.)
"""
import math

import pystitch

from tools import script_flow as sf


def _column(pat, centre_of, normal_of, n=60, half=1.0):
    """A zigzag satin column: station k at centre_of(k), cross along normal_of(k)."""
    left = True
    for k in range(n):
        c, u = centre_of(k), normal_of(k)
        s = 1.0 if left else -1.0
        pat.add_stitch_absolute(pystitch.STITCH, (c[0] + s * u[0] * half) * 10, (c[1] + s * u[1] * half) * 10)
        left = not left


def _write(tmp_path, name, build):
    pat = pystitch.EmbPattern()
    build(pat)
    pat.add_command(pystitch.END)
    path = tmp_path / f"{name}.dst"
    pystitch.write_dst(pat, str(path))
    return path


def _arc(k, r=12.0, n=60):
    t = math.radians(90.0 * k / (n - 1))
    return (r * math.cos(t), r * math.sin(t)), (math.cos(t), math.sin(t))


def test_a_column_round_a_curve_turns_smoothly(tmp_path):
    f = sf.flow(_write(tmp_path, "arc", lambda p: _column(p, lambda k: _arc(k)[0], lambda k: _arc(k)[1])), 0)
    assert f["columns"] == 1
    assert f["jump_max"] < 8.0 and f["jumps_over_15"] == 0


def test_a_jump_in_cross_angle_is_read(tmp_path):
    def normal(k):
        a = math.radians(0.0 if k < 30 else 30.0)
        return (math.cos(a), math.sin(a))
    f = sf.flow(_write(tmp_path, "jump", lambda p: _column(p, lambda k: (0.0, 0.4 * k), normal)), 0)
    assert f["jump_max"] > 25.0 and f["jumps_over_15"] >= 1


def test_a_hand_over_is_read_at_its_turn(tmp_path):
    def two(p, turn_deg):
        _column(p, lambda k: (0.0, 0.4 * k), lambda k: (1.0, 0.0), n=30)
        a = math.radians(turn_deg)
        _column(p, lambda k: (0.0, 0.4 * (30 + k)), lambda k: (math.cos(a), math.sin(a)), n=30)
    same = sf.flow(_write(tmp_path, "same", lambda p: two(p, 0.0)), 0)
    right = sf.flow(_write(tmp_path, "right", lambda p: two(p, 80.0)), 0)
    # the stitch that hands over is itself a cross half way round, so the
    # next column's first two read a little short of the full turn
    assert right["joins"] >= 1 and right["join_turn_max"] > 55.0 and right["joins_over_30"] >= 1
    assert same["joins_over_30"] == 0
