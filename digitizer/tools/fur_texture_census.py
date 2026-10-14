"""Fur needs a texture signal, not ridges: a CENSUS (2026-10-14). Measures only.

    python -m tools.fur_texture_census run    [--fixtures a,b] [--erode-mm 0.5] [--force]
    python -m tools.fur_texture_census table  [--rows rows.json]
    python -m tools.fur_texture_census render [--logo golden_tee] [--signal NAME]

Why. PR #925 (`fur_regions`, `cfg.hair_regions_directional`, OFF) gated fur on
the line route's RIDGE test and found it fires on no fixture: owl_kent's body
reads 0.025 mm of strand per mm2 and region coherence 0.14. This asks the
other question: does ANY per-region texture signal separate the owl's fur from
every logo region, with a margin, on the repo's own fixtures?

Regions. The very ones the pipeline hands `fur_regions.read_regions`:
`build_generation` -> `finish_generation(gen.fork(), cfg)` -> `result.regions`,
filtered as the gate filters them (stitched, `tier == "auto"`). The raster is
the gate's own `SourcePixels` (`gen.p.rgb`, the pre-quantise pixels, the same
mm<->px origin), built here for every lane because the gate itself only runs
on the raster lanes. A region is read on its INTERIOR (its mask eroded by
`--erode-mm`, default 0.5): the region's own boundary is where a colour step
lives, and a step is not texture. Outside the mask the luminance is replaced
by a normalised-convolution extension of the region's own pixels (no edge is
invented at the boundary). A region with no interior has no texture reading
(a stroke); it is counted and left out of every population.

Signals, all on CIE L* of the source pixels, scales in mm (not pixels):
  gabor_pm    Gabor quadrature energy at 8 orientations, peak / mean over
              orientation, at the wavelength with the most energy
              (0.6 / 1.2 / 2.4 mm). 1.0 = isotropic, large = one direction.
  gabor_amp   the peak-orientation amplitude (L* units) at that wavelength.
  st_coh_*    structure-tensor LOCAL coherence, mean over the interior weighted
              by tensor trace, integration scale 0.5 / 1.0 / 2.0 mm.
  st_gcoh     the same tensor summed over the whole region first (what
              `directionfield.region_direction` reads) at 1.0 mm; fur turns,
              so this is expected low.
  orient_rms  sqrt(mean(trace * coherence)) at 1.0 mm, L*/mm: oriented
              gradient strength, texture amplitude and direction in one.
  grad_rms    sqrt(mean(trace)), L*/mm: gradient strength alone.
  hf_frac     variance fraction of the signal above a 0.35 mm Gaussian.
  hf_pow      its absolute std, L* units.
  ridge_dens  the shipped gate's own number (mm of strand per mm2), as the
              baseline the new signals have to beat.

Separation is judged by AUC (positives = fur regions, negatives = every logo
region, P(pos > neg) with ties half) with a stratified percentile bootstrap
CI over REGIONS, and by the margin between the owl body and the highest logo
region. A raw agreement number is never reported (ROADMAP gate 4). Every
number is a property of the FILE (gate 1); nothing here is a candidate
threshold until the PR says so.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT.parent / "docs" / "renders" / "fur-texture-census"
TESTDATA = ROOT / "testdata"
ERODE_MM = 0.5
AREA_FLOOR_MM2 = 25.0           # fur_regions.FUR_MIN_AREA_MM2, restated to keep imports light
GABOR_WAVELENGTHS_MM = (0.6, 1.2, 2.4)
GABOR_ORIENTS = 8
ST_SCALES_MM = (0.5, 1.0, 2.0)
HF_SIGMA_MM = 0.35
FILL_SIGMA_MM = 1.0
RENDER_PX_PER_MM = 6.0
MAX_JPEG_BYTES = 290_000

# 80 mm left chest, the corpus_scorecard's MATRIX[0]; the Studio's route for
# the real photograph, as PR #925 read it.
ROUTES = {
    "file": {"target_width_mm": 80.0, "garment_id": "left_chest"},
    "studio": {"target_width_mm": 80.0, "detect_photographic": True, "faces_route_flat": True},
    "classical": {"target_width_mm": 80.0, "forced_class": "photo_subject", "photo_prep": False},
}
# name -> fixture spec (path[@route]). The nine logos are `studio_raster_census.NINE`.
LOGOS = {
    "tires": "logo_script_tires.png",
    "enthusiast": "photo/enthusiast_logo.png",
    "fremont": "photo/logo_hotel_fremont.webp",
    "bridge": "photo/logo_bridge_bar.jpg",
    "golden_tee": "photo/logo_golden_tee.jpg",
    "gaulke": "photo/logo_gaulke_roofing.png",
    "drone": "photo/drone_render.png",
    "screenshot": "photo/screenshot_phone_ui_golke.jpg",
    "becker": "becker_marine_logo.png",
}
FIXTURES = {
    "owl": "photo/owl_kent.jpg@studio",
    "owl_classical": "photo/owl_kent.jpg@classical",
    "grass": "photo/photo_grass_macro.png",
    "fur_ramp": "photo/fur_ramp.png",
    **LOGOS,
}
SIGNALS = ("gabor_pm", "gabor_amp", "st_coh_0.5", "st_coh_1.0", "st_coh_2.0", "st_gcoh",
           "orient_rms", "grad_rms", "hf_frac", "hf_pow", "ridge_dens")


# --- the signals (pure: a raster and a mask in, numbers out) -----------------

def luminance(rgb: np.ndarray) -> np.ndarray:
    """CIE L* (0..100) of an (H, W, 3) uint8 RGB raster, float32."""
    return cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[..., 0]


def extend(lum: np.ndarray, mask: np.ndarray, sigma_px: float) -> np.ndarray:
    """`lum` inside `mask`; outside it the normalised-convolution extension of
    the inside, so the region's boundary carries no step. A pixel the blur
    cannot reach takes the region's mean."""
    m = mask.astype(np.float32)
    num = cv2.GaussianBlur(lum * m, (0, 0), sigma_px)
    den = cv2.GaussianBlur(m, (0, 0), sigma_px)
    mean = float(lum[mask].mean()) if mask.any() else 0.0
    ext = np.where(den > 1e-3, num / np.maximum(den, 1e-3), mean)
    return np.where(mask, lum, ext).astype(np.float32)


