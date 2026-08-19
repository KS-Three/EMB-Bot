# digitizer/tests/test_sam2_availability.py
"""The availability probe must catch a husk venv (Scripts/ stubs present,
no Lib/, no pyvenv.cfg) BEFORE the subprocess attempt — the 2026-08-18 probe
showed exactly that husk reading as 'available' then dying with exit 106."""
from pathlib import Path
from digitizer_core.stage2_sam2_segment import sam2_segmentation_unavailable_reason

def test_husk_venv_is_reported_unavailable(tmp_path: Path):
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "python.exe").write_bytes(b"stub")
    reason = sam2_segmentation_unavailable_reason(venv)
    assert reason is not None and "pyvenv.cfg" in reason

def test_complete_venv_is_available(tmp_path: Path):
    venv = tmp_path / "venv"
    (venv / "Scripts").mkdir(parents=True)
    (venv / "Scripts" / "python.exe").write_bytes(b"stub")
    (venv / "pyvenv.cfg").write_text("home = x")
    (venv / "Lib" / "site-packages").mkdir(parents=True)
    assert sam2_segmentation_unavailable_reason(venv) is None
