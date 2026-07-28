<script>
  import { update, updateElement, selectElement, addElement, removeElement } from "./lib/project.js";
  import { createHistory } from "./lib/history.js";
  import { applyTemplate } from "./lib/templates.js";
  import { canAdvance, nextStep, prevStep } from "./lib/flow.js";
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
    listProjects,
  } from "./lib/projects.js";
  import { shouldShow, dismiss, visibleHint } from "./lib/hints.js";
  import { EMB } from "./lib/emb.js";
  import GarmentStep from "./ui/GarmentStep.svelte";
  import ContentStep from "./ui/ContentStep.svelte";
  import DownloadStep from "./ui/DownloadStep.svelte";
  import StepNav from "./ui/StepNav.svelte";
  import EmbroideryField from "./ui/EmbroideryField.svelte";
  import SizePanel from "./ui/SizePanel.svelte";
  import ProjectsDrawer from "./ui/ProjectsDrawer.svelte";
  import FontCredits from "./ui/FontCredits.svelte";
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
    return entry ? entry.name : "Untitled design";
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
    const created = createProject("Untitled design");
    currentId = created.id;
    bootProject = created.project;
    projects = listProjects();
  }

  let project = resetHasImage(bootProject);
  let projectName = nameFor(currentId);
  let step = "garment";

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
    saveProject(currentId, project);
    refreshProjects();
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
  // Dims of the SELECTED element's last generated design ({ widthMM, heightMM })
  // or null on failure/no-content -- fed to SizePanel so its W/H display
  // (and the below-5mm warning) always reflects the real current design,
  // including while the user drags the field's resize handles.
  let designDims = null;

  // The currently-selected element (SizePanel/ContentStep/the "create" step
  // summary all key off this one, not project.elements[0], so they stay in
  // sync with whatever the user clicked on the field).
  $: selectedElement = project.elements.find((el) => el.id === project.selectedId) || project.elements[0];

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
  // collects whichever of the three are BOTH still-shown AND contextually
  // eligible right now --
  //   drag-field   ⇔ the combined design has stitches (hasStitches, from
  //                  EmbroideryField's "stats" event -- A8)
  //   add-elements ⇔ on the content step with < 2 elements
  //   templates    ⇔ on the garment step
  // -- and hands that list to hints.js's visibleHint(), which picks the
  // single highest-priority one (drag-field > add-elements > templates).
  // Note the embroidery field (and therefore drag-field's eligibility) is
  // visible alongside EVERY step, so it can legitimately outrank templates
  // even while step === "garment".
  let templatesShown = shouldShow("templates");
  let addElementsShown = shouldShow("add-elements");
  let dragFieldShown = shouldShow("drag-field");
  let hasStitches = false;

  function dismissHint(key) {
    dismiss(key);
    if (key === "templates") templatesShown = false;
    else if (key === "add-elements") addElementsShown = false;
    else if (key === "drag-field") dragFieldShown = false;
  }

  // EmbroideryField's "stats" event -- reports the COMBINED design's stitch
  // count after every generate attempt (0 on error/no-content).
  function onStats(detail) {
    hasStitches = !!(detail && detail.stitchCount > 0);
  }

  $: eligibleHints = [
    dragFieldShown && hasStitches ? "drag-field" : null,
    addElementsShown && step === "content" && project.elements.length < 2 ? "add-elements" : null,
    templatesShown && step === "garment" ? "templates" : null,
  ].filter(Boolean);
  $: visibleHintKey = visibleHint(eligibleHints);
  $: showTemplatesHint = visibleHintKey === "templates";
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
  function persist(record = true) {
    if (record) {
      history.record(project);
      syncHistoryFlags();
    }
    saveProject(currentId, project);
    refreshProjects();
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

  // Hoop width in mm for the current garment — new elements are seeded with
  // a size relative to it (see project.js's addElement). Falls back to a
  // sane default if the garment can't be resolved (shouldn't happen: the
  // "content" step, where adding elements happens, is unreachable until a
  // garment is picked — see flow.js's canAdvance).
  function hoopWidthMm(p) {
    const garment = p && EMB.getGarment(p.garmentId);
    return garment ? garment.widthIn * MM_PER_INCH : 300;
  }

  function onAddElement(type) {
    project = addElement(project, type, hoopWidthMm(project));
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
    project = applyTemplate(project, template);
    persist();
    step = "content";
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

  function onFlat(elementId, flat) {
    runtime = { ...runtime, flats: { ...runtime.flats, [elementId]: flat } };
    elUpdate(elementId, { _hasImage: !!flat });
  }

  function onDims(detail) {
    designDims = detail;
  }

  function go(dir) {
    const s = dir > 0 ? nextStep(step) : prevStep(step);
    if (s) step = s;
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
  // own comment above), and updates currentId/projectName/step together so
  // there's never a moment where one is stale relative to the others.
  function enterProject(id, proj, name, targetStep) {
    project = resetHasImage(proj);
    runtime = { flats: {}, workImages: {} };
    designDims = null;
    currentId = id;
    projectName = name;
    step = targetStep;
    history.reset(project); // history is per-project; a switch starts fresh
    syncHistoryFlags();
  }

  // Drawer "Open" (plan amendment A6): lands on "content", not "garment" --
  // switching to an existing, already-started project shouldn't dump the
  // user back at the beginning. Opening the CURRENTLY-open project just
  // closes the drawer.
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
    enterProject(id, loaded, nameFor(id), "content");
    drawerOpen = false;
  }

  // Drawer "+ New design": a genuinely blank project, so (unlike Open) it
  // lands on "garment" -- there's no content yet to jump into.
  function newDesign() {
    const created = createProject("Untitled design");
    enterProject(created.id, created.project, "Untitled design", "garment");
    drawerOpen = false;
    refreshProjects();
  }

  function renameCurrent(name) {
    const finalName = (name || "").trim() || "Untitled design";
    projectName = finalName;
    renameProject(currentId, finalName);
    refreshProjects();
  }

  function renameFromDrawer(id, name) {
    const finalName = (name || "").trim() || "Untitled design";
    renameProject(id, finalName);
    if (id === currentId) projectName = finalName;
    refreshProjects();
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
  function deleteFromDrawer(id) {
    const wasCurrent = id === currentId;
    deleteProject(id);
    refreshProjects();
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
      enterProject(survivor.id, survivor.project, survivor.name, "content");
    } else {
      const created = createProject("Untitled design");
      enterProject(created.id, created.project, "Untitled design", "garment");
      refreshProjects();
    }
  }
</script>

<svelte:window on:keydown={onGlobalKey} />

<header class="topbar">
  <div class="topbar-logo">
    <span class="logomark" aria-hidden="true">EMB</span>
    <span class="logo">Bot Studio</span>
    <span class="undoredo">
      <button type="button" class="undo-btn" disabled={!canUndo} on:click={undoEdit} title="Undo (Ctrl+Z)" aria-label="Undo">↶</button>
      <button type="button" class="undo-btn" disabled={!canRedo} on:click={redoEdit} title="Redo (Ctrl+Y)" aria-label="Redo">↷</button>
    </span>
  </div>
  <input
    class="projectname"
    value={projectName}
    on:change={(e) => renameCurrent(e.currentTarget.value)}
    aria-label="Project name"
  />
  <div class="topbar-actions">
    <button
      type="button"
      class="topbar-download"
      disabled={!hasStitches}
      on:click={() => (step = "download")}
    >
      Download
    </button>
    <button type="button" class="mydesigns" bind:this={myDesignsBtn} on:click={() => (drawerOpen = !drawerOpen)}>
      My designs <span class="badge">{projects.length}</span>
    </button>
    <button type="button" class="font-credits-btn" bind:this={creditsBtn} on:click={() => openCredits(creditsBtn)}>
      Font credits
    </button>
  </div>
</header>

{#if drawerOpen}
  <ProjectsDrawer
    {projects}
    {currentId}
    on:open={(e) => openProject(e.detail)}
    on:new={newDesign}
    on:rename={(e) => renameFromDrawer(e.detail.id, e.detail.name)}
    on:duplicate={(e) => duplicateFromDrawer(e.detail)}
    on:delete={(e) => deleteFromDrawer(e.detail)}
    on:close={() => (drawerOpen = false)}
  />
{/if}

{#if creditsOpen}
  <FontCredits on:close={() => (creditsOpen = false)} />
{/if}

<div class="studio">
  <aside class="panel">
    <div class="panel-body">
      {#if step === "garment"}
        <GarmentStep
          {project}
          {showTemplatesHint}
          on:update={(e) => apply(e.detail)}
          on:template={(e) => pickTemplate(e.detail)}
          on:dismisshint={() => dismissHint("templates")}
        />
      {:else if step === "content"}
        <ContentStep
          {project}
          workImage={runtime.workImages[project.selectedId]}
          flat={runtime.flats[project.selectedId]}
          {designDims}
          {showAddElementsHint}
          on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch)}
          on:select={(e) => onSelect(e.detail)}
          on:addelement={(e) => onAddElement(e.detail)}
          on:removeelement={(e) => onRemoveElement(e.detail)}
          on:image={(e) => onImage(project.selectedId, e.detail)}
          on:flat={(e) => onFlat(project.selectedId, e.detail)}
          on:dismisshint={() => dismissHint("add-elements")}
        />
      {:else if step === "create"}
        <div class="createstep">
          <h2>Ready to stitch</h2>
          <p>Looks good? The field on the right is your stitch-out.</p>
          <dl class="summary">
            <div><dt>Garment</dt><dd>{readable(project.garmentId)}</dd></div>
            {#if selectedElement.type === "image"}
              <div><dt>Content</dt><dd>Logo / image</dd></div>
              <div><dt>Colors</dt><dd>{selectedElement.nColors}{selectedElement.removeBg ? " · background removed" : ""}</dd></div>
            {:else}
              <div><dt>Content</dt><dd>Text — "{selectedElement.text}"</dd></div>
              <div><dt>Font</dt><dd>{readable(selectedElement.fontKey)}</dd></div>
            {/if}
          </dl>
          <p class="hint">Not quite right? Go back to adjust the garment or content — the field updates live.</p>
          <SizePanel project={{ ...project, ...selectedElement }} {designDims} on:update={(e) => elUpdate(selectedElement.id, e.detail)} />
        </div>
      {:else}
        <DownloadStep {project} {runtime} on:credits={(e) => openCredits(e.detail)} />
      {/if}
    </div>
    <StepNav
      {step}
      {project}
      canNext={canAdvance(step, project)}
      on:back={() => go(-1)}
      on:next={() => go(1)}
      on:goto={(e) => (step = e.detail)}
    />
  </aside>

  <section class="field">
    <EmbroideryField
      {project}
      {runtime}
      showDragHint={showDragFieldHint}
      on:elupdate={(e) => elUpdate(e.detail.id, e.detail.patch, !e.detail.quiet)}
      on:select={(e) => onSelect(e.detail)}
      on:dims={(e) => onDims(e.detail)}
      on:stats={(e) => onStats(e.detail)}
      on:dismisshint={() => dismissHint("drag-field")}
    />
  </section>
</div>