def gabor_bank(wavelength_px: float, orients: int = GABOR_ORIENTS):
    """-> [(even, odd)] real Gabor kernels, DC-free, scaled so a sinusoid of
    amplitude A at the kernel's frequency and orientation reads A (quadrature
    magnitude). sigma = 0.56 wavelength (about one octave)."""
    sigma = 0.56 * wavelength_px
    half = max(2, int(math.ceil(2.5 * sigma)))
    y, x = np.mgrid[-half:half + 1, -half:half + 1].astype(np.float64)
    out = []
    for k in range(orients):
        th = math.pi * k / orients
        u = x * math.cos(th) + y * math.sin(th)
        v = -x * math.sin(th) + y * math.cos(th)
        env = np.exp(-(u * u + v * v) / (2.0 * sigma * sigma))
        even = env * np.cos(2.0 * math.pi * u / wavelength_px)
        odd = env * np.sin(2.0 * math.pi * u / wavelength_px)
        even -= env * (even.sum() / env.sum())
        scale = 2.0 / env.sum()
        out.append(((even * scale).astype(np.float32), (odd * scale).astype(np.float32)))
    return out


def gabor_signals(ext: np.ndarray, interior: np.ndarray, ppm: float) -> dict:
    """Peak / mean energy over orientation, and the peak amplitude, at the
    wavelength with the most mean energy. Wavelengths under 3 px are skipped
    (nothing the raster can carry)."""
    best = None
    for lam_mm in GABOR_WAVELENGTHS_MM:
        lam = lam_mm * ppm
        if lam < 3.0:
            continue
        energy = []
        for even, odd in gabor_bank(lam):
            re = cv2.filter2D(ext, cv2.CV_32F, even, borderType=cv2.BORDER_REFLECT)
            im = cv2.filter2D(ext, cv2.CV_32F, odd, borderType=cv2.BORDER_REFLECT)
            energy.append(float(((re * re + im * im)[interior]).mean()))
        e = np.asarray(energy)
        if best is None or e.mean() > best[1].mean():
            best = (lam_mm, e)
    if best is None:
        return {"gabor_pm": 1.0, "gabor_amp": 0.0}
    _lam, e = best
    mean = float(e.mean())
    return {"gabor_pm": (float(e.max()) / mean) if mean > 1e-9 else 1.0,
            "gabor_amp": math.sqrt(float(e.max()))}


