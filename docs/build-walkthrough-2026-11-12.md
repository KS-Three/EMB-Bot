# EMB-Bot build walkthrough — 2026-11-12

Screenshots of the Studio built from `main` at `bdae1860` (after #1411), driven in a browser as a user would, so Kent can see the product without running it. Nothing was changed. Artwork used is already in the repo: the starter pack, `app/e2e/fixtures/enthusiast_logo.png`, `app/e2e/fixtures/two-squares.png`. Images are in [`build-walkthrough-2026-11-12/`](build-walkthrough-2026-11-12/).

**How it was run.** `npm run build` in `app/` (13 s), then the digitizer service serving that build on `127.0.0.1:8721` (about 4–12 s to start). The one-click launcher from #1405 did **not** start from a checkout; see "What did not work", item 1. Timings are on a busy laptop: two other digitize jobs were running, so treat them as upper-ish bounds.

## 1. Start screen and starter designs (#1402) — works

An empty canvas, a hoop, and three ways in: Add text, Upload file, Starter designs. The picker shows 12 CC0 / public-domain designs, each with artist, licence and a source link. Picking Heart put a real 80×75 mm, 3-colour, 15,649-stitch design on the canvas with no waiting.

![start](build-walkthrough-2026-11-12/01-start-screen.jpg)
![picker](build-walkthrough-2026-11-12/02-starter-picker.jpg)
![heart on canvas](build-walkthrough-2026-11-12/03-starter-on-canvas.jpg)

## 2. Upload, lane reading, Auto Digitize, quality report — works

Upload shows the artwork and one reading line ("Read as flat art, sewing as solid color regions."). Nothing runs until Auto Digitize is pressed. After the run the same row says "27 shapes, 2 colors at 96 mm", the canvas shows 2,954 stitches, 96×19 mm. The Download step carries the quality report: grade B 88/100, with a warning that 12 of 26 satin shapes sew below readable size, plus run time, bobbin, stabilizer, needle and thread list.

![uploaded](build-walkthrough-2026-11-12/04-upload-lane-reading.jpg)
![running](build-walkthrough-2026-11-12/05-digitize-running.jpg)
![result](build-walkthrough-2026-11-12/06-digitize-result.jpg)
![quality report](build-walkthrough-2026-11-12/07-download-step-quality.jpg)

Timing: about 12–15 s the first time (poll started ~6 s after the click: 9 s measured + ~6 s). The same image again right after a Cancel: **44.0 s** click to caption. Not understood: busy machine, or something left over from the cancel.

## 3. Cancel a running digitize (#1400/#1408) — works

A Cancel button appears beside "Digitizing your art…" 0.4–0.6 s after the click. Pressing it brings Auto Digitize back in 0.1–0.3 s with no error and no half-result on the canvas. The reading row keeps its "27 shapes, 2 colors" line. The next run started normally.

![cancel mid-run](build-walkthrough-2026-11-12/09-cancel-mid-run.jpg)
![after cancel](build-walkthrough-2026-11-12/10-after-cancel.jpg)
![digitize again](build-walkthrough-2026-11-12/11-digitize-after-cancel.jpg)

## 4. Edit: reshape, add hole, move, Undo/Redo — works, with one trap

Click a shape: a popover offers Edit points, Move shape, Add hole, simplify (0.2/0.5/1 mm) and Delete shape. The artwork is a black and a red square (digitize 10.4 s, 9,050 stitches).

- **Edit points:** dragged the black square's top-right corner outward; the outline follows live. Done, then Auto Digitize restitched in 7.1 s: 9,050 → 9,816 stitches, 97×37 → 97×42 mm.
- **Add hole:** four clicks inside the red square, click the first point to close. Restitch 5.7 s: the hole sews as open garment with an edge. 9,816 → 9,875 stitches.
- **Move shape:** dragged the red square 11.97 mm left. Restitch 6.0 s: 85×42 mm.
- **Undo/Redo:** both buttons walk back and forward through those edits.

![popover](build-walkthrough-2026-11-12/13-shape-popover.jpg)
![edit points](build-walkthrough-2026-11-12/14-edit-points-mode.jpg)
![after reshape, outline only](build-walkthrough-2026-11-12/15-after-reshape.jpg)
![reshape restitched](build-walkthrough-2026-11-12/16-reshape-restitched.jpg)
![add hole](build-walkthrough-2026-11-12/17-add-hole-draw.jpg)
![hole restitched](build-walkthrough-2026-11-12/20-hole-restitched.jpg)
![move shape](build-walkthrough-2026-11-12/22-shape-moved.jpg)
![move restitched](build-walkthrough-2026-11-12/23-move-restitched.jpg)
![three undos](build-walkthrough-2026-11-12/25-undo-three.jpg)

**Delete right after add (#1399/#1411): works.** Added a Text element, deleted it immediately; Undo brought it back; a second Undo took the add back; Redo re-added it. Each is its own step.

![undo restores the deleted element](build-walkthrough-2026-11-12/32-undo-restores-element.jpg)

## 5. Lettering — works

Typing a name updates the canvas at once (0.14 s): "Kent" in the default Ink/Stitch Medium font, 1,266 stitches, 96×25 mm. The font browser has search, category chips and a "Fits your text (109)" filter, each card showing its best size range. Picking Allegria 55 restitched in 0.15 s: 2,109 stitches, 98×53 mm.

![default font](build-walkthrough-2026-11-12/27-lettering-default-font.jpg)
![font browser](build-walkthrough-2026-11-12/28-font-browser.jpg)
![Allegria 55](build-walkthrough-2026-11-12/29-lettering-allegria.jpg)

## 6. Export — works

The Download step lists DST, PES, EXP, JEF, XXX, VP3, SVG, PNG and the PDF worksheet, a thread chart picker, machine brand, and Download all. Download all took 1.6 s and produced `kent.zip` (552 KB) holding the 6 machine formats (DST, PES, EXP, JEF, XXX, VP3), SVG, the PDF worksheet, a PNG preview and a threads text file. The read-back result is a one-line status, "Saved ZIP" or "Saved DST (browser encoder)"; a success says nothing about the check it ran.

![export panel](build-walkthrough-2026-11-12/33-export-panel.jpg)
![Download all](build-walkthrough-2026-11-12/34-download-all-result.jpg)

## What did not work, most serious first

1. **The Windows launcher (#1405) never started the service from a checkout.** `python digitizer/embbot_launcher.py --console --no-browser` printed "Starting EMB-Bot…", then after 120 s: "EMB-Bot could not start: its service was not ready after 120 seconds, so it was stopped." Reproduced twice (16:25 and 16:49, once from a clean single start). The log (`%LOCALAPPDATA%\EMB-Bot\logs\emb-bot.log`) has only the launcher's own two lines and nothing from the service. The same child command run by hand, `launcher.py --serve --studio app/dist --port 8721`, was up in 4–12 s. Run by hand with the launcher's pipe switch (`EMBBOT_LAUNCHER_PIPE=1`, stdin a pipe), it printed nothing and never bound the port in 45 s. So the hang looks to sit in the child's "exit when the launcher goes" path (`_exit_when_launcher_goes`) on this machine. That is a read of one experiment, not a fix. The CI Windows run (frozen exe) was reported green, so this may be specific to running from a checkout. I did not test the frozen exe or the installer.
2. **Edits do not show in the stitches until you press Auto Digitize.** After Done, the canvas keeps the old stitches and the panel says "Changed since the last run — press Auto Digitize Image to restitch." That matches the documented rule, but it reads like a hang: my first two checks waited 60 s and 90 s for a stitch count that never changed. A new customer will hit the same thing.
3. **Undo steps do not map one-to-one onto what you see.** After move, restitch, three Undos left the black shape still skewed, the hole outline still drawn, and stitches back at the pre-hole count (9,816) with the "changed since last run" banner. The restitches seem to be steps of their own. Not investigated.
4. **A hole made the stitch count go up** (9,816 → 9,875, +59) although it removed roughly a fifth of the red square's area. It may be the hole's edge stitching. Not checked.
5. **The same digitize took 44 s on the second run vs 12–15 s on the first** (item 2 above). Cause unknown.
6. **Quiet success on export.** "Saved ZIP" gives no sign that the read-back verification ran. I did not exercise the block-on-mismatch path, nor the service-side export of digitized artwork (only the browser encoders: lettering).
7. Nitpick: hovering the Colors slider left its tooltip over the panel in an early screenshot (my mouse position, not a bug).

**Not covered:** the frozen exe and installer, the 5173 Studio dev server (another session holds it), photo-lane artwork, the Compare view, Simulate, the Hat and Tee garments, the Windows `.cmd` shortcut, anything needing the rembg/SAM2 venvs.

**Process notes:** the app restarted mid-session and killed my service; I restarted it on the same port and redid only what was lost. The service from my first launcher attempt exited by itself. When done I stopped only the service I started.
