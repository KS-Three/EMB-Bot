"""Fabric presets — a straight port of the browser engine's `src/fabrics.js`.

Same ids, same values, deliberately. Until sew-outs say otherwise the Python
engine and the browser engine must make the SAME physical choices, or a design
digitized here and one built there would need different tuning on the same
garment. When a sew-out moves a number, move it in both places.

Underlay ids: none | edge_run | center_run | edge_zigzag | edge_lattice |
double_lattice | zigzag | cross_tatami
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Fabric:
    id: str
    label: str
    pull_comp_mm: float
    fill_underlay: str
    satin_underlay: str      # read by stage7_sequence's satin underlay choice
                             # (a photo design overrides it); kept in step with
                             # the browser engine's table
    density_adjust: float
    trim_at_mm: float
    notes: str
    # --- what the DIGITIZER assumed the operator would hoop (Law 33) -------
    #
    # Neither field places a stitch. They exist because the worksheet has
    # always made a stabilizer claim to the customer and had no fabric to
    # base it on — it prescribed cutaway purely past a stitch COUNT, so a
    # 3,000-stitch left chest on jersey and the same design on canvas got the
    # same silence. The backing class is a property of the goods.
    #
    # `cutaway` for knits and pile (they stretch or crush and need permanent
    # support), `tearaway` for stable wovens, `cap_buckram` for a structured
    # cap front whose backing is built into the garment. Categorical trade
    # practice, not a tuned number, so gate 1 does not apply — no sew-out
    # settles whether a polo is a knit. Topper (a water-soluble film over the
    # nap) is a separate axis: only the two pile goods need it, which is the
    # same pair `density_adjust` already singles out below.
    assumed_backing: str = "cutaway"
    needs_topper: bool = False
    # The needle the operator loads (playbook Law 21 [P — Tajima, Madeira,
    # Groz-Beckert, A&E]): 75/11 is the standard for 40wt thread, ballpoint
    # on knits, sharp on wovens and caps. Advice like the two above — places
    # no stitch — and carried here only so the two tables stay field-for-field
    # identical; the function that states it to a person is `hoopingAdvice`
    # in `src/fabrics.js`. Kent's call 2026-10-01 (DOCTRINE).
    needle: str = "75/11 ballpoint"
    # The calibration profile this preset was adjusted by, or None — the
    # unadjusted table entry. Set only by `apply_profile`, read by whoever
    # states which fabric is in force (the Studio's Garment step, a job's
    # report). Not a physical field and not in `test_fabric_wire`'s FIELDS.
    profile: dict | None = None


FABRICS: list[Fabric] = [
    Fabric("structured_cap", "Structured cap", 0.4, "edge_zigzag", "center_run",
           1.0, 3.0, "Foam/structured cap front; firm, sew center-out.",
           "cap_buckram", False, "75/11 sharp"),
    # fill_underlay was "edge_lattice" until corpus law 26 (docs/corpus-laws-
    # round3-2026-08-01.md): the professional corpus never puts a full
    # crosshatch-lattice pass under a knit fill, only a single edge-walk
    # ("edge_run") — lattice is what heavier/looser goods (fleece, terry)
    # get. Landed 2026-08-05 alongside law 23 and a matching recalibration
    # of COVERAGE_WARN_UNITS (machine.py); see that constant's derivation
    # comment for why the two moved together.
    Fabric("pique_knit", "Pique knit (polo)", 0.3, "edge_run", "center_run",
           1.0, 3.0, "Polo pique; moderate stretch.", "cutaway", False,
           "75/11 ballpoint"),
    Fabric("jersey_tee", "Jersey / t-shirt", 0.35, "edge_run", "center_run",
           1.0, 3.0, "Stretchy knit; needs solid underlay.", "cutaway", False,
           "75/11 ballpoint"),
    # Pile fabrics run BELOW 1.0: the multiplier scales row SPACING, and pile
    # needs tighter rows, not looser — stitches sink into the nap (physics law
    # 30: density +10-20% on lofty goods, and more total thread on loft
    # puckers LESS because the loft absorbs it). These shipped at 1.05/1.1 for
    # months: the field reads like "more density" and is applied as "more
    # spacing", so towels and blankets — the two garments already mapped to
    # these presets — sewed 5-10% SPARSER than a polo. Caught independently by
    # the specialty-techniques research, the preflight coverage instrument,
    # and a direct code read, same day. Exact values are sew-out-gated; the
    # DIRECTION is not.
    Fabric("fleece_sweatshirt", "Fleece / sweatshirt", 0.5, "double_lattice", "zigzag",
           0.90, 3.5, "Thick nap; heavy underlay, topping helps.",
           "cutaway", True, "75/11 ballpoint"),
    Fabric("canvas_tote", "Canvas / twill", 0.2, "edge_run", "center_run",
           1.0, 3.0, "Stable woven; minimal compensation.", "tearaway", False,
           "75/11 sharp"),
    Fabric("terry_towel", "Terry towel", 0.6, "double_lattice", "zigzag",
           0.85, 4.0, "High loops; heavy underlay + topping essential.",
           # Woven, so Law 21 says sharp; Kent ruled ballpoint 2026-10-01 —
           # it parts the loops instead of cutting them.
           "cutaway", True, "75/11 ballpoint"),
    Fabric("woven_dress", "Woven dress shirt", 0.2, "edge_run", "center_run",
           1.0, 3.0, "Stable woven; minimal compensation.", "tearaway", False,
           "75/11 sharp"),
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


# The presets whose fill underlay `cfg.fill_underlay_cross` (built OFF
# 2026-10-21) swaps to `cross_tatami`: hat (structured_cap), left chest
# (pique_knit), beanie and sleeve (jersey_tee). The professional's own files
# sew one crossing tatami pass under every dense fill on every job in the
# zip — ~1.0 mm rows, ~4 mm stitches, ~90 degrees to the top fill
# (`docs/underlay-audit-2026-10-05.md`, `docs/settings-vs-pro-2026-10-21.md`
# rows 13-15). A fabric preset is a physical constant (ROADMAP gate 1), so
# this is a flag with a sew-out card arm, and the table above is untouched.
# Mirrored in `src/fabrics.js` (CROSS_UNDERLAY_FABRICS / fillUnderlayFor);
# `test_fabric_wire.py` holds the pair.
CROSS_UNDERLAY_FABRICS = ("structured_cap", "pique_knit", "jersey_tee")


# `cfg.pro_measured_values` (built OFF 2026-10-23): the three plain value gaps
# `docs/settings-vs-pro-2026-10-21.md` rows 1, 2, 11 and 19 measured against 28
# of the pro's DSTs, on the presets those jobs cover. Physical constants (gate
# 1): a flag for the sew-out, nothing here is a default. Mirrored in
# `src/fabrics.js` (PRO_MEASURED / proMeasuredFor); `test_fabric_wire.py`
# holds the pair.
PRO_VALUE_FABRICS = CROSS_UNDERLAY_FABRICS
PRO_FILL_STITCH_MM = 3.49          # row 11: 3.45-3.52 on rows >= 10 mm, 10 of 11 jobs
PRO_BEAN_STITCH_MM = 0.95          # row 19: 0.80-1.04 by job
# row 1 (hat & LC 0.37, 9 jobs) and row 2 (beanie 0.35, 6 files)
PRO_SATIN_SPACING_MM = {"structured_cap": 0.37, "pique_knit": 0.37, "jersey_tee": 0.35}


def pro_values_for(fabric: Fabric, on: bool) -> dict:
    """The pro-measured values one preset takes when the flag is on, else {}.
    Keys: fill_stitch_mm, bean_stitch_mm, satin_spacing_mm."""
    if not on or fabric.id not in PRO_VALUE_FABRICS:
        return {}
    return {"fill_stitch_mm": PRO_FILL_STITCH_MM, "bean_stitch_mm": PRO_BEAN_STITCH_MM,
            "satin_spacing_mm": PRO_SATIN_SPACING_MM[fabric.id]}


def fill_underlay_for(fabric: Fabric, cross: bool = False) -> str:
    """The fill underlay a preset sews: its own, or `cross_tatami` when the
    cross flag is on and the preset is one the pro's jobs cover."""
    if cross and fabric.id in CROSS_UNDERLAY_FABRICS:
        return "cross_tatami"
    return fabric.fill_underlay


