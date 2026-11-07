<script>
  // The stitch simulator's control bar (moved out of EmbroideryField
  // 2026-11-07, when it grew the thread readout and the thread-change steps).
  //
  // EmbroideryField owns the playback (the rAF loop, the canvas, the keys);
  // this only shows state and says what was pressed. It is mounted inside
  // `.fieldbars` and positioned absolutely over the zoom bar (theme.css
  // `.simbar`), so its height can never change the canvas's — see the
  // ResizeObserver note in EmbroideryField before changing that.
  //
  // The global class names (.simbar, .simscrub, .simcount, .simspeed) and
  // every aria-label that was here before are kept: the e2e specs drive the
  // bar by them.
  import { createEventDispatcher } from "svelte";
  import Icon from "./Icon.svelte";
  import { blockAt } from "../lib/simulate.js";

  export let playing = false;
  export let index = 0;          // strands drawn (integer)
  export let total = 0;          // strands in the design
  export let ordinals = [];      // stitch number per strand (strandStitchOrdinals)
  export let speed = 1;
  export let timeline = null;    // simTimeline(design)
  export let names = [];         // thread label per block, from the chosen chart
  export let stopAtChanges = true;
  export let stopped = false;    // paused AT a thread change by the stop

  const dispatch = createEventDispatcher();

  $: blocks = (timeline && timeline.blocks) || [];
  $: nBlocks = blocks.length;
  // Paused at a change, the bar names the thread the operator loads NEXT;
  // otherwise the thread on the needle.
  $: cur = timeline ? blockAt(timeline, stopped ? index + 1 : index) : 0;
  $: curBlock = blocks[cur] || null;
  $: curRgb = curBlock ? curBlock.rgb : [0, 0, 0];
  $: curName = names[cur] || (curBlock && curBlock.color && curBlock.color.name) || "";
  $: stitchNow = index >= 1 ? ordinals[Math.min(index, ordinals.length) - 1] || 0 : 0;
  $: stitchTotal = ordinals[ordinals.length - 1] || 0;

  // The scrubber's thread strip: each block's colour over its share of the
  // strands, built once per design (not per frame — `blocks` only changes
  // when the timeline does).
  $: strip = stripGradient(blocks, total);
  function stripGradient(bl, n) {
    if (!n || bl.length < 2) return "";
    const stops = [];
    for (const b of bl) {
      if (b.end <= b.start) continue;
      const c = `rgb(${b.rgb[0]},${b.rgb[1]},${b.rgb[2]})`;
      stops.push(`${c} ${((b.start / n) * 100).toFixed(3)}%`, `${c} ${((b.end / n) * 100).toFixed(3)}%`);
    }
    return stops.length ? `linear-gradient(to right, ${stops.join(", ")})` : "";
  }
</script>

<div class="simbar" role="group" aria-label="Stitch simulator controls">
  <button type="button" class="zoombtn" on:click={() => dispatch("thread", { dir: -1 })} disabled={index <= 0} aria-label="Previous thread change" title="Previous thread change ( < )">
    <Icon name="skip-back" />
  </button>
  <button type="button" class="zoombtn" on:click={() => dispatch("toggle")} aria-label={playing ? "Pause" : "Play"}>
    <Icon name={playing ? "pause" : "play"} />
  </button>
  <button type="button" class="zoombtn" on:click={() => dispatch("thread", { dir: 1 })} disabled={index >= total} aria-label="Next thread change" title="Next thread change ( > )">
    <Icon name="skip-forward" />
  </button>
  <span class="simtrack">
    <input
      type="range"
      class="simscrub"
      min="0"
      max={total}
      step="1"
      value={index}
      on:input={(e) => dispatch("scrub", { value: e.currentTarget.value })}
      aria-label="Stitch progress"
    />
    {#if strip}<i class="simstrip" style="background: {strip}" aria-hidden="true"></i>{/if}
  </span>
  <!-- Grouped, like every other stitch count in the app. #402 gave this
       counter its UNIT because it sat beside a caption reading
       "1,289 stitches" while showing a bare strand index; measured again
       2026-09-07, the two still did not look alike: caption
       "1,779 stitches", counter "302 / 1779 stitches". Same number, two
       renderings, one screen. -->
  <span class="simcount">{stitchNow.toLocaleString()} / {stitchTotal.toLocaleString()} stitches</span>
  {#if nBlocks}
    <!-- Thread K of B: B is the PDF worksheet's "Thread Sequence" row count
         (one row per block, colors[k] names block k), and the name is read
         off the same chart that sheet prints from. -->
    <span class="simthread" class:simthread-stop={stopped} data-testid="sim-thread" title={curName}>
      <i class="simswatch" style="background: rgb({curRgb[0]},{curRgb[1]},{curRgb[2]})" aria-hidden="true"></i>
      <span class="simthread-k">{stopped ? "Next: " : ""}Thread {cur + 1} of {nBlocks}</span>
      {#if curName}<span class="simthread-name">{curName}</span>{/if}
    </span>
  {/if}
  {#if nBlocks > 1}
    <button
      type="button"
      class="zoombtn simstops"
      class:simon={stopAtChanges}
      on:click={() => dispatch("stops")}
      aria-pressed={stopAtChanges}
      aria-label="Stop at thread changes"
      title="Stop at each thread change, as the machine does"
    >Stops</button>
  {/if}
  <button type="button" class="zoombtn simspeed" on:click={() => dispatch("speed")} aria-label="Playback speed">
    {speed}x
  </button>
  <button type="button" class="zoombtn" on:click={() => dispatch("close")} aria-label="Close simulator"><Icon name="close" /></button>
</div>

<style>
  .simtrack {
    position: relative;
    flex: 1;
    min-width: 80px;
    display: flex;
    align-items: center;
  }
  .simtrack :global(.simscrub) { flex: 1; min-width: 0; width: 100%; }
  /* The thread strip sits under the slider's track: where each colour sews,
     so a scrub lands on a thread by eye. */
  .simstrip {
    position: absolute;
    left: 6px;
    right: 6px;
    bottom: 1px;
    height: 3px;
    border-radius: 2px;
    pointer-events: none;
  }
  .simthread {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
    max-width: 220px;
    font-size: var(--fs-xs);
    color: var(--muted);
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .simthread-stop { color: var(--ink); font-weight: var(--fw-medium); }
  .simswatch {
    flex: none;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 1px solid var(--border);
  }
  .simthread-name { overflow: hidden; text-overflow: ellipsis; min-width: 0; }
  .simstops { width: auto; padding: 0 6px; font-size: var(--fs-xs); }
  /* The bar has the zoom bar's width to work in; the chart name is the first
     thing to go when that is short. The swatch and "Thread K of B" stay. */
  @container fieldbars (max-width: 900px) {
    .simthread-name { display: none; }
  }
  @container fieldbars (max-width: 640px) {
    .simthread-k { display: none; }
  }
</style>
