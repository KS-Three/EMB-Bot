"""Determinism sweep (2026-10-08), after the unseeded `medial_axis` in
`outline_cut._spine_ends` sewed a different design on every run.

The sweep digitized six real-art fixtures (becker_marine_logo, enthusiast_logo,
logo_hotel_fremont, logo_gaulke_roofing, art/logo_mfab_hat,
art/logo_toat_beanie) in two runs under PYTHONHASHSEED=0 and one under 12345:
all six design-byte digests were identical across the three. A grep of
`digitizer_core` found every RNG already seeded. Nothing needed fixing, so what
is left is the two pins below -- the source rule (a tie only shows on some
shapes, so a run-twice test can pass by luck) and the hash-seed run.
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "digitizer_core"

# Constructors that draw from OS entropy when called without a seed.
_SEEDED_CTORS = {"default_rng", "RandomState", "Generator"}
# Legacy global-state draws (np.random.rand, ...) and the `random` module.
_GLOBAL_DRAWS = {"rand", "randn", "randint", "random", "random_sample", "choice",
                 "shuffle", "permutation", "normal", "uniform", "sample", "seed"}


def _name(func):
    return getattr(func, "id", getattr(func, "attr", None))


def test_no_unseeded_randomness_in_the_engine():
    bad = []
    for f in sorted(CORE.rglob("*.py")):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            where = f"{f.relative_to(CORE)}:{getattr(node, 'lineno', 0)}"
            if isinstance(node, ast.Import) and any(a.name == "random" for a in node.names):
                bad.append(f"{where} import random")
            elif isinstance(node, ast.ImportFrom) and node.module == "random":
                bad.append(f"{where} from random import")
            elif isinstance(node, ast.Call):
                n = _name(node.func)
                if n in _SEEDED_CTORS:
                    seed = node.args[0] if node.args else next(
                        (k.value for k in node.keywords if k.arg in ("seed", "x")), None)
                    if seed is None or (isinstance(seed, ast.Constant) and seed.value is None):
                        bad.append(f"{where} {n}() unseeded")
                elif (isinstance(node.func, ast.Attribute) and n in _GLOBAL_DRAWS
                      and ast.unparse(node.func.value) in ("np.random", "numpy.random", "random")):
                    bad.append(f"{where} {ast.unparse(node.func)} global draw")
                elif n == "hash" and isinstance(node.func, ast.Name):
                    bad.append(f"{where} hash() is salted per process for str/bytes")
    assert bad == []


_SNIPPET = """
import hashlib, sys
sys.path.insert(0, {root!r})
from digitizer_core import PipelineConfig, digitize
from tests.test_generation_cache import _design_bytes
cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest")
r, p = digitize({img!r}, cfg)
print(hashlib.sha256(_design_bytes(r, p)).hexdigest())
"""


def test_design_bytes_do_not_depend_on_the_string_hash_seed():
    """Same artwork, two processes, two PYTHONHASHSEEDs: identical design bytes.
    A set/dict of strings iterated into geometry would differ here."""
    code = _SNIPPET.format(root=str(ROOT), img=str(ROOT / "testdata" / "becker_marine_logo.png"))
    procs = [subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True,
                              env={**os.environ, "PYTHONHASHSEED": seed})
             for seed in ("0", "12345")]
    digests = []
    for p in procs:
        out, err = p.communicate(timeout=600)
        assert p.returncode == 0, err[-2000:]
        digests.append(out.strip().splitlines()[-1])
    assert digests[0] == digests[1] and len(digests[0]) == 64, digests