def get_fabric(fabric_id: str | None) -> Fabric:
    """Look up a preset; an unknown id falls back to the default rather than
    raising, because a garment list that grows on the browser side must never
    take the engine down."""
    return _BY_ID.get(fabric_id or "", _BY_ID[DEFAULT_FABRIC_ID])


def fabric_for_garment(garment_id: str | None) -> Fabric:
    return get_fabric(GARMENT_FABRIC.get(garment_id or "", DEFAULT_FABRIC_ID))


# --- Calibration profiles (2026-09-30, Kent's call) ---------------------------
#
# A profile is what `tools/sewout_reader.py` drafts from a photo of the sewn
# calibration card: how far the customer's cloth pulled a satin column in,
# how much it showed through a fill, how far a float can run before it is
# cut. It ADJUSTS the shipped preset and never replaces it (DOCTRINE standing
# ruling, 2026-09-30): each field is a delta or a scale on the preset's own
# value, and the result is clamped.
#
# THE CLAMP IS THE SPAN OF THE SHIPPED TABLE, NOT A NEW NUMBER. Every value a
# profile can produce is one this table already sews on some fabric — a polo
# can be pulled as far as terry or as little as canvas, and no further. That
# is the whole of what makes a profile gate-1 clean: it re-slots a garment
# within physics the presets already commit to, and cannot invent a regime
# no sew-out has seen. Widening a bound is a sew-out question, not an edit.
#
# Wire form, both engines, verbatim (`src/fabrics.js` carries the same three
# keys and the same arithmetic; `test_fabric_wire.py` runs both and compares):
#   {"pull_comp_delta_mm": float, "density_scale": float, "trim_at_delta_mm": float}
# Any key may be absent. A no-op value (delta 0, scale 1) is dropped, so a
# profile that changes nothing IS no profile — byte-identical, and one cache
# key rather than two.

