// Which pills the garment row shows (spec §3). The three commonest
// placements are always there under a short name; any other garment in
// force rides along as a fourth pill, so the row always shows what is
// selected without listing all ten.
export const PRIMARY_PILLS = [
  { id: "left_chest", short: "Polo" },
  { id: "hat_front", short: "Hat" },
  { id: "full_back", short: "Tee" },
];

export function pillsFor(garmentId, garments) {
  const labelOf = (id) => {
    const g = (garments || []).find((x) => x.id === id);
    return g ? g.label : id;
  };
  const pills = PRIMARY_PILLS.map((p) => ({
    id: p.id,
    text: p.short,
    title: labelOf(p.id),
    selected: p.id === garmentId,
  }));
  const isPrimary = PRIMARY_PILLS.some((p) => p.id === garmentId);
  const known = (garments || []).some((g) => g.id === garmentId);
  if (!isPrimary && known) {
    pills.push({ id: garmentId, text: labelOf(garmentId), title: labelOf(garmentId), selected: true });
  }
  return pills;
}
