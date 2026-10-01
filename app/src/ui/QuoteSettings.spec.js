// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./QuoteSettings.testHarness.svelte";

const EMPTY = { profileId: null, spm: null, conePrice: null, coneM: null, hourRate: null };

function mount(quote) {
  const onChange = vi.fn();
  const view = render(Harness, { props: { quote: quote || EMPTY, onChange } });
  return { ...view, onChange };
}

test("is closed until asked for, so a customer who wants a file never meets it", () => {
  const { container } = mount();
  expect(container.querySelector("details").open).toBe(false);
  expect(screen.getByText("Quote settings")).toBeInTheDocument();
});

test("a typed price is dispatched as a number, with the rest of the record intact", async () => {
  const { onChange } = mount({ ...EMPTY, hourRate: 30 });
  const cone = screen.getByLabelText("Thread cone price ($)");
  await fireEvent.change(cone, { target: { value: "7.5" } });
  expect(onChange).toHaveBeenCalledWith({ ...EMPTY, hourRate: 30, conePrice: 7.5 });
});

test("clearing a box clears the value rather than storing a zero", async () => {
  const { onChange } = mount({ ...EMPTY, hourRate: 30 });
  await fireEvent.change(screen.getByLabelText("Machine rate ($ per hour)"), { target: { value: "" } });
  expect(onChange).toHaveBeenCalledWith(EMPTY);
});

test("choosing the S-1501 names its rated speed and caps a speed above it", async () => {
  const { onChange } = mount({ ...EMPTY, profileId: "smartstitch_s1501" });
  expect(screen.getByText(/rated up to 1,200 spm/)).toBeInTheDocument();
  await fireEvent.change(screen.getByLabelText("Speed I run at (spm)"), { target: { value: "1500" } });
  expect(onChange).toHaveBeenCalledWith({ ...EMPTY, profileId: "smartstitch_s1501", spm: 1200 });
});

test("with no machine chosen the hint claims no rating", () => {
  mount();
  expect(screen.queryByText(/rated up to/)).toBeNull();
  expect(screen.getByText("Leave blank for the 650 spm planning rate.")).toBeInTheDocument();
});
