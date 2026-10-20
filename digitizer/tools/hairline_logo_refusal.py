"""Hair line supplement: refuse rendered-logo line detail (2026-10-15).

    python -m tools.hairline_logo_refusal probe [--only drone,owl_kent]
    python -m tools.hairline_logo_refusal logos [--only drone,screenshot]
    python -m tools.hairline_logo_refusal owl [--arms region,supp,refuse]
    python -m tools.hairline_logo_refusal drawn
    python -m tools.hairline_logo_refusal table | render [--only drone]

#942's supplement (`cfg.hairline_lines_gradient`, OFF) moves 3 of the 9
corpus logos (drone, screenshot, golden_tee): it sews highlights, hatching
and bevel edges of rendered art as if they were hair. `probe` plans the
supplement arm once per design and records, for every strand that SURVIVES
#942's two refusals, the features a third refusal could read: the host
shape the strand lies on, that shape's tone spread and grain (source L*
minus a blur of itself, over the shape's own pixels), and the same in a
band beside the strand. Every number is a property of the FILE, not of
cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import shapely

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import stage6_hairline_lines as L  # noqa: E402
from digitizer_core import stage7_sequence as S7  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import hair_reach as hr  # noqa: E402
from tools import hairline_lines_gradient as G  # noqa: E402
from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases  # noqa: E402

DEBUG = ROOT / "debug_out" / "hairline_logo_refusal"
OWL_WIDTH = G.OWL_WIDTH
GRAIN_SIGMAS = (1.0, 2.0, 4.0)


def _cases(only):
    out = [(n, p, w, dict(garment_id=g, max_colors=STUDIO_MAX_COLORS))
           for n, p, w, g in corpus_cases()]
    out.append(("owl_kent", hr.IMAGES["owl_kent"], OWL_WIDTH, {}))
    return [c for c in out if not only or c[0] in only]


def _mask(poly, sp, shape) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    geoms = getattr(poly, "geoms", [poly])
    for g in geoms:
        if g.is_empty:
            continue
        def px(ring):
            c = np.asarray(ring.coords, np.float64)
            return np.round(np.c_[c[:, 0] * sp.px_per_mm + sp.origin_px[0],
                                  c[:, 1] * sp.px_per_mm + sp.origin_px[1]]).astype(np.int32)
        cv2.fillPoly(m, [px(g.exterior)], 1)
        for h in g.interiors:
            cv2.fillPoly(m, [px(h)], 0)
    return m.astype(bool)


def _line_mask(pts, sp, shape, r: int) -> np.ndarray:
    m = np.zeros(shape, np.uint8)
    q = np.round(np.array([sp.to_px(x, y) for x, y in pts])).astype(np.int32)
    cv2.polylines(m, [q], False, 1, thickness=2 * r + 1)
    return m.astype(bool)


class Probe:
    """Wraps stage 7's `hairline_supplement_test`: every strand its refuse
    lets through is recorded with its features."""

    def __init__(self, image: str):
        self.image = image
        self.rows: list[dict] = []

    def __call__(self, regions, walked, sp, cfg):
        refuse = L.supplement_test(regions, walked, sp, cfg)
        light = L._light(sp)
        shape = light.shape
        small, std4, f4 = _texture(sp)
        bounds = shapely.union_all([r.polygon.boundary for r in regions])
        shapely.prepare(bounds)
        # Every FDoG line, both polarities, ridge or not.
        sampler, gray = L.field_gray(sp)
        every = []
        for g in (gray, 1.0 - gray):
            H = L.fdog_response(g, sampler.field.tangent)
            lmap = L._fill_slits(L.fdog_threshold(H, sampler.field.tangent,
                                                  sampler.field.coherence))
            every += [shapely.LineString(p) for p in
                      L.lines_from_map(lmap, sp, sampler.scale, min_len_mm=0.0) if len(p) >= 2]
        etree = shapely.STRtree(every)
        seen = set()
        resid = {s: np.abs(light - cv2.GaussianBlur(light, (0, 0), s)) for s in GRAIN_SIGMAS}
        tree = shapely.STRtree([r.polygon for r in regions])
        host_stats: dict[int, dict] = {}

        def stats_for(j):
            if j not in host_stats:
                m = _mask(regions[j].polygon, sp, shape)
                d = {"px": int(m.sum())}
                if m.any():
                    d["tone_std"] = round(float(light[m].std()), 2)
                    for s in GRAIN_SIGMAS:
                        d[f"grain_s{s:g}"] = round(float(np.median(resid[s][m])), 3)
                host_stats[j] = (m, d)
            return host_stats[j]

        def wrapped(s):
            why = refuse(s)
            if why is not None:
                return why
            x, y = L._samples(s["pts"])
            hit = tree.query(shapely.points(x, y), predicate="within")
            top = np.full(len(x), -1)
            for i, j in zip(hit[0].tolist(), hit[1].tolist()):
                top[i] = max(top[i], j)
            on = top[top >= 0]
            row = {"polarity": s["polarity"], "length_mm": round(s["length_mm"], 2),
                   "contrast": round(s["contrast"], 1), "strength": round(s["strength"], 3),
                   "stack": s.get("stack"), "on_shape_share": round(float(np.mean(top >= 0)), 2)}
            key = (s["polarity"], tuple(np.round(s["pts"][0], 3)), round(s["length_mm"], 3))
            if key in seen:
                return None
            seen.add(key)
            q = np.array([sp.to_px(a, b) for a, b in s["pts"]]).mean(axis=0)
            h, w = shape
            row["zone"] = hr.zone_of(self.image, q[0] / w, q[1] / h)
            row["pts"] = [[round(a, 3), round(b, 3)] for a, b in s["pts"]]
            bd_any = shapely.distance(bounds, shapely.points(x, y))
            row["any_edge_share_0.3"] = round(float(np.mean(bd_any < 0.3)), 2)
            row["any_edge_share_0.15"] = round(float(np.mean(bd_any < 0.15)), 2)
            ls = shapely.LineString(s["pts"])
            near = etree.query(ls, predicate="dwithin", distance=1.5)
            buf = ls.buffer(1.5)
            other = sum(every[i].intersection(buf).length for i in near.tolist()
                        if every[i].hausdorff_distance(ls) > 0.3)
            row["nbr_mm_per_mm"] = round(other / max(s["length_mm"], 1e-6), 2)
            band4 = _line_mask(s["pts"], _scaled(sp, f4), small.shape, 4) \
                & ~_line_mask(s["pts"], _scaled(sp, f4), small.shape, 1)
            if band4.any():
                b = std4[band4]
                row["band4_std_med"] = round(float(np.median(b)), 2)
                row["band4_flat1"] = round(float(np.mean(b < 1.0)), 2)
                row["band4_tone_std"] = round(float(small[band4].std()), 2)
            if len(on):
                j = int(np.bincount(on).argmax())
                poly = regions[j].polygon
                row["host"] = j
                row["host_width_mm"] = round(2.0 * poly.area / poly.length, 2)
                row["host_area_mm2"] = round(poly.area, 1)
                bd = shapely.distance(poly.boundary, shapely.points(x, y))
                row["edge_share_0.3"] = round(float(np.mean(bd < 0.3)), 2)
                m, d = stats_for(j)
                row.update({f"host_{k}": v for k, v in d.items()})
                core = _line_mask(s["pts"], sp, shape, 2)
                band = _line_mask(s["pts"], sp, shape, 8) & ~core & m
                row["band_px"] = int(band.sum())
                if band.any():
                    row["band_tone_std"] = round(float(light[band].std()), 2)
                    for sg in GRAIN_SIGMAS:
                        row[f"band_grain_s{sg:g}"] = round(float(np.median(resid[sg][band])), 3)
                rest = m & ~core
                if rest.any():
                    for sg in GRAIN_SIGMAS:
                        row[f"host_rest_grain_s{sg:g}"] = round(
                            float(np.median(resid[sg][rest])), 3)
            self.rows.append(row)
            return None
        return wrapped


def cmd_probe(only) -> int:
    DEBUG.mkdir(parents=True, exist_ok=True)
    orig = S7.hairline_supplement_test
    try:
        for name, path, width, kw in _cases(only):
            t0 = time.time()
            cfg = G.cfg_for("supp", width, **kw)
            result = run_stages(path, cfg)
            probe = Probe(name)
            S7.hairline_supplement_test = probe
            plan = plan_stitches(result, cfg)
            S7.hairline_supplement_test = orig
            light = L._light(result.source_pixels)
            g = {f"image_grain_s{s:g}": round(float(np.median(
                np.abs(light - cv2.GaussianBlur(light, (0, 0), s)))), 3) for s in GRAIN_SIGMAS}
            row = {"image": name, "width_mm": width, "design_class": result.design_class,
                   "raster": list(result.source_pixels.rgb.shape[:2]), **g,
                   "trims": plan.stats.trims, "strands": probe.rows,
                   "seconds": round(time.time() - t0)}
            (DEBUG / f"probe_{name}.json").write_text(json.dumps(row, indent=1) + "\n",
                                                    encoding="utf-8")
            print(json.dumps({k: v for k, v in row.items() if k != "strands"}),
                  len(probe.rows), flush=True)
    finally:
        S7.hairline_supplement_test = orig
    return 0


def _texture(sp, grid: float = 4.0):
    """(L* at `grid` px/mm, its 3x3 local std, the scale factor)."""
    light = L._light(sp)
    f = grid / sp.px_per_mm
    small = cv2.resize(light, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    m = cv2.blur(small, (3, 3))
    sq = cv2.blur(small * small, (3, 3))
    return small, np.sqrt(np.maximum(sq - m * m, 0.0)), f


def _scaled(sp, f):
    """`sp`'s mm -> px mapping at `f` times its density."""
    class _S:
        px_per_mm = sp.px_per_mm * f
        origin_px = (sp.origin_px[0] * f, sp.origin_px[1] * f)

        @staticmethod
        def to_px(x, y):
            return (x * _S.px_per_mm + _S.origin_px[0], y * _S.px_per_mm + _S.origin_px[1])
    return _S