PROFILE_FIELDS = ("pull_comp_delta_mm", "density_scale", "trim_at_delta_mm")
_PROFILE_NOOP = {"pull_comp_delta_mm": 0.0, "density_scale": 1.0, "trim_at_delta_mm": 0.0}
PROFILE_ROUND = 4     # both engines round the adjusted values here


def profile_clamps() -> dict[str, tuple[float, float]]:
    """Bounds for each adjustable preset field: the min and max the shipped
    table itself carries. Derived, never written down, so a preset change
    moves them and nothing else has to."""
    return {
        "pull_comp_mm": (min(f.pull_comp_mm for f in FABRICS), max(f.pull_comp_mm for f in FABRICS)),
        "density_adjust": (min(f.density_adjust for f in FABRICS), max(f.density_adjust for f in FABRICS)),
        "trim_at_mm": (min(f.trim_at_mm for f in FABRICS), max(f.trim_at_mm for f in FABRICS)),
    }


def normalize_profile(profile) -> dict | None:
    """The canonical wire form of a profile, or None when it changes nothing.

    Raises ValueError on anything that is not a dict of the three known keys
    holding finite numbers — the service turns that into a 400 at submit, so
    a bad profile never reaches a job."""
    if profile is None:
        return None
    if not isinstance(profile, dict):
        raise ValueError("fabric_profile must be an object")
    unknown = sorted(set(profile) - set(PROFILE_FIELDS))
    if unknown:
        raise ValueError(f"fabric_profile: unknown field(s) {', '.join(unknown)}; "
                         f"valid: {', '.join(PROFILE_FIELDS)}")
    out: dict[str, float] = {}
    for key in PROFILE_FIELDS:
        if key not in profile or profile[key] is None:
            continue
        v = profile[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise ValueError(f"fabric_profile.{key} must be a finite number")
        v = float(v)
        if v == _PROFILE_NOOP[key]:
            continue
        out[key] = v
    return out or None


def _clamp(v: float, lo: float, hi: float) -> float:
    return round(min(hi, max(lo, v)), PROFILE_ROUND)


def apply_profile(fabric: Fabric, profile) -> Fabric:
    """`fabric` adjusted by `profile`, clamped to the table's span — or the
    very same object when the profile is absent or a no-op, so a design that
    never asked for one is byte-identical (`test_fabric_profile.py`)."""
    p = normalize_profile(profile)
    if not p:
        return fabric
    c = profile_clamps()
    return replace(
        fabric,
        pull_comp_mm=_clamp(fabric.pull_comp_mm + p.get("pull_comp_delta_mm", 0.0), *c["pull_comp_mm"]),
        density_adjust=_clamp(fabric.density_adjust * p.get("density_scale", 1.0), *c["density_adjust"]),
        trim_at_mm=_clamp(fabric.trim_at_mm + p.get("trim_at_delta_mm", 0.0), *c["trim_at_mm"]),
        profile=p,
    )
