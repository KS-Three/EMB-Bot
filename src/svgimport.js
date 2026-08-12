(function (root, factory) {
  const api = factory(root);
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  // SVG document -> color regions for the digitizer.
  //
  // parseSVG(svgText, opts) returns { regions, pxPerMm, warnings } with
  // regions = [{ rgb: [r,g,b], shapes: [{ outer: [{x,y}], holes: [[{x,y}]] }] }]
  // — the exact contract flatToRegions (app/src/lib/imageRegions.js) returns
  // for raster art, so buildQualityDesign consumes either unchanged.
  //
  // Supported: path/rect/circle/ellipse/line/polyline/polygon geometry;
  // transform lists with translate/scale/rotate/matrix/skewX/skewY on any
  // element or group; fill via presentation attribute, inline style, or
  // inheritance; hex/#rgb/rgb()/named colors; fill-rule evenodd and nonzero.
  //
  // NOT supported (documented so the caller can warn honestly):
  // - <use>/<symbol> instancing, external references, CSS <style> blocks and
  //   class selectors (only inline style="" is read)
  // - gradients and patterns (url(#...) paints) — the element is skipped
  // - strokes (no outline expansion), markers, filters, masks, clip-paths
  // - <text> (must be converted to outlines upstream)
  // - opacity/fill-opacity (a translucent fill imports as solid)
  // - preserveAspectRatio (geometry is taken in viewBox units as-is)
  const IDENTITY = [1, 0, 0, 1, 0, 0];
  const NUM_RE = /[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?/g;

  // SVG matrices are [a,b,c,d,e,f] meaning
  //   x' = a*x + c*y + e
  //   y' = b*x + d*y + f
  function multiplyMatrix(m1, m2) {
    return [
      m1[0] * m2[0] + m1[2] * m2[1],
      m1[1] * m2[0] + m1[3] * m2[1],
      m1[0] * m2[2] + m1[2] * m2[3],
      m1[1] * m2[2] + m1[3] * m2[3],
      m1[0] * m2[4] + m1[2] * m2[5] + m1[4],
      m1[1] * m2[4] + m1[3] * m2[5] + m1[5],
    ];
  }

  function applyMatrix(m, pt) {
    return {
      x: m[0] * pt.x + m[2] * pt.y + m[4],
      y: m[1] * pt.x + m[3] * pt.y + m[5],
    };
  }

  // Parses a transform LIST. Per spec the list applies left to right, which
  // means the leftmost is the outermost — so they compose by successive
  // right-multiplication. Unknown functions are ignored.
  function parseTransform(str) {
    let m = IDENTITY.slice();
    const re = /([a-zA-Z]+)\s*\(([^)]*)\)/g;
    let match;
    while ((match = re.exec(String(str || "")))) {
      const name = match[1];
      const a = (match[2].match(NUM_RE) || []).map(Number);
      let t = null;
      if (name === "translate") t = [1, 0, 0, 1, a[0] || 0, a.length > 1 ? a[1] : 0];
      else if (name === "scale") t = [a[0] || 0, 0, 0, a.length > 1 ? a[1] : a[0] || 0, 0, 0];
      else if (name === "matrix" && a.length >= 6) t = a.slice(0, 6);
      else if (name === "rotate") {
        const rad = ((a[0] || 0) * Math.PI) / 180;
        const cos = Math.cos(rad), sin = Math.sin(rad);
        const rot = [cos, sin, -sin, cos, 0, 0];
        if (a.length >= 3) {
          // rotate(angle cx cy) == translate(cx,cy) rotate(angle) translate(-cx,-cy)
          t = multiplyMatrix([1, 0, 0, 1, a[1], a[2]], rot);
          t = multiplyMatrix(t, [1, 0, 0, 1, -a[1], -a[2]]);
        } else t = rot;
      } else if (name === "skewX") t = [1, 0, Math.tan(((a[0] || 0) * Math.PI) / 180), 1, 0, 0];
      else if (name === "skewY") t = [1, Math.tan(((a[0] || 0) * Math.PI) / 180), 0, 1, 0, 0];
      if (t) m = multiplyMatrix(m, t);
    }
    return m;
  }

  function num(attrs, name, fallback) {
    const v = parseFloat(attrs[name]);
    return isFinite(v) ? v : fallback;
  }

  // Builds a rounded-rectangle or plain-rectangle outline. Corner arcs reuse
  // the path parser so arc flattening logic exists in exactly one place.
  function rectSubpath(attrs, opts) {
    const x = num(attrs, "x", 0), y = num(attrs, "y", 0);
    const w = num(attrs, "width", 0), h = num(attrs, "height", 0);
    if (w <= 0 || h <= 0) return [];
    let rx = num(attrs, "rx", NaN), ry = num(attrs, "ry", NaN);
    if (!isFinite(rx) && !isFinite(ry)) {
      return [{ points: [
        { x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h },
      ], closed: true }];
    }
    if (!isFinite(rx)) rx = ry;
    if (!isFinite(ry)) ry = rx;
    rx = Math.min(Math.abs(rx), w / 2); ry = Math.min(Math.abs(ry), h / 2);
    if (rx === 0 || ry === 0) {
      return [{ points: [
        { x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h },
      ], closed: true }];
    }
    const d = [
      "M", x + rx, y,
      "H", x + w - rx,
      "A", rx, ry, 0, 0, 1, x + w, y + ry,
      "V", y + h - ry,
      "A", rx, ry, 0, 0, 1, x + w - rx, y + h,
      "H", x + rx,
      "A", rx, ry, 0, 0, 1, x, y + h - ry,
      "V", y + ry,
      "A", rx, ry, 0, 0, 1, x + rx, y,
      "Z",
    ].join(" ");
    return root.EMB.parsePathData(d, opts);
  }

  function ellipseSubpath(cx, cy, rx, ry, opts) {
    rx = Math.abs(rx); ry = Math.abs(ry);
    if (rx <= 0 || ry <= 0) return [];
    // Two half arcs, because a single arc from a point back to itself is
    // skipped per the SVG spec.
    const d = [
      "M", cx - rx, cy,
      "A", rx, ry, 0, 0, 1, cx + rx, cy,
      "A", rx, ry, 0, 0, 1, cx - rx, cy,
      "Z",
    ].join(" ");
    return root.EMB.parsePathData(d, opts);
  }

  function pointsList(str) {
    const a = (String(str || "").match(NUM_RE) || []).map(Number);
    const pts = [];
    for (let i = 0; i + 1 < a.length; i += 2) pts.push({ x: a[i], y: a[i + 1] });
    return pts;
  }

  function primitiveToSubpaths(tagName, attrs, opts) {
    const o = opts || {};
    switch (tagName) {
      case "rect": return rectSubpath(attrs, o);
      case "circle": {
        const r = num(attrs, "r", 0);
        return ellipseSubpath(num(attrs, "cx", 0), num(attrs, "cy", 0), r, r, o);
      }
      case "ellipse":
        return ellipseSubpath(num(attrs, "cx", 0), num(attrs, "cy", 0),
          num(attrs, "rx", 0), num(attrs, "ry", 0), o);
      case "line":
        return [{ points: [
          { x: num(attrs, "x1", 0), y: num(attrs, "y1", 0) },
          { x: num(attrs, "x2", 0), y: num(attrs, "y2", 0) },
        ], closed: false }];
      case "polygon": {
        const pts = pointsList(attrs.points);
        return pts.length ? [{ points: pts, closed: true }] : [];
      }
      case "polyline": {
        const pts = pointsList(attrs.points);
        return pts.length ? [{ points: pts, closed: false }] : [];
      }
      case "path":
        return root.EMB.parsePathData(attrs.d || "", o);
      default: return [];
    }
  }

  // ---------------------------------------------------------------------
  // Document parsing
  // ---------------------------------------------------------------------

  // Minimal element scanner. A real XML parser is unnecessary and would be a
  // dependency: exported vector art is well-formed, and all this needs is tag
  // name, attributes, and nesting depth for transform and fill inheritance.
  const TAG_RE = /<\s*(\/?)\s*([a-zA-Z][\w:-]*)((?:\s+[\w:-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)\s*>/g;
  const ATTR_RE = /([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g;

  const NAMED_COLORS = {
    black: [0, 0, 0], white: [255, 255, 255], red: [255, 0, 0],
    green: [0, 128, 0], lime: [0, 255, 0], blue: [0, 0, 255],
    yellow: [255, 255, 0], cyan: [0, 255, 255], aqua: [0, 255, 255],
    magenta: [255, 0, 255], fuchsia: [255, 0, 255], gray: [128, 128, 128],
    grey: [128, 128, 128], silver: [192, 192, 192], maroon: [128, 0, 0],
    olive: [128, 128, 0], navy: [0, 0, 128], purple: [128, 0, 128],
    teal: [0, 128, 128], orange: [255, 165, 0], pink: [255, 192, 203],
    brown: [165, 42, 42], gold: [255, 215, 0], beige: [245, 245, 220],
  };

  // Container elements whose CONTENT never renders directly. Geometry found
  // inside them must not become stitches (a <defs> circle only appears where
  // a <use> instances it, and <use> is unsupported).
  const HIDDEN_CONTAINERS = {
    defs: 1, symbol: 1, clippath: 1, mask: 1, pattern: 1, marker: 1,
    lineargradient: 1, radialgradient: 1, filter: 1, style: 1, metadata: 1, title: 1, desc: 1,
  };

  function parseAttrs(raw) {
    const attrs = {};
    let m;
    ATTR_RE.lastIndex = 0;
    while ((m = ATTR_RE.exec(raw || ""))) attrs[m[1]] = m[2] !== undefined ? m[2] : m[3];
    return attrs;
  }

  // Reads a property from the inline style attribute, which per CSS cascade
  // outranks the equivalent presentation attribute.
  function styleProp(styleStr, prop) {
    if (!styleStr) return null;
    const re = new RegExp("(?:^|;)\\s*" + prop + "\\s*:\\s*([^;]+)", "i");
    const m = re.exec(styleStr);
    return m ? m[1].trim() : null;
  }

  function parseColor(value) {
    if (!value) return null;
    const v = String(value).trim().toLowerCase();
    if (v === "none" || v === "transparent") return null;
    if (v[0] === "#") {
      const hex = v.slice(1);
      if (hex.length === 3) {
        return [parseInt(hex[0] + hex[0], 16), parseInt(hex[1] + hex[1], 16), parseInt(hex[2] + hex[2], 16)];
      }
      if (hex.length === 6) {
        return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
      }
      return null;
    }
    if (v.startsWith("rgb")) {
      const a = (v.match(NUM_RE) || []).map(Number);
      if (a.length >= 3) return [Math.round(a[0]), Math.round(a[1]), Math.round(a[2])];
      return null;
    }
    if (Object.prototype.hasOwnProperty.call(NAMED_COLORS, v)) return NAMED_COLORS[v].slice();
    return null; // url(#gradient) and anything else unsupported
  }

  function signedArea(pts) {
    let a = 0;
    for (let i = 0, n = pts.length; i < n; i++) {
      const p = pts[i], q = pts[(i + 1) % n];
      a += p.x * q.y - q.x * p.y;
    }
    return a / 2;
  }

  function bboxOf(pts) {
    let minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    for (const p of pts) {
      if (p.x < minx) minx = p.x; if (p.x > maxx) maxx = p.x;
      if (p.y < miny) miny = p.y; if (p.y > maxy) maxy = p.y;
    }
    return { minx, miny, maxx, maxy };
  }

  function pointInPolygon(pt, poly) {
    let inside = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const a = poly[i], b = poly[j];
      if ((a.y > pt.y) !== (b.y > pt.y) &&
          pt.x < ((b.x - a.x) * (pt.y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
    }
    return inside;
  }

  // Groups one ELEMENT's subpath rings into filled shapes with holes,
  // honoring that element's fill-rule. Rings are grouped per element (not
  // per color) because SVG's painting model fills each element
  // independently — a same-colored element drawn inside another is painted
  // ON TOP, never punched out as a hole.
  //
  // Fill-rule semantics, stated explicitly:
  // - evenodd: a ring nested inside an odd number of other rings bounds a
  //   hole; even nesting bounds a fill. Winding direction is irrelevant.
  // - nonzero: classify by winding number. For a point just inside ring i,
  //   w_in = sum of orientations of every ring containing it (including i);
  //   just outside, w_out = w_in - orientation(i). Filled means w != 0, so:
  //   w_in != 0 && w_out == 0  -> outer boundary
  //   w_in == 0 && w_out != 0  -> hole boundary
  //   both nonzero             -> ring is invisible inside a filled area
  //                               (e.g. same-direction nested ring): dropped.
  // This is exact for rings that nest without crossing; self-intersecting
  // rings and partially overlapping sibling rings are beyond this importer
  // (they come out as drawn, without boolean resolution).
  function groupIntoShapes(rings, fillRule) {
    const evenodd = String(fillRule || "nonzero").toLowerCase() === "evenodd";
    const withMeta = [];
    for (const pts of rings) {
      if (pts.length < 3) continue;
      const sa = signedArea(pts);
      if (sa === 0) continue; // zero-area sliver contributes nothing
      withMeta.push({ pts, box: bboxOf(pts), area: Math.abs(sa), sign: sa > 0 ? 1 : -1 });
    }
    withMeta.sort((a, b) => b.area - a.area); // outers before their holes
    // containers[i] = indices of rings properly containing ring i.
    const containers = withMeta.map(() => []);
    for (let i = 0; i < withMeta.length; i++) {
      for (let j = 0; j < withMeta.length; j++) {
        if (i === j) continue;
        const inner = withMeta[i], outer = withMeta[j];
        if (outer.area <= inner.area) continue;
        if (inner.box.minx < outer.box.minx || inner.box.maxx > outer.box.maxx ||
            inner.box.miny < outer.box.miny || inner.box.maxy > outer.box.maxy) continue;
        if (pointInPolygon(inner.pts[0], outer.pts)) containers[i].push(j);
      }
    }
    const role = withMeta.map((ring, i) => {
      if (evenodd) return containers[i].length % 2 === 0 ? "outer" : "hole";
      let wOut = 0;
      for (const j of containers[i]) wOut += withMeta[j].sign;
      const wIn = wOut + ring.sign;
      if (wIn !== 0 && wOut === 0) return "outer";
      if (wIn === 0 && wOut !== 0) return "hole";
      return "drop"; // buried inside an already-filled area
    });
    const shapes = [];
    const shapeIndexByRing = new Array(withMeta.length).fill(-1);
    for (let i = 0; i < withMeta.length; i++) {
      if (role[i] !== "outer") continue;
      shapeIndexByRing[i] = shapes.length;
      shapes.push({ outer: withMeta[i].pts, holes: [] });
    }
    for (let i = 0; i < withMeta.length; i++) {
      if (role[i] !== "hole") continue;
      // Attach to the smallest containing ring that became an outer.
      let bestIdx = -1, bestArea = Infinity;
      for (const j of containers[i]) {
        if (role[j] !== "outer") continue;
        if (withMeta[j].area < bestArea) { bestArea = withMeta[j].area; bestIdx = j; }
      }
      if (bestIdx >= 0) shapes[shapeIndexByRing[bestIdx]].holes.push(withMeta[i].pts);
    }
    return shapes;
  }

  function parseSVG(svgText, opts) {
    const o = opts || {};
    const targetLongMm = o.targetLongMm || 50;
    const warnings = [];
    const text = String(svgText || "");

    // Root sizing: viewBox is authoritative; width/height is the fallback.
    let vbW = 0, vbH = 0;
    const rootMatch = /<\s*svg\b([^>]*)>/i.exec(text);
    const rootAttrs = rootMatch ? parseAttrs(rootMatch[1]) : {};
    if (rootAttrs.viewBox) {
      const a = (rootAttrs.viewBox.match(NUM_RE) || []).map(Number);
      if (a.length >= 4) { vbW = a[2]; vbH = a[3]; }
    }
    if (!vbW || !vbH) {
      vbW = parseFloat(rootAttrs.width) || 0;
      vbH = parseFloat(rootAttrs.height) || 0;
      if (vbW && vbH) warnings.push("No viewBox found; using the width/height attributes for scale.");
    }
    if (!vbW || !vbH) {
      vbW = 100; vbH = 100;
      warnings.push("No viewBox, width or height found; assuming a 100x100 coordinate space.");
    }

    // Flattening tolerance resolves in FINAL MM, not source units: a fixed
    // source-unit tolerance silently coarsens as a design scales up. This is
    // the same class of bug as the 2026-07-27 density-floor regression.
    const unitsPerMm = Math.max(vbW, vbH) / targetLongMm;
    const TOLERANCE_MM = 0.05;
    const tolerance = TOLERANCE_MM * unitsPerMm;

    // Stack of inherited state, one frame per open element.
    const stack = [{ matrix: IDENTITY.slice(), fill: null, fillRule: "nonzero", hidden: false }];
    const byColor = new Map();
    let sawText = false, sawStrokeOnly = false, sawUse = false, sawUnsupportedPaint = false;

    let m;
    TAG_RE.lastIndex = 0;
    while ((m = TAG_RE.exec(text))) {
      const closing = m[1] === "/";
      const tag = m[2].toLowerCase().replace(/^.*:/, ""); // strip any namespace
      const selfClosing = m[4] === "/";
      if (closing) { if (stack.length > 1) stack.pop(); continue; }

      const attrs = parseAttrs(m[3]);
      const parent = stack[stack.length - 1];

      let matrix = parent.matrix;
      if (attrs.transform) matrix = multiplyMatrix(matrix, parseTransform(attrs.transform));

      const styleFill = styleProp(attrs.style, "fill");
      const rawFill = styleFill !== null ? styleFill : attrs.fill;
      const fill = rawFill !== undefined && rawFill !== null
        ? { value: rawFill, rgb: parseColor(rawFill) }
        : parent.fill;
      const fillRule = styleProp(attrs.style, "fill-rule") || attrs["fill-rule"] || parent.fillRule;
      const hidden = parent.hidden || HIDDEN_CONTAINERS[tag] === 1;
      const frame = { matrix, fill, fillRule, hidden };

      if (tag === "text" || tag === "tspan") sawText = true;
      if (tag === "use") sawUse = true;

      const subs = hidden ? [] : primitiveToSubpaths(tag, attrs, { tolerance });
      if (subs.length) {
        // An explicit fill of "none" (or an unresolvable paint) means no
        // fill; an ABSENT fill anywhere in the ancestor chain means black,
        // per the SVG initial value.
        const explicitNone = fill && fill.rgb === null;
        const rgb = fill && fill.rgb ? fill.rgb : (explicitNone ? null : [0, 0, 0]);
        if (rgb === null) {
          if (fill && /^url\s*\(/i.test(fill.value)) sawUnsupportedPaint = true;
          const strokeVal = styleProp(attrs.style, "stroke") || attrs.stroke;
          if (strokeVal && strokeVal !== "none") sawStrokeOnly = true;
        } else {
          const rings = subs.map((s) => s.points.map((p) => applyMatrix(matrix, p)));
          // Group THIS element's rings into shapes under its own fill-rule,
          // then merge the shapes into the per-color region.
          const shapes = groupIntoShapes(rings, fillRule);
          if (shapes.length) {
            const key = rgb.join(",");
            if (!byColor.has(key)) byColor.set(key, { rgb, shapes: [] });
            for (const s of shapes) byColor.get(key).shapes.push(s);
          }
        }
      }
      // Every non-self-closing element gets a frame so its closing tag pops
      // symmetrically (a <rect></rect> pair must not pop its parent).
      if (!selfClosing) stack.push(frame);
    }

    if (sawText) {
      warnings.push("This file contains live text. Convert text to outlines in your design app, or it will not stitch.");
    }
    if (sawUse) {
      warnings.push("<use> references are not supported; instanced artwork was skipped. Flatten/expand symbols before exporting.");
    }
    if (sawUnsupportedPaint) {
      warnings.push("Gradient or pattern fills are not supported; those elements were skipped. Use solid fills.");
    }
    if (sawStrokeOnly && byColor.size === 0) {
      warnings.push("This artwork is made of strokes with no fills. Stroke conversion is not supported yet — add fills, or expand the strokes to outlines.");
    }

    const regions = [];
    for (const { rgb, shapes } of byColor.values()) {
      if (shapes.length) regions.push({ rgb, shapes });
    }

    return { regions, pxPerMm: unitsPerMm, warnings };
  }

  return { parseTransform, multiplyMatrix, applyMatrix, primitiveToSubpaths, parseSVG };
});