def _mask_scaled(poly, sp, f, shape):
    return _mask(poly, _scaled(sp, f), shape)


def cmd_census(only) -> int:
    """Design-level texture of every region: at a common 4 px/mm, the share
    of each region's pixels whose 3x3 L* std is under 0.5 / 1 / 2 L*."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    cases = _cases(only) + [(n, hr.IMAGES[n], hr.DRAWN_WIDTH, {}) for n in hr.DRAWN
                            if not only or n in only]
    for name, path, width, kw in cases:
        result = run_stages(path, cfg_arm("base", width, **kw))
        sp = result.source_pixels
        row = {"image": name, "design_class": result.design_class}
        if sp is not None:
            small, std, f = _texture(sp)
            regs, tot = [], {0.5: 0, 1.0: 0, 2.0: 0, "px": 0}
            for r in result.regions:
                m = _mask_scaled(r.polygon, sp, f, small.shape)
                n = int(m.sum())
                if not n:
                    continue
                s = std[m]
                d = {"px": n, "width_mm": round(2 * r.polygon.area / r.polygon.length, 2),
                     "tone_std": round(float(small[m].std()), 2),
                     "std_med": round(float(np.median(s)), 3)}
                for t in (0.5, 1.0, 2.0):
                    k = int((s < t).sum())
                    d[f"flat{t:g}"] = round(k / n, 3)
                    tot[t] += k
                tot["px"] += n
                regs.append(d)
            row.update({f"flat{t:g}": round(tot[t] / max(tot["px"], 1), 3) for t in (0.5, 1.0, 2.0)})
            row["regions"] = regs
        _write_quiet(row, f"census_{name}")
    return 0


class _CachedSP:
    def __init__(self, rgb, px_per_mm, origin_px):
        self.rgb, self.px_per_mm, self.origin_px = rgb, float(px_per_mm), tuple(origin_px)

    def to_px(self, x, y):
        return (x * self.px_per_mm + self.origin_px[0], y * self.px_per_mm + self.origin_px[1])


def _sp_cached(name: str):
    f = DEBUG / f"sp_{name}.npz"
    if not f.exists():
        path, width, kw = next((p, w, k) for n, p, w, k in _cases({name}))
        sp = run_stages(path, cfg_arm("base", width, **kw)).source_pixels
        np.savez(f, rgb=sp.rgb, ppm=sp.px_per_mm, origin=np.array(sp.origin_px))
    z = np.load(f)
    return _CachedSP(z["rgb"], z["ppm"], z["origin"])


def jitter(pts, small, sp4, *, polarity: str, side_mm: float = 0.0, step_px: float = 1.0):
    """Median |second difference| of L* sampled along the polyline `pts` (mm)
    on the common grid `small` (`sp4` its mapping), every `step_px` grid
    pixels: the line's own tone (extreme within one pixel across) when
    `side_mm` is 0, else the ground `side_mm` either side (both sides'
    values, each its own sequence)."""
    seqs = []
    res = L._resample([tuple(p) for p in pts], step_px / sp4.px_per_mm)
    if len(res) < 5:
        return None
    h, w = small.shape
    def at(t):
        X = np.array([sp4.to_px(x + t * nx, y + t * ny)[0] for (x, y), (nx, ny) in res], np.float32)
        Y = np.array([sp4.to_px(x + t * nx, y + t * ny)[1] for (x, y), (nx, ny) in res], np.float32)
        X, Y = np.clip(X, 0, w - 1), np.clip(Y, 0, h - 1)
        return cv2.remap(small, X.reshape(1, -1), Y.reshape(1, -1), cv2.INTER_LINEAR).ravel()
    if side_mm == 0.0:
        d = 1.0 / sp4.px_per_mm
        stack = np.vstack([at(-d), at(0.0), at(d)])
        seqs.append(stack.min(axis=0) if polarity == "dark" else stack.max(axis=0))
    else:
        seqs += [at(-side_mm), at(side_mm)]
    vals = [np.abs(s[:-2] - 2 * s[1:-1] + s[2:]) for s in seqs]
    return round(float(np.median(np.concatenate(vals))), 3)


def cmd_features(only) -> int:
    """Along-line features of the probe's strands, from the cached raster."""
    lo = 2.2
    for name in only or ("golden_tee", "screenshot", "drone", "owl_kent"):
        d = json.loads((DEBUG / f"probe_{name}.json").read_text(encoding="utf-8"))
        sp = _sp_cached(name)
        out = {}
        for grid in (4.0, 8.0):
            small, _std, f = _texture(sp, grid)
            out[grid] = (small, _scaled(sp, f))
        seen = set()
        print("==", name)
        for s in d["strands"]:
            k = (s["polarity"], str(s["pts"][0]), s["length_mm"])
            if s["length_mm"] < lo or k in seen:
                continue
            seen.add(k)
            row = [s["polarity"][0], s["zone"][:5], s["length_mm"], s["contrast"]]
            for grid, (small, sp4) in out.items():
                row += [jitter(s["pts"], small, sp4, polarity=s["polarity"]),
                        jitter(s["pts"], small, sp4, polarity=s["polarity"], side_mm=0.5)]
            print(" ".join(str(v)[:7].ljust(7) for v in row))
    return 0


