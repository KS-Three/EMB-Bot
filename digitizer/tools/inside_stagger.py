"""inside_stagger: how the inside of a satin pivot is sewn -- an L fold's
inside corner, an S's curl, a bowl -- read with ONE rule off the
professional's hat DSTs and off ours (2026-10-23,
`cfg.lettering_columns_inside_stagger`).

WHAT IT READS. Needle-down runs -> zigzag columns (stitches of 0.5 mm or
more, each anti-parallel to the one before; eight points make a column),
stations (the zigzag's A1 B1 A2 B2 ... order: A_i, B_i). A PIVOT ZONE is
four or more consecutive stations whose ends on one side stay within a
`R` disc of their centroid (the inside) while the crosses sweep `SWEEP` deg
or more and the other ends walk at satin pitch (median step under 0.75 mm);
its core is the rotating stations (a turn of `ROT` deg or more to the next)
and one either side. Per zone, a LONG inner end is a station whose cross is
a local maximum of length, a SHORT one a local minimum.

  long_step   distance between consecutive long inner ends (the walk)
  pile        share of those steps under 0.1 mm (the same hole again)
  depth / rel how much shorter a short cross is than its two neighbours'
              mean, in mm / as a share of that mean
  short_frac  short crosses over interior crosses
  same_hole   inner ends within 0.1 mm of an earlier one in the zone
  under1      crosses under 1.0 mm

The zone's inner SPAN is NOT reported: it is set by `R`, not by the
construction (at `R` 0.6 the pro and ours read the same 0.8-1.0 mm; PR
#1054's "0.4-0.8 mm spread" was a 0.45 mm window, 0.9 at most).

  python -m tools.inside_stagger [--jobs fremont,drone,mfab,proseal,becker]
                                 [--arms pro,off,on,fold,fold_on] [--json OUT]
  python -m tools.inside_stagger --jobs drone,fremont --crops DIR

Ours: the band letters of `tools.column_harness`'s `--job`s, sewn through
`columns.lettering_columns_shape` with each arm's keywords; the pro's: his
hat DST's band (`column_harness.pro_points`); Becker: the whole large hat
logo from `testdata/reference/` (the pro's side only -- no letters file).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402

MIN_CROSS = 0.5
R = 0.6
SWEEP = 50.0
ROT = 4.0
BECKER = DIGITIZER / "testdata" / "reference" / "becker_hat_polo_large_beckers_logo_hat.dst"
ARMS = {"off": {}, "on": {"inside_stagger": True},
        "fold": {"corner_fold": True}, "fold_on": {"corner_fold": True, "inside_stagger": True}}


def columns_of(run) -> list[list]:
    """Maximal stretches of zigzag crosses -> point lists."""
    out, cur, prev = [], [], None
    for a, b in zip(run, run[1:]):
        L = math.dist(a, b)
        if L < MIN_CROSS:
            if len(cur) >= 8:
                out.append(cur)
            cur, prev = [], None
            continue
        d = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        if prev is not None and prev[0] * d[0] + prev[1] * d[1] < -0.2:
            cur.append(b)
        else:
            if len(cur) >= 8:
                out.append(cur)
            cur = [a, b]
        prev = d
    if len(cur) >= 8:
        out.append(cur)
    return out


def _dang(x, y):
    return (y - x + math.pi) % (2 * math.pi) - math.pi


def zones(col) -> list[dict]:
    """Pivot zones of one column: inner and outer ends of the core stations."""
    A, B = col[0::2], col[1::2]
    n = min(len(A), len(B))
    st = [(A[i], B[i]) for i in range(n)]
    th = [math.atan2(b[1] - a[1], b[0] - a[0]) for a, b in st]
    found, i = [], 0
    while i < n - 3:
        hit = None
        for side in (0, 1):
            pts, j = [], i
            while j < n:
                pts.append(st[j][side])
                c = np.mean(pts, 0)
                if max(math.dist(q, c) for q in pts) > R:
                    pts.pop()
                    break
                j += 1
            if j - i < 4:
                continue
            sw = max(abs(math.degrees(_dang(th[i], th[k]))) for k in range(i, j))
            outer = [st[k][1 - side] for k in range(i, j)]
            if sw < SWEEP or np.median([math.dist(p, q) for p, q in zip(outer, outer[1:])]) > 0.75:
                continue
            k0, k1 = i, j - 1
            while k0 < k1 and abs(math.degrees(_dang(th[k0], th[k0 + 1]))) < ROT:
                k0 += 1
            while k1 > k0 and abs(math.degrees(_dang(th[k1 - 1], th[k1]))) < ROT:
                k1 -= 1
            k0, k1 = max(i, k0 - 1), min(j - 1, k1 + 1)
            if k1 - k0 < 3:
                continue
            hit = (j, side, k0, k1)
            break
        if hit:
            j, side, k0, k1 = hit
            found.append(dict(inner=[st[k][side] for k in range(k0, k1 + 1)],
                              outer=[st[k][1 - side] for k in range(k0, k1 + 1)]))
            i = j - 1
        else:
            i += 1
    return found


def zone_row(z) -> dict:
    inn, out = np.array(z["inner"]), np.array(z["outer"])
    L = np.hypot(*(out - inn).T)
    n = len(L)
    longs = [k for k in range(n) if (k == 0 or L[k] >= L[k - 1]) and (k == n - 1 or L[k] >= L[k + 1])]
    shorts = [k for k in range(n) if 0 < k < n - 1 and L[k] < L[k - 1] and L[k] < L[k + 1]]
    return dict(n=n, at=[float(v) for v in inn.mean(0)],
                long_step=[math.dist(inn[a], inn[b]) for a, b in zip(longs, longs[1:])],
                depth=[(L[k - 1] + L[k + 1]) / 2 - L[k] for k in shorts],
                rel=[1 - L[k] / ((L[k - 1] + L[k + 1]) / 2) for k in shorts],
                short_frac=len(shorts) / max(1, n - 2),
                same_hole=sum(1 for k in range(1, n) if min(math.dist(inn[k], inn[m]) for m in range(k)) < 0.1),
                under1=int((L < 1.0).sum()))


def read(runs) -> list[dict]:
    return [zone_row(z) for r in runs for col in columns_of([tuple(p) for p in r]) for z in zones(col)]


def summary(rows) -> dict:
    ls = [x for z in rows for x in z["long_step"]]
    dp = [x for z in rows for x in z["depth"]]
    rl = [x for z in rows for x in z["rel"]]
    q = lambda v, p: round(float(np.percentile(v, p)), 2) if v else None  # noqa: E731
    return dict(zones=len(rows), crosses=sum(z["n"] for z in rows),
                long_step=q(ls, 50), pile=round(float(np.mean(np.array(ls) < 0.1)), 2) if ls else None,
                depth=q(dp, 50), rel=q(rl, 50),
                short_frac=round(float(np.mean([z["short_frac"] for z in rows])), 2) if rows else None,
                same_hole=sum(z["same_hole"] for z in rows), under1=sum(z["under1"] for z in rows))


def ours_runs(job: str, extra: dict) -> list:
    from tools import column_harness as ch
    J = ch.jobs()[job]
    letters = ch.load_letters(J["letters"])
    letters = {s: v for s, v in letters.items() if any(p(v[0].bounds) for p in J["words"].values())}
    sewn = ch.sew(letters, **extra)
    return ch.ours_points(letters, sewn, list(letters))[0]


def pro_runs(job: str) -> list:
    from tools import column_harness as ch
    from tools import small_text_columns as stc
    if job == "becker":
        return [r for b in stc.read_blocks(BECKER) for r in stc._runs(b)]
    return ch.pro_points(ch.jobs()[job])[0]


CROP_PPM = 100
CROP_HALF_MM = 1.8


def _panel(runs, centre, label: str):
    """Needle paths round `centre`: 1 px lines, needle dots (red)."""
    import cv2
    cx, cy = centre
    x0, y0 = cx - CROP_HALF_MM, cy - CROP_HALF_MM
    size = int(2 * CROP_HALF_MM * CROP_PPM) + 1
    img = np.full((size + 22, size, 3), 255, np.uint8)
    for r in runs:
        q = np.round((np.array(r) - (x0, y0)) * CROP_PPM).astype(np.int32) + (0, 22)
        cv2.polylines(img, [q], False, (60, 60, 60), 1, cv2.LINE_AA)
        for x, y in q:
            if 0 <= x < size and 22 <= y < size + 22:
                cv2.circle(img, (int(x), int(y)), 3, (0, 0, 220), -1, cv2.LINE_AA)
    img[:22] = 255
    cv2.putText(img, label, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return img


def crops(job: str, out: Path, n: int = 4, off: str = "fold", on: str = "fold_on") -> list[Path]:
    """Pivot corners of `job`'s band word, needle paths at `CROP_PPM`: ours
    `off` | ours `on` | the pro's same corner (his zone nearest our corner
    mapped by the word's box). Corners: ours `off`'s zones with the most
    same-hole re-entries, one per letter-sized stretch of the word."""
    import cv2
    from tools import column_harness as ch
    J = ch.jobs()[job]
    letters = ch.load_letters(J["letters"])
    letters = {s: v for s, v in letters.items() if any(p(v[0].bounds) for p in J["words"].values())}
    arms = {}
    for arm in (off, on):
        arms[arm] = ch.ours_points(letters, ch.sew(letters, **ARMS[arm]), list(letters))[0]
    pro, pcs, _t = ch.pro_points(J)
    ob = np.array([p.bounds for p, _kw in letters.values()])
    ox0, oy0, ox1, oy1 = ob[:, 0].min(), ob[:, 1].min(), ob[:, 2].max(), ob[:, 3].max()
    pb = np.array([b.bounds for b in pcs])
    px0, py0, px1, py1 = pb[:, 0].min(), pb[:, 1].min(), pb[:, 2].max(), pb[:, 3].max()

    def to_pro(q):
        return (px0 + (q[0] - ox0) / (ox1 - ox0) * (px1 - px0), py0 + (q[1] - oy0) / (oy1 - oy0) * (py1 - py0))
    ours = sorted(read(arms[off]), key=lambda z: -z["same_hole"])
    pro_z = read(pro)
    picked, paths = [], []
    for z in ours:
        if len(picked) >= n:
            break
        if any(math.dist(z["at"], q) < 2.5 for q in picked):
            continue
        picked.append(z["at"])
        tq = to_pro(z["at"])
        pz = min(pro_z, key=lambda r: math.dist(r["at"], tq)) if pro_z else None
        pc = pz["at"] if pz is not None and math.dist(pz["at"], tq) < 3.0 else tq
        sheet = np.hstack([_panel(arms[off], z["at"], f"ours {off}"),
                           np.full((int(2 * CROP_HALF_MM * CROP_PPM) + 23, 16, 3), 255, np.uint8),
                           _panel(arms[on], z["at"], f"ours {on}"),
                           np.full((int(2 * CROP_HALF_MM * CROP_PPM) + 23, 16, 3), 255, np.uint8),
                           _panel(pro, pc, "pro")])
        path = out / f"{job}_corner_{len(picked)}.png"
        cv2.imwrite(str(path), sheet)
        paths.append(path)
    return paths


def table(res: dict) -> str:
    cols = ["zones", "crosses", "long_step", "pile", "depth", "rel", "short_frac", "same_hole", "under1"]
    lines = ["| job | arm | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for key, row in res.items():
        job, arm = key.split(":")
        lines.append(f"| {job} | {arm} | " + " | ".join(str(row.get(c)) for c in cols) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--jobs", default="fremont,drone,mfab,proseal,becker")
    ap.add_argument("--arms", default="pro,off,on,fold,fold_on")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--crops", type=Path, help="write corner crops (ours fold | fold_on | pro) here, "
                                               "no table")
    args = ap.parse_args(argv)
    if args.crops:
        args.crops.mkdir(parents=True, exist_ok=True)
        for job in args.jobs.split(","):
            if job != "becker":
                print(job, [p.name for p in crops(job, args.crops)], flush=True)
        return 0
    res = {}
    for job in args.jobs.split(","):
        for arm in args.arms.split(","):
            if job == "becker" and arm != "pro":
                continue
            runs = pro_runs(job) if arm == "pro" else ours_runs(job, ARMS[arm])
            res[f"{job}:{arm}"] = summary(read(runs))
            print(json.dumps({"job": job, "arm": arm, **res[f"{job}:{arm}"]}), flush=True)
    print(table(res))
    if args.json:
        args.json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