def tensor_signals(ext: np.ndarray, interior: np.ndarray, ppm: float) -> dict:
    """Structure-tensor coherence at ST_SCALES_MM (local, trace-weighted), the
    region-summed coherence at 1.0 mm, and the gradient strengths (L*/mm)."""
    sd = max(0.8, 0.15 * ppm)
    sm = cv2.GaussianBlur(ext, (0, 0), sd)
    gx = cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=3, scale=1.0 / 8.0)
    gy = cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=3, scale=1.0 / 8.0)
    jxx0, jxy0, jyy0 = gx * gx, gx * gy, gy * gy
    out: dict = {}
    for rho_mm in ST_SCALES_MM:
        rho = max(1.0, rho_mm * ppm)
        jxx = cv2.GaussianBlur(jxx0, (0, 0), rho)
        jxy = cv2.GaussianBlur(jxy0, (0, 0), rho)
        jyy = cv2.GaussianBlur(jyy0, (0, 0), rho)
        tr = (jxx + jyy)[interior].astype(np.float64)
        coh = (np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2)[interior]
               / np.maximum((jxx + jyy)[interior], 1e-12)).astype(np.float64)
        wsum = float(tr.sum())
        out[f"st_coh_{rho_mm:.1f}"] = (
            float((tr * coh).sum() / wsum) if wsum > 1e-9 else 0.0)
        if rho_mm == 1.0:
            sxx, sxy, syy = (float(a[interior].sum()) for a in (jxx0, jxy0, jyy0))
            tot = sxx + syy
            out["st_gcoh"] = (math.sqrt((sxx - syy) ** 2 + 4.0 * sxy ** 2) / tot) if tot > 1e-9 else 0.0
            out["orient_rms"] = math.sqrt(float((tr * coh).mean())) * ppm
            out["grad_rms"] = math.sqrt(float(tr.mean())) * ppm
    return out


def hf_signals(ext: np.ndarray, interior: np.ndarray, ppm: float) -> dict:
    hp = ext - cv2.GaussianBlur(ext, (0, 0), max(0.8, HF_SIGMA_MM * ppm))
    var_hp = float(hp[interior].astype(np.float64).var())
    var_all = float(ext[interior].astype(np.float64).var())
    return {"hf_frac": (var_hp / var_all) if var_all > 1e-9 else 0.0, "hf_pow": math.sqrt(var_hp)}


def region_signals(lum: np.ndarray, mask: np.ndarray, ppm: float, erode_mm: float = ERODE_MM):
    """-> dict of SIGNALS (less `ridge_dens`) over `mask`'s interior, or None
    when the region has no interior (a stroke). `lum` is L* of the crop,
    `mask` its region, `ppm` the source pixels per mm."""
    r = int(round(erode_mm * ppm))
    if r > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        interior = cv2.erode(mask.astype(np.uint8), k).astype(bool)
    else:
        interior = mask.astype(bool)
    if interior.sum() < 25:
        return None
    ext = extend(lum.astype(np.float32), mask.astype(bool), max(1.0, FILL_SIGMA_MM * ppm))
    out = {**gabor_signals(ext, interior, ppm), **tensor_signals(ext, interior, ppm),
           **hf_signals(ext, interior, ppm)}
    out["interior_mm2"] = float(interior.sum()) / (ppm * ppm)
    return out


