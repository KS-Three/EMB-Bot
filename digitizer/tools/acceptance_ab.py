#!/usr/bin/env python
"""Acceptance A/B contact-sheet harness -- the phase-4 eyeball loop (spec
decisions 1, 5, 6).

Runs every image in the gitignored acceptance dir through the classical
lane and, when the isolated SAM2 venv is actually runnable on this machine,
the SAM2 lane too -- both auto-routed off nothing but
forced_class="photo_subject" (see digitizer_core.tools_acceptance.
variant_matrix: Task 3's auto_photo_tier picks streamline, Task 2's
effective_split_tonal picks the tonal split, both from that one field).
Talks to the LIVE service over the same wire the probe scripts use (POST
/digitize, GET /jobs/{id}, POST /export) -- deliberately not a direct
pipeline call, since the point is judging what a real digitize job produces
end to end, Studio included.

Writes a side-by-side contact sheet Kent judges by eye. No scorecard number
anywhere on it: build step 8's decision record calls the metric explicitly
non-authoritative for this call, so the sheet carries stitch/trim/thread
counts only (digitizer_core.tools_acceptance.sheet_row is a pass-through
for exactly this reason -- see its docstring).

Usage:
    .venv/Scripts/python tools/acceptance_ab.py
    .venv/Scripts/python tools/acceptance_ab.py --dir testdata/photo/acceptance --service http://127.0.0.1:8721

Produces, per run:
    debug_out/acceptance_<UTCdate>/contact_sheet.html   the sheet
    debug_out/acceptance_<UTCdate>/<file>_<variant>.json  each job's full
        response (design/review/stats/warnings/preflight), for whichever
        run needs a closer look than the sheet gives
"""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.stage2_sam2_segment import sam2_segmentation_unavailable_reason  # noqa: E402
from digitizer_core.tools_acceptance import sheet_row, variant_matrix  # noqa: E402

DEFAULT_DIR = ROOT / "testdata" / "photo" / "acceptance"
DEFAULT_SERVICE = "http://127.0.0.1:8721"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

# SAM2 is measured 40-60s warm, up to ~156s cold (task-5 evidence,
# task5_live_job_sam2.json's _meta.elapsed_s alongside the cold-start
# probe) -- generous headroom so a cold checkpoint load never reads as a
# stuck job. Classical runs finish in low single-digit seconds by
# comparison; the same timeout covers both without needing a per-variant
# knob.
POLL_TIMEOUT_S = 300.0
POLL_INTERVAL_S = 2.0
HEALTH_TIMEOUT_S = 60.0


