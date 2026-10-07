"""Apply the letterform fit to one saved run: group the lettering the way
the engine does (`textcluster._lettering_groups`), read each word's line
and slant with the engine's own house instruments, build the word prior,
refit every text-tagged member, and hand back per-letter results.

`refit_logo(d)` takes the dict `run.py` pickled; `refit_regions(regions,
src_px_mm, grid_px_mm, k)` is the piece that would be wired into stage 4/5
if Kent picks that. Neither mutates the regions it is given: the refit
polygons come back in the result rows, and `apply(regions, rows)` writes
them in.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]        # digitizer/
sys.path.insert(0, str(ROOT))
SCRATCH = Path(os.environ.get("LETTERFORM_SCRATCH", ROOT.parent / "scratch_letterform_priors"))

from shapely.geometry import Polygon                                    # noqa: E402

from digitizer_core.regions import Region                               # noqa: E402
from digitizer_core.textcluster import (                               # noqa: E402
    _house_chains, _lettering_groups, _line_of_text_deg, _skeleton_stroke_stats,
    _stem_slant_deg)

import numpy as np                                                      # noqa: E402

from fit import (FitResult, K_DEFAULT, WordPrior, fit_letter,          # noqa: E402
                 letter_prior, word_prior)

# A word whose letters' stem leans (each read by `textcluster._stem_slant_deg`
# on that letter alone) spread more than this is arched: each letter then
# gets its own line of text. Set on Becker's two words -- MARINE's six leans
# agree within 2 deg, the arched BECKER's spread past 20 -- and nothing
# else; gaulke was held out.
ARCH_LEAN_SPREAD_DEG = 6.0


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

    @property
    def refit(self) -> Polygon:
        return self.fit.polygon


def source_px_mm(d: dict) -> float:
    """The source image's pixel at the design size: the design width over
    the pixels the art box spans (the art box is what stage 1 scales to the
    target width, so a transparent margin does not shrink the pixel)."""
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
                  k: float = K_DEFAULT, *, text_only: bool = True,
                  measure_widths: bool = True) -> list[LetterRow]:
    rows: list[LetterRow] = []
    for wi, members in enumerate(_lettering_groups(regions)):
        letters = [r for r in members if (r.meta.get("text_candidate") or not text_only)]
        if not letters:
            continue
        line = _line_of_text_deg(members)
        if line is None:
            line = 0.0
        slant = _stem_slant_deg(_house_chains(members), line)
        # the word's stroke width from the engine's own instrument
        halfs = [s.mean_mm for s in (_skeleton_stroke_stats(r) for r in members) if s is not None]
        width_hint = 2.0 * float(np.median(halfs)) if halfs else None
        # An arched word: each letter is upright on its own piece of the arc,
        # so its stems lean by a different amount. Read each letter's lean
        # with the engine's own stem instrument; when the leans spread more
        # than ARCH_LEAN_SPREAD_DEG the word is arched and each letter gets
        # its own line of text (line = its stems - 90), with no shared
        # baseline / cap line. A straight word's leans agree within noise.
        leans = [_stem_slant_deg(_house_chains([r]), line) for r in letters]
        known = [x for x in leans if x is not None]
        line_degs = None
        if len(known) >= 3 and (max(known) - min(known)) > ARCH_LEAN_SPREAD_DEG:
            fallback = float(np.median(known))
            line_degs = [(line + (x if x is not None else fallback) - (slant or 0.0)) % 180.0
                         for x in leans]
        prior = word_prior([r.polygon for r in letters], line, slant, src_px_mm, grid_px_mm, k,
                           line_degs=line_degs, width_hint_mm=width_hint)
        for li, r in enumerate(letters):
            lp = letter_prior(prior, line_degs[li]) if line_degs is not None else prior
            res = fit_letter(r.polygon, lp)
            mb = cb = ma = ca = None
            if measure_widths:
                mb, cb = _width_stats(r.polygon)
                ma, ca = (_width_stats(res.polygon) if res.status == "refit" else (mb, cb))
            rows.append(LetterRow(wi, r.shape_id, r.meta.get("ocr_char"), r.polygon, res, lp,
                                  cb, ca, mb, ma))
    return rows


def apply(regions: list[Region], rows: list[LetterRow]) -> int:
    """Write the accepted refits into `regions` (same shape_id, same meta,
    plus `letterform_refit` naming what happened). Returns how many moved."""
    by_id = {row.shape_id: row for row in rows}
    n = 0
    for r in regions:
        row = by_id.get(r.shape_id)
        if row is None:
            continue
        r.meta["letterform_refit"] = row.fit.status + (":" + row.fit.reason if row.fit.reason else "")
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
    import numpy as np
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
