<script>
  import { update, updateElement, updateElements, selectElement, toggleSelectElement, addElement, addSeededTextElement, removeElement, resolveArtworkType, deriveProjectName, UNTITLED_NAME } from "./lib/project.js";
  import { createHistory } from "./lib/history.js";
  import { applyTemplate } from "./lib/templates.js";
  import { onMount } from "svelte";
  import { isSewable } from "./lib/flow.js";
  import { designSummary } from "./lib/summary.js";
  import { sewSummary } from "./lib/estimate.js";
  import { generateAll } from "./lib/generate.js";
  import { rehydrateImages } from "./lib/imageSource.js";
  import { chartIdForProject, designChartId } from "./lib/designChart.js";
  import { flattenRGBA, WORK_MAX_PX, ALPHA_CUTOFF, sewnColorCount } from "./lib/flatten.js";
  import {
    migrateLegacy,
    currentProjectId,
    setCurrentProject,
    loadProject,
    saveProject,
    createProject,
    renameProject,
    deleteProject,
    duplicateProject,
    importProject,
    listProjects,
    isAutoNamed,
    autoNameProject,
  } from "./lib/projects.js";
  import { buildProjectFile, parseProjectFile, projectFileName } from "./lib/projectFile.js";
  import { collectSources, restoreSources } from "./lib/projectSources.js";
  import { triggerDownload } from "./lib/download.js";
  import { shouldShow, dismiss, visibleHint } from "./lib/hints.js";
  import { effectiveHoop } from "./lib/hoop.js";
  import { fetchHealth, spoolCount } from "./lib/digitizer.js";
  import { EMB } from "./lib/emb.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import ContentStep from "./ui/ContentStep.svelte";
  import Configurator from "./ui/Configurator.svelte";
  import DownloadSheet from "./ui/DownloadSheet.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import ProjectsDrawer from "./ui/ProjectsDrawer.svelte";
  import FontCredits from "./ui/FontCredits.svelte";
  import Icon from "./ui/Icon.svelte";
  import "./ui/theme.css";

  // The image itself never survives a reload (see `runtime` below), so a
  // persisted `_hasImage` flag on any element would let the flow gate pass
  // with nothing actually loaded — strip it from every element at boot AND
  // on every project switch (openProject/newDesign/deleteFromDrawer all
  // route through enterProject(), which calls this too).
  function resetHasImage(p) {
    if (!p.elements.some((el) => el._hasImage)) return p;
    return { ...p, elements: p.elements.map((el) => (el._hasImage ? { ...el, _hasImage: false } : el)) };
  }

  // Looks up a registry entry's display name from the current `projects`
  // snapshot; falls back if it's somehow missing (shouldn't happen, but
  // keeps the topbar from ever showing a blank name).
  function nameFor(id) {
    const entry = projects.find((p) => p.id === id);
    return entry ? entry.name : UNTITLED_NAME;
  }

  // ---- Boot (Slice 7 Task 2) ------------------------------------------------
  // migrateLegacy() first (one-time, no-op after the first successful run or
  // if there was never a legacy blob), then load whatever the registry says
  // is current. If there's no current project (first run) or its record is
  // missing/corrupt, loadProject returns null and we fall back to a brand
  // new project.
  migrateLegacy();
  let projects = listProjects();
  let currentId = currentProjectId();
  // currentId must also be present in the index -- a stale/orphaned pointer
  // (e.g. left over from a partial createProject/duplicateProject failure,
  // or a record that's since been deleted) is otherwise indistinguishable
  // from a real id, and loadProject() would happily return whatever record
  // happens to still sit under that key. Requiring it to also appear in
  // `projects` means an orphaned pointer routes through the same
  // createProject() fallback below as "no current project at all", which
  // sets a fresh, index-backed CURRENT_KEY instead of leaving auto-save
  // pointed at an id the registry doesn't know about.
  let bootProject = currentId && projects.some((p) => p.id === currentId) ? loadProject(currentId) : null;
  if (!bootProject) {
    const created = createProject(UNTITLED_NAME);
    currentId = created.id;
    bootProject = created.project;
    projects = listProjects();
  }

  let project = resetHasImage(bootProject);
  let projectName = nameFor(currentId);
  // The Download sheet (spec §2.4). The only browser-history entry the
  // Studio pushes: opening pushes one, so the phone's Back gesture closes
  // the sheet instead of leaving the app; closing pops it. No URL changes.
  //
  // `window.history` explicitly, never bare `history`: the undo history
  // below is `const history = createHistory(project)`, which shadows the
  // browser's inside this component.
  let sheetOpen = false;
  const SHEET_STATE = { embSheet: "download" };
  function isSheetEntry() {
    const s = window.history.state;
    return !!(s && s.embSheet === "download");
  }
  function openSheet() {
    if (sheetOpen) return;
    sheetOpen = true;
    window.history.pushState(SHEET_STATE, "");
    checkDigitizer();
  }
  function closeSheet() {
    if (!sheetOpen) return;
    if (isSheetEntry()) window.history.back();
    else sheetOpen = false;
  }
  function onPopState() {
    const wasOpen = sheetOpen;
    sheetOpen = isSheetEntry();
    // Forward can re-open the sheet; re-probe as openSheet does, so its
    // service-only controls (JEF) are not judged on a stale answer.
    if (sheetOpen && !wasOpen) checkDigitizer();
  }
  // A reload with the sheet open boots with sheetOpen false while the
  // browser still sits on the sheet's entry. Left there, the next Download
  // pushes a SECOND entry: Close then takes two presses and Back is a dead
  // one. Normalise it away on mount.
  onMount(() => {
    if (isSheetEntry()) window.history.replaceState(null, "");
  });
  // Boot builds `project` directly rather than through enterProject(), so
  // the open-a-legacy-project case above needs its twin here.
  applyAutoName();

  // The step panel scrolls, and its scroll offset used to survive a step
  // change — which lands on the path EVERY user takes, because the fabric
  // picker sits below the fold. Measured on the shipped build at 1440x900:
  // the garment step is 1320px of content in a 741px viewport with "Fabric
  // color" 529px down, so choosing a fabric requires scrolling; pressing
  // Next then opened the content step already 493px down, with "what do you
  // want to say?" off-screen above and no visible way forward.
  //
  // Reset on the project too, not just the step: switching projects replaces
  // the panel's content just as completely, and leaving that scrolled is the
  // same defect wearing a different hat.
  //
  // Set synchronously, and deliberately NOT via tick()/afterUpdate: calling
  // tick() from inside a reactive statement re-enters Svelte's flush from
  // within the flush and spins the main thread — the app booted to a blank
  // page that never fired `load`, which is how it was caught (every
  // wizard-smoke e2e failed at page.goto, not on any assertion).
  //
  // Waiting for the DOM would buy nothing anyway: 0 is in range for ANY
  // content height, so unlike a non-zero offset it can never be clamped by
  // the outgoing step's shorter content.
  //
  // The wizard's steps are gone (2026-09-30, the configurator): the panel is
  // one scroll now, so only the project switch still resets it.
  let panelBody = null;
  $: if (panelBody) { currentId; panelBody.scrollTop = 0; }

  // Every digitized element that has been through the service, for the review
  // step's quality report. Deliberately NOT scoped to the selected element the
  // way the summary above it is: the report answers "should I sew this file",
  // and the file is the whole project — a clean logo does not stop mattering
  // because a text element happens to be selected.
  //
  // Text, shape and hand-drawn elements are absent on purpose, not by
  // oversight: preflight runs in the Python digitizer, so nothing generated in
  // the browser has a QUALITY judgement to show, and that belongs to the
  // engine rather than to this component. What the browser CAN state about
  // them — how big, how many stitches, how many stops, how much thread — it
  // now does: `sewFacts` below, rendered only when this list is empty, so one
  // design never gets two answers.
  $: qualityEntries = (project.elements || [])
    .filter((el) => el.type === "digitized" && (el.preflight || el.stats))
    .map((el) => ({
      id: el.id,
      label: el.name || "Artwork",
      preflight: el.preflight,
      stats: el.stats,
    }));

  // Does the quality report above cover the WHOLE design, or only part of it?
  //
  // This is the question `!qualityEntries.length` was standing in for, and it
  // is not the same question. Measured in the shipped app 2026-09-08 on the
  // commonest thing a customer combines — a name and a logo:
  //
  //   canvas caption ....... 3,219 stitches   (966 lettering + 2,253 artwork)
  //   review summary ....... 2,253 stitches   the artwork alone
  //
  // One digitized element was enough to suppress `sewFacts`, so the screen
  // headed "Ready to stitch" understated the design by 30% — and QualityReport
  // hides its per-entry label at exactly one entry, so nothing said the number
  // was about a part. The comment below promised "one design never gets two
  // answers"; what a mixed design got was one answer to a different question.
  //
  // Whole-design totals are suppressed only when a single quality entry IS the
  // design, which is the case that comment was written for.
  //
  // "every sewable element is digitized" was the first version of this and it
  // still had a residual, found by driving TWO logos into one design
  // (2026-09-08): each entry reported 2,187 stitches, the design was 4,374,
  // and no number on the recap was the design's. Neither entry is wrong there
  // — but neither is the answer either, and the customer is left adding them
  // up from two panels. One entry covering everything is the only case where
  // showing the totals as well would really be two answers to one question.
  $: qualityIsTheWholeDesign = (() => {
    const sewable = (project.elements || []).filter(isSewable);
    return sewable.length === 1 && sewable[0].type === "digitized";
  })();

  // What the COMBINED design costs to sew —
  // the numbers `qualityEntries` above cannot supply for a browser-built
  // design. Derived here rather than in the template so it recomputes with
  // project/runtime like every other `$:` and never runs inside a render loop.
  // Never throws: it runs on every change, including while nothing is ready to
  // stitch. Feeds both the summary bar and the Download sheet's recap.
  $: combinedDesign = (() => {
    try {
      return generateAll(project, runtime).combined || null;
    } catch (e) {
      return null;
    }
  })();
  $: sewFacts = combinedDesign ? sewSummary(combinedDesign) : [];
  // The summary bar's colour figure: SPOOLS, the customer-facing meaning of
  // "colors" here (see spoolCount in lib/digitizer.js), counted on the same
  // combined design the size and stitch figures beside it come from.
  $: colorCount = combinedDesign && sewFacts.length ? spoolCount(combinedDesign) : 0;

  // The rows the Download sheet recaps — one list, built here, so the
  // sheet is a renderer and never re-derives what the app already knows.
  $: summaryRows = [
    { label: "Garment", value: readable(project.garmentId) },
    { label: "Hoop", value: hoopInEffect.hoop.label + (hoopInEffect.suggested ? " (suggested)" : "") },
    ...designSummary(project, sewnColors),
    ...(qualityIsTheWholeDesign ? [] : sewFacts),
  ];
  $: subtitle = `${readable(project.garmentId)} · ${hoopInEffect.hoop.label}`;

  // ---- Undo/redo (Ember-audit follow-up) ------------------------------------
  // Per-project, in-memory only (never persisted). Every committed project
  // change routes through persist() below, which records a snapshot; pure
  // selection changes opt out (persist(false)) so undo never burns steps on
  // clicks. Drag storms coalesce inside history.js (500ms window).
  const history = createHistory(project);
  let canUndo = false;
  let canRedo = false;
  function syncHistoryFlags() {
    canUndo = history.canUndo();
    canRedo = history.canRedo();
  }

  // A restored snapshot's _hasImage flags may reference runtime image state
  // that no longer exists (removing an image element also drops its
  // runtime.flats entry — see onRemoveElement — and undo can't bring the
  // pixels back). Re-truth the flag against what runtime actually holds so
  // the flow gate can't pass on an image that isn't really loaded.
  function truthHasImage(p) {
    if (!p.elements.some((el) => el._hasImage && !runtime.flats[el.id])) return p;
    return {
      ...p,
      elements: p.elements.map((el) =>
        el._hasImage && !runtime.flats[el.id] ? { ...el, _hasImage: false } : el
      ),
    };
  }

  function applyHistorySnapshot(p) {
    if (!p) return;
    project = truthHasImage(p);
    // persist(false) rather than a bare saveProject: `false` skips the
    // history record (an undo must not push a new step), and everything
    // else in persist's tail applies to an undo exactly as it does to an
    // edit -- the storage-failure banner, and the auto-name.
    //
    // The auto-name half was a real defect, measured 2026-09-07 the same
    // day auto-naming shipped: type HELLO, type GOODBYE, undo -- the
    // design read HELLO and the topbar, the drawer and the stored index
    // all still read GOODBYE. An undo is an edit as far as every surface
    // downstream of it is concerned, and this function was the one path
    // that changed `project` without going through persist().
    persist(false);
    syncHistoryFlags();
  }

  function undoEdit() {
    applyHistorySnapshot(history.undo());
  }

  function redoEdit() {
    applyHistorySnapshot(history.redo());
  }

  // Ctrl/Cmd+Z and Ctrl+Y / Ctrl/Cmd+Shift+Z — skipped while a text control
  // has focus so the browser's native input-level undo stays intact.
  function onGlobalKey(e) {
    if (!(e.ctrlKey || e.metaKey)) return;
    const t = e.target;
    const tag = t && t.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
    const k = e.key.toLowerCase();
    if (k === "z" && !e.shiftKey) {
      e.preventDefault();
      undoEdit();
    } else if (k === "y" || (k === "z" && e.shiftKey)) {
      e.preventDefault();
      redoEdit();
    }
  }
  let drawerOpen = false;
  // .embproj import outcome line, shown inside the drawer. Reset on every
  // open/close so a stale error never greets the next visit.
  let drawerNotice = "";
  $: if (!drawerOpen) drawerNotice = "";
  // ---- Drawer focus restore (A11Y/UX finding 5) -----------------------------
  // ProjectsDrawer moves focus INTO itself on mount and traps Tab while
  // open (see its own comments), but restoring focus back to whatever
  // opened it is App's job, since App is what destroys the drawer (the
  // {#if drawerOpen} block) in the first place. myDesignsBtn is bound to
  // the "My designs" button below; drawerWasOpen lets the reactive block
  // fire exactly once per open->close transition (not on initial mount,
  // when drawerOpen starts false and there's nothing to restore focus
  // from) regardless of which of the several code paths (openProject,
  // newDesign, the drawer's own "close" event, or the toggle button click
  // itself) flipped drawerOpen back to false.
  let myDesignsBtn;
  let drawerWasOpen = false;
  $: if (drawerOpen) {
    drawerWasOpen = true;
  } else if (drawerWasOpen) {
    drawerWasOpen = false;
    if (myDesignsBtn) myDesignsBtn.focus();
  }

  // ---- Font credits dialog (Slice 10B Task 5) -------------------------------
  // Same focus-restore contract as the drawer above: FontCredits moves focus
  // INTO itself on mount and traps Tab while open, but restoring focus to
  // whichever control opened it is App's job. Two openers exist -- the
  // topbar "Font credits" button and DownloadStep's footer link -- so
  // creditsOpener tracks whichever one was actually clicked instead of
  // assuming it was always the topbar button.
  let creditsOpen = false;
  let creditsBtn;
  let creditsWasOpen = false;
  let creditsOpener = null;
  $: if (creditsOpen) {
    creditsWasOpen = true;
  } else if (creditsWasOpen) {
    creditsWasOpen = false;
    if (creditsOpener?.isConnected) creditsOpener.focus();
    else creditsBtn?.focus();
    creditsOpener = null;
  }
  function openCredits(opener) {
    creditsOpener = opener || null;
    creditsOpen = true;
  }
  // Runtime image state, owned here (not by ImagePanel) so it survives
  // ContentStep/ImagePanel being destroyed and recreated whenever the user
  // navigates steps or toggles Text/Image mode (both are {#if} blocks).
  // Keyed by element id (Task 4/Slice 5: was a single workImage/flat pair,
  // now a map so each image element in a multi-element project keeps its
  // own working image) -- see generate.js's generateAll(project, runtime).
  // workImages[id] is the prepped working source ({ rgba, w, h }, alpha-cut,
  // at WORK_MAX_PX) that ImagePanel re-flattens from; flats[id] is the
  // flattened palette derived from it. Neither is persisted -- only project
  // settings are (see persist() below).
  let runtime = { flats: {}, workImages: {} };

  // How many colours each image element will actually SEW, for the review
  // recap. `element.nColors` is the slider — a ceiling the customer asked for —
  // and median-cut returns only as many entries as the art needs, so the card
  // used to claim four colours beside a `Thread changes` row counted from the
  // design's own records saying two. `runtime` is reassigned wholesale by
  // onFlat, so this recomputes on every flatten.
  $: sewnColors = Object.fromEntries(
    Object.entries(runtime.flats).map(([id, flat]) => [id, sewnColorCount(flat)]),
  );

  // ---- Digitizer service health (build step 10) -----------------------------
  // Whether the localhost auto-digitize service is reachable gates the
  // "+ Auto-digitize" tile (and turns DigitizePanel's controls off with an
  // explanation instead of a dead button). The token guard drops a stale
  // slow probe that resolves after a newer one already answered.
  let digitizerHealth = null;
  let digitizerProbeToken = 0;
  async function checkDigitizer() {
    const token = ++digitizerProbeToken;
    const h = await fetchHealth();
    if (token === digitizerProbeToken) digitizerHealth = h;
  }
  // Probed once on mount; the Download sheet re-probes on open (openSheet),
  // since it has a control only the service can serve (JEF), and the UI's
  // "check again" affordances probe on demand.
  onMount(checkDigitizer);
  // Dims of the SELECTED element's last generated design ({ widthMM, heightMM })
  // or null on failure/no-content -- fed to SizePanel so its W/H display
  // (and the below-5mm warning) always reflects the real current design,
  // including while the user drags the field's resize handles.
  let designDims = null;

  // A shape selected ON THE FIELD (EmbroideryField's click-to-edit popover,
  // 2026-09-29): { elementId, shapeId, n }. Runtime only — never saved.
  // `n` counts field selections so the same shape picked twice still reaches
  // ManualPanel as a new request.
  let fieldShapeSelect = null;

  // The hoop in effect (manual pick or per-garment suggestion, lib/hoop.js)
  // — shown in the "Ready to stitch" summary so the review step names the
  // physical hoop the operator will actually mount.
  $: hoopInEffect = effectiveHoop(project);

  // The chart the engine snapped this design's cones out of, published
  // for every ThreadPicker in the app (nine call sites across seven
  // components — a prop threaded through all of them would be the wrong
  // shape for a fact that belongs to the project). See lib/designChart.js.
  $: designChartId.set(chartIdForProject(project));

  // Does this project contain anything a machine could sew?
  //
  // flow.js's `isSewable` is the existing answer — one predicate per element
  // type, already specced. A brand-new project holds one EMPTY text element,
  // and until 2026-09-07 the review screen called that "Ready to stitch".
  // Reusing the predicate rather than writing a second rule is the point: a
  // new element type that flow.js calls sewable is sewable here too, with no
  // second list to forget. It gates the summary bar's Download.
  $: readyToStitch = project.elements.some(isSewable);

  const MM_PER_INCH = 25.4;

  // ---- Onboarding hints (Slice 7 Task 3) ------------------------------------
  //
  // Each hint has its own "still shown" boolean, seeded once at boot from
  // hints.js's shouldShow() (storage-backed, defaults to true) and flipped
  // locally the instant it's dismissed -- see dismissHint(), the single path
  // that also persists the dismissal via hints.js's dismiss(). App.svelte is
  // only ever instantiated once (main.js), so this top-level `let` runs
  // exactly once per page load, which is the right lifetime for "seen this
  // session/before".
  //
  // At most one hint renders at a time (plan amendment A7): `eligibleHints`
  // collects whichever of the two are BOTH still-shown AND contextually
  // eligible right now --
  //   drag-field   ⇔ the combined design has stitches (hasStitches, from
  //                  EmbroideryField's "stats" event -- A8)
  //   add-elements ⇔ fewer than 2 elements
  // -- and hands that list to hints.js's visibleHint(), which picks the
  // single highest-priority one (drag-field > add-elements). The templates
  // hint went with the garment step (2026-09-30): templates live in
  // My designs now.
  let addElementsShown = shouldShow("add-elements");
  let dragFieldShown = shouldShow("drag-field");
  let hasStitches = false;

  function dismissHint(key) {
    dismiss(key);
    if (key === "add-elements") addElementsShown = false;
    else if (key === "drag-field") dragFieldShown = false;
  }

  // EmbroideryField's "stats" event -- reports the COMBINED design's stitch
  // count after every generate attempt (0 on error/no-content).
  function onStats(detail) {
    hasStitches = !!(detail && detail.stitchCount > 0);
  }

  $: eligibleHints = [
    dragFieldShown && hasStitches ? "drag-field" : null,
    addElementsShown && project.elements.length < 2 ? "add-elements" : null,
  ].filter(Boolean);
  $: visibleHintKey = visibleHint(eligibleHints);
  $: showAddElementsHint = visibleHintKey === "add-elements";
  $: showDragFieldHint = visibleHintKey === "drag-field";

  // Permanent auto-dismiss (same effect as clicking ✕): once a second
  // element exists, the user has already discovered +Text/+Image, so this
  // never shows again even if they later remove elements back down to one.
  // Guarded on addElementsShown so it only ever fires the one time it
  // transitions true -> false.
  $: if (addElementsShown && project.elements.length >= 2) dismissHint("add-elements");

  // Single write path to the registry (Slice 7 Task 2) — replaces every old
  // saveLocal(project) call site. saveProject is a safe no-op if currentId
  // has since been deleted out from under an in-flight edit (see the A2/A10
  // no-op contract in projects.js), and bumps the registry's updatedAt, so
  // every persist also refreshes the `projects` snapshot (see instruction 3
  // in the task brief: refresh after every registry mutation).
  // ---- "your changes aren't being saved" ------------------------------
  //
  // `saveProject` has always returned false when the write fails, and this
  // function has always ignored it. Everything in EMB-Bot lives in
  // localStorage, so a failed write is silent data loss and the customer is
  // the last to know.
  //
  // Measured in the shipped app 2026-09-07, with the origin's store filled to
  // the byte (its real quota here is 5,241,856 characters — the app's own
  // reading of it, not a 5 MB rule of thumb):
  //
  //   * upload a logo -> it digitizes, the panel reads "2,253 stitches ·
  //     81x16 mm · 2 colors", the canvas caption reads 3,818 stitches;
  //   * the stored record is 842 characters, the element saved WITHOUT its
  //     baked result;
  //   * reload -> back on the quick-start screen, caption 1,565 stitches.
  //     The logo is gone. Nothing was said at any point.
  //
  // One digitized project measures ~186,600 characters, so the store holds
  // about 28 of them. This is a browser-storage app with no server; a working
  // customer reaches that.
  //
  // The banner names controls that exist on this screen: My designs holds
  // both the export and the delete.
  let saveFailed = false;

  function persist(record = true) {
    if (record) {
      history.record(project);
      syncHistoryFlags();
    }
    const ok = saveProject(currentId, project);
    refreshProjects();
    // saveProject ALSO returns false for an id that is no longer in the
    // registry — the A2/A10 no-op contract, e.g. a project deleted out from
    // under an in-flight edit. That is not a storage problem and must not
    // raise this. `refreshProjects()` above makes `projects` current.
    saveFailed = !ok && projects.some((p) => p.id === currentId);
    applyAutoName();
  }

  // A registry write that reported failure, routed to the same banner
  // persist() raises. Renames and deletes live ONLY in the index, so unlike
  // a design edit there is no saved copy to fall back on -- a rename that
  // silently didn't stick is gone at the next reload with the customer
  // still looking at the new name.
  //
  // Same A2/A10 distinction persist() makes: a false return for an id the
  // registry no longer holds is the deliberate no-op contract, not a full
  // disk, and must not raise a storage banner.
  function noteWriteFailed(ok, id) {
    if (!ok && projects.some((p) => p.id === id)) saveFailed = true;
  }

  function refreshProjects() {
    projects = listProjects();
  }

  function apply(patch) {
    project = update(project, patch);
    persist();
  }

  // Patches a single element (by id) — used by EmbroideryField's drag/resize/
  // reclamp "elupdate" events and by ContentStep's element-scoped TextStep/
  // ImagePanel/SizePanel controls (see ContentStep.svelte), which all funnel
  // their patches through this same { id, patch } shape.
  function elUpdate(id, patch, record = true) {
    project = updateElement(project, id, patch);
    persist(record);
  }

  // Multi-select group edits (EmbroideryField's group move/resize and
  // ContentStep's bulk-edit panel): one patch per member, applied in a
  // single immutable pass so undo records ONE step for the whole gesture.
  function elUpdateMany(patchById, record = true) {
    project = updateElements(project, patchById);
    persist(record);
  }

  function onToggleSelect(id) {
    project = toggleSelectElement(project, id);
    persist(false); // pure selection, same no-undo-step rule as onSelect
  }

  // Hoop width in mm for the current garment — new elements are seeded with
  // a size relative to it (see project.js's addElement). Falls back to a
  // sane default if the garment can't be resolved (a project always carries
  // a garmentId, so this is a guard, not a path).
  function hoopWidthMm(p) {
    const garment = p && EMB.getGarment(p.garmentId);
    return garment ? garment.widthIn * MM_PER_INCH : 300;
  }

  // "artwork" is the Content step's ONE upload tile (Kent's call, 2026-08-13:
  // "automatically recognize if it's working with a photo or a logo, and
  // remove all of the unnecessary upload buttons"). It is not an element type
  // — it is the routing decision that used to be the user's, made from the
  // one fact that actually determines it: whether the digitizer is running.
  //
  // With the service up, uploaded art becomes a `digitized` element and the
  // pipeline classifies and stitches it. With the service down there is no
  // pipeline to classify anything, so it becomes an `image` — the browser
  // engine's own flatten-and-sew lane, which needs no service. Same tile,
  // same upload, no question asked of the user either way.
  function onAddElement(type) {
    const resolved = type === "artwork"
      ? resolveArtworkType(digitizerHealth)
      : type;
    project = addElement(project, resolved, hoopWidthMm(project));
    // addElement selects the new element, and its editor is always on
    // screen now — the configurator panel shows the Design section at all
    // times — so the field's right-click menu can no longer create an
    // element nobody can see (the orphan the old step jump here fixed).
    persist();
  }

  // "Convert cluster to text" (text-cluster-detection feature; the badge/
  // action UI itself is Step 6b, built on top of this — DigitizePanel
  // doesn't dispatch "converttotext" yet, only ContentStep's bubbling is
  // wired below). detail: { seed, clusterId, sourceElementId,
  // memberShapeIds }. This is genuinely new coordination, not a reuse of
  // elUpdateMany: elUpdateMany patches multiple EXISTING elements, each with
  // its own caller-supplied patch; this instead creates a brand-new element
  // (via addSeededTextElement) AND, in the same step, patches a DIFFERENT,
  // already-existing element (the digitized source) with data the new
  // element doesn't carry -- so it can't be expressed as a single
  // patchById map the way elUpdateMany's callers already build one.
  //
  // The source element's shapeOverrides get `stitched: false` for every
  // member shape id (hides the original traced shapes -- same override key
  // the enclosed-background restore feature already uses, just the opposite
  // direction), merged the same way DigitizePanel's own setOverride merges
  // a single shape's overrides (that helper lives on DigitizePanel's
  // `element` prop, not on `project`, so it isn't reachable from here --
  // this inlines the same merge shape rather than duplicating a helper this
  // file has no other use for). `textConversions` (Record<clusterId,
  // textElementId>) records the provenance Step 6b's undo action will read
  // back; per the design doc it is pure Studio-side state, never sent to
  // the server.
  function onConvertClusterToText(detail) {
    const { seed, clusterId, sourceElementId, memberShapeIds } = detail || {};
    const { project: withText, id: newElementId } = addSeededTextElement(
      project,
      seed,
      hoopWidthMm(project)
    );

    const source = withText.elements.find((el) => el.id === sourceElementId);
    if (!source) {
      // Source element vanished from under us (shouldn't happen -- this
      // action only exists while its owning DigitizePanel row is on
      // screen). Still land the new text element; just skip the
      // now-meaningless source-side patch.
      project = withText;
      persist();
      return;
    }

    const shapeOverrides = { ...(source.shapeOverrides || {}) };
    for (const sid of memberShapeIds || []) {
      shapeOverrides[sid] = { ...(shapeOverrides[sid] || {}), stitched: false };
    }
    const textConversions = { ...(source.textConversions || {}), [clusterId]: newElementId };

    project = updateElement(withText, sourceElementId, { shapeOverrides, textConversions });
    persist();
  }

  function onRemoveElement(id) {
    project = removeElement(project, id);
    // Element ids can be reused (nextElementId in project.js picks the next
    // number after whatever's left once the removed one is gone), so a
    // stale runtime.flats/workImages entry for this id must be dropped now
    // — otherwise a LATER element that happens to land on the same id could
    // silently inherit this removed element's flattened art / working image.
    if (id in runtime.flats || id in runtime.workImages) {
      const flats = { ...runtime.flats };
      const workImages = { ...runtime.workImages };
      delete flats[id];
      delete workImages[id];
      runtime = { flats, workImages };
    }
    persist();
  }

  function pickTemplate(template) {
    project = applyTemplate(project, template, digitizerHealth);
    // Clear the per-element runtime, exactly as enterProject does.
    //
    // applyTemplate REPLACES the design ("start from template" semantics) with
    // fresh elements, and every template's patch hard-codes the id "e1" -- so
    // without this the new element inherits the PREVIOUS design's flattened
    // artwork, which is keyed by element id. Pick "Logo patch", upload a logo,
    // go Back and pick a template again: the fresh e1 reports _hasImage false
    // and the user has uploaded nothing, but runtime.flats.e1 still holds the
    // old logo. enterProject (the other whole-project-replacement path) has
    // always cleared this; pickTemplate was its unfixed sibling. Found by a
    // sibling-pattern sweep 2026-08-26.
    //
    // designDims is deliberately NOT reset here: it is re-dispatched on the
    // next generate, and unlike runtime it is not keyed by element id, so a
    // stale value cannot attach itself to the wrong element.
    runtime = { flats: {}, workImages: {} };
    persist();
    // Templates are picked from My designs (2026-09-30); close it so the
    // customer lands on the design they just started.
    drawerOpen = false;
  }

  // The shape the Layers list and the canvas are both pointing at
  // (2026-09-30). Two surfaces, one state: a row's hover or click lands
  // here and goes to the field as `hoverShape` / `focusShape`; a canvas
  // hover or click lands here and goes to the panel as the ids it should
  // highlight. Each is { elId, shapeId } or null, and the panel only ever
  // sees the pair for the element it is showing.
  let hoverShape = null;
  let selectedShape = null;
  $: panelHoverShapeId = hoverShape && hoverShape.elId === project.selectedId ? hoverShape.shapeId : null;
  $: panelSelectedShapeId = selectedShape && selectedShape.elId === project.selectedId ? selectedShape.shapeId : null;
  function onPanelShapeHover(shapeId) {
    hoverShape = shapeId ? { elId: project.selectedId, shapeId } : null;
  }
  function onPanelShapeSelect(shapeId) {
    selectedShape = { elId: project.selectedId, shapeId };
  }

  function onSelect(id) {
    project = selectElement(project, id);
    // record=false: pure selection isn't an edit — undo should never spend a
    // step un-clicking (the restored snapshots still carry whatever
    // selectedId they had when a real edit recorded them).
    persist(false);
  }

  function onImage(elementId, workImage) {
    runtime = { ...runtime, workImages: { ...runtime.workImages, [elementId]: workImage } };
  }

  // `record` is false when this is a RESTORE rather than an edit — see
  // restoreArtwork. Rehydrating a saved project's artwork must not become an
  // undo step: the user did nothing to undo, and undoing it returned
  // `_hasImage` to false while `runtime.flats` still held the flat, so the
  // design stayed on screen while the review step called it empty and Next
  // went disabled. Measured 2026-09-07 — 1473 stitches visible under
  // "Nothing to stitch yet".
  function onFlat(elementId, flat, record = true) {
    runtime = { ...runtime, flats: { ...runtime.flats, [elementId]: flat } };
    elUpdate(elementId, { _hasImage: !!flat }, record);
  }

  // ---- bringing a saved project's artwork back ------------------------------
  //
  // `enterProject` and boot both clear `runtime` and strip `_hasImage`,
  // which is correct — at that instant no pixels are loaded. The artwork
  // itself lives on the element as `sourcePng`, and this is what turns it
  // back into runtime state. Until 2026-09-07 nothing did: an `image`
  // element (the type an upload makes when the digitizer service is DOWN)
  // came back from a reload with no pixels at all, no stitches, and no
  // message. Measured in a browser: 2739 stitches before a refresh, none
  // after.
  //
  // The token guards a switch that overtakes an in-flight decode — the same
  // shape as `digitizerProbeToken` above, and for the same reason.
  let rehydrateToken = 0;

  async function decodeWorkImage(b64) {
    const img = await new Promise((resolve, reject) => {
      const im = new Image();
      im.onload = () => resolve(im);
      im.onerror = () => reject(new Error("saved artwork could not be decoded"));
      im.src = "data:image/png;base64," + b64;
    });
    const scale = Math.min(1, WORK_MAX_PX / (Math.max(img.width, img.height) || 1));
    const w = Math.max(1, Math.round(img.width * scale));
    const h = Math.max(1, Math.round(img.height * scale));
    const cv = document.createElement("canvas");
    cv.width = w;
    cv.height = h;
    cv.getContext("2d").drawImage(img, 0, 0, w, h);
    const rgba = cv.getContext("2d").getImageData(0, 0, w, h).data;
    // Same alpha cut ImagePanel's prepRGBA applies, so a rehydrated working
    // image is the one the flatten was built for rather than a near-miss.
    for (let i = 3; i < rgba.length; i += 4) if (rgba[i] < ALPHA_CUTOFF) rgba[i] = 0;
    return { rgba, w, h };
  }

  function restoreArtwork(proj) {
    const mine = ++rehydrateToken;
    rehydrateImages(proj, runtime, {
      decode: decodeWorkImage,
      flatten: (img, nColors, removeBg) =>
        flattenRGBA(img.rgba, img.w, img.h, { nColors, removeBg }),
      onImage,
      onFlat: (id, flat) => onFlat(id, flat, false),   // a restore, not an edit
      // A record that will not decode is dropped, not retried: the field is
      // on every step, so a decode failing on every reactive pass would spin
      // forever. Clearing the name too leaves the panel in its honest "no
      // artwork" state rather than showing a filename with nothing behind
      // it — which is exactly the mismatch this whole change removes.
      onError: (id) => elUpdate(id, { sourcePng: null, name: "" }, false),
      token: () => mine === rehydrateToken,
    });
  }

  // Boot does NOT go through enterProject — it assigns `project` directly,
  // near the top — so the artwork of whatever was loaded from storage is
  // restored here. Both entry points now call the same thing; there is no
  // third.
  //
  // Placed BELOW `restoreArtwork` rather than beside the `project`
  // assignment on purpose: Svelte hoists the function declaration but not
  // the `let rehydrateToken` it closes over, so calling it any earlier
  // throws "Cannot access 'rehydrateToken' before initialization" and the
  // whole app renders an empty body. (Done exactly that, 2026-09-07.)
  restoreArtwork(project);

  function onDims(detail) {
    designDims = detail;
  }

  function readable(id) {
    return (id || "")
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }

  // ---- Project switching (Slice 7 Task 2) -----------------------------------
  //
  // Every path that moves the app to a different project (or a brand-new
  // one) routes through this: it resets the in-memory `project` (stripped of
  // any stale _hasImage flags), clears the per-element runtime image maps
  // and stale designDims (none of that survives a switch — see `runtime`'s
  // own comment above), and updates currentId/projectName together so
  // there's never a moment where one is stale relative to the other.
  function enterProject(id, proj, name) {
    project = resetHasImage(proj);
    runtime = { flats: {}, workImages: {} };
    designDims = null;
    currentId = id;
    projectName = name;
    history.reset(project); // history is per-project; a switch starts fresh
    syncHistoryFlags();
    restoreArtwork(project);
    // Catch the name up on OPEN, not only on the next edit. Every project
    // already in a customer's browser predates auto-naming and is called
    // "Untitled design"; without this they would each keep that name until
    // something was typed into them, which is the population the drawer's
    // identical rows hurt most. A no-op for a design the customer has
    // named, and for a blank one there is nothing to derive from.
    applyAutoName();
  }

  // Drawer "Open". Opening the CURRENTLY-open project just closes the drawer.
  function openProject(id) {
    if (id === currentId) {
      drawerOpen = false;
      return;
    }
    const loaded = loadProject(id);
    if (!loaded) {
      // Shouldn't happen (the drawer only ever offers ids from `projects`),
      // but if the record's gone, don't leave the drawer open on a dead row.
      drawerOpen = false;
      return;
    }
    setCurrentProject(id);
    enterProject(id, loaded, nameFor(id));
    drawerOpen = false;
  }

  // Drawer "+ New design": a genuinely blank project.
  function newDesign() {
    const created = createProject(UNTITLED_NAME);
    enterProject(created.id, created.project, UNTITLED_NAME);
    drawerOpen = false;
    refreshProjects();
  }

  // Keeps the still-unnamed design's name tracking what is actually in it,
  // so "My designs" lists rows a customer can tell apart and a backup
  // downloads under a filename that says what it is. See
  // deriveProjectName() in lib/project.js for the measured defect and
  // isAutoNamed() in lib/projects.js for when this is allowed to fire.
  //
  // A no-op the moment the customer names the design by hand, and a no-op
  // when the guess has not moved -- so the common case of a keystroke that
  // does not change the first line costs one array scan and no write.
  //
  // Falls back to the placeholder rather than holding the last guess: the
  // name is a function of the content, and a design whose text has been
  // deleted is once again a design with nothing to go on.
  function applyAutoName() {
    const entry = projects.find((p) => p.id === currentId);
    if (!isAutoNamed(entry)) return;
    const derived = deriveProjectName(project) || UNTITLED_NAME;
    if (derived === entry.name) return;
    if (!autoNameProject(currentId, derived)) return;
    projectName = derived;
    refreshProjects();
  }

  // Takes the INPUT ELEMENT, not its value, because committing a name has
  // to be able to correct the field it came from.
  //
  // `value={projectName}` is a one-way binding, and Svelte only touches the
  // DOM when the EXPRESSION changes. A name that normalises back to the
  // stored one therefore leaves the typed text sitting in the field for
  // good. Measured in the shipped app 2026-09-07: with the design called
  // "Untitled design", clearing the name field and tabbing away left the
  // topbar showing an empty name while the drawer one panel over showed
  // "Untitled design" and the export still wrote untitled-design.embproj --
  // two places disagreeing about one design's name, with the blank one
  // being the one the customer is looking at. Typing only spaces did the
  // same. This is the same defect the size field had (see SizePanel's
  // resyncIfClamped), at a second site.
  function renameCurrent(target) {
    const finalName = (target.value || "").trim() || UNTITLED_NAME;
    projectName = finalName;
    const ok = renameProject(currentId, finalName);
    refreshProjects();
    noteWriteFailed(ok, currentId);
    // Clearing the name is how a customer asks for the app's guess back;
    // renameProject re-arms auto-naming for exactly that case, so apply it
    // now instead of leaving the placeholder up until the next edit. This
    // can move projectName again, which is why the resync below comes
    // after it and reads projectName rather than finalName.
    applyAutoName();
    // The resync, and it has to be the LAST thing here. Writing the
    // intermediate name straight after normalising it reproduced this very
    // defect one layer up, measured 2026-09-07: clearing the field on a
    // design auto-named HELLO wrote "Untitled design" into the DOM, then
    // applyAutoName took projectName back to "HELLO" -- the same value
    // Svelte had last rendered, so it left the DOM alone and the field
    // sat there reading "Untitled design" over a design called HELLO.
    // Setting the field from the name that actually SURVIVED cannot go
    // stale that way.
    if (target.value !== projectName) target.value = projectName;
  }

  function renameFromDrawer(id, name) {
    const finalName = (name || "").trim() || UNTITLED_NAME;
    const ok = renameProject(id, finalName);
    if (id === currentId) projectName = finalName;
    refreshProjects();
    noteWriteFailed(ok, id);
    // Only the open project has a live `project` object to derive from; a
    // cleared name on any other row keeps the placeholder until it is
    // opened and edited.
    if (id === currentId) applyAutoName();
  }

  function duplicateFromDrawer(id) {
    // Never switches the app away from whatever's currently open (see
    // duplicateProject's own contract in projects.js).
    duplicateProject(id);
    refreshProjects();
  }

  // Plan amendment A2: deleting the CURRENTLY-open project must switch the
  // app to something else immediately -- the most-recently-updated
  // survivor, or a fresh "Untitled design" if that was the last project left
  // (delete-last is just this same fallback with zero survivors). currentId
  // and project are updated together (via enterProject) so there's never a
  // moment where an in-flight persist could fire against a half-switched
  // state -- and saveProject is a no-op for unknown ids regardless (see
  // projects.js).
  // ---- .embproj export/import (2026-07-29 market-parity launch scope) ------
  // The drawer picks files and clicks buttons; the actual work lives here
  // (same App-owns-the-registry split as every other drawer action).

  // Export the current project from live in-memory state (never a stale
  // storage read mid-edit); any other row loads from the registry.
  async function exportFromDrawer(id) {
    const proj = id === currentId ? project : loadProject(id);
    if (!proj) {
      drawerNotice = "Couldn't load that design to export it.";
      return;
    }
    const name = nameFor(id);
    // The customer's original artwork rides in the file (2026-09-20,
    // projectFile.js `sources`): the design then digitizes from the FILE
    // wherever it is opened, not from the 1,200-px preview the registry
    // keeps. An original this browser no longer holds is simply not
    // embedded; that element digitizes from its preview there, with the
    // panel's note, as every element did before originals travelled.
    const sources = await collectSources(proj);
    triggerDownload({
      bytes: buildProjectFile(proj, name, sources),
      filename: projectFileName(name),
      mime: "application/json",
    });
    drawerNotice = "";
  }

  // A successful import lands like Open: registered as a NEW entry (an
  // import can never overwrite an existing design), made current, entered
  // on "content". Failures set the drawer's notice line and leave
  // everything else untouched.
  async function importFromDrawer(file) {
    let text;
    try {
      text = await file.text();
    } catch (e) {
      drawerNotice = "Couldn't read that file.";
      return;
    }
    const parsed = parseProjectFile(text);
    if (!parsed) {
      drawerNotice = "That doesn't look like a design file (.embproj).";
      return;
    }
    // The file's originals go into this browser's store BEFORE the project
    // is registered, so every element points at a record that exists here
    // (and at the key its bytes hash to — projectSources.js). A browser that
    // cannot keep them registers the design all the same; those elements
    // digitize from the preview, and the panel says so when they do.
    const restored = await restoreSources(parsed.project, parsed.sources);
    const imported = importProject(restored.project, parsed.name);
    if (!imported) {
      drawerNotice = "Couldn't save the imported design — storage may be full.";
      return;
    }
    drawerNotice = "";
    refreshProjects();
    setCurrentProject(imported.id);
    enterProject(imported.id, imported.project, parsed.name);
    drawerOpen = false;
  }

  function deleteFromDrawer(id) {
    const wasCurrent = id === currentId;
    const deleted = deleteProject(id);
    refreshProjects();
    if (!deleted) {
      // A false return ALSO covers "that id isn't in the registry any more"
      // (the A2/A10 no-op contract) -- not a storage problem, and already
      // put right by the refresh above. So only speak up if the row
      // genuinely survived the delete, and say it in the drawer the
      // customer is looking at rather than moving them somewhere else.
      if (projects.some((p) => p.id === id)) {
        drawerNotice = "Couldn’t delete that design — this browser is blocking storage.";
      }
      return;
    }
    if (!wasCurrent) return;

    // Walk survivors newest-updated first (listProjects()'s sort) and adopt
    // the first one whose record actually loads. A registry entry can
    // outlive its record -- e.g. a corrupt/missing embstudio:p:<id> value --
    // and fabricating a defaultProject() stand-in for it (as this used to
    // do) would mean the very next persist() overwrites that survivor's
    // real, still-stored-somewhere-if-corrupt data with a blank design
    // under its id. So an unloadable entry is skipped, not adopted; only if
    // NONE of them load do we fall through to the same fresh-project
    // branch used when there are zero survivors at all.
    let survivor = null;
    for (const entry of projects) {
      const loaded = loadProject(entry.id);
      if (loaded) {
        survivor = { id: entry.id, project: loaded, name: entry.name };
        break;
      }
    }

    if (survivor) {
      setCurrentProject(survivor.id);
      enterProject(survivor.id, survivor.project, survivor.name);
    } else {
      const created = createProject(UNTITLED_NAME);
      enterProject(created.id, created.project, UNTITLED_NAME);
      refreshProjects();
    }
  }
