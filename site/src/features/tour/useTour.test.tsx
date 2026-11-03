import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useTour } from "./useTour";

function TourProbe() {
  const tour = useTour(3);
  return (
    <>
      <div id="tl" role="tablist" tabIndex={0} aria-label="test tour">
        tabs
      </div>
      <div id="win">window</div>
      <output>{tour.active}</output>
      <button onClick={() => tour.setPaused(!tour.paused)}>{tour.paused ? "Resume" : "Pause"}</button>
    </>
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useTour", () => {
  it("advances on its timer and pauses while the app window is hovered", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: false } as MediaQueryList);
    render(<TourProbe />);
    act(() => vi.advanceTimersByTime(7000));
    expect(screen.getByRole("status")).toHaveTextContent("1");
    fireEvent.mouseEnter(document.getElementById("win")!);
    act(() => vi.advanceTimersByTime(14000));
    expect(screen.getByRole("status")).toHaveTextContent("1");
    fireEvent.mouseLeave(document.getElementById("win")!);
    act(() => vi.advanceTimersByTime(7000));
    expect(screen.getByRole("status")).toHaveTextContent("2");
  });

  it("starts paused when reduced motion is requested and allows manual resume", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "matchMedia").mockReturnValue({ matches: true } as MediaQueryList);
    render(<TourProbe />);
    expect(screen.getByRole("button", { name: "Resume" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Resume" }));
    act(() => vi.advanceTimersByTime(7000));
    expect(screen.getByRole("status")).toHaveTextContent("1");
  });
});
