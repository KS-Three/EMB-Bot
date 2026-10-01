// @vitest-environment jsdom
import { expect, test } from "vitest";
import { render, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import HoopingCard from "./HoopingCard.svelte";

const ROWS = [
  { label: "Stabilizer", value: "cutaway", note: "escalated - 26,676 stitches; tear-away releases under this much thread" },
  { label: "Topper", value: "no", note: "" },
  { label: "Needle", value: "75/11 sharp", note: "standard for 40wt thread" },
];

test("states each row, with the basis beside the figure it qualifies", () => {
  render(HoopingCard, { props: { rows: ROWS } });
  const card = screen.getByRole("region", { name: "What to hoop" });
  expect(card).toBeInTheDocument();
  for (const label of ["Stabilizer", "Topper", "Needle"]) {
    expect(screen.getByText(label)).toBeInTheDocument();
  }
  // The needle size never appears without what it is a standard FOR.
  const needle = screen.getByText("Needle").parentElement;
  expect(needle).toHaveTextContent("75/11 sharp");
  expect(needle).toHaveTextContent("standard for 40wt thread");
  expect(screen.getByText("Stabilizer").parentElement).toHaveTextContent("26,676 stitches");
  // A row with no note renders no empty <small>.
  expect(screen.getByText("Topper").parentElement.querySelector("small")).toBeNull();
});

test("says it is advice, not a stitch setting", () => {
  render(HoopingCard, { props: { rows: ROWS } });
  expect(screen.getByText(/does not change the stitches/)).toBeInTheDocument();
});

test("renders nothing at all when there is no advice to give", () => {
  const { container } = render(HoopingCard, { props: { rows: [] } });
  expect(container.querySelector(".hooping")).toBeNull();
  expect(container).not.toHaveTextContent("What to hoop");
});