</script>

<svelte:window on:keydown={onGlobalKey} on:popstate={onPopState} />

<header class="topbar">
  <div class="topbar-logo">
    <span class="logomark" aria-hidden="true">EMB</span>
    <span class="logo">Bot Studio</span>
    <span class="undoredo">
      <button type="button" class="undo-btn" disabled={!canUndo} on:click={undoEdit} title="Undo (Ctrl+Z)" aria-label="Undo"><Icon name="undo" size={16} /></button>
      <button type="button" class="undo-btn" disabled={!canRedo} on:click={redoEdit} title="Redo (Ctrl+Y)" aria-label="Redo"><Icon name="redo" size={16} /></button>
    </span>
  </div>
  <input
    class="projectname"
    value={projectName}
    on:change={(e) => renameCurrent(e.currentTarget)}
    aria-label="Project name"
  />
  <div class="topbar-actions">
    <button type="button" class="mydesigns" bind:this={myDesignsBtn} on:click={() => (drawerOpen = !drawerOpen)}>
      My designs <span class="badge">{projects.length}</span>
    </button>
    <button type="button" class="font-credits-btn" bind:this={creditsBtn} on:click={() => openCredits(creditsBtn)}>
      Font credits
    </button>
  </div>
</header>

{#if saveFailed}
  <p class="savefail" role="alert" data-testid="save-failed-banner">
    <strong>Your changes aren’t being saved — this browser’s storage is full.</strong>
    Open <strong>My designs</strong>, download anything you want to keep as a design
    file, then delete it there to make room. Until you do, what you add is only on
    screen and will be gone if you reload.
  </p>
{/if}

{#if drawerOpen}
  <ProjectsDrawer
    {projects}
    {currentId}
    on:open={(e) => openProject(e.detail)}
    on:new={newDesign}
    on:rename={(e) => renameFromDrawer(e.detail.id, e.detail.name)}
    on:duplicate={(e) => duplicateFromDrawer(e.detail)}
    on:delete={(e) => deleteFromDrawer(e.detail)}
    on:export={(e) => exportFromDrawer(e.detail)}
    on:importfile={(e) => importFromDrawer(e.detail)}
    on:template={(e) => pickTemplate(e.detail)}
    on:close={() => (drawerOpen = false)}
    notice={drawerNotice}
  />
{/if}

{#if creditsOpen}
  <FontCredits on:close={() => (creditsOpen = false)} />
{/if}

<div class="studio">
  <section class="field">
    <EmbroideryField
      {project}
      {runtime}
      showDragHint={showDragFieldHint}
      {hoverShape}
      focusShape={selectedShape}
      on:shapehover={(e) => (hoverShape = e.detail)}
      on:shapefocus={(e) => (selectedShape = e.detail)}
      on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch, !e.detail.quiet)}
      on:elupdatemany={(e) => elUpdateMany(e.detail)}
      on:select={(e) => onSelect(e.detail)}
      on:toggleselect={(e) => onToggleSelect(e.detail)}
      on:dims={(e) => onDims(e.detail)}
      on:stats={(e) => onStats(e.detail)}
      on:addelement={(e) => onAddElement(e.detail)}
      on:shapeselect={(e) => { fieldShapeSelect = { ...e.detail, n: (fieldShapeSelect ? fieldShapeSelect.n : 0) + 1 }; }}
      on:dismisshint={() => dismissHint("drag-field")}
    />
  </section>

  <aside class="panel">
    <Configurator
      {subtitle}
      {sewFacts}
      {colorCount}
      canDownload={readyToStitch}
      bind:body={panelBody}
      on:addelement={(e) => onAddElement(e.detail)}
      on:download={openSheet}
    >
      <svelte:fragment slot="design">
        <ContentStep
          {project}
          workImage={runtime.workImages[project.selectedId]}
          flat={runtime.flats[project.selectedId]}
          {sewnColors}
          {designDims}
          {digitizerHealth}
          {showAddElementsHint}
          hoverShapeId={panelHoverShapeId}
          selectedShapeId={panelSelectedShapeId}
          on:shapehover={(e) => onPanelShapeHover(e.detail)}
          on:shapeselect={(e) => onPanelShapeSelect(e.detail)}
          {fieldShapeSelect}
          on:checkservice={checkDigitizer}
          on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
          on:elupdatemany={(e) => elUpdateMany(e.detail)}
          on:select={(e) => onSelect(e.detail)}
          on:toggleselect={(e) => onToggleSelect(e.detail)}
          on:addelement={(e) => onAddElement(e.detail)}
          on:converttotext={(e) => onConvertClusterToText(e.detail)}
          on:removeelement={(e) => onRemoveElement(e.detail)}
          on:image={(e) => onImage(project.selectedId, e.detail)}
          on:flat={(e) => onFlat(project.selectedId, e.detail)}
          on:dismisshint={() => dismissHint("add-elements")}
        />
      </svelte:fragment>
      <svelte:fragment slot="garment">
        <GarmentStep {project} {digitizerHealth} on:update={(e) => apply(e.detail)} />
      </svelte:fragment>
    </Configurator>
    {#if sheetOpen}
      <DownloadSheet
        {project}
        {runtime}
        {digitizerHealth}
        {summaryRows}
        {qualityEntries}
        qualityPartial={!qualityIsTheWholeDesign}
        ready={readyToStitch}
        on:close={closeSheet}
        on:credits={(e) => openCredits(e.detail)}
      />
    {/if}
  </aside>
</div>
