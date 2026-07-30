"""Fabric presets — a straight port of the browser engine's `src/fabrics.js`.

Same ids, same values, deliberately. Until sew-outs say otherwise the Python
engine and the browser engine must make the SAME physical choices, or a design
digitized here and one built there would need different tuning on the same
garment. When a sew-out moves a number, move it in both places.

Underlay ids: none | edge_run | center_run | edge_zigzag | edge_lattice |
double_lattice | zigzag
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fabric:
    id: str
    label: str
    pull_comp_mm: float
    fill_underlay: str
    satin_underlay: str      # unused until build step 4; carried so the table
                             # stays in step with the browser engine's
    density_adjust: float
    trim_at_mm: float
    notes: str


FABRICS: list[Fabric] = [
    Fabric("structured_cap", "Structured cap", 0.4, "edge_zigzag", "center_run",
           1.0, 3.0, "Foam/structured cap front; firm, sew center-out."),
    Fabric("pique_knit", "Pique knit (polo)", 0.3, "edge_lattice", "center_run",
           1.0, 3.0, "Polo pique; moderate stretch."),
    Fabric("jersey_tee", "Jersey / t-shirt", 0.35, "edge_lattice", "center_run",
           1.0, 3.0, "Stretchy knit; needs solid underlay."),
    Fabric("fleece_sweatshirt", "Fleece / sweatshirt", 0.5, "double_lattice", "zigzag",
           1.05, 3.5, "Thick nap; heavy underlay, topping helps."),
    Fabric("canvas_tote", "Canvas / twill", 0.2, "edge_run", "center_run",
           1.0, 3.0, "Stable woven; minimal compensation."),
    Fabric("terry_towel", "Terry towel", 0.6, "double_lattice", "zigzag",
           1.1, 4.0, "High loops; heavy underlay + topping essential."),
    Fabric("woven_dress", "Woven dress shirt", 0.2, "edge_run", "center_run",
           1.0, 3.0, "Stable woven; minimal compensation."),
]

_BY_ID = {f.id: f for f in FABRICS}

# Default fabric per garment id, matching the browser engine's GARMENT_FABRIC.
GARMENT_FABRIC = {
    "hat_front": "structured_cap",
    "beanie": "jersey_tee",
    "left_chest": "pique_knit",
    "full_back": "fleece_sweatshirt",
    "sleeve": "jersey_tee",
    "tote": "canvas_tote",
    "jacket_back": "canvas_tote",
    "patch": "canvas_tote",
    "towel": "terry_towel",
    "blanket": "fleece_sweatshirt",
}

DEFAULT_FABRIC_ID = "pique_knit"


def get_fabric(fabric_id: str | None) -> Fabric:
    """Look up a preset; an unknown id falls back to the default rather than
    raising, because a garment list that grows on the browser side must never
    take the engine down."""
    return _BY_ID.get(fabric_id or "", _BY_ID[DEFAULT_FABRIC_ID])


def fabric_for_garment(garment_id: str | None) -> Fabric:
    return get_fabric(GARMENT_FABRIC.get(garment_id or "", DEFAULT_FABRIC_ID))
