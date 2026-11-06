"""`POST /lettering` + `GET /fonts/outline*`: outline fonts through the service.

Same `client` fixture and `wait_for_job` poll as `tests/test_service.py`.
"""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")

from .conftest import wait_for_job  # noqa: E402

BODY = {"font": "bebas-neue", "text": "FAB", "cap_mm": 8,
        "config": {"garment_id": "left_chest", "preflight": False}}


def test_font_list_carries_coverage_and_file_routes(client):
    r = client.get("/fonts/outline")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1 and body["fonts"]
    row = next(f for f in body["fonts"] if f["key"] == "montserrat-bold")
    assert row["kind"] == "outline" and row["licenseId"] == "OFL-1.1"
    assert row["weight"] == 700 and row["variable"] is True
    assert row["coverage"] and row["file"] == "/fonts/outline/montserrat-bold/file"
    assert row["license"] == "/fonts/outline/montserrat-bold/license"


def test_font_file_and_license_are_served(client):
    r = client.get("/fonts/outline/bebas-neue/file")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("font/ttf")
    assert r.content[:4] in (b"\x00\x01\x00\x00", b"true", b"OTTO")
    lic = client.get("/fonts/outline/bebas-neue/license")
    assert lic.status_code == 200 and "SIL Open Font License" in lic.text
    assert client.get("/fonts/outline/nope/file").status_code == 404
    assert client.get("/fonts/outline/nope/license").status_code == 404


def test_lettering_job_delivers_the_digitize_contract(client):
    r = client.post("/lettering", json=BODY)
    assert r.status_code == 202, r.text
    job = wait_for_job(client, r.json()["job_id"])
    assert job["state"] == "done", job
    design = job["design"]
    assert design["stitchCount"] > 200
    assert {run["kind"] for run in design["runs"]} >= {"satin"}
    assert job["review"]["shapes"] and job["stats"]["stitch_count"] == design["stitchCount"]
    assert job["preflight"] is None
    assert job["lettering"]["letters"] == 3 and job["lettering"]["font"] == "bebas-neue"
    assert job["lettering"]["cap_mm"] == pytest.approx(8.0, abs=1e-3)
    # every review shape sewed as a satin letter
    assert all(s["tier"] == "satin" for s in job["review"]["shapes"]), job["review"]["shapes"]


def test_identical_lettering_request_is_served_from_cache(client):
    first = client.post("/lettering", json=BODY).json()
    second = client.post("/lettering", json=BODY).json()
    assert second["job_id"] == first["job_id"] and second["cached"] is True


def test_width_mm_sizes_the_block(client):
    r = client.post("/lettering", json={**BODY, "cap_mm": None, "width_mm": 40,
                                        "text": "FABRIC"})
    assert r.status_code == 202, r.text
    job = wait_for_job(client, r.json()["job_id"])
    assert job["state"] == "done"
    assert job["lettering"]["width_mm"] == pytest.approx(40.0, abs=1e-3)
    assert job["design"]["widthMM"] == pytest.approx(40.0, abs=1.5)  # pull comp + rails


@pytest.mark.parametrize("patch, needle", [
    ({"font": "no-such"}, "unknown outline font"),
    ({"text": "   "}, "text"),
    ({"cap_mm": None}, "exactly one"),
    ({"cap_mm": 8, "width_mm": 40}, "exactly one"),
    ({"text": "中"}, "no glyph"),
    ({"thread_index": 10 ** 6}, "thread_index"),
    ({"letter_spacing_mm": "wide"}, "letter_spacing_mm"),
    ({"bogus": 1}, "Unknown field"),
    ({"config": {"deleted_shape_ids": ["x"]}}, "deleted_shape_ids"),
])
def test_bad_requests_are_400_at_submit(client, patch, needle):
    r = client.post("/lettering", json={**BODY, **patch})
    assert r.status_code == 400, r.text
    assert needle.lower() in r.json()["detail"].lower()


def test_unsupported_characters_are_named_in_warnings(client):
    r = client.post("/lettering", json={**BODY, "text": "A中B"})
    assert r.status_code == 202, r.text
    job = wait_for_job(client, r.json()["job_id"])
    assert job["state"] == "done"
    assert job["lettering"]["unsupported"] == ["中"]
    assert any("no glyph for" in w for w in job["warnings"] if isinstance(w, str)), job["warnings"]


def test_lettering_design_exports_to_a_machine_file(client):
    job = wait_for_job(client, client.post("/lettering", json=BODY).json()["job_id"])
    r = client.post("/export", json={"design": job["design"], "format": "dst", "label": "FAB"})
    assert r.status_code == 200, r.text
    assert r.headers["X-Export-Verified"] == "true"
