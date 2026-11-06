---
name: export-readback-2026-11-05
description: Every stitch-file export is re-read and BLOCKED on a mismatch (Kent 11-05); per-format checks on each path, what pystitch's readers cannot give back, measured cost at 20k stitches
metadata:
  type: project
---

Kent 2026-11-05: re-read every export, **block the download** on a mismatch. A file
that fails its own read-back is broken, not low quality, so the 10-02 "no warnings
reach readouts" ruling does not apply; a plain "Export failed" is allowed.
Prompted by the 11-04 free-digitizer survey (openstitch, Needler, embroidery-magic
all re-read before download).

**Service (`digitizer_service/readback.py`, in `/export`).** `expect(pattern)` BEFORE
`formats.write`, `verify` after, with pystitch's reader (independent of the writer).
Mismatch = **500** `{detail: "Export failed: <check> (expected X, read back Y).",
readback: {failed: [...]}}`, no file. 500 not 422: the service answers a caller's bad
input 400 and its own defect 500 (the unhandled handler); a mismatch is the second.
Success adds `X-Export-Verified: true` + `X-Export-Readback` (JSON counts); SVG (and
anything unreadable) gets `false` + `X-Export-Verify-Reason`. Bytes never change.
Checks: stitch_count, stitch_positions, trim_count/order, color_count/order,
longest_stitch (chained, <= 121), bounding_box, DST header_bbox. All 8 machine
formats read back; what pystitch cannot give back is listed in `skipped`, not
hidden: VP3 longest_stitch; XXX run-start stitches read as moves (0x7D big move) so
order/box/positions skipped and stitch_count is a range; JEF/VP3 trims "at least".
Fit on ~15k random write/read cycles to zero false alarms; a seeded slice is a test.

**Browser (`src/readback.js`, in `exportDesign`).** Writer bytes re-read for DST
(`readDSTRecords` in dstimport.js, same bit table as the axis fix), EXP and PES
(readers lifted from `tools/file-cut-census.mjs`, not new codecs). Expected values
by arithmetic on the design, not the encoders' splitters. DST trims are read at the
writer's own jumps-per-trim N (at 1 or 2 a jump also reads as a trim, both sides).
Failure throws `ExportVerifyError` ("Export failed: ..."), nothing saved. Same-repo
check: it catches a writer that does not write what it was handed, NOT a shared
misreading of the format (the DST axis bug); the service read is the independent one.

**Service refuses its own file -> browser file** (verified by the same read-back)
is returned instead; both failing = no file. Director may veto this fallback.

**Cost, 20,000 sewn stitches (median):** browser DST 12.7 ms, EXP 6.7, PES 9.1.
Service `expect` ~40 ms + read-back 48-60 ms per format, DST 175 ms (second raw read
for the header); writes themselves are 60-150 ms.

**Traps found fitting it:** pystitch drops a colour change before the first stitch,
merges a trim with no stitch since the last cut, gives colour changes no position,
turns a PES colour change between two same-cone threads into a STOP, and writes a
DST trim as a +-4 wiggle that widens raw extents. Vitest through a node_modules
junction fails ~230 UI specs (duplicate DOM, not a code bug); use `npm ci`.

Links: [[no-warnings-reaches-readouts]], [[free-digitizer-survey-2026-11-04]].
