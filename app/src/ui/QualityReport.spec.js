// @vitest-environment jsdom
//
// The review step's quality report.
//
// What this closes: `preflight.py` has always returned {score, grade,
// findings, metrics} for every digitize and the service has always attached
// it to the job, but the Studio read exactly one field out of it
// (metrics.trims_per_1000, in the Sequencer header). `score` and `grade`
// appeared NOWHERE in app/src — so the app could know a design graded D and
// still let someone sew it without saying so.
//
// These tests are about what the screen SAYS, not about the numbers: the
// grading lives in Python and is tested there. The one exception is the
// duplicate-code case, which is a real crash this component hit against the
// real service before it was fixed.
import { expect, test } from "vitest";
import { render, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";

import QualityReport from "./QualityReport.svelte";

function entry(over = {}) {
  return {
    id: "e1",
    label: "Artwork",
    preflight: {
      score: 40,
      grade: "D",
      findings: [
        { code: "TRIM_HEAVY", severity: "warn", message: "10.3 trims per 1,000 stitches." },
      ],
      metrics: { stitch_count: 10938, color_changes: 17 },
    },
    stats: { thread_m_total: 20.14 },
    ...over,
  };
}

test("renders the grade, the score, and the findings verbatim", () => {
  const { container, getByText } = render(QualityReport, { props: { entries: [entry()] } });

  expect(getByText("D")).toBeInTheDocument();
  expect(getByText("40/100")).toBeInTheDocument();
  // Verbatim: preflight's messages are already written for the person at the
  // machine, so re-wording them here would fork one voice into two.
  expect(getByText("10.3 trims per 1,000 stitches.")).toBeInTheDocument();
  expect(container.querySelector(".qr-grade").className).toMatch(/tone-bad/);
});

test("a finding code is NOT unique, and the list survives repeats", () => {
  // The real crash. Preflight emits one finding per offending thing, so a
  // design with three badly-matched threads gets three THREAD_MATCH_POOR
  // rows. Keying the {#each} on `code` threw `each_key_duplicate` and blanked
  // the whole app — caught by driving the real service, not by a unit test,
  // which is why this one exists.
  const dup = entry({
    preflight: {
      score: 0, grade: "F",
      findings: [
        { code: "THREAD_MATCH_POOR", severity: "warn", message: "Cobblestone is clearly a different color." },
        { code: "THREAD_MATCH_POOR", severity: "warn", message: "Dark Charcoal is clearly a different color." },
        { code: "THREAD_MATCH_POOR", severity: "warn", message: "Caribbean is clearly a different color." },
      ],
      metrics: {},
    },
  });
  const { container, getByText } = render(QualityReport, { props: { entries: [dup] } });

  expect(container.querySelectorAll(".qr-list li")).toHaveLength(3);
  expect(getByText(/Cobblestone/)).toBeInTheDocument();
  expect(getByText(/Caribbean/)).toBeInTheDocument();
});

test("worst first — block, then warn, then info", () => {
  // Severity is reading order, not decoration: "will visibly go wrong" has to
  // come before "sew anyway".
  const mixed = entry({
    preflight: {
      score: 58, grade: "C",
      findings: [
        { code: "A", severity: "info", message: "Informational row." },
        { code: "B", severity: "block", message: "Blocking row." },
        { code: "C", severity: "warn", message: "Warning row." },
      ],
      metrics: {},
    },
  });
  const { container } = render(QualityReport, { props: { entries: [mixed] } });
  const rows = [...container.querySelectorAll(".qr-list li")];
  expect(rows.map((r) => r.className.replace(/.*sev-(\w+).*/, "$1")))
    .toEqual(["block", "warn", "info"]);
});

test("severity is never carried by colour alone", () => {
  // Each row pairs its colour with a glyph, and the two severities that mean
  // "act on this" get a different glyph from the one that means "FYI".
  const mixed = entry({
    preflight: {
      score: 58, grade: "C",
      findings: [
        { code: "B", severity: "block", message: "Blocking row." },
        { code: "A", severity: "info", message: "Informational row." },
      ],
      metrics: {},
    },
  });
  const { container } = render(QualityReport, { props: { entries: [mixed] } });
  const rows = [...container.querySelectorAll(".qr-list li")];
  for (const r of rows) expect(r.querySelector("svg")).toBeTruthy();
  // Different shapes, not just different fills.
  const [blockSvg, infoSvg] = rows.map((r) => r.querySelector("svg").innerHTML);
  expect(blockSvg).not.toBe(infoSvg);
});

test("a clean report says so rather than showing an empty panel", () => {
  const clean = entry({
    preflight: { score: 100, grade: "A", findings: [], metrics: { stitch_count: 900 } },
  });
  const { getByText, container } = render(QualityReport, { props: { entries: [clean] } });
  expect(getByText(/ready to sew/i)).toBeInTheDocument();
  expect(container.querySelector(".qr-grade").className).toMatch(/tone-good/);
});

test("no report at all is stated, never shown as all-clear", () => {
  // A job stored before this field existed, or one run with preflight off.
  // Silence here would read as a pass.
  const { getByText, container } = render(QualityReport, {
    props: { entries: [entry({ preflight: null })] },
  });
  expect(getByText(/No quality report/i)).toBeInTheDocument();
  expect(container.querySelector(".qr-grade")).toBeNull();
});

test("the production line composes from whichever source carries each number", () => {
  // Stitches and thread changes come from preflight's metrics; thread LENGTH
  // exists only on the job's stats, which is why the review step reads both.
  const { getByText } = render(QualityReport, { props: { entries: [entry()] } });
  expect(getByText("10,938 stitches · 17 thread changes · 20.1 m of thread")).toBeInTheDocument();
});

test("a missing number is omitted, never rendered as a zero", () => {
  const sparse = entry({
    preflight: { score: 88, grade: "B", findings: [], metrics: { stitch_count: 500 } },
    stats: null,
  });
  const { container } = render(QualityReport, { props: { entries: [sparse] } });
  const bill = container.querySelector(".qr-bill").textContent;
  expect(bill).toBe("500 stitches");
  expect(bill).not.toMatch(/0 m|0 thread/);
});

test("one thread change reads as singular", () => {
  const one = entry({
    preflight: { score: 88, grade: "B", findings: [], metrics: { stitch_count: 500, color_changes: 1 } },
    stats: null,
  });
  const { container } = render(QualityReport, { props: { entries: [one] } });
  expect(container.querySelector(".qr-bill").textContent).toBe("500 stitches · 1 thread change");
});

test("several artworks are named; a single one is not", () => {
  const solo = render(QualityReport, { props: { entries: [entry()] } });
  expect(solo.container.querySelector(".qr-name")).toBeNull();
  solo.unmount();

  const pair = render(QualityReport, {
    props: { entries: [entry(), entry({ id: "e2", label: "Second logo" })] },
  });
  const names = [...pair.container.querySelectorAll(".qr-name")].map((n) => n.textContent);
  expect(names).toEqual(["Artwork", "Second logo"]);
});

test("nothing digitized means no section at all", () => {
  // A lettering-only project has no report to show, and an empty "Quality
  // check" heading over nothing would imply the check ran and passed.
  const { container } = render(QualityReport, { props: { entries: [] } });
  expect(container.querySelector(".quality")).toBeNull();
});

test("the section is labelled for assistive tech", () => {
  const { container } = render(QualityReport, { props: { entries: [entry()] } });
  const section = container.querySelector("section.quality");
  const heading = container.querySelector("#quality-h");
  expect(section.getAttribute("aria-labelledby")).toBe("quality-h");
  expect(within(section).getByText(heading.textContent)).toBeInTheDocument();
});
