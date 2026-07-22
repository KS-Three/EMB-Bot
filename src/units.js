(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MM_PER_INCH = 25.4;
  const DST_UNITS_PER_MM = 10;

  function inToMm(inch) {
    return inch * MM_PER_INCH;
  }

  function mmToInch(mm) {
    return mm / MM_PER_INCH;
  }

  function mmToDstUnits(mm) {
    return Math.round(mm * DST_UNITS_PER_MM);
  }

  function dstUnitsToMm(u) {
    return u / DST_UNITS_PER_MM;
  }

  return {
    MM_PER_INCH,
    DST_UNITS_PER_MM,
    inToMm,
    mmToInch,
    mmToDstUnits,
    dstUnitsToMm,
  };
});
