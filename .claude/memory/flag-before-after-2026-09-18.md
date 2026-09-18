---
name: flag-before-after-2026-09-18
description: 2026-09-18 — the "Flag Before After" artifact was a hand-made labelled copy of the reveal gallery whose generator never reached the repo; rebuilt as `--labelled`, re-rendered in the cloud with every arm, republished to the same URL. What was found, what to carry forward.
metadata:
  type: project
---

# Flag Before After — the labelled page, found and finished — 2026-09-18

Kent: *"the embot was working on a large export previewer to judge different
tools and compare the tool. it did not finish."* It was the Artifact
**Flag Before After** (`https://claude.ai/artifact/6mjKrbnCX21MM9gQUry4Zp`):
34 before | after pairs, six flags, nine logos, verdict controls on the
page. A local session had made it by hand from PR #507's reveal page
(`LABELLED MODE (scratch copy)` in its script), published it, and its
generator lived only in that session's scratchpad. Nothing on any branch
named it; `git fetch --all` found only PR #513 (the jump-run render fix),
pushed from the same session an hour earlier.

## What "finish" turned out to be

- **The generator is in the repo now** — `python -m tools.eye_pairs_gallery
  --labelled` (COOKBOOK "The labelled before | after page"). Same file as the
  reveal; one `DATA.labelled` switch in the page.
- **Every arm, not six.** The scratch copy had `per_stroke`,
  `patch_junctions`, `polygon_axis`, `area_weighted`, `design_angle` and
  `rails_follow_edge` — the last was never in `ARMS` or the spec's §3.2 table,
  so it is a row there now. The rebuild rendered all eleven flags plus
  `ref_0827` on the nine logos: __COUNTS__.
- **Republished to the SAME URL.** Its `db` was empty (no notes, no rulings),
  so nothing was at risk; ids changed from `P001…` to `<arm>__<fixture>` so
  the next republish never can be.

## What to carry forward

- **A null pick is not a loss.** The scratch copy's `DATA.arms` read
  `wins: 0, losses: 9` for every arm because `arm_tally` counted `pick ==
  null` as a loss. Harmless there (the page recomputed from verdicts) and
  wrong on paper; `labelled_arms` carries no wins/losses at all.
- **`#export{display:flex}` beat `[hidden]`** outside the artifact host, so
  the JSON export box was always visible in a static preview. The host's
  skeleton CSS hid it, which is why PR #507's browser check never saw it.
  `#export[hidden]{display:none}` now.
- **The cloud matches Kent's box to platform rounding** — fremont, drone,
  enthusiast, gaulke exact; becker 17,701 vs 17,700, bridge 14,607 vs
  14,608 (the known cross-platform numerics) — **except tires, and that
  difference is the cutout.** `tires` is `photo_scene` to stage 0 (a logo).
  Kent's page had it at 2,345 stitches; with `rembg_isolated/venv` present
  it digitizes to 2,287 (`PHOTO_BACKGROUND_REMOVED`), and with
  `photo_prep=False` to exactly 2,345 — the cutout-unavailable path is
  byte-identical to that, so **his scratch copy was rendered from a worktree
  with no rembg venv** (the venv is gitignored and lives only in the main
  checkout). The rebuild has the cutout, i.e. the product's shipped path.
  Build `rembg_isolated/venv` FIRST (pip + a 179 MB model download, both
  worked through the proxy), and never let it appear mid-lane, or the base
  arm and a later arm of the same fixture were prepped differently. Under
  four-lane contention tires takes ~80 s an arm against 33 s solo, fremont
  ~150 s.
- **Four lanes on four cores**: three `--render --out <lane> --fixtures …`
  lanes for the flag arms and one for `ref_0827` (its worktree path is
  fixed, so two ref lanes would collide), merged by unioning `features.json`
  and copying `renders/` + `designs/`. Launch them as separate background
  commands: a `VAR=… && (a) & (b) &` one-liner backgrounds only the first
  group with the variables set, and the rest run with `--out /lanes/…`.
- **The yardstick's renderer never had the jump-run bug.** `stitchviz.
  render_design` draws every `stitch` record and skips only the `jump`
  MOVE; PR #513 fixed `bare_patch_render.py` and `thread_color_render.py`,
  which the eye-pairs pages do not use. The scratch copy's renders were sound.
- **Kent's held `design_angle` ruling** is still only on the throwaway
  preview artifact (`6Rc8urLWN1fXc8oh7xVtPg`), by his choice; it was not
  copied to the labelled page and its text is not in the repo.
- **Labelled judging contaminates a blind sitting on the same pairs.** He
  chose the labelled page knowing that; COOKBOOK says what the choices are.

See [[eye-pairs-build-2026-09-17]] (the yardstick this page sits beside),
[[concurrent-session-designed-the-same-tool-2026-09-17]].
