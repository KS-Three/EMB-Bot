"""Does a frozen digitizer service produce the same bytes as the venv one?

Started as the 2026-11-10 spike instrument
(docs/packaging-freeze-spike-2026-11-10.md); `packaging/release_smoke.py`
drives it for the release build.

    python packaging/freeze_check.py run http://127.0.0.1:8731 venv.json testdata/logo_whitebg.png ...
    python packaging/freeze_check.py run http://127.0.0.1:8732 frozen.json testdata/logo_whitebg.png ...
    python packaging/freeze_check.py compare venv.json frozen.json

`run` drives a service that is ALREADY listening and writes a hash of
everything that came back. With fixture paths it is the spike's check:
`/digitize` with the default config, then `/export` as DST, PES and JEF. With
`--suite` it is the release check (`SUITE` below): one job down each lane the
spike did not reach (gradient, photo, `/lettering`, `/digitize-manual`)
beside the flat logo, every one exported in every format the Studio ships,
plus the Studio's own page if the service serves one.

`compare` exits 1 unless the capabilities, and each job's design, review
payload, warnings and exported bytes, are identical on both sides.

JEF is compared WITHOUT its clock: pystitch writes the wall time into the
header (offset 8, `YYYYMMDDHHMMSS`), so two JEF writes one second apart
differ in the same process. Those fourteen bytes are zeroed before hashing;
every other byte counts. (The spike did not compare JEF at all. Reading the
raw difference as "the freeze changed the file" is the mistake to avoid.)

Needs `httpx` (in requirements.txt). Starts nothing and stops nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parents[1]

#: The spike's three, kept so its recipe still runs as written.
REPORTED_FORMATS = ("dst", "pes", "jef")
#: One export per format the Studio's Download step offers
#: (`app/src/lib/machines.js`, `app/src/ui/DownloadStep.svelte`).
SHIPPED_FORMATS = ("dst", "pes", "exp", "jef", "xxx", "vp3")

#: Where pystitch's JEF writer puts `YYYYMMDDHHMMSS`.
JEF_CLOCK = slice(8, 22)

#: The release suite. Only fixtures already committed under testdata/.
#: `forced_class` pins the LANE, so a threshold retune cannot quietly turn the
#: gradient job into a second flat one; `detect_photographic` is what the
#: Studio sends with every upload. The lettering font is a VARIABLE one on
#: purpose: naming a weight makes fontTools instance it, the code path a
#: frozen build is most likely to have lost a module from.
SUITE = (
    {"name": "flat", "route": "digitize", "image": "testdata/logo_whitebg.png", "config": None},
    {"name": "gradient", "route": "digitize", "image": "testdata/photo/repro_gradient_white_icon.png",
     "config": {"forced_class": "gradient"}},
    {"name": "photo", "route": "digitize", "image": "testdata/photo/owl_kent.jpg",
     "config": {"forced_class": "photo_subject", "detect_photographic": True}},
    {"name": "lettering", "route": "lettering",
     "payload": {"font": "montserrat-bold", "text": "Fritsch's", "cap_mm": 8, "thread_rgb": [20, 40, 120]}},
    {"name": "manual", "route": "digitize-manual",
     "payload": {"shapes": [
         {"polygon": [[0, 0], [30, 0], [30, 18], [0, 18]],
          "holes": [[[10, 6], [20, 6], [20, 12], [10, 12]]],
          "technique": "fill", "thread_rgb": [200, 30, 30], "fill_angle_deg": 30},
         {"polygon": [[34, 0], [38, 0], [38, 18], [34, 18]], "technique": "satin", "thread_rgb": [20, 20, 20]},
         {"polygon": [[0, 22], [38, 22], [38, 23], [0, 23]], "technique": "run", "thread_index": 0},
     ], "config": {}}},
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def comparable_sha(fmt: str, data: bytes) -> str:
    """The hash `compare` uses: the file's own, except JEF's with the clock
    field zeroed (module docstring)."""
    if fmt == "jef" and len(data) >= JEF_CLOCK.stop:
        data = data[:JEF_CLOCK.start] + bytes(JEF_CLOCK.stop - JEF_CLOCK.start) + data[JEF_CLOCK.stop:]
    return _sha(data)


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


def _poll(c, name: str, submitted, t0: float) -> dict:
    if submitted.status_code != 202:
        return {"state": "refused", "error": f"HTTP {submitted.status_code}: {submitted.text[:300]}"}
    job = submitted.json()["job_id"]
    while True:
        s = c.get(f"/jobs/{job}").json()
        if s["state"] in ("done", "error"):
            return s
        if time.perf_counter() - t0 > 900:
            raise SystemExit(f"{name}: job still running after 900 s")
        time.sleep(0.5)


def _row(c, name: str, submit, formats: tuple[str, ...]) -> dict:
    t0 = time.perf_counter()
    s = _poll(c, name, submit(), t0)
    row = {"state": s["state"], "job_s": round(time.perf_counter() - t0, 1)}
    if s["state"] != "done":
        row["error"] = s.get("error")
        return row
    design = s["design"]
    row["stitches"] = len(design["stitches"])
    row["design_sha"] = _sha(json.dumps(design, sort_keys=True).encode())
    row["review_sha"] = _sha(json.dumps(s.get("review"), sort_keys=True).encode())
    row["blended_shapes"] = sum(1 for sh in (s.get("review") or {}).get("shapes", []) if sh.get("blended"))
    row["warnings"] = sorted(
        w if isinstance(w, str) else w.get("code", str(w)) for w in s.get("warnings") or [])
    for fmt in formats:
        e = c.post("/export", json={"design": design, "format": fmt, "label": "SPIKE"})
        row[fmt] = {"status": e.status_code, "bytes": len(e.content), "sha": _sha(e.content),
                    "cmp": comparable_sha(fmt, e.content),
                    "verified": e.headers.get("X-Export-Verified")}
    return row


def _studio(c) -> dict:
    """The page at `/` and every file it names. `served: False` when this
    service has no Studio mounted (the plain venv service)."""
    r = c.get("/")
    kind = r.headers.get("content-type", "")
    if r.status_code != 200 or "text/html" not in kind:
        return {"served": False, "status": r.status_code}
    refs = sorted(set(re.findall(r'(?:src|href)="\./([^"]+)"', r.text)))
    want = {".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
    bad = []
    for ref in refs:
        f = c.get(f"/{ref}")
        expect = want.get(Path(ref).suffix)
        got = f.headers.get("content-type", "")
        if f.status_code != 200 or not f.content or (expect and expect not in got):
            bad.append(f"{ref}: HTTP {f.status_code}, {got or 'no content type'}, {len(f.content)} B")
    return {"served": True, "status": 200, "app_root": '<div id="app">' in r.text,
            "files": len(refs), "scripts": sum(ref.endswith(".js") for ref in refs), "bad": bad}


def run(base: str, out_path: Path, fixtures: list[Path], suite: bool = False) -> dict:
    import httpx

    health, waited = _wait_health(base, 120)
    out = {"base": base, "health_wait_s": round(waited, 2),
           "capabilities": health["capabilities"], "engine": health.get("engine"),
           "fixtures": {}}
    with httpx.Client(base_url=base, timeout=120) as c:
        for p in fixtures:
            data = p.read_bytes()
            out["fixtures"][p.name] = _row(
                c, p.name, lambda: c.post("/digitize", files={"image": (p.name, data, "image/png")}),
                REPORTED_FORMATS)
        if suite:
            out["studio"] = _studio(c)
            fonts = c.get("/fonts/outline")
            out["outline_fonts"] = len(fonts.json().get("fonts", [])) if fonts.status_code == 200 else None
        for case in SUITE if suite else ():
            if case["route"] == "digitize":
                p = DIGITIZER / case["image"]
                files = {"image": (p.name, p.read_bytes(), "application/octet-stream")}
                form = {"config": json.dumps(case["config"])} if case["config"] else {}
                row = _row(c, case["name"], lambda: c.post("/digitize", files=files, data=form),
                           SHIPPED_FORMATS)
                seen = c.post("/classify", files=files, data=form)
                row["class"] = seen.json().get("class") if seen.status_code == 200 else f"HTTP {seen.status_code}"
            else:
                row = _row(c, case["name"], lambda: c.post(f"/{case['route']}", json=case["payload"]),
                           SHIPPED_FORMATS)
            out["fixtures"][case["name"]] = row
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _formats(row: dict) -> list[str]:
    return [k for k, v in row.items() if isinstance(v, dict) and "sha" in v]


def compare(a: dict, b: dict) -> int:
    """Print both sides; return the number of compared fields that differ."""
    differ = 0
    same = a["capabilities"] == b["capabilities"]
    differ += not same
    print(f"capabilities  {'SAME' if same else 'DIFF: the two sides are not running the same pipeline'}\n"
          f"              A {a['capabilities']}\n              B {b['capabilities']}")
    for name in sorted(set(a["fixtures"]) | set(b["fixtures"])):
        ra, rb = a["fixtures"].get(name, {}), b["fixtures"].get(name, {})
        print(f"\n{name}: A {ra.get('state')} {ra.get('job_s')} s, B {rb.get('state')} {rb.get('job_s')} s, "
              f"stitches {ra.get('stitches')} / {rb.get('stitches')}")
        for key in ("state", "design_sha", "review_sha", "warnings"):
            same = ra.get(key) == rb.get(key) and key in ra
            differ += not same
            print(f"  {key:11} {'SAME' if same else 'DIFF'}")
            if not same:
                print(f"     A {ra.get(key)}\n     B {rb.get(key)}")
        for fmt in sorted(set(_formats(ra)) | set(_formats(rb))):
            fa, fb = ra.get(fmt, {}), rb.get(fmt, {})
            if "cmp" not in fa or "cmp" not in fb:
                # A run file written before JEF's clock was masked.
                print(f"  {fmt:11} not compared (no clock-free hash in this file)")
                continue
            same = all(fa.get(k) == fb.get(k) for k in ("status", "bytes", "cmp", "verified"))
            differ += not same
            note = " (clock field zeroed)" if fmt == "jef" else ""
            print(f"  {fmt:11} {'SAME' if same else 'DIFF'}, {fa.get('bytes')} B{note}")
            if not same:
                print(f"     A {fa}\n     B {fb}")
    print(f"\n{differ} compared field(s) differ")
    return differ


def release_failures(frozen: dict, expect_commit: str | None = None,
                     expect_release: str | None = None) -> list[str]:
    """What is wrong with a `run --suite` of the FROZEN app, judged on its
    own (the comparison with the venv is `compare`). Empty means ship-shaped."""
    bad = []
    eng = frozen.get("engine") or {}
    if expect_commit and eng.get("commit") != expect_commit:
        bad.append(f"/health engine.commit is {eng.get('commit')!r}, the build stamped {expect_commit!r}")
    if expect_release and eng.get("release") != expect_release:
        bad.append(f"/health engine.release is {eng.get('release')!r}, the build stamped {expect_release!r}")
    caps = frozen.get("capabilities") or {}
    if caps.get("ocr") is not True:
        bad.append("capabilities.ocr is not true: the bundled tessdata is not being read")
    if caps.get("face_priors") is not True:
        bad.append("capabilities.face_priors is not true: the bundled face model is not being read")
    if not frozen.get("outline_fonts"):
        bad.append("GET /fonts/outline lists no font: the bundled outline fonts are not being read")
    studio = frozen.get("studio") or {}
    if not studio.get("served"):
        bad.append(f"GET / is not the Studio (HTTP {studio.get('status')})")
    else:
        if not studio.get("app_root") or not studio.get("scripts"):
            bad.append("GET / is HTML but not the Studio's page (no #app, or no script)")
        bad += [f"Studio file {b}" for b in studio.get("bad", [])]
    rows = frozen.get("fixtures") or {}
    for case in SUITE:
        row = rows.get(case["name"])
        if row is None:
            bad.append(f"{case['name']}: not run")
            continue
        if row.get("state") != "done" or not row.get("stitches"):
            bad.append(f"{case['name']}: {row.get('state')}, {row.get('error') or 'no stitches'}")
            continue
        forced = (case.get("config") or {}).get("forced_class")
        if forced and row.get("class") != forced:
            bad.append(f"{case['name']}: classified {row.get('class')!r}, asked for {forced!r}")
        if case["name"] == "gradient" and not row.get("blended_shapes"):
            bad.append("gradient: no shape sewed through the blend tier, so the gradient lane did not run")
        for fmt in SHIPPED_FORMATS:
            e = row.get(fmt) or {}
            if e.get("status") != 200 or e.get("verified") != "true" or not e.get("bytes"):
                bad.append(f"{case['name']}: {fmt} export HTTP {e.get('status')}, "
                           f"verified {e.get('verified')}, {e.get('bytes')} B")
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="drive a listening service, write hashes")
    r.add_argument("base")
    r.add_argument("out", type=Path)
    r.add_argument("fixtures", nargs="*", type=Path)
    r.add_argument("--suite", action="store_true", help="the release suite: every lane, every shipped format")
    c = sub.add_parser("compare", help="exit 1 unless two `run` files agree")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "run":
        if not args.fixtures and not args.suite:
            ap.error("run: name at least one fixture, or pass --suite")
        print(json.dumps(run(args.base, args.out, args.fixtures, suite=args.suite), indent=1))
        return 0
    differ = compare(json.loads(args.a.read_text(encoding="utf-8")),
                     json.loads(args.b.read_text(encoding="utf-8")))
    return 1 if differ else 0


if __name__ == "__main__":
    sys.exit(main())
