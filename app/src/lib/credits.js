// Credits data derived from the font manifest — never hand-maintained.
export function creditLines(manifestFonts) {
  return (manifestFonts || [])
    .map((f) => ({
      name: f.name || f.key,
      licenseId: f.licenseId || "",
      attribution: f.attribution || "",
      source: f.source || "",
      binHref: "/fonts/bin/" + f.key + ".embf",
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
