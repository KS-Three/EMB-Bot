"""From a photo of the sewn calibration card to a fabric profile.

The service's half of the loop (`/calibration/card`, `/calibration/read`),
kept out of `app.py` so the arithmetic is testable without HTTP and the
route is a thin adapter.

## The card, built once

`card_bundle()` builds card v2 through the real emitters (block 5 runs the
pipeline four times, ~15 s) and reads the engine's own render of it once
(`reader.read_reference`), under a lock, and keeps both for the life of the
process. Every download and every photo read reuses them: the card a
customer sews and the reference their photo is compared against are the
same object.

## The profile, drafted

`draft_profile` turns the reader's per-feature deltas into the three
numbers `fabrics.apply_profile` takes. Two conventions carry the whole
mapping, both from `machine.py`:

  * `Fabric.pull_comp_mm` is PER RAIL — each rail moves that far from the
    other, so a column is `2 * pull_comp_mm` wider than solved. The card's
    satin bars are emitted with NO compensation (they bypass stage 5), so
    the photo's pull-in is the cloth's raw total narrowing. The ideal
    compensation is half of it, and the delta is that minus the preset's.
  * Row spacing is `FILL_ROW_MM * density_adjust`, and the shipped fill row
    is 0.15 mm — which is square D on card v2. Cloth showing through D is
    cloth that will show through the customer's designs, so the density
    scale is `1 - deficit` on that square, and only ever tightens: a photo
    can show a gap; it cannot show that a gap is safe to open.

The trim distance has no arm on the card (block 7, FLOAT CLEARANCE, is
drafted and unbuilt), so its delta is always 0 and the reading says so.

Nothing here writes a constant. The result is a DRAFT the customer accepts
in the Studio, and it lands on `project.fabricProfile`, which adjusts a
preset inside the table's own span (gate 1).
"""
from __future__ import annotations

import base64
import threading
from dataclasses import dataclass

import cv2
import numpy as np

from ..adapter import plan_to_design
from ..fabrics import Fabric, apply_profile, normalize_profile
from . import card_v2, reader

# Card v2's density square at the shipped fill row (`machine.FILL_ROW_MM`
# 0.15); v1 has no such arm and its nearest is the 0.20 one.
DENSITY_SQUARES = ("fill-D-0.15", "fill-B-0.20")
# Below this the deficit is the reader's own noise (±0.01 on the simulation).
COVERAGE_DEFICIT_MIN = 0.02
# The overlay the Studio shows; the rectified raster is 20 px/mm and does not
# need to travel at that size.
OVERLAY_MAX_W = 900


class CalibrationReadError(ValueError):
    """The photo could not be registered or read — a 422, never a 500."""


@dataclass
class CardBundle:
    design: dict
    report: dict
    reference: dict          # `reader.read_reference(design)`, sans the raster

    @property
    def card_mm(self) -> list[float]:
        return list(self.reference["card_mm"])


_lock = threading.Lock()
_bundle: CardBundle | None = None


def card_bundle() -> CardBundle:
    """Card v2 and its reference reading, built once per process."""
    global _bundle
    with _lock:
        if _bundle is None:
            plan, report = card_v2.build_card_v2()
            design = plan_to_design(plan, name=card_v2.LABEL)
            ref = reader.read_reference(design)
            ref.pop("_rectified", None)
            _bundle = CardBundle(design=design, report=report, reference=ref)
        return _bundle


def reset_bundle() -> None:
    """Tests only."""
    global _bundle
    with _lock:
        _bundle = None


def card_info(built: CardBundle | None = None) -> dict:
    """What a client can show before the card is built: the hoop and the
    marks are constants; the size and count arrive once it is."""
    info = {
        "name": card_v2.NAME,
        "hoop": {"target_mm": list(card_v2.HOOP_MM), "margin_mm": card_v2.HOOP_MARGIN_MM,
                 "preset": "5x7"},
        "fiducial_mm": card_v2.FIDUCIAL_MM,
        "dense_row_mm": card_v2.DENSE_ROW_MM,
        "blocks": [name for name, _b, _rgb, _t in card_v2.BLOCKS],
        "built": built is not None,
        "card_mm": None,
        "stitch_count": None,
        "color_blocks": None,
    }
    if built is not None:
        info["card_mm"] = built.card_mm
        info["stitch_count"] = sum(1 for s in built.design["stitches"] if s.get("type") == "stitch")
        info["color_blocks"] = len(built.design.get("colors") or [])
    return info


def _row(cmp: dict, name: str) -> dict | None:
    return next((r for r in cmp["features"] if r["name"] == name), None)


