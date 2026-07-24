export function triggerDownload(out) {
  const blob = out.bytes instanceof Uint8Array ? new Blob([out.bytes], { type: out.mime }) : new Blob([out.bytes], { type: out.mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = out.filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
