<script>
  // The digitize ring: one bright arc chasing round a faint track, throbbing
  // gently, over the embroidery field while a digitize is in flight, fading
  // out as the stitches land and the outline pulse takes over. Kent,
  // 2026-10-08: "don't make it a pinwheel, make it a ring" (it was the
  // "throbbing pulsating" indicator).
  //
  // Pure SVG; the motion is CSS in theme.css's Motion section (`.digitize-ring`).
  // With reduced motion it is a static ring: no spin, no throb.
  import { fade } from "svelte/transition";
  import { prefersReducedMotion } from "../lib/reducedMotion.js";
  export let label = "Digitizing your art";
</script>

<!-- data-testid keeps the old "digitize-pinwheel" id so e2e/field-outlines.spec.js is unchanged. -->
<div class="digitize-ring" role="status" aria-label={label} data-testid="digitize-pinwheel" out:fade={{ duration: prefersReducedMotion() ? 0 : 350 }}>
  <svg class="digitize-ring-svg" viewBox="-50 -50 100 100" aria-hidden="true" focusable="false">
    <circle class="digitize-ring-halo" r="38" />
    <circle class="digitize-ring-track" r="38" />
    <g class="digitize-ring-spin">
      <circle class="digitize-ring-arc" r="38" pathLength="100" stroke-dasharray="28 72" />
    </g>
  </svg>
</div>
