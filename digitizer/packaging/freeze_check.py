"""Does a frozen digitizer service produce the same bytes as the venv one?

SPIKE instrument (2026-11-10, docs/packaging-freeze-spike-2026-11-10.md).

    python packaging/freeze_check.py run http://127.0.0.1:8731 venv.json testdata/logo_whitebg.png ...
    python packaging/freeze_check.py run http://127.0.0.1:8732 frozen.json testdata/logo_whitebg.png ...
    python packaging/freeze_check.py compare venv.json frozen.json

`run` drives a service that is ALREADY listening: `/digitize` with the default
config, then `/export` as DST, PES and JEF, and writes a hash of everything
that came back. `compare` exits 1 unless the design, the review payload, the
warnings and the DST and PES bytes are identical.

JEF is reported and NOT compared: pystitch writes the wall clock into the
header (offset 8, `YYYYMMDDHHMMSS`), so two JEF writes one second apart differ
in the same process. Reading that as "the freeze changed the file" is the
mistake this line exists to prevent.

Needs `httpx` (the `dev` extra). Starts nothing and stops nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

#: Compared byte-for-byte. JEF is absent on purpose: see the module docstring.
COMPARED_FORMATS = ("dst", "pes")
REPORTED_FORMATS = (*COMPARED_FORMATS, "jef")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _wait_health(base: str, budget_s: float) -> tuple[dict, float]:
    import httpx

    t0 = time.perf_counter()
    while time.perf_counter() - t0 < budget_s:
        try:
            r = httpx.get(f"{base}/health", timeout=2)
            if r.status_code == 200:
                return r.json(), time.perf_counter() - t0
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise SystemExit(f"no /health from {base} in {budget_s:.0f} s")


def run(base: str, out_path: Path, fixtures: list[Path]) -> dict:
    import httpx

    health, waited = _wait_health(base, 120)
    out = {"base": base, "health_wait_s": round(waited, 2),
           "capabilities": health["capabilities"], "engine": health.get("engine"),
           "fixtures": {}}
    with httpx.Client(base_url=base, timeout=60) as c:
        for p in fixtures:
            t0 = time.perf_counter()
            r = c.post("/digitize", files={"image": (p.name, p.read_bytes(), "image/png")})
            r.raise_for_status()
            job = r.json()["job_id"]
            while True:
                s = c.get(f"/jobs/{job}").json()
                if s["state"] in ("done", "error"):
                    break
                if time.perf_counter() - t0 > 600:
                    raise SystemExit(f"{p.name}: job still running after 600 s")
                time.sleep(0.5)
            row = {"state": s["state"], "job_s": round(time.perf_counter() - t0, 1)}
            if s["state"] == "error":
                row["error"] = s.get("error")
            else:
                design = s["design"]
                row["stitches"] = len(design["stitches"])
                row["design_sha"] = _sha(json.dumps(design, sort_keys=True).encode())
                row["review_sha"] = _sha(json.dumps(s.get("review"), sort_keys=True).encode())
                row["warnings"] = sorted(
                    w if isinstance(w, str) else w.get("code", str(w)) for w in s.get("warnings") or [])
                for fmt in REPORTED_FORMATS:
                    e = c.post("/export", json={"design": design, "format": fmt, "label": "SPIKE"})
                    row[fmt] = {"status": e.status_code, "bytes": len(e.content), "sha": _sha(e.content),
                                "verified": e.headers.get("X-Export-Verified")}
            out["fixtures"][p.name] = row
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def compare(a: dict, b: dict) -> int:
    """Print both sides; return the number of compared fields that differ."""
    differ = 0
    print(f"capabilities  A {a['capabilities']}\n              B {b['capabilities']}")
    for name, ra in a["fixtures"].items():
        rb = b["fixtures"].get(name, {})
        print(f"\n{name}: A {ra.get('state')} {ra.get('job_s')} s, B {rb.get('state')} {rb.get('job_s')} s, "
              f"stitches {ra.get('stitches')} / {rb.get('stitches')}")
        for key in ("state", "design_sha", "review_sha", "warnings", *COMPARED_FORMATS):
            same = ra.get(key) == rb.get(key)
            differ += not same
            print(f"  {key:11} {'SAME' if same else 'DIFF'}")
            if not same:
                print(f"     A {ra.get(key)}\n     B {rb.get(key)}")
        ja, jb = ra.get("jef", {}), rb.get("jef", {})
        print(f"  {'jef':11} {'same' if ja == jb else 'differs'} (not compared: clock in the header); "
              f"verified A={ja.get('verified')} B={jb.get('verified')}")
    print(f"\n{differ} compared field(s) differ")
    return differ


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="drive a listening service, write hashes")
    r.add_argument("base")
    r.add_argument("out", type=Path)
    r.add_argument("fixtures", nargs="+", type=Path)
    c = sub.add_parser("compare", help="exit 1 unless two `run` files agree")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        print(json.dumps(run(args.base, args.out, args.fixtures), indent=1))
        return 0
    differ = compare(json.loads(args.a.read_text(encoding="utf-8")),
                     json.loads(args.b.read_text(encoding="utf-8")))
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
