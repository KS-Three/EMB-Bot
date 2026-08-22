"""Measure the stage 0-4 cache's effect over the real service wire.

For each fixture: submit plain (miss), then submit with a one-shape edit
(hit), then clear the generation cache and submit a second edit (miss with
edit) — the last one is the honest 'what an edit used to cost' baseline,
since it runs the full pipeline WITH edit config exactly as before the
cache existed. Times are wall-clock around submit->done over TestClient.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from digitizer_service.app import app, generations  # noqa: E402

FIXTURES = [
    Path("testdata/photo/enthusiast_logo.png"),  # the logo-class exemplar (81% stage 0-4)
    Path("testdata/photo/owl_kent.jpg"),         # the photo exemplar (53% stage 0-4)
]


def run(client, art: Path, cfg: dict) -> tuple[float, dict]:
    t0 = time.perf_counter()
    with art.open("rb") as f:
        r = client.post("/digitize", files={"image": (art.name, f, "image/png")},
                        data={"config": json.dumps(cfg)})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    while True:
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            break
        time.sleep(0.05)
    dt = time.perf_counter() - t0
    assert state["state"] == "done", state.get("detail") or state.get("error")
    return dt, state


def main() -> None:
    with TestClient(app) as client:
        for art in FIXTURES:
            generations.clear()
            base_cfg = {"preflight": False}
            t_plain, first = run(client, art, base_cfg)
            assert first["generation_cache"] == "miss"
            sid = first["review"]["shapes"][0]["shape_id"]
            sid2 = first["review"]["shapes"][1]["shape_id"] if len(first["review"]["shapes"]) > 1 else sid

            edit_cfg = {**base_cfg, "shape_overrides": {sid: {"fill_angle_deg": 63.0}}}
            t_hit, hit = run(client, art, edit_cfg)
            assert hit["generation_cache"] == "hit", hit["generation_cache"]

            generations.clear()
            edit2_cfg = {**base_cfg, "shape_overrides": {sid2: {"fill_angle_deg": 27.0}}}
            t_cold_edit, cold = run(client, art, edit2_cfg)
            assert cold["generation_cache"] == "miss"

            print(f"{art.name}:")
            print(f"  first run (miss, no edit) : {t_plain:6.2f}s")
            print(f"  edited re-run (HIT)       : {t_hit:6.2f}s")
            print(f"  edited cold run (pre-cache behavior): {t_cold_edit:6.2f}s")
            print(f"  edit-loop speedup: {t_cold_edit / t_hit:.1f}x "
                  f"(hit is {t_hit / t_cold_edit:.0%} of the old cost)")


if __name__ == "__main__":
    main()
