"""A calibration profile ADJUSTS the fabric preset, clamped, and is OFF by
default — Kent's 2026-09-30 ruling (DOCTRINE), phase 3 of
`docs/sewout-calibration-brief-2026-09-30.md`.

Three things are pinned, in the order they matter:

  1. **Byte-identical off.** A design that never asked for a profile, or
     asked for one that changes nothing, sews the same DST bytes it sewed
     before the field existed. Pinned on bytes, not a count.
  2. **A profile reaches every fabric number through one door.** Pull
     compensation, row spacing and the trim distance all read the fabric
     via `pipeline.fabric_for`, so one profile moves all three — and moves
     the plan (a design under a profile sews the profile's pull comp).
  3. **The clamp is the table's span.** A delta past what any shipped
     preset sews lands ON the extreme preset's value, never beyond it, and
     the bounds are derived from the table rather than written down.

The service half: a malformed profile is a 400 at submit naming the field;
a no-op one canonicalises to absence, so it is one cache key with none.
"""
from __future__ import annotations

import pytest

import json
import time

from digitizer_core import digitize, export
from digitizer_core.fabrics import (FABRICS, apply_profile, get_fabric,
                                    normalize_profile, profile_clamps)
from digitizer_core.pipeline import fabric_for
from tests.conftest import TESTDATA, cfg

ART = TESTDATA / "logo_whitebg.png"


# --- the arithmetic ------------------------------------------------------------

def test_no_profile_is_the_same_object():
    f = get_fabric("pique_knit")
    assert apply_profile(f, None) is f
    assert apply_profile(f, {}) is f
    assert apply_profile(f, {"pull_comp_delta_mm": 0.0, "density_scale": 1.0}) is f
    assert f.profile is None


def test_a_profile_adjusts_and_records_itself():
    f = get_fabric("pique_knit")                      # 0.3 / 1.0 / 3.0
    g = apply_profile(f, {"pull_comp_delta_mm": 0.15, "density_scale": 0.9, "trim_at_delta_mm": 0.5})
    assert (g.pull_comp_mm, g.density_adjust, g.trim_at_mm) == (0.45, 0.9, 3.5)
    assert g.profile == {"pull_comp_delta_mm": 0.15, "density_scale": 0.9, "trim_at_delta_mm": 0.5}
    # Nothing categorical moves: underlay, backing and topper are the preset's.
    assert (g.id, g.fill_underlay, g.satin_underlay, g.assumed_backing, g.needs_topper) == \
        (f.id, f.fill_underlay, f.satin_underlay, f.assumed_backing, f.needs_topper)
    assert f.pull_comp_mm == 0.3, "the preset itself is untouched"


def test_the_clamp_is_the_shipped_tables_span():
    c = profile_clamps()
    assert c["pull_comp_mm"] == (min(f.pull_comp_mm for f in FABRICS), max(f.pull_comp_mm for f in FABRICS))
    assert c["pull_comp_mm"] == (0.2, 0.6)           # canvas to terry, as shipped 2026-09-30
    assert c["density_adjust"] == (0.85, 1.0)
    assert c["trim_at_mm"] == (3.0, 4.0)
    polo = get_fabric("pique_knit")
    hi = apply_profile(polo, {"pull_comp_delta_mm": 5.0, "density_scale": 3.0, "trim_at_delta_mm": 9.0})
    lo = apply_profile(polo, {"pull_comp_delta_mm": -5.0, "density_scale": 0.01, "trim_at_delta_mm": -9.0})
    assert (hi.pull_comp_mm, hi.density_adjust, hi.trim_at_mm) == (0.6, 1.0, 4.0)
    assert (lo.pull_comp_mm, lo.density_adjust, lo.trim_at_mm) == (0.2, 0.85, 3.0)


@pytest.mark.parametrize("bad, msg", [
    ([0.1], "must be an object"),
    ({"pull_comp_mm": 0.1}, "unknown field"),
    ({"pull_comp_delta_mm": "0.1"}, "finite number"),
    ({"density_scale": float("nan")}, "finite number"),
    ({"trim_at_delta_mm": True}, "finite number"),
])
def test_a_malformed_profile_is_refused_by_name(bad, msg):
    with pytest.raises(ValueError, match=msg):
        normalize_profile(bad)