def _write_quiet(row: dict, name: str) -> None:
    (DEBUG / f"{name}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in row.items() if k != "regions"}), flush=True)


# ------------------------------------------------------------- measurement

FLAG = "hairline_lines_logo_refusal"
# arm -> extra cfg over the Studio route (`G.cfg_for`'s base arms).
ARMS = {"off": ("off", {}), "region": ("region", {}), "base": ("base", {}),
        "supp": ("supp", {}), "refuse": ("supp", {FLAG: True})}
LABELS = {"off": "OFF", "region": "hairline ON (regions)",
          "base": "supplement OFF (hairline + from_lines + strand test)",
          "supp": "supplement ON (#942)", "refuse": f"supplement ON + {FLAG}"}


def cfg_arm(arm: str, width: float, **kw):
    base, extra = ARMS[arm]
    return G.cfg_for(base, width, **extra, **kw)


def _measure(plan, image, sp) -> dict:
    m = G.measure(plan, image, sp)
    _reg, sup = G.tier_warnings(plan)
    for k in L.LOGO_KEYS:
        if sup and k in sup:
            m["supplement"][k] = sup[k]
    m["lines_kept"] = (sup or {}).get("strands", 0)
    return m


def cmd_logos(only, arms=("base", "supp", "refuse")) -> int:
    """The nine logos, three plans from one `run_stages` each."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    for name, path, width, kw in _cases(only):
        if name == "owl_kent":
            continue
        t0 = time.time()
        result = run_stages(path, cfg_arm("base", width, **kw))
        plans = {a: plan_stitches(result, cfg_arm(a, width, **kw)) for a in arms}
        row = {"logo": name, "file": path.name, "width_mm": width,
               "garment": kw["garment_id"], "design_class": result.design_class}
        for a, plan in plans.items():
            row[a] = _measure(plan, name, result.source_pixels)
        cfg = cfg_arm("base", width, **kw)
        bare = {a: G._bare(p, result, path, cfg) for a, p in plans.items()
                if a != "base" and row[a]["md5"] != row["base"]["md5"]}
        if bare:
            b0 = G._bare(plans["base"], result, path, cfg)
            for a, b in bare.items():
                row[a]["bare_new_vs_base_mm2"] = round(G.bare_new_mm2(b, b0), 2)
        row["seconds"] = round(time.time() - t0)
        _write(row, f"logo_{name}")
    return 0


def _write(row: dict, name: str) -> dict:
    (DEBUG / f"{name}.json").write_text(json.dumps(row, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(row), flush=True)
    return row


def cmd_owl(arms) -> int:
    """owl_kent on the Studio route: stages once, one plan per arm; bare
    fabric read against the region arm (planned first)."""
    from digitizer_core.adapter import plan_to_design
    DEBUG.mkdir(parents=True, exist_ok=True)
    path = hr.IMAGES["owl_kent"]
    result = run_stages(path, cfg_arm("base", OWL_WIDTH))
    ref = None
    for a in ["region"] + [a for a in arms if a != "region"]:
        t0 = time.time()
        cfg = cfg_arm(a, OWL_WIDTH)
        plan = plan_stitches(result, cfg)
        row = {"image": "owl_kent", "width_mm": OWL_WIDTH, "arm": a,
               "design_class": result.design_class,
               **_measure(plan, "owl_kent", result.source_pixels)}
        bare = G._bare(plan, result, path, cfg)
        row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
        if ref is None:
            ref = bare
        row["bare_new_vs_region_mm2"] = round(G.bare_new_mm2(bare, ref), 2)
        (DEBUG / f"owl_kent_{a}_design.json").write_text(
            json.dumps(plan_to_design(plan, name=f"owl_kent {a}")), encoding="utf-8")
        row["seconds"] = round(time.time() - t0)
        _write(row, f"owl_kent_{a}")
    return 0


def cmd_drawn() -> int:
    """hair_strands / hair_fine at 80 mm: region, supp and refuse plan md5."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    for image in hr.DRAWN:
        result = run_stages(hr.IMAGES[image], cfg_arm("off", hr.DRAWN_WIDTH))
        row = {"image": image, "width_mm": hr.DRAWN_WIDTH, "design_class": result.design_class}
        for a in ("region", "supp", "refuse"):
            row[a] = _measure(plan_stitches(result, cfg_arm(a, hr.DRAWN_WIDTH)), image,
                              result.source_pixels)
        _write(row, f"drawn_{image}")
    return 0


# --------------------------------------------------------------- tables

OUT = ROOT.parent / "docs" / "renders" / "hairline-lines-logo-refusal"
MOVED = ("drone", "screenshot", "golden_tee")
# Render labels (`G._label` keeps 48 characters).
SHORT = {"supp": "supplement ON (#942)", "refuse": "supplement ON + logo refusal"}


def _load(prefix: str) -> list[dict]:
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(DEBUG.glob(f"{prefix}*.json"))
            if not f.name.endswith("_design.json")]


