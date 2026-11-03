import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("RouteMesh portfolio site", () => {
  it("renders the hero, project walkthrough, and load lab", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /know why every request/i })).toBeInTheDocument();
    expect(screen.getByRole("tablist", { name: /routemesh routing walkthrough/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /change the signals/i })).toBeInTheDocument();
  });

  it("supports arrow-key movement through walkthrough tabs", () => {
    render(<App />);
    const tabs = screen.getByRole("tablist", { name: /routemesh routing walkthrough/i });
    fireEvent.keyDown(tabs, { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: /explain/i })).toHaveAttribute("aria-selected", "true");
  });

  it("lets visitors change the routing policy and open an FAQ answer", () => {
    render(<App />);
    fireEvent.change(screen.getByRole("combobox", { name: /routing policy/i }), {
      target: { value: "least_connections" },
    });
    expect(screen.getAllByRole("heading", { name: /least connections/i })).toHaveLength(2);

    const faq = screen.getByText(/which policies are implemented today/i);
    expect(faq.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(faq);
    expect(faq.closest("details")).toHaveAttribute("open");
  });

  it("shows the generated service graph impact when a dependency fails", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Fail inventory" }));
    expect(screen.getByText(/Affected callers:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/12×/)).toHaveLength(2);
  });
});
