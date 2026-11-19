#!/usr/bin/env python
"""Census for a two-tone split of a large dark NEUTRAL stage-2 region (2026-11-19).

Question: on which of the sweep's 44 designs does a stage-2 region exist that is
dark, neutral and holds two large, coherent, well-separated tones (the Precision
Drone's black base: shadows/ring/glass at L* ~2 beside body panels at L* ~20)?

    python -m tools.dark_split_census --out DIR [--only SLUG ...]

Hooks `stage2_photo_segment.split_tonal_regions` (called once with the merged
region list, whatever the flag), records one row per region over MIN_AREA, and
aborts that run (nothing after stage 2 is needed). Writes `census.json`; the
bounds table is `tools.dark_split_census.table` over it. Scratch output only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")
DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

import cv2
import numpy as np

MIN_REGION_MM2 = 100.0     # rows below this are never candidates
CLEAN_PX = 3
NEUTRAL_C = 8.0
THRESHOLDS = (6.0, 8.0, 10.0)
MIN_PIECE_MM2 = 5.0        # a piece counts toward piece_count above this


class _Stop(BaseException):
    pass


def region_row(p, r) -> dict | None:
    from digitizer_core.threads import rgb_to_lab
    k = 1.0 / (p.px_per_mm * p.px_per_mm)
    area = r.area * k
    if area < MIN_REGION_MM2:
        return None
    lab = rgb_to_lab(p.rgb[r.frame_slice()][r.crop].reshape(-1, 3))
    L = lab[:, 0]
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    row = {"area": round(area, 1), "meanL": round(float(L.mean()), 1),
           "chroma": round(float(chroma.mean()), 1), "stdL": round(float(L.std()), 1)}
    # Two tones over the NEUTRAL pixels (chroma <= NEUTRAL_C): "mid" = neutral L* >= T,
    # "black" = the rest (near-black and any chromatic pixels ride with it). A chromatic
    # half (the Drone's blue sky, chroma ~47) must not pose as a tone of its own.
    nmask = chroma <= NEUTRAL_C
    row["neutral_share"] = round(float(nmask.mean()), 2)
    full = np.full(r.crop.shape, -1.0)
    full[r.crop] = np.where(nmask, L, -1.0)
    row["black_area"] = round(float((nmask & (L < 3.0)).sum() * k), 1)
    kern = np.ones((CLEAN_PX, CLEAN_PX), np.uint8)
    row["T"] = {}
    for T in THRESHOLDS:
        m8 = (r.crop & (full >= T)).astype(np.uint8)
        m8 = cv2.morphologyEx(cv2.morphologyEx(m8, cv2.MORPH_OPEN, kern), cv2.MORPH_CLOSE, kern)
        m8 &= r.crop.astype(np.uint8)
        num, lab_, st, _ = cv2.connectedComponentsWithStats(m8)
        areas = {i: st[i, cv2.CC_STAT_AREA] * k for i in range(1, num)}
        out = {}
        for floor in (5.0, 10.0):
            big = {i: a for i, a in areas.items() if a >= floor}
            tot = sum(big.values())
            solid = []
            for i in big:
                cs, _ = cv2.findContours((lab_ == i).astype(np.uint8), cv2.RETR_EXTERNAL,
                                         cv2.CHAIN_APPROX_SIMPLE)
                cnt = max(cs, key=cv2.contourArea)
                hull = cv2.contourArea(cv2.convexHull(cnt))
                solid.append(cv2.contourArea(cnt) / hull if hull > 0 else 0.0)
            sel = np.isin(lab_, list(big)) if big else np.zeros_like(r.crop)
            out[f"f{int(floor)}"] = {
                "mid_area": round(tot, 1), "pieces": len(big),
                "mid_meanL": round(float(full[sel].mean()), 1) if sel.any() else None,
                "solidity": round(float(np.average(solid, weights=list(big.values()))), 2) if big else 0.0,
                "biggest_share": round(max(big.values()) / tot, 2) if big else 0.0,
                "speck_share": round(1 - tot / max(sum(areas.values()), 1e-9), 2)}
        # the other tone: neutral pixels below T, mean L (the near-black thread's colour)
        dm = nmask & (L < T)
        out["dark_area"] = round(float(dm.sum() * k), 1)
        out["dark_meanL"] = round(float(L[dm].mean()), 1) if dm.any() else None
        row["T"][str(T)] = out
    return row


def census_one(row: dict) -> dict:
    from digitizer_core import stage2_photo_segment as s2
    from digitizer_core.pipeline import build_generation
    from digitizer_service.app import _decode
    from tools import pro_pair
    from tools.flag_sweep import _resolve_art
    art = _resolve_art(row, None)
    data = art.read_bytes()
    cfg = pro_pair.config(row["width_mm"], row["garment"], None)
    out: dict = {"slug": row["slug"], "regions": []}
    orig = s2.split_tonal_regions

    def hook(p, kept, split_tonal=False, veto_px=None):
        out["split_tonal_on"] = bool(split_tonal)
        out["n_regions"] = len(kept)
        for r in kept:
            rr = region_row(p, r)
            if rr:
                out["regions"].append(rr)
        raise _Stop()
    s2.split_tonal_regions = hook
    try:
        build_generation(_decode(data), cfg, exif_source=data)
        out["no_stage2_photo"] = True        # this lane never reached the hook
    except _Stop:
        pass
    finally:
        s2.split_tonal_regions = orig
    return out


def qualifies(reg: dict, T: str, floor: str, b: dict) -> bool:
    t = reg["T"][T]
    m = t[floor]
    return (reg["meanL"] <= b["max_meanL"] and reg["neutral_share"] >= b["min_neutral"]
            and m["mid_area"] >= b["min_tone_mm2"] and t["dark_area"] >= b["min_tone_mm2"]
            and (m["mid_meanL"] or 0) - (t["dark_meanL"] or 0) >= b["min_gap"]
            and m["pieces"] <= b["max_pieces"] and m["solidity"] >= b["min_solidity"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--kent-dir", type=Path)
    a = ap.parse_args(argv)
    from tools.flag_sweep import population
    from tools import tripwire as tw
    pop = population(True, True, a.only)
    a.out.mkdir(parents=True, exist_ok=True)
    tws = [r["slug"] for r in pop if r["kind"] == "tripwire"]
    if tws:
        tw.materialise(a.kent_dir or a.out / "_kent", tws)
    rows = []
    for i, row in enumerate(pop, 1):
        t = time.time()
        try:
            r = census_one(row)
        except Exception as e:                      # noqa: BLE001
            r = {"slug": row["slug"], "regions": [], "error": f"{type(e).__name__}: {e}"[:200]}
        rows.append(r)
        print(f"[{i}/{len(pop)}] {row['slug']}: {len(r['regions'])} candidates, "
              f"split_tonal={r.get('split_tonal_on')} {r.get('error','')} ({time.time()-t:.0f}s)", flush=True)
        (a.out / "census.json").write_text(json.dumps({"rows": rows}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