def logo_table(rows) -> str:
    out = ["| logo | class | supplement OFF: trims / stitches | supplement ON (#942): trims / "
           "stitches / lines kept | ON + refusal: trims / stitches / lines kept | refused "
           "edge / flat / pattern | bare new vs OFF mm2 (ON / ON+refusal) | ON+refusal == OFF? |",
           "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["logo"]):
        b, s, f = r["base"], r["supp"], r["refuse"]
        rs = (f.get("supplement") or {})
        why = " / ".join(str(sum((rs.get(k) or {}).values())) if rs.get(k) is not None else "-"
                         for k in ("refused_logo_edge", "refused_logo_flat", "refused_logo_pattern"))
        out.append(
            f"| {r['logo']} | {r['design_class']} | {b['trims']} / {b['stitches']:,} | "
            f"{s['trims']} / {s['stitches']:,} / {s['lines_kept']} | "
            f"{f['trims']} / {f['stitches']:,} / {f['lines_kept']} | {why} | "
            f"{s.get('bare_new_vs_base_mm2', 0.0)} / {f.get('bare_new_vs_base_mm2', 0.0)} | "
            f"{'yes' if f['md5'] == b['md5'] else 'NO'} (`{f['md5'][:8]}`) |")
    return "\n".join(out)


def owl_table(rows) -> str:
    out = ["| arm | strands (region / supplement) | bristle-box strands | refused edge / flat / "
           "pattern | stitches | trims | colour chg | thread m | bare new vs region mm2 | md5 |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    order = {a: i for i, a in enumerate(ARMS)}
    for r in sorted(rows, key=lambda r: order[r["arm"]]):
        sup = r.get("supplement") or {}
        why = " / ".join(str(sum(sup[k].values())) if sup.get(k) is not None else "-"
                         for k in ("refused_logo_edge", "refused_logo_flat", "refused_logo_pattern"))
        z = (r.get("zones") or {}).get("bristles", {}).get("n", "-") if r.get("zones") else "-"
        out.append(
            f"| {LABELS[r['arm']]} | {(r.get('region') or {}).get('strands', '-')} / "
            f"{sup.get('strands', '-')} | {z} | {why} | {r['stitches']:,} | {r['trims']} | "
            f"{r['color_changes']} | {r['thread_m']} | {r['bare_new_vs_region_mm2']} | "
            f"`{r['md5'][:8]}` |")
    return "\n".join(out)


def drawn_table(rows) -> str:
    out = ["| fixture | region md5 | supplement ON md5 | ON + refusal md5 | identical |",
           "|---|---|---|---|---|"]
    for r in rows:
        m = [r[a]["md5"] for a in ("region", "supp", "refuse")]
        out.append(f"| {r['image']} | `{m[0][:8]}` | `{m[1][:8]}` | `{m[2][:8]}` | "
                   f"{'yes' if len(set(m)) == 1 else 'NO'} |")
    return "\n".join(out)


def cmd_table(out: Path) -> int:
    out.mkdir(parents=True, exist_ok=True)
    logos, owl, drawn = _load("logo_"), _load("owl_kent_"), _load("drawn_")
    text = ("NINE LOGOS (Studio route, max_colors 6; OFF = hairline + from_lines + strand "
            "test, the supplement off)\n\n" + logo_table(logos)
            + "\n\nOWL_KENT 127 mm (Studio route, 40 wt, grid 8)\n\n" + owl_table(owl)
            + "\n\nDRAWN HAIR 80 mm\n\n" + drawn_table(drawn) + "\n")
    (out / "table.md").write_text(text, encoding="utf-8")
    (out / "table.json").write_text(json.dumps({"logos": logos, "owl": owl, "drawn": drawn},
                                               indent=1) + "\n", encoding="utf-8")
    print(text)
    return 0


# -------------------------------------------------------------- renders

def _render(design: dict, px_per_mm: float):
    from digitizer_core import machine, stitchviz
    return stitchviz.render_design(design, px_per_mm=px_per_mm,
                                   thread_mm=machine.thread_profile(40).width_mm)


def cmd_render(out: Path, only) -> int:
    """BEFORE (supplement ON, #942) | AFTER (ON + the refusal) for each moved
    logo, re-planned here, and owl_kent's bristle box at 16 px/mm from
    `owl`'s saved designs."""
    from digitizer_core.adapter import plan_to_design
    out.mkdir(parents=True, exist_ok=True)
    for name, path, width, kw in _cases(set(only or MOVED)):
        if name == "owl_kent":
            continue
        result = run_stages(path, cfg_arm("base", width, **kw))
        tiles = []
        for a, tag in (("supp", "BEFORE"), ("refuse", "AFTER")):
            plan = plan_stitches(result, cfg_arm(a, width, **kw))
            tiles.append(G._label(_render(plan_to_design(plan, name=f"{name} {a}"), 8.0),
                                  f"{tag}: {SHORT[a]}"))
        hr.write_jpeg(out / f"{name}_before_after_8pxmm.jpg", G._strip(tiles))
        print("wrote", name, flush=True)
    have = [a for a in ("supp", "refuse") if (DEBUG / f"owl_kent_{a}_design.json").exists()]
    if have:
        sp = _sp_cached("owl_kent")
        h, w = sp.rgb.shape[:2]
        x0, y0, x1, y1 = hr.ZONES["owl_kent"]["bristles"]
        to_mm = lambda px, py: ((px - sp.origin_px[0]) / sp.px_per_mm,  # noqa: E731
                                (py - sp.origin_px[1]) / sp.px_per_mm)
        a, b = to_mm(x0 * w, y0 * h), to_mm(x1 * w, y1 * h)
        tiles = [G._label(hr.beak_crop("owl_kent", json.loads(
            (DEBUG / f"owl_kent_{arm}_design.json").read_text(encoding="utf-8")),
            (a[0], a[1], b[0], b[1]), 16.0, 40),
            f"{'BEFORE' if arm == 'supp' else 'AFTER'}: {SHORT[arm]}") for arm in have]
        hr.write_jpeg(out / "owl_kent_bristles_before_after_16pxmm.jpg", G._strip(tiles))
        print("wrote owl_kent", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--only", default="")
    g = sub.add_parser("logos")
    g.add_argument("--only", default="")
    o = sub.add_parser("owl")
    o.add_argument("--arms", default="region,supp,refuse")
    sub.add_parser("drawn")
    c = sub.add_parser("census")
    c.add_argument("--only", default="")
    fe = sub.add_parser("features")
    fe.add_argument("--only", default="")
    t = sub.add_parser("table")
    t.add_argument("--out", type=Path, default=OUT)
    r = sub.add_parser("render")
    r.add_argument("--out", type=Path, default=OUT)
    r.add_argument("--only", default="")
    args = ap.parse_args(argv)
    if args.cmd == "table":
        return cmd_table(args.out)
    if args.cmd == "render":
        return cmd_render(args.out, [s for s in args.only.split(",") if s])
    if args.cmd == "features":
        return cmd_features([s for s in args.only.split(",") if s])
    if args.cmd == "census":
        return cmd_census({s for s in args.only.split(",") if s})
    if args.cmd == "probe":
        return cmd_probe({s for s in args.only.split(",") if s})
    if args.cmd == "logos":
        return cmd_logos({s for s in args.only.split(",") if s})
    if args.cmd == "owl":
        return cmd_owl([s for s in args.arms.split(",") if s])
    if args.cmd == "drawn":
        return cmd_drawn()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