def draft_profile(cmp: dict, fabric: Fabric) -> dict:
    """The reader's `compare()` result → the three-number profile, plus what
    was measured, what the preset is, what would be in force, and why."""
    d = cmp.get("draft_profile_delta") or {}
    notes: list[str] = []
    profile: dict[str, float] = {}

    pull_in = d.get("satin_pull_in_mm")
    if pull_in is None:
        notes.append("No satin column could be read, so pull compensation stays at the preset.")
    else:
        ideal = max(0.0, float(pull_in)) / 2.0
        delta = round(ideal - fabric.pull_comp_mm, 4)
        profile["pull_comp_delta_mm"] = delta
        notes.append(f"Satin columns pulled in {pull_in:.2f} mm across on this cloth, so each rail "
                     f"wants {ideal:.2f} mm of compensation; the {fabric.label} preset gives "
                     f"{fabric.pull_comp_mm:.2f}.")

    square = next((n for n in DENSITY_SQUARES if _row(cmp, n) and _row(cmp, n).get("d_coverage") is not None), None)
    deficit = None
    if square is None:
        notes.append("No fill square could be read, so density stays at the preset.")
    else:
        deficit = round(-float(_row(cmp, square)["d_coverage"]), 4)
        if deficit >= COVERAGE_DEFICIT_MIN:
            profile["density_scale"] = round(1.0 - deficit, 4)
            notes.append(f"Cloth shows through {deficit * 100:.0f}% of the {square.split('-')[-1]} mm "
                         f"fill, so rows tighten by that much.")
        else:
            notes.append(f"The {square.split('-')[-1]} mm fill covered the cloth; rows stay as the preset.")

    profile["trim_at_delta_mm"] = 0.0
    notes.append("The card has no float-length arm, so the trim distance stays at the preset.")

    canonical = normalize_profile(profile)
    in_force = apply_profile(fabric, canonical)
    measured = {
        "satin_pull_in_mm": pull_in,
        "satin_push_out_mm": d.get("satin_push_out_mm"),
        "fill_pull_in_mm": d.get("fill_pull_in_mm"),
        "coverage_deficit": deficit,
        "coverage_square": square,
        "seam_gap_delta_mm": cmp.get("seam_gap_delta_mm") or {},
    }
    return {
        "profile": canonical,
        "measured": measured,
        "preset": {"id": fabric.id, "label": fabric.label, "pull_comp_mm": fabric.pull_comp_mm,
                   "density_adjust": fabric.density_adjust, "trim_at_mm": fabric.trim_at_mm},
        "in_force": {"pull_comp_mm": in_force.pull_comp_mm, "density_adjust": in_force.density_adjust,
                     "trim_at_mm": in_force.trim_at_mm},
        "notes": notes,
    }


def _overlay_jpeg_b64(rect: np.ndarray, design: dict, rd: dict) -> str:
    ov = reader.overlay(rect, design, rd)
    if ov.shape[1] > OVERLAY_MAX_W:
        f = OVERLAY_MAX_W / ov.shape[1]
        ov = cv2.resize(ov, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", ov, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""


def read_calibration_photo(photo_bgr: np.ndarray, fabric: Fabric,
                           bundle: CardBundle | None = None) -> dict:
    """A photo of the sewn card v2 → readings, a draft profile, and the
    overlay the Studio shows. Registers off the fiducials first; falls back
    to the automatic path (which cannot see a global shrink) and says so."""
    bundle = bundle or card_bundle()
    img = reader.prepare_photo(photo_bgr)
    mode = "fiducials"
    try:
        rd = reader.read_card(img, bundle.design, mode="fiducials")
    except ValueError as first:
        try:
            rd = reader.read_card(img, bundle.design, mode="auto")
            mode = "auto"
        except ValueError as second:
            raise CalibrationReadError(
                f"Could not find the card in the photo ({second}). Photograph it flat, "
                f"square-on, in even light, with the whole card and its four corner marks in frame."
            ) from first
    cmp = reader.compare(rd, bundle.reference)
    unread = [r["name"] for r in rd["features"] if r.get("note") == "no thread found"]
    bars_read = sum(1 for r in cmp["features"] if r["role"] == "bar" and r.get("d_height_mm") is not None)
    confidence = {
        "mode": mode,
        "ecc": rd.get("ecc"),
        "features_unread": unread,
        "bars_read": bars_read,
        "global_shrink_visible": mode == "fiducials",
    }
    out = draft_profile(cmp, fabric)
    if mode == "auto":
        out["notes"].insert(0, "The corner marks were not found, so the card was registered on its "
                               "artwork; a shrink of the whole card cannot be seen this way.")
    out.update({
        "confidence": confidence,
        "features": cmp["features"],
        "seam_gap_delta_mm": cmp["seam_gap_delta_mm"],
        "card_mm": bundle.card_mm,
        "overlay_jpeg_base64": _overlay_jpeg_b64(rd["_rectified"], bundle.design, rd),
    })
    return out