def _post_digitize(service: str, image_path: Path, config: dict) -> dict:
    """POST /digitize -- multipart form, plain urllib, no new deps. Same
    wire pattern the probe scripts use (session scratchpad t3_smoke.py)."""
    boundary = uuid.uuid4().hex
    data = image_path.read_bytes()
    mime = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"config\"\r\n\r\n"
        f"{json.dumps(config)}\r\n".encode(),
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
         f"filename=\"{image_path.name}\"\r\nContent-Type: {mime}\r\n\r\n"
         ).encode() + data + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req = urllib.request.Request(
        service.rstrip("/") + "/digitize", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _poll_job(service: str, job_id: str) -> dict:
    """Poll GET /jobs/{id} until done/error, or our own generous timeout --
    the probe scripts' loop, with a longer ceiling for SAM2's cold start."""
    deadline = time.monotonic() + POLL_TIMEOUT_S
    job: dict = {"job_id": job_id, "state": "queued"}
    while True:
        with urllib.request.urlopen(f"{service.rstrip('/')}/jobs/{job_id}", timeout=10) as resp:
            job = json.load(resp)
        if job.get("state") in ("done", "error"):
            return job
        if time.monotonic() >= deadline:
            job["state"] = "timeout"
            return job
        time.sleep(POLL_INTERVAL_S)


def _export_svg(service: str, design: dict, label: str) -> str:
    """POST /export, format=svg -- the service's vector proof
    (digitizer_service/formats.py: "Not a machine file -- a proof for
    review or printing."). Returns the raw `<svg ...>...</svg>` markup:
    pystitch.write_svg emits a bare root element, no XML prolog and no
    ids/defs to collide across multiple instances on one page (checked
    directly against pystitch's output before relying on it here) -- safe
    to drop straight into the contact sheet's <td>."""
    payload = json.dumps({"design": design, "format": "svg", "label": label}).encode()
    req = urllib.request.Request(
        service.rstrip("/") + "/export", data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _wait_for_health(service: str) -> None:
    deadline = time.monotonic() + HEALTH_TIMEOUT_S
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(service.rstrip("/") + "/health", timeout=2)
            return
        except Exception as exc:  # noqa: BLE001 -- any failure just means "not up yet"
            last_exc = exc
            time.sleep(1)
    raise SystemExit(f"service at {service} never came up ({last_exc})")


def _fail_stats(wall_s: float, warning: str) -> dict:
    return {"shapes": 0, "stitches": 0, "trims": 0, "threads": 0,
            "warnings": [warning], "wall_s": round(wall_s, 1)}


def _job_stats(job: dict, wall_s: float) -> dict:
    """A finished job -> the counts sheet_row carries.

    `design["colors"]` is one entry per SEW BLOCK (adapter.plan_to_design),
    not per shape and not per distinct thread -- the owl SAM2 run tonight
    had 84 shapes, 59 color blocks, and only 20 distinct threads, three
    different real numbers. The distinct count that answers "how many
    thread changes is Kent looking at" is `thread_index` across
    review['shapes'], not colorCount.
    """
    review = job.get("review") or {}
    design = job.get("design") or {}
    stats = job.get("stats") or {}
    shapes = review.get("shapes") or []
    # F5, 2026-08-19: a shape dict missing `thread_index` folded `None` into
    # the set as a phantom extra "thread" on top of every real one -- guard
    # it out rather than count a missing field as a distinct colour.
    threads = {s.get("thread_index") for s in shapes
               if isinstance(s, dict) and s.get("thread_index") is not None}
    warnings = [w.get("code", w) if isinstance(w, dict) else w
                for w in job.get("warnings") or []]
    return {
        "shapes": len(shapes),
        "stitches": design.get("stitchCount", 0),
        "trims": stats.get("trims", 0),
        "threads": len(threads),
        "warnings": warnings,
        "wall_s": round(wall_s, 1),
    }


def _write_job_json(out_dir: Path, file: str, tag: str, payload: dict) -> None:
    stem = Path(file).stem
    (out_dir / f"{stem}_{tag}.json").write_text(
        json.dumps(payload, indent=1, sort_keys=False), encoding="utf-8")


_WIRE_ERRORS = (urllib.error.URLError, OSError, KeyError, json.JSONDecodeError)


def run(images: list[Path], service: str, out_dir: Path
       ) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """-> (sheet_rows, {file: {variant_tag: {"svg": str|None, "error": str|None}}}, matrix)"""
    _wait_for_health(service)
    sam2_available = sam2_segmentation_unavailable_reason() is None
    matrix = variant_matrix(sam2_available)
    tags = [v["tag"] for v in matrix]
    note = "" if sam2_available else "  (SAM2 unavailable on this machine -- no sam2 arm)"
    print(f"variants: {tags}{note}")

    rows: list[dict] = []
    cells: dict[str, dict] = {}
    for image_path in images:
        file = image_path.name
        cells[file] = {}
        for variant in matrix:
            tag, config = variant["tag"], variant["config"]
            t0 = time.monotonic()
            try:
                sub = _post_digitize(service, image_path, config)
                job = _poll_job(service, sub["job_id"])
            except _WIRE_ERRORS as exc:
                wall_s = time.monotonic() - t0
                rows.append(sheet_row(file, tag, _fail_stats(wall_s, f"REQUEST_ERROR: {exc}")))
                cells[file][tag] = {"svg": None, "error": str(exc)}
                _write_job_json(out_dir, file, tag, {"error": str(exc)})
                continue

            wall_s = time.monotonic() - t0
            if job.get("state") != "done":
                detail = job.get("error") or job.get("state")
                rows.append(sheet_row(file, tag, _fail_stats(wall_s, f"JOB_{detail}")))
                cells[file][tag] = {"svg": None, "error": str(detail)}
                _write_job_json(out_dir, file, tag, job)
                continue

            stats = _job_stats(job, wall_s)
            rows.append(sheet_row(file, tag, stats))
            _write_job_json(out_dir, file, tag, job)
            try:
                svg = _export_svg(service, job["design"], label=f"{image_path.stem}_{tag}")
                cells[file][tag] = {"svg": svg, "error": None}
            except _WIRE_ERRORS as exc:
                # Digitizing worked -- the counts above are real -- only the
                # vector proof is missing, so the row stays, just without a
                # picture in its cell.
                cells[file][tag] = {"svg": None, "error": f"export failed: {exc}"}
    return rows, cells, matrix


def _print_table(rows: list[dict]) -> None:
    cols = ["file", "variant", "regions", "threads", "stitches", "trims", "warnings", "seconds"]
    widths = [28, 10, 7, 7, 8, 6, 40, 7]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        warnings = ", ".join(str(w) for w in row.get("warnings", [])) or "-"
        cells = [
            row.get("file", ""), row.get("variant", ""),
            str(row.get("shapes", 0)), str(row.get("threads", 0)),
            str(row.get("stitches", 0)), str(row.get("trims", 0)),
            warnings, f"{row.get('wall_s', 0):.1f}",
        ]
        print("  ".join(c.ljust(w) for c, w in zip(cells, widths)))


def _counts_html(row: dict | None) -> str:
    if row is None:
        return "<p class=\"counts\">not run</p>"
    warn = ", ".join(html.escape(str(w)) for w in row.get("warnings", [])) or "none"
    return (
        f"<p class=\"counts\">{row.get('shapes', 0)} regions &middot; "
        f"{row.get('threads', 0)} threads &middot; {row.get('stitches', 0)} stitches &middot; "
        f"{row.get('trims', 0)} trims &middot; {row.get('wall_s', 0):.1f}s</p>"
        f"<p class=\"warn\">{warn}</p>"
    )


def _render_html(images: list[Path], matrix: list[dict], cells: dict, rows: list[dict],
                  image_dir: Path, service: str) -> str:
    tags = [v["tag"] for v in matrix]
    row_by_key = {(r["file"], r["variant"]): r for r in rows}

    header = "<tr><th>file</th>" + "".join(f"<th>{html.escape(t)}</th>" for t in tags) + "</tr>"

    body_rows = []
    for image_path in images:
        file = image_path.name
        tds = [f"<th class=\"rowhead\">{html.escape(file)}</th>"]
        for tag in tags:
            cell = cells.get(file, {}).get(tag)
            row = row_by_key.get((file, tag))
            if cell is None:
                proof = "<p class=\"missing\">not run</p>"
            elif cell.get("error"):
                proof = f"<p class=\"error\">error: {html.escape(cell['error'])}</p>"
            else:
                proof = cell["svg"]
            tds.append(f"<td><div class=\"proof\">{proof}</div>{_counts_html(row)}</td>")
        body_rows.append(f"<tr>{''.join(tds)}</tr>")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Acceptance contact sheet</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; margin: 24px;
          color: #1c1c1c; background: #fafafa; }}
  h1 {{ font-size: 1.2rem; margin-bottom: 0.2rem; }}
  .meta {{ color: #555; font-size: 0.85rem; margin-bottom: 1rem; }}
  .meta code {{ background: #eee; padding: 0 4px; border-radius: 3px; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; }}
  th, td {{ border: 1px solid #ccc; padding: 10px; vertical-align: top; text-align: left; }}
  th {{ background: #f0f0f0; }}
  th.rowhead {{ white-space: nowrap; font-family: monospace; }}
  .proof {{ min-width: 240px; max-width: 340px; }}
  .proof svg {{ width: 100%; height: auto; max-height: 340px; display: block;
                background: #fff; border: 1px solid #eee; }}
  .counts {{ font-family: monospace; font-size: 0.8rem; margin: 6px 0 2px; color: #333; }}
  .warn {{ font-size: 0.78rem; color: #a15c00; margin: 0; word-break: break-word; }}
  .error {{ color: #b00020; font-weight: bold; }}
  .missing {{ color: #999; font-style: italic; }}
</style>
</head>
<body>
<h1>Acceptance contact sheet</h1>
<p class="meta">
  dir: <code>{html.escape(str(image_dir))}</code> &middot;
  service: <code>{html.escape(service)}</code> &middot;
  generated {generated} &middot;
  counts only, no score -- judge by eye (spec: the metric is
  non-authoritative for this call)
</p>
<table>
{header}
{''.join(body_rows)}
</table>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR,
                     help=f"acceptance photos dir (default: {DEFAULT_DIR})")
    ap.add_argument("--service", default=DEFAULT_SERVICE,
                     help=f"running digitizer service base URL (default: {DEFAULT_SERVICE})")
    args = ap.parse_args()

    image_dir = args.dir if args.dir.is_absolute() else (ROOT / args.dir)
    if not image_dir.is_dir():
        print(f"no such directory: {image_dir}", file=sys.stderr)
        return 1

    images = sorted(
        p for p in image_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        print(f"no images in {image_dir} -- drop 3-5 real portrait/pet photos in "
              f"and re-run (see {image_dir / 'README.md'}).")
        return 0

    stamp = datetime.now(timezone.utc).date().isoformat()
    out_dir = ROOT / "debug_out" / f"acceptance_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows, cells, matrix = run(images, args.service, out_dir)

    print()
    _print_table(rows)

    sheet_path = out_dir / "contact_sheet.html"
    sheet_path.write_text(
        _render_html(images, matrix, cells, rows, image_dir, args.service), encoding="utf-8")
    print(f"\nwrote {sheet_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