# --- separation statistics ---------------------------------------------------

def auc(pos, neg) -> float:
    """P(pos > neg), ties half. Rank-free exact O(n*m); the populations are tens."""
    p = np.asarray(pos, float)[:, None]
    n = np.asarray(neg, float)[None, :]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def bootstrap_auc(pos, neg, reps: int = 2000, seed: int = 0):
    """Stratified percentile bootstrap over REGIONS (positives and negatives
    resampled separately), 95%. Deterministic (seeded). -> (auc, lo, hi)."""
    pos = np.asarray(pos, float)
    neg = np.asarray(neg, float)
    rng = np.random.default_rng(seed)
    vals = np.empty(reps)
    for i in range(reps):
        vals[i] = auc(rng.choice(pos, pos.size), rng.choice(neg, neg.size))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return auc(pos, neg), float(lo), float(hi)


# --- reading a fixture --------------------------------------------------------

def split(spec: str) -> tuple[str, str]:
    path, _, route = spec.partition("@")
    return path, route or "file"


def _mask_for(poly, sp, box_px):
    """Bool mask of `poly` on the crop `box_px` = (x0, y0, x1, y1), holes cut,
    with `to_px`-then-`fillPoly`, the convention the blend tier and
    `directionfield` use."""
    x0, y0, x1, y1 = box_px
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)

    def ring(coords):
        return np.array([[sp.to_px(x, y)[0] - x0, sp.to_px(x, y)[1] - y0] for x, y in coords], np.int32)

    for g in getattr(poly, "geoms", [poly]):
        cv2.fillPoly(m, [ring(g.exterior.coords)], 255)
        for hole in g.interiors:
            cv2.fillPoly(m, [ring(hole.coords)], 0)
    return m.astype(bool)


