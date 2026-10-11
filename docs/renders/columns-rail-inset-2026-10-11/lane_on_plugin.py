"""pytest plugin: run a test module with the Column lane ON (both flags) by
wrapping the module's own `base_cfg`. Used to read
`tests/test_lettering_coverage_regression.py` with the lane ON:

    cd digitizer
    PYTHONPATH=../docs/renders/columns-rail-inset-2026-10-11 \
        python -m pytest -q -p lane_on_plugin tests/test_lettering_coverage_regression.py
"""
import pytest

LANE = {"lettering_columns": True, "lettering_words": True}


@pytest.fixture(autouse=True)
def _lane_on(monkeypatch, request):
    mod = request.module
    orig = getattr(mod, "base_cfg", None)
    if orig is not None:
        def lane_cfg(w, g, **kw):
            cfg = orig(w, g, **{**LANE, **kw})
            print(f"[lane_on_plugin] {request.node.name}: lettering_columns="
                  f"{cfg.lettering_columns} lettering_words={cfg.lettering_words}")
            return cfg
        monkeypatch.setattr(mod, "base_cfg", lane_cfg)
    yield
