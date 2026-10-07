"""Apply the letterform fit to one saved run (the dict `run.py` pickled) and
hand back per-letter rows the sheets and `batch.py` read.

The fit, the grouping and the word prior live in the engine
(`digitizer_core.letterform_priors`, behind `PipelineConfig.
letterform_priors_k`); this module only adds what the spike's instruments
want on top of an outcome -- the skeleton width statistics before and
after -- and the `apply` that writes accepted refits into a region list the
way the pipeline does.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]        # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRATCH = Path(os.environ.get("LETTERFORM_SCRATCH", ROOT.parent / "scratch_letterform_priors"))

import numpy as np                                                      # noqa: E402
from shapely.geometry import Polygon                                    # noqa: E402

from digitizer_core.letterform_priors import (                         # noqa: E402,F401
    ARCH_LEAN_SPREAD_DEG, K_DEFAULT, SLANT_DISAGREE_DEG, FitResult, LetterOutcome, WordPrior,
    plan_letterform_priors)
from digitizer_core.regions import Region                               # noqa: E402
from digitizer_core.textcluster import _skeleton_stroke_stats          # noqa: E402


@dataclass
class LetterRow:
    word: int
    shape_id: str
    char: str | None
    traced: Polygon
    fit: FitResult
    prior: WordPrior
    width_cv_before: float | None
    width_cv_after: float | None
    width_mean_before: float | None
    width_mean_after: float | None
    note: dict = field(default_factory=dict)     # the word's slant source, arch verdict, leans

    @property
    def refit(self) -> Polygon:
        return self.fit.polygon


def source_px_mm(d: dict) -> float:
    """The source image's pixel at the design size: the design width over
    the pixels the art box spans (what `Prep.input_px_per_mm` inverts)."""
    iw = d["image_size"][0]
    fx = d.get("art_box_frac")
    span = (fx[2] - fx[0]) if fx else 1.0
    return float(d["width"]) / (iw * max(span, 1e-9))


def regions_from(d: dict) -> list[Region]:
    return [Region(shape_id=r["shape_id"], polygon=r["polygon"],
                   thread_index=r["thread_index"] if r["thread_index"] is not None else 0,
                   thread_number="", area_mm2=r["polygon"].area, meta=dict(r["meta"]))
            for r in d["regions"]]


def _width_stats(poly: Polygon):
    st = _skeleton_stroke_stats(Region(shape_id="tmp", polygon=poly, thread_index=0,
                                       thread_number="", area_mm2=poly.area))
    return (st.mean_mm, st.cv) if st is not None else (None, None)


def refit_regions(regions: list[Region], src_px_mm: float, grid_px_mm: float,
                  k: float = K_DEFAULT, *, measure_widths: bool = True) -> list[LetterRow]:
    """The engine's plan for these regions, as rows with the width
    instrument's reading before and after. Nothing is written back."""
    rows: list[LetterRow] = []
    for o in plan_letterform_priors(regions, src_px_mm, grid_px_mm, k):
        mb = cb = ma = ca = None
        if measure_widths:
            mb, cb = _width_stats(o.traced)
            ma, ca = (_width_stats(o.refit) if o.fit.status == "refit" else (mb, cb))
        rows.append(LetterRow(o.word, o.shape_id, o.char, o.traced, o.fit, o.prior,
                              cb, ca, mb, ma, dict(o.note)))
    return rows


def apply(regions: list[Region], rows: list[LetterRow]) -> int:
    """Write the accepted refits into `regions` exactly as the pipeline's
    `apply_letterform_priors` does (same shape_id, same meta, plus
    `letterform_prior`). Returns how many moved."""
    by_id = {row.shape_id: row for row in rows}
    n = 0
    for r in regions:
        row = by_id.get(r.shape_id)
        if row is None:
            continue
        r.meta["letterform_prior"] = row.fit.status + (":" + row.fit.reason if row.fit.reason else "")
        if row.fit.status == "refit":
            r.polygon = row.fit.polygon
            r.area_mm2 = row.fit.polygon.area
            n += 1
    return n


def refit_logo(d: dict, k: float = K_DEFAULT, **kw) -> tuple[list[Region], list[LetterRow]]:
    regions = regions_from(d)
    rows = refit_regions(regions, source_px_mm(d), 1.0 / float(d["px_per_mm"]), k, **kw)
    return regions, rows


def summarize(rows: list[LetterRow]) -> dict:
    out = dict(letters=len(rows), refit=0, passed=0, refused=0, reasons={})
    for row in rows:
        f = row.fit
        if f.status == "refit":
            out["refit"] += 1
        elif f.status == "pass":
            out["passed"] += 1
        else:
            out["refused"] += 1
        if f.reason:
            out["reasons"][f.reason] = out["reasons"].get(f.reason, 0) + 1
    # structure, over the letters that were refit
    done = [r for r in rows if r.fit.status == "refit"]
    if done:
        out["prims_before"] = float(np.mean([r.fit.before_n_prims for r in done]))
        out["prims_after"] = float(np.mean([r.fit.n_prims for r in done]))
        out["moved_max"] = float(max(r.fit.moved_max_mm for r in done))
        out["moved_p95"] = float(np.median([r.fit.moved_p95_mm for r in done]))

        def spread(pairs):
            if not pairs:
                return None
            a = np.array([p[0] for p in pairs])
            w = np.array([p[1] for p in pairs])
            m = (a * w).sum() / w.sum()
            return float(np.sqrt(((a - m) ** 2 * w).sum() / w.sum()))
        by_word: dict[int, tuple[list, list]] = {}
        for r in done:
            b, a = by_word.setdefault(r.word, ([], []))
            b += r.fit.before_stem_angles
            a += r.fit.stem_angles
        sb = [spread(b) for b, _a in by_word.values()]
        sa = [spread(a) for _b, a in by_word.values()]
        out["stem_spread_before"] = float(np.mean([s for s in sb if s is not None])) if any(s is not None for s in sb) else None
        out["stem_spread_after"] = float(np.mean([s for s in sa if s is not None])) if any(s is not None for s in sa) else None
        cb = [r.width_cv_before for r in done if r.width_cv_before is not None]
        ca = [r.width_cv_after for r in done if r.width_cv_after is not None]
        out["width_cv_before"] = float(np.mean(cb)) if cb else None
        out["width_cv_after"] = float(np.mean(ca)) if ca else None
        # the word's width consistency: CV of the per-letter means
        wb: dict[int, list] = {}
        wa: dict[int, list] = {}
        for r in done:
            if r.width_mean_before is not None:
                wb.setdefault(r.word, []).append(r.width_mean_before)
            if r.width_mean_after is not None:
                wa.setdefault(r.word, []).append(r.width_mean_after)
        cvw = lambda m: float(np.std(m) / np.mean(m)) if len(m) > 1 and np.mean(m) > 0 else None  # noqa: E731
        vb = [cvw(m) for m in wb.values()]
        va = [cvw(m) for m in wa.values()]
        out["word_width_cv_before"] = float(np.mean([x for x in vb if x is not None])) if any(x is not None for x in vb) else None
        out["word_width_cv_after"] = float(np.mean([x for x in va if x is not None])) if any(x is not None for x in va) else None
    return out