def test_normalize_drops_noops_and_nulls():
    assert normalize_profile({"pull_comp_delta_mm": 0, "density_scale": None, "trim_at_delta_mm": 0.0}) is None
    assert normalize_profile({"pull_comp_delta_mm": 0.2, "density_scale": 1}) == {"pull_comp_delta_mm": 0.2}


# --- through the pipeline ------------------------------------------------------

def test_profile_off_is_byte_identical():
    """None and a no-op profile sew the bytes the engine sewed before."""
    a = digitize(ART, cfg(garment_id="left_chest"))[1]
    b = digitize(ART, cfg(garment_id="left_chest", fabric_profile=None))[1]
    c = digitize(ART, cfg(garment_id="left_chest",
                          fabric_profile={"pull_comp_delta_mm": 0.0, "density_scale": 1.0}))[1]
    assert export.export_dst(a) == export.export_dst(b) == export.export_dst(c)


def test_one_door_for_every_fabric_number():
    base = fabric_for(cfg(garment_id="left_chest"))
    adj = fabric_for(cfg(garment_id="left_chest",
                         fabric_profile={"pull_comp_delta_mm": 0.2, "density_scale": 0.9, "trim_at_delta_mm": 1.0}))
    assert (base.pull_comp_mm, base.density_adjust, base.trim_at_mm) == (0.3, 1.0, 3.0)
    assert (adj.pull_comp_mm, adj.density_adjust, adj.trim_at_mm) == (0.5, 0.9, 4.0)
    # An explicit fabric_id still wins over the garment, and is adjusted too.
    explicit = fabric_for(cfg(garment_id="left_chest", fabric_id="canvas_tote",
                              fabric_profile={"pull_comp_delta_mm": 0.1}))
    assert explicit.id == "canvas_tote" and explicit.pull_comp_mm == 0.3


def test_a_design_under_a_profile_sews_the_profiles_numbers():
    """Pull comp widens satin columns and row scale tightens fills, so the
    plan moves; and the pull comp the plan was built with is the adjusted
    one. Pinned on bytes plus the count direction density implies."""
    plain = digitize(ART, cfg(garment_id="left_chest"))[1]
    under = digitize(ART, cfg(garment_id="left_chest",
                              fabric_profile={"pull_comp_delta_mm": 0.2, "density_scale": 0.85}))[1]
    assert export.export_dst(plain) != export.export_dst(under)
    # 0.85 on the row spacing is ~18% more rows: the stitch count rises.
    assert under.stats.stitch_count > plain.stats.stitch_count


# --- the service -------------------------------------------------------------------

def _post(client, config):
    with open(ART, "rb") as fh:
        return client.post("/digitize", files={"image": ("logo.png", fh, "image/png")},
                           data={"config": json.dumps(config)})


def _wait(client, job_id: str) -> None:
    for _ in range(600):
        if client.get(f"/jobs/{job_id}").json()["state"] in ("done", "error"):
            return
        time.sleep(0.1)


def test_service_refuses_a_malformed_profile_at_submit(client):
    r = _post(client, {"target_width_mm": 60, "fabric_profile": {"pull_comp_mm": 0.3}})
    assert r.status_code == 400, r.text
    assert "fabric_profile" in r.json()["detail"] and "unknown field" in r.json()["detail"]
    r = _post(client, {"target_width_mm": 60, "fabric_profile": [1, 2]})
    assert r.status_code == 400, r.text


def test_service_accepts_a_profile_and_canonicalises_a_noop_away(client):
    base = {"target_width_mm": 60, "garment_id": "left_chest"}
    ok = _post(client, {**base, "fabric_profile": {"pull_comp_delta_mm": 0.15, "density_scale": 1.0}})
    assert ok.status_code == 202, ok.text
    none = _post(client, base)
    assert none.status_code == 202, none.text
    _wait(client, none.json()["job_id"])
    # One cache key: the no-op profile lands on the SAME job as no profile
    # (the cache is checked against finished jobs, as
    # `test_identical_request_is_served_from_cache` does).
    noop = _post(client, {**base, "fabric_profile": {"pull_comp_delta_mm": 0.0, "density_scale": None}})
    assert noop.status_code == 202, noop.text
    assert noop.json()["job_id"] == none.json()["job_id"], (noop.json(), none.json())
    assert noop.json()["cached"] is True
    assert ok.json()["job_id"] != none.json()["job_id"]
