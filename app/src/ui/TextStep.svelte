<script>
  import FontSelect from "./FontSelect.svelte";
  import { createEventDispatcher } from "svelte";

  // Element-scoped text editor (Task 5, Slice 5): bound to whichever text
  // element is currently selected in ContentStep's element list, not a
  // single project-wide text field like the old v1 shape.
  //
  // Patch convention (documented here, ImagePanel.svelte follows the same
  // one): every edit dispatches an "elupdate" event shaped
  // { id: element.id, patch } directly -- this component already knows its
  // own element's id, so it wraps the patch itself instead of dispatching a
  // bare patch and making the parent guess whose id to attach. ContentStep
  // just bubbles these straight through to App unchanged.
  export let element;
  const d = createEventDispatcher();

  function patch(p) {
    d("elupdate", { id: element.id, patch: p });
  }

  function rgbToHex([r, g, b]) {
    return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
  }
  function hexToRgb(h) {
    return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
</script>

<textarea
  class="textin"
  rows="2"
  value={element.text}
  on:input={(e) => patch({ text: e.target.value })}
  placeholder="Type a name or word"
></textarea>
<label>
  Color
  <input type="color" value={rgbToHex(element.colorRgb)} on:input={(e) => patch({ colorRgb: hexToRgb(e.target.value) })} />
</label>
<h3>Font</h3>
<FontSelect selected={element.fontKey} on:pick={(e) => patch({ fontKey: e.detail })} />
<label class="letterspacing">
  <span>Letter spacing</span>
  <input
    type="range"
    min="-1"
    max="6"
    step="0.5"
    value={element.letterSpacingMm || 0}
    on:input={(e) => patch({ letterSpacingMm: parseFloat(e.target.value) })}
  />
  <span class="label">{(element.letterSpacingMm || 0).toFixed(1)} mm</span>
</label>
<label class="letterspacing">
  <span>Curve</span>
  <input
    type="range"
    min="-180"
    max="180"
    step="10"
    value={element.arcDeg || 0}
    on:input={(e) => patch({ arcDeg: parseInt(e.target.value, 10) })}
  />
  <span class="label">{element.arcDeg || 0}°</span>
</label>
