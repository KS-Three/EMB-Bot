"""Write the standard-conformant DST fixture the JS import tests read.

`test/fixtures/standard-tajima.dst` is written by pystitch — an independent,
Tajima/pyembroidery-convention implementation — so the JS side has one file
whose contents are NOT produced by the codec under test. Everything about
EMB-Bot's DST reader that the round-trip tests cannot see (they encode with
EMB-Bot's own writer, so a symmetric error cancels) is visible against this.

The design is asymmetric under all eight dihedral transforms, which is the
whole point: a bbox comparison cannot tell a rotation from a mirror, and the
defect this fixture exists for turned out to be a mirror after a year of being
recorded as "a quarter turn". A long arm along +x, ONE short arm at ONE end,
and a second colour block in ONE corner pin the orientation exactly.

Regenerate:  digitizer/.venv/bin/python digitizer/tools/make_standard_dst_fixture.py
"""
from __future__ import annotations

import os

import pystitch

# 0.1 mm units, pystitch's own frame (+y down). 40 x 10 mm.
POINTS = [
    (0, 0), (100, 0), (200, 0), (300, 0), (400, 0),   # long arm, left -> right
    (400, -50), (400, -100),                          # short arm, at the RIGHT end only
]
BLOCK2 = [(0, -100), (50, -100), (0, -60)]            # small block, top-LEFT corner


def build() -> pystitch.EmbPattern:
    p = pystitch.EmbPattern()
    p.add_thread({"hex": "c81e1e", "description": "Red", "catalog": "1"})
    p.add_thread({"hex": "1e3cc8", "description": "Blue", "catalog": "2"})
    for x, y in POINTS:
        p.add_stitch_absolute(pystitch.STITCH, x, y)
    p.trim()
    p.color_change()
    for x, y in BLOCK2:
        p.add_stitch_absolute(pystitch.STITCH, x, y)
    p.end()
    return p


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out = os.path.join(root, "test", "fixtures", "standard-tajima.dst")
    pattern = build()
    pystitch.write_dst(pattern, out)
    back = pystitch.read_dst(out)
    b = back.bounds()
    print(f"wrote {out}")
    print(f"  {(b[2]-b[0])/10:.1f} x {(b[3]-b[1])/10:.1f} mm, {len(back.stitches)} records")
