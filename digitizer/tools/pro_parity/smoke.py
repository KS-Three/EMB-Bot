"""Three designs, one minute: does this change help, or did I look at one number?

Exists because of a specific 2026-08-17 failure. A full corpus arm costs ~6
minutes, so a candidate constant got checked against ONE design, improved it
(hotel_fremont_hat 2.607 -> 0.799 mm), and shipped — while the corpus mean got
worse (1.205 -> 1.359) because the same change more than doubled gaulke and
mfab. The cost of checking was the reason the check did not happen.

The three designs are chosen to span the failure modes that hid that, not to
be representative of anything:

    becker_hat_large    low-resolution art (~4.0 px/mm) — the only rung where
                        stage 4's `eps_px = max(0.5, tol * px_per_mm)` floor
                        bites, which is what silently collapsed two arms of
                        the tolerance ladder into one
    tires_hat_3d        high-resolution, clean, high art_iou — the "nothing
                        should move here" control
    gaulke_roofing_lc   heavily over-covering (engine_extra ~0.75, re-composed
                        by the pro) — moves OPPOSITE to under-covering designs
                        under any coverage-width change, which is exactly the
                        trade a single-design check cannot see

A change that improves all three is probably real. A change that improves one
and worsens another is a re-weighting, and the corpus will say so — but you
now know that in one minute instead of after publishing.

Validated against the failure it exists for. Mean boundary distance, 0.40 mm
paint -> 0.50 mm, on exactly these three:

    becker_hat_large    0.310 -> 0.315
    tires_hat_3d        0.206 -> 0.281
    gaulke_roofing_lc   1.329 -> 3.608

All three worse, one of them nearly tripled. The change that shipped on the
strength of one improving design would have died here, in seconds.

Usage (from digitizer/, with the corpus reachable):
    PRO_PARITY_OUT=<somewhere> python tools/pro_parity/smoke.py
    PRO_PARITY_OUT=<somewhere> PRO_PARITY_SIMPLIFY_TOL=0.1 \
        python tools/pro_parity/smoke.py

Prep is skipped for any design already present in PRO_PARITY_OUT, so a second
run with a different instrument constant costs seconds. Delete the arm dir to
force a re-prep after an ENGINE change.

This is a triage instrument, not evidence. Nothing published should cite it —
run the full corpus for that, and read enginefidelity's FLOOR_* before
believing any delta.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import artfidelity as af  # noqa: E402
import enginefidelity as ef  # noqa: E402

DESIGNS = ["becker_hat_large", "tires_hat_3d", "gaulke_roofing_lc"]
HERE = Path(__file__).resolve().parent


def prep_missing(out: Path):
    want = [d for d in DESIGNS if not (out / "real" / d / "ours_stitches.csv").exists()]
    if not want:
        print(f"all {len(DESIGNS)} designs already prepped in {out}")
        return
    print(f"prepping {len(want)}: {', '.join(want)}", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "prep_both.py"), *want])
    if r.returncode != 0:
        raise SystemExit(f"prep_both failed (exit {r.returncode})")


def measure(out: Path):
    rows = []
    for slug in DESIGNS:
        d = out / "real" / slug
        csv, art = d / "ours_stitches.csv", d / "art.png"
        if not (csv.exists() and art.exists()):
            print(f"{slug:20s} MISSING")
            continue
        E = ef.engine_mask(csv)
        A = af.art_mask(art, (E.shape[1] - ef.MASK_PAD_PX) / af.RES)
        iou, extra, missed, dx, dy = af.best_iou(E, A)
        H = max(E.shape[0], A.shape[0]) + int(2 * af.SHIFT_MM * af.RES) + 4
        W = max(E.shape[1], A.shape[1]) + int(2 * af.SHIFT_MM * af.RES) + 4
        Ep = ef._place(E, H, W)
        Ap = ef._place(A, H, W, int(round(dx * af.RES)), int(round(dy * af.RES)))
        try:
            haus, meanb = ef.boundary_distance_mm(Ep, Ap)
        except ValueError as e:
            print(f"{slug:20s} {iou:7.3f} {extra:9.3f} {missed:10.3f}  ({e})")
            continue
        rows.append((slug, iou, extra, missed, haus, meanb))
        print(f"{slug:20s} {iou:7.3f} {extra:9.3f} {missed:10.3f} "
              f"{haus:7.2f} {meanb:8.3f}", flush=True)
    return rows


def main():
    out = Path(os.environ.get("PRO_PARITY_OUT", ""))
    if not str(out):
        raise SystemExit("set PRO_PARITY_OUT")
    tol = os.environ.get("PRO_PARITY_SIMPLIFY_TOL")
    forced = os.environ.get("PRO_PARITY_FORCED_CLASS")
    print(f"out={out}"
          + (f" | simplify_tol_mm={tol}" if tol else "")
          + (f" | forced_class={forced}" if forced else ""))
    prep_missing(out)
    print(f"\n{'design':20s} {'art_iou':>7s} {'eng_extra':>9s} {'art_missed':>10s} "
          f"{'haus_mm':>7s} {'meanb_mm':>8s}")
    rows = measure(out)
    if rows:
        n = len(rows)
        print(f"\nmean art_iou {sum(r[1] for r in rows)/n:.3f} · "
              f"mean boundary {sum(r[5] for r in rows)/n:.3f} mm · {n} designs")
        print(f"instrument floor: haus {ef.FLOOR_HAUS_MM:.2f} mm, boundary "
              f"{ef.FLOOR_MEANB_MM:.2f} mm — smaller deltas are not signal")
        print("triage only — do not publish a number from three designs")


if __name__ == "__main__":
    main()
