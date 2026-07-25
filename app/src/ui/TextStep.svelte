<script>
  import FontSelect from "./FontSelect.svelte";
  import { createEventDispatcher } from "svelte";
  export let project;
  const d = createEventDispatcher();

  function rgbToHex([r, g, b]) {
    return "#" + [r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("");
  }
  function hexToRgb(h) {
    return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  }
</script>

<input
  class="textin"
  type="text"
  bind:value={project.text}
  on:input={() => d("update", { text: project.text })}
  placeholder="Type a name or word"
/>
<label>
  Color
  <input type="color" value={rgbToHex(project.colorRgb)} on:input={(e) => d("update", { colorRgb: hexToRgb(e.target.value) })} />
</label>
<h3>Font</h3>
<FontSelect selected={project.fontKey} on:pick={(e) => d("update", { fontKey: e.detail })} />
<label class="letterspacing">
  <span>Letter spacing</span>
  <input
    type="range"
    min="-1"
    max="6"
    step="0.5"
    value={project.letterSpacingMm || 0}
    on:input={(e) => d("update", { letterSpacingMm: parseFloat(e.target.value) })}
  />
  <span class="label">{(project.letterSpacingMm || 0).toFixed(1)} mm</span>
</label>