def read_fixture(spec: str, erode_mm: float = ERODE_MM, keep: dict | None = None) -> dict:
    from digitizer_core import PipelineConfig, fur_regions
    from digitizer_core.pipeline import build_generation, finish_generation
    from digitizer_core.stage6_blend import SourcePixels

    path, route = split(spec)
    cfg = PipelineConfig(**ROUTES[route])
    gen = build_generation(TESTDATA / path, cfg)
    res = finish_generation(gen.fork(), cfg)
    p = gen.p
    x0, y0, x1, y1 = p.art_bbox
    sp = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm, origin_px=((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                      gradient_class=False, subject_mask=gen.subject_mask)
    # Exactly the regions the gate reads: stitched, auto tier.
    regions = [r for r in res.regions
               if r.meta.get("stitched", True) and str(r.meta.get("tier", "auto")).lower() == "auto"]
    ridge = fur_regions.read_regions(res.regions, sp, cfg)
    lum_full = luminance(p.rgb)
    h, w = lum_full.shape
    pad = int(math.ceil(4.0 * p.px_per_mm))        # past the widest kernel's reach
    rows, no_interior = [], 0
    for r in regions:
        if r.area_mm2 < AREA_FLOOR_MM2:
            continue
        minx, miny, maxx, maxy = r.polygon.bounds
        ax, ay = sp.to_px(minx, miny)
        bx, by = sp.to_px(maxx, maxy)
        box = (max(0, int(math.floor(min(ax, bx))) - pad), max(0, int(math.floor(min(ay, by))) - pad),
               min(w, int(math.ceil(max(ax, bx))) + pad), min(h, int(math.ceil(max(ay, by))) + pad))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        mask = _mask_for(r.polygon, sp, box)
        sig = region_signals(lum_full[box[1]:box[3], box[0]:box[2]], mask, p.px_per_mm, erode_mm)
        if sig is None:
            no_interior += 1
            continue
        rd = ridge.get(r.shape_id, {})
        rows.append({"id": r.shape_id, "area_mm2": round(float(r.area_mm2), 2),
                     "width_mm": rd.get("width_mm"), "strands": rd.get("strands"),
                     "ridge_gate_fur": rd.get("fur"),
                     "mean_rgb": [int(v) for v in p.rgb[box[1]:box[3], box[0]:box[2]][mask].mean(axis=0)],
                     "ridge_dens": rd.get("density", 0.0),
                     **{k: round(float(v), 5) for k, v in sig.items()}})
    if keep is not None:
        keep.update(sp=sp, regions=regions, res=res)
    return {"fixture": path, "route": route, "class": res.design_class,
            "px_per_mm": round(float(p.px_per_mm), 3), "erode_mm": erode_mm,
            "regions_total": len(res.regions), "regions_read": len(regions),
            "regions_over_floor": sum(r.area_mm2 >= AREA_FLOOR_MM2 for r in regions),
            "no_interior": no_interior, "regions": rows}


def _load(out: Path) -> dict:
    f = out / "rows.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = args.fixtures.split(",") if args.fixtures else list(FIXTURES)
    for name in names:
        rows = _load(out)
        if name in rows and "error" not in rows[name] and not args.force and \
                rows[name].get("erode_mm") == args.erode_mm:
            print(f"{name}: cached", flush=True)
            continue
        try:
            rows[name] = read_fixture(FIXTURES.get(name, name), args.erode_mm)
            rows[name]["name"] = name
            r = rows[name]
            print(f"{name}: class {r['class']} {r['px_per_mm']} px/mm, regions over floor "
                  f"{r['regions_over_floor']}, read {len(r['regions'])}, no interior {r['no_interior']}",
                  flush=True)
        except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
            rows[name] = {"name": name, "error": f"{type(exc).__name__}: {exc}"}
            print(f"{name}: ERROR {rows[name]['error']}", flush=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


# --- the table ------------------------------------------------------------------

OWL_FUR_MIN_WIDTH_MM = 3.0


def populations(rows: dict, fur_ids: list[str] | None = None):
    """-> (owl body row, fur positives [(label, row)], logo negatives [(label, row)]).

    The owl body is the largest region of owl_kent on the Studio route. Fur
    positives are the owl regions at least `OWL_FUR_MIN_WIDTH_MM` wide (a field,
    not a stroke), unless `fur_ids` names them (a render-checked list)."""
    owl = rows["owl"]["regions"]
    body = max(owl, key=lambda r: r["area_mm2"])
    if fur_ids is None:
        pos = [("owl", r) for r in owl if (r.get("width_mm") or 0) >= OWL_FUR_MIN_WIDTH_MM]
    else:
        pos = [("owl", r) for r in owl if r["id"] in fur_ids]
    neg = [(n, r) for n in LOGOS if n in rows and "regions" in rows[n] for r in rows[n]["regions"]]
    return body, pos, neg


def table_rows(rows: dict, fur_ids: list[str] | None = None) -> list[dict]:
    body, pos, neg = populations(rows, fur_ids)
    grass = max(rows["grass"]["regions"], key=lambda r: r["area_mm2"]) if rows.get("grass", {}).get("regions") else None
    ramp = rows.get("fur_ramp", {}).get("regions") or []
    ramp_max = None
    out = []
    for sig in SIGNALS:
        nv = [r[sig] for _n, r in neg]
        pv = [r[sig] for _n, r in pos]
        a, lo, hi = bootstrap_auc(pv, nv) if pv and nv else (float("nan"),) * 3
        top = max(neg, key=lambda t: t[1][sig])
        owl_v = body[sig]
        ramp_v = max((r[sig] for r in ramp), default=None)
        out.append({"signal": sig, "owl_body": owl_v, "grass": None if grass is None else grass[sig],
                    "fur_ramp_max": ramp_v, "logo_max": top[1][sig], "logo_max_at": f"{top[0]} {top[1]['id']}",
                    "margin_abs": owl_v - top[1][sig],
                    "margin_ratio": (owl_v / top[1][sig]) if top[1][sig] > 1e-9 else float("inf"),
                    "owl_rank_in_negatives": int(sum(v < owl_v for v in nv)), "n_neg": len(nv),
                    "n_pos": len(pv), "auc": a, "auc_lo": lo, "auc_hi": hi,
                    "separates": bool(owl_v > top[1][sig] and lo > 0.9)})
    return out


def _f(v, n=3):
    return "-" if v is None else ("inf" if v == float("inf") else f"{v:.{n}g}")


def markdown(rows: dict, fur_ids: list[str] | None = None) -> str:
    body, pos, neg = populations(rows, fur_ids)
    tr = table_rows(rows, fur_ids)
    lines = [f"Regions: area >= {AREA_FLOOR_MM2:g} mm2, interior after {rows['owl']['erode_mm']:g} mm erosion, "
             "80 mm; owl_kent on the Studio route, the rest on the file route (80 mm left_chest).", "",
             f"Owl body = {body['id']} ({body['area_mm2']:.0f} mm2). Fur positives (n={len(pos)}): "
             + ", ".join(f"{r['id']} ({r['area_mm2']:.0f} mm2, {r['width_mm']} mm wide)" for _n, r in pos)
             + f". Logo negatives: n={len(neg)} regions over {len({n for n, _ in neg})} logos.", "",
             "| signal | owl body | grass (largest) | fur_ramp (max disc) | max over logo regions | at | margin (owl - max) | owl / max "
             "| owl beats N of n logo regions | AUC [95% CI] | clears |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in tr:
        lines.append(f"| {t['signal']} | {_f(t['owl_body'])} | {_f(t['grass'])} | {_f(t['fur_ramp_max'])} | "
                     f"{_f(t['logo_max'])} | {t['logo_max_at']} | {_f(t['margin_abs'])} | {_f(t['margin_ratio'])} | "
                     f"{t['owl_rank_in_negatives']} of {t['n_neg']} | {t['auc']:.2f} [{t['auc_lo']:.2f}, {t['auc_hi']:.2f}] | "
                     f"{'**yes**' if t['separates'] else 'no'} |")
    lines += ["", "clears = owl body above EVERY logo region AND the AUC's lower bound above 0.90.", "",
              "### Per-fixture counts", "", "| fixture | class | px/mm | regions >= floor | read | no interior |",
              "|---|---|---|---|---|---|"]
    for n, r in rows.items():
        if "error" in r:
            lines.append(f"| {n} | ERROR {r['error']} | | | | |")
        else:
            lines.append(f"| {n} | {r['class']} | {r['px_per_mm']} | {r['regions_over_floor']} | "
                         f"{len(r['regions'])} | {r['no_interior']} |")
    return "\n".join(lines) + "\n"


def cmd_table(args) -> int:
    out = Path(args.out)
    rows = _load(out)
    fur_ids = args.fur_ids.split(",") if args.fur_ids else None
    text = markdown(rows, fur_ids)
    (out / "table.md").write_text(text, encoding="utf-8")
    (out / "table.json").write_text(json.dumps(table_rows(rows, fur_ids), indent=1) + "\n", encoding="utf-8")
    print(text)
    return 0


# --- the render -------------------------------------------------------------------

def _heat(v, lo, hi):
    t = 0.0 if hi <= lo else min(1.0, max(0.0, (v - lo) / (hi - lo)))
    c = cv2.applyColorMap(np.array([[int(round(t * 255))]], np.uint8), cv2.COLORMAP_INFERNO)[0, 0]
    return tuple(int(x) for x in c)


def _write_jpeg(path: Path, img) -> None:
    q = 85
    while True:
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
        if len(buf) <= MAX_JPEG_BYTES or (q <= 60 and img.shape[1] < 400):
            break
        if q > 60:
            q -= 8
        else:
            img = cv2.resize(img, (img.shape[1] * 4 // 5, img.shape[0] * 4 // 5), interpolation=cv2.INTER_AREA)
    path.write_bytes(buf.tobytes())


def _tile(spec: str, name: str, rows: dict, signal: str, lo: float, hi: float, erode_mm: float):
    """Source | per-region heat of `signal` for one fixture, same colour scale."""
    keep: dict = {}
    read_fixture(spec, erode_mm, keep)
    sp = keep["sp"]
    by_id = {r["id"]: r for r in rows[name]["regions"]}
    src = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2BGR)
    scale = RENDER_PX_PER_MM / sp.px_per_mm
    src = cv2.resize(src, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    heat = (src * 0.35 + 255 * 0.65).astype(np.uint8)
    for r in keep["regions"]:
        row = by_id.get(r.shape_id)
        col = (200, 200, 200) if row is None else _heat(row[signal], lo, hi)
        for g in getattr(r.polygon, "geoms", [r.polygon]):
            ring = np.array([[sp.to_px(x, y)[0] * scale, sp.to_px(x, y)[1] * scale] for x, y in g.exterior.coords], np.int32)
            cv2.fillPoly(heat, [ring], col)
            for hole in g.interiors:
                hr = np.array([[sp.to_px(x, y)[0] * scale, sp.to_px(x, y)[1] * scale] for x, y in hole.coords], np.int32)
                cv2.fillPoly(heat, [hr], (255, 255, 255))
        if row is not None and row["area_mm2"] >= 120:
            cx, cy = r.polygon.representative_point().x, r.polygon.representative_point().y
            px, py = sp.to_px(cx, cy)
            cv2.putText(heat, f"{row[signal]:.3g}", (int(px * scale) - 20, int(py * scale)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(heat, f"{row[signal]:.3g}", (int(px * scale) - 20, int(py * scale)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return src, heat


def _panel(img, label):
    band = np.full((30, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def cmd_render(args) -> int:
    out = Path(args.out)
    rows = _load(out)
    sig = args.signal
    names = ["owl", args.logo]
    vals = [r[sig] for n in names for r in rows[n]["regions"]]
    lo, hi = min(vals), max(vals)
    tiles = []
    for n in names:
        src, heat = _tile(FIXTURES[n], n, rows, sig, lo, hi, rows[n]["erode_mm"])
        tiles += [_panel(src, f"{n}: source"), _panel(heat, f"{n}: {sig} per region ({lo:.3g} dark .. {hi:.3g} light)")]
    h = max(t.shape[0] for t in tiles)
    pad = [np.vstack([t, np.full((h - t.shape[0], t.shape[1], 3), 255, np.uint8)]) for t in tiles]
    top = np.hstack([pad[0], np.full((h, 8, 3), 255, np.uint8), pad[1]])
    bot = np.hstack([pad[2], np.full((h, 8, 3), 255, np.uint8), pad[3]])
    w = max(top.shape[1], bot.shape[1])
    fit = lambda a: np.hstack([a, np.full((a.shape[0], w - a.shape[1], 3), 255, np.uint8)])  # noqa: E731
    img = np.vstack([fit(top), np.full((8, w, 3), 255, np.uint8), fit(bot)])
    path = out / f"owl_vs_{args.logo}_{sig}.jpg"
    _write_jpeg(path, img)
    print(json.dumps({"written": path.name, "signal": sig, "scale": [lo, hi]}))
    return 0


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", default="")
    r.add_argument("--erode-mm", type=float, default=ERODE_MM)
    r.add_argument("--force", action="store_true")
    r.set_defaults(fn=cmd_run)
    t = sub.add_parser("table")
    t.add_argument("--fur-ids", default="", help="comma list of owl region ids to use as fur positives")
    t.set_defaults(fn=cmd_table)
    d = sub.add_parser("render")
    d.add_argument("--logo", default="golden_tee", choices=list(LOGOS))
    d.add_argument("--signal", default="gabor_amp", choices=list(SIGNALS))
    d.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
