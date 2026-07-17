import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Landing from "./Landing";

describe("Landing", () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ token: "jwt-test" }) })
    );
  });

  it("renders the hero tagline, capabilities and registration steps", () => {
    render(<Landing onAuthenticated={() => {}} />);
    expect(screen.getByRole("heading", { name: "Manage Every Moment" })).toBeInTheDocument();
    expect(screen.getByText(/Platform Capabilities/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Operations Copilot/i })).toBeInTheDocument();
    expect(screen.getByText(/Steps to Register/i)).toBeInTheDocument();
  });

  it("logs a fan in with test/test and calls onAuthenticated", async () => {
    const onAuth = vi.fn();
    render(<Landing onAuthenticated={onAuth} />);

    fireEvent.click(screen.getAllByRole("button", { name: /^Fan Login$/i })[0]);
    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: "test" } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: "test" } });
    fireEvent.click(screen.getByRole("button", { name: /Enter as Fan/i }));

    expect(onAuth).toHaveBeenCalledWith({ mode: "fan" });
  });

  it("rejects wrong credentials", () => {
    const onAuth = vi.fn();
    render(<Landing onAuthenticated={onAuth} />);

    fireEvent.click(screen.getAllByRole("button", { name: /^Staff Login$/i })[0]);
    fireEvent.change(screen.getByLabelText(/Username/i), { target: { value: "wrong" } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: /Enter as Staff/i }));

    expect(onAuth).not.toHaveBeenCalled();
    expect(screen.getByText(/use test \/ test/i)).toBeInTheDocument();
  });

  it("opens the Get Started wizard with a role picker", () => {
    render(<Landing onAuthenticated={() => {}} />);
    fireEvent.click(screen.getAllByRole("button", { name: /Get Started/i })[0]);
    expect(screen.getByText(/I'm a Fan/i)).toBeInTheDocument();
    expect(screen.getByText(/I'm Staff/i)).toBeInTheDocument();
  });
});
