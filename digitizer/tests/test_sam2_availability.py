# digitizer/tests/test_sam2_availability.py
"""The availability probe must catch a husk venv (Scripts/ stubs present,
no Lib/, no pyvenv.cfg) BEFORE the subprocess attempt — the 2026-08-18 probe
showed exactly that husk reading as 'available' then dying with exit 106.

Both venv layouts are covered on purpose. The first version of this file
built ONLY the Windows shape (`Scripts/python.exe` + `Lib/site-packages`)
in its own fixtures, so it passed identically on every platform while the
probe it covers rejected every real POSIX venv — `lib/pythonX.Y/site-
packages`, never `Lib/site-packages`. A test that constructs the layout it
is validating can only ever confirm the platform it was written on; the
POSIX case below is what makes this file able to fail."""
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


def test_complete_posix_venv_is_available(tmp_path: Path):
    """A real Linux/macOS venv: bin/python and a VERSIONED lowercase
    lib/pythonX.Y/site-packages. This repo's CI is ubuntu-latest and its
    goldens are re-captured on Linux, so this is the deploy shape that
    matters most, not an exotic one."""
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_bytes(b"stub")
    (venv / "pyvenv.cfg").write_text("home = x")
    (venv / "lib" / "python3.11" / "site-packages").mkdir(parents=True)
    assert sam2_segmentation_unavailable_reason(venv) is None


def test_posix_husk_venv_is_still_reported_unavailable(tmp_path: Path):
    """The POSIX half of the husk case: interpreter and pyvenv.cfg present,
    but nothing ever installed — no site-packages under lib/. Must be caught
    pre-spawn like its Windows twin, not waved through by a laxer glob."""
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_bytes(b"stub")
    (venv / "pyvenv.cfg").write_text("home = x")
    (venv / "lib").mkdir()
    reason = sam2_segmentation_unavailable_reason(venv)
    assert reason is not None and "site-packages" in reason
