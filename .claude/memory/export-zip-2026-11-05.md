---
name: export-zip-2026-11-05
description: Studio "Download all" = one zip (7 stitch formats + worksheet PDF + preview PNG + threads.txt) through the verified export path; fails whole on any one format; PEC/U01 left out; measured time and size at 24k stitches
metadata:
  type: project
---

Kent 2026-11-05 (free-digitizer follow-ups): **ZIP ONLY, one "Download all"**. No basting
frame, no max-stitch split, no PES v1/v6 pair. Built on the 11-04 Stitchist teardown's
export bundle.

**What it is.** A "Download all" button in the Download step's format grid
(`DownloadStep.svelte` `dlAll`, `data-testid="download-all"`), assembled by
`app/src/lib/exportZip.js` with `fflate` `zipSync` (already in the bundle as jsPDF's
dependency, pinned `^0.8.3` to keep one copy). Entries, stem = the single files' slug
(`exportFileName`): `<name>.{dst,pes,exp,jef,xxx,vp3,svg}`, `<name>-worksheet.pdf`,
`<name>-preview.png`, `<name>-threads.txt` (chart label, then `n. <code name> (#HEX)`
in sewn order, CRLF).

**Rules it keeps.**
- Each format is the SAME `exportDesignPreferService` call the single button makes
  (see [[export-readback-2026-11-05]]), so every file in the zip has been re-read; one
  failure throws, the archive stops there, **nothing is saved**, and the customer sees
  that format's "Export failed: ..." sentence. A zip with a missing tenth file reads
  as complete, so it is all or nothing.
- Locked like the machine-file buttons ([[download-stale-guard-2026-10-25]]): disabled
  while `blocksDownload`; also disabled with no service (JEF/XXX/VP3 have no browser
  encoder), no text either way. Same hoop/preflight confirm ("Download all anyway").
- DST inside the zip honours Jumps per trim (#1238). Saves through `saveOut`, so the
  chosen save folder applies.
- No new settings, no explanatory text ([[no-warnings-reaches-readouts]]).

**Left out on purpose.** PEC and U01: the Studio ships neither (Kent 2026-09-12 scope
call), so the zip does not hand over files its own buttons refuse to. The service's
`/export` writes both; add them to `ZIP_STITCH_FORMATS` only with a button for each.

**Plumbing.** `exportWorksheetPDF(..., { asBytes: true })` returns the PDF bytes unsaved
(`pdfsheet.js` takes `save: false`; default unchanged). PNG is `exportPNG`'s blob.
PDF and PNG are stored (level 0): they are already deflated.

**Measured (Chromium, real service, `WWWWWWWW` x 8 lines on Full Back, 23,936 stitches,
click to download event, 3 runs):** 2.59 / 2.23 / 2.15 s; zip 1,078,531 bytes. Members:
DST 73 KB, PES 147 KB, EXP 49 KB, JEF 49 KB, XXX 49 KB, VP3 48 KB, SVG 256 KB, PDF
207 KB, PNG 709 KB. The PNG is 2/3 of the archive. At 2,867 stitches: 1.3 s, 90 KB.
Lettering caps near 15k stitches on one line of text; the 24k needed 8 lines.

**Tests.** `exportZip.spec.js` (entries, bytes, fail-all), `DownloadStep.zip.spec.js`
(button, jumps-per-trim, confirm, no service), `DownloadStep.zip.readback.spec.js`
(real writers, corrupted DST/PES saves nothing), `DownloadStep.stale.spec.js`
(locked), `e2e/download-all.spec.js` (real service: zip DST equals the DST button's).
