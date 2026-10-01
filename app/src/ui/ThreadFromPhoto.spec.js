// @vitest-environment jsdom
import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import ThreadFromPhoto from "./ThreadFromPhoto.svelte";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const THREADS = [
  { name: "Grey", code: "0108", rgb: [110, 116, 122] },
  { name: "Navy", code: "3355", rgb: [22, 42, 92] },
  { name: "Red", code: "1902", rgb: [200, 16, 46] },
  { name: "White", code: "0015", rgb: [255, 255, 255] },
];

// A 40 x 20 "photo": navy on the left half, red on the right.
function photo() {
  const width = 40;
  const height = 20;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      data.set(x < 20 ? [20, 40, 90, 255] : [200, 16, 46, 255], (y * width + x) * 4);
    }
  }
  return { data, width, height };
}

// jsdom has no layout and no canvas: the decoder is injected, and the
// preview is given a 400 x 200 box so a click maps onto the 40 x 20 image.
function setup(props = {}) {
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    left: 0, top: 0, right: 400, bottom: 200, width: 400, height: 200, x: 0, y: 0,
  });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const onpick = vi.fn();
  const decode = vi.fn(async () => ({ image: photo(), source: null }));
  render(ThreadFromPhoto, { threads: THREADS, chartLabel: "Test chart", onpick, decode, ...props });
  return { onpick, decode };
}

async function upload() {
  const input = screen.getByLabelText("Choose a photo");
  const file = new File(["x"], "shirt.jpg", { type: "image/jpeg" });
  await fireEvent.change(input, { target: { files: [file] } });
  return waitFor(() => screen.getByRole("img", { name: /Your photo/ }));
}

describe("ThreadFromPhoto", () => {
  it("says up front that a photo is not a colour measurement", () => {
    setup();
    expect(screen.getByText(/approximate starting point/i)).toBeInTheDocument();
    expect(screen.getByText(/lighting/i)).toBeInTheDocument();
  });

  it("shows no matches before a photo is clicked", async () => {
    setup();
    await upload();
    expect(screen.queryByRole("list", { name: /Nearest threads/ })).toBeNull();
    expect(screen.getByText(/Click the colour/i)).toBeInTheDocument();
  });

  it("samples where the photo is clicked and ranks the chart, nearest first, with a difference number", async () => {
    setup();
    const canvas = await upload();
    await fireEvent.click(canvas, { clientX: 100, clientY: 100 }); // navy half
    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(rows[0]).toHaveTextContent("3355 Navy");
    expect(rows[0]).toHaveTextContent(/ΔE \d+\.\d/);
    expect(screen.getByRole("list", { name: "Nearest threads in Test chart" })).toBeInTheDocument();

    await fireEvent.click(canvas, { clientX: 300, clientY: 100 }); // red half
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("1902 Red");
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("ΔE 0.0");
  });

  it("hands the chosen thread to onpick", async () => {
    const { onpick } = setup();
    const canvas = await upload();
    await fireEvent.click(canvas, { clientX: 300, clientY: 100 });
    await fireEvent.click(screen.getByRole("button", { name: /Use 1902 Red/ }));
    expect(onpick).toHaveBeenCalledTimes(1);
    expect(onpick.mock.calls[0][0]).toMatchObject({ code: "1902", rgb: [200, 16, 46] });
  });

  it("re-ranks the same sample when the chart changes", async () => {
    const { rerender } = (() => {
      vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
        left: 0, top: 0, right: 400, bottom: 200, width: 400, height: 200, x: 0, y: 0,
      });
      vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
      return render(ThreadFromPhoto, {
        threads: THREADS, chartLabel: "Test chart", decode: async () => ({ image: photo(), source: null }),
      });
    })();
    const canvas = await upload();
    await fireEvent.click(canvas, { clientX: 300, clientY: 100 });
    await rerender({ threads: [{ name: "Brick", code: "B1", rgb: [190, 30, 50] }], chartLabel: "Other" });
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getAllByRole("listitem")[0]).toHaveTextContent("B1 Brick");
  });

  it("reports a file it cannot read instead of failing silently", async () => {
    setup({ decode: async () => { throw new Error("bad"); } });
    const input = screen.getByLabelText("Choose a photo");
    await fireEvent.change(input, { target: { files: [new File(["x"], "x.heic")] } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/could not read/i));
  });
});
