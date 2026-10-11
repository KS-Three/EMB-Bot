// Sewn-width preview: draw a satin column at the width the cloth will show,
// not the width the FILE carries (Kent, 2026-10-06).
//
// Every satin column in a machine file is wider than the artwork it covers,
// on purpose: the fabric pulls each rail inward when the thread tightens, so
// the digitizer pushes each rail OUT by the fabric's pull compensation
// before writing the file (`digitizer_core/stage6_satin._push_rails`, and
// `src/satin.js` for the lettering lane). Hotel Fremont's letters are
// 0.76 mm in the artwork and 1.23 mm in the file; the professional's own
// Wilcom file of the same logo is 1.40 at 92.5 mm. Rendered at the file's
// width plus the 0.4 mm thread, both look about twice as heavy as the
// artwork — and both sew at the artwork's weight, because the pull takes
// the compensation back. The preview could only show the file; Kent, who had
// only ever seen the pro's file on cloth, read ours as "waaaay thicker".
//
// This is a VIEW: it moves no stitch and changes nothing in the file. Each
// satin strand (a cross, or the lean leg to the next cross — both run rail
// to rail) loses the pull at each end along its own direction, which is the
// rail stepping back in by exactly what `_push_rails` gave it. Fill, run,
// underlay and travel strands are left alone: a tatami's pull shows as row
// shrinkage the preview does not model, and a run has no width to give up.
// A design without run spans (the lettering lane, a .dst, a pre-2026-09
// project) carries no satin kind, so the view is a no-op there and the
// toggle says so by staying disabled.
//
// The AMOUNT is the fabric's `pullCompMm` in force for the project's garment,
// profile applied — the same number the service used (`fabric_for` reads the
// same preset table), so what is taken back is what was put on. It is a
// model of the fabric, not a sew-out: whatever the cloth really does beyond
// its preset, this view is wrong by that much too.
import { EMB } from "./emb.js";
import { shrinkSatinStrands } from "./strands.js";
export { shrinkSatinStrands };

// The pull compensation in force for a project: its garment's fabric preset
// with the calibration profile applied, exactly as `generate.js`'s
// `fabricInForce` resolves it for the lettering lane and `fabrics.py`'s
// `fabric_for` resolves it service-side. 0 when there is no project or no
// garment (nothing was compensated, so nothing is taken back).
export function sewnPullFor(project) {
  if (!project || !project.garmentId) return 0;
  const preset = EMB.getFabric(EMB.fabricForGarment(project.garmentId));
  if (!preset) return 0;
  let fabric = preset;
  if (project.fabricProfile) {
    try { fabric = EMB.applyFabricProfile(preset, project.fabricProfile); } catch { fabric = preset; }
  }
  const pull = Number(fabric && fabric.pullCompMm);
  return pull > 0 ? pull : 0;
}

// Whether a design has anything this view can act on: at least one satin
// span. A design without spans renders as before, so the toggle is disabled
// rather than silently doing nothing.
export function hasSatinSpans(design) {
  return !!(design && Array.isArray(design.runs) && design.runs.some((r) => r && r.kind === "satin"));
}
