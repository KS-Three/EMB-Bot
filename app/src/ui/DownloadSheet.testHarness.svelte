<script>
  import DownloadSheet from "./DownloadSheet.svelte";
  export let project;
  export let runtime = { flats: {}, workImages: {} };
  export let summaryRows = [];
  export let hoopingRows = [];
  export let qualityEntries = [];
  export let qualityPartial = false;
  export let ready = true;
  export let onClose = () => {};
</script>

<DownloadSheet
  {project}
  {runtime}
  digitizerHealth={null}
  {summaryRows}
  {hoopingRows}
  {qualityEntries}
  {qualityPartial}
  {ready}
  on:close={onClose}
/>
